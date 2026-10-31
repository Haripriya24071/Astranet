import { useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Cpu,
  Network,
  Radio,
  Satellite,
} from "lucide-react";

import type {
  AutonomySummary,
  MissionEvent,
  NetworkSummary,
  SatelliteTelemetry,
  SwarmSummary,
} from "../../data/mockMissionControl";

type Mode = "Swarm" | "Telemetry" | "Events";

interface Props {
  mode: Mode;
  satellites: SatelliteTelemetry[];
  events: MissionEvent[];
  networkMetrics: NetworkSummary | null;
  swarmSummary: SwarmSummary | null;
  autonomy: AutonomySummary | null;
  selectedSatelliteId: string;
  onSelectSatellite: (id: string) => void;
}

export default function MissionDataPanel({
  mode,
  satellites,
  events,
  networkMetrics,
  swarmSummary,
  autonomy,
  selectedSatelliteId,
  onSelectSatellite,
}: Props) {
  if (mode === "Swarm") {
    return (
      <SwarmView
        satellites={satellites}
        networkMetrics={networkMetrics}
        swarmSummary={swarmSummary}
        autonomy={autonomy}
        selectedSatelliteId={selectedSatelliteId}
        onSelectSatellite={onSelectSatellite}
      />
    );
  }

  if (mode === "Telemetry") {
    return (
      <TelemetryView
        satellites={satellites}
        selectedSatelliteId={selectedSatelliteId}
        onSelectSatellite={onSelectSatellite}
      />
    );
  }

  return <EventsView events={events} />;
}

function SwarmView({
  satellites,
  networkMetrics,
  swarmSummary,
  autonomy,
  selectedSatelliteId,
  onSelectSatellite,
}: Omit<Props, "mode" | "events">) {
  const coordinator =
    swarmSummary?.coordinatorId ??
    satellites.find((sat) => sat.role === "COORDINATOR")?.id ??
    "NONE";

  return (
    <PanelShell
      eyebrow="Distributed Constellation"
      title="Swarm Status"
      description="Live health, roles, network participation and autonomous recovery state across all 12 CubeSats."
    >
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
        <TopMetric
          label="Nominal"
          value={swarmSummary?.nominal ?? 0}
          accent="green"
        />

        <TopMetric
          label="Degraded"
          value={swarmSummary?.degraded ?? 0}
          accent="amber"
        />

        <TopMetric
          label="Failed"
          value={swarmSummary?.failed ?? 0}
          accent="red"
        />

        <TopMetric
          label="Coordinator"
          value={coordinator}
          accent="blue"
        />
      </div>

      <div className="grid xl:grid-cols-[1fr_260px] gap-5">
        <div className="rounded-lg border border-white/[0.08] bg-[#080D15] overflow-hidden">
          <div className="grid grid-cols-[90px_1fr_110px_100px_90px_90px] px-4 py-2.5 border-b border-white/[0.06] text-[9px] uppercase tracking-[0.14em] text-[#617181]">
            <span>Node</span>
            <span>Assignment</span>
            <span>Role</span>
            <span>State</span>
            <span>Battery</span>
            <span>Peers</span>
          </div>

          <div className="divide-y divide-white/[0.045]">
            {satellites.map((sat) => {
              const selected = sat.id === selectedSatelliteId;

              return (
                <button
                  key={sat.id}
                  onClick={() => onSelectSatellite(sat.id)}
                  className={`w-full grid grid-cols-[90px_1fr_110px_100px_90px_90px] items-center px-4 py-3 text-left transition-colors ${
                    selected
                      ? "bg-[#5C9FD6]/10"
                      : "hover:bg-white/[0.025]"
                  }`}
                >
                  <span className="text-xs font-medium text-white">
                    {sat.id}
                  </span>

                  <span className="text-[10px] text-[#8493A2]">
                    {sat.plane} · {sat.slot}
                  </span>

                  <span className="text-[10px] text-[#B4C2CE]">
                    {sat.role}
                  </span>

                  <StateText state={sat.state} />

                  <span className="text-[10px] text-[#D8E0E7] tabular-nums">
                    {sat.battery.toFixed(0)}%
                  </span>

                  <span className="text-[10px] text-[#D8E0E7] tabular-nums">
                    {sat.network.neighbors}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="space-y-4">
          <InfoCard title="Network">
            <InfoLine
              label="Active links"
              value={`${networkMetrics?.activeLinks ?? 0}`}
            />
            <InfoLine
              label="Partitions"
              value={`${networkMetrics?.partitionCount ?? 0}`}
            />
            <InfoLine
              label="Latency"
              value={
                networkMetrics
                  ? `${networkMetrics.averageLatencyMs.toFixed(1)} ms`
                  : "—"
              }
            />
            <InfoLine
              label="Topology"
              value={
                networkMetrics?.connected
                  ? "CONNECTED"
                  : "PARTITIONED"
              }
            />
          </InfoCard>

          <InfoCard title="Autonomy Engine">
            <InfoLine
              label="Status"
              value={autonomy?.engineStatus ?? "MONITORING"}
            />
            <InfoLine
              label="Active tasks"
              value={`${autonomy?.activeTaskCount ?? 0}`}
            />
            <InfoLine
              label="Leadership"
              value={
                autonomy?.leadershipUnresolved
                  ? "UNRESOLVED"
                  : "STABLE"
              }
            />

            <div className="pt-3 mt-3 border-t border-white/[0.06]">
              <div className="text-[9px] uppercase tracking-[0.13em] text-[#617181]">
                Latest Decision
              </div>

              <p className="mt-2 text-[10px] leading-4 text-[#9CAAB7]">
                {autonomy?.latestDecision ??
                  "Autonomy engine monitoring swarm health"}
              </p>
            </div>
          </InfoCard>
        </div>
      </div>
    </PanelShell>
  );
}

function TelemetryView({
  satellites,
  selectedSatelliteId,
  onSelectSatellite,
}: Pick<
  Props,
  "satellites" | "selectedSatelliteId" | "onSelectSatellite"
>) {
  return (
    <PanelShell
      eyebrow="Live Digital Twin"
      title="Spacecraft Telemetry"
      description="Authoritative simulation telemetry streamed from the FastAPI backend."
    >
      <div className="rounded-lg border border-white/[0.08] bg-[#080D15] overflow-x-auto">
        <table className="w-full min-w-[1050px] text-left">
          <thead className="border-b border-white/[0.06]">
            <tr className="text-[9px] uppercase tracking-[0.13em] text-[#617181]">
              <th className="px-4 py-3">Node</th>
              <th className="px-3 py-3">State</th>
              <th className="px-3 py-3">Latitude</th>
              <th className="px-3 py-3">Longitude</th>
              <th className="px-3 py-3">Altitude</th>
              <th className="px-3 py-3">Velocity</th>
              <th className="px-3 py-3">Battery</th>
              <th className="px-3 py-3">Propellant</th>
              <th className="px-3 py-3">Compute</th>
              <th className="px-3 py-3">Trust</th>
              <th className="px-3 py-3">Links</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-white/[0.045]">
            {satellites.map((sat) => (
              <tr
                key={sat.id}
                onClick={() => onSelectSatellite(sat.id)}
                className={`cursor-pointer ${
                  selectedSatelliteId === sat.id
                    ? "bg-[#5C9FD6]/10"
                    : "hover:bg-white/[0.025]"
                }`}
              >
                <td className="px-4 py-3 text-xs font-medium text-white">
                  {sat.id}
                </td>

                <td className="px-3 py-3">
                  <StateText state={sat.state} />
                </td>

                <TelemetryCell
                  value={
                    sat.position
                      ? `${sat.position.lat.toFixed(2)}°`
                      : "—"
                  }
                />

                <TelemetryCell
                  value={
                    sat.position
                      ? `${sat.position.lon.toFixed(2)}°`
                      : "—"
                  }
                />

                <TelemetryCell
                  value={
                    sat.position
                      ? `${sat.position.altKm.toFixed(1)} km`
                      : `${sat.altitudeKm.toFixed(1)} km`
                  }
                />

                <TelemetryCell
                  value={
                    sat.velocity
                      ? `${sat.velocity.speedKmS.toFixed(3)} km/s`
                      : "—"
                  }
                />

                <TelemetryCell value={`${sat.battery.toFixed(1)}%`} />
                <TelemetryCell value={`${sat.propellant.toFixed(1)}%`} />
                <TelemetryCell value={`${sat.compute.toFixed(1)}%`} />
                <TelemetryCell value={sat.trust.toFixed(3)} />
                <TelemetryCell value={`${sat.network.neighbors}`} />
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </PanelShell>
  );
}

function EventsView({ events }: Pick<Props, "events">) {
  const [filter, setFilter] =
    useState<"ALL" | "FAULT" | "RECOVERY" | "NETWORK">("ALL");

  const filtered = useMemo(() => {
    if (filter === "ALL") return events;

    return events.filter((event) => {
      if (filter === "FAULT") {
        return (
          event.type === "FAULT" ||
          event.category === "FAULTS"
        );
      }

      if (filter === "RECOVERY") {
        return (
          event.type === "RECOVERY" ||
          event.category === "RECOVERY"
        );
      }

      return (
        event.type === "TOPOLOGY" ||
        event.category === "NETWORK"
      );
    });
  }, [events, filter]);

  return (
    <PanelShell
      eyebrow="Mission Log"
      title="Events"
      description="Chronological fault, recovery, network and mission decisions generated by the simulation."
    >
      <div className="flex gap-2 mb-4">
        {(["ALL", "FAULT", "RECOVERY", "NETWORK"] as const).map(
          (item) => (
            <button
              key={item}
              onClick={() => setFilter(item)}
              className={`px-3 py-1.5 rounded-md text-[10px] border transition-colors ${
                filter === item
                  ? "border-[#5C9FD6]/30 bg-[#5C9FD6]/10 text-[#BCD7EB]"
                  : "border-white/[0.07] text-[#71808F] hover:text-white"
              }`}
            >
              {item}
            </button>
          )
        )}
      </div>

      <div className="rounded-lg border border-white/[0.08] bg-[#080D15] overflow-hidden">
        {filtered.length === 0 ? (
          <div className="py-16 text-center text-xs text-[#617181]">
            No events in this category.
          </div>
        ) : (
          <div className="divide-y divide-white/[0.05]">
            {filtered.map((event) => (
              <div
                key={event.id}
                className="grid grid-cols-[90px_110px_110px_1fr] gap-3 px-4 py-3"
              >
                <span className="text-[10px] font-mono text-[#617181]">
                  {event.timestamp}
                </span>

                <span className="text-[10px] text-[#8FA0AF]">
                  {event.satelliteId ?? "SWARM"}
                </span>

                <EventType event={event} />

                <span className="text-[10px] leading-4 text-[#C0CBD5]">
                  {event.message}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </PanelShell>
  );
}

function PanelShell({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="h-full overflow-y-auto bg-[#05080D] p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-6">
          <div className="text-[10px] uppercase tracking-[0.2em] text-[#6C7C8B]">
            {eyebrow}
          </div>

          <h2 className="mt-2 text-xl font-medium text-white">
            {title}
          </h2>

          <p className="mt-1 text-xs leading-5 text-[#7F8C9A]">
            {description}
          </p>
        </div>

        {children}
      </div>
    </div>
  );
}

function TopMetric({
  label,
  value,
  accent,
}: {
  label: string;
  value: string | number;
  accent: "green" | "amber" | "red" | "blue";
}) {
  const classes = {
    green: "text-emerald-300",
    amber: "text-amber-300",
    red: "text-red-300",
    blue: "text-[#8FC5EA]",
  };

  return (
    <div className="rounded-lg border border-white/[0.08] bg-[#080D15] p-4">
      <div className="text-[9px] uppercase tracking-[0.14em] text-[#617181]">
        {label}
      </div>

      <div className={`mt-2 text-xl font-medium ${classes[accent]}`}>
        {value}
      </div>
    </div>
  );
}

function InfoCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-white/[0.08] bg-[#080D15] p-4">
      <div className="text-[10px] uppercase tracking-[0.15em] text-[#8091A2] mb-3">
        {title}
      </div>

      <div className="space-y-2.5">
        {children}
      </div>
    </div>
  );
}

function InfoLine({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-[10px] text-[#71808F]">
        {label}
      </span>

      <span className="text-[10px] text-[#D8E1E8] text-right">
        {value}
      </span>
    </div>
  );
}

function StateText({ state }: { state: string }) {
  const className =
    state === "NOMINAL"
      ? "text-emerald-400"
      : state === "FAILED" || state === "ISOLATED"
      ? "text-red-400"
      : state === "RECOVERING"
      ? "text-[#6CA6D9]"
      : "text-amber-400";

  return (
    <span className={`text-[10px] font-medium ${className}`}>
      {state}
    </span>
  );
}

function TelemetryCell({ value }: { value: string }) {
  return (
    <td className="px-3 py-3 text-[10px] text-[#B8C4CE] tabular-nums">
      {value}
    </td>
  );
}

function EventType({ event }: { event: MissionEvent }) {
  let className = "text-[#8FA0AF]";
  let Icon = Activity;

  if (
    event.type === "FAULT" ||
    event.severity === "critical"
  ) {
    className = "text-red-400";
    Icon = AlertTriangle;
  } else if (event.type === "RECOVERY") {
    className = "text-emerald-400";
    Icon = Cpu;
  } else if (
    event.type === "TOPOLOGY" ||
    event.category === "NETWORK"
  ) {
    className = "text-[#6CA6D9]";
    Icon = Network;
  } else if (event.type === "TELEMETRY") {
    Icon = Radio;
  } else {
    Icon = Satellite;
  }

  return (
    <span className={`flex items-center gap-1.5 text-[10px] ${className}`}>
      <Icon className="w-3 h-3" />
      {event.type}
    </span>
  );
}
