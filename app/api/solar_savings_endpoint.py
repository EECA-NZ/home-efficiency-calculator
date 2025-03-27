"""
Module for the solar savings endpoint.
"""

from fastapi import APIRouter, HTTPException

from ..models.response_models import SolarSavingsResponse
from ..models.user_answers import HouseholdAnswers, SolarAnswers
from ..services.helpers import round_floats_to_2_dp
from ..services.solar_calculator import calculate_solar_savings

router = APIRouter()


@router.post("/solar/savings", response_model=SolarSavingsResponse)
def get_solar_savings(profile: HouseholdAnswers):
    """
    Calculate savings and emissions reductions if solar is added to the household.
    Assumes that the user has already provided information about their household
    energy usage. We make the assumption that in addition to solar panels, the
    household installs a home energy management system which enables it to still
    benefit from night rates for the time-flexible part of its load that isn't able
    to be met by solar. (We use a simple load-matching model to estimate how much
    electricity demand can be met by solar, and put the rest onto night rates.)

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
        solar_savings = round_floats_to_2_dp(solar_savings)
        return SolarSavingsResponse(**solar_savings)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
