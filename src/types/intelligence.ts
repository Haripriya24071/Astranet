import type { SatelliteTelemetry } from "../data/mockMissionControl";

export type IntelligenceStatus =
  | "NOMINAL"
  | "ANOMALOUS"
  | "UNAVAILABLE"
  | string;

export interface IntelligenceSignal {
  feature: string;
  label?: string;
  value: string | number | boolean | null;
  baseline?: string | number | null;
  impact?: "LOW" | "MODERATE" | "HIGH" | string;
  direction?: string;
  reason?: string;
}

export interface IntelligenceAnalysis {
  satelliteId: string;
  status: IntelligenceStatus;
  anomalyScore: number | null;
  model?: string;
  modelVersion?: string;
  timestamp?: string;
  signals: IntelligenceSignal[];
  message?: string;
}

export interface IntelligenceAnalyzeRequest {
  satelliteId: string;
  telemetry: SatelliteTelemetry;
}


export interface DiagnosticEvidence {
  signal: string;
  value?: string | number | boolean | null;
  explanation: string;
  strength?: "LOW" | "MODERATE" | "HIGH" | string;
}

export interface DiagnosticHypothesis {
  cause: string;
  confidence: number | null;
  rank?: number;
  affectedCapabilities?: string[];
  evidence: DiagnosticEvidence[];
}

export interface DiagnosticReport {
  satelliteId: string;
  timestamp?: string;
  uncertainty?: string;
  hypotheses: DiagnosticHypothesis[];
  recommendedInvestigation?: string[];
  message?: string;
}
