import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from tests.contracts.schemas import SatelliteState

FIXTURES = Path(__file__).parent.parent / "fixtures"


def load(name):
    return json.loads((FIXTURES / name).read_text())


def test_valid_satellite_passes():
    sat = SatelliteState(**load("sample_satellite.json"))
    assert sat.id == "SAT-01"


def test_missing_field_fails():
    data = load("sample_satellite.json")
    del data["battery"]
    with pytest.raises(ValidationError):
        SatelliteState(**data)


def test_wrong_type_fails():
    data = load("sample_satellite.json")
    data["plane"] = "not a number"
    with pytest.raises(ValidationError):
        SatelliteState(**data)
