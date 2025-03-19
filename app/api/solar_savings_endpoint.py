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
    try:
        solar_savings = calculate_solar_savings(profile)
        return SolarSavingsResponse(**solar_savings)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
