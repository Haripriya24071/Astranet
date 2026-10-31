import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from tests.contracts.enums import FAILURE_TYPES, MISSION_STATES
from tests.contracts.schemas import (
    EventLog,
    FaultEvent,
    RecoveryCandidate,
    RecoveryDecision,
    ResilienceSnapshot,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"

# (model, fixture file, field to delete, field to break, bad value)
CASES = [
    (FaultEvent, "sample_fault_event.json", "target", "severity", "bad"),
    (RecoveryCandidate, "sample_recovery_candidate.json", "planId", "risk", "bad"),
    (RecoveryDecision, "sample_recovery_decision.json", "selectedPlanId", "ranking", "not a list"),
    (ResilienceSnapshot, "sample_resilience_snapshot.json", "coverage", "connectivity", "bad"),
    (EventLog, "sample_event_log.json", "eventType", "timestamp", "bad"),
]


def load(name):
    return json.loads((FIXTURES / name).read_text())


@pytest.mark.parametrize("model,file,missing,broken,bad", CASES)
def test_valid_passes(model, file, missing, broken, bad):
    model(**load(file))


@pytest.mark.parametrize("model,file,missing,broken,bad", CASES)
def test_missing_field_fails(model, file, missing, broken, bad):
    data = load(file)
    del data[missing]
    with pytest.raises(ValidationError):
        model(**data)


@pytest.mark.parametrize("model,file,missing,broken,bad", CASES)
def test_wrong_type_fails(model, file, missing, broken, bad):
    data = load(file)
    data[broken] = bad
    with pytest.raises(ValidationError):
        model(**data)


def test_fault_type_is_known():
    assert load("sample_fault_event.json")["failureType"] in FAILURE_TYPES


def test_mission_states_are_known():
    d = load("sample_recovery_decision.json")
    assert d["missionStateBefore"] in MISSION_STATES
    assert d["missionStateAfter"] in MISSION_STATES