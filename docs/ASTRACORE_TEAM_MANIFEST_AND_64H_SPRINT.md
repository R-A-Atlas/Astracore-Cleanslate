# AstraCore Team Manifest + 64h Study Sprint Packet

## Chain of Command (order of importance)
1. **R.A. (Roberto Avila)** — Founder / Owner / Master Admin Architect
2. **Elias Vega** — Chief of Operations (global orchestrator)
3. **Mira Solen** — CMO (growth, messaging, content systems)
4. **Mateo Cruz** — Chief Strategy Analyst (fulfillment + behavioral analysis)
5. **Diego Ramos** — CTO / Implementation Systems (architecture, reliability, sandbox)
6. **Sofía Rivera** — CDO (asset vault, structured deliverables, data discipline)
7. **Nolan Voss** — CXO (Jarvis consult experience, front-facing response quality)
8. **Devin Kross** — CKO (research acceleration, learning maps, knowledge ops)
9. **Enzo Varek** — CISO + Head of QA (security gates, red-team checks, integrity walls)
10. **Val Noor** — CPO (product opportunities, macro signal packaging)

## Role Summaries
- **Elias:** converts founder intent into execution sequence and control.
- **Mira:** grows demand via clear positioning, website copy angles, social content.
- **Mateo:** extracts behavioral and strategic signal from sessions/evidence.
- **Diego:** hardens system paths, reliability, and implementation quality.
- **Sofía:** transforms findings into polished, structured client assets.
- **Nolan:** manages high-quality consult interaction and user-facing clarity.
- **Devin:** runs deep study loops and converts learning into usable team guidance.
- **Enzo:** secures runtime, validates integrity, enforces QA evidence gates.
- **Val:** turns aggregate signals into roadmap priorities and product packaging.

## 64-Hour Study Sprint Directive
- Runner: **Devin profile**
- Cadence: **every 1 hour for 64 cycles**
- Output root: `/root/AstraCore/research/devin_64h/`
- Prompt file: `docs/DEVIN_64H_STUDY_SPRINT_PROMPT.md`

## Optional scheduler command (run when token/auth is ready)
```bash
hermes --profile devin chat -q "Load and execute prompt from /root/AstraCore/Astracore-Cleanslate/docs/DEVIN_64H_STUDY_SPRINT_PROMPT.md"
```

## Telegram token wiring (new agents)
Use these variable names in each profile `.env`:
- `ENZO_TELEGRAM_BOT_TOKEN`
- `DEVIN_TELEGRAM_BOT_TOKEN`
- `VAL_TELEGRAM_BOT_TOKEN`

Mapped runtime key required by Hermes gateway:
- `TELEGRAM_BOT_TOKEN=<agent_specific_token>`

Never paste tokens in chat. Paste only in VPS terminal.
