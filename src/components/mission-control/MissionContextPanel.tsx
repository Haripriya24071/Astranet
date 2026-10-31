import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  Activity,
  CheckCircle2,
  Flame,
  Loader2,
  Play,
  RadioTower,
  Satellite,
  Waves,
} from "lucide-react";

interface ContextEvent {
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
  events: ContextEvent[];
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
  status: string;
  classification: string;
  priority: string;
  assignedSatelliteId: string;
  candidateDistanceKm: number;
  relayPath: string[];
  networkReachable: boolean;
  progressPct: number;
  plannedDurationSec: number;
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
    useState("");

  const [sourceFilter, setSourceFilter] =
    useState<
      "ALL" | "NASA_EONET" | "USGS"
    >("ALL");

  const [loading, setLoading] =
    useState(true);

  const [creating, setCreating] =
    useState(false);

  const [executing, setExecuting] =
    useState(false);

  const [task, setTask] =
    useState<ObservationTask | null>(
      null
    );

  const [error, setError] =
    useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadContext() {
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
                (event) =>
                  event.id === previous
              )
            ) {
              return previous;
            }

            return (
              payload.events[0]?.id ?? ""
            );
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

    loadContext();

    const timer = window.setInterval(
      loadContext,
      60000
    );

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [apiBaseUrl]);

  useEffect(() => {
    if (!task) return;

    const timer = window.setInterval(
      async () => {
        try {
          const response = await fetch(
            `${apiBaseUrl}/api/mission/observation-tasks`
          );

          if (!response.ok) return;

          const tasks:
            ObservationTask[] =
            await response.json();

          const updated = tasks.find(
            (candidate) =>
              candidate.taskId ===
              task.taskId
          );

          if (updated) {
            setTask(updated);
          }
        } catch {
          // Live telemetry will retry.
        }
      },
      700
    );

    return () =>
      window.clearInterval(timer);
  }, [apiBaseUrl, task?.taskId]);

  const filteredEvents =
    useMemo(() => {
      const events =
        context?.events ?? [];

      if (sourceFilter === "ALL") {
        return events;
      }

      return events.filter(
        (event) =>
          event.source === sourceFilter
      );
    }, [context, sourceFilter]);

  const selected =
    context?.events.find(
      (event) =>
        event.id === selectedId
    ) ??
    filteredEvents[0] ??
    null;

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
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            eventId: selected.id,
            source: selected.source,
            title: selected.title,
            category:
              selected.category,
            latitude:
              selected.latitude,
            longitude:
              selected.longitude,
            timestamp:
              selected.timestamp,
            magnitudeLabel:
              selected.magnitudeLabel,
            priority:
              selected.severity ===
              "CRITICAL"
                ? "CRITICAL"
                : "HIGH",
          }),
        }
      );

      const payload =
        await response.json();

      if (!response.ok) {
        throw new Error(
          payload?.detail ??
            "Task planning failed"
        );
      }

      setTask(payload);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Task planning failed"
      );
    } finally {
      setCreating(false);
    }
  }

  async function executeTask() {
    if (
      !task ||
      task.status !== "PLANNED"
    ) {
      return;
    }

    try {
      setExecuting(true);
      setError(null);

      const response = await fetch(
        `${apiBaseUrl}/api/mission/observation-task/${task.taskId}/execute`,
        {
          method: "POST",
        }
      );

      const payload =
        await response.json();

      if (!response.ok) {
        throw new Error(
          payload?.detail ??
            "Task execution failed"
        );
      }

      setTask(payload);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Task execution failed"
      );
    } finally {
      setExecuting(false);
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
              Convert current NASA EONET
              and USGS events into simulated
              autonomous ASTRANET
              Earth-observation tasks.
            </p>
          </div>

          <div className="text-right">
            <div className="text-[9px] uppercase tracking-[0.14em] text-[#617181]">
              Events
            </div>

            <div className="mt-1 text-xl text-white">
              {context?.eventCount ?? 0}
            </div>
          </div>
        </div>

        <div className="mb-5 px-4 py-3 rounded-md border border-[#5C9FD6]/15 bg-[#5C9FD6]/[0.035] text-[10px] leading-4 text-[#8CA0B2]">
          External event data is real-world
          context. The ASTRANET spacecraft,
          assignment, relay selection and
          observation execution are simulated
          digital-twin outputs.
        </div>

        {error && (
          <div className="mb-4 px-4 py-3 rounded-md border border-red-400/20 bg-red-400/[0.05] text-xs text-red-300">
            {error}
          </div>
        )}

        <div className="grid lg:grid-cols-[380px_1fr] gap-5">
          <div className="rounded-lg border border-white/[0.08] bg-[#080D15] overflow-hidden">
            <div className="px-4 py-3 border-b border-white/[0.06] flex items-center justify-between">
              <span className="text-[10px] uppercase tracking-[0.16em] text-[#8091A2]">
                Live Events
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
                      setSourceFilter(
                        filter
                      )
                    }
                    className={`px-2 py-0.5 rounded border text-[8px] ${
                      sourceFilter ===
                      filter
                        ? "border-[#5C9FD6]/30 bg-[#5C9FD6]/10 text-[#B9D6EC]"
                        : "border-white/[0.06] text-[#617181]"
                    }`}
                  >
                    {filter ===
                    "NASA_EONET"
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
              <div className="max-h-[610px] overflow-y-auto divide-y divide-white/[0.045]">
                {filteredEvents.map(
                  (event) => (
                    <button
                      key={`${event.source}-${event.id}`}
                      onClick={() => {
                        setSelectedId(
                          event.id
                        );
                        setTask(null);
                      }}
                      className={`w-full text-left px-4 py-3 ${
                        selected?.id ===
                        event.id
                          ? "bg-[#5C9FD6]/10"
                          : "hover:bg-white/[0.025]"
                      }`}
                    >
                      <div className="flex justify-between gap-3">
                        <span className="text-[9px] text-[#6E8192]">
                          {event.source ===
                          "NASA_EONET"
                            ? "NASA EONET"
                            : "USGS"}
                        </span>

                        <Severity
                          value={
                            event.severity
                          }
                        />
                      </div>

                      <div className="mt-1.5 text-xs leading-4 text-[#E3EAF0]">
                        {event.title}
                      </div>

                      <div className="mt-2 text-[9px] text-[#617181]">
                        {event.category}
                        {event.magnitudeLabel
                          ? ` · ${event.magnitudeLabel}`
                          : ""}
                      </div>
                    </button>
                  )
                )}
              </div>
            )}
          </div>

          <div className="space-y-5">
            {selected && (
              <div className="rounded-lg border border-white/[0.08] bg-[#080D15] p-5">
                <div className="flex justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.15em] text-[#7090AA]">
                      {selected.category
                        .toLowerCase()
                        .includes(
                          "wildfire"
                        ) ? (
                        <Flame className="w-3.5 h-3.5 text-red-400" />
                      ) : selected.source ===
                        "USGS" ? (
                        <Waves className="w-3.5 h-3.5 text-amber-400" />
                      ) : (
                        <Activity className="w-3.5 h-3.5 text-[#6CA6D9]" />
                      )}

                      {selected.source}
                    </div>

                    <h3 className="mt-2 text-lg font-medium text-white">
                      {selected.title}
                    </h3>
                  </div>

                  <Severity
                    value={
                      selected.severity
                    }
                  />
                </div>

                <div className="grid sm:grid-cols-2 gap-3 mt-5">
                  <Detail
                    label="Category"
                    value={
                      selected.category
                    }
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
                  className="mt-5 px-4 py-2.5 rounded-md border border-[#5C9FD6]/30 bg-[#5C9FD6]/10 hover:bg-[#5C9FD6]/15 text-xs text-[#C3DFF2] flex items-center gap-2 disabled:opacity-50"
                >
                  {creating ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Satellite className="w-3.5 h-3.5" />
                  )}

                  Create Observation Plan
                </button>
              </div>
            )}

            {task && (
              <div
                className={`rounded-lg border p-5 ${
                  task.status ===
                  "COMPLETED"
                    ? "border-emerald-400/20 bg-emerald-400/[0.035]"
                    : task.status ===
                      "ABORTED"
                    ? "border-red-400/20 bg-red-400/[0.035]"
                    : "border-[#5C9FD6]/20 bg-[#5C9FD6]/[0.025]"
                }`}
              >
                <div className="flex justify-between items-start gap-4">
                  <div className="flex items-center gap-2.5">
                    {task.status ===
                    "COMPLETED" ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    ) : (
                      <Satellite className="w-5 h-5 text-[#7FB4DD]" />
                    )}

                    <div>
                      <div className="text-sm font-medium text-white">
                        {task.taskId}
                      </div>

                      <div className="mt-0.5 text-[9px] text-[#71808F]">
                        {
                          task.classification
                        }
                      </div>
                    </div>
                  </div>

                  <span className="text-[10px] text-[#A9B8C5]">
                    {task.status}
                  </span>
                </div>

                <div className="grid sm:grid-cols-2 gap-3 mt-5">
                  <Detail
                    label="Assigned Observer"
                    value={
                      task.assignedSatelliteId
                    }
                  />

                  <Detail
                    label="Ground-track Distance"
                    value={`${task.candidateDistanceKm.toFixed(
                      1
                    )} km`}
                  />

                  <Detail
                    label="Priority"
                    value={task.priority}
                  />

                  <Detail
                    label="Network"
                    value={
                      task.networkReachable
                        ? "REACHABLE"
                        : "LOCAL ONLY"
                    }
                  />
                </div>

                <div className="mt-4 rounded-md border border-white/[0.06] bg-black/15 px-4 py-3">
                  <div className="flex items-center gap-2 text-[9px] uppercase tracking-[0.14em] text-[#617181]">
                    <RadioTower className="w-3 h-3" />
                    Relay Path
                  </div>

                  <div className="mt-2 text-xs text-[#C7D2DC]">
                    {task.relayPath.join(
                      "  →  "
                    )}
                  </div>
                </div>

                {(task.status ===
                  "EXECUTING" ||
                  task.status ===
                    "COMPLETED") && (
                  <div className="mt-4">
                    <div className="flex justify-between text-[9px] text-[#71808F] mb-1.5">
                      <span>
                        Observation execution
                      </span>

                      <span>
                        {task.progressPct.toFixed(
                          0
                        )}
                        %
                      </span>
                    </div>

                    <div className="h-1.5 rounded-full bg-white/[0.07] overflow-hidden">
                      <div
                        className="h-full bg-[#6CA6D9] transition-all duration-500"
                        style={{
                          width: `${task.progressPct}%`,
                        }}
                      />
                    </div>
                  </div>
                )}

                {task.status ===
                  "PLANNED" && (
                  <button
                    onClick={executeTask}
                    disabled={executing}
                    className="mt-4 px-4 py-2 rounded-md border border-emerald-400/25 bg-emerald-400/[0.07] hover:bg-emerald-400/[0.12] text-xs text-emerald-300 flex items-center gap-2"
                  >
                    {executing ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Play className="w-3.5 h-3.5" />
                    )}

                    Execute Mission Task
                  </button>
                )}

                <p className="mt-4 text-[10px] leading-4 text-[#71808F]">
                  {task.reason}
                </p>
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
      className={`px-2 py-0.5 rounded border text-[8px] ${className}`}
    >
      {value}
    </span>
  );
}
