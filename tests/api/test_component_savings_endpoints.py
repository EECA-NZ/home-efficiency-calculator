"""
Tests for the API
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_cooktop_savings_specific_alternative():
    """
    Test the /cooktop/savings endpoint with a specific
    alternative cooktop provided.
    """
    profile_data = {
        "your_home": {
            "people_in_house": 1,
            "postcode": "6012",
            "disconnect_gas": True,
        },
        "cooktop_answers": {
            "cooktop": "Piped gas",
            "alternative_cooktop": "Electric induction",
        },
    }

    response = client.post("/cooktop/savings", json=profile_data)
    assert response.status_code == 200
    response_data = response.json()

    assert len(response_data["alternatives"]) == 1
    assert "Electric induction" in response_data["alternatives"]
    assert response_data["user_geography"]["edb_region"] == "Wellington Electricity"
    assert response_data["user_geography"]["climate_zone"] == "Wellington"
    assert isinstance(response_data["alternatives"], dict)


def test_cooktop_savings_all_alternatives():
    """
    Test the /cooktop/savings endpoint without a specific
    alternative cooktop provided.
    """
    profile_data = {
        "your_home": {
            "people_in_house": 1,
            "postcode": "6012",
            "disconnect_gas": True,
        },
        "cooktop_answers": {
            "cooktop": "Piped gas",
        },
    }

    response = client.post("/cooktop/savings", json=profile_data)
    assert response.status_code == 200
    response_data = response.json()

    assert "Electric induction" in response_data["alternatives"]
    assert "Piped gas" in response_data["alternatives"]
    assert "Bottled gas" in response_data["alternatives"]
    assert "Electric (coil or ceramic)" in response_data["alternatives"]
    assert response_data["user_geography"]["edb_region"] == "Wellington Electricity"
    assert response_data["user_geography"]["climate_zone"] == "Wellington"
