import { useState } from "react";
import {
  Activity,
  AlertTriangle,
  Network,
  Radio,
  Satellite,
  ShieldCheck,
  Trophy,
} from "lucide-react";

import type {
  MissionEvent,
  NetworkSummary,
  SatelliteTelemetry,
  SwarmSummary,
} from "../../data/mockMissionControl";

interface LiveGlobeHUDProps {
  satellites: SatelliteTelemetry[];
  events: MissionEvent[];
  networkMetrics: NetworkSummary | null;
  swarmSummary: SwarmSummary | null;
  isConnected: boolean;
  onOpenTournament?: () => void;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

export default function LiveGlobeHUD({
  satellites,
  events,
  networkMetrics,
  swarmSummary,
  isConnected,
  onOpenTournament,
}: LiveGlobeHUDProps) {
  const total = swarmSummary?.total ?? satellites.length;

  const nominal =
    swarmSummary?.nominal ??
    satellites.filter((sat) => sat.state === "NOMINAL").length;

  const degraded =
    swarmSummary?.degraded ??
    satellites.filter((sat) =>
      ["WARNING", "SUSPECTED", "DEGRADED", "RECOVERING"].includes(sat.state)
    ).length;

  const failed =
    swarmSummary?.failed ??
    satellites.filter((sat) =>
      ["FAILED", "ISOLATED"].includes(sat.state)
    ).length;

  const operational = Math.max(0, total - failed);

  const missionHealth =
    total > 0
      ? (degraded === 0 && failed === 0)
        ? 100
        : clamp(
            Math.round(((nominal * 1.0 + degraded * 0.6) / total) * (failed > 0 ? 82 : 92)),
            10,
            96
          )
      : 0;

  const activeRecovery = satellites.some((sat) =>
    [
      "WARNING",
      "SUSPECTED",
      "DEGRADED",
      "FAILED",
      "ISOLATED",
      "RECOVERING",
    ].includes(sat.state)
  );

  const recoveryEvents = events
    .filter(
      (event) =>
        event.type === "RECOVERY" ||
        event.type === "FAULT" ||
        event.category === "RECOVERY"
    )
    .slice(0, 4);

  const missionState =
    (failed > 0 || degraded > 0)
      ? (swarmSummary?.missionState && swarmSummary.missionState !== "NOMINAL"
          ? swarmSummary.missionState
          : (failed >= 3 ? "SURVIVAL" : (failed > 0 ? "DEGRADED-B" : "DEGRADED-A")))
      : (swarmSummary?.missionState ?? "NOMINAL");

  const coordinator =
    swarmSummary?.coordinatorId ??
    satellites.find((sat) => sat.role === "COORDINATOR")?.id ??
    "UNASSIGNED";

  const [isHudMinimized, setIsHudMinimized] = useState<boolean>(false);

  return (
    <div className="pointer-events-none absolute inset-0 z-20 overflow-hidden">
      {/* Top-Right HUD Toggle Minimizer */}
      <div className="pointer-events-auto absolute top-4 right-4 z-30">
        <button
          onClick={() => setIsHudMinimized(!isHudMinimized)}
          title={isHudMinimized ? "Expand HUD metrics" : "Minimize HUD to clear globe"}
          className="px-2 py-1 rounded bg-[#071019]/70 hover:bg-[#071019]/90 border border-white/10 text-[10px] text-[#AAB7C4] hover:text-white transition-colors cursor-pointer flex items-center gap-1.5 backdrop-blur-md"
        >
          <span>{isHudMinimized ? "👁 Show HUD" : "👁 Minimize HUD"}</span>
        </button>
      </div>

      {!isHudMinimized && (
        <>
          {/* TOP-LEFT: Consolidated Constellation & Mission Health Card (w-56) */}
          <div className="pointer-events-auto absolute left-4 top-4 w-56">
            <div className="border border-white/10 bg-[#071019]/75 backdrop-blur-md rounded-lg shadow-xl shadow-black/20 overflow-hidden">
              {/* Header */}
              <div className="px-3 py-2 border-b border-white/[0.07] flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <Satellite className="w-3.5 h-3.5 text-[#B7C8D8]" />
                  <span className="text-xs font-semibold tracking-tight text-white">
                    ASTRANET-12
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      isConnected ? "bg-emerald-400 animate-pulse" : "bg-red-400"
                    }`}
                  />
                  <span className="text-[9px] text-[#718397] font-mono">
                    {isConnected ? "LIVE" : "MOCK"}
                  </span>
                </div>
              </div>

              {/* Counts */}
              <div className="grid grid-cols-3 divide-x divide-white/[0.07] py-1.5 bg-black/20 text-center">
                <div>
                  <div className="text-[8px] text-[#718397] uppercase">Active</div>
                  <div className="text-xs font-medium text-white">{operational}</div>
                </div>
                <div>
                  <div className="text-[8px] text-[#718397] uppercase">Degraded</div>
                  <div className={`text-xs font-medium ${degraded > 0 ? "text-amber-400" : "text-[#718397]"}`}>
                    {degraded}
                  </div>
                </div>
                <div>
                  <div className="text-[8px] text-[#718397] uppercase">Failed</div>
                  <div className={`text-xs font-medium ${failed > 0 ? "text-red-400" : "text-[#718397]"}`}>
                    {failed}
                  </div>
                </div>
              </div>

              {/* Health & Mission State */}
              <div className="px-3 py-2 space-y-1.5 border-t border-white/[0.07]">
                <div className="flex items-center justify-between">
                  <span className="text-[9px] uppercase tracking-wider text-[#718397]">
                    Mission Health
                  </span>
                  <span className={`text-xs font-bold font-mono ${
                    missionHealth >= 80
                      ? "text-emerald-400"
                      : missionHealth >= 55
                      ? "text-amber-400"
                      : "text-red-400"
                  }`}>
                    {missionHealth}%
                  </span>
                </div>
                <div className="h-1 rounded-full bg-white/[0.07] overflow-hidden">
                  <div
                    className={`h-full transition-all duration-500 ${
                      missionHealth >= 80
                        ? "bg-emerald-400"
                        : missionHealth >= 55
                        ? "bg-amber-400"
                        : "bg-red-400"
                    }`}
                    style={{ width: `${missionHealth}%` }}
                  />
                </div>
                <div className="flex items-center justify-between pt-0.5">
                  <span className="text-[9px] text-[#718397] uppercase">State</span>
                  <span
                    className={`text-[9px] font-bold px-1.5 py-0.5 rounded tracking-wide ${
                      missionState === "NOMINAL"
                        ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                        : missionState.includes("DEGRADED")
                        ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                        : "bg-red-500/20 text-red-300 border border-red-500/30"
                    }`}
                  >
                    {missionState}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* TOP-RIGHT: Compact Swarm Network Card (w-48) */}
          <div className="pointer-events-auto absolute right-4 top-12 w-48">
            <div className="border border-white/10 bg-[#071019]/75 backdrop-blur-md rounded-lg shadow-xl shadow-black/20 p-2.5 space-y-1.5 text-xs">
              <div className="flex items-center justify-between border-b border-white/[0.07] pb-1.5">
                <div className="flex items-center gap-1.5">
                  <Network className="w-3 h-3 text-[#9FB4C8]" />
                  <span className="text-[10px] uppercase tracking-wider text-[#9FB4C8] font-medium">
                    RF ISL Net
                  </span>
                </div>
                <span className={`text-[8px] font-bold ${networkMetrics?.connected ? "text-emerald-400" : "text-amber-400"}`}>
                  {networkMetrics?.connected ? "CONNECTED" : "DISTRIBUTED"}
                </span>
              </div>
              <div className="space-y-1 text-[10px]">
                <div className="flex justify-between">
                  <span className="text-[#718397]">Active Links:</span>
                  <span className="text-white font-mono">{networkMetrics?.activeLinks ?? 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#718397]">Partitions:</span>
                  <span className={(networkMetrics?.partitionCount ?? 0) > 1 ? "text-amber-400 font-mono" : "text-white font-mono"}>
                    {networkMetrics?.partitionCount ?? 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#718397]">Avg Latency:</span>
                  <span className="text-white font-mono">
                    {networkMetrics ? `${networkMetrics.averageLatencyMs.toFixed(1)}ms` : "—"}
                  </span>
                </div>
                <div className="flex justify-between border-t border-white/[0.05] pt-1">
                  <span className="text-[#718397]">Coordinator:</span>
                  <span className="text-cyan-400 font-mono font-medium">{coordinator}</span>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Autonomous Recovery Active Banner */}

      {activeRecovery && (
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 w-[560px] max-w-[calc(100%-40px)] pointer-events-auto">
          <div className="border border-amber-300/15 bg-[#090D12]/94 backdrop-blur-xl rounded-lg overflow-hidden shadow-2xl shadow-black/40">
            <div className="h-[2px] bg-amber-400/70" />

            <div className="px-4 py-3 flex items-center justify-between border-b border-white/[0.07]">
              <div className="flex items-center gap-2.5">
                <AlertTriangle className="w-4 h-4 text-amber-400" />

                <div>
                  <div className="text-[10px] tracking-[0.2em] uppercase text-amber-300">
                    Autonomous Recovery Active
                  </div>

                  <div className="text-[11px] text-[#7F8C9A] mt-0.5">
                    Swarm resilience engine is resolving mission degradation
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {onOpenTournament && (
                  <button
                    onClick={onOpenTournament}
                    className="px-2.5 py-1 rounded bg-cyan-500/15 hover:bg-cyan-500/25 border border-cyan-500/30 text-cyan-300 text-[10px] font-medium transition-colors cursor-pointer flex items-center gap-1.5"
                    title="View counterfactual recovery tournament"
                  >
                    <Trophy className="w-3.5 h-3.5 text-cyan-400" />
                    <span>View Tournament</span>
                  </button>
                )}
                <div className="flex items-center gap-1.5 text-[10px] text-[#AAB7C4]">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  SELF-HEAL
                </div>
              </div>
            </div>

            <div className="grid grid-cols-4 divide-x divide-white/[0.06]">
              {["DETECT", "VERIFY", "RECONFIGURE", "STABILIZE"].map(
                (stage, index) => {
                  const completedStages = failed > 0 || degraded > 0 ? 2 : 0;

                  return (
                    <div key={stage} className="px-3 py-3">
                      <div className="flex items-center gap-2">
                        <div
                          className={`w-1.5 h-1.5 rounded-full ${
                            index < completedStages
                              ? "bg-emerald-400"
                              : index === completedStages
                              ? "bg-amber-400 animate-pulse"
                              : "bg-white/20"
                          }`}
                        />

                        <span className="text-[9px] tracking-[0.15em] text-[#AAB7C4]">
                          {stage}
                        </span>
                      </div>
                    </div>
                  );
                }
              )}
            </div>

            {recoveryEvents.length > 0 && (
              <div className="px-4 py-2.5 bg-white/[0.025] border-t border-white/[0.05]">
                <div className="flex gap-2 items-start">
                  <span className="text-[9px] text-[#637282] tabular-nums pt-[1px]">
                    {recoveryEvents[0].timestamp}
                  </span>

                  <span className="text-[10px] text-[#AAB7C4] leading-relaxed">
                    {recoveryEvents[0].message}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Metric({
  label,
  value,
  sub,
  warning = false,
  critical = false,
}: {
  label: string;
  value: string;
  sub?: string;
  warning?: boolean;
  critical?: boolean;
}) {
  return (
    <div className="px-3 py-3 text-center">
      <div className="text-[9px] tracking-[0.14em] text-[#687887]">
        {label}
      </div>

      <div
        className={`mt-1 text-[16px] font-medium ${
          critical
            ? "text-red-400"
            : warning
            ? "text-amber-400"
            : "text-[#E9EFF4]"
        }`}
      >
        {value}

        {sub && (
          <span className="ml-1 text-[9px] font-normal text-[#667583]">
            {sub}
          </span>
        )}
      </div>
    </div>
  );
}

function DataRow({
  label,
  value,
  accent = false,
  warn = false,
}: {
  label: string;
  value: string;
  accent?: boolean;
  warn?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-[10px] text-[#708090]">{label}</span>

      <span
        className={`text-[10px] tabular-nums font-medium ${
          warn
            ? "text-amber-400"
            : accent
            ? "text-[#BBD5EA]"
            : "text-[#D5DEE6]"
        }`}
      >
        {value}
      </span>
    </div>
  );
}
