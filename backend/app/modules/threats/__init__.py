"""Threats Module - Threat detection and analysis.

Implements:
- Threat detection and tracking
- Security event monitoring
- Threat analysis and response
"""

from .service import (
    add_threat,
    get_threat,
    get_all_threats,
    resolve_threat,
    get_threat_stats,
)
from .models import Threat, ThreatSeverity, ThreatStatus

__all__ = [
    "add_threat",
    "get_threat",
    "get_all_threats",
    "resolve_threat",
    "get_threat_stats",
    "Threat",
    "ThreatSeverity",
    "ThreatStatus",
]
