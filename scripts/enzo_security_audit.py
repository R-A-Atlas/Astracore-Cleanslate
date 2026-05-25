#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/root/AstraCore/Astracore-Cleanslate')
LOG_ROOT = Path('/root/AstraCore/logs/enzo_security')
LOG_ROOT.mkdir(parents=True, exist_ok=True)

now = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
report = {
    'timestamp': now,
    'checks': {},
    'status': 'ok',
}

# C-02 ledger integrity hints
ledger_targets = [
    ROOT / 'app/core/ledger.py',
    ROOT / 'app/server/session_store.py',
    ROOT / 'app/intel/store.py',
]
mutex_hits = 0
atomic_hits = 0
for p in ledger_targets:
    if not p.exists():
        continue
    txt = p.read_text()
    mutex_hits += txt.count('Lock(') + txt.count('asyncio.Lock')
    atomic_hits += txt.count('os.replace') + txt.count('.replace(')
report['checks']['ledger_integrity'] = {
    'targets': [str(p) for p in ledger_targets],
    'mutex_signal_hits': mutex_hits,
    'atomic_signal_hits': atomic_hits,
}

# C-03 compiler sandbox presence
sandbox = ROOT / 'app/core/compiler_sandbox.py'
sandbox_text = sandbox.read_text() if sandbox.exists() else ''
report['checks']['compiler_sandbox'] = {
    'path': str(sandbox),
    'exists': sandbox.exists(),
    'has_gate_entrypoint': 'def gate(' in sandbox_text,
    'has_violation_log': '_log_violation' in sandbox_text,
}

# C-01 prompt eval placeholder (manual/automated runner can fill this later)
report['checks']['prompt_eval'] = {
    'status': 'pending_runner',
    'note': 'Attach adversarial eval runner output here.'
}

out = LOG_ROOT / f'enzo_security_audit_{now}.json'
out.write_text(json.dumps(report, indent=2))
print(str(out))
