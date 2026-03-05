/**
 * WarriorPortraitCanvas — 像素武将立绘 Canvas 组件
 * 吞食天地2 NES/FC 风格，32×48 native → 3× 缩放显示 96×144
 */
import { useEffect, useRef } from "react";
import {
  WARRIORS,
  PORTRAIT_W,
  PORTRAIT_H,
  drawWarriorPortrait,
  getWarriorForAgent,
  type WarriorId,
} from "../phaser/warriorPortraits";

interface Props {
  /** 直接指定武将 ID，优先于 agentDisplayName */
  warriorId?: WarriorId;
  /** agent 显示名，用于自动匹配武将 */
  agentDisplayName?: string;
  /** 像素缩放倍率，默认 3（96×144px） */
  scale?: number;
  /** 额外 className */
  className?: string;
  /** 是否显示名称+官职标签条 */
  showLabel?: boolean;
}

export function WarriorPortraitCanvas({
  warriorId,
  agentDisplayName,
  scale = 3,
  className = "",
  showLabel = true,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // 确定武将
  const wid: WarriorId =
    warriorId ?? (agentDisplayName ? getWarriorForAgent(agentDisplayName) : "generic");
  const info = WARRIORS[wid];

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.imageSmoothingEnabled = false;
    ctx.save();
    ctx.scale(scale, scale);
    drawWarriorPortrait(ctx, wid);
    ctx.restore();
  }, [wid, scale]);

  const px = (n: number) => `${n * scale}px`;

  return (
    <div
      className={`inline-flex flex-col items-center select-none ${className}`}
      style={{ width: px(PORTRAIT_W) }}
    >
      {/* 立绘 canvas */}
      <div
        className="relative overflow-hidden rounded-sm"
        style={{
          width: px(PORTRAIT_W),
          height: px(PORTRAIT_H),
          boxShadow: `0 0 0 1px #000, 0 0 12px ${info.color}66`,
        }}
      >
        <canvas
          ref={canvasRef}
          width={PORTRAIT_W * scale}
          height={PORTRAIT_H * scale}
          style={{
            imageRendering: "pixelated",
            display: "block",
            width: px(PORTRAIT_W),
            height: px(PORTRAIT_H),
          }}
        />
        {/* 阵营标记角标 */}
        <div
          className="absolute top-0 right-0 px-1 text-[9px] font-bold leading-4"
          style={{
            background: info.factionColor + "CC",
            color: "#fff",
            textShadow: "0 1px 2px #000",
          }}
        >
          {info.faction}
        </div>
      </div>

      {/* 名称 + 官职条 */}
      {showLabel && (
        <div
          className="w-full mt-0.5 rounded-b text-center leading-tight"
          style={{
            background: "linear-gradient(180deg, #0C1020 0%, #060810 100%)",
            border: `1px solid ${info.color}66`,
            borderTop: "none",
          }}
        >
          <div
            className="text-[11px] font-bold tracking-wider px-1 pt-0.5"
            style={{ color: info.color, textShadow: `0 0 6px ${info.color}` }}
          >
            {info.name}
          </div>
          <div className="text-[9px] text-slate-400 px-1 pb-0.5 truncate leading-tight">
            {info.title}
          </div>
        </div>
      )}
    </div>
  );
}

