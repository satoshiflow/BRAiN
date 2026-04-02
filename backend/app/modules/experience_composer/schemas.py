from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class InputType(str, Enum):
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    FILE = "file"
    URL = "url"
    EVENT = "event"
    API = "api"


class InputSource(str, Enum):
    USER = "user"
    SYSTEM = "system"
    AGENT = "agent"


class IntentType(str, Enum):
    EXPLAIN = "explain"
    PRESENT = "present"
    SELL = "sell"
    SUMMARIZE = "summarize"


class ExperienceType(str, Enum):
    LANDINGPAGE = "landingpage"
    CUSTOMER_EXPLAINER = "customer_explainer"
    MOBILE_VIEW = "mobile_view"
    CHAT_ANSWER = "chat_answer"
    PRESENTATION = "presentation"


class AudienceType(str, Enum):
    CUSTOMER = "customer"
    PARTNER = "partner"
    INTERNAL = "internal"
    PUBLIC = "public"


class OutputType(str, Enum):
    ANSWER = "answer"
    UI = "ui"
    PRESENTATION = "presentation"
    ACTION = "action"
    ARTIFACT = "artifact"
    EVENT = "event"


class OutputTarget(str, Enum):
    CHAT = "chat"
    WEB = "web"
    MOBILE = "mobile"
    ADMIN = "admin"
    SYSTEM = "system"


class InputEnvelope(BaseModel):
    type: InputType
    source: InputSource
    content: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)


class ExperienceSubject(BaseModel):
    type: str = Field(..., min_length=1, max_length=60)
    id: str | None = None
    query: str | None = None


class ExperienceAudience(BaseModel):
    type: AudienceType = AudienceType.PUBLIC
    id: str | None = None


class ExperienceContext(BaseModel):
    device: str = Field(default="web", min_length=1, max_length=40)
    locale: str = Field(default="de-DE", min_length=2, max_length=20)
    customer_id: str | None = None
    region: str | None = None
    season: str | None = None
    user_skill: str | None = None


class ExperienceRenderRequest(BaseModel):
    intent: IntentType
    experience_type: ExperienceType
    subject: ExperienceSubject
    audience: ExperienceAudience = Field(default_factory=ExperienceAudience)
    context: ExperienceContext = Field(default_factory=ExperienceContext)
    input: InputEnvelope | None = None


class ExperienceSection(BaseModel):
    component: str = Field(..., min_length=1, max_length=80)
    data_ref: str = Field(..., min_length=1, max_length=120)
    title: str | None = None
    props: dict[str, Any] = Field(default_factory=dict)


class ExperienceSourceRef(BaseModel):
    id: str
    title: str
    type: str
    tags: list[str] = Field(default_factory=list)


class ExperienceSafety(BaseModel):
    mode: str = Field(default="strict", min_length=1, max_length=40)
    warnings: list[str] = Field(default_factory=list)


class ExperienceCachePolicy(BaseModel):
    ttl_seconds: int = Field(default=1800, ge=0)
    persist: bool = False


class ExperiencePayload(BaseModel):
    schema_version: str = "1.0"
    experience_type: ExperienceType
    variant: str
    context: dict[str, Any] = Field(default_factory=dict)
    data: dict[str, Any] = Field(default_factory=dict)
    sources: list[ExperienceSourceRef] = Field(default_factory=list)
    sections: list[ExperienceSection] = Field(default_factory=list)
    safety: ExperienceSafety = Field(default_factory=ExperienceSafety)
    cache: ExperienceCachePolicy = Field(default_factory=ExperienceCachePolicy)


class OutputEnvelope(BaseModel):
    schema_version: str = "1.0"
    type: OutputType
    target: OutputTarget
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExperienceRenderResponse(BaseModel):
    output: OutputEnvelope
