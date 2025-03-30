"""
Module for the gas fixed cost savings endpoint
"""

from fastapi import APIRouter, HTTPException

from ..models.response_models import FixedCostsResponse
from ..models.user_answers import HouseholdAnswers
from ..services.cost_calculator import calculate_fixed_cost_savings

router = APIRouter()


@router.post("/gas-fixed-costs/savings/", response_model=FixedCostsResponse)
def household_energy_profile(profile: HouseholdAnswers):
    """
    Endpoint to retrieve gas fixed cost savings based on the user's home answers.

    Returns:
    - Savings and emissions reductions for heating, hot water, cooking, and driving.
    """
    try:
        gas_connection_savings = calculate_fixed_cost_savings(profile)
        return FixedCostsResponse(gas_connection_savings=gas_connection_savings)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
