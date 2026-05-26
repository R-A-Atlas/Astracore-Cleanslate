# Hermes/Agents Upgrade Plan — R.A. Omega v2.1

Date: 2026-05-25
Scope: Hermes orchestration layer for AstraCore OS execution reliability

## 1) Objective
Turn Hermes into a disciplined multi-agent execution fabric that can build and operate AstraCore safely under long-session ingest pressure.

## 2) Non-Negotiables
1. No blind autonomous edits outside assigned lane.
2. Atomic writes for all ledger/fault/session mutations.
3. Org-scoped lock discipline for multi-seat commit moments.
4. RAM-spike prevention for upload/processing paths.
5. Every agent output must carry verification evidence.

---

## 3) Hermes Profile Topology

### Primary profiles
- `default` → Elias Orchestrator (control plane)
- `researchassistant` → Mateo (research/policy lane)
- `diego` → implementation systems/reliability lane
- `nolan` → tests/quality lane
- `mira` → messaging/docs alignment lane
- `sofia` → client-facing language alignment lane

### Commands
```bash
hermes profile list
hermes profile show default
```

If missing profiles, create:
```bash
hermes profile create diego
hermes profile create nolan
hermes profile create mira
hermes profile create sofia
```

---

## 4) Toolset Boundaries (least privilege)

### Elias (orchestrator)
- enabled toolsets: `delegation,file,terminal,todo,session_search,skills,cronjob`

### Diego (implementation)
- enabled toolsets: `file,terminal,todo,skills`

### Nolan (testing)
- enabled toolsets: `file,terminal,todo,skills`

### Mateo (research/policy)
- enabled toolsets: `web,search,file,todo,skills`

### Mira/Sofía (docs/comms)
- enabled toolsets: `file,todo,skills`

Apply interactively per profile:
```bash
hermes --profile diego tools
hermes --profile nolan tools
hermes --profile researchassistant tools
```

---

## 5) Routing + Concurrency Policy

## Control policy
- Global orchestrator: Elias only.
- Worker agents cannot spawn nested workers by default.
- Max parallel children at a time: 3.
- For high-risk file mutation phases, run 1 lane at a time.

## Suggested config keys
```yaml
delegation:
  max_concurrent_children: 3
  max_spawn_depth: 1
  orchestrator_enabled: true
```

Set via CLI:
```bash
hermes config set delegation.max_concurrent_children 3
hermes config set delegation.max_spawn_depth 1
hermes config set delegation.orchestrator_enabled true
```

---

## 6) Ledger Context Sync Standard

Since v2.1 spec requires tight ledger-context routing, enforce context injection convention in task prompts:
- include `org_id`
- include `operator_key`
- include exact target ledger path(s)
- include allowed mutation files

Prompt template fragment for all worker tasks:
```text
Context lock:
- org_id: <ORG>
- operator_key: <OP>
- allowed files: <list>
- forbidden files: everything else
- mutation rule: atomic tmp+replace only
```

---

## 7) Atomic Commit & Mutex Standard (Hermes-side policy)

Agent policy requirements:
1. Never direct-write JSON ledgers without tmp+replace.
2. Any org-level read-modify-write must be inside org lock block.
3. Seat/fault logs follow same atomic discipline (currently partial gap).
4. Stop-commit path must verify drift alignment before summary persist.

These become mandatory review checks in every commit message body.

---

## 8) Background/Cron Usage Policy

Use cron only for:
- periodic status digests
- watchdog checks
- non-interactive health tasks

Do NOT use cron for active code mutation loops.

Example watchdog (daily status):
```bash
hermes cron create "0 9 * * *" --name "astracore-daily-ops" \
  --prompt "Check /ops/metrics patterns and summarize anomalies for R.A."
```

---

## 9) Execution Board Mapping (from Gap Audit)

### Lane A (Diego)
- streamed upload writer in `/api/upload/part`
- remove full-buffer `await file.read()` path

### Lane B (Diego + Nolan)
- wire `verify_timeline_alignment()` gate into stop-commit
- atomic seat/fault log writes

### Lane C (Nolan)
- add tests for upload, drift gate, stop-commit integrity

### Lane D (Mateo)
- finalize tier constants (retail/team) from business policy

### Lane E (Mira/Sofía)
- UI/docs alignment after backend truth lock

---

## 10) Command Pack (operator runbook)

## Preflight
```bash
hermes doctor
hermes config check
hermes status --all
```

## During sprint
```bash
python -m compileall app
pytest -q
```

## After merge block
```bash
git status --short
git log --oneline -n 10
```

---

## 11) Definition of Done (Hermes upgrade phase)

This phase is complete when:
1. Profile topology is present and validated.
2. Tool boundaries are enforced per worker role.
3. Delegation/concurrency keys are set.
4. Execution board lanes are assigned.
5. Next sprint tasks are queued with verification criteria.

Current state: 3/5 done (board + policy + runbook prepared). Remaining are live profile/config verification and assignment execution.
