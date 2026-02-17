"""
ROS2 Bridge Schemas

Pydantic models for ROS2 communication and integration.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field


# ============================================================================
# ROS2 MESSAGE TYPES
# ============================================================================

class ROS2MessageType(str, Enum):
    """Standard ROS2 message types."""
    # Geometry messages
    POSE = "geometry_msgs/Pose"
    TWIST = "geometry_msgs/Twist"
    POINT = "geometry_msgs/Point"
    QUATERNION = "geometry_msgs/Quaternion"

    # Sensor messages
    IMAGE = "sensor_msgs/Image"
    LASER_SCAN = "sensor_msgs/LaserScan"
    POINT_CLOUD2 = "sensor_msgs/PointCloud2"
    IMU = "sensor_msgs/Imu"
    BATTERY_STATE = "sensor_msgs/BatteryState"

    # Navigation messages
    ODOMETRY = "nav_msgs/Odometry"
    PATH = "nav_msgs/Path"
    OCCUPANCY_GRID = "nav_msgs/OccupancyGrid"

    # Standard messages
    STRING = "std_msgs/String"
    BOOL = "std_msgs/Bool"
    INT32 = "std_msgs/Int32"
    FLOAT32 = "std_msgs/Float32"

    # Custom
    CUSTOM = "custom"


class ROS2QoSProfile(str, Enum):
    """ROS2 Quality of Service profiles."""
    SYSTEM_DEFAULT = "system_default"
    SENSOR_DATA = "sensor_data"
    SERVICES_DEFAULT = "services_default"
    PARAMETERS = "parameters"
    PARAMETER_EVENTS = "parameter_events"


# ============================================================================
# TOPIC OPERATIONS
# ============================================================================

class TopicInfo(BaseModel):
    """ROS2 topic information."""
    name: str = Field(description="Topic name (e.g., /robot/pose)")
    msg_type: str = Field(description="Message type (e.g., geometry_msgs/Pose)")
    publisher_count: int = Field(ge=0, description="Number of publishers")
    subscriber_count: int = Field(ge=0, description="Number of subscribers")


class TopicSubscribeRequest(BaseModel):
    """Request to subscribe to a ROS2 topic."""
    topic_name: str = Field(description="Topic to subscribe to")
    msg_type: ROS2MessageType = Field(description="Expected message type")
    qos_profile: ROS2QoSProfile = Field(default=ROS2QoSProfile.SYSTEM_DEFAULT)
    callback_url: Optional[str] = Field(
        default=None,
        description="Webhook URL for message callbacks (optional)"
    )


class TopicPublishRequest(BaseModel):
    """Request to publish to a ROS2 topic."""
    topic_name: str = Field(description="Topic to publish to")
    msg_type: ROS2MessageType = Field(description="Message type")
    message_data: Dict[str, Any] = Field(description="Message payload")
    qos_profile: ROS2QoSProfile = Field(default=ROS2QoSProfile.SYSTEM_DEFAULT)


class TopicMessage(BaseModel):
    """ROS2 topic message."""
    topic_name: str
    msg_type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sequence: int = Field(default=0, description="Message sequence number")


# ============================================================================
# SERVICE OPERATIONS
# ============================================================================

class ServiceInfo(BaseModel):
    """ROS2 service information."""
    name: str = Field(description="Service name (e.g., /robot/set_mode)")
    srv_type: str = Field(description="Service type (e.g., std_srvs/SetBool)")


class ServiceCallRequest(BaseModel):
    """Request to call a ROS2 service."""
    service_name: str = Field(description="Service to call")
    srv_type: str = Field(description="Service type")
    request_data: Dict[str, Any] = Field(description="Service request payload")
    timeout_s: float = Field(default=5.0, ge=0.1, le=60.0)


class ServiceCallResponse(BaseModel):
    """Response from ROS2 service call."""
    service_name: str
    success: bool
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    duration_s: float


# ============================================================================
# ACTION OPERATIONS
# ============================================================================

class ActionGoalStatus(str, Enum):
    """ROS2 action goal status."""
    ACCEPTED = "accepted"
    EXECUTING = "executing"
    CANCELING = "canceling"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"
    ABORTED = "aborted"


class ActionInfo(BaseModel):
    """ROS2 action information."""
    name: str = Field(description="Action name (e.g., /navigate_to_pose)")
    action_type: str = Field(description="Action type (e.g., nav2_msgs/NavigateToPose)")


class ActionGoalRequest(BaseModel):
    """Request to send action goal to ROS2."""
    action_name: str = Field(description="Action to execute")
    action_type: str = Field(description="Action type")
    goal_data: Dict[str, Any] = Field(description="Goal payload")
    timeout_s: float = Field(default=300.0, ge=1.0, le=3600.0)


class ActionGoalResponse(BaseModel):
    """Response from action goal submission."""
    goal_id: str
    action_name: str
    status: ActionGoalStatus
    accepted: bool


class ActionFeedback(BaseModel):
    """Action feedback message."""
    goal_id: str
    action_name: str
    feedback_data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ActionResult(BaseModel):
    """Action result."""
    goal_id: str
    action_name: str
    status: ActionGoalStatus
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


# ============================================================================
# PARAMETER OPERATIONS
# ============================================================================

class ParameterType(str, Enum):
    """ROS2 parameter types."""
    BOOL = "bool"
    INT = "integer"
    DOUBLE = "double"
    STRING = "string"
    BYTE_ARRAY = "byte_array"
    BOOL_ARRAY = "bool_array"
    INT_ARRAY = "integer_array"
    DOUBLE_ARRAY = "double_array"
    STRING_ARRAY = "string_array"


class Parameter(BaseModel):
    """ROS2 parameter."""
    name: str
    type: ParameterType
    value: Union[bool, int, float, str, List[Any]]


class ParameterGetRequest(BaseModel):
    """Request to get ROS2 parameter."""
    node_name: str = Field(description="Node name (e.g., /robot_controller)")
    parameter_name: str = Field(description="Parameter name")


class ParameterSetRequest(BaseModel):
    """Request to set ROS2 parameter."""
    node_name: str
    parameter: Parameter


# ============================================================================
# NODE INFORMATION
# ============================================================================

class NodeInfo(BaseModel):
    """ROS2 node information."""
    name: str = Field(description="Node name")
    namespace: str = Field(description="Node namespace")
    topics_published: List[str] = Field(default_factory=list)
    topics_subscribed: List[str] = Field(default_factory=list)
    services: List[str] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)


class NodeListResponse(BaseModel):
    """Response with list of ROS2 nodes."""
    total: int
    nodes: List[NodeInfo]


# ============================================================================
# BRIDGE STATUS
# ============================================================================

class BridgeStatus(BaseModel):
    """ROS2 bridge connection status."""
    connected: bool
    ros2_domain_id: int
    active_subscriptions: int
    active_publishers: int
    nodes_discovered: int
    last_heartbeat: datetime = Field(default_factory=datetime.utcnow)


class BridgeInfo(BaseModel):
    """ROS2 bridge module information."""
    name: str = "ROS2 Bridge"
    version: str = "1.0.0"
    description: str
    status: BridgeStatus
    features: List[str] = Field(default_factory=list)
