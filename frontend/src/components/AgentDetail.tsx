/** Agent 详情抽屉 — 规则 / 技能 / 决策 */
import { useEffect, useState } from "react";

interface Rule {
  id?: string;
  instruction?: string;
  content?: string;
  effectiveness?: number;
}

export function AgentDetail({
  agentId,
  onClose,
}: {
  agentId: string;
  onClose: () => void;
}) {
  const [tab, setTab] = useState<"rules" | "skills" | "decisions">("rules");
  const [rules, setRules] = useState<Rule[]>([]);
  const [skills, setSkills] = useState<string[]>([]);
  const [decisions, setDecisions] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [rRes, sRes, dRes] = await Promise.all([
          fetch(`/agents/${agentId}/rules`),
          fetch(`/agents/${agentId}/skills`),
          fetch(`/agents/${agentId}/decisions?limit=20`),
        ]);
        setRules((await rRes.json()) ?? []);
        setSkills((await sRes.json()) ?? []);
        setDecisions((await dRes.json()) ?? []);
      } catch {
        setRules([]);
        setSkills([]);
        setDecisions([]);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [agentId]);

  return (
    <div className="absolute inset-0 z-20 flex flex-col bg-slate-900/95 backdrop-blur-sm border-l border-slate-600/50">
      <div className="flex items-center justify-between p-3 border-b border-slate-600/50">
        <h3 className="text-sm font-medium text-slate-200">{agentId} 详情</h3>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-white text-lg leading-none"
        >
          ×
        </button>
      </div>
      <div className="flex border-b border-slate-600/50">
        {(["rules", "skills", "decisions"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-xs font-medium transition-colors ${
              tab === t
                ? "text-evo-accent border-b-2 border-evo-accent"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            {t === "rules" ? "规则" : t === "skills" ? "技能" : "决策"}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto p-3">
        {loading ? (
          <p className="text-sm text-slate-500">加载中...</p>
        ) : tab === "rules" ? (
          <ul className="space-y-2">
            {rules.length === 0 ? (
              <li className="text-sm text-slate-500">暂无规则</li>
            ) : (
              rules.map((r, i) => (
                <li
                  key={r.id ?? i}
                  className="p-2 rounded bg-slate-800/50 border border-slate-700/50 text-xs text-slate-300"
                >
                  <p className="font-mono whitespace-pre-wrap break-words">
                    {r.instruction ?? r.content ?? JSON.stringify(r)}
                  </p>
                  {r.effectiveness != null && (
                    <p className="text-slate-500 mt-1">effectiveness: {r.effectiveness}</p>
                  )}
                </li>
              ))
            )}
          </ul>
        ) : tab === "skills" ? (
          <ul className="space-y-1">
            {skills.length === 0 ? (
              <li className="text-sm text-slate-500">暂无进化技能</li>
            ) : (
              skills.map((s) => (
                <li key={s} className="text-sm font-mono text-slate-300">
                  · {s}
                </li>
              ))
            )}
          </ul>
        ) : (
          <ul className="space-y-2">
            {decisions.length === 0 ? (
              <li className="text-sm text-slate-500">暂无决策记录</li>
            ) : (
              decisions.map((d, i) => (
                <li
                  key={i}
                  className="p-2 rounded bg-slate-800/50 border border-slate-700/50 text-xs"
                >
                  <p className="text-slate-400">
                    {String((d as { task_completed?: boolean }).task_completed ?? "?") === "true"
                      ? "✓ 完成"
                      : "✗ 未完成"}
                  </p>
                  <p className="text-slate-500 truncate mt-0.5">
                    {(d as { task_description?: string }).task_description ?? "-"}
                  </p>
                </li>
              ))
            )}
          </ul>
        )}
      </div>
    </div>
  );
}
