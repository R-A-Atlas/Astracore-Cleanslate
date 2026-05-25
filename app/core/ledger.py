import asyncio
import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

LEDGERS_DIR      = Path("workspace/memory/ledgers")
SEATS_DIR        = LEDGERS_DIR / "seats"
DEEP_HISTORY_DIR = LEDGERS_DIR / "deep_history"
TEMPLATE_PATH    = LEDGERS_DIR / "user_template_ledger.json"
ORG_TEMPLATE_PATH = Path("workspace/memory/org_template_ledger.json")

ROLLING_WINDOW = 10  # max live entries per array in the primary runtime ledger

# Per-org async mutex registry — one Lock per org_id, created on first access.
# Prevents silent data corruption when multiple seats write simultaneously.
_org_ledger_locks: dict[str, asyncio.Lock] = {}


def _get_org_lock(org_id: str) -> asyncio.Lock:
    return _org_ledger_locks.setdefault(org_id, asyncio.Lock())


# ---------------------------------------------------------------------------
# Directory bootstrap helpers
# ---------------------------------------------------------------------------

def _ensure_seats_dir() -> None:
    SEATS_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_deep_history_dir() -> None:
    DEEP_HISTORY_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Schema backfill helper
# ---------------------------------------------------------------------------

def _backfill_schema(record: dict, template: dict) -> bool:
    """
    Recursively insert any keys present in template but absent from record.

    Nested dicts are traversed so sub-structure additions (e.g. new fields
    inside indicator_inventory) are handled without a full template rewrite.
    Returns True if record was modified, False if it was already up-to-date.

    Existing values — including all user history and custom overrides — are
    never touched; only genuinely absent keys receive the template default.
    """
    modified = False
    for key, default in template.items():
        if key not in record:
            record[key] = default
            modified = True
        elif isinstance(default, dict) and isinstance(record.get(key), dict):
            if _backfill_schema(record[key], default):
                modified = True
    return modified


# ---------------------------------------------------------------------------
# Individual user ledger helpers
# ---------------------------------------------------------------------------

def _ledger_path(user_id: str) -> Path:
    return LEDGERS_DIR / f"{user_id}_ledger.json"


def _deep_history_path(user_id: str) -> Path:
    return DEEP_HISTORY_DIR / f"deep_{user_id}.json"


def _archive_to_deep_history(user_id: str, field: str, entry: dict) -> None:
    """Append one evicted entry to the user's offline deep history archive."""
    _ensure_deep_history_dir()
    path = _deep_history_path(user_id)
    if path.exists():
        archive = json.loads(path.read_text())
    else:
        archive = {
            "user_token": user_id,
            "archived_mistakes": [],
            "archived_patterns": [],
        }
    archive_key = (
        "archived_mistakes" if field == "historical_mistakes" else "archived_patterns"
    )
    archive[archive_key].append(entry)
    path.write_text(json.dumps(archive, indent=2))


def _enforce_rolling_window(ledger: dict, user_id: str, field: str) -> dict:
    """
    Enforce a ROLLING_WINDOW cap on a ledger array field.
    Each entry beyond the cap is extracted oldest-first and written to
    the user's deep history archive before being removed from the live ledger.
    """
    array = ledger.get(field, [])
    while len(array) > ROLLING_WINDOW:
        evicted = array.pop(0)
        _archive_to_deep_history(user_id, field, evicted)
    ledger[field] = array
    return ledger


def write_ledger(user_id: str, data: dict) -> None:
    """
    Atomic user ledger write via tmp-file → os.replace().

    Serializes to a .tmp sibling in the same directory first, then invokes
    os.replace() to swap the reference at OS level.  A partially written
    .tmp never replaces the real file, and readers never see a half-written
    state between the two steps.
    """
    target   = _ledger_path(user_id)
    tmp_path = target.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(data, indent=2))
    os.replace(tmp_path, target)


def ensure_ledger(user_id: str) -> dict:
    """
    Return a user's ledger, creating it from the template if it doesn't exist.

    If the file already exists, compare its keys against the current template
    and backfill any missing structural fields introduced by schema updates.
    Existing historical records, patterns, and custom values are preserved.
    The resulting write is atomic (tmp → os.replace).
    """
    path = _ledger_path(user_id)
    if not path.exists():
        # Bootstrap from template, stamp user token, write atomically.
        ledger = json.loads(TEMPLATE_PATH.read_text())
        ledger["user_token"] = user_id
        write_ledger(user_id, ledger)
    else:
        # Existing file — backfill any keys the template now has but the
        # file was written before they existed.
        template = json.loads(TEMPLATE_PATH.read_text())
        ledger   = json.loads(path.read_text())
        if _backfill_schema(ledger, template):
            write_ledger(user_id, ledger)
    return json.loads(path.read_text())


def read_ledger(user_id: str) -> dict:
    path = _ledger_path(user_id)
    if not path.exists():
        return ensure_ledger(user_id)
    return json.loads(path.read_text())


def append_mistake(user_id: str, mistake: dict) -> None:
    ledger = read_ledger(user_id)
    ledger["historical_mistakes"].append(mistake)
    ledger = _enforce_rolling_window(ledger, user_id, "historical_mistakes")
    write_ledger(user_id, ledger)


def append_pattern(user_id: str, pattern: dict) -> None:
    ledger = read_ledger(user_id)
    ledger["behavioral_patterns"].append(pattern)
    ledger = _enforce_rolling_window(ledger, user_id, "behavioral_patterns")
    write_ledger(user_id, ledger)


def set_indicator(user_id: str, key: str, value) -> None:
    ledger = read_ledger(user_id)
    ledger["indicator_inventory"][key] = value
    write_ledger(user_id, ledger)


# ---------------------------------------------------------------------------
# Organisation ledger helpers — async, mutex-protected
#
# Architecture note: _write_org_ledger_raw() is the single atomic disk writer
# for org ledgers.  Every public async function acquires _get_org_lock(org_id)
# before calling it to avoid re-entrant lock deadlocks.
# ensure_org_ledger() is intentionally sync — it runs during startup before
# concurrent access begins, so calling _write_org_ledger_raw() lock-free
# inside it is safe.
# ---------------------------------------------------------------------------

def _org_ledger_path(org_id: str) -> Path:
    return LEDGERS_DIR / f"{org_id}_ledger.json"


def _write_org_ledger_raw(org_id: str, data: dict) -> None:
    """
    Atomic org ledger write via tmp-file → os.replace().

    Serializes to a .tmp sibling in the same directory; os.replace() swaps
    the reference atomically so no concurrent reader can observe a partial
    write.  Call either while holding the org lock (concurrent path) or from
    startup-phase code where no concurrency exists yet (ensure_org_ledger).
    """
    target   = _org_ledger_path(org_id)
    tmp_path = target.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(data, indent=2))
    os.replace(tmp_path, target)


def ensure_org_ledger(org_id: str) -> dict:
    """
    Idempotent initialization — bootstrap from the org template and stamp
    org_token on first call; backfill missing schema keys on subsequent calls.
    Call once at startup before any concurrent seat activity begins.
    """
    path = _org_ledger_path(org_id)
    if not path.exists():
        # Bootstrap from template, stamp org token, write atomically.
        org = json.loads(ORG_TEMPLATE_PATH.read_text())
        org["org_token"] = org_id
        _write_org_ledger_raw(org_id, org)
    else:
        # Existing file — backfill any keys added to the org template since
        # this org ledger was first written.
        template = json.loads(ORG_TEMPLATE_PATH.read_text())
        org      = json.loads(path.read_text())
        if _backfill_schema(org, template):
            _write_org_ledger_raw(org_id, org)
    _ensure_seats_dir()
    return json.loads(path.read_text())


def read_org_ledger(org_id: str) -> dict:
    path = _org_ledger_path(org_id)
    if not path.exists():
        return ensure_org_ledger(org_id)
    return json.loads(path.read_text())


async def write_org_ledger(org_id: str, data: dict) -> None:
    """Mutex-protected atomic write for ad-hoc external callers."""
    async with _get_org_lock(org_id):
        _write_org_ledger_raw(org_id, data)


async def register_operator(org_id: str, operator_id: str) -> dict:
    """
    Mutex-protected seat registration.
    ensure_org_ledger() must be called before this during startup.
    """
    async with _get_org_lock(org_id):
        path = _org_ledger_path(org_id)
        if not path.exists():
            raise FileNotFoundError(
                f"Org ledger '{org_id}' not found. Call ensure_org_ledger() first."
            )
        org = json.loads(path.read_text())

        if len(org["active_operators"]) >= org["max_seats"]:
            raise ValueError(
                f"Org '{org_id}' has reached its seat limit of {org['max_seats']}."
            )

        if operator_id not in org["active_operators"]:
            org["active_operators"][operator_id] = {"sessions": 0, "status": "active"}
            _write_org_ledger_raw(org_id, org)

    # Provision the per-seat log outside the lock — each operator file is independent.
    _ensure_seats_dir()
    seat_log_path = SEATS_DIR / f"{operator_id}_log.json"
    if not seat_log_path.exists():
        seat_log_path.write_text(
            json.dumps(
                {"operator_key": operator_id, "org_token": org_id, "session_rows": []},
                indent=2,
            )
        )

    return json.loads(_org_ledger_path(org_id).read_text())


async def consume_org_session(org_id: str, operator_id: str) -> dict:
    """
    Atomic read-modify-write for session consumption.

    The entire read → ceiling check → increment → write cycle runs under one
    lock, eliminating the race window between simultaneous multi-laptop
    submissions.  The write itself uses _write_org_ledger_raw() so the disk
    state is always replaced atomically — no reader sees a partially updated
    session count.
    """
    async with _get_org_lock(org_id):
        path = _org_ledger_path(org_id)
        org  = json.loads(path.read_text())

        if org["sessions_consumed_this_month"] >= org["allocated_monthly_sessions"]:
            raise ValueError(
                f"Org '{org_id}' has exhausted its "
                f"{org['allocated_monthly_sessions']} monthly sessions."
            )

        org["sessions_consumed_this_month"] += 1
        if operator_id in org["active_operators"]:
            org["active_operators"][operator_id]["sessions"] += 1

        _write_org_ledger_raw(org_id, org)

    return org


# ---------------------------------------------------------------------------
# Per-seat session log helpers (workspace/memory/ledgers/seats/)
# ---------------------------------------------------------------------------

def append_seat_session_row(operator_id: str, row: dict) -> None:
    """
    Append a tagged session metadata row to the operator's isolated seat log.
    Row must carry a 'session_by' key before being passed here.
    """
    _ensure_seats_dir()
    path = SEATS_DIR / f"{operator_id}_log.json"
    if path.exists():
        log = json.loads(path.read_text())
    else:
        log = {"operator_key": operator_id, "org_token": None, "session_rows": []}
    log["session_rows"].append(row)
    path.write_text(json.dumps(log, indent=2))


def read_seat_log(operator_id: str) -> dict:
    _ensure_seats_dir()
    path = SEATS_DIR / f"{operator_id}_log.json"
    if not path.exists():
        return {"operator_key": operator_id, "org_token": None, "session_rows": []}
    return json.loads(path.read_text())


# ---------------------------------------------------------------------------
# Server epoch timestamp baseline — cross-seat timeline synchronization
# ---------------------------------------------------------------------------

def get_server_time_baseline() -> dict:
    """
    Return the server's authoritative Unix epoch baseline for session init.

    Clients must call this once at session start and propagate epoch_ms through
    every voice transcript and image frame metadata entry, guaranteeing timeline
    alignment across all seats regardless of individual laptop clock skew.
    """
    now = time.time()
    return {
        "epoch_s":  now,
        "epoch_ms": int(now * 1000),
        "iso":      datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
    }


def stamp_epoch_metadata(entry: dict, epoch_ms: int) -> dict:
    """
    Inject the server epoch baseline into a file-tracking metadata entry.
    Mutates and returns the entry for inline chaining with append helpers.
    """
    entry["server_epoch_ms"] = epoch_ms
    return entry
