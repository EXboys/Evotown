# EvoTown Reward Mechanism — Overview

## 1. Balance Change Sources

| Trigger | Change | Config Source | Description |
|---------|--------|---------------|-------------|
| **Accept task** | -3 | economy.cost_accept | Two-phase: fee deducted when agent accepts task |
| **Task complete** | -5 ~ +5 | judge internal mapping | Determined by Judge score |
| **Evolution event** | +2 ~ +8 | evolution.rewards | rule_added, skill_confirmed, etc. |
| **Elimination** | — | balance ≤ 0 | Agent removed when balance hits zero |

---

## 2. Task Rewards (Judge)

### 2.1 Flow

```
Task complete (on_task_done)
  → judge_task(task, response, tool_total, tool_failed)
  → JudgeResult.reward  # Internal mapping, does not read economy config
  → arena.add_balance(agent_id, judge_result.reward)
```

### 2.2 Judge Scoring Dimensions

- **completion** (0–10): Whether user intent was fulfilled
- **quality** (0–10): Answer quality
- **efficiency** (0–10): Tool call efficiency  
- **total_score** = completion + quality + efficiency (0–30)

### 2.3 Judge → Reward Mapping (hardcoded)

| total_score | reward |
|-------------|--------|
| 0–5 | -5 |
| 6–10 | 0 |
| 11–20 | +3 |
| 21–30 | +5 |

### 2.4 Fast Path (no LLM call)

- All tools failed → reward = -5
- Empty response → reward = -5
- Judge timeout → estimate score from tool success rate, then map to reward

### 2.5 Potential Issues

**Economy vs Judge inconsistency**:

- `_format_arena_context` tells agent: `Success: +{reward_complete}, Fail: {penalty_fail}` (default +10 / -5)
- Actual reward comes from Judge's `JudgeResult.reward` (-5 / 0 / +5 / +10)
- Success may yield +5 or +10, failure may yield -5 or 0; does not fully match agent-facing text

---

## 3. Evolution Rewards

### 3.1 Flow

```
skilllite evolution run
  → Writes evolution.log (rule_added, skill_confirmed, etc.)
  → log_watcher detects
  → broadcast_evolution_event(data)
  → Look up evolution.rewards by event_type
  → arena.add_balance(agent_id, reward)
  → WS push evolution_event (with balance)
```

### 3.2 Evolution Reward Config (evolution.rewards)

| event_type | Default reward | Description |
|------------|----------------|-------------|
| rule_added | +5 | New planning rule |
| example_added | +3 | New few-shot example |
| skill_confirmed | +12 | After manual confirm |
| skill_refined | +5 | Skill refinement |
| skill_pending | +4 | New skill from evolution (pending confirm) |

### 3.3 Config Path

- `evotown_config.json` → `evolution.rewards`
- Example: `evotown_config.json.example`

---

## 4. Task Acceptance Fee (Two-phase)

### 4.1 Flow

```
dispatch_inject(agent_id, task, difficulty)
  Phase 1: preview_task → agent returns ACCEPT/REFUSE
  Phase 2: If ACCEPT → inject_task
    → arena.add_balance(agent_id, cost_accept)  # Negative
    → arena.set_in_task(agent_id, True)
```

### 4.2 Config

- `economy.cost_accept`: Default -5 (5 deducted when accepting task)

---

## 5. Elimination Logic

- `economy.eliminate_on_zero`: Default true
- When `balance <= 0`: Remove agent, kill process, WS push agent_eliminated

---

## 6. Config Summary

### economy (evotown_config.json)

```json
{
  "economy": {
    "initial_balance": 100,
    "cost_accept": -5,
    "reward_complete": 10,   // ⚠️ Only for agent display, Judge does not read
    "penalty_fail": -5,      // ⚠️ Only for agent display, Judge does not read
    "eliminate_on_zero": true
  }
}
```

### evolution.rewards

```json
{
  "evolution": {
    "rewards": {
      "rule_added": 5,
      "example_added": 3,
      "skill_confirmed": 12,
      "skill_refined": 5,
      "skill_pending": 4
    }
  }
}
```

---

## 7. Issues and Improvement Directions

| Issue | Suggestion |
|-------|------------|
| **Judge vs economy mismatch** | Have Judge use `reward_complete` / `penalty_fail`, or unify arena context text |
| **Judge mapping too coarse** | Use continuous mapping or more tiers (e.g. 0–30 → -5 ~ +15) |
| **No evolution reward cap** | Add daily/single-evolution cap to prevent farming |
| **Difficulty not in reward** | Give higher reward for hard task success |
| **Timeout penalty** | Timeout goes to on_task_done, currently same as failure (Judge gives low score) |

[中文版](../zh-CN/REWARD_MECHANISM.md)
