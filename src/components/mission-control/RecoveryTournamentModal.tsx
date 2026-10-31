import { useState } from "react";
import {
  X,
  Trophy,
  ShieldCheck,
  AlertTriangle,
  Zap,
  Activity,
  Flame,
  ArrowRight,
  Loader2,
  CheckCircle2,
} from "lucide-react";
import { RecoveryDecision } from "../../data/mockMissionControl";

interface RecoveryTournamentModalProps {
  isOpen: boolean;
  onClose: () => void;
  decision: RecoveryDecision | null;
  onExecuteRecovery: () => Promise<boolean>;
  onHoverCandidate?: (candidate: any) => void;
}

export default function RecoveryTournamentModal({
  isOpen,
  onClose,
  decision,
  onExecuteRecovery,
  onHoverCandidate,
}: RecoveryTournamentModalProps) {
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionStatus, setExecutionStatus] = useState<string | null>(null);

  if (!isOpen || !decision) return null;

  const handleExecute = async () => {
    setIsExecuting(true);
    setExecutionStatus(null);
    try {
      const ok = await onExecuteRecovery();
      if (ok) {
        setExecutionStatus("Plan executed successfully! Swarm reconfigured.");
        setTimeout(() => {
          onClose();
        }, 1800);
      } else {
        setExecutionStatus("Execution failed or simulation rejected plan.");
      }
    } catch {
      setExecutionStatus("Network error during recovery dispatch.");
    } finally {
      setIsExecuting(false);
    }
  };

  const winner = decision.candidates.find((c) => c.planId === decision.selectedPlanId);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md select-none font-sans text-xs">
      <div className="w-full max-w-5xl bg-[#070D16] border border-cyan-500/30 rounded-xl shadow-2xl shadow-cyan-950/40 overflow-hidden flex flex-col max-h-[92vh]">
        {/* Header */}
        <div className="px-5 py-3.5 border-b border-white/10 bg-gradient-to-r from-cyan-950/40 via-transparent to-transparent flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-cyan-500/15 border border-cyan-500/30 text-cyan-400">
              <Trophy className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-medium text-sm text-white">
                  Counterfactual Recovery Tournament
                </h3>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                  Target: {decision.targetSatelliteId}
                </span>
              </div>
              <p className="text-[11px] text-[#7F8C9A] mt-0.5">
                Evaluated parallel digital-twin futures for: <span className="text-[#E2E8F0] font-mono">{decision.triggeringAnomaly}</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-[#7F8C9A] hover:text-white transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="p-4 space-y-4 overflow-y-auto">
          {/* Winner Showcase Banner */}
          {winner && (
            <div className="p-3.5 rounded-xl border border-emerald-500/40 bg-emerald-950/20">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                      ★ Winning Strategy
                    </span>
                    <h4 className="font-semibold text-white text-sm">
                      {winner.name}
                    </h4>
                  </div>
                  <p className="text-[11px] text-[#A0AEC0] mt-1.5 leading-relaxed">
                    {decision.rationale}
                  </p>
                </div>
                <div className="text-right shrink-0 ml-4">
                  <div className="text-[10px] text-[#718096] uppercase tracking-wider">Composite Score</div>
                  <div className="text-2xl font-bold text-emerald-400 font-mono">
                    {winner.compositeScore.toFixed(1)}
                    <span className="text-xs text-[#718096] font-normal"> / 100</span>
                  </div>
                </div>
              </div>

              {/* Action list */}
              <div className="mt-2.5 pt-2.5 border-t border-emerald-500/20 flex flex-wrap gap-2">
                {winner.actions.map((act, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-1 rounded bg-black/40 border border-emerald-500/20 text-[10px] text-emerald-200"
                  >
                    {act.description}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Candidate Comparison Grid */}
          <div>
            <div className="text-[11px] text-[#7F8C9A] uppercase tracking-wider font-medium mb-2">
              Candidate Futures Evaluated ({decision.candidates.length})
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
              {decision.candidates.map((cand) => {
                const isSelected = cand.planId === decision.selectedPlanId;
                return (
                  <div
                    key={cand.planId}
                    onMouseEnter={() => onHoverCandidate?.(cand)}
                    onMouseLeave={() => onHoverCandidate?.(null)}
                    className={`p-3.5 rounded-lg border flex flex-col justify-between transition-all cursor-pointer ${
                      isSelected
                        ? "bg-cyan-950/20 border-cyan-400/50 shadow-lg shadow-cyan-950/20"
                        : "bg-white/[0.02] border-white/8 hover:border-cyan-500/40 hover:bg-cyan-950/10"
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[10px] font-mono text-[#718096]">
                          {cand.planId.split("-")[1] || cand.planId}
                        </span>
                        <span
                          className={`text-xs font-bold font-mono ${
                            isSelected ? "text-cyan-300" : "text-white"
                          }`}
                        >
                          {cand.compositeScore.toFixed(1)}
                        </span>
                      </div>
                      <div className="font-medium text-white text-xs mb-1">
                        {cand.name}
                      </div>
                      <div className="text-[9px] text-cyan-400/80 font-mono mb-2.5 flex items-center gap-1">
                        <span>👻</span> 3D Multiverse Ghost
                      </div>

                      {/* Key scorecard metrics */}
                      <div className="space-y-1.5 text-[10px]">
                        <div className="flex justify-between">
                          <span className="text-[#7F8C9A]">Mission Yield:</span>
                          <span className="text-white font-mono">{cand.expectedMissionUtility}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-[#7F8C9A]">Delta-V Burn:</span>
                          <span className={cand.deltaVCostMs > 0 ? "text-amber-400 font-mono" : "text-emerald-400 font-mono"}>
                            {cand.deltaVCostMs > 0 ? `+${cand.deltaVCostMs.toFixed(2)} m/s` : "0.0 m/s"}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-[#7F8C9A]">Resilience Debt:</span>
                          <span className={cand.resilienceDebt > 25 ? "text-red-400 font-mono" : "text-[#E2E8F0] font-mono"}>
                            {cand.resilienceDebt.toFixed(1)}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-[#7F8C9A]">N-1 Survival:</span>
                          <span className="text-cyan-400 font-mono">{(cand.n1Survival * 100).toFixed(0)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-[#7F8C9A]">N-2 Survival:</span>
                          <span className="text-cyan-400 font-mono">{(cand.n2Survival * 100).toFixed(0)}%</span>
                        </div>
                      </div>
                    </div>

                    {/* Footer badge */}
                    <div className="mt-3 pt-2 border-t border-white/6 text-center">
                      {isSelected ? (
                        <span className="text-[10px] font-bold text-cyan-300 flex items-center justify-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Selected Winner
                        </span>
                      ) : (
                        <span className="text-[9px] text-[#718096]">
                          Rejected alternative
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Machine-Readable Rejections Breakdown */}
          {Object.keys(decision.rejectedPlansWithReasons).length > 0 && (
            <div className="p-3 rounded-lg bg-black/40 border border-white/6 space-y-2">
              <div className="text-[10px] uppercase tracking-wider text-[#7F8C9A] font-medium flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                <span>Counterfactual Rejection Provenance</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[10.5px]">
                {Object.entries(decision.rejectedPlansWithReasons).map(([id, reason]) => (
                  <div key={id} className="p-2 rounded bg-white/[0.02] border border-white/5">
                    <span className="text-amber-300 font-mono font-medium block mb-0.5">{id}</span>
                    <span className="text-[#A0AEC0] leading-relaxed">{reason}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Execution feedback */}
          {executionStatus && (
            <div className="p-3 rounded-lg bg-cyan-950/40 border border-cyan-500/40 text-cyan-200 text-xs text-center font-medium">
              {executionStatus}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-white/10 bg-[#060B12] flex items-center justify-between">
          <div className="text-[11px] text-[#7F8C9A]">
            Predicted Post-Recovery Mode:{" "}
            <span className="text-emerald-400 font-mono font-medium">
              {decision.missionStateAfter}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              disabled={isExecuting}
              className="px-3.5 py-1.5 rounded-lg border border-white/10 text-[#7F8C9A] hover:text-white transition-colors cursor-pointer disabled:opacity-50"
            >
              Close
            </button>
            <button
              onClick={handleExecute}
              disabled={isExecuting}
              className="px-4 py-1.5 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-400/50 text-cyan-300 font-medium transition-colors cursor-pointer flex items-center gap-2 disabled:opacity-50"
            >
              {isExecuting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Executing Recovery…
                </>
              ) : (
                <>
                  <ShieldCheck className="w-3.5 h-3.5" />
                  Execute Autonomous Recovery
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
