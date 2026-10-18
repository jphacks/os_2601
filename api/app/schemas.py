from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_UTTERANCE_CHARS = 200
SPEECH_REQUEST_MAX_CHARS = 200
StuckSeconds = Annotated[int, Field(ge=5, le=1200)]
CooldownSeconds = Annotated[int, Field(ge=0, le=300)]
MaxLevel = Annotated[int, Field(ge=1, le=2)]


class SettingsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stuck_seconds: StuckSeconds | None = None
    cooldown_seconds: CooldownSeconds | None = None
    max_level: MaxLevel | None = None
    persona: Literal["teacher", "ikemen"] | None = None


class SessionCreateRequest(BaseModel):
    worksheet_id: Literal["FREE"]
    learner_label: str = "学習者"
    mode: Literal["live", "scripted"]
    settings: SettingsInput = SettingsInput()


class SettingsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stuck_seconds: StuckSeconds | None = None
    cooldown_seconds: CooldownSeconds | None = None
    persona: Literal["teacher", "ikemen"] | None = None

    @model_validator(mode="after")
    def require_one(self) -> "SettingsPatch":
        if self.stuck_seconds is None and self.cooldown_seconds is None and self.persona is None:
            raise ValueError("stuck_seconds、cooldown_seconds、persona のどれかが要る")
        return self


class SignalRequest(BaseModel):
    motion: float | None = Field(default=None, ge=0, le=1)
    camera_ok: bool | None = None
    force_stuck: bool = False

    @model_validator(mode="after")
    def require_camera_ok(self) -> "SignalRequest":
        if not self.force_stuck and self.camera_ok is None:
            raise ValueError("force_stuck でなければ camera_ok が要る")
        return self


class HintRequest(BaseModel):
    trigger: Literal["auto", "manual", "voice"]
    frame_id: str
    utterance: str | None = Field(default=None, max_length=MAX_UTTERANCE_CHARS)


class CheckRequest(BaseModel):
    frame_id: str


class ProblemRequest(BaseModel):
    frame_id: str


class SpeechRequest(BaseModel):
    text: Annotated[str, Field(min_length=1, max_length=SPEECH_REQUEST_MAX_CHARS)]
    character: Literal["handsome", "teacher"] = "handsome"
