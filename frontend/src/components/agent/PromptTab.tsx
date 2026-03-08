import { useState } from "react";
import { PromptDiffView } from "./PromptDiffView";

interface PromptItem {
  name: string;
  filename: string;
  content: string;
  evolved: boolean;
  original_content?: string | null;
}

interface PromptTabProps {
  prompts: PromptItem[];
  onRefresh: () => void;
  loading: boolean;
}

export function PromptTab({ prompts, onRefresh, loading }: PromptTabProps) {
  const [showDiff, setShowDiff] = useState<Record<string, boolean>>({});

  const header = (
    <div className="flex items-center justify-between gap-2 mb-1">
      <p className="text-xs text-slate-500">
        <span className="text-violet-400">+紫色</span> = 进化新增，
        <span className="text-red-400/70 line-through">−红色</span> = 原有已移除
      </p>
      <button
        onClick={onRefresh}
        disabled={loading}
        className="shrink-0 px-2 py-0.5 rounded text-[10px] bg-slate-700/60 text-slate-400 border border-slate-600/40 hover:bg-slate-600/60 hover:text-slate-200 transition-colors disabled:opacity-40"
      >
        {loading ? "刷新中…" : "↻ 刷新"}
      </button>
    </div>
  );

  if (prompts.length === 0) {
    return (
      <div className="space-y-2">
        {header}
        <p className="text-sm text-slate-500 py-4 text-center rounded-lg bg-slate-800/30 border border-dashed border-slate-600/50">
          暂无 Prompts
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {header}
      {prompts.map((p) => {
        const canDiff = p.evolved && !!p.original_content;
        const isDiffMode = canDiff && (showDiff[p.name] ?? true);
        return (
          <div
            key={p.name}
            className={`rounded-xl border text-xs overflow-hidden ${
              p.evolved ? "bg-violet-900/10 border-violet-700/40" : "bg-slate-800/40 border-slate-700/40"
            }`}
          >
            <div className="flex items-center justify-between gap-2 px-3 py-2 border-b border-slate-700/50 bg-slate-900/30">
              <span className="font-mono font-medium text-slate-200">{p.filename}</span>
              <div className="flex items-center gap-2 shrink-0">
                {p.evolved && (
                  <span
                    className="px-1.5 py-0.5 rounded text-[10px] bg-violet-900/50 text-violet-400 border border-violet-600/50"
                    title="曾被进化修改"
                  >
                    ✨ 进化
                  </span>
                )}
                {canDiff && (
                  <button
                    onClick={() => setShowDiff((prev) => ({ ...prev, [p.name]: !isDiffMode }))}
                    className="px-1.5 py-0.5 rounded text-[10px] bg-slate-700/60 text-slate-400 border border-slate-600/40 hover:bg-slate-600/60 hover:text-slate-200 transition-colors"
                  >
                    {isDiffMode ? "原文" : "对比"}
                  </button>
                )}
              </div>
            </div>
            {isDiffMode && p.original_content != null ? (
              <PromptDiffView original={p.original_content} current={p.content} />
            ) : (
              <pre className="p-3 text-slate-400 whitespace-pre-wrap break-words font-mono text-[11px] max-h-48 overflow-y-auto">
                {p.content || "(空)"}
              </pre>
            )}
          </div>
        );
      })}
    </div>
  );
}
