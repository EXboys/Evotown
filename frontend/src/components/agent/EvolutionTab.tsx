export interface EvolutionLogItem {
  ts: string;
  type: string;
  target_id: string;
  reason: string;
}

const EVO_TYPE_LABELS: Record<string, string> = {
  rule_added: "规则+",
  rule_retired: "规则-",
  example_added: "示例+",
  skill_pending: "技能待确认",
  skill_confirmed: "技能确认",
  skill_refined: "技能优化",
  skill_retired: "技能归档",
  evolution_run: "运行",
  auto_rollback: "回滚",
};

interface EvolutionTabProps {
  evolutionLog: EvolutionLogItem[];
}

export function EvolutionTab({ evolutionLog }: EvolutionTabProps) {
  return (
    <div className="space-y-2">
      <p className="text-xs text-slate-500">进化事件明细（时间倒序）</p>
      {evolutionLog.length === 0 ? (
        <p className="text-sm text-slate-500 py-4 text-center rounded-lg bg-slate-800/30 border border-dashed border-slate-600/50">
          暂无进化记录
        </p>
      ) : (
        <div className="rounded-lg border border-slate-700/50 overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-slate-800/50 text-slate-400">
                <th className="text-left py-2 px-2 font-medium">时间</th>
                <th className="text-left py-2 px-2 font-medium">类型</th>
                <th className="text-left py-2 px-2 font-medium">目标</th>
                <th className="text-left py-2 px-2 font-medium">说明</th>
              </tr>
            </thead>
            <tbody>
              {evolutionLog.map((e, i) => (
                <tr key={i} className="border-t border-slate-700/30 hover:bg-slate-800/30">
                  <td className="py-1.5 px-2 text-slate-500 whitespace-nowrap">
                    {e.ts ? new Date(e.ts).toLocaleString("zh-CN") : "-"}
                  </td>
                  <td className="py-1.5 px-2">
                    <span className="px-1.5 py-0.5 rounded bg-slate-700/50 text-slate-300">
                      {EVO_TYPE_LABELS[e.type] ?? e.type}
                    </span>
                  </td>
                  <td className="py-1.5 px-2 font-mono text-slate-400 truncate max-w-[80px]" title={e.target_id}>
                    {e.target_id || "-"}
                  </td>
                  <td className="py-1.5 px-2 text-slate-400 break-words max-w-[180px]">
                    {e.reason || "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
