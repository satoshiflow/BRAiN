"""Synergie-Mechanik - Cooperation rewards and work reuse detection.

Implements Myzel-Hybrid-Charta principles:
- Reuse detection and credit refunds
- Deduplication before mission execution
- Collaboration rewards (not competition)
- Resource efficiency through cooperation
"""

import logging
import hashlib
from typing import List, Dict, Optional, Set
from datetime import datetime, timezone
from dataclasses import dataclass
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class MissionSignature:
    """Mission signature for deduplication."""

    mission_id: str
    signature_hash: str
    description: str
    requirements: Dict
    created_at: datetime
    status: str  # "pending", "in_progress", "completed", "cancelled"
    result: Optional[Dict] = None


@dataclass
class ReuseDetection:
    """Detected reuse of previous work."""

    original_mission_id: str
    new_mission_id: str
    similarity_score: float  # 0.0-1.0
    reusable_percentage: float  # 0.0-1.0
    refund_amount: float
    reasoning: str


@dataclass
class CollaborationEvent:
    """Collaboration event between agents."""

    event_id: str
    primary_agent_id: str
    collaborating_agent_id: str
    mission_id: str
    collaboration_type: str  # "knowledge_share", "resource_share", "joint_execution"
    value_added: float  # 0.0-1.0
    timestamp: datetime


class SynergieMechanik:
    """Cooperation-based resource optimization.

    Features:
    - Mission deduplication (prevent redundant work)
    - Work reuse detection (refund credits for reused results)
    - Collaboration tracking (reward cooperation)
    - Resource sharing incentives

    Myzel-Hybrid Principles:
    - Cooperation over competition
    - Resource efficiency through reuse
    - Fair credit distribution
    """

    # Similarity thresholds
    HIGH_SIMILARITY_THRESHOLD = 0.90  # 90% similar → likely duplicate
    REUSE_SIMILARITY_THRESHOLD = 0.70  # 70% similar → reusable work
    PARTIAL_REUSE_THRESHOLD = 0.50    # 50% similar → partial reuse

    def __init__(self):
        self.mission_signatures: Dict[str, MissionSignature] = {}
        self.reuse_detections: List[ReuseDetection] = []
        self.collaboration_events: List[CollaborationEvent] = []
        self.event_counter = 0

        logger.info("[SynergieMechanik] Initialized")

    def register_mission(
        self,
        mission_id: str,
        description: str,
        requirements: Dict,
    ) -> MissionSignature:
        """Register mission for deduplication tracking.

        Args:
            mission_id: Mission identifier
            description: Mission description
            requirements: Mission requirements

        Returns:
            Mission signature
        """
        # Create signature hash (based on description + requirements)
        signature_data = f"{description}|{sorted(requirements.items())}"
        signature_hash = hashlib.sha256(signature_data.encode()).hexdigest()

        signature = MissionSignature(
            mission_id=mission_id,
            signature_hash=signature_hash,
            description=description,
            requirements=requirements,
            created_at=datetime.now(timezone.utc),
            status="pending",
        )

        self.mission_signatures[mission_id] = signature

        logger.debug(f"[SynergieMechanik] Registered mission {mission_id} with hash {signature_hash[:8]}...")

        return signature

    def check_for_duplicates(
        self,
        mission_id: str,
    ) -> List[Dict]:
        """Check if mission is duplicate of existing work.

        Args:
            mission_id: Mission identifier

        Returns:
            List of potential duplicates with similarity scores
        """
        if mission_id not in self.mission_signatures:
            logger.warning(f"[SynergieMechanik] Mission {mission_id} not registered")
            return []

        current_signature = self.mission_signatures[mission_id]
        duplicates = []

        # Check against all other missions
        for other_id, other_signature in self.mission_signatures.items():
            if other_id == mission_id:
                continue

            # Skip failed/cancelled missions
            if other_signature.status in ["failed", "cancelled"]:
                continue

            # Calculate similarity
            similarity = self._calculate_similarity(
                current_signature.description,
                other_signature.description,
            )

            if similarity >= self.REUSE_SIMILARITY_THRESHOLD:
                duplicates.append({
                    "mission_id": other_id,
                    "similarity": similarity,
                    "status": other_signature.status,
                    "is_high_similarity": similarity >= self.HIGH_SIMILARITY_THRESHOLD,
                    "has_result": other_signature.result is not None,
                })

        # Sort by similarity (descending)
        duplicates.sort(key=lambda d: d["similarity"], reverse=True)

        if duplicates:
            logger.info(
                f"[SynergieMechanik] Found {len(duplicates)} potential duplicates for mission {mission_id} "
                f"(highest similarity: {duplicates[0]['similarity']:.2%})"
            )

        return duplicates

    def detect_reuse_opportunity(
        self,
        mission_id: str,
        original_mission_id: str,
    ) -> Optional[ReuseDetection]:
        """Detect if new mission can reuse previous work.

        Args:
            mission_id: New mission identifier
            original_mission_id: Original mission identifier

        Returns:
            ReuseDetection or None if not reusable
        """
        if mission_id not in self.mission_signatures:
            logger.warning(f"[SynergieMechanik] Mission {mission_id} not registered")
            return None

        if original_mission_id not in self.mission_signatures:
            logger.warning(f"[SynergieMechanik] Original mission {original_mission_id} not found")
            return None

        current = self.mission_signatures[mission_id]
        original = self.mission_signatures[original_mission_id]

        # Check if original mission is completed
        if original.status != "completed" or original.result is None:
            logger.debug(
                f"[SynergieMechanik] Original mission {original_mission_id} "
                f"not completed or has no result"
            )
            return None

        # Calculate similarity
        similarity = self._calculate_similarity(
            current.description,
            original.description,
        )

        if similarity < self.REUSE_SIMILARITY_THRESHOLD:
            return None

        # Determine reusable percentage (based on similarity)
        if similarity >= self.HIGH_SIMILARITY_THRESHOLD:
            reusable_percentage = 0.95  # 95% reusable
            reasoning = f"High similarity ({similarity:.2%}) - almost complete reuse possible"
        elif similarity >= self.REUSE_SIMILARITY_THRESHOLD:
            reusable_percentage = similarity * 0.8  # 70-80% reusable
            reasoning = f"Moderate similarity ({similarity:.2%}) - partial reuse possible"
        else:
            reusable_percentage = similarity * 0.5  # 35-50% reusable
            reasoning = f"Low similarity ({similarity:.2%}) - minimal reuse possible"

        # Calculate refund amount (would be determined by credit system)
        # Placeholder: assume original mission had 50 credits allocated
        original_allocation = 50.0  # TODO: Get from credit ledger
        refund_amount = original_allocation * reusable_percentage

        detection = ReuseDetection(
            original_mission_id=original_mission_id,
            new_mission_id=mission_id,
            similarity_score=similarity,
            reusable_percentage=reusable_percentage,
            refund_amount=refund_amount,
            reasoning=reasoning,
        )

        self.reuse_detections.append(detection)

        logger.info(
            f"[SynergieMechanik] Reuse opportunity detected: "
            f"{mission_id} can reuse {reusable_percentage:.1%} of {original_mission_id} "
            f"(refund: {refund_amount:.2f} credits)"
        )

        return detection

    def record_collaboration(
        self,
        primary_agent_id: str,
        collaborating_agent_id: str,
        mission_id: str,
        collaboration_type: str,
        value_added: float,
    ) -> CollaborationEvent:
        """Record collaboration event.

        Myzel-Hybrid: Track cooperation for credit bonuses.

        Args:
            primary_agent_id: Primary agent
            collaborating_agent_id: Collaborating agent
            mission_id: Mission identifier
            collaboration_type: Type of collaboration
            value_added: Value added by collaboration (0.0-1.0)

        Returns:
            CollaborationEvent
        """
        self.event_counter += 1
        event_id = f"COLLAB_{self.event_counter:06d}"

        event = CollaborationEvent(
            event_id=event_id,
            primary_agent_id=primary_agent_id,
            collaborating_agent_id=collaborating_agent_id,
            mission_id=mission_id,
            collaboration_type=collaboration_type,
            value_added=value_added,
            timestamp=datetime.now(timezone.utc),
        )

        self.collaboration_events.append(event)

        logger.info(
            f"[SynergieMechanik] Collaboration recorded: {primary_agent_id} + {collaborating_agent_id} "
            f"on {mission_id} ({collaboration_type}, value: {value_added:.2f})"
        )

        return event

    def calculate_collaboration_bonus(
        self,
        agent_id: str,
        time_window_hours: float = 24.0,
    ) -> float:
        """Calculate collaboration bonus for agent.

        Myzel-Hybrid: Reward cooperation.

        Args:
            agent_id: Agent identifier
            time_window_hours: Time window for bonus calculation

        Returns:
            Bonus credits
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)

        # Get recent collaboration events
        recent_events = [
            event for event in self.collaboration_events
            if event.timestamp >= cutoff_time and (
                event.primary_agent_id == agent_id or
                event.collaborating_agent_id == agent_id
            )
        ]

        if not recent_events:
            return 0.0

        # Calculate bonus based on number and quality of collaborations
        collaboration_count = len(recent_events)
        avg_value_added = sum(e.value_added for e in recent_events) / collaboration_count

        # Bonus formula: base (2 credits/collaboration) * quality multiplier
        base_bonus_per_collaboration = 2.0
        quality_multiplier = 0.5 + (avg_value_added * 0.5)  # 0.5 - 1.0

        bonus = collaboration_count * base_bonus_per_collaboration * quality_multiplier

        logger.info(
            f"[SynergieMechanik] Collaboration bonus for {agent_id}: "
            f"{bonus:.2f} credits ({collaboration_count} events, "
            f"avg value: {avg_value_added:.2f})"
        )

        return bonus

    def get_reuse_statistics(self) -> Dict:
        """Get reuse statistics.

        Returns:
            Statistics dictionary
        """
        total_detections = len(self.reuse_detections)

        if total_detections == 0:
            return {
                "total_reuse_detections": 0,
                "total_refund_amount": 0.0,
                "average_similarity": 0.0,
                "average_reuse_percentage": 0.0,
            }

        total_refund = sum(d.refund_amount for d in self.reuse_detections)
        avg_similarity = sum(d.similarity_score for d in self.reuse_detections) / total_detections
        avg_reuse = sum(d.reusable_percentage for d in self.reuse_detections) / total_detections

        return {
            "total_reuse_detections": total_detections,
            "total_refund_amount": total_refund,
            "average_similarity": avg_similarity,
            "average_reuse_percentage": avg_reuse,
        }

    def get_collaboration_statistics(self) -> Dict:
        """Get collaboration statistics.

        Returns:
            Statistics dictionary
        """
        total_events = len(self.collaboration_events)

        if total_events == 0:
            return {
                "total_collaboration_events": 0,
                "unique_agents": 0,
                "average_value_added": 0.0,
            }

        unique_agents: Set[str] = set()
        for event in self.collaboration_events:
            unique_agents.add(event.primary_agent_id)
            unique_agents.add(event.collaborating_agent_id)

        avg_value = sum(e.value_added for e in self.collaboration_events) / total_events

        return {
            "total_collaboration_events": total_events,
            "unique_agents": len(unique_agents),
            "average_value_added": avg_value,
        }

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0.0-1.0)
        """
        # Use SequenceMatcher for simple similarity
        matcher = SequenceMatcher(None, text1.lower(), text2.lower())
        return matcher.ratio()


# Global Synergie-Mechanik instance
_synergie_mechanik: Optional[SynergieMechanik] = None


def get_synergie_mechanik() -> SynergieMechanik:
    """Get global Synergie-Mechanik instance.

    Returns:
        SynergieMechanik instance
    """
    global _synergie_mechanik
    if _synergie_mechanik is None:
        _synergie_mechanik = SynergieMechanik()
    return _synergie_mechanik


# Import for datetime
from datetime import timedelta
