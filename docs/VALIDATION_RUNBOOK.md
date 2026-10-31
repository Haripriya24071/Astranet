# ASTRANET — Scenario Integration, Validation & QA Runbook

**Owner**: Rits (`mer-ritz`) — Scenario Integration, Validation & QA  
**Reference**: *ASTRANET Research, Novelty & Implementation Master Blueprint v2.0* (Sections 18, 21 & 22)

---

## 1. Environment & Setup

Ensure Python 3.11+ (or 3.14) is available. Install the required test dependencies:

```bash
pip install -r astranet/requirements-test.txt
pip install fastapi httpx networkx numpy uvicorn websockets
```

---

## 2. Test Execution

### 2.1 Run All Tests Across the Repository
Executes both contract schema verification tests (20 tests) and backend/autonomy/simulation tests (105 tests), for a total of **125 tests**:

```powershell
$env:PYTHONPATH="."
pytest tests backend/tests
```

### 2.2 Run Only Shared Contract Validation Tests
Validates the Blueprint Section 20 minimum shared data objects (`SatelliteState`, `FaultEvent`, `RecoveryCandidate`, `RecoveryDecision`, `ResilienceSnapshot`, `EventLog`):

```powershell
pytest tests/contracts
```

### 2.3 Run Scenario Benchmark Acceptance Tests
Validates the 10 benchmark scenarios, timing bounds, detection delay thresholds, and zero manual intervention requirements:

```powershell
pytest backend/tests/test_phase6_scenarios.py
```

---

## 3. Scenario Runner CLI

ASTRANET provides a CLI tool in [`backend/app/run_scenario.py`](file:///C:/Users/rithi/.gemini/antigravity/scratch/Astranet/backend/app/run_scenario.py) to inspect, execute, and export scenario benchmark results.

### 3.1 List All Available Benchmark Scenarios
```powershell
python -m backend.app.run_scenario --list
```

### 3.2 Execute a Single Scenario
```powershell
# Run the core capability-loss scenario
python -m backend.app.run_scenario --scenario propulsion_failure

# Run the relay handover scenario
python -m backend.app.run_scenario --scenario comms_failure

# Run the Byzantine isolation scenario
python -m backend.app.run_scenario --scenario byzantine_node
```

### 3.3 Verify Execution Determinism (Repeatability Test)
Test deterministic repeatability across $N$ consecutive runs:

```powershell
python -m backend.app.run_scenario --scenario seeded_random_faults --repeat 3
```

### 3.4 Run Full Benchmark Suite & Export Report
```powershell
python -m backend.app.run_scenario --all --export backend/scenarios/reports/benchmark_report.json
```

---

## 4. Current Quality Status

* **Total Scenarios**: 10
* **Scenario Status**: 10 / 10 Passing ($100\%$)
* **Total Automated Tests**: 125
* **Automated Test Status**: 125 / 125 Passing ($100\%$)
* **Manual Intervention Required**: 0 (Fully autonomous self-healing verified across all profiles)
