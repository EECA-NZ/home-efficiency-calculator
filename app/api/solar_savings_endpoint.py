"""
Module for the household energy profile endpoint.
"""

from fastapi import APIRouter, HTTPException

from ..models.response_models import SolarSavingsResponse
from ..models.user_answers import HouseholdAnswers, SolarAnswers
from ..services.solar_calculator import calculate_solar_savings

router = APIRouter()


@router.post("/solar/savings", response_model=SolarSavingsResponse)
def household_energy_profile(profile: HouseholdAnswers):
    """
    Calculate savings and emissions reductions if solar is added to the household.
    Assumes that the user has already provided information about their household
    energy usage. The benefits of solar are calculated assuming that a HEMS is
    also installed, and is able to manage the electricity consumption for EV
    charging and hot water so as to use night-time electricity to make up for
    any shortfall in solar generation.

    Returns:
    - Savings and emissions reductions attributable to adding solar.
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

    # For this endpoint, solar is assumed to be added
    profile.solar = SolarAnswers(add_solar=True)
    try:
        solar_savings = calculate_solar_savings(profile)
        return SolarSavingsResponse(**solar_savings)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
