import re
import os
import base64
import hashlib
from urllib.parse import quote
from typing import Any, Optional, Dict, Set, List

import httpx
from pydantic import Field

from wikiops.core.exceptions import ConfigurationError
from wikiops_sdk.contracts import ProviderSettings
from wikiops_sdk.domain import (
    Asset,
    AssetRef,
    AssetRefKind,
    AppliedOperationResult,
    ApplyResult,
    ChangeSet,
    CreateChildDocumentOperation,
    CreateDocumentOperation,
    Document,
    DocumentRef,
    DocumentVersion,
    ExecutionContext,
    OperationStatus,
    ProviderCapability,
    PutAssetOperation,
    RefKind,
    UpdateDocumentOperation,
)


class BaseAzureDevOpsProviderSettings(ProviderSettings):
    """Base settings for Azure DevOps Wiki access"""

    organization: str = Field(..., description="Azure DevOps organization name")
    project: str = Field(..., description="Azure DevOps project name")
    wiki: str = Field(..., description="Azure DevOps wiki name")
    api_version: str = Field(
        "7.1", description="Azure DevOps API version to use for requests"
    )
    timeout_seconds: float = Field(
        30.0, description="Timeout in seconds for API requests to Azure DevOps"
    )


class PatAzureDevOpsProviderSettings(BaseAzureDevOpsProviderSettings):
    """Settings for Azure DevOps Wiki access using Personal Access Token (PAT)"""

    pat_token_env: str = Field(
        default="AZDO_PAT",
        description="Personal Access Token for Azure DevOps authentication",
    )


class AzureDevOpsWikiProvider:
    """Azure DevOps Wiki provider backed by the REST API"""

    provider_id = "azure_devops_wiki"

    def __init__(self, settings: PatAzureDevOpsProviderSettings):
        self.settings = settings
        self.common_params = {"api-version": self.settings.api_version}

    def _pages_url(self) -> str:
        return (
            f"https://dev.azure.com/{self.settings.organization}/{self.settings.project}"
            f"/_apis/wiki/wikis/{self.settings.wiki}/pages"
        )

    def _attachments_url(self) -> str:
        return (
            f"https://dev.azure.com/{self.settings.organization}/{self.settings.project}"
            f"/_apis/wiki/wikis/{self.settings.wiki}/attachments"
        )

    def _auth_headers(self) -> Dict[str, str]:
        token = os.getenv(self.settings.pat_token_env, "")
        raw = f":{token}".encode("utf-8")
        encoded = base64.b64encode(raw).decode("utf-8")
        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        url: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None,
        content: Optional[bytes] = None,
        expected_status: Set[int] = None,
    ) -> httpx.Response:
        expected = expected_status or {200}
        with httpx.Client(timeout=self.settings.timeout_seconds) as client:
            response = client.request(
                method,
                url or self._pages_url(),
                params={**self.common_params, **(params or {})},
                headers={**self._auth_headers(), **(headers or {})},
                json=json,
                content=content,
            )
        if response.status_code not in expected:
            raise ConfigurationError(
                f"Azure DevOps API request failed with status {response.status_code}: {response.text}"
            )
        return response

    @staticmethod
    def _if_match_headers(version: Optional[DocumentVersion]) -> Dict[str, str]:
        if version and version.etag:
            return {"If-Match": version.etag}
        return {}

    @staticmethod
    def _path(ref: DocumentRef) -> str:
        return ref.locator["path"]

    def _derive_path_ref(
        self, parent_ref: Optional[DocumentRef], title: str
    ) -> DocumentRef:
        if not parent_ref:
            raise ConfigurationError(
                "A parent_ref is required to derive the Azure DevOps wiki path."
            )
        base_path = self._path(parent_ref).rstrip("/")
        child_path = f"{base_path}/{title}"
        return DocumentRef(
            provider=self.settings.provider_name,
            kind=RefKind.PATH,
            locator={"path": child_path},
            title_hint=title,
        )

    def _upload_content(
        self, path: str, content: str, headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        return self._request(
            "PUT",
            params={"path": path},
            headers=headers,
            json={"content": content},
            expected_status={200, 201},
        )

    def capabilities(self) -> set[ProviderCapability]:
        return {
            ProviderCapability.READ_DOCUMENT,
            ProviderCapability.CHECK_EXISTS,
            ProviderCapability.CREATE_DOCUMENT,
            ProviderCapability.UPDATE_DOCUMENT,
            ProviderCapability.CREATE_CHILD_DOCUMENT,
            ProviderCapability.BUILD_LINK,
            ProviderCapability.PUT_ASSET,
            ProviderCapability.RESOLVE_BY_PATH,
            ProviderCapability.HIERARCHICAL_PAGES,
            ProviderCapability.VERSION_CHECK,
        }

    def validate_settings(self) -> None:
        if not os.getenv(self.settings.pat_token_env):
            raise ConfigurationError(
                f"Environment variable '{self.settings.pat_token_env}' is required for Azure DevOps authentication."
            )

    def resolve_ref(
        self, ref: DocumentRef, ctx: Optional[ExecutionContext] = None
    ) -> DocumentRef:
        if ref.kind != RefKind.PATH:
            raise ConfigurationError(
                "The MVP Azure DevOps provider only supports path-based refs."
            )
        if "path" not in ref.locator:
            raise ConfigurationError("Azure DevOps path refs require locator.path.")
        if not ref.provider:
            ref.provider = self.settings.provider_name
        return ref

    def exists(self, ref: DocumentRef) -> bool:
        response = self._request(
            "GET",
            params={"path": self._path(ref)},
            expected_status={200, 404},
        )
        return response.status_code == 200

    def get_document(self, ref: DocumentRef) -> Document:
        response = self._request(
            "GET",
            params={"path": self._path(ref), "includeContent": "true"},
            expected_status={200},
        )
        payload = response.json()
        return Document(
            ref=ref,
            title=payload.get("path", self._path(ref)).split("/")[-1] or None,
            content=payload.get("content", ""),
            version=DocumentVersion(etag=response.headers.get("ETag")),
            metadata={
                "path": payload.get("path"),
                "remote_url": payload.get("remoteUrl"),
                "url": payload.get("url"),
            },
        )

    def build_link(self, ref: DocumentRef) -> Optional[str]:
        path = quote(self._path(ref), safe="/")
        return (
            f"https://dev.azure.com/{self.settings.organization}/{self.settings.project}"
            f"/_wiki/wikis/{self.settings.wiki}?pagePath={path}"
        )

    def put_asset(self, operation: PutAssetOperation, content: bytes) -> Asset:
        stored_name = self._hashed_asset_name(operation.name, content)
        # Azure DevOps documents this endpoint as an octet-stream upload, but in
        # practice the wiki attachments API expects the request body to contain
        # Base64-encoded payload bytes.
        encoded_content = base64.b64encode(content)
        try:
            response = self._request(
                "PUT",
                url=self._attachments_url(),
                params={"name": stored_name},
                headers={"Content-Type": "application/octet-stream"},
                content=encoded_content,
                expected_status={201},
            )
            payload = response.json()
            asset_path = payload.get("path", f"/.attachments/{stored_name}")
            asset_name = payload.get("name", stored_name)
            asset_metadata = {
                "path": payload.get("path"),
                "url": payload.get("url"),
            }
            asset_version = DocumentVersion(etag=response.headers.get("ETag"))
        except ConfigurationError as exc:
            if not self._is_duplicate_attachment_error(str(exc)):
                raise
            asset_path = (
                self._extract_attachment_path(str(exc))
                or f"/.attachments/{stored_name}"
            )
            asset_name = asset_path.rsplit("/", 1)[-1]
            asset_metadata = {"path": asset_path}
            asset_version = None

        asset_ref = AssetRef(
            provider=self.settings.provider_name,
            kind=AssetRefKind.PATH,
            locator={"path": asset_path},
        )
        return Asset(
            ref=asset_ref,
            name=asset_name,
            media_type=operation.media_type or "application/octet-stream",
            size_bytes=len(content),
            version=asset_version,
            metadata=asset_metadata,
        )

    def build_asset_reference(self, ref: AssetRef) -> str:
        if ref.kind is not AssetRefKind.PATH or "path" not in ref.locator:
            raise ConfigurationError(
                "Azure DevOps asset references must be path-based and include locator.path."
            )
        return ref.locator["path"]

    @staticmethod
    def _hashed_asset_name(name: str | None, content: bytes) -> str:
        if not name:
            raise ConfigurationError(
                "Azure DevOps asset uploads require the prepared operation to include a file name."
            )
        path = os.path.splitext(name)
        digest = hashlib.sha256(content).hexdigest()[:8]
        stem, suffix = path
        return f"{stem}--{digest}{suffix}"

    @staticmethod
    def _is_duplicate_attachment_error(message: str) -> bool:
        lowered = message.lower()
        return (
            "wikicreateattachmentfailedexception" in lowered
            and "already exists" in lowered
        )

    @staticmethod
    def _extract_attachment_path(message: str) -> str | None:
        match = re.search(
            r"path '([^']+/\.attachments/[^']+|/\.attachments/[^']+)'", message
        )
        if match is not None:
            candidate = match.group(1)
            attachment_index = candidate.find("/.attachments/")
            return candidate[attachment_index:]
        return None

    def apply_changes(self, changeset: ChangeSet) -> ApplyResult:
        results: List[AppliedOperationResult] = []

        for op in changeset.operations:
            try:
                if isinstance(op, UpdateDocumentOperation):

                    response = self._upload_content(
                        self._path(op.ref),
                        op.new_content,
                        headers=self._if_match_headers(op.expected_version),
                    )

                    results.append(
                        AppliedOperationResult(
                            operation_id=op.operation_id,
                            status=OperationStatus.APPLIED,
                            resolved_ref=op.ref,
                            resulting_version=DocumentVersion(
                                etag=response.headers.get("ETag")
                            ),
                        )
                    )

                elif isinstance(op, CreateDocumentOperation):
                    target_ref = op.ref or self._derive_path_ref(
                        op.parent_ref, op.title
                    )

                    response = self._upload_content(
                        self._path(target_ref),
                        op.content,
                    )

                    results.append(
                        AppliedOperationResult(
                            operation_id=op.operation_id,
                            status=OperationStatus.APPLIED,
                            resolved_ref=target_ref,
                            resulting_version=DocumentVersion(
                                etag=response.headers.get("ETag")
                            ),
                        )
                    )

                elif isinstance(op, CreateChildDocumentOperation):
                    child_ref = self._derive_path_ref(op.parent_ref, op.child_title)

                    response = self._upload_content(
                        self._path(child_ref),
                        op.child_content,
                    )
                    results.append(
                        AppliedOperationResult(
                            operation_id=op.operation_id,
                            status=OperationStatus.APPLIED,
                            resolved_ref=child_ref,
                            resulting_version=DocumentVersion(
                                etag=response.headers.get("ETag")
                            ),
                        )
                    )

                else:
                    results.append(
                        AppliedOperationResult(
                            operation_id=op.operation_id,
                            status=OperationStatus.SKIPPED,
                            message=f"Unsupported operation type: {type(op).__name__}",
                        )
                    )
            except Exception as exc:  # noqa: PERF203, BLE001
                results.append(
                    AppliedOperationResult(
                        operation_id=op.operation_id,
                        status=OperationStatus.FAILED,
                        message=str(exc),
                    )
                )

        return ApplyResult(provider_name=self.settings.provider_name, results=results)


class AzureDevOpsWikiProviderFactory:
    """Factory for Azure DevOps Wiki providers."""

    provider_id = AzureDevOpsWikiProvider.provider_id
    settings_model = PatAzureDevOpsProviderSettings

    def create(
        self, settings: PatAzureDevOpsProviderSettings | Dict[str, Any]
    ) -> AzureDevOpsWikiProvider:
        typed_settings = (
            settings
            if isinstance(settings, PatAzureDevOpsProviderSettings)
            else self.settings_model.model_validate(settings)
        )
        provider = AzureDevOpsWikiProvider(typed_settings)
        return provider
