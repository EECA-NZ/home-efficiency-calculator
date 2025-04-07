"""
Tests for the checkbox behaviour API endpoint.
"""

import os

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(autouse=True, scope="session")
def set_test_environment_variable():
    """
    Ensure TEST_MODE environment variable is set.
    """
    os.environ["TEST_MODE"] = "True"


client = TestClient(app)


def test_checkbox_behaviour_removing_gas_connection():
    """ "
    Test the checkbox behaviour when removing gas connection.
    """
    profile_data = {
        "your_home": {"people_in_house": 1, "postcode": "6012"},
        "heating": {
            "main_heating_source": "Piped gas heater",
            "alternative_main_heating_source": "Heat pump",
            "heating_during_day": "Never",
            "insulation_quality": "Not well insulated",
        },
        "hot_water": {
            "hot_water_usage": "Low",
            "hot_water_heating_source": "Electric hot water cylinder",
            "alternative_hot_water_heating_source": "Electric hot water cylinder",
        },
        "cooktop": {
            "cooktop": "Electric induction",
            "alternative_cooktop": "Electric induction",
        },
        "driving": {
            "vehicle_size": "Small",
            "km_per_week": "50 or less",
            "vehicle_type": "Petrol",
            "alternative_vehicle_type": "Petrol",
        },
        "solar": {"add_solar": True},
        "other": {"fixed_cost_changes": True},
    }

    response = client.post("/checkbox-behaviour/", json=profile_data)
    assert response.status_code == 200, "Expected HTTP 200 OK"

    expected_checkbox_data = {
        "checkbox_visible": True,
        "checkbox_text": "Savings associated with removing your gas connection",
        "checkbox_greyed_out": False,
        "checkbox_default_on": True,
    }
    assert (
        response.json() == expected_checkbox_data
    ), "Mismatch in checkbox behaviour when removing gas connection"


def test_checkbox_behaviour_when_gas_connection_should_stay():
    """ "
    Test the checkbox behaviour when gas connection should stay.
    """
    profile_data = {
        "your_home": {"people_in_house": 1, "postcode": "6012"},
        "heating": {
            "main_heating_source": "Piped gas heater",
            "alternative_main_heating_source": "Heat pump",
            "heating_during_day": "Never",
            "insulation_quality": "Not well insulated",
        },
        "hot_water": {
            "hot_water_usage": "Low",
            "hot_water_heating_source": "Electric hot water cylinder",
            "alternative_hot_water_heating_source": "Electric hot water cylinder",
        },
        "cooktop": {
            "cooktop": "Electric induction",
            "alternative_cooktop": "Piped gas",
        },
        "driving": {
            "vehicle_size": "Small",
            "km_per_week": "50 or less",
            "vehicle_type": "Petrol",
            "alternative_vehicle_type": "Petrol",
        },
        "solar": {"add_solar": True},
        "other": {"fixed_cost_changes": True},
    }

    response = client.post("/checkbox-behaviour/", json=profile_data)
    assert response.status_code == 200, "Expected HTTP 200 OK"

    expected_checkbox_data = {
        "checkbox_visible": True,
        "checkbox_text": "Savings associated with removing your gas connection",
        "checkbox_greyed_out": True,
        "checkbox_default_on": False,
    }
    assert (
        response.json() == expected_checkbox_data
    ), "Mismatch in checkbox behaviour when gas connection should stay"


def test_checkbox_behaviour_invalid_input():
    """ "
    Test the checkbox behaviour with invalid input data.
    """
    profile_data = {"your_home": {"postcode": "6012"}}  # Missing required fields

    response = client.post("/checkbox-behaviour/", json=profile_data)
    assert response.status_code == 422, "Expected HTTP 422 for invalid input"
    assert "detail" in response.json(), "Expected detail in error response"
