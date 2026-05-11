from __future__ import annotations

import base64
from types import SimpleNamespace

import pytest

from docops.core.exceptions import ConfigurationError
from docops.providers.azure_devops.provider import (
    AzureDevOpsWikiProvider,
    AzureDevOpsWikiProviderFactory,
    PatAzureDevOpsProviderSettings,
)
from docops_sdk.domain import (
    AssetRef,
    AssetRefKind,
    ChangeSet,
    CreateChildDocumentOperation,
    CreateDocumentOperation,
    DocumentVersion,
    OperationStatus,
    PutAssetOperation,
    RefKind,
    UpdateDocumentOperation,
)


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, headers=None, text="") -> None:
        self.status_code = status_code
        self._json_data = json_data or {}
        self.headers = headers or {}
        self.text = text

    def json(self):
        return self._json_data


def settings() -> PatAzureDevOpsProviderSettings:
    return PatAzureDevOpsProviderSettings(
        provider_name="azure",
        organization="acme",
        project="docops",
        wiki="engineering",
    )


def provider() -> AzureDevOpsWikiProvider:
    return AzureDevOpsWikiProvider(settings())


def test_pages_url_builds_expected_endpoint() -> None:
    assert (
        provider()._pages_url()
        == "https://dev.azure.com/acme/docops/_apis/wiki/wikis/engineering/pages"
    )


def test_auth_headers_encode_pat_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZDO_PAT", "secret-token")

    headers = provider()._auth_headers()

    assert headers["Authorization"].startswith("Basic ")
    assert headers["Content-Type"] == "application/json"


def test_if_match_headers_return_expected_values() -> None:
    assert provider()._if_match_headers(None) == {}
    assert provider()._if_match_headers(DocumentVersion(etag='"v1"')) == {"If-Match": '"v1"'}


def test_request_returns_response_for_expected_status(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    class FakeClient:
        def __init__(self, timeout):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def request(self, method, url, params=None, headers=None, json=None, content=None):
            captured.update(
                {
                    "method": method,
                    "url": url,
                    "params": params,
                    "headers": headers,
                    "json": json,
                    "content": content,
                }
            )
            return FakeResponse(status_code=201, json_data={"ok": True})

    monkeypatch.setattr("docops.providers.azure_devops.provider.httpx.Client", FakeClient)
    monkeypatch.setenv("AZDO_PAT", "secret-token")

    response = provider()._request(
        "PUT",
        params={"path": "/docs"},
        json={"content": "hello"},
        expected_status={200, 201},
    )

    assert response.status_code == 201
    assert captured["timeout"] == settings().timeout_seconds
    assert captured["params"]["api-version"] == settings().api_version
    assert captured["params"]["path"] == "/docs"


def test_request_raises_on_unexpected_status(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def __init__(self, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def request(self, method, url, params=None, headers=None, json=None, content=None):
            return FakeResponse(status_code=500, text="broken")

    monkeypatch.setattr("docops.providers.azure_devops.provider.httpx.Client", FakeClient)
    monkeypatch.setenv("AZDO_PAT", "secret-token")

    with pytest.raises(ConfigurationError, match="status 500"):
        provider()._request("GET")


def test_derive_path_ref_requires_parent_reference(doc_ref_factory) -> None:
    with pytest.raises(ConfigurationError, match="parent_ref is required"):
        provider()._derive_path_ref(None, "Child")

    child_ref = provider()._derive_path_ref(doc_ref_factory(path="/Parent"), "Child")

    assert child_ref.locator["path"] == "/Parent/Child"
    assert child_ref.title_hint == "Child"


def test_validate_settings_requires_pat_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AZDO_PAT", raising=False)

    with pytest.raises(ConfigurationError, match="Environment variable 'AZDO_PAT'"):
        provider().validate_settings()

    monkeypatch.setenv("AZDO_PAT", "secret-token")
    provider().validate_settings()


def test_resolve_ref_validates_path_references(doc_ref_factory) -> None:
    candidate = doc_ref_factory(provider="", path="/Docs")
    resolved = provider().resolve_ref(candidate)

    assert resolved.provider == "azure"

    non_path = doc_ref_factory(kind=RefKind.ID)
    with pytest.raises(ConfigurationError, match="only supports path-based refs"):
        provider().resolve_ref(non_path)

    missing_path = doc_ref_factory(path="/Docs")
    missing_path.locator = {}
    with pytest.raises(ConfigurationError, match="require locator.path"):
        provider().resolve_ref(missing_path)


def test_exists_returns_true_for_200_and_false_for_404(monkeypatch: pytest.MonkeyPatch, doc_ref_factory) -> None:
    responses = [FakeResponse(status_code=200), FakeResponse(status_code=404)]

    def _request(*_args, **_kwargs):
        return responses.pop(0)

    monkeypatch.setattr(provider(), "_request", _request)
    live_provider = provider()
    monkeypatch.setattr(live_provider, "_request", _request)

    assert live_provider.exists(doc_ref_factory(path="/docs")) is True
    assert live_provider.exists(doc_ref_factory(path="/docs")) is False


def test_get_document_parses_response(monkeypatch: pytest.MonkeyPatch, doc_ref_factory) -> None:
    ref = doc_ref_factory(path="/Docs/Page")
    live_provider = provider()
    monkeypatch.setattr(
        live_provider,
        "_request",
        lambda *_args, **_kwargs: FakeResponse(
            json_data={
                "path": "/Docs/Page",
                "content": "# Page\n",
                "remoteUrl": "https://example.test/remote",
                "url": "https://example.test/api",
            },
            headers={"ETag": '"v1"'},
        ),
    )

    document = live_provider.get_document(ref)

    assert document.title == "Page"
    assert document.content == "# Page\n"
    assert document.version.etag == '"v1"'
    assert document.metadata["remote_url"] == "https://example.test/remote"


def test_build_link_encodes_page_path(doc_ref_factory) -> None:
    link = provider().build_link(doc_ref_factory(path="/Docs/My Page"))

    assert "pagePath=/Docs/My%20Page" in link


def test_put_asset_uploads_attachment_and_returns_asset(monkeypatch: pytest.MonkeyPatch) -> None:
    live_provider = provider()
    captured = {}

    def _request(method, url=None, params=None, headers=None, json=None, content=None, expected_status=None):
        captured.update(
            {
                "method": method,
                "url": url,
                "params": params,
                "headers": headers,
                "content": content,
                "expected_status": expected_status,
            }
        )
        return FakeResponse(
            status_code=201,
            json_data={"name": "logo--abcd1234.png", "path": "/.attachments/logo--abcd1234.png"},
            headers={"ETag": '"asset-v1"'},
        )

    monkeypatch.setattr(live_provider, "_request", _request)

    asset = live_provider.put_asset(
        PutAssetOperation(
            asset_key="logo",
            source={"kind": "plugin_resource", "relative_path": "resources/logo.png"},
            name="logo.png",
            media_type="image/png",
        ),
        b"PNG",
    )

    assert captured["method"] == "PUT"
    assert captured["url"] == live_provider._attachments_url()
    assert captured["params"]["name"].startswith("logo--")
    assert captured["headers"]["Content-Type"] == "application/octet-stream"
    assert captured["content"] == base64.b64encode(b"PNG")
    assert asset.ref.kind is AssetRefKind.PATH
    assert asset.ref.locator["path"] == "/.attachments/logo--abcd1234.png"
    assert asset.version.etag == '"asset-v1"'


def test_put_asset_treats_duplicate_attachment_as_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    live_provider = provider()

    def _request(*_args, **_kwargs):
        raise ConfigurationError(
            "Azure DevOps API request failed with status 500: "
            '{"message":"The wiki attachment creation failed with message : '
            "The path '/.attachments/logo--abcd1234.png' specified in the add "
            'operation already exists. Please specify a new path.",'
            '"typeKey":"WikiCreateAttachmentFailedException"}'
        )

    monkeypatch.setattr(live_provider, "_request", _request)

    asset = live_provider.put_asset(
        PutAssetOperation(
            asset_key="logo",
            source={"kind": "plugin_resource", "relative_path": "resources/logo.png"},
            name="logo.png",
            media_type="image/png",
        ),
        b"PNG",
    )

    assert asset.ref.locator["path"] == "/.attachments/logo--abcd1234.png"
    assert asset.name == "logo--abcd1234.png"
    assert asset.version is None
    assert asset.metadata["path"] == "/.attachments/logo--abcd1234.png"


def test_put_asset_raises_for_non_idempotent_provider_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    live_provider = provider()

    def _request(*_args, **_kwargs):
        raise ConfigurationError(
            "Azure DevOps API request failed with status 500: "
            '{"message":"backend unavailable","typeKey":"SomeOtherFailure"}'
        )

    monkeypatch.setattr(live_provider, "_request", _request)

    with pytest.raises(ConfigurationError, match="backend unavailable"):
        live_provider.put_asset(
            PutAssetOperation(
                asset_key="logo",
                source={
                    "kind": "plugin_resource",
                    "relative_path": "resources/logo.png",
                },
                name="logo.png",
                media_type="image/png",
            ),
            b"PNG",
        )


def test_build_asset_reference_requires_path_based_asset_ref() -> None:
    asset_ref = AssetRef(
        provider="azure",
        kind=AssetRefKind.PATH,
        locator={"path": "/.attachments/logo.png"},
    )

    assert provider().build_asset_reference(asset_ref) == "/.attachments/logo.png"


def test_apply_changes_handles_update_create_and_child_operations(
    monkeypatch: pytest.MonkeyPatch,
    doc_ref_factory,
) -> None:
    ref = doc_ref_factory(path="/Docs/Page")
    parent_ref = doc_ref_factory(path="/Docs")
    live_provider = provider()
    uploaded_paths = []

    def _upload_content(path, content, headers=None):
        uploaded_paths.append((path, content, headers))
        return FakeResponse(headers={"ETag": '"v2"'})

    monkeypatch.setattr(live_provider, "_upload_content", _upload_content)
    change_set = ChangeSet(
        plugin_id="demo.plugin",
        operations=[
            UpdateDocumentOperation(
                ref=ref,
                new_content="# Updated\n",
                expected_version=DocumentVersion(etag='"v1"'),
            ),
            CreateDocumentOperation(ref=ref, title="Page", content="# Created\n"),
            CreateChildDocumentOperation(
                parent_ref=parent_ref,
                child_title="Child",
                child_content="# Child\n",
            ),
        ],
    )

    result = live_provider.apply_changes(change_set)

    assert [item.status for item in result.results] == [
        OperationStatus.APPLIED,
        OperationStatus.APPLIED,
        OperationStatus.APPLIED,
    ]
    assert uploaded_paths[0] == ("/Docs/Page", "# Updated\n", {"If-Match": '"v1"'})
    assert uploaded_paths[1] == ("/Docs/Page", "# Created\n", None)
    assert uploaded_paths[2] == ("/Docs/Child", "# Child\n", None)


def test_apply_changes_skips_unsupported_operations() -> None:
    live_provider = provider()
    change_set = SimpleNamespace(
        operations=[SimpleNamespace(operation_id="op-1", operation="noop")]
    )

    result = live_provider.apply_changes(change_set)

    assert result.results[0].status == OperationStatus.SKIPPED
    assert "Unsupported operation type" in result.results[0].message


def test_apply_changes_records_failures(monkeypatch: pytest.MonkeyPatch, doc_ref_factory) -> None:
    ref = doc_ref_factory(path="/Docs/Page")
    live_provider = provider()
    monkeypatch.setattr(
        live_provider,
        "_upload_content",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    change_set = ChangeSet(
        plugin_id="demo.plugin",
        operations=[UpdateDocumentOperation(ref=ref, new_content="# Updated\n")],
    )

    result = live_provider.apply_changes(change_set)

    assert result.results[0].status == OperationStatus.FAILED
    assert result.results[0].message == "boom"


def test_factory_accepts_typed_and_raw_settings() -> None:
    factory = AzureDevOpsWikiProviderFactory()
    typed_settings = settings()

    provider_from_model = factory.create(typed_settings)
    provider_from_dict = factory.create(typed_settings.model_dump())

    assert provider_from_model.settings == typed_settings
    assert provider_from_dict.settings.provider_name == "azure"
