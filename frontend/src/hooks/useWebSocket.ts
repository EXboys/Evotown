import { useEffect, useRef, useState } from "react";
import { evotownEvents } from "../phaser/events";
import { useEvotownStore } from "../store/evotownStore";

const WS_URL = import.meta.env.DEV ? "ws://localhost:5174/ws" : `ws://${location.host}/ws`;

export function useWebSocket() {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout>>();
  const pushEvolutionEvent = useEvotownStore((s) => s.pushEvolutionEvent);
  const updateAgentBalance = useEvotownStore((s) => s.updateAgentBalance);
  const removeAgent = useEvotownStore((s) => s.removeAgent);

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(WS_URL);
      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        reconnectRef.current = setTimeout(connect, 3000);
      };
      ws.onerror = () => {};
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          if (msg.type === "sprite_move") evotownEvents.emit("sprite_move", msg);
          else if (msg.type === "task_complete") {
            evotownEvents.emit("task_complete", msg);
            if (msg.balance != null) updateAgentBalance(msg.agent_id, msg.balance);
          } else if (msg.type === "agent_eliminated") {
            evotownEvents.emit("agent_eliminated", msg);
            removeAgent(msg.agent_id);
          } else if (msg.type === "evolution_event") {
            evotownEvents.emit("evolution_event", msg);
            pushEvolutionEvent({
              agent_id: msg.agent_id,
              ts: msg.timestamp ?? msg.ts ?? new Date().toISOString(),
              type: msg.event_type ?? msg.type ?? "evolution",
              target_id: msg.target_id,
              reason: msg.reason,
              version: msg.version,
            });
          }
        } catch {}
      };
      wsRef.current = ws;
    };
    connect();
    return () => {
      clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, [pushEvolutionEvent, updateAgentBalance, removeAgent]);

  return { connected };
}
