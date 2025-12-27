"""
Course Distribution Storage Adapter

Sprint 15: Course Distribution & Growth Layer
File-based atomic storage for course distributions.
"""

from __future__ import annotations

import json
import fcntl
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .distribution_models import (
    CourseDistribution,
    CourseVisibility,
    MicroNicheDerivedContent,
)


# Storage paths
STORAGE_BASE = Path("storage/course_distribution")
DISTRIBUTIONS_FILE = STORAGE_BASE / "distributions.json"
SLUG_INDEX_FILE = STORAGE_BASE / "slug_index.json"
VIEWS_LOG_FILE = STORAGE_BASE / "views.jsonl"
DERIVATIONS_FILE = STORAGE_BASE / "derivations.json"


@contextmanager
def file_lock(file_path: Path, mode: str = 'r'):
    """
    Atomic file operations with exclusive locking.

    Args:
        file_path: Path to file
        mode: File open mode ('r', 'a', 'w')

    Yields:
        File handle with exclusive lock
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Ensure file exists for read mode
    if mode == 'r' and not file_path.exists():
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({} if file_path.suffix == '.json' else [], f)

    with open(file_path, mode, encoding='utf-8') as f:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            yield f
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


class DistributionStorage:
    """
    Storage adapter for course distributions.

    Features:
    - Atomic file operations
    - Slug-based lookups
    - Version management
    - Aggregated view tracking
    """

    def __init__(self, storage_path: Path = STORAGE_BASE):
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._initialize_storage()

    def _initialize_storage(self):
        """Initialize storage files if they don't exist."""
        files = [
            (DISTRIBUTIONS_FILE, {}),
            (SLUG_INDEX_FILE, {}),
            (DERIVATIONS_FILE, {}),
        ]
        for file_path, default_content in files:
            if not file_path.exists():
                with file_lock(file_path, 'w') as f:
                    json.dump(default_content, f, indent=2)

        if not VIEWS_LOG_FILE.exists():
            VIEWS_LOG_FILE.touch()

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    def save_distribution(self, distribution: CourseDistribution) -> bool:
        """
        Save or update a course distribution.

        Args:
            distribution: CourseDistribution instance

        Returns:
            True if successful

        Raises:
            ValueError: If slug already exists for different distribution
        """
        # Update timestamp
        distribution.updated_at = datetime.utcnow().timestamp()

        # Load existing data
        with file_lock(DISTRIBUTIONS_FILE, 'r') as f:
            distributions = json.load(f)

        with file_lock(SLUG_INDEX_FILE, 'r') as f:
            slug_index = json.load(f)

        # Check slug uniqueness
        existing_dist_id = slug_index.get(distribution.slug)
        if existing_dist_id and existing_dist_id != distribution.distribution_id:
            raise ValueError(
                f"Slug '{distribution.slug}' already exists for distribution {existing_dist_id}"
            )

        # Save distribution
        distributions[distribution.distribution_id] = distribution.model_dump()

        # Update slug index
        slug_index[distribution.slug] = distribution.distribution_id

        # Write atomically
        with file_lock(DISTRIBUTIONS_FILE, 'w') as f:
            json.dump(distributions, f, indent=2)

        with file_lock(SLUG_INDEX_FILE, 'w') as f:
            json.dump(slug_index, f, indent=2)

        return True

    def get_distribution_by_id(self, distribution_id: str) -> Optional[CourseDistribution]:
        """Get distribution by ID."""
        with file_lock(DISTRIBUTIONS_FILE, 'r') as f:
            distributions = json.load(f)

        data = distributions.get(distribution_id)
        if not data:
            return None

        return CourseDistribution(**data)

    def get_distribution_by_slug(self, slug: str) -> Optional[CourseDistribution]:
        """Get distribution by slug."""
        with file_lock(SLUG_INDEX_FILE, 'r') as f:
            slug_index = json.load(f)

        distribution_id = slug_index.get(slug)
        if not distribution_id:
            return None

        return self.get_distribution_by_id(distribution_id)

    def list_distributions(
        self,
        visibility: Optional[CourseVisibility] = None,
        language: Optional[str] = None,
        only_published: bool = False,
    ) -> List[CourseDistribution]:
        """
        List distributions with optional filters.

        Args:
            visibility: Filter by visibility
            language: Filter by language
            only_published: Only return published courses

        Returns:
            List of CourseDistribution instances
        """
        with file_lock(DISTRIBUTIONS_FILE, 'r') as f:
            distributions = json.load(f)

        results = []
        for data in distributions.values():
            dist = CourseDistribution(**data)

            # Apply filters
            if visibility and dist.visibility != visibility:
                continue

            if language and dist.language != language:
                continue

            if only_published and not dist.is_public():
                continue

            results.append(dist)

        # Sort by published_at (newest first)
        results.sort(key=lambda x: x.published_at or 0, reverse=True)
        return results

    def delete_distribution(self, distribution_id: str) -> bool:
        """
        Delete a distribution.

        Args:
            distribution_id: Distribution ID

        Returns:
            True if deleted, False if not found
        """
        with file_lock(DISTRIBUTIONS_FILE, 'r') as f:
            distributions = json.load(f)

        if distribution_id not in distributions:
            return False

        # Get slug before deleting
        slug = distributions[distribution_id].get("slug")

        # Delete from distributions
        del distributions[distribution_id]

        # Delete from slug index
        with file_lock(SLUG_INDEX_FILE, 'r') as f:
            slug_index = json.load(f)

        if slug in slug_index:
            del slug_index[slug]

        # Write atomically
        with file_lock(DISTRIBUTIONS_FILE, 'w') as f:
            json.dump(distributions, f, indent=2)

        with file_lock(SLUG_INDEX_FILE, 'w') as f:
            json.dump(slug_index, f, indent=2)

        return True

    # =========================================================================
    # View Tracking (Aggregated, No PII)
    # =========================================================================

    def log_view(self, slug: str, language: Optional[str] = None) -> bool:
        """
        Log a course view (aggregated event).

        Args:
            slug: Course slug
            language: Browser language (optional)

        Returns:
            True if logged
        """
        event = {
            "event": "course.viewed",
            "slug": slug,
            "language": language,
            "timestamp": datetime.utcnow().timestamp(),
        }

        with file_lock(VIEWS_LOG_FILE, 'a') as f:
            f.write(json.dumps(event) + '\n')

        # Increment view count
        self._increment_counter(slug, "view_count")
        return True

    def log_enrollment_click(self, slug: str) -> bool:
        """
        Log enrollment CTA click.

        Args:
            slug: Course slug

        Returns:
            True if logged
        """
        event = {
            "event": "course.enrollment_clicked",
            "slug": slug,
            "timestamp": datetime.utcnow().timestamp(),
        }

        with file_lock(VIEWS_LOG_FILE, 'a') as f:
            f.write(json.dumps(event) + '\n')

        # Increment enrollment count
        self._increment_counter(slug, "enrollment_count")
        return True

    def _increment_counter(self, slug: str, counter_field: str) -> bool:
        """
        Atomically increment a counter field.

        Args:
            slug: Course slug
            counter_field: Field name ('view_count' or 'enrollment_count')

        Returns:
            True if incremented
        """
        distribution = self.get_distribution_by_slug(slug)
        if not distribution:
            return False

        # Increment counter
        current_value = getattr(distribution, counter_field, 0)
        setattr(distribution, counter_field, current_value + 1)

        # Save
        self.save_distribution(distribution)
        return True

    # =========================================================================
    # Micro-Niche Derivations
    # =========================================================================

    def save_derivation(
        self,
        parent_course_id: str,
        child_distribution_id: str,
        derived_content: MicroNicheDerivedContent,
    ) -> bool:
        """
        Save micro-niche derivation metadata.

        Args:
            parent_course_id: Parent course ID
            child_distribution_id: Child distribution ID
            derived_content: Derivation content overrides

        Returns:
            True if saved
        """
        with file_lock(DERIVATIONS_FILE, 'r') as f:
            derivations = json.load(f)

        # Store derivation tree
        if parent_course_id not in derivations:
            derivations[parent_course_id] = []

        derivations[parent_course_id].append({
            "child_distribution_id": child_distribution_id,
            "derived_content": derived_content.model_dump(),
            "created_at": datetime.utcnow().timestamp(),
        })

        with file_lock(DERIVATIONS_FILE, 'w') as f:
            json.dump(derivations, f, indent=2)

        return True

    def get_derivations(self, parent_course_id: str) -> List[Dict[str, Any]]:
        """
        Get all micro-niche variants derived from parent course.

        Args:
            parent_course_id: Parent course ID

        Returns:
            List of derivation records
        """
        with file_lock(DERIVATIONS_FILE, 'r') as f:
            derivations = json.load(f)

        return derivations.get(parent_course_id, [])

    # =========================================================================
    # Version Management
    # =========================================================================

    def bump_version(self, distribution_id: str) -> Optional[str]:
        """
        Bump course version (v1 -> v2, etc.).

        Args:
            distribution_id: Distribution ID

        Returns:
            New version string, or None if not found
        """
        distribution = self.get_distribution_by_id(distribution_id)
        if not distribution:
            return None

        # Parse version
        current_version = distribution.version
        if current_version.startswith("v"):
            version_num = int(current_version[1:])
            new_version = f"v{version_num + 1}"
        else:
            new_version = "v2"

        # Update
        distribution.version = new_version
        distribution.updated_at = datetime.utcnow().timestamp()

        self.save_distribution(distribution)
        return new_version

    # =========================================================================
    # Publishing
    # =========================================================================

    def publish_distribution(self, distribution_id: str) -> bool:
        """
        Publish a distribution (set visibility to PUBLIC and published_at timestamp).

        Args:
            distribution_id: Distribution ID

        Returns:
            True if published
        """
        distribution = self.get_distribution_by_id(distribution_id)
        if not distribution:
            return False

        distribution.visibility = CourseVisibility.PUBLIC
        distribution.published_at = datetime.utcnow().timestamp()

        self.save_distribution(distribution)
        return True

    def unpublish_distribution(self, distribution_id: str) -> bool:
        """
        Unpublish a distribution (set visibility to PRIVATE).

        Args:
            distribution_id: Distribution ID

        Returns:
            True if unpublished
        """
        distribution = self.get_distribution_by_id(distribution_id)
        if not distribution:
            return False

        distribution.visibility = CourseVisibility.PRIVATE
        # Keep published_at for historical record

        self.save_distribution(distribution)
        return True
