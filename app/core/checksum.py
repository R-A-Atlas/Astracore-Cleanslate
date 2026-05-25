import re
import sys
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

ERROR_LOG = Path("workspace/memory/error.log")


def _token_fingerprint(data: dict) -> str:
    """Stable SHA-256 of sorted key-value pairs in a data structure."""
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _log_error(context: str, baseline_keys: set, current_keys: set) -> None:
    ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
    missing = baseline_keys - current_keys
    added = current_keys - baseline_keys
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "context": context,
        "missing_keys": sorted(missing),
        "unexpected_keys": sorted(added),
    }
    with ERROR_LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def verify_output_integrity(baseline: dict, output: dict, context: str = "export") -> None:
    """
    Compare output token keys against the baseline transcript inputs.
    Halts the process via sys.exit() if any key indicator shifts or disappears.
    """
    baseline_keys = set(baseline.keys())
    output_keys = set(output.keys())

    if baseline_keys != output_keys or _token_fingerprint(baseline) != _token_fingerprint(output):
        _log_error(context, baseline_keys, output_keys)
        print(
            f"[CHECKSUM GATE] Integrity failure in '{context}'. "
            "Transaction halted. See workspace/memory/error.log.",
            file=sys.stderr,
        )
        sys.exit(1)


def verify_key_coverage(baseline: dict, output: dict, context: str = "compilation") -> None:
    """
    Soft variant: only checks that every key present in baseline survives into output.
    Extra keys in output are permitted. Halts on any missing key.
    """
    baseline_keys = set(baseline.keys())
    output_keys = set(output.keys())
    missing = baseline_keys - output_keys

    if missing:
        _log_error(context, baseline_keys, output_keys)
        print(
            f"[CHECKSUM GATE] Missing keys {sorted(missing)} in '{context}'. "
            "Transaction halted. See workspace/memory/error.log.",
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# String sanitization & filename security guardrails
# ---------------------------------------------------------------------------

# Matches path traversal sequences: ../ and ..\
_TRAVERSAL_RE = re.compile(r"\.{2,}[/\\]")

# Allowlist for label strings: alphanumeric, underscore, hyphen only.
# Dots are intentionally excluded from labels to prevent extension injection.
_SAFE_LABEL_RE = re.compile(r"[^A-Za-z0-9_\-]")

# Allowlist for filename stems: same as labels plus a single dot for extension boundary.
_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9_\-\.]")

# Collapse consecutive dots to prevent extension spoofing (e.g. "file..php.json")
_MULTI_DOT_RE = re.compile(r"\.{2,}")


def sanitize_label(value: str) -> str:
    """
    Strip directory traversal sequences and all non-safe characters from any
    user-supplied session name, ticker symbol, or tracking parameter before it
    is written into a storage hash or memory map key.

    Safe characters: A-Z, a-z, 0-9, underscore, hyphen.
    """
    value = _TRAVERSAL_RE.sub("", value)
    value = _SAFE_LABEL_RE.sub("", value)
    return value.strip("-_")


def sanitize_filename(value: str) -> str:
    """
    Produce a filesystem-safe filename stem from any user-supplied string.
    Preserves a single dot for file extension boundaries; collapses multiples.
    Falls back to 'unnamed' if the result is empty after stripping.
    """
    value = _TRAVERSAL_RE.sub("", value)
    value = _SAFE_FILENAME_RE.sub("", value)
    value = _MULTI_DOT_RE.sub(".", value)
    value = value.strip("-_.")
    return value or "unnamed"


def generate_media_filename(operator_key: str, extension: str = "mp4") -> str:
    """
    Derive a deterministic, filesystem-safe physical media filename from the
    operator key and the current millisecond epoch timestamp.

    Output format: astracore_{8-char SHA-256 hex}.{extension}
    Example:       astracore_8f3a9b1c.mp4

    The user's human-readable strategy name must be preserved separately in
    the 'display_name' field of their JSON profile ledger — never embedded in
    this physical filename, so special characters and slash markers in strategy
    identifiers can never cause directory breaks or file I/O errors.
    """
    ms_timestamp = int(time.time() * 1000)
    raw = f"{operator_key}:{ms_timestamp}"
    hash_hex = hashlib.sha256(raw.encode()).hexdigest()[:8]
    ext = extension.lstrip(".")
    return f"astracore_{hash_hex}.{ext}"


# ---------------------------------------------------------------------------
# Frame-to-transcript timeline binding & drift validation
# ---------------------------------------------------------------------------

# Maximum tolerated gap between consecutive aligned entries.
# 30 s = 6× the 5-second screenshot interval, providing comfortable tolerance
# for network jitter, spool-flush latency, and multi-laptop clock skew.
_DRIFT_CEILING_MS = 30_000


def bind_frame_to_transcript(
    frame_path: str,
    transcript_segment: str,
    epoch_ms: int,
    operator_key: str,
) -> dict:
    """
    Bind a captured frame snapshot to its voice transcript segment using the
    server epoch baseline as the shared timeline anchor.

    Returns the canonical seat-log row format.  frame_hash provides a
    content-addressable reference to the visual record; epoch_ms pins both
    the image and the text to the same absolute moment so that timeline
    alignment survives long sessions, server restarts, and clock drift
    between operator laptops.
    """
    path = Path(frame_path)
    frame_hash = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    return {
        "epoch_ms":           epoch_ms,
        "bound_at":           datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).isoformat(),
        "operator_key":       sanitize_label(operator_key),
        "frame_ref":          path.name,
        "frame_hash":         frame_hash,
        "transcript_segment": transcript_segment,
    }


def verify_timeline_alignment(entries: list, context: str = "session") -> None:
    """
    Assert that a sequence of bind_frame_to_transcript entries is
    monotonically ordered by epoch_ms with no inter-entry gap exceeding
    _DRIFT_CEILING_MS.

    On any violation: writes a structured record to ERROR_LOG and raises
    RuntimeError so the caller can decide whether to abort or warn.
    An empty or single-entry list always passes.
    """
    for i in range(1, len(entries)):
        prev_ms = entries[i - 1]["epoch_ms"]
        curr_ms = entries[i]["epoch_ms"]
        gap_ms  = curr_ms - prev_ms

        if curr_ms < prev_ms:
            violation = "non-monotonic"
        elif gap_ms > _DRIFT_CEILING_MS:
            violation = "drift-ceiling-exceeded"
        else:
            continue

        ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp":     datetime.now(timezone.utc).isoformat(),
            "context":       context,
            "entry_index":   i,
            "prev_epoch_ms": prev_ms,
            "curr_epoch_ms": curr_ms,
            "gap_ms":        gap_ms,
            "violation":     violation,
        }
        with ERROR_LOG.open("a") as f:
            f.write(json.dumps(record) + "\n")
        raise RuntimeError(
            f"[TIMELINE] Alignment violation at entry {i}: "
            f"gap={gap_ms}ms ({violation}). See {ERROR_LOG}."
        )
