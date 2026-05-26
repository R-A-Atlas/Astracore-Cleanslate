from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

_STORE_LOCK = Lock()


def _subscriptions_store_path() -> Path:
    raw = os.getenv("ASTRACORE_BILLING_SUBSCRIPTIONS_FILE", "workspace/memory/billing/subscriptions.json").strip()
    return Path(raw)


def _webhook_secret() -> str:
    return os.getenv("ASTRACORE_STRIPE_WEBHOOK_SECRET", "dev_stripe_webhook_secret").strip()


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True))
    tmp.replace(path)


def _load_subscriptions() -> dict[str, dict[str, Any]]:
    with _STORE_LOCK:
        data = _read_json(_subscriptions_store_path())
    return data if isinstance(data, dict) else {}


def _save_subscriptions(payload: dict[str, dict[str, Any]]) -> None:
    with _STORE_LOCK:
        _atomic_write_json(_subscriptions_store_path(), payload)


def _normalize_user_id(user_id: str) -> str:
    return user_id.strip().lower()


def _stable_id(prefix: str, user_id: str, plan: str = "") -> str:
    digest = hashlib.sha256(f"{prefix}:{user_id}:{plan}".encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def create_checkout_session(*, user_id: str, plan: str) -> dict[str, str]:
    norm_user = _normalize_user_id(user_id)
    session_id = _stable_id("cs_test", norm_user, plan)
    return {
        "checkout_session_id": session_id,
        "checkout_url": f"https://billing.stripe.local/checkout/{session_id}",
    }


def create_billing_portal_link(*, user_id: str) -> dict[str, str]:
    norm_user = _normalize_user_id(user_id)
    portal_id = _stable_id("bps_test", norm_user)
    return {"portal_url": f"https://billing.stripe.local/portal/{portal_id}"}


def verify_webhook_secret(provided_secret: str | None) -> bool:
    return bool(provided_secret) and provided_secret.strip() == _webhook_secret()


def _extract_event_user_id(event: dict[str, Any]) -> str:
    data_obj = ((event.get("data") or {}).get("object") or {}) if isinstance(event, dict) else {}
    candidates = [
        data_obj.get("user_id"),
        data_obj.get("user_email"),
        data_obj.get("customer_email"),
        event.get("user_id"),
    ]
    for val in candidates:
        if isinstance(val, str) and val.strip():
            return _normalize_user_id(val)
    return ""


def process_webhook_event(event: dict[str, Any]) -> dict[str, Any]:
    event_type = str(event.get("type") or "").strip().lower()
    user_id = _extract_event_user_id(event)
    if not user_id:
        return {"updated": False, "reason": "missing_user"}

    status_map = {
        "subscription.active": "active",
        "subscription.past_due": "past_due",
        "subscription.canceled": "canceled",
    }
    mapped = status_map.get(event_type)
    if not mapped:
        return {"updated": False, "reason": "ignored_event", "user_id": user_id}

    data_obj = ((event.get("data") or {}).get("object") or {}) if isinstance(event, dict) else {}
    plan = str(data_obj.get("plan") or "retail").strip().lower() or "retail"
    now_iso = datetime.now(timezone.utc).isoformat()

    store = _load_subscriptions()
    store[user_id] = {
        "status": mapped,
        "plan": plan,
        "updated_at": now_iso,
        "event_type": event_type,
    }
    _save_subscriptions(store)
    return {"updated": True, "user_id": user_id, "status": mapped, "plan": plan}


def get_billing_state(user_id: str) -> dict[str, str]:
    norm = _normalize_user_id(user_id)
    row = _load_subscriptions().get(norm)
    if not isinstance(row, dict):
        return {"status": "active", "plan": "retail", "event_type": "default"}
    status = str(row.get("status") or "active").strip().lower()
    plan = str(row.get("plan") or "retail").strip().lower() or "retail"
    return {"status": status, "plan": plan, "event_type": str(row.get("event_type") or "")}


def resolve_effective_plan(*, user_id: str, requested_plan: str) -> tuple[str, str | None, str]:
    billing = get_billing_state(user_id)
    status = billing["status"]
    if status in {"past_due", "canceled"}:
        return "restricted", f"Billing status '{status}' enforces restricted plan lock", status
    if status == "active":
        return requested_plan, None, status
    return requested_plan, None, status
