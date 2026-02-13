"""
Built-in Trait Definitions

Predefined traits for agent characteristics across all categories.
"""

from .schemas import TraitCategory, TraitDefinition, TraitType

# ============================================================================
# COGNITIVE TRAITS - Intelligence, reasoning, learning
# ============================================================================

COGNITIVE_TRAITS = [
    TraitDefinition(
        id="cognitive.reasoning_depth",
        name="Reasoning Depth",
        category=TraitCategory.COGNITIVE,
        type=TraitType.FLOAT,
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        inheritable=True,
        mutable=True,
        ethics_critical=False,
        description="Depth of logical reasoning (0=shallow quick, 1=deep thorough)",
    ),
    TraitDefinition(
        id="cognitive.creativity",
        name="Creativity",
        category=TraitCategory.COGNITIVE,
        type=TraitType.FLOAT,
        default_value=0.3,
        min_value=0.0,
        max_value=1.0,
        inheritable=True,
        mutable=True,
        ethics_critical=False,
        description="Novel solution generation ability",
    ),
    TraitDefinition(
        id="cognitive.learning_rate",
        name="Learning Rate",
        category=TraitCategory.COGNITIVE,
        type=TraitType.FLOAT,
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        inheritable=True,
        mutable=True,
        ethics_critical=False,
        description="Speed of adaptation to new information",
    ),
    TraitDefinition(
        id="cognitive.pattern_recognition",
        name="Pattern Recognition",
        category=TraitCategory.COGNITIVE,
        type=TraitType.FLOAT,
        default_value=0.6,
        min_value=0.0,
        max_value=1.0,
        inheritable=True,
        mutable=True,
        ethics_critical=False,
        description="Ability to identify patterns in data",
    ),
]

# ============================================================================
# ETHICAL TRAITS - Alignment, safety, compliance
# ============================================================================

ETHICAL_TRAITS = [
    TraitDefinition(
        id="ethical.safety_priority",
        name="Safety Priority",
        category=TraitCategory.ETHICAL,
        type=TraitType.FLOAT,
        default_value=0.9,
        min_value=0.7,  # CRITICAL: Minimum safety threshold
        max_value=1.0,
        inheritable=True,
        mutable=False,  # Safety is IMMUTABLE
        ethics_critical=True,
        description="Priority given to safety constraints (IMMUTABLE, min 0.7)",
    ),
    TraitDefinition(
        id="ethical.compliance_strictness",
        name="Compliance Strictness",
        category=TraitCategory.ETHICAL,
        type=TraitType.FLOAT,
        default_value=0.8,
        min_value=0.5,
        max_value=1.0,
        inheritable=True,
        mutable=True,
        ethics_critical=True,
        description="Adherence to policy rules and regulations",
    ),
    TraitDefinition(
        id="ethical.transparency",
        name="Transparency",
        category=TraitCategory.ETHICAL,
        type=TraitType.FLOAT,
        default_value=0.8,
        min_value=0.0,
        max_value=1.0,
        inheritable=True,
        mutable=True,
        ethics_critical=True,
        description="Openness about decision-making process",
    ),
    TraitDefinition(
        id="ethical.harm_avoidance",
        name="Harm Avoidance",
        category=TraitCategory.ETHICAL,
        type=TraitType.FLOAT,
        default_value=0.95,
        min_value=0.8,  # High minimum
        max_value=1.0,
        inheritable=True,
        mutable=False,  # IMMUTABLE
        ethics_critical=True,
        description="Avoidance of harmful actions (IMMUTABLE, min 0.8)",
    ),
]

# ============================================================================
# PERFORMANCE TRAITS - Speed, accuracy, efficiency
# ============================================================================

PERFORMANCE_TRAITS = [
    TraitDefinition(
        id="performance.speed_priority",
        name="Speed Priority",
        category=TraitCategory.PERFORMANCE,
        type=TraitType.FLOAT,
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        inheritable=True,
        mutable=True,
        ethics_critical=False,
        description="Preference for speed over accuracy (0=accuracy, 1=speed)",
    ),
    TraitDefinition(
        id="performance.energy_efficiency",
        name="Energy Efficiency",
        category=TraitCategory.PERFORMANCE,
        type=TraitType.FLOAT,
        default_value=0.7,
        min_value=0.0,
        max_value=1.0,
        inheritable=True,
        mutable=True,
        ethics_critical=False,
        description="Conservation of computational/physical resources",
    ),
    TraitDefinition(
        id="performance.accuracy_target",
        name="Accuracy Target",
        category=TraitCategory.PERFORMANCE,
        type=TraitType.FLOAT,
        default_value=0.9,
        min_value=0.5,
        max_value=1.0,
        inheritable=True,
        mutable=True,
        ethics_critical=False,
        description="Target accuracy level for tasks",
    ),
    TraitDefinition(
        id="performance.multitasking",
        name="Multitasking Ability",
        category=TraitCategory.PERFORMANCE,
        type=TraitType.FLOAT,
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        inheritable=True,
        mutable=True,
        ethics_critical=False,
        description="Ability to handle multiple concurrent tasks",
    ),
]

# ============================================================================
# BEHAVIORAL TRAITS - Response patterns, decision-making
# ============================================================================

BEHAVIORAL_TRAITS = [
    TraitDefinition(
        id="behavioral.proactiveness",
        name="Proactiveness",
        category=TraitCategory.BEHAVIORAL,
        type=TraitType.FLOAT,
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        inheritable=True,
        mutable=True,
        ethics_critical=False,
        description="Tendency to act without explicit instruction",
    ),
    TraitDefinition(
        id="behavioral.risk_tolerance",
        name="Risk Tolerance",
        category=TraitCategory.BEHAVIORAL,
        type=TraitType.FLOAT,
        default_value=0.3,
        min_value=0.0,
        max_value=0.5,  # Capped at moderate risk
        inheritable=True,
        mutable=True,
        ethics_critical=True,
        description="Willingness to take calculated risks (capped at 0.5)",
    ),
    TraitDefinition(
        id="behavioral.adaptability",
        name="Adaptability",
        category=TraitCategory.BEHAVIORAL,
        type=TraitType.FLOAT,
        default_value=0.6,
        min_value=0.0,
        max_value=1.0,
        inheritable=True,
        mutable=True,
        ethics_critical=False,
        description="Ability to adapt to changing circumstances",
    ),
    TraitDefinition(
        id="behavioral.decisiveness",
        name="Decisiveness",
        category=TraitCategory.BEHAVIORAL,
        type=TraitType.FLOAT,
        default_value=0.7,
        min_value=0.0,
        max_value=1.0,
        inheritable=True,
        mutable=True,
        ethics_critical=False,
        description="Speed of decision-making",
    ),
]

# ============================================================================
# SOCIAL TRAITS - Communication, collaboration, empathy
# ============================================================================

SOCIAL_TRAITS = [
    TraitDefinition(
        id="social.coordination_skill",
        name="Coordination Skill",
        category=TraitCategory.SOCIAL,
        type=TraitType.FLOAT,
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        inheritable=True,
        mutable=True,
        ethics_critical=False,
        description="Ability to coordinate with other agents/systems",
    ),
    TraitDefinition(
        id="social.communication_clarity",
        name="Communication Clarity",
        category=TraitCategory.SOCIAL,
        type=TraitType.FLOAT,
        default_value=0.7,
        min_value=0.0,
        max_value=1.0,
        inheritable=True,
        mutable=True,
        ethics_critical=False,
        description="Clarity and effectiveness of communication",
    ),
    TraitDefinition(
        id="social.empathy",
        name="Empathy",
        category=TraitCategory.SOCIAL,
        type=TraitType.FLOAT,
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        inheritable=True,
        mutable=True,
        ethics_critical=False,
        description="Understanding and responding to user needs",
    ),
    TraitDefinition(
        id="social.collaboration_preference",
        name="Collaboration Preference",
        category=TraitCategory.SOCIAL,
        type=TraitType.FLOAT,
        default_value=0.6,
        min_value=0.0,
        max_value=1.0,
        inheritable=True,
        mutable=True,
        ethics_critical=False,
        description="Preference for collaborative vs. independent work",
    ),
]

# ============================================================================
# TECHNICAL TRAITS - Skills, capabilities, expertise
# ============================================================================

TECHNICAL_TRAITS = [
    TraitDefinition(
        id="technical.code_generation",
        name="Code Generation",
        category=TraitCategory.TECHNICAL,
        type=TraitType.FLOAT,
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        inheritable=True,
        mutable=True,
        ethics_critical=False,
        description="Proficiency in generating code",
    ),
    TraitDefinition(
        id="technical.fleet_management",
        name="Fleet Management",
        category=TraitCategory.TECHNICAL,
        type=TraitType.FLOAT,
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        inheritable=True,
        mutable=True,
        ethics_critical=False,
        description="Expertise in managing robot fleets",
    ),
    TraitDefinition(
        id="technical.navigation_planning",
        name="Navigation Planning",
        category=TraitCategory.TECHNICAL,
        type=TraitType.FLOAT,
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        inheritable=True,
        mutable=True,
        ethics_critical=False,
        description="Proficiency in path planning and navigation",
    ),
    TraitDefinition(
        id="technical.data_analysis",
        name="Data Analysis",
        category=TraitCategory.TECHNICAL,
        type=TraitType.FLOAT,
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        inheritable=True,
        mutable=True,
        ethics_critical=False,
        description="Capability in analyzing data and extracting insights",
    ),
    TraitDefinition(
        id="technical.system_administration",
        name="System Administration",
        category=TraitCategory.TECHNICAL,
        type=TraitType.FLOAT,
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        inheritable=True,
        mutable=True,
        ethics_critical=False,
        description="Expertise in system administration and operations",
    ),
]

# ============================================================================
# ALL TRAITS REGISTRY
# ============================================================================

ALL_TRAIT_DEFINITIONS = (
    COGNITIVE_TRAITS
    + ETHICAL_TRAITS
    + PERFORMANCE_TRAITS
    + BEHAVIORAL_TRAITS
    + SOCIAL_TRAITS
    + TECHNICAL_TRAITS
)

# Trait ID index for quick lookup
TRAIT_DEFINITIONS_BY_ID = {trait.id: trait for trait in ALL_TRAIT_DEFINITIONS}
