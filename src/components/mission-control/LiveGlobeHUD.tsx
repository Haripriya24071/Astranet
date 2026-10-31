import {
  Activity,
  AlertTriangle,
  Network,
  Radio,
  Satellite,
  ShieldCheck,
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
      ? clamp(
          Math.round(((nominal + degraded * 0.6) / total) * 100),
          0,
          100
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
    swarmSummary?.missionState ??
    (activeRecovery ? "RECOVERY ACTIVE" : "NOMINAL");

  const coordinator =
    swarmSummary?.coordinatorId ??
    satellites.find((sat) => sat.role === "COORDINATOR")?.id ??
    "UNASSIGNED";

  return (
    <div className="pointer-events-none absolute inset-0 z-20">
      <div className="absolute left-5 top-5 w-[260px]">
        <div className="border border-white/10 bg-[#071019]/82 backdrop-blur-md rounded-lg shadow-2xl shadow-black/20">
          <div className="px-4 pt-3.5 pb-3 border-b border-white/[0.07]">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-[10px] tracking-[0.22em] text-[#718397] uppercase">
                  Constellation
                </div>

                <div className="mt-1 flex items-center gap-2">
                  <Satellite className="w-4 h-4 text-[#B7C8D8]" />

                  <span className="text-[14px] font-medium tracking-tight text-white">
                    ASTRANET-12
                  </span>
                </div>
              </div>

              <div
                className={`w-2 h-2 rounded-full ${
                  isConnected ? "bg-emerald-400" : "bg-red-400"
                }`}
              />
            </div>
          </div>

          <div className="grid grid-cols-3 divide-x divide-white/[0.07]">
            <Metric label="ACTIVE" value={`${operational}`} sub={`of ${total}`} />

            <Metric
              label="DEGRADED"
              value={`${degraded}`}
              warning={degraded > 0}
            />

            <Metric
              label="FAILED"
              value={`${failed}`}
              critical={failed > 0}
            />
          </div>
        </div>
      </div>

      <div className="absolute left-5 top-[160px] w-[260px]">
        <div className="border border-white/10 bg-[#071019]/82 backdrop-blur-md rounded-lg px-4 py-3.5">
          <div className="flex justify-between items-start">
            <div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-[#718397]">
                Mission integrity
              </div>

              <div className="mt-1 text-[28px] leading-none text-white font-light tracking-tight">
                {missionHealth}
                <span className="text-[13px] text-[#718397] ml-1">%</span>
              </div>
            </div>

            <Activity
              className={`w-4 h-4 ${
                missionHealth >= 80
                  ? "text-emerald-400"
                  : missionHealth >= 55
                  ? "text-amber-400"
                  : "text-red-400"
              }`}
            />
          </div>

          <div className="mt-3 h-[3px] rounded-full bg-white/[0.07] overflow-hidden">
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

          <div className="mt-3 flex justify-between items-center">
            <span className="text-[10px] uppercase tracking-[0.14em] text-[#718397]">
              Mission state
            </span>

            <span
              className={`text-[10px] font-medium tracking-[0.1em] ${
                activeRecovery ? "text-amber-300" : "text-emerald-300"
              }`}
            >
              {missionState}
            </span>
          </div>
        </div>
      </div>

      <div className="absolute right-5 top-5 w-[245px]">
        <div className="border border-white/10 bg-[#071019]/82 backdrop-blur-md rounded-lg">
          <div className="px-4 py-3 border-b border-white/[0.07] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Network className="w-3.5 h-3.5 text-[#9FB4C8]" />

              <span className="text-[10px] uppercase tracking-[0.18em] text-[#9FB4C8]">
                Swarm network
              </span>
            </div>

            <span
              className={`text-[9px] tracking-[0.12em] ${
                networkMetrics?.connected
                  ? "text-emerald-400"
                  : "text-amber-400"
              }`}
            >
              {networkMetrics?.connected ? "CONNECTED" : "DISTRIBUTED"}
            </span>
          </div>

          <div className="px-4 py-3 space-y-2.5">
            <DataRow
              label="Active links"
              value={`${networkMetrics?.activeLinks ?? 0}`}
            />

            <DataRow
              label="Partitions"
              value={`${networkMetrics?.partitionCount ?? 0}`}
              warn={(networkMetrics?.partitionCount ?? 0) > 1}
            />

            <DataRow
              label="Avg. latency"
              value={
                networkMetrics
                  ? `${networkMetrics.averageLatencyMs.toFixed(2)} ms`
                  : "—"
              }
            />

            <DataRow label="Coordinator" value={coordinator} accent />
          </div>
        </div>
      </div>

      <div className="absolute top-5 left-1/2 -translate-x-1/2">
        <div className="px-4 py-2 rounded-full border border-white/[0.09] bg-black/35 backdrop-blur-md flex items-center gap-3">
          <Radio className="w-3.5 h-3.5 text-[#8EA6BA]" />

          <span className="text-[10px] uppercase tracking-[0.22em] text-[#C3D0DC]">
            Autonomous Swarm Digital Twin
          </span>

          <div className="h-3 w-px bg-white/10" />

          <span
            className={`text-[9px] uppercase tracking-[0.14em] ${
              isConnected ? "text-emerald-400" : "text-red-400"
            }`}
          >
            {isConnected ? "Live telemetry" : "Offline fallback"}
          </span>
        </div>
      </div>

      {activeRecovery && (
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 w-[560px] max-w-[calc(100%-40px)]">
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

              <div className="flex items-center gap-1.5 text-[10px] text-[#AAB7C4]">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                SELF-HEAL
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
