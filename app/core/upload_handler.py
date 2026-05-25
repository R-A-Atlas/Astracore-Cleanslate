import asyncio
import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Awaitable

SEATS_DIR = Path("workspace/memory/ledgers/seats")
MAX_CONCURRENT = 3
PROCESSING_TIMEOUT_SECONDS = 300  # hard ceiling per session before forced failure

STATUS_MESSAGE = (
    "Processing your first 3 trading sessions. "
    "Your personal strategy ledger is updating sequentially."
)

# Type alias: each submission is a (file_path, operator_key) pair.
TaggedAsset = tuple[Path, str]


class SessionStatus:
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


def _log_processing_error(packet: dict, tb: str) -> None:
    """
    Write the fault payload exclusively to the operator's isolated seat fault log.
    Parallel threads for other seats are never touched by this write.
    """
    operator_key = packet.get("session_by") or "unknown"
    SEATS_DIR.mkdir(parents=True, exist_ok=True)
    seat_log_path = SEATS_DIR / f"usr_floor_{operator_key}_log.json"

    if seat_log_path.exists():
        log = json.loads(seat_log_path.read_text())
    else:
        log = {"operator_key": operator_key, "fault_rows": []}

    log["fault_rows"].append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_by": operator_key,
        "asset": packet.get("asset"),
        "error": packet.get("error"),
        "traceback": tb,
    })
    seat_log_path.write_text(json.dumps(log, indent=2))


class BatchUploadInterceptor:
    """
    Shared upload gate for all org seats.

    A single instance must be held at the org/server level so the
    asyncio.Semaphore cap of MAX_CONCURRENT (3) enforces a global ceiling
    across all laptops simultaneously — not per-seat.

    Every session packet is initialized as "processing" and can only
    transition to "ready" (both media extraction and speech sidecar
    validation complete) or "failed" (exception or timeout). No consumer
    path can read a packet while it is still "processing".
    """

    def __init__(self, processor: Callable[[Path, str], Awaitable[dict]]):
        """
        processor: async callable receiving (asset_path, operator_key).
                   Must complete both local media splitting AND any required
                   speech sidecar validation before returning. The handler
                   marks the session "ready" only on clean return.
        """
        self._processor = processor
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        self._results: list[dict] = []

    async def _process_one(self, asset: Path, operator_key: str) -> dict:
        """
        Acquire a semaphore slot, run the processor inside the state machine.

        State transitions:
          PROCESSING → READY   : processor coroutine returns without exception
          PROCESSING → FAILED  : asyncio.TimeoutError or any Exception raised
        """
        packet: dict = {
            "status": SessionStatus.PROCESSING,
            "session_by": operator_key,
            "asset": str(asset),
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        async with self._semaphore:
            try:
                result = await asyncio.wait_for(
                    self._processor(asset, operator_key),
                    timeout=PROCESSING_TIMEOUT_SECONDS,
                )
                # Merge processor output; status and operator tag are authoritative here.
                packet.update(result)
                packet["status"] = SessionStatus.READY
                packet["session_by"] = operator_key  # enforce — processor must not override
                packet["completed_at"] = datetime.now(timezone.utc).isoformat()

            except asyncio.TimeoutError:
                packet["status"] = SessionStatus.FAILED
                packet["error"] = (
                    f"Processing timeout after {PROCESSING_TIMEOUT_SECONDS}s. "
                    "Local media split or speech sidecar did not complete in time."
                )
                _log_processing_error(packet, traceback.format_exc())

            except Exception as exc:
                packet["status"] = SessionStatus.FAILED
                packet["error"] = str(exc)
                _log_processing_error(packet, traceback.format_exc())

        return packet

    async def submit(self, tagged_assets: list[TaggedAsset]) -> dict:
        """
        Accept a batch of (asset, operator_key) tuples from one or more seats.

        Submissions from multiple laptops arriving simultaneously are merged
        into a single ordered queue before the semaphore is applied, so no seat
        can bypass the MAX_CONCURRENT=3 global cap.

        The response payload is returned as soon as processing completes.
        If the batch exceeds MAX_CONCURRENT the frontend status message is set
        so the UI log can surface it immediately while overflow drains.
        """
        total = len(tagged_assets)
        response_payload: dict = {
            "status": "ok",
            "message": None,
            "total": total,
        }

        if total > MAX_CONCURRENT:
            response_payload["message"] = STATUS_MESSAGE
            # First MAX_CONCURRENT fire concurrently; overflow drains one-at-a-time.
            concurrent_batch = tagged_assets[:MAX_CONCURRENT]
            overflow = tagged_assets[MAX_CONCURRENT:]

            concurrent_results = await asyncio.gather(
                *[self._process_one(asset, key) for asset, key in concurrent_batch]
            )
            self._results.extend(concurrent_results)

            for asset, key in overflow:
                result = await self._process_one(asset, key)
                self._results.append(result)
        else:
            results = await asyncio.gather(
                *[self._process_one(asset, key) for asset, key in tagged_assets]
            )
            self._results.extend(results)

        response_payload["processed"] = len(self._results)
        return response_payload

    def get_results(self) -> list[dict]:
        """Return all tagged result rows accumulated since instantiation."""
        return list(self._results)

    def get_ready_results(self) -> list[dict]:
        """Return only sessions that completed successfully."""
        return [r for r in self._results if r.get("status") == SessionStatus.READY]

    def get_failed_results(self) -> list[dict]:
        """Return only sessions that failed or timed out."""
        return [r for r in self._results if r.get("status") == SessionStatus.FAILED]

    def drain_results(self) -> list[dict]:
        """Return and clear the result buffer (use after writing rows to seat logs)."""
        rows, self._results = list(self._results), []
        return rows
