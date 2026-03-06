"""App models package.

Keep package import resilient: load core user models eagerly, while optional/legacy
model groups are imported best-effort to avoid hard-failing unrelated test runs.
"""

from app.models.user import User, Invitation

__all__ = ["User", "Invitation"]


def _try_export(module_path: str, names: list[str]) -> None:
    """Best-effort export helper for optional model groups."""
    try:
        module = __import__(module_path, fromlist=names)
        for name in names:
            if hasattr(module, name):
                globals()[name] = getattr(module, name)
                __all__.append(name)
    except Exception:
        # Do not fail package import for unrelated model group issues.
        pass


_try_export(
    "app.models.business",
    ["BusinessProcess", "ProcessStep", "ProcessExecution", "ProcessTrigger"],
)
_try_export(
    "app.models.courses",
    ["CourseTemplate", "CourseModule", "Lesson", "CourseEnrollment"],
)
_try_export("app.models.audit", ["AuthAuditLog"])
_try_export("app.models.policy", ["Policy"])
_try_export("app.models.autonomous_pipeline", ["Workspace", "Project", "RunContract"])
_try_export("app.models.widget", ["WidgetSessionORM", "WidgetMessageORM", "WidgetCredentialORM"])

# Compatibility aliases
if "CourseTemplate" in globals():
    Course = globals()["CourseTemplate"]
    __all__.append("Course")
if "Lesson" in globals():
    CourseLesson = globals()["Lesson"]
    __all__.append("CourseLesson")
if "CourseEnrollment" in globals():
    Enrollment = globals()["CourseEnrollment"]
    __all__.append("Enrollment")
