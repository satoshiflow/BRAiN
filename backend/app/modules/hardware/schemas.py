"""Hardware module schemas."""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class RobotModel(str, Enum):
    UNITREE_GO1 = "unitree_go1"
    UNITREE_GO2 = "unitree_go2"
    UNITREE_B2 = "unitree_b2"

class MotorState(BaseModel):
    motor_id: int
    angle: float
    velocity: float
    torque: float
    temperature: float

class RobotHardwareState(BaseModel):
    robot_id: str
    model: RobotModel
    battery_voltage: float
    battery_percentage: float
    motor_states: List[MotorState]
    imu_data: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class MovementCommand(BaseModel):
    linear_x: float = Field(ge=-1.0, le=1.0)
    linear_y: float = Field(ge=-1.0, le=1.0)
    angular_z: float = Field(ge=-2.0, le=2.0)
