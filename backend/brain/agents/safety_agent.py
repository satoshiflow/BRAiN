"""
safety_agent.py

SafetyAgent - RYR Robot Safety Monitoring Agent

Responsibilities:
- Real-time safety monitoring and alerting
- Safety zone enforcement
- Emergency stop coordination
- Obstacle detection and collision prevention
- Human proximity detection and response
- Compliance monitoring and reporting

Integrates with:
- Foundation layer for ethics and safety validation
- Policy Engine for safety rule enforcement
- KARMA system for safety metrics tracking
- Fleet coordination for emergency responses
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from backend.brain.agents.base_agent import BaseAgent, AgentConfig, AgentResult, LLMClient


class SafetyLevel(str, Enum):
    """Safety alert levels."""
    NORMAL = "normal"
    CAUTION = "caution"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class IncidentType(str, Enum):
    """Types of safety incidents."""
    COLLISION = "collision"
    NEAR_MISS = "near_miss"
    ZONE_VIOLATION = "zone_violation"
    SPEED_VIOLATION = "speed_violation"
    HUMAN_PROXIMITY = "human_proximity"
    EMERGENCY_STOP = "emergency_stop"
    SENSOR_FAILURE = "sensor_failure"
    BATTERY_CRITICAL = "battery_critical"
    COMMUNICATION_LOSS = "communication_loss"


@dataclass
class SafetyIncident:
    """Safety incident record."""
    incident_id: str
    incident_type: IncidentType
    severity: SafetyLevel
    robot_id: str
    timestamp: datetime
    location: Optional[Dict[str, float]] = None
    description: str = ""
    resolved: bool = False
    resolution_time: Optional[datetime] = None


@dataclass
class SafetyZone:
    """Safety-restricted zone definition."""
    zone_id: str
    zone_type: str  # "restricted", "caution", "human_only", "maintenance"
    max_speed_ms: float
    allowed_robots: List[str]  # Empty = all allowed
    coordinates: Dict[str, float]  # Center point and radius


@dataclass
class RobotSafetyStatus:
    """Current safety status of a robot."""
    robot_id: str
    safety_level: SafetyLevel
    battery_percentage: float
    sensors_operational: List[str]
    sensors_failed: List[str]
    current_speed_ms: float
    distance_to_nearest_obstacle_m: float
    distance_to_nearest_human_m: Optional[float]
    emergency_stop_active: bool
    last_update: datetime


class SafetyAgent(BaseAgent):
    """
    Safety Monitoring Agent for RYR robot systems.

    Monitors and enforces:
    - Safety zone compliance
    - Speed limits
    - Obstacle avoidance
    - Human proximity protocols
    - Sensor health
    - Battery levels
    - Emergency protocols
    """

    def __init__(self, llm_client: LLMClient, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="SafetyAgent",
                role="SAFETY_MONITOR",
                model="phi3",
                system_prompt=self._get_system_prompt(),
                temperature=0.2,  # Very low temperature for safety-critical decisions
                max_tokens=2048,
                tools=[
                    "check_safety_status",
                    "trigger_emergency_stop",
                    "validate_zone_entry",
                    "report_incident",
                    "assess_risk",
                ],
                permissions=["SAFETY_MONITOR", "EMERGENCY_CONTROL", "ZONE_ENFORCE"],
            )

        super().__init__(llm_client, config)

        # Safety state
        self.robot_status: Dict[str, RobotSafetyStatus] = {}
        self.safety_zones: Dict[str, SafetyZone] = {}
        self.incidents: List[SafetyIncident] = []
        self.emergency_stops: Dict[str, datetime] = {}  # robot_id -> stop_time

        # Safety thresholds
        self.MIN_OBSTACLE_DISTANCE_M = 0.5
        self.MIN_HUMAN_DISTANCE_M = 1.5
        self.CRITICAL_BATTERY_PERCENTAGE = 15.0
        self.MAX_SPEED_DEFAULT_MS = 2.0

        # Register tools
        self.register_tool("check_safety_status", self.check_safety_status)
        self.register_tool("trigger_emergency_stop", self.trigger_emergency_stop)
        self.register_tool("validate_zone_entry", self.validate_zone_entry)
        self.register_tool("report_incident", self.report_incident)
        self.register_tool("assess_risk", self.assess_risk)

    @staticmethod
    def _get_system_prompt() -> str:
        return """You are the Safety Monitoring Agent for the BRAiN RYR system.

Your PRIMARY RESPONSIBILITY is ensuring the safety of:
1. Humans in the environment
2. The robots themselves
3. Equipment and infrastructure

Safety principles (in order of priority):
1. HUMAN SAFETY: Always prioritize human safety above all else
2. PREVENT HARM: Stop any action that could cause injury or damage
3. COMPLY WITH RULES: Enforce all safety zones and speed limits
4. MONITOR CONTINUOUSLY: Track sensor health, battery, and proximity
5. RESPOND IMMEDIATELY: Trigger emergency stops when necessary

Decision-making framework:
- If human proximity < 1.5m → IMMEDIATE WARNING, reduce speed or stop
- If obstacle distance < 0.5m → IMMEDIATE STOP
- If battery < 15% → CRITICAL ALERT, navigate to charging station
- If sensor failure → IMMEDIATE INVESTIGATION, possibly stop robot
- If safety zone violation → STOP robot, report incident
- If speed limit exceeded → SLOW DOWN immediately

Never compromise safety for efficiency or convenience.
When in doubt, err on the side of caution - stop first, analyze later.

All safety decisions must be validated through the Foundation layer."""

    # ========================================================================
    # Safety Monitoring Tools
    # ========================================================================

    def check_safety_status(self, robot_id: str) -> Tuple[SafetyLevel, List[str]]:
        """
        Check current safety status of a robot.

        Returns:
            (SafetyLevel, list of issues found)
        """
        status = self.robot_status.get(robot_id)
        if not status:
            return SafetyLevel.NORMAL, ["Robot status not available"]

        issues = []
        max_level = SafetyLevel.NORMAL

        # Check battery
        if status.battery_percentage < self.CRITICAL_BATTERY_PERCENTAGE:
            issues.append(f"Critical battery: {status.battery_percentage:.1f}%")
            max_level = SafetyLevel.CRITICAL

        # Check sensor failures
        if status.sensors_failed:
            issues.append(f"Sensor failures: {', '.join(status.sensors_failed)}")
            max_level = max(max_level, SafetyLevel.WARNING, key=lambda x: list(SafetyLevel).index(x))

        # Check obstacle proximity
        if status.distance_to_nearest_obstacle_m < self.MIN_OBSTACLE_DISTANCE_M:
            issues.append(f"Obstacle proximity: {status.distance_to_nearest_obstacle_m:.2f}m")
            max_level = SafetyLevel.CRITICAL

        # Check human proximity
        if status.distance_to_nearest_human_m is not None:
            if status.distance_to_nearest_human_m < self.MIN_HUMAN_DISTANCE_M:
                issues.append(f"Human proximity: {status.distance_to_nearest_human_m:.2f}m")
                max_level = SafetyLevel.CRITICAL

        # Check emergency stop
        if status.emergency_stop_active:
            issues.append("Emergency stop active")
            max_level = SafetyLevel.EMERGENCY

        self.logger.info(
            "Safety check for robot %s: %s (%d issues)",
            robot_id,
            max_level,
            len(issues),
        )

        return max_level, issues

    def trigger_emergency_stop(
        self,
        robot_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        """
        Trigger emergency stop for a robot.

        This is a CRITICAL operation that immediately halts all robot movement.

        Args:
            robot_id: Robot to stop
            reason: Reason for emergency stop

        Returns:
            Emergency stop confirmation
        """
        self.logger.critical(
            "🚨 EMERGENCY STOP triggered for robot %s: %s",
            robot_id,
            reason,
        )

        # Record emergency stop
        self.emergency_stops[robot_id] = datetime.utcnow()

        # Update robot status
        if robot_id in self.robot_status:
            self.robot_status[robot_id].emergency_stop_active = True

        # Report incident
        incident = self.report_incident(
            robot_id=robot_id,
            incident_type=IncidentType.EMERGENCY_STOP,
            severity=SafetyLevel.EMERGENCY,
            description=f"Emergency stop: {reason}",
        )

        # In production, would send stop command to robot hardware
        return {
            "status": "emergency_stop_activated",
            "robot_id": robot_id,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
            "incident_id": incident.incident_id,
        }

    def validate_zone_entry(
        self,
        robot_id: str,
        zone_id: str,
        current_speed_ms: float,
    ) -> Dict[str, Any]:
        """
        Validate if a robot can safely enter a safety zone.

        Checks:
        - Robot authorization for zone
        - Speed compliance
        - Current safety status

        Returns:
            Permission status and required actions
        """
        zone = self.safety_zones.get(zone_id)
        if not zone:
            return {
                "permission": True,
                "reason": "Zone not defined (no restrictions)",
            }

        # Check robot authorization
        if zone.allowed_robots and robot_id not in zone.allowed_robots:
            self.logger.warning(
                "Robot %s not authorized for zone %s",
                robot_id,
                zone_id,
            )
            return {
                "permission": False,
                "reason": f"Robot not authorized for {zone.zone_type} zone",
                "required_action": "denied",
            }

        # Check speed compliance
        if current_speed_ms > zone.max_speed_ms:
            self.logger.warning(
                "Robot %s exceeds speed limit for zone %s (%.2f > %.2f m/s)",
                robot_id,
                zone_id,
                current_speed_ms,
                zone.max_speed_ms,
            )
            return {
                "permission": False,
                "reason": f"Speed limit exceeded: {current_speed_ms:.2f} > {zone.max_speed_ms:.2f} m/s",
                "required_action": "reduce_speed",
                "required_speed_ms": zone.max_speed_ms,
            }

        # Check safety status
        safety_level, issues = self.check_safety_status(robot_id)
        if safety_level in [SafetyLevel.CRITICAL, SafetyLevel.EMERGENCY]:
            return {
                "permission": False,
                "reason": f"Robot safety status: {safety_level}",
                "safety_issues": issues,
                "required_action": "resolve_issues",
            }

        # Permission granted
        return {
            "permission": True,
            "reason": "All safety checks passed",
            "max_speed_ms": zone.max_speed_ms,
        }

    def report_incident(
        self,
        robot_id: str,
        incident_type: IncidentType,
        severity: SafetyLevel,
        description: str = "",
        location: Optional[Dict[str, float]] = None,
    ) -> SafetyIncident:
        """
        Report a safety incident.

        Incidents are logged and tracked for compliance and analysis.

        Returns:
            SafetyIncident record
        """
        incident = SafetyIncident(
            incident_id=f"INC-{len(self.incidents) + 1:05d}",
            incident_type=incident_type,
            severity=severity,
            robot_id=robot_id,
            timestamp=datetime.utcnow(),
            location=location,
            description=description,
        )

        self.incidents.append(incident)

        self.logger.warning(
            "Safety incident reported: %s | Type: %s | Severity: %s | Robot: %s",
            incident.incident_id,
            incident_type,
            severity,
            robot_id,
        )

        return incident

    def assess_risk(
        self,
        robot_id: str,
        planned_action: str,
        environment_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Assess risk of a planned action before execution.

        This is a proactive safety check that validates actions before they're taken.

        Args:
            robot_id: Robot planning the action
            planned_action: Description of planned action
            environment_data: Current environment state

        Returns:
            Risk assessment with recommendations
        """
        self.logger.info(
            "Assessing risk for robot %s action: %s",
            robot_id,
            planned_action,
        )

        risks = []
        risk_level = SafetyLevel.NORMAL

        # Check robot status
        safety_level, issues = self.check_safety_status(robot_id)
        if issues:
            risks.extend(issues)
            risk_level = max(risk_level, safety_level, key=lambda x: list(SafetyLevel).index(x))

        # Check environment data
        if "humans_detected" in environment_data and environment_data["humans_detected"]:
            risks.append("Humans present in environment")
            risk_level = max(risk_level, SafetyLevel.CAUTION, key=lambda x: list(SafetyLevel).index(x))

        if "obstacles_nearby" in environment_data and environment_data["obstacles_nearby"]:
            risks.append("Obstacles detected nearby")
            risk_level = max(risk_level, SafetyLevel.CAUTION, key=lambda x: list(SafetyLevel).index(x))

        # Determine recommendation
        if risk_level == SafetyLevel.EMERGENCY or risk_level == SafetyLevel.CRITICAL:
            recommendation = "ABORT - Critical safety risk"
        elif risk_level == SafetyLevel.WARNING:
            recommendation = "PROCEED WITH CAUTION - Monitor closely"
        elif risk_level == SafetyLevel.CAUTION:
            recommendation = "PROCEED - Reduce speed and increase monitoring"
        else:
            recommendation = "PROCEED - Normal operation"

        return {
            "risk_level": risk_level,
            "risks_identified": risks,
            "recommendation": recommendation,
            "safe_to_proceed": risk_level not in [SafetyLevel.CRITICAL, SafetyLevel.EMERGENCY],
        }

    # ========================================================================
    # Agent Interface
    # ========================================================================

    async def run(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """
        Execute safety monitoring task.

        Examples:
        - "Check safety status of robot ROBOT-001"
        - "Validate if robot ROBOT-002 can enter zone WAREHOUSE-A"
        - "Assess risk of movement command for robot ROBOT-003"
        - "Trigger emergency stop for robot ROBOT-004 due to human proximity"

        The LLM will analyze the task and select appropriate safety tools.
        """
        self.logger.info("SafetyAgent executing task: %s", task)

        try:
            # Add context about safety tools and current state
            tools_context = f"""
Available safety tools:
- check_safety_status(robot_id)
- trigger_emergency_stop(robot_id, reason)
- validate_zone_entry(robot_id, zone_id, current_speed_ms)
- report_incident(robot_id, incident_type, severity, description)
- assess_risk(robot_id, planned_action, environment_data)

Active safety zones: {list(self.safety_zones.keys())}
Robots under monitoring: {list(self.robot_status.keys())}
Recent incidents: {len([i for i in self.incidents if not i.resolved])} unresolved

Context: {context or 'None'}

REMEMBER: Safety is the top priority. When in doubt, stop the robot and investigate.
"""

            # Call LLM with safety context
            llm_response = await self.call_llm(
                user_message=task,
                extra_messages=[{"role": "system", "content": tools_context}],
            )

            # In production, would parse LLM response and execute safety tools
            return {
                "id": f"safety_task_{id(task)}",
                "success": True,
                "message": llm_response,
                "raw_response": llm_response,
                "used_tools": [],
                "meta": {
                    "agent_name": "SafetyAgent",
                    "task": task,
                },
            }

        except Exception as e:
            self.logger.exception("SafetyAgent task failed: %s", e)
            return {
                "id": f"safety_task_{id(task)}",
                "success": False,
                "message": "Safety monitoring task failed",
                "error": str(e),
                "used_tools": [],
                "meta": {
                    "agent_name": "SafetyAgent",
                    "task": task,
                },
            }

    # ========================================================================
    # Safety Zone Management
    # ========================================================================

    def define_safety_zone(
        self,
        zone_id: str,
        zone_type: str,
        max_speed_ms: float,
        allowed_robots: Optional[List[str]] = None,
        coordinates: Optional[Dict[str, float]] = None,
    ) -> SafetyZone:
        """
        Define a new safety zone.

        Args:
            zone_id: Unique zone identifier
            zone_type: Type of zone (restricted, caution, human_only, maintenance)
            max_speed_ms: Maximum allowed speed in m/s
            allowed_robots: List of authorized robot IDs (empty = all allowed)
            coordinates: Zone center and radius

        Returns:
            SafetyZone definition
        """
        zone = SafetyZone(
            zone_id=zone_id,
            zone_type=zone_type,
            max_speed_ms=max_speed_ms,
            allowed_robots=allowed_robots or [],
            coordinates=coordinates or {},
        )

        self.safety_zones[zone_id] = zone
        self.logger.info(
            "Safety zone defined: %s (type: %s, max_speed: %.2f m/s)",
            zone_id,
            zone_type,
            max_speed_ms,
        )

        return zone
