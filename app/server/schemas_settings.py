from pydantic import BaseModel, Field, field_validator


class ProfileSettings(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    timezone: str = Field(min_length=1, max_length=80)


class ExperienceSettings(BaseModel):
    coach_tone: str = Field(min_length=1, max_length=40)
    coaching_preferences: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("coaching_preferences")
    @classmethod
    def validate_preferences_items(cls, value: list[str]) -> list[str]:
        for item in value:
            if len(item) > 80:
                raise ValueError("each coaching preference must be <= 80 characters")
        return value


class PrivacySettings(BaseModel):
    retention_days: int = Field(ge=1, le=3650)
    export_request: bool


class UserSettingsV1(BaseModel):
    profile: ProfileSettings
    experience: ExperienceSettings
    privacy: PrivacySettings
