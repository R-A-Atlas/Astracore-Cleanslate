from __future__ import annotations

import os
from dataclasses import dataclass


def _env_int(name: str, default: int, *, min_value: int, max_value: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(min_value, min(max_value, value))


@dataclass(frozen=True)
class SecuritySettings:
    ops_token_header: str = "x-ops-token"
    ops_token: str = "dev-ops-token"
    ops_token_prev: str = ""
    rate_limit_per_min: int = 60
    rate_limit_window_sec: int = 60


@dataclass(frozen=True)
class RuntimeSettings:
    port: int = 8080
    environment: str = "development"


@dataclass(frozen=True)
class OpsAlertSettings:
    error_rate_warn_pct: int = 5
    error_rate_crit_pct: int = 15
    queue_depth_warn: int = 5
    queue_depth_crit: int = 10


def load_security_settings() -> SecuritySettings:
    return SecuritySettings(
        ops_token=os.getenv("ASTRACORE_OPS_TOKEN", "dev-ops-token").strip() or "dev-ops-token",
        ops_token_prev=os.getenv("ASTRACORE_OPS_TOKEN_PREV", "").strip(),
        rate_limit_per_min=_env_int("ASTRACORE_RATE_LIMIT_PER_MIN", 60, min_value=1, max_value=10000),
        rate_limit_window_sec=_env_int("ASTRACORE_RATE_LIMIT_WINDOW_SEC", 60, min_value=1, max_value=3600),
    )


def load_runtime_settings() -> RuntimeSettings:
    return RuntimeSettings(
        port=_env_int("PORT", 8080, min_value=1, max_value=65535),
        environment=os.getenv("ENVIRONMENT", "development").strip() or "development",
    )


def load_ops_alert_settings() -> OpsAlertSettings:
    return OpsAlertSettings(
        error_rate_warn_pct=_env_int("ASTRACORE_ALERT_ERROR_RATE_WARN_PCT", 5, min_value=1, max_value=100),
        error_rate_crit_pct=_env_int("ASTRACORE_ALERT_ERROR_RATE_CRIT_PCT", 15, min_value=1, max_value=100),
        queue_depth_warn=_env_int("ASTRACORE_ALERT_QUEUE_DEPTH_WARN", 5, min_value=1, max_value=10000),
        queue_depth_crit=_env_int("ASTRACORE_ALERT_QUEUE_DEPTH_CRIT", 10, min_value=1, max_value=10000),
    )
