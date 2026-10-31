# ASTRANET — Benchmark Scenarios Catalog

**Owner**: Rits (`mer-ritz`) — Scenario Integration, Validation & QA  
**Reference**: *ASTRANET Research, Novelty & Implementation Master Blueprint v2.0* (Sections 15, 16, 18 & 22)

---

## Overview

ASTRANET tests swarm mission resilience through deterministic, reproducible scenario definitions located in [`backend/scenarios/`](file:///C:/Users/rithi/.gemini/antigravity/scratch/Astranet/backend/scenarios).

Each scenario models a discrete mission profile, establishing baseline constellation invariants at $t=0$, injecting timed anomalies into specific spacecraft subsystems, evaluating autonomous recovery reactions, and assessing quantitative acceptance criteria.

---

## Canonical Scenarios (10 Scenarios)

| Scenario ID | Name | Duration | Injected Anomaly / Failure Type | Target | Key Autonomy Mechanism Tested |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `nominal_flight` | Nominal Swarm Flight (Baseline) | 10.0s | None ($0$ faults) | Swarm | Invariant stability, bootstrap coordinator SAT-07, Keplerian orbit propagation |
| `propulsion_failure` | Propulsion-Only Partial Failure | 10.0s | `Propulsion Failure` (Moderate) | SAT-03 (Plane A) | **Capability-Loss Reasoning**: Loss of maneuvering while preserving sensing, relay, compute, and storage; zero node ejection |
| `comms_failure` | ISL Relay Failure & Dynamic Handover | 12.0s | `Communication Failure` (Critical) | SAT-08 (Plane B) | **Peer Observation & Relay Promotion**: Bounded heartbeat loss detection, intra-plane failover, observer SAT-06 promoted to relay |
| `network_partition` | Network Partition & Quorum Safety | 10.0s | `Node Loss` (Critical) | SAT-07 (Coord) | **Quorum-Constrained Leadership**: Prevents split-brain election when connected component lacks $\ge 7$ nodes; yields safe `UNRESOLVED` |
| `low_energy` | Power Degradation & Load Shedding | 10.0s | `Power Degradation` (Critical) | SAT-05 (Plane B) | **Resource-Aware Survival**: Solar bus collapse triggers load shedding to preserve core bus telemetry and ISL mesh links |
| `dual_node_failure` | Dual-Node Failure & Local Recovery | 15.0s | `Communication Failure` + `Compute Failure` | SAT-04 & SAT-02 | **Multi-Subsystem Coordination**: Relay reassignment in Plane A + watchdog reset recovery (`RESET_COMPUTE`) for SAT-02 |
| `cascade_failure` | Cascading Multi-Subsystem Failure | 16.0s | 4 faults (Propulsion, Comms, Node Loss, Compute) | SAT-05, SAT-08, SAT-10, SAT-01 | **Complex Fault Containment**: Hardware failures permanently isolated/contained while compute upset recovers autonomously |
| `stale_state` | Stale-State Disagreement & Reset | 12.0s | `Stale State` (Moderate) | SAT-01 (Plane A) | **Eventual Consistency & Watchdog**: Consensus epoch lag detected, trust penalized, automated watchdog reset restores nominal state |
| `byzantine_node` | Byzantine Spacecraft Quarantine | 10.0s | `Byzantine Behavior` (Critical) | SAT-10 (Plane C) | **Adversarial Cyber-Resilience**: Peer telemetry cross-check detects contradictory data; trust drops $<0.40$; node isolated/quarantined |
| `seeded_random_faults` | Seeded Stochastic Fault Benchmark | 15.0s | Pseudo-random stochastic generator | Constellation | **Stochastic Reproducibility**: Pseudo-random faults evaluated with fixed seed for bit-for-bit repeatability across test runs |

---

## Detailed Scenario Walkthroughs

### 1. `propulsion_failure` (Section 3.1 & 15.4)
* **Rationale**: Directly proves the ASTRANET core thesis: *"Model each spacecraft as a bundle of capabilities rather than a binary alive/dead node."*
* **Fault Injection**: SAT-03 experiences thruster valve leak at $t=2.0\text{s}$.
* **Autonomy Response**: Subsystem `propulsion` drops to `DEGRADED`. Active orbital station-keeping is flagged lost (`capabilities.maneuvering = False`), but SAT-03 retains Earth observation payload (`sensing = True`), ISL packet routing (`relay = True`), navigation (`navigation = True`), and compute/storage.
* **Acceptance**: Constellation maintains 11 nominal satellites, 1 degraded satellite, 0 failed satellites, and $\ge 4$ active ISL links.

### 2. `comms_failure` (Section 16 & 18)
* **Rationale**: Validates autonomous peer observation and intra-plane relay failover.
* **Fault Injection**: Primary relay SAT-08 in Plane B experiences total transmitter burnout at $t=2.0\text{s}$.
* **Autonomy Response**: Neighbor nodes in Plane B observe link loss within $<1.0\text{s}$. SAT-08 is attributed as unrecoverable hardware failure. Surviving healthy observer SAT-06 in Plane B is autonomously promoted to `RELAY`, restoring intra-plane ISL communications.
* **Acceptance**: Relay handover message observed, SAT-08 contained in `FAILED`, 11 nominal satellites, $\ge 4$ active links.

### 3. `low_energy` (Section 3.18 & 16)
* **Rationale**: Demonstrates resource-aware degradation under severe power constraints.
* **Fault Injection**: SAT-05 experiences solar array regulator failure at $t=2.0\text{s}$.
* **Autonomy Response**: Battery drops to critical threshold ($45\%$). System sheds high-power payload demands to safeguard core telemetry and attitude control, entering survivable degraded mode.
* **Acceptance**: Anomaly bounded within $1.0\text{s}$, SAT-05 contained in degraded operation, 0 manual intervention required.

### 4. `stale_state` (Section 3.10 & 3.11)
* **Rationale**: Tests consensus under stale and inconsistent local views.
* **Fault Injection**: SAT-01 experiences epoch desynchronization at $t=2.0\text{s}$.
* **Autonomy Response**: Quorum detects delayed epoch; trust rating is penalized (drops from $0.99 \to 0.64$). Flight computer watchdog triggers automated `RESET_COMPUTE`. Within $3.0\text{s}$, flight software re-synchronizes and returns SAT-01 to full `NOMINAL` operational status.
* **Acceptance**: Recovery task `RESET_COMPUTE` completes, final nominal satellites = 12, final failed satellites = 0.

### 5. `byzantine_node` (Section 3.13 & 3.14)
* **Rationale**: Demonstrates adversarial cyber-resilience and Byzantine node quarantine.
* **Fault Injection**: Malicious/corrupted telemetry injected into SAT-10 at $t=2.0\text{s}$.
* **Autonomy Response**: Cross-verification by peer satellites detects contradictory sensor vectors. SAT-10 trust score drops to $0.38$ (below safety threshold $0.40$). Node is quarantined: role set to `ISOLATED` and excluded from coordinator consensus voting.
* **Acceptance**: SAT-10 contained in state `ISOLATED`, 11 nominal satellites, surviving constellation decision-making safeguarded.
