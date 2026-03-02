/** Evotown 全局状态 — 进化事件、Agent 列表、选中 Agent */
import { create } from "zustand";

export interface AgentInfo {
  id: string;
  balance: number;
  chat_dir?: string;
  status?: string;
}

export interface EvolutionEventItem {
  agent_id: string;
  ts: string;
  type: string;
  target_id?: string;
  reason?: string;
  version?: string;
  event_type?: string;
}

export interface MetricsPoint {
  date: string;
  egl?: number;
  first_success_rate?: number;
  avg_replans?: number;
}

interface EvotownState {
  agents: AgentInfo[];
  evolutionEvents: EvolutionEventItem[];
  selectedAgentId: string | null;
  metricsCache: Record<string, MetricsPoint[]>;
  evolutionLogCache: Record<string, EvolutionEventItem[]>;

  setAgents: (agents: AgentInfo[]) => void;
  addAgent: (agent: AgentInfo) => void;
  updateAgentBalance: (agentId: string, balance: number) => void;
  removeAgent: (agentId: string) => void;

  pushEvolutionEvent: (ev: EvolutionEventItem) => void;
  setEvolutionLog: (agentId: string, log: EvolutionEventItem[]) => void;
  getEvolutionLog: (agentId: string) => EvolutionEventItem[];

  setSelectedAgent: (id: string | null) => void;
  setMetricsCache: (agentId: string, data: MetricsPoint[]) => void;
  getMetrics: (agentId: string) => MetricsPoint[];
}

export const useEvotownStore = create<EvotownState>((set, get) => ({
  agents: [],
  evolutionEvents: [],
  selectedAgentId: null,
  metricsCache: {},
  evolutionLogCache: {},

  setAgents: (agents) => set({ agents }),
  addAgent: (agent) => set((s) => ({ agents: [...s.agents, agent] })),
  updateAgentBalance: (agentId, balance) =>
    set((s) => ({
      agents: s.agents.map((a) => (a.id === agentId ? { ...a, balance } : a)),
    })),
  removeAgent: (agentId) =>
    set((s) => ({
      agents: s.agents.filter((a) => a.id !== agentId),
      selectedAgentId: s.selectedAgentId === agentId ? null : s.selectedAgentId,
    })),

  pushEvolutionEvent: (ev) =>
    set((s) => ({
      evolutionEvents: [...s.evolutionEvents, ev].slice(-200),
    })),

  setEvolutionLog: (agentId, log) =>
    set((s) => ({
      evolutionLogCache: { ...s.evolutionLogCache, [agentId]: log },
    })),

  getEvolutionLog: (agentId) => get().evolutionLogCache[agentId] ?? [],

  setSelectedAgent: (id) => set({ selectedAgentId: id }),
  setMetricsCache: (agentId, data) =>
    set((s) => ({
      metricsCache: { ...s.metricsCache, [agentId]: data },
    })),
  getMetrics: (agentId) => get().metricsCache[agentId] ?? [],
}));
