from pydantic import BaseModel, Field


class CreateCheckoutSessionRequest(BaseModel):
    plan: str = Field(default="retail", min_length=1)


class StripeWebhookEvent(BaseModel):
    type: str = Field(..., min_length=1)
    data: dict = Field(default_factory=dict)
