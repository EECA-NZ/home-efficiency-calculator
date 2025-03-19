"""
Module for the household energy profile endpoint.
"""

from fastapi import APIRouter, HTTPException

from ..models.response_models import SolarSavingsResponse
from ..models.user_answers import HouseholdAnswers
from ..services.solar_calculator import calculate_solar_savings

router = APIRouter()


@router.post("/solar/savings", response_model=SolarSavingsResponse)
def household_energy_profile(profile: HouseholdAnswers):
    """
    Calculate savings and emissions reductions for the household energy profile.

    Returns:
    - Savings and emissions reductions for heating, hot water, cooking, and driving.
    """
    assert (
        profile.heating.alternative_main_heating_source is not None
    ), "Missing alternative heating source"
    assert (
        profile.hot_water.alternative_hot_water_heating_source is not None
    ), "Missing alternative hot water heating source"
    assert (
        profile.cooktop.alternative_cooktop is not None
    ), "Missing alternative cooktop"
    assert (
        profile.driving.alternative_vehicle_type is not None
    ), "Missing alternative vehicle type"
    assert profile.solar.add_solar, "Missing solar details"

    try:
        solar_savings = calculate_solar_savings(profile)
        return SolarSavingsResponse(**solar_savings)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
