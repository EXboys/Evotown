# EvoTown Agent Task Acceptance Logic — Analysis and Design

## 1. Problem Statement

Current EvoTown has these issues:

1. **No agent choice**: After TaskDispatcher selects an idle agent, it injects the task and **immediately deducts fee and marks in_task**. The agent has no chance to decide whether to accept.
2. **Aimless wandering**: Agents cannot make rational decisions based on capability, balance, or task difficulty, leading to blind acceptance, high failure rate, and elimination when balance runs out.
3. **Low evolution efficiency**: Without "selective acceptance", it is hard to form a "act within ability, evolve steadily" strategy.

---

## 2. Current State

### 2.1 Current Task Dispatch Flow

```
TaskDispatcher._tick()
  → get_idle_agents()
  → _pick_task_for_agent(agent_id)  # Pick task by difficulty balance
  → inject_fn(agent_id, task_text, difficulty)  # dispatch_inject
      → process_mgr.inject_task(agent_id, task)   # ⚠️ context not passed!
      → arena.add_balance(agent_id, -cost_accept) # Immediate deduction
      → arena.set_in_task(agent_id, True)        # Immediate in-task mark
```

**Findings**:

| Component | Status | Issue |
|-----------|--------|-------|
| `callbacks._format_arena_context` | Implemented: balance, cost, reward, penalty, difficulty | Design correct |
| `callbacks.dispatch_inject` | Passes `context=context` | Correct |
| `process_manager.inject_task` | **Signature only `(agent_id, task)`, does not receive context** | context dropped |
| `process_manager` request body | Only `message`, `session_key`, `skill_dirs`, `config` | No `context.append` |
| SkillLite RPC protocol | Docs support `context.append` | General capability |
| `rpc.handle_agent_chat` | **Does not parse `params.context`** | Not implemented |
| `AgentConfig.context_append` | Missing in type def (compile error) | Incomplete |
| `prompt.build_system_prompt` | No `context_append` param | Not appended |
| `ARENA_SOUL_TEMPLATE` | **Not defined** | `process_manager._ensure_agent_structure` will NameError |

### 2.2 Design Intent vs Reality

`_format_arena_context` text clearly states:

> "Only proceed if you believe you can complete this task. If not, reply with a short refusal and do not use tools."

So the design expects agents to perceive rules and refuse, but:

1. **Context never reaches the agent**; agent cannot see balance, cost, reward.
2. **Fee is deducted on inject success**; even if agent replies "I refuse", fee is already taken.
3. **SOUL template missing**; Arena identity/boundaries are not written.

---

## 3. SkillLite vs EvoTown Boundary (Important)

### 3.1 Principle

- **SkillLite**: General agent engine, **no game/arena concepts**.
- **EvoTown**: Game logic, Arena rules, economy, evolution, elimination — all on evotown side.

### 3.2 Belongs in SkillLite (General Logic)

| Capability | Description | Game-related? |
|------------|-------------|---------------|
| RPC `context.append` | Caller injects extra system prompt fragment | No, general |
| `AgentConfig.context_append` | Append to system prompt at runtime | No, general |
| SOUL loading | From `--soul` / `.skilllite/SOUL.md` | No, general |
| Two-phase "preview-confirm" protocol | If designed as general "return decision then execute" | TBD |

### 3.3 Belongs in EvoTown (Game Logic)

| Capability | Description |
|------------|-------------|
| Arena rule text | `_format_arena_context` balance, cost, reward, penalty |
| Arena SOUL template | `ARENA_SOUL_TEMPLATE`, defines arena agent identity and boundaries |
| Two-phase task dispatch | Send "task preview" → agent returns accept/reject → then deduct fee and execute |
| Per-agent soul customization | Different personality, risk preference (conservative/aggressive) |
| Task pool, difficulty balance, judge, evolution trigger | All game logic |

### 3.4 Conclusion

- **SkillLite only provides "injectable context"**; it does not know Arena, balance, or task difficulty.
- **EvoTown is responsible for**: Building context content, defining SOUL template, implementing two-phase dispatch, handling state updates after accept/reject.

---

## 4. Design Options

### 4.1 Option A: Minimal Change (Pass context only, no flow change)

**Idea**: Pass Arena context to the agent so it sees rules in system prompt. Agent can still "refuse" (text reply, no tools), but **fee is still deducted at inject**.

**SkillLite changes** (general):

1. Add `context_append: Option<String>` to `AgentConfig`.
2. Add `context_append` param to `prompt::build_system_prompt`, append to end.
3. Parse `params.context.append` in `rpc::handle_agent_chat`, set `config.context_append`.
4. Support `context_append` in `planning.rs` task-planning path.

**EvoTown changes**:

1. Define `ARENA_SOUL_TEMPLATE` constant.
2. Change `process_manager.inject_task(agent_id, task, context=None)` to accept context, write to request `context.append`.

**Pros**: Small change, agent at least sees rules.  
**Cons**: Fee still deducted on refuse; logic imperfect.

---

### 4.2 Option B: Two-phase Task Dispatch (Recommended) ✅ Implemented

**Idea**: Send "task preview" first; agent returns accept/reject; **only deduct fee and execute on accept**.

**Flow**:

```
Phase 1 — Preview
  EvoTown sends agent_chat, message = "【Task Preview】{task}\nReply ACCEPT or REFUSE with brief reason."
  context.append = _format_arena_context(...)
  → Agent returns text only, no tools

Phase 2 — Decision
  EvoTown parses reply; if REFUSE/reject → return task to pool, no fee
  If ACCEPT → deduct fee, set_in_task, send agent_chat again to execute
```

**Implementation**:
- `process_manager.preview_task()`: Send preview, wait for done event, parse ACCEPT/REFUSE
- `callbacks.dispatch_inject`: Call preview_task first; on refuse → `return_task_to_pool`; on accept → inject_task
- `task_dispatcher.return_task_to_pool()`: Return task to pool

---

### 4.3 Option C: Per-agent Soul Customization (Advanced) ✅ Implemented

**Idea**: Different agents have different "personality" and risk preference, affecting acceptance strategy.

**Implementation**:
- `ARENA_SOUL_TEMPLATES`: conservative, aggressive, balanced
- When creating agent, optionally choose soul_type; on spawn write template to `agent_home/SOUL.md`
- Agent detail page: Soul tab for view, edit, save

---

## 5. Recommended Implementation Order

1. **Fix base capability (SkillLite general)**
   - Complete `context_append` support (AgentConfig, prompt, rpc, planning).
   - Align RPC protocol docs with implementation.

2. **Fix EvoTown integration**
   - Define `ARENA_SOUL_TEMPLATE`.
   - Change `inject_task` to accept and pass context.

3. **Implement two-phase dispatch (EvoTown)**
   - Add `preview_task`, change `dispatch_inject` flow.

4. **Optional: Soul customization**
   - Generate different Soul variants per agent for differentiation and evolution.

---

## 6. Summary Table

| Change | Owner | General? |
|--------|-------|----------|
| `AgentConfig.context_append` | SkillLite | Yes |
| `build_system_prompt` append context | SkillLite | Yes |
| RPC parse `params.context.append` | SkillLite | Yes |
| `ARENA_SOUL_TEMPLATE` | EvoTown | No, game |
| `inject_task` pass context | EvoTown | No, game |
| Two-phase preview → inject | EvoTown | No, game |
| Per-agent Soul customization | EvoTown | No, game |

**Core principle**: SkillLite only provides "inject arbitrary context"; Arena rules, task acceptance logic, and Soul templates are all implemented in EvoTown.

[中文版](../zh-CN/AGENT_TASK_ACCEPTANCE_ANALYSIS.md)
