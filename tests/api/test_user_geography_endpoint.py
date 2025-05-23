"""
Tests for the user geography endpoint in the FastAPI application.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(name="client_fixture")
def _client_fixture():
    """
    Provides a test client for the FastAPI application.
    """
    with TestClient(app) as client:
        yield client


test_data = [
    ("9016", {"edb_region": "Aurora Energy", "climate_zone": "Dunedin"}),
    ("6012", {"edb_region": "Wellington Electricity", "climate_zone": "Wellington"}),
    ("1010", {"edb_region": "Vector", "climate_zone": "Auckland"}),
]


@pytest.mark.parametrize("postcode, expected", test_data)
def test_get_user_geography(postcode, expected, client_fixture):
    """
    Test retrieval of geography information based on different postcodes.
    """
    response = client_fixture.post(
        "/user/geography",
        json={"postcode": postcode, "people_in_house": 1},
    )
    assert response.status_code == 200
    assert response.json() == expected
