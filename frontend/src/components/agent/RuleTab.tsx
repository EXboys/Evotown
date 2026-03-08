export interface Rule {
  id?: string;
  instruction?: string;
  content?: string;
  effectiveness?: number;
  tool_hint?: string;
  has_skill?: boolean;
  origin?: string;
}

interface RuleTabProps {
  rules: Rule[];
}

export function RuleTab({ rules }: RuleTabProps) {
  if (rules.length === 0) {
    return <li className="text-sm text-slate-500">暂无规则</li>;
  }

  return (
    <ul className="space-y-2">
      {rules.map((r, i) => (
        <li
          key={r.id ?? i}
          className={`px-3 py-2.5 rounded border text-xs ${
            r.origin === "evolved"
              ? "bg-violet-900/20 border-violet-700/40"
              : "bg-slate-800/50 border-slate-700/50"
          }`}
        >
          {(r.origin === "evolved" || r.tool_hint != null || r.effectiveness != null) && (
            <div className="flex items-center gap-1.5 mb-1.5">
              {r.origin === "evolved" && (
                <span
                  className="px-1.5 py-0.5 rounded text-[10px] bg-violet-900/50 text-violet-400 border border-violet-600/50"
                  title="进化产出"
                >
                  ✨ 进化
                </span>
              )}
              {r.tool_hint != null && (
                <span
                  className={`px-1.5 py-0.5 rounded text-[10px] ${
                    r.has_skill
                      ? "bg-emerald-900/50 text-emerald-400 border border-emerald-700/50"
                      : "bg-amber-900/30 text-amber-500/90 border border-amber-700/30"
                  }`}
                  title={r.has_skill ? "已拥有此技能" : "未拥有此技能"}
                >
                  {r.tool_hint}
                  {r.has_skill ? " ✓" : " ✗"}
                </span>
              )}
              {r.effectiveness != null && (
                <span className="text-[10px] text-slate-500 ml-auto">
                  效能 {r.effectiveness}
                </span>
              )}
            </div>
          )}
          <p className="text-slate-300 leading-relaxed whitespace-pre-wrap break-words">
            {r.instruction ?? r.content ?? JSON.stringify(r)}
          </p>
        </li>
      ))}
    </ul>
  );
}
