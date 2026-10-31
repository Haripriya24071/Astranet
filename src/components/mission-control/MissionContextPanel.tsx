import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  CheckCircle2,
  Flame,
  Loader2,
  RadioTower,
  Satellite,
  Waves,
} from "lucide-react";

interface MissionContextEvent {
  id: string;
  source: "NASA_EONET" | "USGS";
  title: string;
  category: string;
  latitude: number;
  longitude: number;
  timestamp?: string | null;
  magnitudeLabel?: string | null;
  severity: string;
}

interface LiveContext {
  generatedAt: string;
  classification: string;
  disclaimer: string;
  eventCount: number;
  events: MissionContextEvent[];
  sourceStatus: {
    nasaEonet: {
      ok: boolean;
      error?: string | null;
    };
    usgs: {
      ok: boolean;
      error?: string | null;
    };
  };
}

interface ObservationTask {
  taskId: string;
  createdAt: string;
  status: string;
  classification: string;
  priority: string;
  assignedSatelliteId: string;
  candidateDistanceKm: number;
  relayPath: string[];
  reason: string;
}

interface Props {
  apiBaseUrl: string;
}

export default function MissionContextPanel({
  apiBaseUrl,
}: Props) {
  const [context, setContext] =
    useState<LiveContext | null>(null);

  const [selectedId, setSelectedId] =
    useState<string>("");

  const [sourceFilter, setSourceFilter] =
    useState<"ALL" | "NASA_EONET" | "USGS">("ALL");

  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  const [error, setError] =
    useState<string | null>(null);

  const [task, setTask] =
    useState<ObservationTask | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchContext() {
      try {
        const response = await fetch(
          `${apiBaseUrl}/api/external/live-context`
        );

        if (!response.ok) {
          throw new Error(
            `Mission context HTTP ${response.status}`
          );
        }

        const payload: LiveContext =
          await response.json();

        if (!cancelled) {
          setContext(payload);

          setSelectedId((previous) => {
            if (
              previous &&
              payload.events.some(
                (event) => event.id === previous
              )
            ) {
              return previous;
            }

            return payload.events[0]?.id ?? "";
          });

          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to load mission context"
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchContext();

    const timer = window.setInterval(
      fetchContext,
      60000
    );

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [apiBaseUrl]);

  const filteredEvents = useMemo(() => {
    const events = context?.events ?? [];

    if (sourceFilter === "ALL") {
      return events;
    }

    return events.filter(
      (event) => event.source === sourceFilter
    );
  }, [context, sourceFilter]);

  const selected =
    context?.events.find(
      (event) => event.id === selectedId
    ) ?? filteredEvents[0] ?? null;

  async function createTask() {
    if (!selected || creating) return;

    try {
      setCreating(true);
      setTask(null);
      setError(null);

      const response = await fetch(
        `${apiBaseUrl}/api/mission/observation-task`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            eventId: selected.id,
            source: selected.source,
            title: selected.title,
            category: selected.category,
            latitude: selected.latitude,
            longitude: selected.longitude,
            timestamp: selected.timestamp,
            magnitudeLabel:
              selected.magnitudeLabel,
            priority:
              selected.severity === "CRITICAL"
                ? "CRITICAL"
                : "HIGH",
          }),
        }
      );

      if (!response.ok) {
        const body = await response
          .json()
          .catch(() => null);

        throw new Error(
          body?.detail ??
            `Task creation HTTP ${response.status}`
        );
      }

      const created: ObservationTask =
        await response.json();

      setTask(created);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to create observation task"
      );
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="h-full overflow-y-auto bg-[#05080D] p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between gap-5 mb-6">
          <div>
            <div className="text-[10px] uppercase tracking-[0.2em] text-[#6C7C8B]">
              Real-World Mission Intelligence
            </div>

            <h2 className="mt-2 text-xl font-medium text-white">
              Mission Context
            </h2>

            <p className="mt-1 text-xs leading-5 text-[#7F8C9A] max-w-2xl">
              NASA EONET and USGS events can be
              converted into simulated ASTRANET
              Earth-observation mission plans.
            </p>
          </div>

          <div className="text-right">
            <div className="text-[9px] uppercase tracking-[0.14em] text-[#617181]">
              Live Context
            </div>

            <div className="mt-1 text-lg text-white">
              {context?.eventCount ?? 0}
            </div>
          </div>
        </div>

        <div className="rounded-md border border-[#5C9FD6]/15 bg-[#5C9FD6]/[0.035] px-4 py-3 mb-5">
          <p className="text-[10px] leading-4 text-[#8CA0B2]">
            External events are real-world context.
            ASTRANET spacecraft telemetry and
            observation tasking are simulated
            digital-twin outputs.
          </p>
        </div>

        {error && (
          <div className="mb-4 rounded-md border border-red-400/20 bg-red-400/[0.05] px-4 py-3 text-xs text-red-300">
            {error}
          </div>
        )}

        <div className="grid lg:grid-cols-[380px_1fr] gap-5">
          <div className="rounded-lg border border-white/[0.08] bg-[#080D15] overflow-hidden">
            <div className="px-4 py-3 border-b border-white/[0.06] flex justify-between">
              <span className="text-[10px] uppercase tracking-[0.16em] text-[#8091A2]">
                Detected Events
              </span>

              <div className="flex gap-1">
                {(
                  [
                    "ALL",
                    "NASA_EONET",
                    "USGS",
                  ] as const
                ).map((filter) => (
                  <button
                    key={filter}
                    onClick={() =>
                      setSourceFilter(filter)
                    }
                    className={`px-2 py-0.5 rounded text-[8px] border ${
                      sourceFilter === filter
                        ? "border-[#5C9FD6]/30 text-[#B9D6EC] bg-[#5C9FD6]/10"
                        : "border-white/[0.06] text-[#617181]"
                    }`}
                  >
                    {filter === "NASA_EONET"
                      ? "NASA"
                      : filter}
                  </button>
                ))}
              </div>
            </div>

            {loading ? (
              <div className="py-16 grid place-items-center">
                <Loader2 className="w-5 h-5 animate-spin text-[#6CA6D9]" />
              </div>
            ) : (
              <div className="max-h-[620px] overflow-y-auto divide-y divide-white/[0.045]">
                {filteredEvents.map((event) => (
                  <button
                    key={`${event.source}-${event.id}`}
                    onClick={() => {
                      setSelectedId(event.id);
                      setTask(null);
                    }}
                    className={`w-full text-left px-4 py-3 transition-colors ${
                      selected?.id === event.id
                        ? "bg-[#5C9FD6]/10"
                        : "hover:bg-white/[0.025]"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-[9px] text-[#6E8192]">
                        {event.source ===
                        "NASA_EONET"
                          ? "NASA EONET"
                          : "USGS"}
                      </span>

                      <Severity
                        value={event.severity}
                      />
                    </div>

                    <div className="mt-1.5 text-xs text-[#E3EAF0] leading-4">
                      {event.title}
                    </div>

                    <div className="mt-2 text-[9px] text-[#617181]">
                      {event.category}
                      {event.magnitudeLabel
                        ? ` · ${event.magnitudeLabel}`
                        : ""}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-5">
            {selected ? (
              <>
                <div className="rounded-lg border border-white/[0.08] bg-[#080D15] p-5">
                  <div className="flex items-start justify-between gap-5">
                    <div>
                      <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.16em] text-[#7090AA]">
                        {selected.category
                          .toLowerCase()
                          .includes("wildfire") ? (
                          <Flame className="w-3.5 h-3.5 text-red-400" />
                        ) : selected.source ===
                          "USGS" ? (
                          <Waves className="w-3.5 h-3.5 text-amber-400" />
                        ) : (
                          <Activity className="w-3.5 h-3.5 text-[#6CA6D9]" />
                        )}

                        {selected.source}
                      </div>

                      <h3 className="mt-2 text-lg text-white font-medium">
                        {selected.title}
                      </h3>
                    </div>

                    <Severity
                      value={selected.severity}
                    />
                  </div>

                  <div className="grid sm:grid-cols-2 gap-3 mt-5">
                    <Detail
                      label="Category"
                      value={selected.category}
                    />

                    <Detail
                      label="Magnitude"
                      value={
                        selected.magnitudeLabel ??
                        "N/A"
                      }
                    />

                    <Detail
                      label="Latitude"
                      value={`${selected.latitude.toFixed(
                        3
                      )}°`}
                    />

                    <Detail
                      label="Longitude"
                      value={`${selected.longitude.toFixed(
                        3
                      )}°`}
                    />
                  </div>

                  <button
                    onClick={createTask}
                    disabled={creating}
                    className="mt-5 w-full sm:w-auto px-4 py-2.5 rounded-md border border-[#5C9FD6]/30 bg-[#5C9FD6]/10 hover:bg-[#5C9FD6]/15 text-xs text-[#C3DFF2] flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    {creating ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Satellite className="w-3.5 h-3.5" />
                    )}

                    Create Observation Task
                  </button>
                </div>

                {task && (
                  <div className="rounded-lg border border-emerald-400/20 bg-emerald-400/[0.035] p-5">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-5 h-5 text-emerald-400" />

                      <div>
                        <div className="text-sm font-medium text-emerald-300">
                          Observation Plan Created
                        </div>

                        <div className="text-[9px] text-[#71808F] mt-0.5">
                          {task.taskId} ·{" "}
                          {task.classification}
                        </div>
                      </div>
                    </div>

                    <div className="grid sm:grid-cols-2 gap-3 mt-5">
                      <Detail
                        label="Observer"
                        value={
                          task.assignedSatelliteId
                        }
                      />

                      <Detail
                        label="Candidate distance"
                        value={`${task.candidateDistanceKm.toFixed(
                          1
                        )} km`}
                      />

                      <Detail
                        label="Priority"
                        value={task.priority}
                      />

                      <Detail
                        label="Status"
                        value={task.status}
                      />
                    </div>

                    <div className="mt-4 rounded-md border border-white/[0.06] bg-black/15 px-4 py-3">
                      <div className="flex items-center gap-2 text-[9px] uppercase tracking-[0.14em] text-[#617181]">
                        <RadioTower className="w-3 h-3" />
                        Planned Relay Path
                      </div>

                      <div className="mt-2 text-xs text-[#C7D2DC]">
                        {task.relayPath.join(
                          "  →  "
                        )}
                      </div>
                    </div>

                    <p className="mt-3 text-[10px] leading-4 text-[#71808F]">
                      {task.reason}
                    </p>
                  </div>
                )}
              </>
            ) : (
              <div className="min-h-[350px] rounded-lg border border-dashed border-white/[0.08] grid place-items-center text-xs text-[#617181]">
                No external events available.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function Detail({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-md border border-white/[0.06] bg-white/[0.018] px-3 py-3">
      <div className="text-[9px] uppercase tracking-[0.13em] text-[#617181]">
        {label}
      </div>

      <div className="mt-1 text-xs text-[#D8E1E8]">
        {value}
      </div>
    </div>
  );
}

function Severity({
  value,
}: {
  value: string;
}) {
  const className =
    value === "CRITICAL"
      ? "text-red-300 border-red-400/20 bg-red-400/[0.06]"
      : value === "HIGH"
      ? "text-orange-300 border-orange-400/20 bg-orange-400/[0.06]"
      : value === "MEDIUM"
      ? "text-amber-300 border-amber-400/20 bg-amber-400/[0.06]"
      : "text-[#8FC5EA] border-[#5C9FD6]/20 bg-[#5C9FD6]/[0.06]";

  return (
    <span
      className={`px-2 py-0.5 rounded border text-[8px] font-medium ${className}`}
    >
      {value}
    </span>
  );
}
