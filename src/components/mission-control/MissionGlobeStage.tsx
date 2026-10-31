import { useState, useEffect } from "react";
import type {
  SatelliteTelemetry,
  RecoveryCandidate,
  BlastRadiusResult,
} from "../../data/mockMissionControl";

import CesiumGlobe from "./CesiumGlobe";
import SwarmGlobe from "./SwarmGlobe";

export type GlobeMode = "SWARM" | "ORBITAL";

interface MissionGlobeStageProps {
  satellites: SatelliteTelemetry[];
  selectedSatelliteId: string;
  onSelectSatellite: (id: string) => void;
  missionTime: string;
  coordinatorId: string;
  activeLinks?: Array<[string, string]>;
  apiBaseUrl: string;
  onModeChange?: (mode: GlobeMode) => void;
  ghostCandidate?: RecoveryCandidate | null;
  blastRadiusData?: BlastRadiusResult | null;
}

export default function MissionGlobeStage({
  satellites,
  selectedSatelliteId,
  onSelectSatellite,
  missionTime,
  coordinatorId,
  activeLinks,
  apiBaseUrl,
  onModeChange,
  ghostCandidate,
  blastRadiusData,
}: MissionGlobeStageProps) {
  const [mode, setMode] = useState<GlobeMode>("SWARM");

  useEffect(() => {
    onModeChange?.(mode);
  }, [mode, onModeChange]);

  // Auto-switch to ORBITAL mode when multiverse ghosting or blast radius preview is triggered
  useEffect(() => {
    if (ghostCandidate || blastRadiusData) {
      setMode("ORBITAL");
    }
  }, [ghostCandidate, blastRadiusData]);

  return (
    <div className="relative w-full h-full">
      {mode === "SWARM" ? (
        <SwarmGlobe
          satellites={satellites}
          selectedSatelliteId={selectedSatelliteId}
          onSelectSatellite={onSelectSatellite}
          coordinatorId={coordinatorId}
          activeLinks={activeLinks}
          apiBaseUrl={apiBaseUrl}
        />
      ) : (
        <CesiumGlobe
          satellites={satellites}
          selectedSatelliteId={selectedSatelliteId}
          onSelectSatellite={onSelectSatellite}
          missionTime={missionTime}
          coordinatorId={coordinatorId}
          activeLinks={activeLinks}
          ghostCandidate={ghostCandidate}
          blastRadiusData={blastRadiusData}
        />
      )}

      <div className="absolute z-40 top-5 left-1/2 -translate-x-1/2 flex items-center rounded-lg border border-white/[0.08] bg-[#05080D]/82 backdrop-blur-md p-1 shadow-xl shadow-black/20">
        <button
          type="button"
          onClick={() => setMode("SWARM")}
          className={`px-3 py-1.5 rounded-md text-[10px] font-medium tracking-[0.08em] transition-colors ${
            mode === "SWARM"
              ? "bg-white/[0.10] text-white"
              : "text-[#718391] hover:text-white"
          }`}
        >
          SWARM LIVE
        </button>

        <button
          type="button"
          onClick={() => setMode("ORBITAL")}
          className={`px-3 py-1.5 rounded-md text-[10px] font-medium tracking-[0.08em] transition-colors ${
            mode === "ORBITAL"
              ? "bg-white/[0.10] text-white"
              : "text-[#718391] hover:text-white"
          }`}
        >
          ORBITAL MAP
        </button>
      </div>
    </div>
  );
}
