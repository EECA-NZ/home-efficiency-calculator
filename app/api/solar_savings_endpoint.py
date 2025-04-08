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
def get_solar_savings(answers: BasicHouseholdAnswers):
    """
    Calculate savings and emissions reductions if solar is added to the household.
    """
    assert (
        answers.heating.alternative_main_heating_source is not None
    ), "Missing alternative heating source"
    assert (
        answers.hot_water.alternative_hot_water_heating_source is not None
    ), "Missing alternative hot water heating source"
    assert (
        answers.cooktop.alternative_cooktop is not None
    ), "Missing alternative cooktop"
    assert (
        answers.driving.alternative_vehicle_type is not None
    ), "Missing alternative vehicle type"

    try:
        solar_savings = calculate_solar_savings(answers)
        solar_savings = round_floats_to_2_dp(solar_savings)
        return SolarSavingsResponse(**solar_savings)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
