from __future__ import annotations

from wikiops.core.apply_engine import ApplyEngine


def test_apply_delegates_to_provider(changeset_factory, apply_result_factory) -> None:
    changeset = changeset_factory()
    expected = apply_result_factory()
    calls = []

    class Provider:
        def apply_changes(self, candidate):
            calls.append(candidate)
            return expected

    result = ApplyEngine().apply(Provider(), changeset)

    assert result is expected
    assert calls == [changeset]
