import { useCallback, useState } from "react";
import type { SatelliteTelemetry } from "../data/mockMissionControl";
import type {
  IntelligenceAnalysis,
  IntelligenceAnalyzeRequest,
  IntelligenceSignal,
} from "../types/intelligence";

interface UseIntelligenceReturn {
  analysis: IntelligenceAnalysis | null;
  isLoading: boolean;
  error: string | null;
  analyzeSatellite: (
    satellite: SatelliteTelemetry
  ) => Promise<IntelligenceAnalysis | null>;
  resetAnalysis: () => void;
}

export function useIntelligence(
  apiBaseUrl: string
): UseIntelligenceReturn {
  const [analysis, setAnalysis] =
    useState<IntelligenceAnalysis | null>(null);

  const [isLoading, setIsLoading] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);

  const resetAnalysis = useCallback(() => {
    setAnalysis(null);
    setError(null);
  }, []);

  const analyzeSatellite = useCallback(
    async (
      satellite: SatelliteTelemetry
    ): Promise<IntelligenceAnalysis | null> => {
      setIsLoading(true);
      setError(null);

      const payload: IntelligenceAnalyzeRequest = {
        satelliteId: satellite.id,
        telemetry: satellite,
      };

      try {
        const response = await fetch(
          `${apiBaseUrl}/intelligence/analyze`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
          }
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
            // Ignore non-JSON error responses.
          }

          if (response.status === 404) {
            throw new Error(
              "Intelligence endpoint is not available yet. Waiting for POST /intelligence/analyze from the backend."
            );
          }

          throw new Error(
            detail ||
              `Intelligence request failed with HTTP ${response.status}.`
          );
        }

        const raw = await response.json();

        const rawSignals =
          Array.isArray(raw?.signals)
            ? raw.signals
            : Array.isArray(raw?.flaggedFeatures)
            ? raw.flaggedFeatures
            : [];

        const signals: IntelligenceSignal[] =
          rawSignals.map(
            (
              item: IntelligenceSignal
            ) => ({
              feature:
                item.feature ??
                "unknown_feature",
              label: item.label,
              value: item.value ?? null,
              baseline: item.baseline,
              impact: item.impact,
              direction: item.direction,
              reason: item.reason,
            })
          );

        const normalized: IntelligenceAnalysis = {
          satelliteId:
            typeof raw?.satelliteId === "string"
              ? raw.satelliteId
              : satellite.id,

          status:
            typeof raw?.status === "string"
              ? raw.status
              : "UNAVAILABLE",

          anomalyScore:
            typeof raw?.anomalyScore === "number"
              ? raw.anomalyScore
              : null,

          model:
            typeof raw?.model === "string"
              ? raw.model
              : undefined,

          modelVersion:
            typeof raw?.modelVersion === "string"
              ? raw.modelVersion
              : undefined,

          timestamp:
            typeof raw?.timestamp === "string"
              ? raw.timestamp
              : undefined,

          signals,

          message:
            typeof raw?.message === "string"
              ? raw.message
              : undefined,
        };

        setAnalysis(normalized);
        return normalized;
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : "Intelligence analysis failed.";

        setAnalysis(null);
        setError(message);

        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [apiBaseUrl]
  );

  return {
    analysis,
    isLoading,
    error,
    analyzeSatellite,
    resetAnalysis,
  };
}
