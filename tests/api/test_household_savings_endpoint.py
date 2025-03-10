"""
Tests for the API
"""

from fastapi.testclient import TestClient

import app.services.configuration as cfg
from app.api.household_savings_endpoint import household_energy_profile
from app.main import app
from app.models.user_answers import HouseholdAnswers

client = TestClient(app)


def test_read_root():
    """
    Test the root endpoint to ensure it returns the correct response.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert "<html>" in response.text


def test_household_energy_profile():
    """
    Test the /household-energy-profile/ endpoint with valid input data.
    """

    profile_data = {
        "your_home": {
            "people_in_house": 3,
            "postcode": "6012",
            "disconnect_gas": True,
        },
        "heating": {
            "main_heating_source": "Heat pump",
            "alternative_main_heating_source": "Wood burner",
            "heating_during_day": "5-7 days a week",
            "insulation_quality": "Moderately insulated",
        },
        "hot_water": {
            "hot_water_usage": "Average",
            "hot_water_heating_source": "Electric hot water cylinder",
            "alternative_hot_water_heating_source": "Hot water heat pump",
        },
        "cooktop": {
            "cooktop": "Electric induction",
            "alternative_cooktop": "Piped gas",
        },
        "driving": {
            "vehicle_type": "Hybrid",
            "alternative_vehicle_type": "Electric",
            "vehicle_size": "Medium",
            "km_per_week": "200",
        },
        "solar": {
            "hasSolar": False,
        },
    }

    response = client.post("/household-energy-profile/", json=profile_data)
    print(response.json())
    assert response.status_code == 200
    response_data = response.json()

    assert "heating_fuel_savings" in response_data
    assert "hot_water_fuel_savings" in response_data
    assert "cooktop_fuel_savings" in response_data
    assert "driving_fuel_savings" in response_data
    assert "total_fuel_savings" in response_data
    assert "gas_connection_savings" in response_data

    assert isinstance(response_data["heating_fuel_savings"], dict)
    assert isinstance(response_data["hot_water_fuel_savings"], dict)
    assert isinstance(response_data["cooktop_fuel_savings"], dict)
    assert isinstance(response_data["driving_fuel_savings"], dict)
    assert isinstance(response_data["total_fuel_savings"], dict)
    assert isinstance(response_data["gas_connection_savings"], dict)


def test_complete_household_energy_profile():
    """
    Test the /household-energy-profile/ endpoint with
    complete details and alternatives provided.
    """
    profile_data = {
        "your_home": {
            "people_in_house": 1,
            "postcode": "3010",
            "disconnect_gas": True,
        },
        "heating": {
            "main_heating_source": "Piped gas heater",
            "alternative_main_heating_source": "Heat pump",
            "heating_during_day": "Never",
            "insulation_quality": "Not well insulated",
        },
        "hot_water": {
            "hot_water_usage": "Low",
            "hot_water_heating_source": "Electric hot water cylinder",
            "alternative_hot_water_heating_source": "Hot water heat pump",
        },
        "cooktop": {
            "cooktop": "Piped gas",
            "alternative_cooktop": "Electric induction",
        },
        "driving": {
            "vehicle_type": "Petrol",
            "alternative_vehicle_type": "Electric",
            "vehicle_size": "Small",
            "km_per_week": "50 or less",
        },
        "solar": {"hasSolar": True},
    }

    response = client.post("/household-energy-profile/", json=profile_data)
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["heating_fuel_savings"] is not None
    assert response_data["hot_water_fuel_savings"] is not None
    assert response_data["cooktop_fuel_savings"] is not None
    assert response_data["driving_fuel_savings"] is not None
    assert response_data["total_fuel_savings"] is not None
    assert response_data["gas_connection_savings"] is not None
    assert response_data["user_geography"]["edb_region"] == "Unison Networks Ltd"
    assert response_data["user_geography"]["climate_zone"] == "Rotorua"


def test_partial_household_energy_profile():
    """
    Test the /household-energy-profile/ endpoint with
    some components missing alternative details.
    """
    profile_data = {
        "your_home": {
            "people_in_house": 1,
            "postcode": "3010",
            "disconnect_gas": True,
        },
        "heating": {
            "main_heating_source": "Piped gas heater",
            "heating_during_day": "Never",
            "insulation_quality": "Not well insulated",
        },
        "hot_water": {
            "hot_water_usage": "Low",
            "hot_water_heating_source": "Electric hot water cylinder",
            "alternative_hot_water_heating_source": "Hot water heat pump",
        },
        "cooktop": {
            "cooktop": "Piped gas",
            "alternative_cooktop": "Electric induction",
        },
    }

    response = client.post("/household-energy-profile/", json=profile_data)
    assert response.status_code == 200
    response_data = response.json()

    assert response_data["heating_fuel_savings"] is None
    assert response_data["hot_water_fuel_savings"] is not None
    assert response_data["cooktop_fuel_savings"] is not None
    assert response_data["driving_fuel_savings"] is None
    assert response_data["total_fuel_savings"] is not None
    assert response_data["gas_connection_savings"] is not None
    assert response_data["user_geography"]["edb_region"] == "Unison Networks Ltd"
    assert response_data["user_geography"]["climate_zone"] == "Rotorua"


def test_household_energy_profile_incomplete_answers():
    """
    Check that the endpoint copes with an incomplete input.
    """
    household_profile = HouseholdAnswers(
        your_home=cfg.get_default_your_home_answers(),
        heating=cfg.get_default_heating_answers(),
        hot_water=cfg.get_default_hot_water_answers(),
    )
    household_energy_profile(household_profile)
