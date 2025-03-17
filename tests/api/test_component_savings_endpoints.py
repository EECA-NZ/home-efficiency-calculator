"""
Tests for the API
"""

import os

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(autouse=True, scope="session")
def set_test_environment_variable():
    """
    Set the TEST_MODE environment variable to True.
    This will ensure that the test data is used, allowing
    the tests to run without the need for data files that
    are not licensed for sharing publicly.
    """
    os.environ["TEST_MODE"] = "True"


client = TestClient(app)


def test_heating_savings_specific_alternative():
    """
    Test the /heating/savings endpoint with specific
    alternative heating source provided.
    """
    profile_data = {
        "your_home": {
            "people_in_house": 1,
            "postcode": "9810",
            "disconnect_gas": True,
        },
        "heating_answers": {
            "main_heating_source": "Piped gas heater",
            "alternative_main_heating_source": "Heat pump",
            "heating_during_day": "Never",
            "insulation_quality": "Not well insulated",
        },
    }
    response = client.post("/heating/savings", json=profile_data)
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data["alternatives"]) == 1
    assert "Heat pump" in response_data["alternatives"]
    assert isinstance(response_data["alternatives"], dict)


def test_heating_savings_all_alternatives():
    """
    Test the /heating/savings endpoint without specific
    alternative heating source provided.
    """
    profile_data = {
        "your_home": {
            "people_in_house": 1,
            "postcode": "9810",
            "disconnect_gas": True,
        },
        "heating_answers": {
            "main_heating_source": "Piped gas heater",
            "heating_during_day": "Never",
            "insulation_quality": "Not well insulated",
        },
    }
    response = client.post("/heating/savings", json=profile_data)
    assert response.status_code == 200
    response_data = response.json()

    assert "Piped gas heater" in response_data["alternatives"]
    assert "Bottled gas heater" in response_data["alternatives"]
    assert "Heat pump" in response_data["alternatives"]
    assert "Electric heater" in response_data["alternatives"]
    assert "Wood burner" in response_data["alternatives"]


def test_hot_water_savings_specific_alternative():
    """
    Test the /hot_water/savings endpoint with a specific
    alternative hot water source provided.
    """
    profile_data = {
        "your_home": {
            "people_in_house": 1,
            "postcode": "8022",
            "disconnect_gas": True,
        },
        "hot_water_answers": {
            "hot_water_usage": "Low",
            "hot_water_heating_source": "Electric hot water cylinder",
            "alternative_hot_water_heating_source": "Hot water heat pump",
        },
    }

    response = client.post("/hot_water/savings", json=profile_data)
    assert response.status_code == 200
    response_data = response.json()

    assert len(response_data["alternatives"]) == 1
    assert "Hot water heat pump" in response_data["alternatives"]
    assert response_data["user_geography"]["edb_region"] == "Orion New Zealand Ltd"
    assert response_data["user_geography"]["climate_zone"] == "Christchurch"


def test_hot_water_savings_without_alternative():
    """
    Test the /hot_water/savings endpoint without a specific
    alternative hot water source provided.
    """
    profile_data = {
        "your_home": {
            "people_in_house": 1,
            "postcode": "8022",
            "disconnect_gas": True,
        },
        "hot_water_answers": {
            "hot_water_usage": "Low",
            "hot_water_heating_source": "Electric hot water cylinder",
        },
    }

    response = client.post("/hot_water/savings", json=profile_data)
    assert response.status_code == 200
    response_data = response.json()

    assert "Hot water heat pump" in response_data["alternatives"]
    assert response_data["user_geography"]["edb_region"] == "Orion New Zealand Ltd"
    assert response_data["user_geography"]["climate_zone"] == "Christchurch"


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


def test_driving_savings_specific_alternative():
    """
    Test the /driving/savings endpoint with a specific
    alternative vehicle type provided.
    """
    profile_data = {
        "your_home": {
            "people_in_house": 1,
            "postcode": "1024",
            "disconnect_gas": True,
        },
        "driving_answers": {
            "vehicle_type": "Petrol",
            "alternative_vehicle_type": "Electric",
            "vehicle_size": "Small",
            "km_per_week": "50 or less",
        },
    }

    response = client.post("/driving/savings", json=profile_data)
    assert response.status_code == 200
    response_data = response.json()

    assert len(response_data["alternatives"]) == 1
    assert "Electric" in response_data["alternatives"]
    assert response_data["user_geography"]["edb_region"] == "Vector"
    assert response_data["user_geography"]["climate_zone"] == "Auckland"


def test_driving_savings_all_alternatives():
    """
    Test the /driving/savings endpoint without a specific
    alternative vehicle type provided.
    """
    profile_data = {
        "your_home": {
            "people_in_house": 1,
            "postcode": "1024",
            "disconnect_gas": True,
        },
        "driving_answers": {
            "vehicle_type": "Petrol",
            "vehicle_size": "Small",
            "km_per_week": "50 or less",
        },
    }

    response = client.post("/driving/savings", json=profile_data)
    assert response.status_code == 200
    response_data = response.json()

    assert "Petrol" in response_data["alternatives"]
    assert "Diesel" in response_data["alternatives"]
    assert "Hybrid" in response_data["alternatives"]
    assert "Plug-in hybrid" in response_data["alternatives"]
    assert "Electric" in response_data["alternatives"]
    assert response_data["user_geography"]["edb_region"] == "Vector"
    assert response_data["user_geography"]["climate_zone"] == "Auckland"
