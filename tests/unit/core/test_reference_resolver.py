from __future__ import annotations

import pytest

from docops.core.config_loader import ProfileDefinition
from docops.core.exceptions import ReferenceResolutionError
from docops.core.reference_resolver import ReferenceResolver


def test_resolve_alias_returns_matching_ref(doc_ref_factory) -> None:
    ref = doc_ref_factory(path="/inventory")
    profile = ProfileDefinition(provider="default", refs={"inventory": ref})

    assert ReferenceResolver().resolve_alias(profile, "inventory") == ref


def test_resolve_alias_rejects_missing_alias() -> None:
    profile = ProfileDefinition(provider="default")

    with pytest.raises(ReferenceResolutionError, match="Reference alias 'missing'"):
        ReferenceResolver().resolve_alias(profile, "missing")
