"""
Tests for the API
"""

import os

import pytest
from fastapi.testclient import TestClient

from app.api.component_savings_endpoints import (
    cooktop_savings,
    driving_savings,
    heating_savings,
    hot_water_savings,
)
from app.main import app
from app.models.user_answers import (
    CooktopAnswers,
    DrivingAnswers,
    HeatingAnswers,
    HotWaterAnswers,
    YourHomeAnswers,
)


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


@pytest.mark.asyncio
async def test_heating_savings_specific_alternative_1():
    """
    Test the /heating/savings endpoint with specific
    alternative heating source provided.
    """
    your_home_data = {
        "people_in_house": 1,
        "postcode": "9810",
    }
    heating_answers_data = {
        "main_heating_source": "Piped gas heater",
        "alternative_main_heating_source": "Heat pump",
        "heating_during_day": "Never",
        "insulation_quality": "Not well insulated",
    }
    your_home = YourHomeAnswers(**your_home_data)
    heating_answers = HeatingAnswers(**heating_answers_data)
    result = await heating_savings(heating_answers, your_home)
    response_data = result.model_dump()
    assert len(response_data["alternatives"]) == 1
    assert "Heat pump" in response_data["alternatives"]
    assert isinstance(response_data["alternatives"], dict)


def test_heating_savings_specific_alternative_2():
    """
    Test the /heating/savings endpoint with specific
    alternative heating source provided.
    """
    answers_data = {
        "your_home": {
            "people_in_house": 1,
            "postcode": "9810",
        },
        "heating_answers": {
            "main_heating_source": "Piped gas heater",
            "alternative_main_heating_source": "Heat pump",
            "heating_during_day": "Never",
            "insulation_quality": "Not well insulated",
        },
    }
    response = client.post("/heating/savings", json=answers_data)
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
    answers_data = {
        "your_home": {
            "people_in_house": 1,
            "postcode": "9810",
        },
        "heating_answers": {
            "main_heating_source": "Piped gas heater",
            "heating_during_day": "Never",
            "insulation_quality": "Not well insulated",
        },
    }
    response = client.post("/heating/savings", json=answers_data)
    assert response.status_code == 200
    response_data = response.json()

    assert "Piped gas heater" in response_data["alternatives"]
    assert "Bottled gas heater" in response_data["alternatives"]
    assert "Heat pump" in response_data["alternatives"]
    assert "Electric heater" in response_data["alternatives"]
    assert "Wood burner" in response_data["alternatives"]


@pytest.mark.asyncio
async def test_hot_water_savings_specific_alternative_1():
    """
    Test the /hot_water/savings endpoint with specific
    alternative hot water source provided with a direct
    call to the function.
    """
    your_home = YourHomeAnswers(people_in_house=1, postcode="8022")
    hot_water_answers = HotWaterAnswers(
        hot_water_usage="Low",
        hot_water_heating_source="Electric hot water cylinder",
        alternative_hot_water_heating_source="Hot water heat pump",
    )
    result = await hot_water_savings(hot_water_answers, your_home)
    response_data = result.model_dump()
    assert len(response_data["alternatives"]) == 1
    assert "Hot water heat pump" in response_data["alternatives"]
    assert response_data["user_geography"]["edb_region"] == "Orion New Zealand Ltd"
    assert response_data["user_geography"]["climate_zone"] == "Christchurch"


def test_hot_water_savings_specific_alternative_2():
    """
    Test the /hot_water/savings endpoint with specific
    alternative hot water source provided.
    """
    answers_data = {
        "your_home": {
            "people_in_house": 1,
            "postcode": "8022",
        },
        "hot_water_answers": {
            "hot_water_usage": "Low",
            "hot_water_heating_source": "Electric hot water cylinder",
            "alternative_hot_water_heating_source": "Hot water heat pump",
        },
    }
    response = client.post("/hot_water/savings", json=answers_data)
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
    answers_data = {
        "your_home": {
            "people_in_house": 1,
            "postcode": "8022",
        },
        "hot_water_answers": {
            "hot_water_usage": "Low",
            "hot_water_heating_source": "Electric hot water cylinder",
        },
    }

    response = client.post("/hot_water/savings", json=answers_data)
    assert response.status_code == 200
    response_data = response.json()

    assert "Hot water heat pump" in response_data["alternatives"]
    assert response_data["user_geography"]["edb_region"] == "Orion New Zealand Ltd"
    assert response_data["user_geography"]["climate_zone"] == "Christchurch"


@pytest.mark.asyncio
async def test_cooktop_savings_specific_alternative_1():
    """
    Test the /cooktop/savings endpoint with specific
    alternative cooktop provided with a direct
    call to the function.
    """
    your_home = YourHomeAnswers(people_in_house=1, postcode="6012")
    cooktop_answers = CooktopAnswers(
        cooktop="Piped gas",
        alternative_cooktop="Electric induction",
    )
    result = await cooktop_savings(cooktop_answers, your_home)
    response_data = result.model_dump()
    assert len(response_data["alternatives"]) == 1
    assert "Electric induction" in response_data["alternatives"]
    assert response_data["user_geography"]["edb_region"] == "Wellington Electricity"
    assert response_data["user_geography"]["climate_zone"] == "Wellington"
    assert isinstance(response_data["alternatives"], dict)


def test_cooktop_savings_specific_alternative_2():
    """
    Test the /cooktop/savings endpoint with specific
    alternative cooktop provided.
    """
    answers_data = {
        "your_home": {
            "people_in_house": 1,
            "postcode": "6012",
        },
        "cooktop_answers": {
            "cooktop": "Piped gas",
            "alternative_cooktop": "Electric induction",
        },
    }
    response = client.post("/cooktop/savings", json=answers_data)
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
    answers_data = {
        "your_home": {
            "people_in_house": 1,
            "postcode": "6012",
        },
        "cooktop_answers": {
            "cooktop": "Piped gas",
        },
    }

    response = client.post("/cooktop/savings", json=answers_data)
    assert response.status_code == 200
    response_data = response.json()

    assert "Electric induction" in response_data["alternatives"]
    assert "Piped gas" in response_data["alternatives"]
    assert "Bottled gas" in response_data["alternatives"]
    assert "Electric (coil or ceramic)" in response_data["alternatives"]
    assert response_data["user_geography"]["edb_region"] == "Wellington Electricity"
    assert response_data["user_geography"]["climate_zone"] == "Wellington"


@pytest.mark.asyncio
async def test_driving_savings_specific_alternative_1():
    """
    Test the /driving/savings endpoint with specific
    alternative vehicle type provided with a direct
    call to the function.
    """
    your_home = YourHomeAnswers(people_in_house=1, postcode="1024")
    driving_answers = DrivingAnswers(
        vehicle_type="Petrol",
        alternative_vehicle_type="Electric",
        vehicle_size="Small",
        km_per_week="50 or less",
    )
    result = await driving_savings(driving_answers, your_home)
    response_data = result.model_dump()
    assert len(response_data["alternatives"]) == 1
    assert "Electric" in response_data["alternatives"]
    assert response_data["user_geography"]["edb_region"] == "Vector"
    assert response_data["user_geography"]["climate_zone"] == "Auckland"


def test_driving_savings_specific_alternative_2():
    """
    Test the /driving/savings endpoint with specific
    alternative vehicle type provided.
    """
    answers_data = {
        "your_home": {
            "people_in_house": 1,
            "postcode": "1024",
        },
        "driving_answers": {
            "vehicle_type": "Petrol",
            "alternative_vehicle_type": "Electric",
            "vehicle_size": "Small",
            "km_per_week": "50 or less",
        },
    }
    response = client.post("/driving/savings", json=answers_data)
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
    answers_data = {
        "your_home": {
            "people_in_house": 1,
            "postcode": "1024",
        },
        "driving_answers": {
            "vehicle_type": "Petrol",
            "vehicle_size": "Small",
            "km_per_week": "50 or less",
        },
    }

    response = client.post("/driving/savings", json=answers_data)
    assert response.status_code == 200
    response_data = response.json()

    assert "Petrol" in response_data["alternatives"]
    assert "Diesel" in response_data["alternatives"]
    assert "Hybrid" in response_data["alternatives"]
    assert "Plug-in hybrid" in response_data["alternatives"]
    assert "Electric" in response_data["alternatives"]
    assert response_data["user_geography"]["edb_region"] == "Vector"
    assert response_data["user_geography"]["climate_zone"] == "Auckland"
