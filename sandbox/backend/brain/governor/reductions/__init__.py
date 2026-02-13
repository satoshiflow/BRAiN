"""
Constraint Reduction System (Phase 2b)

Applies manifest-defined reductions to base constraints.

Exports:
- ConstraintReducer: Main reduction engine
- apply_reduction: Convenience function
"""

from brain.governor.reductions.reducer import (
    ConstraintReducer,
    apply_reduction,
)

__all__ = [
    "ConstraintReducer",
    "apply_reduction",
]
