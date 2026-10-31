import { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  CheckCircle2,
  RefreshCw,
  Radio,
} from "lucide-react";

import type {
  SatelliteTelemetry,
} from "../../data/mockMissionControl";

import { useIntelligence } from "../../hooks/useIntelligence";
import DiagnosticDrawer from "./DiagnosticDrawer";

interface IntelligencePanelProps {
  apiBaseUrl: string;
  satellites: SatelliteTelemetry[];
  selectedSatelliteId: string;
  onSelectSatellite: (id: string) => void;
}

function statusClass(status: string): string {
  if (status === "ANOMALOUS") {
    return "text-[#F59E0B] border-[#F59E0B]/20 bg-[#F59E0B]/8";
  }

  if (status === "NOMINAL") {
    return "text-[#10B981] border-[#10B981]/20 bg-[#10B981]/8";
  }

  return "text-[#AAB7C4] border-white/10 bg-white/[0.03]";
}

function formatValue(
  value: string | number | boolean | null
): string {
  if (value === null) {
    return "—";
  }

  if (typeof value === "boolean") {
    return value ? "TRUE" : "FALSE";
  }

  if (typeof value === "number") {
    return Number.isInteger(value)
      ? String(value)
      : value.toFixed(3);
  }

  return value;
}

export default function IntelligencePanel({
  apiBaseUrl,
  satellites,
  selectedSatelliteId,
  onSelectSatellite,
}: IntelligencePanelProps) {
  const {
    analysis,
    isLoading,
    error,
    analyzeSatellite,
    resetAnalysis,
  } = useIntelligence(apiBaseUrl);

  const [
    isDiagnosticOpen,
    setIsDiagnosticOpen,
  ] = useState(false);

  const selectedSatellite =
    satellites.find(
      (satellite) =>
        satellite.id === selectedSatelliteId
    ) ?? satellites[0];

  useEffect(() => {
    resetAnalysis();
    setIsDiagnosticOpen(false);
  }, [
    selectedSatelliteId,
    resetAnalysis,
  ]);

  if (!selectedSatellite) {
    return (
      <div className="flex-1 grid place-items-center bg-[#05080D]">
        <p className="text-sm text-[#7F8C9A]">
          No spacecraft telemetry available.
        </p>
      </div>
    );
  }

  const score =
    analysis?.anomalyScore !== null &&
    analysis?.anomalyScore !== undefined
      ? analysis.anomalyScore.toFixed(3)
      : "—";

  return (
    <div className="flex-1 overflow-y-auto bg-[#05080D]">
      <div className="max-w-6xl mx-auto px-7 py-7">
        <div className="flex flex-col gap-5">
          <div className="flex items-start justify-between gap-6">
            <div>
              <div className="flex items-center gap-2 text-[#75AFE0]">
                <BrainCircuit className="w-4 h-4" />
                <span className="text-[11px] uppercase tracking-[0.18em] font-medium">
                  Mission Intelligence
                </span>
              </div>

              <h1 className="mt-2 text-xl font-semibold tracking-tight text-white">
                Predictive Health Intelligence
              </h1>

              <p className="mt-1 max-w-2xl text-xs leading-5 text-[#7F8C9A]">
                Analyze current digital-twin telemetry for unusual behaviour.
                The model output is an anomaly score, not a calibrated
                probability of spacecraft failure.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <select
                value={selectedSatellite.id}
                onChange={(event) =>
                  onSelectSatellite(
                    event.target.value
                  )
                }
                className="h-9 rounded-md border border-white/10 bg-[#080D15] px-3 text-xs text-[#D9E4EC] outline-none focus:border-[#5C9FD6]/50"
              >
                {satellites.map(
                  (satellite) => (
                    <option
                      key={satellite.id}
                      value={satellite.id}
                    >
                      {satellite.id} ·{" "}
                      {satellite.role}
                    </option>
                  )
                )}
              </select>

              <button
                type="button"
                disabled={!analysis || isLoading}
                onClick={() =>
                  setIsDiagnosticOpen(true)
                }
                className="h-9 inline-flex items-center gap-2 rounded-md border border-white/10 bg-white/[0.03] px-3 text-xs font-medium text-[#AAB7C4] hover:bg-white/[0.06] hover:text-white disabled:cursor-not-allowed disabled:opacity-35 transition-colors"
              >
                <BrainCircuit className="w-3.5 h-3.5" />
                Diagnosis
              </button>

              <button
                type="button"
                disabled={isLoading}
                onClick={() =>
                  void analyzeSatellite(
                    selectedSatellite
                  )
                }
                className="h-9 inline-flex items-center gap-2 rounded-md border border-[#5C9FD6]/30 bg-[#5C9FD6]/10 px-3 text-xs font-medium text-[#B8D6EA] hover:bg-[#5C9FD6]/15 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
              >
                {isLoading ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Activity className="w-3.5 h-3.5" />
                )}

                {isLoading
                  ? "Analyzing"
                  : `Analyze ${selectedSatellite.id}`}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-6 gap-2">
            <Metric
              label="Battery"
              value={`${selectedSatellite.battery.toFixed(
                1
              )}%`}
            />
            <Metric
              label="Propellant"
              value={`${selectedSatellite.propellant.toFixed(
                1
              )}%`}
            />
            <Metric
              label="Compute"
              value={`${selectedSatellite.compute.toFixed(
                1
              )}%`}
            />
            <Metric
              label="Neighbors"
              value={String(
                selectedSatellite.network
                  .neighbors
              )}
            />
            <Metric
              label="Packet Loss"
              value={`${selectedSatellite.network.packetLoss.toFixed(
                2
              )}%`}
            />
            <Metric
              label="Link Quality"
              value={`${selectedSatellite.network.linkQuality.toFixed(
                1
              )}%`}
            />
          </div>

          {error && (
            <div className="rounded-xl border border-[#F59E0B]/20 bg-[#F59E0B]/[0.05] px-4 py-3">
              <div className="flex gap-3">
                <AlertTriangle className="mt-0.5 w-4 h-4 shrink-0 text-[#F59E0B]" />

                <div>
                  <p className="text-xs font-medium text-[#F3C969]">
                    Intelligence backend unavailable
                  </p>

                  <p className="mt-1 text-xs leading-5 text-[#AAB7C4]">
                    {error}
                  </p>

                  <p className="mt-2 text-[10px] leading-4 text-[#6F7D89]">
                    Current telemetry above is live from ASTRANET.
                    No anomaly score is fabricated while the intelligence
                    endpoint is unavailable.
                  </p>
                </div>
              </div>
            </div>
          )}

          {!analysis &&
            !error &&
            !isLoading && (
              <div className="min-h-[290px] rounded-xl border border-white/[0.07] bg-[#080D15]/60 grid place-items-center">
                <div className="max-w-md px-8 py-12 text-center">
                  <BrainCircuit className="w-7 h-7 mx-auto text-[#5C9FD6]" />

                  <p className="mt-4 text-sm font-medium text-[#E5EDF3]">
                    Intelligence engine ready
                  </p>

                  <p className="mt-2 text-xs leading-5 text-[#7F8C9A]">
                    Select a spacecraft and request analysis. Once the
                    backend intelligence service is connected, this view
                    will display the model result and the actual input
                    signals that contributed to the flag.
                  </p>
                </div>
              </div>
            )}

          {isLoading && (
            <div className="min-h-[290px] rounded-xl border border-white/[0.07] bg-[#080D15]/60 grid place-items-center">
              <div className="text-center">
                <RefreshCw className="w-5 h-5 mx-auto text-[#5C9FD6] animate-spin" />

                <p className="mt-3 text-xs text-[#AAB7C4]">
                  Evaluating telemetry snapshot...
                </p>
              </div>
            </div>
          )}

          {analysis && !isLoading && (
            <>
              <div className="grid md:grid-cols-3 gap-3">
                <div className="rounded-xl border border-white/[0.07] bg-[#080D15]/70 p-4">
                  <p className="text-[10px] uppercase tracking-[0.14em] text-[#6F7D89]">
                    Analysis Status
                  </p>

                  <div
                    className={`mt-3 inline-flex items-center gap-2 rounded-md border px-2.5 py-1.5 text-xs font-medium ${statusClass(
                      analysis.status
                    )}`}
                  >
                    {analysis.status ===
                    "NOMINAL" ? (
                      <CheckCircle2 className="w-3.5 h-3.5" />
                    ) : (
                      <AlertTriangle className="w-3.5 h-3.5" />
                    )}

                    {analysis.status}
                  </div>
                </div>

                <div className="rounded-xl border border-white/[0.07] bg-[#080D15]/70 p-4">
                  <p className="text-[10px] uppercase tracking-[0.14em] text-[#6F7D89]">
                    Anomaly Score
                  </p>

                  <p className="mt-2 text-2xl font-semibold tabular-nums text-white">
                    {score}
                  </p>

                  <p className="mt-1 text-[10px] text-[#6F7D89]">
                    Model score · not failure probability
                  </p>
                </div>

                <div className="rounded-xl border border-white/[0.07] bg-[#080D15]/70 p-4">
                  <p className="text-[10px] uppercase tracking-[0.14em] text-[#6F7D89]">
                    Model
                  </p>

                  <p className="mt-2 text-sm font-medium text-[#D9E4EC]">
                    {analysis.model ??
                      analysis.modelVersion ??
                      "Not reported"}
                  </p>

                  <p className="mt-1 text-[10px] text-[#6F7D89]">
                    {analysis.timestamp ??
                      "Timestamp not reported"}
                  </p>
                </div>
              </div>

              <div className="rounded-xl border border-white/[0.07] bg-[#080D15]/70">
                <div className="flex items-center justify-between border-b border-white/[0.06] px-4 py-3">
                  <div className="flex items-center gap-2">
                    <Radio className="w-3.5 h-3.5 text-[#75AFE0]" />

                    <h2 className="text-xs font-medium text-[#E5EDF3]">
                      Flagged Input Signals
                    </h2>
                  </div>

                  <span className="text-[10px] text-[#6F7D89]">
                    {analysis.signals.length} signal
                    {analysis.signals.length === 1
                      ? ""
                      : "s"}
                  </span>
                </div>

                {analysis.signals.length ===
                0 ? (
                  <div className="px-4 py-8 text-center text-xs text-[#7F8C9A]">
                    The backend did not report any flagged input signals.
                  </div>
                ) : (
                  <div className="divide-y divide-white/[0.05]">
                    {analysis.signals.map(
                      (signal, index) => (
                        <div
                          key={`${signal.feature}-${index}`}
                          className="grid grid-cols-[1.4fr_1fr_0.8fr] gap-4 px-4 py-3"
                        >
                          <div>
                            <p className="text-xs font-medium text-[#D9E4EC]">
                              {signal.label ??
                                signal.feature}
                            </p>

                            {signal.reason && (
                              <p className="mt-1 text-[10px] leading-4 text-[#6F7D89]">
                                {signal.reason}
                              </p>
                            )}
                          </div>

                          <div>
                            <p className="text-[10px] text-[#6F7D89]">
                              Observed
                            </p>

                            <p className="mt-1 text-xs tabular-nums text-[#C8D4DE]">
                              {formatValue(
                                signal.value
                              )}
                            </p>
                          </div>

                          <div>
                            <p className="text-[10px] text-[#6F7D89]">
                              Impact
                            </p>

                            <p className="mt-1 text-xs font-medium text-[#AAB7C4]">
                              {signal.impact ??
                                "Not reported"}
                            </p>
                          </div>
                        </div>
                      )
                    )}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      <DiagnosticDrawer
        isOpen={isDiagnosticOpen}
        onClose={() =>
          setIsDiagnosticOpen(false)
        }
        apiBaseUrl={apiBaseUrl}
        satelliteId={selectedSatellite.id}
      />
    </div>
  );
}

function Metric({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-white/[0.06] bg-[#080D15]/60 px-3 py-3">
      <p className="text-[10px] uppercase tracking-[0.12em] text-[#667583]">
        {label}
      </p>

      <p className="mt-1.5 text-sm font-medium tabular-nums text-[#D9E4EC]">
        {value}
      </p>
    </div>
  );
}
