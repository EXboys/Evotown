import { useState } from "react";
import { ShareCard } from "../ShareCard";

interface Agent {
  id: string;
  display_name?: string;
  balance?: number;
  task_count?: number;
  success_count?: number;
  evolution_count?: number;
  evolution_success_count?: number;
}

interface AgentHeaderProps {
  agentId: string;
  agent?: Agent;
  onDelete: () => void;
  deleting: boolean;
  onShowShare: () => void;
}

export function AgentHeader({ agentId, agent, onDelete, deleting, onShowShare }: AgentHeaderProps) {
  return (
    <div className="border-b border-slate-600/50 bg-gradient-to-b from-slate-900 to-slate-950 p-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-slate-100 truncate leading-tight">
            {agent?.display_name || agentId}
          </h3>
          {agent && (
            <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1">
              <span className="text-[10px] text-slate-400">
                ⚔️ <span className="text-amber-400 font-medium">{agent.balance} 军功</span>
              </span>
              <span className="text-[10px] text-slate-500">
                📋 {agent.success_count ?? 0}/{agent.task_count ?? 0}
              </span>
              <span className="text-[10px] text-slate-500">
                ✨ {agent.evolution_success_count ?? 0}/{agent.evolution_count ?? 0}
              </span>
            </div>
          )}
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={onShowShare}
            className="px-2 py-1 text-[10px] font-medium rounded bg-violet-600/20 text-violet-400 border border-violet-600/30 hover:bg-violet-600/40"
            title="生成分享卡片"
          >
            📤
          </button>
          <button
            onClick={onDelete}
            disabled={deleting}
            className="px-2 py-1 text-[10px] font-medium rounded bg-rose-600/20 text-rose-400 border border-rose-600/30 hover:bg-rose-600/40 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {deleting ? "删除中..." : "删除"}
          </button>
        </div>
      </div>
    </div>
  );
}

interface TabBarProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
}

const TABS = [
  { key: "executions", label: "执行记录" },
  { key: "decisions", label: "决策" },
  { key: "rules", label: "规则" },
  { key: "prompts", label: "Prompts" },
  { key: "skills", label: "技能" },
  { key: "evolution", label: "进化" },
  { key: "soul", label: "Soul" },
] as const;

export function TabBar({ currentTab, onTabChange }: TabBarProps) {
  return (
    <div className="flex border-b border-slate-600/50 overflow-x-auto">
      {TABS.map((t) => (
        <button
          key={t.key}
          onClick={() => onTabChange(t.key)}
          className={`px-3 py-2 text-xs font-medium transition-colors shrink-0 ${
            currentTab === t.key
              ? "text-evo-accent border-b-2 border-evo-accent"
              : "text-slate-500 hover:text-slate-300"
          }`}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

export { ShareCard };
