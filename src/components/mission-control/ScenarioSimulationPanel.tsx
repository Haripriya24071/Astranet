import { useEffect, useState } from "react";
import {
  CheckCircle2,
  FlaskConical,
  Loader2,
  Play,
  XCircle,
} from "lucide-react";

interface ScenarioMeta {
  id: string;
  name: string;
  description: string;
  version: string;
  durationSec: number;
  faultCount: number;
  isStochastic: boolean;
}

interface MetricSnapshot {
  nominal_count: number;
  degraded_count: number;
  failed_count: number;
  isolated_count: number;
  active_links_count: number;
  partition_count: number;
  coordinator_id: string;
  average_battery: number;
  average_propellant: number;
}

interface AcceptanceCheck {
  name: string;
  passed: boolean;
  details: string;
}

interface ScenarioResult {
  scenario_id: string;
  scenario_name: string;
  status: "PASS" | "FAIL" | "INCONCLUSIVE";
  duration_sim_sec: number;
  steps_executed: number;
  wall_clock_duration_sec: number;
  baseline_metrics: MetricSnapshot;
  final_metrics: MetricSnapshot;
  faults_injected_count: number;
  autonomous_events_count: number;
  no_manual_intervention: boolean;
  acceptance_checks: AcceptanceCheck[];
  failure_reasons: string[];
  completed_recoveries: Array<Record<string, unknown>>;
  role_reassignments: Array<Record<string, unknown>>;
}

interface Props {
  apiBaseUrl: string;
}

export default function ScenarioSimulationPanel({
  apiBaseUrl,
}: Props) {
  const [scenarios, setScenarios] = useState<ScenarioMeta[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [listLoading, setListLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadScenarios() {
      try {
        setListLoading(true);

        const response = await fetch(`${apiBaseUrl}/api/scenarios`);

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data: ScenarioMeta[] = await response.json();

        if (!cancelled) {
          setScenarios(data);
          setSelectedId(data[0]?.id ?? "");
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to load scenarios"
          );
        }
      } finally {
        if (!cancelled) {
          setListLoading(false);
        }
      }
    }

    loadScenarios();

    return () => {
      cancelled = true;
    };
  }, [apiBaseUrl]);

  async function runScenario(id: string) {
    if (!id || loading) return;

    try {
      setLoading(true);
      setError(null);
      setResult(null);

      const response = await fetch(
        `${apiBaseUrl}/api/scenarios/run/${encodeURIComponent(id)}`,
        {
          method: "POST",
        }
      );

      if (!response.ok) {
        const payload = await response.json().catch(() => null);

        throw new Error(
          payload?.detail ??
            `Scenario execution failed: HTTP ${response.status}`
        );
      }

      const data: ScenarioResult = await response.json();
      setResult(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Scenario execution failed"
      );
    } finally {
      setLoading(false);
    }
  }

  const selected =
    scenarios.find((scenario) => scenario.id === selectedId) ??
    null;

  return (
    <div className="h-full overflow-y-auto bg-[#05080D] p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-start justify-between gap-6 mb-6">
          <div>
            <div className="flex items-center gap-2">
              <FlaskConical className="w-4 h-4 text-[#7FB4DD]" />

              <span className="text-[10px] uppercase tracking-[0.2em] text-[#7F8C9A]">
                Phase 6 Validation
              </span>
            </div>

            <h2 className="mt-2 text-xl font-medium text-white">
              Resilience Scenario Benchmarks
            </h2>

            <p className="mt-1 text-xs text-[#7F8C9A] max-w-2xl leading-5">
              Execute deterministic swarm-failure scenarios against the
              autonomous recovery engine and evaluate quantitative
              acceptance criteria.
            </p>
          </div>

          <div className="px-3 py-2 rounded-md border border-white/10 bg-white/[0.025]">
            <div className="text-[9px] uppercase tracking-[0.16em] text-[#617181]">
              Scenarios
            </div>

            <div className="mt-1 text-lg text-white">
              {scenarios.length}
            </div>
          </div>
        </div>

        <div className="grid lg:grid-cols-[340px_1fr] gap-5">
          <div className="rounded-lg border border-white/[0.08] bg-[#080D15] overflow-hidden">
            <div className="px-4 py-3 border-b border-white/[0.07]">
              <span className="text-[10px] uppercase tracking-[0.17em] text-[#8091A2]">
                Benchmark library
              </span>
            </div>

            <div className="p-2 space-y-1.5">
              {listLoading && (
                <div className="py-10 flex justify-center">
                  <Loader2 className="w-4 h-4 animate-spin text-[#6CA6D9]" />
                </div>
              )}

              {!listLoading &&
                scenarios.map((scenario) => {
                  const active = scenario.id === selectedId;

                  return (
                    <button
                      key={scenario.id}
                      onClick={() => {
                        setSelectedId(scenario.id);
                        setResult(null);
                      }}
                      className={`w-full text-left rounded-md px-3 py-3 border transition-colors ${
                        active
                          ? "border-[#5C9FD6]/35 bg-[#5C9FD6]/10"
                          : "border-transparent hover:bg-white/[0.035]"
                      }`}
                    >
                      <div className="flex justify-between gap-3">
                        <span className="text-xs text-[#E5ECF2] font-medium">
                          {scenario.name}
                        </span>

                        {scenario.isStochastic && (
                          <span className="text-[8px] px-1.5 py-0.5 rounded border border-violet-400/20 text-violet-300">
                            SEEDED
                          </span>
                        )}
                      </div>

                      <div className="mt-2 flex gap-3 text-[9px] text-[#617181]">
                        <span>{scenario.durationSec}s SIM</span>
                        <span>{scenario.faultCount} FAULTS</span>
                      </div>
                    </button>
                  );
                })}
            </div>
          </div>

          <div className="space-y-5">
            {selected && (
              <div className="rounded-lg border border-white/[0.08] bg-[#080D15] p-5">
                <div className="flex justify-between gap-6">
                  <div>
                    <div className="text-[10px] uppercase tracking-[0.16em] text-[#617181]">
                      {selected.id}
                    </div>

                    <h3 className="mt-1 text-base text-white font-medium">
                      {selected.name}
                    </h3>

                    <p className="mt-2 text-xs leading-5 text-[#8493A2] max-w-3xl">
                      {selected.description}
                    </p>
                  </div>

                  <button
                    onClick={() => runScenario(selected.id)}
                    disabled={loading}
                    className="shrink-0 h-9 px-4 rounded-md border border-[#5C9FD6]/30 bg-[#5C9FD6]/10 hover:bg-[#5C9FD6]/15 text-xs text-[#B9D6EC] disabled:opacity-50 flex items-center gap-2"
                  >
                    {loading ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Play className="w-3.5 h-3.5" />
                    )}

                    {loading ? "Running" : "Run benchmark"}
                  </button>
                </div>
              </div>
            )}

            {error && (
              <div className="rounded-lg border border-red-400/20 bg-red-400/[0.05] px-4 py-3 text-xs text-red-300">
                {error}
              </div>
            )}

            {!result && !loading && (
              <div className="rounded-lg border border-dashed border-white/[0.08] bg-white/[0.015] min-h-[300px] grid place-items-center">
                <div className="text-center">
                  <FlaskConical className="w-7 h-7 mx-auto text-[#354452]" />

                  <div className="mt-3 text-xs text-[#71808F]">
                    Select a scenario and run the benchmark.
                  </div>
                </div>
              </div>
            )}

            {loading && (
              <div className="rounded-lg border border-white/[0.08] bg-[#080D15] min-h-[300px] grid place-items-center">
                <div className="text-center">
                  <Loader2 className="w-6 h-6 mx-auto animate-spin text-[#6CA6D9]" />

                  <div className="mt-3 text-xs text-[#8493A2]">
                    Running isolated deterministic simulation…
                  </div>
                </div>
              </div>
            )}

            {result && (
              <>
                <div
                  className={`rounded-lg border p-5 ${
                    result.status === "PASS"
                      ? "border-emerald-400/20 bg-emerald-400/[0.035]"
                      : "border-red-400/20 bg-red-400/[0.035]"
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div className="flex items-center gap-3">
                      {result.status === "PASS" ? (
                        <CheckCircle2 className="w-6 h-6 text-emerald-400" />
                      ) : (
                        <XCircle className="w-6 h-6 text-red-400" />
                      )}

                      <div>
                        <div
                          className={`text-lg font-semibold ${
                            result.status === "PASS"
                              ? "text-emerald-300"
                              : "text-red-300"
                          }`}
                        >
                          {result.status}
                        </div>

                        <div className="text-xs text-[#8090A0]">
                          {result.scenario_name}
                        </div>
                      </div>
                    </div>

                    <div className="text-right text-[10px] text-[#71808F]">
                      <div>
                        {result.duration_sim_sec.toFixed(1)}s simulation
                      </div>

                      <div className="mt-1">
                        {result.wall_clock_duration_sec.toFixed(3)}s wall time
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-5">
                    <ResultMetric
                      label="Faults injected"
                      value={result.faults_injected_count}
                    />

                    <ResultMetric
                      label="Autonomy events"
                      value={result.autonomous_events_count}
                    />

                    <ResultMetric
                      label="Recovery actions"
                      value={result.completed_recoveries.length}
                    />

                    <ResultMetric
                      label="Manual intervention"
                      value={result.no_manual_intervention ? "NONE" : "REQUIRED"}
                    />
                  </div>
                </div>

                <div className="grid md:grid-cols-2 gap-5">
                  <MetricCard
                    title="Baseline"
                    metrics={result.baseline_metrics}
                  />

                  <MetricCard
                    title="Final State"
                    metrics={result.final_metrics}
                  />
                </div>

                <div className="rounded-lg border border-white/[0.08] bg-[#080D15] overflow-hidden">
                  <div className="px-4 py-3 border-b border-white/[0.07] text-[10px] uppercase tracking-[0.16em] text-[#8091A2]">
                    Acceptance checks
                  </div>

                  <div className="divide-y divide-white/[0.05]">
                    {result.acceptance_checks.map((check) => (
                      <div
                        key={check.name}
                        className="px-4 py-3 flex gap-3"
                      >
                        {check.passed ? (
                          <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0 text-emerald-400" />
                        ) : (
                          <XCircle className="w-4 h-4 mt-0.5 shrink-0 text-red-400" />
                        )}

                        <div>
                          <div className="text-xs text-[#D7E0E8]">
                            {check.name}
                          </div>

                          <div className="mt-1 text-[10px] leading-4 text-[#71808F]">
                            {check.details}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function ResultMetric({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-md border border-white/[0.07] bg-black/15 px-3 py-3">
      <div className="text-[9px] uppercase tracking-[0.13em] text-[#617181]">
        {label}
      </div>

      <div className="mt-1 text-sm text-white">
        {value}
      </div>
    </div>
  );
}

function MetricCard({
  title,
  metrics,
}: {
  title: string;
  metrics: MetricSnapshot;
}) {
  return (
    <div className="rounded-lg border border-white/[0.08] bg-[#080D15] p-4">
      <div className="text-[10px] uppercase tracking-[0.16em] text-[#8091A2]">
        {title}
      </div>

      <div className="grid grid-cols-2 gap-x-5 gap-y-3 mt-4 text-xs">
        <MetricLine label="Nominal" value={metrics.nominal_count} />
        <MetricLine label="Degraded" value={metrics.degraded_count} />
        <MetricLine label="Failed" value={metrics.failed_count} />
        <MetricLine label="Isolated" value={metrics.isolated_count} />
        <MetricLine label="Active links" value={metrics.active_links_count} />
        <MetricLine label="Partitions" value={metrics.partition_count} />
        <MetricLine label="Coordinator" value={metrics.coordinator_id} />
        <MetricLine
          label="Avg. battery"
          value={`${metrics.average_battery.toFixed(1)}%`}
        />
      </div>
    </div>
  );
}

function MetricLine({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="flex justify-between gap-3 border-b border-white/[0.04] pb-2">
      <span className="text-[#71808F]">{label}</span>
      <span className="text-[#D8E1E8] tabular-nums">{value}</span>
    </div>
  );
}
