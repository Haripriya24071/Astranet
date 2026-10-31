# ASTRANET — Minimum Shared Data Contracts & Schemas

**Owner**: Rits (`mer-ritz`) — Scenario Integration, Validation & QA  
**Reference**: *ASTRANET Research, Novelty & Implementation Master Blueprint v2.0* (Sections 19, 20 & 21)

---

## 1. Architectural Role & Ownership Boundary

Per Blueprint Section 20 and 21, the shared data contracts represent the strict interface across all team layers:

* **Hari -> Zahid**: Normalized `SwarmState` (orbit kinematics, subsystem health, resources, network links).
* **Zahid -> Hari**: `RecoveryPlan` (role reallocations, maneuvers, isolation/quarantine).
* **Hari + Zahid -> Vaibhavi**: Real-time `SatelliteState`, `EventLog`, `RecoveryCandidate[]`, `SelectedPlan`, `ResilienceSnapshot`.
* **Rits -> Everyone**: Contract validation schemas, fixtures, and reproducible verification tests.

All shared contracts are defined using Pydantic in [`tests/contracts/schemas.py`](file:///C:/Users/rithi/.gemini/antigravity/scratch/Astranet/tests/contracts/schemas.py) and validated against canonical test fixtures in [`tests/fixtures/`](file:///C:/Users/rithi/.gemini/antigravity/scratch/Astranet/tests/fixtures).

---

## 2. Minimum Shared Data Objects (Section 20)

### 2.1 `SatelliteState`
Represents an individual spacecraft's real-time physical, subsystem, and autonomy state.

```python
class SatelliteState(BaseModel):
    id: str                             # Spacecraft identifier (e.g. "SAT-01")
    plane: int                          # Orbital plane index (1, 2, 3)
    position: List[float]               # ECI Cartesian coordinates [x, y, z] in km
    velocity: List[float]               # Velocity vectors [vx, vy, vz] in km/s
    status: str                         # Constellation status ("nominal", "degraded", "failed", "isolated")
    subsystemHealth: Dict[str, float]   # Subsystem health metrics (comms, power, propulsion, navigation, attitude)
    battery: float                      # State of charge (0.0 to 1.0)
    propellant: float                   # Propellant reserve (0.0 to 1.0)
    computeLoad: float                  # CPU utilization (0.0 to 1.0)
    storage: float                      # Solid-state storage utilization (0.0 to 1.0)
    role: str                           # Mission role ("sensing_node", "relay", "coordinator", "isolated")
    capabilities: List[str]             # Operational capability tags ("sensing", "relay", "navigation", "compute")
    neighbors: List[str]                # Directly connected ISL peer IDs
    latency: float                      # Average ISL latency in ms
    packetLoss: float                   # Packet loss ratio (0.0 to 1.0)
    trust: float                        # Byzantine consensus trust rating (0.0 to 1.0)
    localEpoch: int                     # Clock tick / local epoch counter
    anomalies: List[str]                # Active anomaly descriptors
```

### 2.2 `FaultEvent`
Defines an anomaly injected into the constellation.

```python
class FaultEvent(BaseModel):
    target: str                         # Target satellite ID (e.g. "SAT-04")
    failureType: str                    # Standardized failure mode (e.g. "comms_failure")
    severity: float                     # Normalized severity (0.0 to 1.0)
    startTime: float                    # Simulation epoch in seconds
    observability: str                  # Observability category ("direct", "peer_inferred", "delayed")
    affectedCapabilities: List[str]     # Capabilities impacted by fault
    adversarialFlag: bool               # True if Byzantine / cyber-physical anomaly
```

### 2.3 `RecoveryCandidate`
A candidate recovery plan evaluated in parallel digital-twin futures during the recovery tournament.

```python
class RecoveryCandidate(BaseModel):
    planId: str                         # Unique plan slug (e.g. "PLAN-A", "PLAN-B")
    actions: List[Dict[str, Any]]       # Sequence of operational actions (reassignment, burn, reset)
    expectedMissionUtility: float       # Preserved Earth-observation / ISL science value
    deltaV: float                       # Fuel expenditure in m/s
    energyCost: float                   # Battery expenditure percentage
    risk: float                         # Operational execution risk
    recoveryConfidence: float           # Confidence estimate for plan success
    predictedSecondaryRisk: float       # Probability of inducing secondary satellite overload
    resilienceDebt: float               # Residual fragility and redundancy reduction
    n1Survival: float                   # Swarm survivability probability under N-1 failure
    n2Survival: float                   # Swarm survivability probability under N-2 failure
```

### 2.4 `RecoveryDecision`
The final explainable decision output of the recovery tournament.

```python
class RecoveryDecision(BaseModel):
    selectedPlanId: str                 # ID of tournament-winning plan
    ranking: List[str]                  # Sorted plan ranking (best to worst)
    evidence: List[Dict[str, Any]]      # Telemetry evidence driving the selection
    rejectedPlansWithReasons: Dict[str, str] # Counterfactual audit: why each alternative lost
    missionStateBefore: str             # Mission mode before execution ("NOMINAL", "DEGRADED-A", etc.)
    missionStateAfter: str              # Projected mission mode post-recovery
```

### 2.5 `ResilienceSnapshot`
Constellation-wide resilience fingerprint across key operational dimensions.

```python
class ResilienceSnapshot(BaseModel):
    connectivity: float                 # ISL network graph connectivity ratio
    coverage: float                     # Ground Earth observation target coverage
    energy: float                       # Swarm-wide power reserve health
    roleRedundancy: float               # Availability of backup nodes for critical roles
    navigationConfidence: float         # Constellation relative positioning certainty
    trustHealth: float                  # Swarm Byzantine trust integrity
    n1Survival: float                   # Swarm survivability under 1 additional failure
    n2Survival: float                   # Swarm survivability under 2 additional failures
    overallScore: float                 # Composite resilience score (0.0 to 100.0)
    resilienceDebt: float               # Cumulative resilience debt incurred
```

### 2.6 `EventLog`
Structured, auditable event log for mission-control telemetry and explainability replay.

```python
class EventLog(BaseModel):
    timestamp: float                    # Simulation epoch timestamp
    source: str                         # Emitting subsystem or satellite ID
    severity: str                       # "info", "warning", "critical"
    eventType: str                      # "FAULT", "OBSERVATION", "RECOVERY", "DECISION"
    message: str                        # Human-readable operator message
    correlationId: str                  # Correlation ID linking fault to decision
    planId: str | None = None           # Associated recovery plan (if applicable)
    satelliteId: str | None = None      # Target satellite ID (if applicable)
```

---

## 3. Fixture Validation

Sample payloads matching each contract are maintained in [`tests/fixtures/`](file:///C:/Users/rithi/.gemini/antigravity/scratch/Astranet/tests/fixtures):
* `sample_satellite.json`
* `sample_fault_event.json`
* `sample_recovery_candidate.json`
* `sample_recovery_decision.json`
* `sample_resilience_snapshot.json`
* `sample_event_log.json`

Validation test suite: [`tests/contracts/test_other_contracts.py`](file:///C:/Users/rithi/.gemini/antigravity/scratch/Astranet/tests/contracts/test_other_contracts.py) and [`tests/contracts/test_satellite_state.py`](file:///C:/Users/rithi/.gemini/antigravity/scratch/Astranet/tests/contracts/test_satellite_state.py) automatically verify valid payloads, required field enforcement, type constraints, and valid enum values.
