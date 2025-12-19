# backend/app/main.py
"""
⚠️ DEPRECATED: This file is deprecated as of v0.3.0

The entry point has been moved to backend/main.py for consolidation.
This file is kept for backward compatibility only.

If you're importing from this file, update your imports:
    OLD: from app.main import app
    NEW: from backend.main import app

This compatibility wrapper will be removed in v0.4.0
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "backend/app/main.py is deprecated since v0.3.0. "
    "Use backend/main.py instead. "
    "This compatibility wrapper will be removed in v0.4.0",
    DeprecationWarning,
    stacklevel=2
)

# Import from new unified location for backward compatibility
try:
    from backend.main import app, create_app, lifespan

    __all__ = ["app", "create_app", "lifespan"]
except ImportError as e:
    # Fallback error message if import fails
    raise ImportError(
        f"Could not import from backend.main: {e}\n"
        "Please ensure backend/main.py exists and update your imports."
    ) from e
