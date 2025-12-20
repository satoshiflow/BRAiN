"""
Robot Simulator - Auto-generates health metrics, navigation data, etc.
"""

import asyncio
import time
import random
from typing import Dict, List

# ========== Mock Robot Class ==========

class MockRobot:
    """Simulated robot with health degradation"""

    def __init__(self, robot_id: str):
        self.robot_id = robot_id
        self.health_base = random.uniform(85, 95)
        self.operating_hours = random.uniform(100, 1000)
        self.cycle_count = int(self.operating_hours * 100)
        self.degradation_rate = random.uniform(0.01, 0.05)  # Health decrease per update
        self.position = {"x": random.uniform(0, 20), "y": random.uniform(0, 20)}
        self.velocity = 0.0

    def get_health_metrics(self):
        """Generate current health metrics"""
        # Degrade health over time
        self.health_base -= self.degradation_rate
        self.health_base = max(self.health_base, 20.0)  # Minimum health
        self.operating_hours += 0.1
        self.cycle_count += 10

        # Components for this robot
        components = {
            "motor_fl": {"type": "motor", "health": self.health_base + random.uniform(-5, 5)},
            "motor_fr": {"type": "motor", "health": self.health_base + random.uniform(-5, 5)},
            "battery": {"type": "battery", "health": self.health_base + random.uniform(-10, 0)},
            "sensor_lidar": {"type": "sensor", "health": self.health_base + random.uniform(-3, 3)},
        }

        metrics = []
        for comp_id, data in components.items():
            health_score = max(min(data["health"], 100.0), 0.0)

            # Anomaly triggers
            temp = random.uniform(45, 85)
            if health_score < 60:
                temp += random.uniform(10, 20)  # Overheating if unhealthy

            vibration = random.uniform(1, 5)
            if health_score < 70:
                vibration += random.uniform(3, 7)  # High vibration if degraded

            metrics.append({
                "component_id": f"{comp_id}_{self.robot_id}",
                "component_type": data["type"],
                "robot_id": self.robot_id,
                "timestamp": time.time(),
                "health_score": health_score,
                "temperature_c": temp,
                "vibration_level": vibration,
                "power_consumption_w": random.uniform(80, 150),
                "operating_hours": self.operating_hours,
                "cycle_count": self.cycle_count,
                "error_rate": max(0.0, (100 - health_score) / 100 * 0.1),
            })

        return metrics


# ========== Simulator Service ==========

class RobotSimulator:
    """Manages multiple simulated robots"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.robots: Dict[str, MockRobot] = {}
        self.running = False
        self.task = None

        # Create 5 robots
        for i in range(1, 6):
            robot_id = f"robot_{i:02d}"
            self.robots[robot_id] = MockRobot(robot_id)

        self._initialized = True

    async def start(self):
        """Start simulator loop"""
        if self.running:
            return

        self.running = True
        self.task = asyncio.create_task(self._run_loop())

    async def stop(self):
        """Stop simulator"""
        self.running = False
        if self.task:
            await self.task

    async def _run_loop(self):
        """Main simulation loop - updates health metrics every 5 seconds"""
        from backend.app.modules.maintenance.service import get_maintenance_service

        while self.running:
            try:
                # Update all robots
                maintenance_service = get_maintenance_service()

                for robot in self.robots.values():
                    metrics_list = robot.get_health_metrics()

                    for metrics in metrics_list:
                        # Record metrics (triggers anomaly detection)
                        maintenance_service.record_health_metrics(metrics)

                        # Predict failures for components with low health
                        if metrics["health_score"] < 75:
                            maintenance_service.predict_failure(metrics["component_id"])

            except Exception as e:
                print(f"Simulator error: {e}")

            await asyncio.sleep(5)  # Update every 5 seconds

    def get_robot_status(self, robot_id: str) -> dict:
        """Get current robot status"""
        robot = self.robots.get(robot_id)
        if not robot:
            return {}

        return {
            "robot_id": robot_id,
            "health_base": robot.health_base,
            "operating_hours": robot.operating_hours,
            "position": robot.position,
            "velocity": robot.velocity,
        }


# Singleton instance
def get_simulator() -> RobotSimulator:
    """Get simulator instance"""
    return RobotSimulator()
