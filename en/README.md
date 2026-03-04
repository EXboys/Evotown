# Evotown — Evolution Testing Platform

Puts evolution engines (e.g. SkillLite) in a controlled environment for **evolution effect validation**. Economy rules are configurable, reproducible, fully local, and **do not depend on virtual/cryptocurrency**.

[中文](../zh-CN/README.md)

## Prerequisites

- SkillLite installed (`skilllite evolution run`, `skilllite agent-rpc` available)
- Python 3.10+
- Node.js 18+
- Backend must run in a directory containing `.skills` or `skills`; each agent gets a copy at `~/.skilllite/arena/{agent_id}/.skills` for isolated evolution artifacts

## Quick Start

### 1. Start Backend

```bash
cd evotown/backend
pip install -r requirements.txt
python main.py
# or: uvicorn main:app --host 0.0.0.0 --port 8765
```

### 2. Start Frontend

```bash
cd evotown/frontend
npm install
npm run dev
```

Visit http://localhost:5174

## Economy Rules (Jungle Law)

Configurable via `evotown_config.json` or environment variables:

| Config | Default | Env Var |
|--------|---------|---------|
| initial_balance | 100 | EVOTOWN_INITIAL_BALANCE |
| cost_accept | -5 | EVOTOWN_COST_ACCEPT |
| reward_complete | 10 | EVOTOWN_REWARD_COMPLETE |
| penalty_fail | -5 | EVOTOWN_PENALTY_FAIL |
| eliminate_on_zero | true | EVOTOWN_ELIMINATE_ON_ZERO |

Query current config via `GET /config/economy`.

## Directory Structure

```
evotown/
├── backend/              # FastAPI backend
│   ├── main.py           # API + WebSocket
│   ├── economy_config.py # Economy rules config
│   ├── evotown_config.json  # Editable rules (optional)
│   ├── process_manager.py
│   ├── sqlite_reader.py
│   └── ...
├── frontend/         # React + Phaser 3 frontend
│   └── src/
├── docs/
│   ├── en/           # English docs
│   └── zh-CN/        # 中文文档
└── README.md
```

## Release Notes

Evotown is developed inside the skillLite repo; **it is split into a separate repo on release** (e.g. `evotown` / `evotown-org/evotown`).

```bash
# Split example
git subtree split -P evotown -b evotown-main
```

## Related Docs

- [REWARD_MECHANISM.md](../docs/en/REWARD_MECHANISM.md) — Reward mechanism
- [AGENT_TASK_ACCEPTANCE_ANALYSIS.md](../docs/en/AGENT_TASK_ACCEPTANCE_ANALYSIS.md) — Agent task acceptance logic
- [EVOLUTION_MECHANISM_ANALYSIS.md](../docs/en/EVOLUTION_MECHANISM_ANALYSIS.md) — Evolution mechanism
- [13-EVOLUTION-ARENA.md](../../todo/13-EVOLUTION-ARENA.md) — Full design
- [12-SELF-EVOLVING-ENGINE.md](../../todo/12-SELF-EVOLVING-ENGINE.md) — Evolution engine
