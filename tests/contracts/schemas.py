from pydantic import BaseModel
from typing import List, Dict, Any


class SatelliteState(BaseModel):
    id: str
    plane: int
    position: List[float]
    velocity: List[float]
    status: str
    subsystemHealth: Dict[str, float]
    battery: float
    propellant: float
    computeLoad: float
    storage: float
    role: str
    capabilities: List[str]
    neighbors: List[str]
    latency: float
    packetLoss: float
    trust: float
    localEpoch: int
    anomalies: List[str]
class FaultEvent(BaseModel):
    target: str
    failureType: str
    severity: float
    startTime: float
    observability: str
    affectedCapabilities: List[str]
    adversarialFlag: bool


class RecoveryCandidate(BaseModel):
    planId: str
    actions: List[Dict[str, Any]]
    expectedMissionUtility: float
    deltaV: float
    energyCost: float
    risk: float
    recoveryConfidence: float
    predictedSecondaryRisk: float
    resilienceDebt: float
    n1Survival: float
    n2Survival: float


class RecoveryDecision(BaseModel):
    selectedPlanId: str
    ranking: List[str]
    evidence: List[Dict[str, Any]]
    rejectedPlansWithReasons: Dict[str, str]
    missionStateBefore: str
    missionStateAfter: str


class ResilienceSnapshot(BaseModel):
    connectivity: float
    coverage: float
    energy: float
    roleRedundancy: float
    navigationConfidence: float
    trustHealth: float
    n1Survival: float
    n2Survival: float
    overallScore: float
    resilienceDebt: float


class EventLog(BaseModel):
    timestamp: float
    source: str
    severity: str
    eventType: str
    message: str
    correlationId: str
    planId: str | None = None
    satelliteId: str | None = None
