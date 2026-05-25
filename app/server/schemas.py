from pydantic import BaseModel, Field


class SessionStartRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    operator_key: str = Field(..., min_length=1)
    plan: str = Field(default="retail", min_length=1)


class SessionStopCommitRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    operator_key: str = Field(..., min_length=1)
