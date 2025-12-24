"""
Blueprint Library Service

Manages blueprint registry and lifecycle.
"""

from __future__ import annotations

from typing import List, Optional

from loguru import logger

from .builtin import ALL_BUILTIN_BLUEPRINTS
from .schemas import AgentBlueprint, BlueprintLibrary as _BlueprintLibrary


class BlueprintLibraryService(_BlueprintLibrary):
    """
    Enhanced Blueprint Library with built-in blueprints.

    Extends base BlueprintLibrary with auto-loading of built-in templates.
    """

    def __init__(self):
        super().__init__()
        self._load_builtin_blueprints()

    def _load_builtin_blueprints(self):
        """Load all built-in blueprint definitions."""
        for blueprint in ALL_BUILTIN_BLUEPRINTS:
            self.register(blueprint)

        logger.info(f"Loaded {len(ALL_BUILTIN_BLUEPRINTS)} built-in blueprints")

    def get_summary(self) -> dict:
        """Get library summary statistics."""
        blueprints = self.list_all()

        return {
            "total_blueprints": len(blueprints),
            "builtin_count": len(ALL_BUILTIN_BLUEPRINTS),
            "custom_count": len(blueprints) - len(ALL_BUILTIN_BLUEPRINTS),
            "blueprints_by_tag": self._get_tag_counts(),
            "allow_mutations_count": sum(1 for bp in blueprints if bp.allow_mutations),
        }

    def _get_tag_counts(self) -> dict:
        """Get blueprint counts by tag."""
        tag_counts = {}

        for blueprint in self.list_all():
            for tag in blueprint.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return tag_counts

    def search(
        self,
        query: str = None,
        tag: str = None,
        allow_mutations: bool = None,
    ) -> List[AgentBlueprint]:
        """
        Search blueprints by criteria.

        Args:
            query: Text search in name/description
            tag: Filter by tag
            allow_mutations: Filter by mutation allowance

        Returns:
            Matching blueprints
        """
        results = self.list_all()

        if tag:
            results = [bp for bp in results if tag in bp.tags]

        if allow_mutations is not None:
            results = [bp for bp in results if bp.allow_mutations == allow_mutations]

        if query:
            query_lower = query.lower()
            results = [
                bp
                for bp in results
                if query_lower in bp.name.lower()
                or query_lower in bp.description.lower()
            ]

        return results


# Singleton instance
_blueprint_library: Optional[BlueprintLibraryService] = None


def get_blueprint_library() -> BlueprintLibraryService:
    """Get singleton BlueprintLibrary instance."""
    global _blueprint_library
    if _blueprint_library is None:
        _blueprint_library = BlueprintLibraryService()
    return _blueprint_library
