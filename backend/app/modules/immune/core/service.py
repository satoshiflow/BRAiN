from datetime import datetime, timedelta
from typing import List

from app.modules.immune.schemas import ImmuneEvent, ImmuneHealthSummary, ImmuneSeverity


class ImmuneService:
    """
    In-Memory Immunsystem.
    Hält Events im Speicher und generiert eine Health-Übersicht.
    """

    def __init__(self) -> None:
        self._events: List[ImmuneEvent] = []
        self._id_counter: int = 1

    def publish_event(self, event: ImmuneEvent) -> int:
        now = datetime.utcnow()
        stored = ImmuneEvent(
            **event.dict(exclude={"id", "created_at"}),
            id=self._id_counter,
            created_at=now,
        )
        self._id_counter += 1
        self._events.append(stored)
        return stored.id

    def get_recent_events(self, minutes: int = 60) -> List[ImmuneEvent]:
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=minutes)
        return [e for e in self._events if e.created_at >= cutoff]

    def health_summary(self, minutes: int = 60) -> ImmuneHealthSummary:
        events = self.get_recent_events(minutes=minutes)
        active_issues = len(events)
        critical_issues = sum(1 for e in events if e.severity == ImmuneSeverity.CRITICAL)
        # letzte 10
        last_events = events[-10:]
        return ImmuneHealthSummary(
            active_issues=active_issues,
            critical_issues=critical_issues,
            last_events=last_events,
        )
