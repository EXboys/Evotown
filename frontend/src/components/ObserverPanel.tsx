import { useEffect, useState } from "react";
import { evotownEvents } from "../phaser/events";
import { useEvotownStore } from "../store/evotownStore";
import { TaskInjectorBar } from "./TaskInjectorBar";
import { EvolutionTimeline } from "./EvolutionTimeline";
import { MetricsDashboard } from "./MetricsDashboard";
import { AgentDetail } from "./AgentDetail";

type TabId = "timeline" | "metrics" | "agents";

export function ObserverPanel() {
  const [taskInput, setTaskInput] = useState("");
  const [tab, setTab] = useState<TabId>("timeline");
  const agents = useEvotownStore((s) => s.agents);
  const setAgents = useEvotownStore((s) => s.setAgents);
  const addAgent = useEvotownStore((s) => s.addAgent);
  const selectedAgentId = useEvotownStore((s) => s.selectedAgentId);
  const setSelectedAgent = useEvotownStore((s) => s.setSelectedAgent);

  useEffect(() => {
    fetch("/agents")
      .then((r) => r.json())
      .then((list: { id: string; balance: number }[]) => {
        setAgents(list);
        list.forEach((a) =>
          evotownEvents.emit("agent_created", { agent_id: a.id, balance: a.balance })
        );
      })
      .catch(() => {});
  }, [setAgents]);

  const createAgent = async () => {
    const res = await fetch("/agents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_dir: null }),
    });
    const data = await res.json();
    addAgent({ id: data.id, balance: data.balance });
    evotownEvents.emit("agent_created", { agent_id: data.id, balance: data.balance });
  };

  const injectTask = async () => {
    if (!taskInput.trim() || agents.length === 0) return;
    await fetch("/tasks/inject", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ agent_id: agents[0].id, task: taskInput }),
    });
    setTaskInput("");
  };

  const triggerEvolve = async () => {
    if (agents.length === 0) return;
    await fetch(`/agents/${agents[0].id}/evolve`, { method: "POST" });
  };

  return (
    <div className="w-[380px] flex flex-col bg-[#1e293b] backdrop-blur-sm border-l border-slate-600/50 shadow-evo-panel relative">
      <div className="p-5 border-b border-slate-600/50">
        <h2 className="text-base font-semibold text-slate-200 tracking-wide flex items-center gap-2">
          <span className="w-1.5 h-4 rounded-full bg-evo-accent" />
          观测面板
        </h2>
        <p className="text-xs text-slate-500 mt-1">监控与操控智能体</p>
      </div>

      <div className="flex border-b border-slate-600/50">
        {[
          { id: "timeline" as TabId, label: "时间线" },
          { id: "metrics" as TabId, label: "EGL" },
          { id: "agents" as TabId, label: "智能体" },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex-1 py-2.5 text-xs font-medium transition-colors ${
              tab === t.id
                ? "text-evo-accent border-b-2 border-evo-accent"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        {tab === "agents" && (
          <section className="space-y-3">
            <h3 className="text-xs font-medium text-slate-400 uppercase tracking-wider">智能体</h3>
            <button
              onClick={createAgent}
              className="w-full py-2.5 px-4 bg-emerald-600/90 hover:bg-emerald-500 rounded-lg text-sm font-medium text-white transition-colors shadow-lg shadow-emerald-900/30 hover:shadow-emerald-800/40"
            >
              + 创建 Agent
            </button>
            <div className="rounded-lg bg-slate-900/50 border border-slate-600/50 p-3 min-h-[48px]">
              <p className="text-xs text-slate-500 mb-1">当前 Agent</p>
              {agents.length > 0 ? (
                <div className="space-y-1">
                  {agents.map((a) => (
                    <button
                      key={a.id}
                      onClick={() => setSelectedAgent(a.id)}
                      className={`w-full text-left px-2 py-1.5 rounded text-sm font-mono truncate transition-colors ${
                        selectedAgentId === a.id
                          ? "bg-evo-accent/20 text-evo-accent"
                          : "text-slate-300 hover:bg-slate-800/50"
                      }`}
                    >
                      · {a.id} <span className="text-amber-400">({a.balance})</span>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="text-slate-500 italic text-sm">暂无</p>
              )}
            </div>
          </section>
        )}

        {tab === "agents" && (
          <section className="space-y-3">
            <h3 className="text-xs font-medium text-slate-400 uppercase tracking-wider">任务与进化</h3>
            <TaskInjectorBar
              agents={agents}
              taskInput={taskInput}
              onTaskInputChange={setTaskInput}
              onInject={injectTask}
              onEvolve={triggerEvolve}
            />
          </section>
        )}

        {tab === "timeline" && <EvolutionTimeline agents={agents} />}
        {tab === "metrics" && <MetricsDashboard agents={agents} />}

        {(tab === "timeline" || tab === "metrics") && (
          <section className="pt-4 border-t border-slate-600/50">
            <TaskInjectorBar
              agents={agents}
              taskInput={taskInput}
              onTaskInputChange={setTaskInput}
              onInject={injectTask}
              onEvolve={triggerEvolve}
            />
          </section>
        )}
      </div>

      {selectedAgentId && (
        <AgentDetail
          agentId={selectedAgentId}
          onClose={() => setSelectedAgent(null)}
        />
      )}
    </div>
  );
}
