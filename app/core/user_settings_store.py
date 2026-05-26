from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from threading import Lock

_STORE_LOCK = Lock()


def _settings_path() -> Path:
    raw = os.getenv("ASTRACORE_USER_SETTINGS_FILE", "workspace/memory/settings/user_settings.json").strip()
    return Path(raw)


def _default_settings() -> dict:
    return {
        "profile": {"name": "User", "timezone": "UTC"},
        "experience": {"coach_tone": "balanced", "coaching_preferences": []},
        "privacy": {"retention_days": 365, "export_request": False},
    }


def _load_store(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _atomic_save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, separators=(",", ":"), sort_keys=True)

    with tempfile.NamedTemporaryFile("w", delete=False, dir=str(path.parent), encoding="utf-8") as tmp:
        tmp.write(payload)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)

    os.replace(tmp_path, path)


def get_user_settings(email: str) -> dict:
    owner = email.strip().lower()
    if not owner:
        return _default_settings()

    path = _settings_path()
    with _STORE_LOCK:
        store = _load_store(path)
        settings = store.get(owner)
        if not isinstance(settings, dict):
            return _default_settings()
        merged = _default_settings()
        for section in ("profile", "experience", "privacy"):
            v = settings.get(section)
            if isinstance(v, dict):
                merged[section].update(v)
        return merged


def put_user_settings(email: str, settings: dict) -> dict:
    owner = email.strip().lower()
    if not owner:
        raise ValueError("owner email required")

    path = _settings_path()
    with _STORE_LOCK:
        store = _load_store(path)
        store[owner] = {
            "profile": dict(settings.get("profile") or {}),
            "experience": dict(settings.get("experience") or {}),
            "privacy": dict(settings.get("privacy") or {}),
        }
        _atomic_save(path, store)
    return get_user_settings(owner)
