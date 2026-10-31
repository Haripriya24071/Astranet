import { useEffect } from "react";
import {
  AlertTriangle,
  BrainCircuit,
  ChevronRight,
  RefreshCw,
  ShieldCheck,
  X,
} from "lucide-react";

import { useDiagnosis } from "../../hooks/useDiagnosis";

interface DiagnosticDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  apiBaseUrl: string;
  satelliteId: string;
}

function confidenceLabel(
  confidence: number | null
): string {
  if (confidence === null) {
    return "Not reported";
  }

  return `${Math.round(
    confidence * 100
  )}%`;
}

export default function DiagnosticDrawer({
  isOpen,
  onClose,
  apiBaseUrl,
  satelliteId,
}: DiagnosticDrawerProps) {
  const {
    diagnosis,
    isLoading,
    error,
    loadDiagnosis,
    resetDiagnosis,
  } = useDiagnosis(apiBaseUrl);

  useEffect(() => {
    if (!isOpen) {
      resetDiagnosis();
      return;
    }

    void loadDiagnosis(
      satelliteId
    );
  }, [
    isOpen,
    satelliteId,
    loadDiagnosis,
    resetDiagnosis,
  ]);

  if (!isOpen) {
    return null;
  }

  const primary =
    diagnosis?.hypotheses?.[0] ??
    null;

  return (
    <div className="absolute inset-0 z-50 flex justify-end">
      <button
        type="button"
        aria-label="Close diagnostic drawer"
        onClick={onClose}
        className="absolute inset-0 bg-black/45 backdrop-blur-[1px]"
      />

      <aside className="relative z-10 h-full w-full max-w-[460px] border-l border-white/[0.08] bg-[#080D15] shadow-2xl shadow-black/50 overflow-y-auto">
        <div className="sticky top-0 z-20 flex items-center justify-between border-b border-white/[0.07] bg-[#080D15]/95 backdrop-blur-md px-5 py-4">
          <div>
            <div className="flex items-center gap-2 text-[#75AFE0]">
              <BrainCircuit className="w-4 h-4" />

              <span className="text-[10px] uppercase tracking-[0.18em] font-medium">
                Diagnostic Evidence
              </span>
            </div>

            <h2 className="mt-1 text-base font-semibold text-white">
              {satelliteId}
            </h2>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-2 text-[#7F8C9A] hover:bg-white/[0.05] hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-4 p-5">
          {isLoading && (
            <div className="min-h-[240px] grid place-items-center rounded-xl border border-white/[0.07] bg-[#05080D]/60">
              <div className="text-center">
                <RefreshCw className="w-5 h-5 mx-auto text-[#5C9FD6] animate-spin" />

                <p className="mt-3 text-xs text-[#AAB7C4]">
                  Building diagnostic evidence...
                </p>
              </div>
            </div>
          )}

          {error && !isLoading && (
            <div className="rounded-xl border border-[#F59E0B]/20 bg-[#F59E0B]/[0.05] p-4">
              <div className="flex gap-3">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-[#F59E0B]" />

                <div>
                  <p className="text-xs font-medium text-[#F3C969]">
                    Diagnostic backend unavailable
                  </p>

                  <p className="mt-1 text-xs leading-5 text-[#AAB7C4]">
                    {error}
                  </p>

                  <p className="mt-3 text-[10px] leading-4 text-[#6F7D89]">
                    ASTRANET will not fabricate likely causes,
                    confidence values or evidence while the backend
                    diagnostic service is unavailable.
                  </p>
                </div>
              </div>
            </div>
          )}

          {diagnosis && !isLoading && (
            <>
              <div className="rounded-xl border border-white/[0.07] bg-[#05080D]/60 p-4">
                <p className="text-[10px] uppercase tracking-[0.14em] text-[#6F7D89]">
                  Primary Hypothesis
                </p>

                {primary ? (
                  <>
                    <p className="mt-2 text-sm font-semibold text-[#E5EDF3]">
                      {primary.cause}
                    </p>

                    <div className="mt-3 grid grid-cols-2 gap-3">
                      <div>
                        <p className="text-[10px] text-[#6F7D89]">
                          Confidence
                        </p>

                        <p className="mt-1 text-sm font-medium tabular-nums text-white">
                          {confidenceLabel(
                            primary.confidence
                          )}
                        </p>
                      </div>

                      <div>
                        <p className="text-[10px] text-[#6F7D89]">
                          Uncertainty
                        </p>

                        <p className="mt-1 text-sm font-medium text-[#D9E4EC]">
                          {diagnosis.uncertainty ??
                            "Not reported"}
                        </p>
                      </div>
                    </div>

                    <p className="mt-3 text-[10px] leading-4 text-[#6F7D89]">
                      Confidence is backend diagnostic confidence,
                      not a validated probability of spacecraft failure.
                    </p>
                  </>
                ) : (
                  <p className="mt-2 text-xs text-[#7F8C9A]">
                    No diagnostic hypothesis was returned.
                  </p>
                )}
              </div>

              <div className="rounded-xl border border-white/[0.07] bg-[#05080D]/60">
                <div className="border-b border-white/[0.06] px-4 py-3">
                  <p className="text-xs font-medium text-[#E5EDF3]">
                    Ranked Hypotheses
                  </p>
                </div>

                {diagnosis.hypotheses.length ===
                0 ? (
                  <div className="px-4 py-7 text-center text-xs text-[#7F8C9A]">
                    No ranked hypotheses reported.
                  </div>
                ) : (
                  <div className="divide-y divide-white/[0.05]">
                    {diagnosis.hypotheses.map(
                      (hypothesis, index) => (
                        <div
                          key={`${hypothesis.cause}-${index}`}
                          className="px-4 py-4"
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex gap-3">
                              <div className="mt-0.5 w-6 h-6 rounded-full border border-white/10 bg-white/[0.03] flex items-center justify-center text-[10px] text-[#AAB7C4]">
                                {hypothesis.rank ??
                                  index + 1}
                              </div>

                              <div>
                                <p className="text-xs font-medium text-[#D9E4EC]">
                                  {hypothesis.cause}
                                </p>

                                {hypothesis.affectedCapabilities &&
                                  hypothesis
                                    .affectedCapabilities
                                    .length > 0 && (
                                    <p className="mt-1 text-[10px] text-[#6F7D89]">
                                      Affects:{" "}
                                      {hypothesis.affectedCapabilities.join(
                                        ", "
                                      )}
                                    </p>
                                  )}
                              </div>
                            </div>

                            <span className="text-xs font-medium tabular-nums text-[#AAB7C4]">
                              {confidenceLabel(
                                hypothesis.confidence
                              )}
                            </span>
                          </div>

                          {hypothesis.evidence.length >
                            0 && (
                            <div className="mt-3 ml-9 space-y-2">
                              {hypothesis.evidence.map(
                                (
                                  evidence,
                                  evidenceIndex
                                ) => (
                                  <div
                                    key={`${evidence.signal}-${evidenceIndex}`}
                                    className="flex gap-2"
                                  >
                                    <ChevronRight className="w-3 h-3 shrink-0 mt-0.5 text-[#5C9FD6]" />

                                    <div>
                                      <p className="text-[10px] leading-4 text-[#AAB7C4]">
                                        {
                                          evidence.explanation
                                        }
                                      </p>

                                      {evidence.value !==
                                        undefined &&
                                        evidence.value !==
                                          null && (
                                          <p className="mt-0.5 text-[9px] text-[#5F6C77]">
                                            {
                                              evidence.signal
                                            }
                                            :{" "}
                                            {String(
                                              evidence.value
                                            )}
                                          </p>
                                        )}
                                    </div>
                                  </div>
                                )
                              )}
                            </div>
                          )}
                        </div>
                      )
                    )}
                  </div>
                )}
              </div>

              <div className="rounded-xl border border-white/[0.07] bg-[#05080D]/60 p-4">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-3.5 h-3.5 text-[#75AFE0]" />

                  <p className="text-xs font-medium text-[#E5EDF3]">
                    Recommended Investigation
                  </p>
                </div>

                {diagnosis
                  .recommendedInvestigation &&
                diagnosis
                  .recommendedInvestigation
                  .length > 0 ? (
                  <div className="mt-3 space-y-2">
                    {diagnosis.recommendedInvestigation.map(
                      (item, index) => (
                        <div
                          key={index}
                          className="flex gap-2 text-[10px] leading-4 text-[#AAB7C4]"
                        >
                          <span className="text-[#5C9FD6]">
                            {String(
                              index + 1
                            ).padStart(2, "0")}
                          </span>

                          <span>{item}</span>
                        </div>
                      )
                    )}
                  </div>
                ) : (
                  <p className="mt-3 text-[10px] leading-4 text-[#6F7D89]">
                    No investigation steps were reported.
                  </p>
                )}
              </div>

              <div className="text-[9px] leading-4 text-[#56636E]">
                Diagnostic output is decision support for the
                ASTRANET simulation. It does not represent
                flight-certified fault isolation.
              </div>
            </>
          )}
        </div>
      </aside>
    </div>
  );
}
