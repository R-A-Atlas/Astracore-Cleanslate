from pydantic import BaseModel, Field, field_validator


class _EmailModel(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        email = value.strip().lower()
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            raise ValueError("invalid email")
        return email


class AuthSignupRequest(_EmailModel):
    password: str = Field(..., min_length=8)


class AuthLoginRequest(_EmailModel):
    password: str = Field(..., min_length=1)


class PasswordResetRequest(_EmailModel):
    pass


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


class OAuthStartRequest(BaseModel):
    link_account: bool = False


class OAuthCallbackRequest(BaseModel):
    state: str = Field(..., min_length=1)
    code: str = Field(..., min_length=1)
    github_user_id: str = Field(..., min_length=1)
    github_email: str | None = None
