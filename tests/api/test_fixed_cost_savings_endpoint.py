"""
Tests for the fixed costs savings API endpoint.
"""

import os

import pytest
from fastapi.testclient import TestClient
from pytest import approx

from app.api.fixed_cost_savings_endpoint import fixed_cost_savings
from app.main import app
from app.models.user_answers import (
    BasicHouseholdAnswers,
    CooktopAnswers,
    DrivingAnswers,
    HeatingAnswers,
    HotWaterAnswers,
    YourHomeAnswers,
)


@pytest.mark.asyncio
async def test_fixed_cost_savings_direct_async():
    """
    Direct async test of fixed_cost_savings function (bypasses HTTP).
    """
    heating = HeatingAnswers(
        main_heating_source="Piped gas heater",
        alternative_main_heating_source="Heat pump",
        heating_during_day="Never",
        insulation_quality="Moderately insulated",
    )
    hot_water = HotWaterAnswers(
        hot_water_usage="Average",
        hot_water_heating_source="Piped gas instantaneous",
        alternative_hot_water_heating_source="Electric hot water cylinder",
    )
    cooktop = CooktopAnswers(
        cooktop="Piped gas",
        alternative_cooktop="Electric induction",
    )
    driving = DrivingAnswers(
        vehicle_size="Medium",
        km_per_week="200",
        vehicle_type="Petrol",
        alternative_vehicle_type="Petrol",
    )
    your_home = YourHomeAnswers(
        people_in_house=1,
        postcode="6012",
    )

    householdanswers = BasicHouseholdAnswers(
        your_home=your_home,
        heating=heating,
        hot_water=hot_water,
        cooktop=cooktop,
        driving=driving,
    )

    result = await fixed_cost_savings(
        householdanswers,
    )

    data = result.model_dump()
    assert "gas_connection_savings" in data
    assert "natural_gas" in data["gas_connection_savings"]
    assert "lpg" in data["gas_connection_savings"]


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
                "current": approx(689.18),
                "alternative": approx(0),
                "absolute_reduction": approx(689.18),
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
                "current": approx(689.18),
                "alternative": approx(689.18),
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
