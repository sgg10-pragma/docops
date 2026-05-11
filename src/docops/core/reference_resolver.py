from docops.core.config_loader import ProfileDefinition
from docops.core.exceptions import ReferenceResolutionError
from wikiops_sdk.domain import DocumentRef


class ReferenceResolver:
    """Resolves logical aliases from a profile."""

    def resolve_alias(self, profile: ProfileDefinition, alias: str) -> DocumentRef:
        ref = profile.refs.get(alias)
        if not ref:
            raise ReferenceResolutionError(
                f"Reference alias '{alias}' was not found in the profile."
            )
        return ref
