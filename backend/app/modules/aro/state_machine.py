"""
ARO State Machine - Deterministic State Control

Manages state transitions for repository operations with strict rules.

Principles:
- Only defined transitions are allowed
- Every transition is logged to audit trail
- Invalid transitions raise exceptions (fail-closed)
- State machine is deterministic and predictable
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Set, Tuple, Optional
from loguru import logger

from .schemas import OperationState, RepoOperation


# ============================================================================
# State Transition Graph
# ============================================================================

# Define all allowed state transitions
# Format: {from_state: {to_state1, to_state2, ...}}
ALLOWED_TRANSITIONS: Dict[OperationState, Set[OperationState]] = {
    # From PROPOSED
    OperationState.PROPOSED: {
        OperationState.VALIDATING,
        OperationState.CANCELLED,  # Can cancel before validation
    },

    # From VALIDATING
    OperationState.VALIDATING: {
        OperationState.PENDING_AUTH,  # Validation passed
        OperationState.DENIED,        # Validation failed
        OperationState.CANCELLED,     # Cancelled during validation
    },

    # From PENDING_AUTH
    OperationState.PENDING_AUTH: {
        OperationState.AUTHORIZED,    # Authorization granted
        OperationState.DENIED,        # Authorization denied
        OperationState.CANCELLED,     # Cancelled before auth
    },

    # From AUTHORIZED
    OperationState.AUTHORIZED: {
        OperationState.EXECUTING,     # Start execution
        OperationState.CANCELLED,     # Cancel before execution
    },

    # From EXECUTING
    OperationState.EXECUTING: {
        OperationState.COMPLETED,     # Execution succeeded
        OperationState.FAILED,        # Execution failed
    },

    # From FAILED
    OperationState.FAILED: {
        OperationState.ROLLED_BACK,   # Rollback after failure
        # Terminal state - no other transitions
    },

    # From DENIED
    OperationState.DENIED: {
        # Terminal state - no transitions allowed
    },

    # From COMPLETED
    OperationState.COMPLETED: {
        # Terminal state - no transitions allowed
    },

    # From ROLLED_BACK
    OperationState.ROLLED_BACK: {
        # Terminal state - no transitions allowed
    },

    # From CANCELLED
    OperationState.CANCELLED: {
        # Terminal state - no transitions allowed
    },
}


# Terminal states (no outgoing transitions)
TERMINAL_STATES: Set[OperationState] = {
    OperationState.COMPLETED,
    OperationState.FAILED,
    OperationState.DENIED,
    OperationState.ROLLED_BACK,
    OperationState.CANCELLED,
}


class StateTransitionError(Exception):
    """
    Raised when an invalid state transition is attempted.

    This is a critical error - state machine integrity is violated.
    """
    pass


class StateMachine:
    """
    Deterministic state machine for repository operations.

    Enforces strict state transition rules.
    """

    def __init__(self):
        """Initialize state machine"""
        self.transition_count = 0
        logger.info("🔄 ARO State Machine initialized")

    def validate_transition(
        self,
        from_state: OperationState,
        to_state: OperationState
    ) -> bool:
        """
        Validate if a state transition is allowed.

        Args:
            from_state: Current state
            to_state: Desired state

        Returns:
            True if transition is allowed, False otherwise

        Raises:
            StateTransitionError: If transition is invalid (fail-closed)
        """
        # Check if transition is defined
        allowed = ALLOWED_TRANSITIONS.get(from_state, set())

        if to_state not in allowed:
            error_msg = (
                f"Invalid state transition: {from_state.value} → {to_state.value}. "
                f"Allowed transitions from {from_state.value}: "
                f"{[s.value for s in allowed]}"
            )
            logger.error(f"❌ {error_msg}")
            raise StateTransitionError(error_msg)

        logger.debug(
            f"✅ Valid transition: {from_state.value} → {to_state.value}"
        )
        return True

    def transition(
        self,
        operation: RepoOperation,
        to_state: OperationState,
        reason: str = ""
    ) -> RepoOperation:
        """
        Perform a state transition.

        Args:
            operation: Operation to transition
            to_state: Target state
            reason: Reason for transition (for audit)

        Returns:
            Updated operation

        Raises:
            StateTransitionError: If transition is invalid
        """
        from_state = operation.current_state

        # Validate transition
        self.validate_transition(from_state, to_state)

        # Update operation state
        operation.state_history.append(from_state)
        operation.current_state = to_state
        operation.updated_at = datetime.utcnow()

        # Track transition count
        self.transition_count += 1

        logger.info(
            f"🔄 State transition: {from_state.value} → {to_state.value} "
            f"(operation={operation.operation_id}, reason={reason or 'none'})"
        )

        return operation

    def can_transition(
        self,
        from_state: OperationState,
        to_state: OperationState
    ) -> bool:
        """
        Check if a transition is allowed without raising an exception.

        Args:
            from_state: Current state
            to_state: Desired state

        Returns:
            True if transition is allowed, False otherwise
        """
        allowed = ALLOWED_TRANSITIONS.get(from_state, set())
        return to_state in allowed

    def get_allowed_transitions(
        self,
        from_state: OperationState
    ) -> Set[OperationState]:
        """
        Get all allowed transitions from a given state.

        Args:
            from_state: State to query

        Returns:
            Set of allowed target states
        """
        return ALLOWED_TRANSITIONS.get(from_state, set())

    def is_terminal_state(self, state: OperationState) -> bool:
        """
        Check if a state is terminal (no outgoing transitions).

        Args:
            state: State to check

        Returns:
            True if state is terminal
        """
        return state in TERMINAL_STATES

    def get_state_path(
        self,
        from_state: OperationState,
        to_state: OperationState
    ) -> Optional[list[OperationState]]:
        """
        Find a valid path between two states (BFS).

        Args:
            from_state: Starting state
            to_state: Target state

        Returns:
            List of states representing the path, or None if no path exists
        """
        # BFS to find shortest path
        queue = [(from_state, [from_state])]
        visited = {from_state}

        while queue:
            current, path = queue.pop(0)

            if current == to_state:
                return path

            # Explore neighbors
            for next_state in ALLOWED_TRANSITIONS.get(current, set()):
                if next_state not in visited:
                    visited.add(next_state)
                    queue.append((next_state, path + [next_state]))

        # No path found
        return None

    def get_transition_statistics(self) -> Dict[str, int]:
        """
        Get statistics about state transitions.

        Returns:
            Dictionary with transition counts
        """
        return {
            "total_transitions": self.transition_count,
            "total_states": len(OperationState),
            "total_defined_transitions": sum(
                len(v) for v in ALLOWED_TRANSITIONS.values()
            ),
            "terminal_states": len(TERMINAL_STATES),
        }

    def validate_state_machine_integrity(self) -> Tuple[bool, list[str]]:
        """
        Validate the state machine definition for consistency.

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Check 1: All states have an entry in ALLOWED_TRANSITIONS
        for state in OperationState:
            if state not in ALLOWED_TRANSITIONS:
                issues.append(f"State {state.value} not in ALLOWED_TRANSITIONS")

        # Check 2: Terminal states should have no outgoing transitions
        for state in TERMINAL_STATES:
            if ALLOWED_TRANSITIONS.get(state, set()):
                issues.append(
                    f"Terminal state {state.value} has outgoing transitions"
                )

        # Check 3: All transitions point to valid states
        for from_state, to_states in ALLOWED_TRANSITIONS.items():
            for to_state in to_states:
                if to_state not in OperationState:
                    issues.append(
                        f"Invalid transition: {from_state.value} → {to_state}"
                    )

        # Check 4: PROPOSED should be reachable from all non-terminal states
        # (Actually, operations always start at PROPOSED, so this is N/A)

        is_valid = len(issues) == 0

        if is_valid:
            logger.info("✅ State machine integrity check passed")
        else:
            logger.error(f"❌ State machine integrity check failed: {issues}")

        return is_valid, issues


# ============================================================================
# Singleton Instance
# ============================================================================

_state_machine: Optional[StateMachine] = None


def get_state_machine() -> StateMachine:
    """Get the singleton state machine instance"""
    global _state_machine
    if _state_machine is None:
        _state_machine = StateMachine()

        # Validate integrity on first use
        is_valid, issues = _state_machine.validate_state_machine_integrity()
        if not is_valid:
            raise RuntimeError(
                f"State machine integrity check failed: {issues}"
            )

    return _state_machine
