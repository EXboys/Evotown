# EvoTown Evolution Mechanism — Current State and Improvements

## 1. Core Requirement

> Need to emphasize agent evolution of skills, memory, rules, etc., not just task completion.  
> Is testing LLM effectiveness alone useful?

**Conclusion**: Evolution mechanism **exists**, but the current design **prioritizes task completion**; evolution is a side effect, and the economy **does not reward evolution**.

---

## 2. Existing Evolution Mechanism (SkillLite + EvoTown)

### 2.1 SkillLite Evolution Engine (Implemented)

`skilllite-evolution` evolves:

| Dimension | Content | Trigger |
|-----------|---------|---------|
| **rules** | planning rules (`rules.json`), examples | `meaningful >= 5` and `failures >= 2` or `replans >= 2` |
| **memory** | Memory retrieval enhancement | `meaningful >= 3` |
| **skills** | New skill generation, existing skill refinement | `meaningful >= 3` and `failures > 0` or `repeated_patterns > 0` |

Data source: agent execution `decisions` table (tool calls, success/failure, replans, etc.).

### 2.2 EvoTown Evolution Trigger (Implemented)

In `callbacks.on_task_done`:

```python
# Every interval_tasks (default 3) tasks trigger once
periodic = count % interval_tasks == 0
# Or: task failed + at least 2 tasks since last evolution
failure_trigger = on_fail and task_failed and (count - last_evolve) >= 2
should_evolve = periodic or failure_trigger
→ trigger_evolve(agent_id, agent_home)  # skilllite evolution run
```

### 2.3 Evolution Event Push (Implemented)

- `log_watcher` listens to `evolution.log`
- `skilllite evolution run` writes `rule_added`, `skill_generated`, `evolution_run`, etc.
- WebSocket pushes `evolution_event` to frontend
- Evolution timeline and Agent detail show evolution events

---

## 3. Problem: Evolution Not Rewarded by Economy

### 3.1 Judge Only Scores Task Completion

`judge.py` scoring dimensions:

- **completion**: Whether user intent was fulfilled
- **quality**: Answer quality
- **efficiency**: Tool call efficiency

→ Maps to `reward`: -5 ~ +10, **entirely based on task performance**.

### 3.2 Economy Does Not Reward Evolution

- Balance changes: accept fee, completion reward, failure penalty
- **No evolution rewards**: `rule_added`, `skill_generated`, `memory` updates do not affect balance

### 3.3 Elimination Only Looks at Balance

- `balance <= 0` → eliminated
- No matter how much evolution, many failures and depleted balance still lead to elimination

### 3.4 Result

- System essentially tests "can the LLM complete tasks"
- Evolution is a byproduct; no "evolution → survival/reward" positive loop
- Hard to form "evolve more → stronger → survive longer" selection pressure

---

## 4. Improvement Directions

### 4.1 Economy: Evolution Rewards (Recommended)

In `on_task_done` or evolution event callback:

- `rule_added` → +2 ~ +5
- `skill_generated` → +5 ~ +10
- `skill_refined` → +2 ~ +3
- `memory` update → +1 ~ +2

Implementation: `trigger_evolve` returns evolution result (or parse `evolution run --json`), add balance and broadcast in callbacks based on change type.

### 4.2 Judge: Add Evolution Dimension (Optional)

Add "did this task trigger evolution, evolution type" to Judge input:

- New dimension `evolution`: 0–10, measures evolution value from this task
- Or: give evolution weight in `total_score`, e.g. `0.7 * task_score + 0.3 * evolution_score`

### 4.3 More Aggressive Evolution Trigger

- Reduce `interval_tasks` from 3 to 2 or 1
- Trigger evolution sooner on failure (e.g. trigger on failure, no need to wait 2 tasks)

### 4.4 Dashboard: Evolution First

- In Agent list, highlight: rule count, skill count, recent evolution events
- Evolution timeline as main tab, alongside "task completion"
- Add "evolution contribution" metrics for comparing agent evolution

### 4.5 Elimination Logic: Consider Evolution (Advanced)

- Not only balance, but also evolution trend
- E.g.: agents with recent effective evolution (new rules/skills) get one elimination waiver, or slightly relaxed threshold

---

## 5. Summary

| Capability | Status | Suggestion |
|------------|--------|------------|
| Evolution engine (rules/memory/skills) | ✅ Exists | Keep |
| Evolution trigger | ✅ Exists (periodic + failure) | Can be more aggressive |
| Evolution event push | ✅ Exists | Keep |
| **Evolution economy reward** | ❌ None | **Implement first** |
| Judge evolution dimension | ❌ None | Optional |
| Dashboard evolution display | Basic | Can improve |

**Core change**: In `callbacks`, when `trigger_evolve` produces `rule_added`, `skill_generated`, etc., add balance and broadcast for that agent, making "evolution" a main survival/competition driver, not just a task-completion side effect.

---

## 6. Implemented Optimizations (2025-03)

| Change | Description |
|--------|-------------|
| **Evolution economy reward** | rule_added +3, example_added +2, skill_confirmed +8 (after manual confirm), skill_refined +3; skill_pending not rewarded |
| **Evolution trigger** | `interval_tasks` default 5, `failure_cooldown` default 3 (3 tasks before next failure trigger) |
| **Evolution reward config** | `evotown_config.json` `evolution.rewards` configurable per type |
| **Frontend balance sync** | `evolution_event` with `balance` updates store, Phaser labels sync |
| **Dashboard** | Agents with evolution events show ✨ in list |

---

## 7. Evolution Output Improvement Strategy (2025-03)

For "runs long but no skills/rules output":

| Strategy | Implementation |
|----------|----------------|
| **Lower evolution trigger threshold** | `interval_tasks` default 3→2, `failure_cooldown` 3→2; support `EVOTOWN_INTERVAL_TASKS`, `EVOTOWN_FAILURE_COOLDOWN` env vars |
| **Task design** | TASK_GEN_PROMPT requires "each task must have 2+ tools", forbid 0-tool pure-memory tasks |
| **Config example** | `evotown_config.json.example` provides full evolution config template |

**SkillLite side**: `meaningful` defined as `total_tools >= 2`; single-tool tasks do not accumulate. To relax further, change `crates/skilllite-evolution/src/lib.rs` SQL `total_tools >= 2` to `>= 1` (evaluate quality impact).

[中文版](../zh-CN/EVOLUTION_MECHANISM_ANALYSIS.md)
