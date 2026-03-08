# Evotown 日志分析报告 (2026-03-08)

## 一、问题概览

根据最新 evotown 运行日志，当前存在以下主要问题：

---

## 二、问题详情

### 1. 【严重】Judge LLM 返回非 JSON 导致评分失败

**现象：**
```
WARNING evotown.judge: Judge LLM returned non-JSON (attempt 1), raw=Here is the JSON requested:
WARNING evotown.judge: Judge LLM returned non-JSON (attempt 2), raw=Here is the JSON requested:
evotown.callbacks: [agent_11] judge: score=0 reward=-5 reason=
```

**原因：** 使用 `gemini-2.5-flash` 作为裁判模型时，模型返回了 `"Here is the JSON requested:"` 这类说明性前缀，而不是纯 JSON。虽然 `judge.py` 已有 `_JSON_PREFIX_PATTERN` 和 `_parse_judge_json` 做清洗，但可能：
- 模型返回内容被截断（completion=0）
- 正则/解析逻辑未覆盖当前 Gemini 输出格式

**影响：** 任务明明完成（如官渡之战模拟、Fibonacci 数列），却被判 0 分、reward=-5，导致忠诚度下降、队伍解散。

**建议：**
- 增强 `_parse_judge_json` 对 `"Here is the JSON requested:"` 后空内容的处理
- 或为 Judge 使用更稳定的 JSON 模式模型（如 qwen2.5:7b 本地模型）
- 检查 `response_format={"type": "json_object"}` 在 Gemini API 中的兼容性

---

### 2. 【严重】Unknown method: confirm 错误

**现象：**
```
event=error data={'message': 'Unknown method: confirm'}
ERROR evotown.process: [agent_12][stdout] error event: Unknown method: confirm
```

**原因：** 
- 进程管理端在收到 `confirmation_request` 时向 agent stdin 发送 `{"method": "confirm", "params": {"approved": true}}`
- agent-rpc 主循环只处理 `agent_chat` 和 `ping`，收到 `confirm` 时当作未知方法返回错误
- 时序问题：当 `inject_task`（agent_chat）先于某次 `confirm` 被写入 stdin 时，agent 的 confirmation 处理器会读到 `agent_chat` 而非 `confirm`，导致确认失败；随后主循环读到滞后的 `confirm`，报 Unknown method

**建议：** 在 `crates/skilllite-agent/src/rpc.rs` 主循环中增加对 `confirm` 的分支，收到时静默忽略（continue），避免当作错误处理。

---

### 3. 【中等】LLM 连续 3 次无进展后停止

**现象：**
```
WARN skilllite_agent::agent_loop::reflection: LLM failed to make progress after 3 attempts, stopping
```

**原因：** 规划模式下，`reflection.rs` 检测到 LLM 多次只输出文本、未调用工具或未推进任务计划，达到 `max_no_tool_retries` 后强制停止。

**影响：** Agent 在任务中途被终止，`task_completed=False`，即使部分工作已完成。

**可能诱因：**
- 任务描述与「任务预览」混淆（预览要求「不要调用任何工具」，正式任务又要求「Please use the available tools」）
- LLM 反复描述计划而不执行
- 任务列表解析失败导致计划异常

---

### 4. 【中等】任务列表解析失败

**现象：**
```
WARN skilllite_agent::task_planner: Failed to parse task list: expected value at line 1 column 1
event=task_plan data={'tasks': [{'completed': False, 'description': '【任务预览】搜索Fibonacci数列...', 'id': 1}]}
```

**原因：** 任务规划 LLM 返回了空字符串或非 JSON，`parse_task_list` 解析失败后回退为单任务，且描述被错误地设为「任务预览」全文。

**影响：** Agent 收到的任务描述包含「请回复 ACCEPT 或 REFUSE，不要调用任何工具」，与后续系统提示「Please use the available tools」矛盾，导致行为混乱。

---

### 5. 【中等】任务预览与正式任务描述混淆

**现象：** Agent 反复纠结「不要调用任何工具」与「Please use the available tools」的冲突。

**原因：** 当 `parse_task_list` 失败时，fallback 任务描述直接使用了预览消息，未替换为正式任务文本。

---

### 6. 【低】psutil 未安装，内存看门狗禁用

**现象：**
```
WARNING evotown.main: [watchdog] psutil not installed — memory watchdog disabled
```

**建议：** `pip install psutil` 以启用内存监控和看门狗。

---

### 7. 【低】agent-browser 超时 / 网络问题

**现象：**
- 百度搜索：`page.goto: Timeout 25000ms exceeded`
- Google 搜索：`net::ERR_ABORTED`

**影响：** 依赖网络搜索的任务可能失败，但 Agent 会 fallback 到其他方式（如直接写代码）。

---

## 三、修复优先级建议

| 优先级 | 问题 | 建议操作 |
|-------|------|----------|
| P0 | Judge 非 JSON | 增强 judge 解析逻辑，或更换 Judge 模型 |
| P0 | Unknown method: confirm | 在 agent-rpc 中静默处理 `confirm` |
| P1 | 任务预览/正式任务混淆 | 修正 task_planner fallback 时的描述来源 |
| P1 | LLM 无进展停止 | 优化 reflection 策略或增加重试/提示 |
| P2 | psutil | 安装 psutil |
| P2 | agent-browser 超时 | 调整超时或使用备用搜索策略 |

---

## 四、相关代码位置

- Judge: `evotown/backend/judge.py`, `evotown/backend/llm_client.py`
- Agent RPC: `crates/skilllite-agent/src/rpc.rs`
- Reflection: `crates/skilllite-agent/src/agent_loop/reflection.rs`
- Task Planner: `crates/skilllite-agent/src/task_planner.rs`
- Process Manager: `evotown/backend/process_manager.py`
