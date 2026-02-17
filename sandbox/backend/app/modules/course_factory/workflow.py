"""
Course Workflow State Machine - Sprint 13

Manages course lifecycle: draft → review → publish_ready
"""

from typing import Optional, List, Dict, Any
from loguru import logger

from app.modules.course_factory.enhanced_schemas import (
    WorkflowState,
    WorkflowTransition,
    EnhancedCourseMetadata,
)


class WorkflowError(Exception):
    """Raised when workflow transition fails."""
    pass


class WorkflowStateMachine:
    """
    Course workflow state machine.

    States: draft → review → publish_ready → published → archived
    Gates: review (HITL optional), publish_ready (validation required)
    """

    # Allowed transitions
    TRANSITIONS = {
        WorkflowState.DRAFT: [WorkflowState.REVIEW, WorkflowState.ARCHIVED],
        WorkflowState.REVIEW: [WorkflowState.DRAFT, WorkflowState.PUBLISH_READY, WorkflowState.ARCHIVED],
        WorkflowState.PUBLISH_READY: [WorkflowState.REVIEW, WorkflowState.PUBLISHED, WorkflowState.ARCHIVED],
        WorkflowState.PUBLISHED: [WorkflowState.ARCHIVED],
        WorkflowState.ARCHIVED: [],  # Terminal state
    }

    # States requiring approval
    APPROVAL_REQUIRED = {
        (WorkflowState.REVIEW, WorkflowState.PUBLISH_READY): True,  # Optional HITL gate
    }

    def validate_transition(
        self,
        from_state: WorkflowState,
        to_state: WorkflowState,
    ) -> tuple[bool, Optional[str]]:
        """
        Validate if transition is allowed.

        Args:
            from_state: Current state
            to_state: Target state

        Returns:
            Tuple of (valid, error_message)
        """
        if from_state not in self.TRANSITIONS:
            return False, f"Unknown state: {from_state}"

        allowed_transitions = self.TRANSITIONS[from_state]
        if to_state not in allowed_transitions:
            return False, f"Invalid transition: {from_state} → {to_state}. Allowed: {allowed_transitions}"

        return True, None

    def requires_approval(
        self,
        from_state: WorkflowState,
        to_state: WorkflowState,
    ) -> bool:
        """
        Check if transition requires HITL approval.

        Args:
            from_state: Current state
            to_state: Target state

        Returns:
            True if approval required
        """
        return self.APPROVAL_REQUIRED.get((from_state, to_state), False)

    def transition(
        self,
        metadata: EnhancedCourseMetadata,
        to_state: WorkflowState,
        transitioned_by: str,
        approval_token: Optional[str] = None,
    ) -> WorkflowTransition:
        """
        Perform workflow state transition.

        Args:
            metadata: Course metadata (will be modified in-place)
            to_state: Target state
            transitioned_by: User/system triggering transition
            approval_token: Optional approval token (for gates)

        Returns:
            WorkflowTransition record

        Raises:
            WorkflowError: If transition is invalid or approval missing
        """
        from_state = metadata.workflow_state

        # Validate transition
        valid, error_msg = self.validate_transition(from_state, to_state)
        if not valid:
            raise WorkflowError(error_msg)

        # Check approval requirement
        requires_approval = self.requires_approval(from_state, to_state)
        if requires_approval and not approval_token:
            raise WorkflowError(
                f"Transition {from_state} → {to_state} requires approval, "
                f"but no approval_token provided"
            )

        # TODO: Validate approval token if provided (Sprint 13+)
        # For MVP, we just log it
        if approval_token:
            logger.info(
                f"[Workflow] Approval token provided for {from_state} → {to_state}: "
                f"{approval_token[:16]}..."
            )

        # Create transition record
        transition = WorkflowTransition(
            course_id=metadata.course_id,
            from_state=from_state,
            to_state=to_state,
            requires_approval=requires_approval,
            approval_token=approval_token if requires_approval else None,
            approved_by=transitioned_by if requires_approval else None,
            transitioned_by=transitioned_by,
            validation_passed=True,
            can_rollback=(to_state != WorkflowState.PUBLISHED),  # Can't rollback from published
            rollback_state=from_state if to_state != WorkflowState.ARCHIVED else None,
        )

        # Update metadata
        metadata.workflow_state = to_state
        metadata.workflow_history.append(transition)

        logger.info(
            f"[Workflow] Transition completed: {from_state} → {to_state} "
            f"(course_id={metadata.course_id}, by={transitioned_by})"
        )

        return transition

    def rollback_transition(
        self,
        metadata: EnhancedCourseMetadata,
        transitioned_by: str,
    ) -> WorkflowTransition:
        """
        Rollback to previous workflow state.

        Args:
            metadata: Course metadata
            transitioned_by: User triggering rollback

        Returns:
            WorkflowTransition record

        Raises:
            WorkflowError: If rollback not possible
        """
        if not metadata.workflow_history:
            raise WorkflowError("No workflow history, cannot rollback")

        last_transition = metadata.workflow_history[-1]

        if not last_transition.can_rollback:
            raise WorkflowError(
                f"Cannot rollback from {metadata.workflow_state} "
                f"(transition {last_transition.transition_id} is not rollbackable)"
            )

        if last_transition.rollback_state is None:
            raise WorkflowError("Last transition has no rollback_state")

        # Perform rollback
        rollback_target = last_transition.rollback_state
        logger.warning(
            f"[Workflow] Rolling back: {metadata.workflow_state} → {rollback_target} "
            f"(course_id={metadata.course_id})"
        )

        return self.transition(
            metadata=metadata,
            to_state=rollback_target,
            transitioned_by=transitioned_by,
        )


# Singleton
_workflow_machine: Optional[WorkflowStateMachine] = None


def get_workflow_machine() -> WorkflowStateMachine:
    """Get workflow state machine singleton."""
    global _workflow_machine
    if _workflow_machine is None:
        _workflow_machine = WorkflowStateMachine()
    return _workflow_machine
