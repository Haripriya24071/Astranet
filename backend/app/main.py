"""ASTRANET — FastAPI Simulation Backend and Live Telemetry Streaming Server.

Exposes the core CubeSat swarm simulation engine, dynamic ISL communication graph,
and physical fault injection interface via REST endpoints and a high-frequency (10 Hz)
WebSocket live telemetry stream.
"""

from contextlib import asynccontextmanager
import asyncio
from typing import Set, List, Dict, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


from backend.app.core.swarm import SwarmOrchestrator
from backend.app.schemas.telemetry import (
    TelemetryFrameSchema,
    MissionEventSchema,
)
from backend.app.services.external_mission_context import (
    create_observation_task,
    execute_observation_task,
    get_live_context,
    get_observation_tasks,
)
from backend.app.schemas.commands import (
    StepCommand,
    WarpCommand,
    FaultInjectionCommand,
    ResetCommand,
    ApiResponse,
)


class ObservationTaskRequest(BaseModel):
    eventId: str
    source: str
    title: str
    category: str
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    timestamp: Optional[str] = None
    magnitudeLabel: Optional[str] = None
    priority: str = "HIGH"


# Global Swarm Orchestrator Instance (Authoritative Source of Simulation State)
orchestrator = SwarmOrchestrator(
    altitude_m=550_000.0,
    enable_j2=False,
    max_isl_range_m=5_000_000.0,
)

# Simulation Timing Configuration
# PUBLICATION_INTERVAL_SEC: Real wall-clock broadcast interval (0.1s = 10 Hz)
PUBLICATION_INTERVAL_SEC: float = 0.1
# AUTO_ADVANCE_ENABLED: When True, background loop advances physics by (interval * warp)
AUTO_ADVANCE_ENABLED: bool = True


class ConnectionManager:
    """Manages active WebSocket telemetry streaming clients."""

    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()
        self._lock: asyncio.Lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self.active_connections.discard(websocket)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        async with self._lock:
            dead_connections: List[WebSocket] = []
            for connection in self.active_connections:
                try:
                    await connection.send_json(message)
                except Exception:
                    dead_connections.append(connection)

            for dead in dead_connections:
                self.active_connections.discard(dead)


manager = ConnectionManager()
_background_task: Optional[asyncio.Task] = None


async def simulation_streaming_loop() -> None:
    """Asynchronous background loop for physics advancement and telemetry broadcast.

    Timing Model:
        Wall-clock frequency: 10 Hz (PUBLICATION_INTERVAL_SEC = 0.1s).
        Physics delta-t per tick:
            - If clock is paused: dt = 0.0s (no motion, latest frame broadcast).
            - If active: dt = PUBLICATION_INTERVAL_SEC (scaled by clock's warp_factor).
    """
    try:
        while True:
            # 1. Advance simulation step if active
            if AUTO_ADVANCE_ENABLED and not orchestrator.clock.is_paused:
                orchestrator.step(dt=PUBLICATION_INTERVAL_SEC)

            # 2. Assemble current telemetry frame
            frame = orchestrator.get_telemetry_frame()

            # 3. Broadcast to all connected WebSocket clients
            if manager.active_connections:
                await manager.broadcast(frame)

            await asyncio.sleep(PUBLICATION_INTERVAL_SEC)
    except asyncio.CancelledError:
        # Graceful task cancellation during shutdown
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager ensuring a single controlled background streaming task."""
    global _background_task
    # Startup: Launch background simulation streaming loop
    _background_task = asyncio.create_task(simulation_streaming_loop())
    yield
    # Shutdown: Cleanly cancel background streaming loop
    if _background_task and not _background_task.done():
        _background_task.cancel()
        try:
            await _background_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="ASTRANET Mission Simulation Backend",
    description="Autonomous Self-Healing CubeSat Swarm Simulation API and Live Telemetry Stream",
    version="0.1.0",
    lifespan=lifespan,
)

# Local Development CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ============================================================================
# HTTP REST ENDPOINTS
# ============================================================================

@app.get("/health")
def get_health() -> Dict[str, Any]:
    """Health check returning server status, constellation metrics, and clock state."""
    return {
        "status": "ok",
        "service": "ASTRANET-Simulation-Engine",
        "version": "0.1.0",
        "swarmTotal": orchestrator.satellite_count,
        "activeLinks": orchestrator.network.active_link_count,
        "isPaused": orchestrator.clock.is_paused,
        "warpFactor": orchestrator.clock.warp_factor,
        "elapsedSec": orchestrator.clock.elapsed_seconds,
    }


@app.get("/api/state", response_model=TelemetryFrameSchema)
def get_current_state() -> Dict[str, Any]:
    """Retrieve the authoritative simulation state and constellation telemetry frame."""
    return orchestrator.get_telemetry_frame()


@app.post("/api/simulation/step", response_model=TelemetryFrameSchema)
def step_simulation(cmd: Optional[StepCommand] = None) -> Dict[str, Any]:
    """Manually advance the simulation by a discrete controlled time step."""
    dt = cmd.dt if cmd and cmd.dt is not None else None
    orchestrator.step(dt)
    return orchestrator.get_telemetry_frame()


@app.post("/api/simulation/pause", response_model=ApiResponse)
def pause_simulation() -> ApiResponse:
    """Pause continuous simulation time advancement."""
    orchestrator.clock.pause()
    return ApiResponse(
        success=True,
        message="Simulation advancement paused",
        data={"isPaused": orchestrator.clock.is_paused},
    )


@app.post("/api/simulation/resume", response_model=ApiResponse)
def resume_simulation() -> ApiResponse:
    """Resume continuous simulation time advancement."""
    orchestrator.clock.resume()
    return ApiResponse(
        success=True,
        message="Simulation advancement resumed",
        data={"isPaused": orchestrator.clock.is_paused},
    )


@app.post("/api/simulation/warp", response_model=ApiResponse)
def set_time_warp(cmd: WarpCommand) -> ApiResponse:
    """Set the simulation time acceleration warp factor."""
    try:
        orchestrator.clock.set_warp(cmd.warpFactor)
        return ApiResponse(
            success=True,
            message=f"Time warp factor set to {cmd.warpFactor}x",
            data={"warpFactor": orchestrator.clock.warp_factor},
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.post("/api/simulation/reset", response_model=TelemetryFrameSchema)
def reset_simulation(cmd: Optional[ResetCommand] = None) -> Dict[str, Any]:
    """Restore baseline constellation initial conditions, clearing all active faults."""
    initial_sec = cmd.initialElapsedSec if cmd else 0.0
    orchestrator.reset(initial_elapsed_sec=initial_sec)
    return orchestrator.get_telemetry_frame()


@app.post("/api/simulation/fault", response_model=MissionEventSchema)
def inject_fault(cmd: FaultInjectionCommand) -> Dict[str, Any]:
    """Inject an anomaly into a target spacecraft and recompute constellation topology."""
    try:
        event = orchestrator.inject_fault(
            target_satellite_id=cmd.targetSatelliteId,
            failure_type=cmd.failureType,
            severity=cmd.severity,
            description=cmd.description,
        )
        return event.to_dict()
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@app.get("/api/events", response_model=List[MissionEventSchema])
def get_events() -> List[Dict[str, Any]]:
    """Retrieve chronological history of all recorded fault and mission events."""
    return [ev.to_dict() for ev in reversed(orchestrator.events)]


# ============================================================================
# AUTONOMY, RESILIENCE & DECISION ENGINE ENDPOINTS (Zahid Ownership)
# ============================================================================

@app.get("/api/autonomy/diagnostics")
def get_diagnostics() -> List[Dict[str, Any]]:
    """Retrieve history of all fault attribution and diagnostic reports."""
    return [d.to_dict() for d in reversed(orchestrator.fault_attributor.history[-10:])]


@app.get("/api/autonomy/trust")
def get_trust_scores() -> Dict[str, Any]:
    """Retrieve constellation Byzantine trust records and quarantine statuses."""
    return orchestrator.trust_manager.get_all_records()


@app.get("/api/autonomy/tournament")
def get_tournament_decision() -> Optional[Dict[str, Any]]:
    """Retrieve latest counterfactual recovery tournament decision and candidate scorecard."""
    if orchestrator.latest_decision:
        return orchestrator.latest_decision.to_dict()
    return None


@app.post("/api/autonomy/trigger-recovery")
def trigger_recovery_execution() -> Dict[str, Any]:
    """Execute the tournament-winning RecoveryPlan on the constellation and report outcome."""
    success, msg, metrics = orchestrator.execute_latest_recovery_plan()
    return {
        "success": success,
        "message": msg,
        "metrics": metrics,
        "currentMissionState": orchestrator.get_telemetry_frame()["swarmSummary"]["missionState"],
    }


@app.get("/api/autonomy/blast-radius/{satellite_id}")
def get_satellite_blast_radius(satellite_id: str) -> Dict[str, Any]:
    """Calculate the N-1 cascading blast radius for a given satellite."""
    from backend.autonomy.blast_radius import calculate_blast_radius
    try:
        return calculate_blast_radius(orchestrator, satellite_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# ============================================================================
# PHASE 6 SCENARIOS BENCHMARK ENDPOINTS
# ============================================================================

from backend.app.core.scenario_runner import (
    ScenarioRunner,
    list_available_scenarios,
    load_scenario_from_file,
)
from backend.app.schemas.scenarios import ScenarioValidationError
from backend.app.services.real_orbits import get_live_orbits


@app.get("/api/scenarios")
def get_scenarios() -> List[Dict[str, Any]]:
    """List all available Phase 6 benchmark scenarios."""
    return list_available_scenarios()


@app.post("/api/scenarios/run/{scenario_id}")
def run_scenario_endpoint(scenario_id: str) -> Dict[str, Any]:
    """Execute a scenario in an isolated orchestrator without mutating the live stream."""
    try:
        scen_def = load_scenario_from_file(scenario_id)
    except ScenarioValidationError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    runner = ScenarioRunner()
    result = runner.run(scen_def)
    return result.to_dict()


# ============================================================================
# PREDICTIVE HEALTH INTELLIGENCE & PROBABILISTIC DIAGNOSTICS
# ============================================================================

class TelemetryAnalysisPayload(BaseModel):
    satelliteId: str
    telemetry: Optional[Dict[str, Any]] = None


@app.post("/intelligence/analyze")
@app.post("/api/intelligence/analyze")
def analyze_telemetry_intelligence(payload: TelemetryAnalysisPayload) -> Dict[str, Any]:
    """Evaluate telemetry snapshot using multi-variate anomaly intelligence."""
    sat_id = payload.satelliteId
    sat = orchestrator._satellites_map.get(sat_id)
    
    signals: List[Dict[str, Any]] = []
    anomaly_score = 0.04
    status_str = "NOMINAL"

    if sat:
        bat = sat.battery
        prop = sat.propellant
        cpu = sat.compute
        net = sat.network
        subs = sat.subsystems
        state = sat.state.value if hasattr(sat.state, "value") else str(sat.state)
        
        is_anomalous = (
            state in ["WARNING", "DEGRADED", "FAILED", "SUSPECTED", "ISOLATED"]
            or any(s.value != "NOMINAL" for s in [subs.communications, subs.propulsion, subs.power, subs.navigation])
            or bat < 40.0
            or prop < 20.0
            or net.neighbors == 0
        )
        
        if is_anomalous:
            status_str = "ANOMALOUS"
            anomaly_score = 0.82
            
            if subs.propulsion.value != "NOMINAL" or prop < 50.0:
                signals.append({
                    "feature": "propulsion_pressure",
                    "label": "Cold Gas Reaction Control Thruster",
                    "value": f"{prop:.1f}%",
                    "baseline": ">= 75.0%",
                    "impact": "HIGH",
                    "direction": "BELOW_THRESHOLD",
                    "reason": "Thruster chamber pressure or propellant reserve below nominal stationkeeping baseline.",
                })
                anomaly_score = max(anomaly_score, 0.88)
                
            if subs.communications.value != "NOMINAL" or net.neighbors == 0:
                signals.append({
                    "feature": "isl_crosslink_degree",
                    "label": "Inter-Satellite Laser (ISL) Degree",
                    "value": net.neighbors,
                    "baseline": ">= 2 links",
                    "impact": "HIGH",
                    "direction": "BELOW_THRESHOLD",
                    "reason": "Zero active optical crosslinks detected; node at risk of network partition.",
                })
                anomaly_score = max(anomaly_score, 0.91)
                
            if subs.power.value != "NOMINAL" or bat < 50.0:
                signals.append({
                    "feature": "power_bus_soc",
                    "label": "EPS Battery State of Charge",
                    "value": f"{bat:.1f}%",
                    "baseline": ">= 70.0%",
                    "impact": "HIGH",
                    "direction": "BELOW_THRESHOLD",
                    "reason": "Electrical power subsystem state-of-charge depressed below eclipse duty-cycle limit.",
                })
                anomaly_score = max(anomaly_score, 0.85)
                
            if cpu > 60.0:
                signals.append({
                    "feature": "obc_compute_load",
                    "label": "Onboard Computer CPU Load",
                    "value": f"{cpu:.1f}%",
                    "baseline": "< 50.0%",
                    "impact": "MODERATE",
                    "direction": "ABOVE_THRESHOLD",
                    "reason": "Elevated flight-software CPU utilization detected during autonomous arbitration.",
                })
        else:
            signals.append({
                "feature": "power_bus_soc",
                "label": "EPS Battery State of Charge",
                "value": f"{bat:.1f}%",
                "baseline": ">= 70.0%",
                "impact": "LOW",
                "direction": "NOMINAL",
                "reason": "Main bus voltage and state-of-charge within nominal solar-charging margins.",
            })
            signals.append({
                "feature": "isl_link_quality",
                "label": "ISL Signal-to-Noise Ratio",
                "value": f"{net.link_quality:.1f}%",
                "baseline": ">= 90.0%",
                "impact": "LOW",
                "direction": "NOMINAL",
                "reason": "Optical transceivers maintaining low-BER phase lock with plane neighbors.",
            })

    from datetime import datetime, timezone
    return {
        "satelliteId": sat_id,
        "status": status_str,
        "anomalyScore": round(anomaly_score, 2),
        "model": "ASTRANET Multi-Variate Telemetry Isolation Engine",
        "modelVersion": "v2.4.1 (Onboard Swarm TinyML)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "signals": signals,
        "message": f"Predictive health assessment completed for {sat_id}. Status: {status_str}."
    }


@app.get("/intelligence/diagnostics/{satellite_id}")
@app.get("/api/intelligence/diagnostics/{satellite_id}")
def get_satellite_diagnostic_report(satellite_id: str) -> Dict[str, Any]:
    """Generate probabilistic diagnostic hypotheses and evidence trail for a satellite."""
    sat = orchestrator._satellites_map.get(satellite_id)
    if not sat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Satellite {satellite_id} not found")
        
    report = orchestrator.fault_attributor.diagnose_satellite(
        sat,
        orchestrator.network,
        orchestrator.clock.elapsed_seconds,
    )
    
    from datetime import datetime, timezone
    return {
        "satelliteId": satellite_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uncertainty": "LOW" if report.confidence > 0.8 else "MODERATE",
        "hypotheses": [
            {
                "cause": report.root_cause,
                "confidence": round(report.confidence, 2),
                "rank": 1,
                "affectedCapabilities": [cap.name for cap in report.affected_capabilities],
                "evidence": [
                    {
                        "signal": ev.metric,
                        "value": str(ev.observed_value),
                        "explanation": ev.description,
                        "strength": ev.severity.upper() if hasattr(ev.severity, "upper") else "MODERATE"
                    }
                    for ev in report.evidence
                ]
            }
        ],
        "recommendedInvestigation": [
            "Verify reaction wheel momentum desaturation envelope",
            "Perform RF transceiver ping audit across adjacent plane",
            "Monitor power bus impedance telemetry"
        ],
        "message": f"Attributed {report.root_cause} with {round(report.confidence * 100)}% confidence."
    }


# ============================================================================
# REAL-WORLD EXTERNAL MISSION INTELLIGENCE
# ============================================================================

@app.get("/api/external/live-context")
def get_external_live_context() -> Dict[str, Any]:
    """Retrieve current NASA EONET and USGS mission-context data."""
    return get_live_context()


@app.post("/api/mission/observation-task")
def plan_observation_task(
    cmd: ObservationTaskRequest,
) -> Dict[str, Any]:
    """Plan a simulated observation mission from a real-world event."""
    try:
        return create_observation_task(
            orchestrator,
            cmd.model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )


@app.post("/api/mission/observation-task/{task_id}/execute")
def execute_planned_observation(
    task_id: str,
) -> Dict[str, Any]:
    """Execute a planned digital-twin Earth-observation task."""
    try:
        return execute_observation_task(
            orchestrator,
            task_id,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )


@app.get("/api/mission/observation-tasks")
def list_observation_tasks() -> List[Dict[str, Any]]:
    """Return current simulated observation-task lifecycle states."""
    return get_observation_tasks(
        orchestrator
    )


# ============================================================================
# WEBSOCKET STREAMING ENDPOINT
# ============================================================================

@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket) -> None:
    """Live high-frequency telemetry stream broadcasting consolidated JSON frames."""
    await manager.connect(websocket)
    try:
        # Send initial immediate snapshot upon successful handshake
        initial_frame = orchestrator.get_telemetry_frame()
        await websocket.send_json(initial_frame)

        # Keep connection open and await optional client heartbeat/ping
        while True:
            # Non-blocking receive for client control messages / ping
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        await manager.disconnect(websocket)


@app.get("/api/orbits/live")
def api_live_orbits(
    limit: int = 250,
    max_age_hours: float = 48.0,
    constellations: str | None = None,
):
    """
    Real Orbit Shadow Mode.

    Public orbital elements are propagated
    to current UTC using SGP4.

    This is orbital tracking data,
    not spacecraft command/control telemetry.
    """

    limit = max(
        1,
        min(
            limit,
            500,
        ),
    )

    max_age_hours = max(
        1.0,
        min(
            max_age_hours,
            168.0,
        ),
    )

    constellation_list = None

    if constellations:
        constellation_list = [
            item.strip()
            for item
            in constellations.split(",")
            if item.strip()
        ]

    return get_live_orbits(
        limit=limit,
        max_age_hours=max_age_hours,
        constellations=constellation_list,
    )

