"""
Tests for the fixed costs savings API endpoint.
"""

import os

import pytest
from fastapi.testclient import TestClient
from pytest import approx

from app.main import app


@pytest.fixture(autouse=True, scope="session")
def set_test_environment_variable():
    """
    Ensure TEST_MODE environment variable is set.
    """
    os.environ["TEST_MODE"] = "True"


client = TestClient(app)


def test_fixed_cost_savings_removing_gas_connection():
    """ "
    Test the fixed costs savings when removing gas connection.
    """
    profile_data = {
        "your_home": {"people_in_house": 1, "postcode": "6012"},
        "heating": {
            "main_heating_source": "Piped gas heater",
            "alternative_main_heating_source": "Heat pump",
            "heating_during_day": "Never",
            "insulation_quality": "Moderately insulated",
        },
        "hot_water": {
            "hot_water_usage": "Average",
            "hot_water_heating_source": "Piped gas instantaneous",
            "alternative_hot_water_heating_source": "Electric hot water cylinder",
        },
        "cooktop": {
            "cooktop": "Piped gas",
            "alternative_cooktop": "Electric induction",
        },
        "driving": {
            "vehicle_size": "Medium",
            "km_per_week": "200",
            "vehicle_type": "Petrol",
            "alternative_vehicle_type": "Petrol",
        },
        "solar": {"add_solar": False},
        "other": {"fixed_cost_changes": True},
    }

    response = client.post("/fixed-costs/savings/", json=profile_data)
    assert response.status_code == 200, "Expected HTTP 200 OK"

    savings_data = response.json()

    expected_savings = {
        "natural_gas": {
            "variable_cost_nzd": {
                "current": approx(370.54),
                "alternative": approx(0),
                "absolute_reduction": approx(370.54),
                "percentage_reduction": approx(100),
            },
            "emissions_kg_co2e": {
                "current": approx(0),
                "alternative": approx(0),
                "absolute_reduction": approx(0),
                "percentage_reduction": approx(0),
            },
        },
        "lpg": {
            "variable_cost_nzd": {
                "current": approx(0),
                "alternative": approx(0),
                "absolute_reduction": approx(0),
                "percentage_reduction": approx(0),
            },
            "emissions_kg_co2e": {
                "current": approx(0),
                "alternative": approx(0),
                "absolute_reduction": approx(0),
                "percentage_reduction": approx(0),
            },
        },
    }

    assert (
        savings_data["gas_connection_savings"] == expected_savings
    ), "Mismatch in gas connection savings data when removing gas connection"


def test_fixed_cost_savings_keeping_gas_connection():
    """ "
    Test the fixed costs savings when keeping gas connection.
    """
    profile_data = {
        "your_home": {"people_in_house": 1, "postcode": "6012"},
        "heating": {
            "main_heating_source": "Piped gas heater",
            "alternative_main_heating_source": "Heat pump",
            "heating_during_day": "Never",
            "insulation_quality": "Moderately insulated",
        },
        "hot_water": {
            "hot_water_usage": "Average",
            "hot_water_heating_source": "Piped gas instantaneous",
            "alternative_hot_water_heating_source": "Electric hot water cylinder",
        },
        "cooktop": {
            "cooktop": "Electric induction",
            "alternative_cooktop": "Piped gas",
        },
        "driving": {
            "vehicle_size": "Medium",
            "km_per_week": "200",
            "vehicle_type": "Petrol",
            "alternative_vehicle_type": "Petrol",
        },
        "solar": {"add_solar": False},
        "other": {"fixed_cost_changes": True},
    }

    response = client.post("/fixed-costs/savings/", json=profile_data)
    assert response.status_code == 200, "Expected HTTP 200 OK"

    savings_data = response.json()

    expected_savings = {
        "natural_gas": {
            "variable_cost_nzd": {
                "current": approx(370.54),
                "alternative": approx(370.54),
                "absolute_reduction": approx(0),
                "percentage_reduction": approx(0),
            },
            "emissions_kg_co2e": {
                "current": approx(0),
                "alternative": approx(0),
                "absolute_reduction": approx(0),
                "percentage_reduction": approx(0),
            },
        },
        "lpg": {
            "variable_cost_nzd": {
                "current": approx(0),
                "alternative": approx(0),
                "absolute_reduction": approx(0),
                "percentage_reduction": approx(0),
            },
            "emissions_kg_co2e": {
                "current": approx(0),
                "alternative": approx(0),
                "absolute_reduction": approx(0),
                "percentage_reduction": approx(0),
            },
        },
    }

    assert (
        savings_data["gas_connection_savings"] == expected_savings
    ), "Mismatch in gas connection savings data when keeping gas connection"


def test_fixed_cost_savings_invalid_input():
    """ "
    Test the fixed costs savings endpoint with invalid input.
    """
    profile_data = {"your_home": {"postcode": "6012"}}

    response = client.post("/fixed-costs/savings/", json=profile_data)
    assert response.status_code == 422, "Expected HTTP 422 for invalid input"
    assert "detail" in response.json(), "Expected detail in error response"
