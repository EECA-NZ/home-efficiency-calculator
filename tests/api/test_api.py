"""
Tests for the API
"""

from fastapi.testclient import TestClient

from app.main import app

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
            "postcode": "1234",
            "disconnect_gas": True,
            "user_provided": True,
        },
        "heating": {
            "main_heating_source": "Heat pump",
            "alternative_main_heating_source": "Wood burner",
            "heating_during_day": "5-7 days a week",
            "insulation_quality": "Moderately insulated",
            "user_provided": True,
        },
        "hot_water": {
            "hot_water_usage": "Average",
            "hot_water_heating_source": "Electric hot water cylinder",
            "alternative_hot_water_heating_source": "Hot water heat pump",
            "user_provided": True,
        },
        "cooktop": {
            "cooktop": "Electric induction",
            "alternative_cooktop": "Piped gas",
            "user_provided": True,
        },
        "driving": {
            "vehicle_type": "Hybrid",
            "alternative_vehicle_type": "Electric",
            "vehicle_size": "Medium",
            "km_per_week": "200",
            "user_provided": True,
        },
        "solar": {
            "hasSolar": False,
            "user_provided": True,
        },
    }

    response = client.post("/household-energy-profile/", json=profile_data)
    assert response.status_code == 200
    response_data = response.json()

    assert "heating_savings" in response_data
    assert "hot_water_savings" in response_data
    assert "cooktop_savings" in response_data
    assert "driving_savings" in response_data
    assert "overall_savings" in response_data

    assert isinstance(response_data["heating_savings"], float)
    assert isinstance(response_data["overall_savings"], float)
    assert "heating_emissions_reduction" in response_data
    assert isinstance(response_data["heating_emissions_reduction"], float)
