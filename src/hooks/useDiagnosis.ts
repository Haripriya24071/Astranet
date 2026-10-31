import { useCallback, useState } from "react";
import type {
  DiagnosticEvidence,
  DiagnosticHypothesis,
  DiagnosticReport,
} from "../types/intelligence";

interface UseDiagnosisReturn {
  diagnosis: DiagnosticReport | null;
  isLoading: boolean;
  error: string | null;
  loadDiagnosis: (
    satelliteId: string
  ) => Promise<DiagnosticReport | null>;
  resetDiagnosis: () => void;
}

export function useDiagnosis(
  apiBaseUrl: string
): UseDiagnosisReturn {
  const [diagnosis, setDiagnosis] =
    useState<DiagnosticReport | null>(null);

  const [isLoading, setIsLoading] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);

  const resetDiagnosis = useCallback(() => {
    setDiagnosis(null);
    setError(null);
  }, []);

  const loadDiagnosis = useCallback(
    async (
      satelliteId: string
    ): Promise<DiagnosticReport | null> => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch(
          `${apiBaseUrl}/intelligence/diagnostics/${encodeURIComponent(
            satelliteId
          )}`
        );

        if (!response.ok) {
          let detail = "";

          try {
            const body = await response.json();
            detail =
              typeof body?.detail === "string"
                ? body.detail
                : "";
          } catch {
            // Ignore non-JSON response.
          }

          if (response.status === 404) {
            throw new Error(
              "Diagnostic endpoint is not available yet. Waiting for GET /intelligence/diagnostics/{id}."
            );
          }

          throw new Error(
            detail ||
              `Diagnostic request failed with HTTP ${response.status}.`
          );
        }

        const raw = await response.json();

        const rawHypotheses =
          Array.isArray(raw?.hypotheses)
            ? raw.hypotheses
            : Array.isArray(raw?.diagnosis)
            ? raw.diagnosis
            : [];

        const hypotheses: DiagnosticHypothesis[] =
          rawHypotheses.map(
            (item: any, index: number) => {
              const rawEvidence =
                Array.isArray(item?.evidence)
                  ? item.evidence
                  : [];

              const evidence: DiagnosticEvidence[] =
                rawEvidence.map(
                  (entry: any) => {
                    if (
                      typeof entry === "string"
                    ) {
                      return {
                        signal: "evidence",
                        explanation: entry,
                      };
                    }

                    return {
                      signal:
                        typeof entry?.signal ===
                        "string"
                          ? entry.signal
                          : typeof entry?.feature ===
                            "string"
                          ? entry.feature
                          : "evidence",

                      value:
                        entry?.value ?? null,

                      explanation:
                        typeof entry?.explanation ===
                        "string"
                          ? entry.explanation
                          : typeof entry?.reason ===
                            "string"
                          ? entry.reason
                          : "Supporting evidence reported by backend.",

                      strength:
                        typeof entry?.strength ===
                        "string"
                          ? entry.strength
                          : undefined,
                    };
                  }
                );

              return {
                cause:
                  typeof item?.cause === "string"
                    ? item.cause
                    : "UNKNOWN_CAUSE",

                confidence:
                  typeof item?.confidence ===
                  "number"
                    ? item.confidence
                    : null,

                rank:
                  typeof item?.rank === "number"
                    ? item.rank
                    : index + 1,

                affectedCapabilities:
                  Array.isArray(
                    item?.affectedCapabilities
                  )
                    ? item.affectedCapabilities
                    : [],

                evidence,
              };
            }
          );

        const normalized: DiagnosticReport = {
          satelliteId:
            typeof raw?.satelliteId === "string"
              ? raw.satelliteId
              : satelliteId,

          timestamp:
            typeof raw?.timestamp === "string"
              ? raw.timestamp
              : undefined,

          uncertainty:
            typeof raw?.uncertainty === "string"
              ? raw.uncertainty
              : undefined,

          hypotheses,

          recommendedInvestigation:
            Array.isArray(
              raw?.recommendedInvestigation
            )
              ? raw.recommendedInvestigation
              : [],

          message:
            typeof raw?.message === "string"
              ? raw.message
              : undefined,
        };

        setDiagnosis(normalized);
        return normalized;
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : "Diagnostic request failed.";

        setDiagnosis(null);
        setError(message);

        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [apiBaseUrl]
  );

  return {
    diagnosis,
    isLoading,
    error,
    loadDiagnosis,
    resetDiagnosis,
  };
}
