"""
Module for the solar savings endpoint.
"""

from fastapi import APIRouter, HTTPException

from ..models.response_models import SolarSavingsResponse
from ..models.user_answers import BasicHouseholdAnswers
from ..services.helpers import round_floats_to_2_dp
from ..services.solar_calculator.calculate_solar_savings import calculate_solar_savings

router = APIRouter()


@router.post("/solar/savings", response_model=SolarSavingsResponse)
async def get_solar_savings(answers: BasicHouseholdAnswers):
    """
    Calculate savings and emissions reductions if solar is added to the household.
    """
    if answers.heating.alternative_main_heating_source is None:
        raise HTTPException(
            status_code=422, detail="Missing alternative heating source"
        )
    if answers.hot_water.alternative_hot_water_heating_source is None:
        raise HTTPException(
            status_code=422, detail="Missing alternative hot water heating source"
        )
    if answers.cooktop.alternative_cooktop is None:
        raise HTTPException(status_code=422, detail="Missing alternative cooktop")
    if answers.driving.alternative_vehicle_type is None:
        raise HTTPException(status_code=422, detail="Missing alternative vehicle type")

    try:
        solar_savings = calculate_solar_savings(answers)
        solar_savings = round_floats_to_2_dp(solar_savings)
        return SolarSavingsResponse(**solar_savings)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
