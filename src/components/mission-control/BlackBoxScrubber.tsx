import React from "react";
import { Play, Pause, RotateCcw, AlertTriangle, Trophy, Radio, FastForward } from "lucide-react";
import type { TelemetryFrame } from "../../data/mockMissionControl";

interface BlackBoxScrubberProps {
  historyFrames: TelemetryFrame[];
  scrubIndex: number | null;
  isScrubbing: boolean;
  isBlackBoxPlaying: boolean;
  onScrubTo: (index: number | null) => void;
  onTogglePlayback: () => void;
  onJumpToAnomaly: () => void;
  onJumpToDecision: () => void;
  onJumpToLive: () => void;
}

export default function BlackBoxScrubber({
  historyFrames,
  scrubIndex,
  isScrubbing,
  isBlackBoxPlaying,
  onScrubTo,
  onTogglePlayback,
  onJumpToAnomaly,
  onJumpToDecision,
  onJumpToLive,
}: BlackBoxScrubberProps) {
  const totalFrames = historyFrames.length;
  if (totalFrames < 2) return null;

  const currentIdx = scrubIndex !== null ? scrubIndex : totalFrames - 1;
  const currentFrame = historyFrames[currentIdx];

  const hasAnomaly = historyFrames.some(
    (f) =>
      f.satellites.some((s) => s.state !== "NOMINAL") ||
      (f.events && f.events.some((e) => e.type === "FAULT" || e.severity === "critical"))
  );

  const hasDecision = historyFrames.some((f) => Boolean(f.latestDecision));

  const formatSimTime = (sec?: number) => {
    if (sec === undefined) return "T+ 00:00:00";
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = Math.floor(sec % 60);
    return `T+ ${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  };

  return (
    <div className="w-full bg-[#070D18]/90 backdrop-blur-md border-t border-cyan-500/20 px-4 py-1.5 flex items-center justify-between gap-4 text-xs select-none z-20">
      {/* Left: Recording Status & Quick Jumpers */}
      <div className="flex items-center gap-2.5 shrink-0">
        <div className="flex items-center gap-1.5 font-mono text-[11px]">
          {isScrubbing ? (
            <span className="flex items-center gap-1 text-amber-400 font-semibold px-2 py-0.5 rounded bg-amber-400/10 border border-amber-400/25 animate-pulse">
              <RotateCcw className="w-3 h-3 animate-spin" style={{ animationDuration: "3s" }} />
              BLACK BOX REPLAY
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-emerald-400 font-medium px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              FLIGHT RECORDER (LIVE)
            </span>
          )}
        </div>

        {/* Play/Pause Button */}
        <button
          onClick={onTogglePlayback}
          title={isBlackBoxPlaying ? "Pause Replay" : "Play Replay"}
          className="p-1 rounded bg-white/[0.06] hover:bg-white/[0.12] text-white border border-white/10 transition-colors cursor-pointer"
        >
          {isBlackBoxPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
        </button>

        {/* Timestamp */}
        <div className="font-mono text-cyan-300 text-[11px] tabular-nums tracking-wide">
          {formatSimTime(currentFrame?.clock?.elapsedSec)}
        </div>
      </div>

      {/* Center: Timeline Scrubber Slider with Anomaly Markers */}
      <div className="flex-1 max-w-2xl relative flex items-center gap-2">
        <span className="text-[10px] text-gray-500 font-mono shrink-0">
          -{Math.max(0, Math.round(((totalFrames - 1 - currentIdx) * 0.1)))}s
        </span>

        <div className="relative flex-1 flex items-center">
          <input
            type="range"
            min={0}
            max={totalFrames - 1}
            value={currentIdx}
            onChange={(e) => {
              const val = parseInt(e.target.value, 10);
              onScrubTo(val === totalFrames - 1 ? null : val);
            }}
            className="w-full h-1.5 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-cyan-400 focus:outline-none"
          />

          {/* Quick markers for anomalies on track */}
          {historyFrames.map((f, i) => {
            const isAnomaly =
              f.satellites.some((s) => s.state !== "NOMINAL") ||
              (f.events && f.events.some((e) => e.type === "FAULT"));
            if (!isAnomaly) return null;
            const leftPct = (i / (totalFrames - 1)) * 100;
            return (
              <span
                key={i}
                className="absolute w-1 h-2.5 bg-rose-500 rounded-full pointer-events-none -translate-x-1/2 opacity-75"
                style={{ left: `${leftPct}%` }}
                title="Fault Injected"
              />
            );
          })}
        </div>

        <span className="text-[10px] text-gray-400 font-mono shrink-0">
          {isScrubbing ? "HISTORICAL" : "LIVE EDGE"}
        </span>
      </div>

      {/* Right: Quick Jump Actions */}
      <div className="flex items-center gap-2 shrink-0 text-[11px]">
        {hasAnomaly && (
          <button
            onClick={onJumpToAnomaly}
            title="Fast forward / rewind to anomaly inception moment"
            className="px-2 py-0.5 rounded bg-rose-500/15 hover:bg-rose-500/25 border border-rose-500/30 text-rose-300 flex items-center gap-1 transition-colors cursor-pointer"
          >
            <AlertTriangle className="w-3 h-3 text-rose-400" />
            <span>Anomaly</span>
          </button>
        )}

        {hasDecision && (
          <button
            onClick={onJumpToDecision}
            title="Jump to Autonomous Tournament Decision"
            className="px-2 py-0.5 rounded bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-500/30 text-cyan-300 flex items-center gap-1 transition-colors cursor-pointer"
          >
            <Trophy className="w-3 h-3 text-cyan-400" />
            <span>Decision</span>
          </button>
        )}

        {isScrubbing && (
          <button
            onClick={onJumpToLive}
            title="Snap back to Real-Time Telemetry Stream"
            className="px-2.5 py-0.5 rounded bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300 font-medium flex items-center gap-1 transition-colors cursor-pointer animate-pulse"
          >
            <FastForward className="w-3 h-3 text-emerald-400" />
            <span>Snap LIVE</span>
          </button>
        )}
      </div>
    </div>
  );
}
