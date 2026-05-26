from fastapi import APIRouter, Depends, Header, HTTPException

from app.billing.stripe_integration import (
    create_billing_portal_link,
    create_checkout_session,
    create_paypal_checkout_session,
    process_paypal_webhook_event,
    process_webhook_event,
    verify_paypal_webhook_secret,
    verify_webhook_secret,
)
from app.security.auth import get_current_user
from app.server.schemas_billing import CreateCheckoutSessionRequest, PaypalWebhookEvent, StripeWebhookEvent

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.post("/checkout-session")
async def create_checkout(payload: CreateCheckoutSessionRequest, user=Depends(get_current_user)):
    session = create_checkout_session(user_id=user["email"], plan=payload.plan)
    return {"status": "ok", **session}


@router.post("/paypal/checkout-session")
async def create_paypal_checkout(payload: CreateCheckoutSessionRequest, user=Depends(get_current_user)):
    session = create_paypal_checkout_session(user_id=user["email"], plan=payload.plan)
    return {"status": "ok", **session}


@router.get("/portal-link")
async def portal_link(user=Depends(get_current_user)):
    return {"status": "ok", **create_billing_portal_link(user_id=user["email"])}


@router.post("/webhook")
async def stripe_webhook(payload: StripeWebhookEvent, x_stripe_webhook_secret: str | None = Header(default=None)):
    if not verify_webhook_secret(x_stripe_webhook_secret):
        raise HTTPException(status_code=401, detail="invalid webhook secret")
    result = process_webhook_event(payload.model_dump())
    return {"status": "ok", **result}


@router.post("/paypal/webhook")
async def paypal_webhook(payload: PaypalWebhookEvent, x_paypal_webhook_secret: str | None = Header(default=None)):
    if not verify_paypal_webhook_secret(x_paypal_webhook_secret):
        raise HTTPException(status_code=401, detail="invalid webhook secret")
    result = process_paypal_webhook_event(payload.model_dump())
    return {"status": "ok", **result}
