"""文言文每日战报服务 — 读取执行日志，用 LLM 生成史记体战报

输出文件：evotown/backend/chronicle/YYYY-MM-DD.json
触发方式：
  - 手动：POST /chronicle/generate
  - 自动：main.py lifespan 每日 00:05 CST 定时任务
"""
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("evotown.chronicle")

_CHRONICLE_DIR = Path(__file__).parent.parent / "data" / "chronicle"
_TASK_HISTORY_PATH = Path(__file__).parent.parent / "task_history.jsonl"
_EXEC_LOG_PATH = Path(__file__).parent.parent / "execution_log.jsonl"
_CST = timezone(timedelta(hours=8))


# ── 日期工具 ───────────────────────────────────────────────────────────────────

_TIANGAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
_DIZHI   = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
_LUNAR_MONTHS = ["正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "冬", "腊"]


def _ganzhi_year(year: int) -> str:
    """公历年 → 干支纪年，如 2026 → 丙午年"""
    return _TIANGAN[(year - 4) % 10] + _DIZHI[(year - 4) % 12] + "年"


def _approx_lunar_month(month: int) -> str:
    """公历月份 → 近似农历月份名（偏移约一个月）"""
    lunar_idx = (month - 2) % 12  # 粗略偏移
    return _LUNAR_MONTHS[lunar_idx] + "月"


def _chinese_date_desc(date_str: str) -> str:
    """返回丰富的中式日期描述，供 prompt 使用
    例：丙午年二月初四（公元2026年3月4日）
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    gz = _ganzhi_year(dt.year)
    lunar_m = _approx_lunar_month(dt.month)
    # 农历日粗估（公历日 - 1，范围 初一~三十）
    lunar_day_num = max(1, dt.day - 1)
    if lunar_day_num == 1:
        lunar_d = "初一"
    elif lunar_day_num <= 10:
        lunar_d = f"初{['一','二','三','四','五','六','七','八','九','十'][lunar_day_num-1]}"
    elif lunar_day_num == 20:
        lunar_d = "二十"
    elif lunar_day_num < 20:
        lunar_d = f"十{['一','二','三','四','五','六','七','八','九'][lunar_day_num-11]}"
    else:
        lunar_d = f"二十{['一','二','三','四','五','六','七','八','九',''][lunar_day_num-21] if lunar_day_num <= 29 else '九'}"
    return f"{gz}{lunar_m}{lunar_d}（公元{dt.year}年{dt.month}月{dt.day}日）"


def today_cst() -> str:
    return datetime.now(_CST).strftime("%Y-%m-%d")


def prev_day_cst() -> str:
    return (datetime.now(_CST) - timedelta(days=1)).strftime("%Y-%m-%d")


def _day_bounds(date_str: str) -> tuple[float, float]:
    d = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=_CST)
    return d.timestamp(), (d + timedelta(days=1)).timestamp()


# ── 数据加载 ───────────────────────────────────────────────────────────────────

def _load_jsonl_for_date(path: Path, date_str: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    start, end = _day_bounds(date_str)
    records: list[dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                    ts = r.get("ts", 0.0)
                    if start <= ts < end:
                        records.append(r)
                except json.JSONDecodeError:
                    continue
    except OSError as e:
        logger.warning("chronicle: load %s failed: %s", path.name, e)
    return records


def _find_latest_date_with_data() -> str | None:
    """扫描 task_history.jsonl，返回有 claimed 记录的最近一天（CST，YYYY-MM-DD）。"""
    if not _TASK_HISTORY_PATH.exists():
        return None
    dates: set[str] = set()
    try:
        with open(_TASK_HISTORY_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                    if r.get("outcome") != "claimed":
                        continue
                    ts = r.get("ts", 0.0)
                    if ts:
                        dt = datetime.fromtimestamp(ts, tz=_CST)
                        dates.add(dt.strftime("%Y-%m-%d"))
                except (json.JSONDecodeError, ValueError, OSError):
                    continue
    except OSError:
        return None
    return max(dates) if dates else None


# 用于 agent_id 无法解析时的确定性名字池（哈希取模）
_FALLBACK_NAME_POOL = [
    "赵子龙", "关云长", "张翼德", "马孟起", "黄汉升",
    "魏文长", "姜伯约", "邓士载", "钟士季", "夏侯元让",
    "徐公明", "张文远", "于文则", "乐文谦", "李典李曼成",
    "孙仲谋", "周公瑾", "鲁子敬", "吕子明", "陆伯言",
]


def _resolve_name(agent_id: str, name_map: dict[str, str]) -> str:
    """将 agent_id 解析为武将名：
    1. name_map 有真实名字（且不等于 id）→ 直接用
    2. 否则用 MD5 哈希从名字池确定性派生（同 ID 永远同名）
    """
    name = name_map.get(agent_id, "")
    if name and name != agent_id:
        return name
    idx = int(hashlib.md5(agent_id.encode()).hexdigest(), 16) % len(_FALLBACK_NAME_POOL)
    return _FALLBACK_NAME_POOL[idx]


def _load_eliminated_name_map() -> dict[str, str]:
    """从 eliminated_agents.jsonl 加载历史 agent_id → display_name 映射（补充已淘汰 agent 的名字）"""
    try:
        from infra.eliminated_agents import load_eliminated
        return {r["agent_id"]: r["display_name"] for r in load_eliminated() if r.get("agent_id") and r.get("display_name")}
    except Exception:
        return {}


def _build_daily_summary(
    date_str: str,
    agent_name_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """汇总指定日期战场数据；agent_name_map 用于将 agent_id 映射为三国武将名"""
    tasks = [r for r in _load_jsonl_for_date(_TASK_HISTORY_PATH, date_str) if r.get("outcome") == "claimed"]
    exec_logs = _load_jsonl_for_date(_EXEC_LOG_PATH, date_str)
    # 合并：活跃 agent 优先，已淘汰 agent 名字作为补充（保证历史数据也能显示武将名）
    name_map = {**_load_eliminated_name_map(), **(agent_name_map or {})}

    # Per-agent 统计
    agent_stats: dict[str, dict[str, Any]] = {}

    def _agent(aid: str) -> dict[str, Any]:
        if aid not in agent_stats:
            agent_stats[aid] = {
                "agent_id": aid,
                "display_name": _resolve_name(aid, name_map),
                "completed": 0, "failed": 0, "total_reward": 0,
                "best_task": "", "best_score": -999, "judge_reasons": [],
            }
        return agent_stats[aid]

    for r in tasks:
        aid = r.get("agent_id", "")
        s = _agent(aid)
        judge = r.get("judge") or {}
        reward = judge.get("reward", 0)
        score = judge.get("total_score", 0)
        reason = (judge.get("reason") or "").strip()
        success = r.get("success", False)
        if success:
            s["completed"] += 1
        else:
            s["failed"] += 1
        s["total_reward"] += reward
        if score > s["best_score"]:
            s["best_score"] = score
            s["best_task"] = r.get("task", "")
        if reason and len(reason) > 20:
            s["judge_reasons"].append(reason[:200])

    refusals: dict[str, int] = {}
    for r in exec_logs:
        if r.get("status") == "refused":
            aid = r.get("agent_id", "")
            refusals[aid] = refusals.get(aid, 0) + 1

    ranking = sorted(agent_stats.values(), key=lambda x: x["total_reward"], reverse=True)
    highlights = [
        {
            "display_name": name_map.get(r.get("agent_id", ""), r.get("agent_id", "")),
            "task": r.get("task", ""),
            "success": r.get("success", False),
            "reason": (r.get("judge") or {}).get("reason", "")[:300],
        }
        for r in tasks if len((r.get("judge") or {}).get("reason", "")) > 30
    ][:5]

    return {
        "date": date_str,
        "total_tasks": len(tasks),
        "total_completed": sum(1 for r in tasks if r.get("success")),
        "total_failed": sum(1 for r in tasks if not r.get("success")),
        "agent_stats": ranking,
        "refusals_by_agent": refusals,
        "highlights": highlights,
    }


# ── Prompt 工程 ────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """你是《孔明进化小镇志》的章回体说书人。

【世界观】
孔明进化小镇，乃一方奇异天地。镇中谋士皆非凡人，各自怀抱绝学，日日在孔明军师所设擂台上领命征战、切磋智勇、积累军功、优胜劣汰。此小镇如同一部正在演进的活史书，强者晋升，弱者淘汰，循环往复，生生不息。

【笔法要求】
- 仿《三国演义》章回体笔法，开篇气势磅礴，如「话说天下大势，分久必合，合久必分」一般引人入胜；
- 开篇必须使用干支纪年（如丙午年、丁未年），配合农历月日，禁止直接写"公元xxxx年x月x日"；
- 日期表述要多样化，可用「时值丙午年仲春」「丙午年二月初四」「是岁丙午，春寒料峭」等，切忌千篇一律；
- 将小镇的每日擂台征战，写成王朝兴衰、群雄逐鹿式的宏大叙事，让读者感受到这是一部关于智慧生命演化的史诗；
- 全文三段：①以宏观视角写当日擂台大势与时令氛围；②重点描写两三位核心人物的征战经过（胜者如何运筹帷幄，败者如何折戟沉沙）；③「正是：」引出押韵七字对联收尾；
- 用「军令」代替「任务」、「告捷」代替「成功」、「兵败」代替「失败」、「军功」代替「积分」；
- 武将名直接用，禁用 agent_id 或任何英文标识符；
- 正文 500-650 字，段落间空一行，精炼有力。

禁止：括号、markdown 符号（#/*/-/```）、AI/LLM/机器学习/算法等现代词汇、重复叙述同一事件、直接写公历年月日。"""


def _build_prompt(summary: dict[str, Any]) -> str:
    date = summary["date"]
    chinese_date = _chinese_date_desc(date)
    no_data = summary["total_tasks"] == 0

    lines = [
        f"以下是孔明进化小镇【{chinese_date}】的擂台战报数据，请据此生成章回体志书：\n",
        f"当日军令总数：{summary['total_tasks']}，告捷：{summary['total_completed']}，兵败：{summary['total_failed']}\n",
    ]
    if no_data:
        lines.append(
            "【特别说明】此日擂台无任何战报记录，属难得的无战之日。"
            "请以此为题，以章回体笔法写擂台寂静之日——或写谋士养精蓄锐、或写孔明军师闭关思量大计，"
            "约 500-600 字，结尾以「正是：」收束押韵对联。"
        )
    if summary["agent_stats"]:
        lines.append("【谋士军功排行（直接用武将名写入正文，禁止 agent_id）】")
        for i, s in enumerate(summary["agent_stats"][:8], 1):
            refusals = summary["refusals_by_agent"].get(s["agent_id"], 0)
            line = (f"{i}. {s['display_name']}：军功增益 {s['total_reward']:+d}，"
                    f"告捷 {s['completed']} 次，兵败 {s['failed']} 次")
            if refusals:
                line += f"，拒接军令 {refusals} 次"
            if s["best_task"]:
                line += f"，最佳军令：「{s['best_task'][:30]}」"
            lines.append(line)
    if summary["highlights"]:
        lines.append("\n【典型战例（文言化融入正文，勿逐条照搬）】")
        for h in summary["highlights"]:
            outcome = "告捷" if h["success"] else "兵败"
            lines.append(f"- {h['display_name']} 领「{h['task'][:40]}」{outcome}：{h['reason'][:120]}")
    lines.append(
        f"\n请据上述数据，以《三国演义》笔法为孔明进化小镇写一章志书。"
        f"日期用干支纪年（参考：{chinese_date}），开篇气势宏大，可仿「话说天下大势」起势，"
        f"三段结构：①擂台大势与时令氛围②两三位核心谋士的征战经过③「正是：」七字对联收尾，全文 500-650 字。"
        f"重点突出军功最高者事迹，其余简短带过。"
        f"禁止：英文、agent_id、括号、markdown 符号、直接写公历年月日。"
    )
    return "\n".join(lines)


# ── 持久化 & 查询 ──────────────────────────────────────────────────────────────

def chronicle_path(date_str: str) -> Path:
    return _CHRONICLE_DIR / f"{date_str}.json"


def load_chronicle(date_str: str) -> dict[str, Any] | None:
    p = chronicle_path(date_str)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("chronicle: load %s failed: %s", p, e)
        return None


def list_chronicles() -> list[dict[str, Any]]:
    _CHRONICLE_DIR.mkdir(parents=True, exist_ok=True)
    result = []
    for p in sorted(_CHRONICLE_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            result.append({
                "date": data.get("date", p.stem),
                "generated_at": data.get("generated_at", ""),
                "total_tasks": data.get("summary", {}).get("total_tasks", 0),
                "preview": (data.get("text", "") or "")[:100],
            })
        except Exception:
            result.append({"date": p.stem, "generated_at": "", "total_tasks": 0, "preview": ""})
    return result


# ── 主入口 ─────────────────────────────────────────────────────────────────────

async def generate_chronicle(
    date_str: str | None = None,
    *,
    agent_name_map: dict[str, str] | None = None,
    broadcast_fn=None,
) -> dict[str, Any]:
    """生成指定日期（默认昨日 CST）的文言文战报并保存；broadcast_fn 可选广播 WS 事件。

    日期自动回退策略（优先级从高到低）：
      1. 调用方指定的 date_str
      2. 昨日（CST）
      3. task_history.jsonl 中有数据的最近一天（避免生成空数据战报）
    """
    import os
    from llm_client import chat_completion

    # 战报生成始终走主（远端）模型，避免误用本地 JUDGE_MODEL 名称
    _main_model = os.getenv("MODEL") or None

    if date_str is None:
        date_str = prev_day_cst()

    # 若目标日期无数据，尝试自动回退至最近有记录的日期
    summary = _build_daily_summary(date_str, agent_name_map)
    if summary["total_tasks"] == 0 and date_str == prev_day_cst():
        fallback = _find_latest_date_with_data()
        if fallback and fallback != date_str:
            logger.info(
                "chronicle: %s has no data, falling back to most recent date with data: %s",
                date_str, fallback,
            )
            date_str = fallback
            summary = _build_daily_summary(date_str, agent_name_map)

    logger.info(
        "chronicle: generating for date=%s (tasks=%d)", date_str, summary["total_tasks"]
    )

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _build_prompt(summary)},
    ]
    try:
        # raw_only=True：战报是纯文言文，跳过 JSON 解析避免误匹配
        # max_tokens=16000：Gemini 2.5 Flash 默认开启 thinking，thinking token 会消耗
        # 输出预算，需留足空间（thinking ~3000-8000 token + 正文 ~1000 token）
        result = await chat_completion(
            messages, model=_main_model, temperature=0.85, max_tokens=16000, raw_only=True
        )
        text = result.get("raw", "")
        logger.info("chronicle: main text generated, len=%d", len(text))
    except Exception as e:
        logger.error("chronicle: LLM call failed: %s", e)
        text = f"（战报生成失败：{e}）"

    # 独立调用：专门生成回目标题（上句 下句，各七字，空格分隔）
    chapter_title = ""
    if text and not text.startswith("（"):
        try:
            title_messages = [
                {"role": "system", "content": (
                    "你是《三国演义》的章回体编者。根据用户提供的战报正文，"
                    "仿照《三国演义》回目格式，生成一行标题：上句与下句各七个汉字，中间用一个空格分隔。"
                    "只输出这一行标题，不要任何其他文字、标点或解释。"
                    "示例：骁将奋勇三军克敌 败将折戟军功大损"
                )},
                {"role": "user", "content": f"战报正文：\n{text[:400]}"},
            ]
            # max_tokens=4096：同样为 Gemini thinking 模式留足 token 预算
            title_result = await chat_completion(
                title_messages, model=_main_model, temperature=0.7, max_tokens=4096, raw_only=True
            )
            raw_title = title_result.get("raw", "").strip()
            title_lines = raw_title.splitlines()
            chapter_title = title_lines[0].strip() if title_lines else ""
            logger.info("chronicle: generated chapter title: %s", chapter_title)
        except Exception as e:
            logger.warning("chronicle: title generation failed: %s", e)

    record = {
        "date": date_str,
        "generated_at": datetime.now(_CST).isoformat(),
        "title": chapter_title,
        "text": text,
        "summary": {
            "total_tasks": summary["total_tasks"],
            "total_completed": summary["total_completed"],
            "total_failed": summary["total_failed"],
        },
        "agent_stats": summary["agent_stats"],
    }

    _CHRONICLE_DIR.mkdir(parents=True, exist_ok=True)
    chronicle_path(date_str).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("chronicle: saved %s (%d chars)", date_str, len(text))

    if broadcast_fn is not None:
        try:
            await broadcast_fn({
                "type": "chronicle_published",
                "date": date_str,
                "preview": text[:200],
            })
        except Exception as e:
            logger.warning("chronicle: broadcast failed: %s", e)

    return record

