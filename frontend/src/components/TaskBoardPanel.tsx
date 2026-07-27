import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { adminFetch } from "../hooks/useAdminToken";
import { formatDateTimeShort } from "../lib/datetime";
import { evotownEvents } from "../phaser/events";

type Agent = {
  agent_id: string;
  name: string;
  status: "active" | "archived";
};

type TaskNode = {
  node_id: string;
  agent_id: string;
  agent_name?: string;
  source_type: "dispatch_job" | "hosted_run";
  source_id: string;
  title: string;
  message: string;
  board_status: "queued" | "running" | "done" | "failed";
  source_status: string;
  depends_on_node_id?: string;
  run_id?: string;
  dispatch_job_id?: string;
  created_at?: string;
  updated_at?: string;
  completed_at?: string;
};

type BoardColumns = Record<TaskNode["board_status"], TaskNode[]>;

type BoardResponse = {
  agent_id: string;
  columns: BoardColumns;
  total: number;
  limit: number;
  has_more: boolean;
  board_statuses: TaskNode["board_status"][];
};

type ModelOption = { id: string; label: string; provider?: string };

type Props = {
  onRefresh?: () => void;
};

const COLUMN_META: Record<
  TaskNode["board_status"],
  { label: string; hint: string; headerClass: string; countClass: string }
> = {
  queued: {
    label: "排队中",
    hint: "Queued",
    headerClass: "border-amber-200 bg-amber-50 text-amber-900",
    countClass: "bg-amber-100 text-amber-800",
  },
  running: {
    label: "执行中",
    hint: "Running",
    headerClass: "border-blue-200 bg-blue-50 text-blue-900",
    countClass: "bg-blue-100 text-blue-800",
  },
  done: {
    label: "已完成",
    hint: "Done",
    headerClass: "border-emerald-200 bg-emerald-50 text-emerald-900",
    countClass: "bg-emerald-100 text-emerald-800",
  },
  failed: {
    label: "失败",
    hint: "Failed",
    headerClass: "border-red-200 bg-red-50 text-red-900",
    countClass: "bg-red-100 text-red-800",
  },
};

const SOURCE_LABEL: Record<TaskNode["source_type"], string> = {
  dispatch_job: "派活",
  hosted_run: "托管运行",
};

const PAGE_SIZE = 10;

function TaskCard({ node }: { node: TaskNode }) {
  const title = node.title?.trim() || node.message.slice(0, 80) || node.source_id;
  const subtitle = node.title?.trim() ? node.message.slice(0, 120) : "";
  const agentLabel = node.agent_name?.trim() || node.agent_id || "未绑定 agent";
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-medium text-slate-900">{title}</div>
          {subtitle && <p className="mt-1 line-clamp-2 text-xs text-slate-500">{subtitle}</p>}
        </div>
        <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-slate-600">
          {SOURCE_LABEL[node.source_type]}
        </span>
      </div>
      <div className="mt-2">
        {node.agent_id ? (
          <Link
            to={`/agent/agents/${node.agent_id}`}
            className="inline-flex max-w-full items-center truncate rounded-md bg-slate-50 px-2 py-0.5 text-[11px] font-medium text-slate-700 ring-1 ring-slate-200 hover:bg-slate-100 hover:text-slate-950"
            title={node.agent_id}
          >
            {agentLabel}
          </Link>
        ) : (
          <span className="inline-flex rounded-md bg-slate-50 px-2 py-0.5 text-[11px] text-slate-400 ring-1 ring-slate-200">
            {agentLabel}
          </span>
        )}
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
        <span className="font-mono">{node.source_id.slice(0, 14)}…</span>
        {node.run_id && node.agent_id && (
          <Link to={`/agent/agents/${node.agent_id}`} className="text-blue-600 hover:underline">
            run
          </Link>
        )}
        {node.depends_on_node_id && <span>依赖上一节点</span>}
      </div>
      {node.created_at && (
        <div className="mt-2 text-[11px] text-slate-400">{formatDateTimeShort(node.created_at)}</div>
      )}
    </article>
  );
}

export function TaskBoardPanel({ onRefresh }: Props) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [agentId, setAgentId] = useState("");
  const [limit, setLimit] = useState(PAGE_SIZE);
  const [board, setBoard] = useState<BoardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<{ tone: "ok" | "err"; text: string } | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [teamPairs, setTeamPairs] = useState("*");
  const [policyLoading, setPolicyLoading] = useState(false);
  const [models, setModels] = useState<ModelOption[]>([]);
  const [form, setForm] = useState({
    kind: "dispatch" as "dispatch" | "handoff" | "notify",
    target_agent_id: "",
    target_team_id: "",
    title: "",
    message: "",
    model: "",
    chain: false,
    chain_team: "",
    chain_message: "",
  });

  const loadAgents = useCallback(async () => {
    const res = await adminFetch("/api/v1/agents?limit=200");
    if (!res.ok) return;
    const data = (await res.json()) as { agents?: Agent[] };
    const active = (data.agents || []).filter((a) => a.status === "active");
    setAgents(active);
  }, []);

  const loadBoard = useCallback(async (selectedAgentId: string, pageLimit: number, quiet = false) => {
    if (!quiet) setLoading(true);
    setError("");
    const params = new URLSearchParams();
    params.set("limit", String(pageLimit));
    if (selectedAgentId) params.set("agent_id", selectedAgentId);
    const res = await adminFetch(`/api/v1/task-board?${params.toString()}`);
    if (!res.ok) {
      setError(`加载看板失败 (${res.status})`);
      setBoard(null);
      setLoading(false);
      setLoadingMore(false);
      return;
    }
    setBoard((await res.json()) as BoardResponse);
    setLoading(false);
    setLoadingMore(false);
  }, []);

  useEffect(() => {
    void loadAgents();
  }, [loadAgents]);

  useEffect(() => {
    setLimit(PAGE_SIZE);
    void loadBoard(agentId, PAGE_SIZE);
  }, [agentId, loadBoard]);

  useEffect(() => {
    adminFetch("/api/v1/dispatch/policy")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((data: { team_pairs?: string }) => setTeamPairs(data.team_pairs || "*"))
      .catch(() => setTeamPairs("*"));
  }, []);

  useEffect(() => {
    adminFetch("/api/v1/agent/options")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((data: { models?: ModelOption[]; default_model?: string }) => {
        const list = data.models || [];
        setModels(list);
        const fallback = data.default_model || list[0]?.id || "";
        setForm((f) => ({ ...f, model: f.model || fallback }));
      })
      .catch(() => setModels([]));
  }, []);

  useEffect(() => {
    if (agents.length === 0) return;
    setForm((f) => {
      if (f.target_agent_id && agents.some((a) => a.agent_id === f.target_agent_id)) return f;
      const preferred = agents[0];
      return preferred ? { ...f, target_agent_id: preferred.agent_id } : f;
    });
  }, [agents]);

  useEffect(() => {
    const onUpdate = () => {
      void loadBoard(agentId, limit, true);
    };
    evotownEvents.on("dispatch_job_updated", onUpdate);
    return () => evotownEvents.off("dispatch_job_updated", onUpdate);
  }, [agentId, limit, loadBoard]);

  const columns = useMemo(() => {
    const empty: BoardColumns = { queued: [], running: [], done: [], failed: [] };
    return board?.columns ?? empty;
  }, [board]);

  const savePolicy = async () => {
    setPolicyLoading(true);
    setMessage(null);
    const r = await adminFetch("/api/v1/dispatch/policy", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ team_pairs: teamPairs }),
    });
    setPolicyLoading(false);
    if (!r.ok) {
      setMessage({ tone: "err", text: `策略保存失败: ${(await r.text()).slice(0, 120)}` });
      return;
    }
    setMessage({ tone: "ok", text: "Handoff 策略已保存" });
  };

  const submit = async () => {
    setMessage(null);
    if (!form.message.trim()) {
      setMessage({ tone: "err", text: "请填写任务内容" });
      return;
    }
    if (!form.target_agent_id) {
      setMessage({ tone: "err", text: "请选择目标 Agent" });
      return;
    }
    setSubmitting(true);
    const body: Record<string, unknown> = {
      kind: form.kind,
      target_agent_id: form.target_agent_id,
      target_team_id: form.target_team_id || undefined,
      title: form.title,
      message: form.message,
    };
    const payload: Record<string, unknown> = {};
    if (form.model.trim()) payload.model = form.model.trim();
    if (form.chain && form.chain_team && form.chain_message.trim()) {
      payload.on_success_handoff = {
        kind: "handoff",
        target_team_id: form.chain_team,
        title: "接续任务",
        message: form.chain_message,
      };
    }
    if (Object.keys(payload).length) body.payload = payload;

    try {
      const r = await adminFetch("/api/v1/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) {
        setMessage({ tone: "err", text: `派发失败: ${(await r.text()).slice(0, 200)}` });
        return;
      }
      setMessage({
        tone: "ok",
        text: form.chain ? "已入队，成功后自动 handoff 到下一团队" : "任务已入队，看板将刷新",
      });
      setForm((f) => ({ ...f, message: "", title: "", chain_message: "" }));
      await loadBoard(agentId, limit, true);
      onRefresh?.();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">Task Board</div>
          <h2 className="mt-1 text-2xl font-semibold text-slate-950">任务看板</h2>
          <p className="mt-1 text-sm text-slate-500">选择 Agent 派活，在看板中跟踪执行状态。</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={agentId}
            onChange={(e) => setAgentId(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700"
          >
            <option value="">全部 agent</option>
            {agents.map((agent) => (
              <option key={agent.agent_id} value={agent.agent_id}>
                {agent.name}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => void loadBoard(agentId, limit)}
            className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            刷新
          </button>
        </div>
      </div>

      {message && (
        <div
          className={`rounded-lg border px-3 py-2 text-sm ${
            message.tone === "ok"
              ? "border-emerald-200 bg-emerald-50 text-emerald-900"
              : "border-red-200 bg-red-50 text-red-900"
          }`}
        >
          {message.text}
        </div>
      )}

      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 bg-slate-50/60 px-3 py-2">
          <div className="mb-1.5 text-[10px] font-medium uppercase tracking-wide text-slate-400">目标 Agent</div>
          {agents.length === 0 ? (
            <div className="py-1 text-xs text-slate-500">暂无活跃 Agent</div>
          ) : (
            <div className="flex gap-2 overflow-x-auto pb-0.5 [scrollbar-width:thin]">
              {agents.map((a) => {
                const active = form.target_agent_id === a.agent_id;
                return (
                  <button
                    key={a.agent_id}
                    type="button"
                    onClick={() => setForm((f) => ({ ...f, target_agent_id: a.agent_id }))}
                    className={`flex shrink-0 items-center gap-2 rounded-lg border px-3 py-1.5 text-left transition ${
                      active
                        ? "border-slate-900 bg-slate-950 text-white shadow-sm"
                        : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
                    }`}
                  >
                    <span className={`h-2 w-2 shrink-0 rounded-full bg-emerald-500`} />
                    <span className="max-w-[140px] truncate text-xs font-medium">{a.name}</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <div className="space-y-3 p-4">
          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <span className="font-medium text-slate-700">{agents.find((a) => a.agent_id === form.target_agent_id)?.name || "未选 Agent"}</span>
            <span className="text-slate-300">·</span>
            <span className="truncate font-mono text-[11px]">{form.target_agent_id || "未选 Agent"}</span>
          </div>

          <div className="flex flex-col gap-3 lg:flex-row lg:items-stretch">
            <label className="min-w-0 flex-1 text-sm">
              <span className="sr-only">任务内容</span>
              <textarea
                className="min-h-[72px] w-full resize-y rounded-lg border border-slate-200 px-3 py-2.5 text-sm leading-relaxed focus:border-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-100"
                placeholder="描述 Agent 需要完成的工作…"
                value={form.message}
                onChange={(e) => setForm({ ...form, message: e.target.value })}
                onKeyDown={(e) => {
                  if ((e.metaKey || e.ctrlKey) && e.key === "Enter") void submit();
                }}
              />
            </label>

            <div className="flex shrink-0 flex-col gap-2 lg:w-44">
              <select
                className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                value={form.model}
                onChange={(e) => setForm({ ...form, model: e.target.value })}
                aria-label="模型"
              >
                {models.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
              <button
                type="button"
                disabled={submitting}
                onClick={() => void submit()}
                className="rounded-lg bg-slate-950 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-60"
              >
                {submitting ? "提交中…" : "派发"}
              </button>
              <button
                type="button"
                onClick={() => setShowAdvanced((v) => !v)}
                className="text-xs text-slate-500 hover:text-slate-700"
              >
                {showAdvanced ? "收起选项" : "更多选项"}
              </button>
            </div>
          </div>

          {showAdvanced && (
            <div className="grid gap-3 rounded-lg border border-dashed border-slate-200 bg-slate-50/80 p-3 sm:grid-cols-2 lg:grid-cols-4">
              <label className="block text-xs sm:col-span-2 lg:col-span-1">
                <span className="mb-1 block font-medium text-slate-600">任务类型</span>
                <select
                  className="w-full rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-sm"
                  value={form.kind}
                  onChange={(e) => setForm({ ...form, kind: e.target.value as typeof form.kind })}
                >
                  <option value="dispatch">dispatch — 中心派活</option>
                  <option value="handoff">handoff — 团队交接</option>
                  <option value="notify">notify — 通知</option>
                </select>
              </label>
              <label className="block text-xs">
                <span className="mb-1 block font-medium text-slate-600">标题（可选）</span>
                <input
                  className="w-full rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-sm"
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                />
              </label>
              <label className="block text-xs">
                <span className="mb-1 block font-medium text-slate-600">目标团队（可选）</span>
                <input
                  placeholder="owner_team"
                  className="w-full rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-sm"
                  value={form.target_team_id}
                  onChange={(e) => setForm({ ...form, target_team_id: e.target.value })}
                />
              </label>
              <label className="block text-xs sm:col-span-2 lg:col-span-1">
                <span className="mb-1 block font-medium text-slate-600">手动 Agent ID</span>
                <input
                  list="taskboard-agent-ids"
                  className="w-full rounded-lg border border-slate-200 bg-white px-2.5 py-2 font-mono text-xs"
                  value={form.target_agent_id}
                  onChange={(e) => setForm({ ...form, target_agent_id: e.target.value })}
                />
                <datalist id="taskboard-agent-ids">
                  {agents.map((a) => (
                    <option key={a.agent_id} value={a.agent_id} />
                  ))}
                </datalist>
              </label>
              <div className="space-y-2 sm:col-span-2 lg:col-span-4">
                <label className="flex items-center gap-2 text-xs text-slate-700">
                  <input
                    type="checkbox"
                    checked={form.chain}
                    onChange={(e) => setForm({ ...form, chain: e.target.checked })}
                  />
                  成功后自动 handoff 到下一团队
                </label>
                {form.chain && (
                  <div className="grid gap-2 sm:grid-cols-2">
                    <input
                      className="rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-sm"
                      placeholder="下一团队"
                      value={form.chain_team}
                      onChange={(e) => setForm({ ...form, chain_team: e.target.value })}
                    />
                    <input
                      className="rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-sm"
                      placeholder="接续内容"
                      value={form.chain_message}
                      onChange={(e) => setForm({ ...form, chain_message: e.target.value })}
                    />
                  </div>
                )}
              </div>
              <details className="text-xs sm:col-span-2 lg:col-span-4">
                <summary className="cursor-pointer font-medium text-slate-600">Handoff 白名单</summary>
                <div className="mt-2 flex flex-wrap items-end gap-2">
                  <textarea
                    className="min-w-[200px] flex-1 rounded border border-slate-200 px-2 py-1.5 font-mono text-[11px]"
                    rows={1}
                    value={teamPairs}
                    onChange={(e) => setTeamPairs(e.target.value)}
                  />
                  <button
                    type="button"
                    disabled={policyLoading}
                    onClick={() => void savePolicy()}
                    className="rounded border border-slate-200 px-2 py-1 hover:bg-white disabled:opacity-50"
                  >
                    {policyLoading ? "…" : "保存"}
                  </button>
                </div>
                <p className="mt-1 text-[11px] text-slate-400">
                  格式：team:team 或 *，用英文逗号分隔（例：sales:finance,it:finance）。
                </p>
              </details>
            </div>
          )}
        </div>
      </section>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</div>
      )}

      {loading ? (
        <div className="py-8 text-center text-sm text-slate-400">加载中…</div>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
          {(Object.keys(COLUMN_META) as TaskNode["board_status"][]).map((status) => (
            <article
              key={status}
              className={`rounded-xl border ${COLUMN_META[status].headerClass} p-3`}
            >
              <div className="mb-3 flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wide">
                  {COLUMN_META[status].label}
                  <span className="ml-1 font-normal tracking-normal opacity-70">{COLUMN_META[status].hint}</span>
                </span>
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${COLUMN_META[status].countClass}`}>
                  {columns[status].length}
                </span>
              </div>
              {columns[status].length === 0 ? (
                <div className="py-4 text-center text-[11px] text-slate-400">暂无</div>
              ) : (
                <div className="space-y-2">
                  {columns[status].map((node) => (
                    <TaskCard key={node.node_id} node={node} />
                  ))}
                </div>
              )}
            </article>
          ))}
        </div>
      )}

      {board?.has_more && (
        <div className="text-center">
          <button
            type="button"
            disabled={loadingMore}
            onClick={() => {
              setLoadingMore(true);
              void loadBoard(agentId, limit + PAGE_SIZE).then(() => setLimit((l) => l + PAGE_SIZE));
            }}
            className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-50"
          >
            {loadingMore ? "加载中…" : "加载更多"}
          </button>
        </div>
      )}
    </div>
  );
}
