"""
Module for the gas fixed cost savings endpoint
"""

from fastapi import APIRouter, HTTPException

from ..models.response_models import FixedCostsResponse
from ..models.user_answers import BasicHouseholdAnswers
from ..services.cost_calculator import calculate_fixed_cost_savings

router = APIRouter()


@router.post("/fixed-costs/savings", response_model=FixedCostsResponse)
def fixed_cost_savings(answers: BasicHouseholdAnswers) -> FixedCostsResponse:
    """
    Endpoint to retrieve gas fixed cost savings based on the user's home answers.
    """
    try:
        gas_connection_savings = calculate_fixed_cost_savings(answers)
        if gas_connection_savings is None:
            raise HTTPException(
                status_code=400, detail="Gas connection savings not found"
            )
        if not isinstance(gas_connection_savings, dict):
            raise HTTPException(
                status_code=400, detail="Invalid gas connection savings data"
            )
        return FixedCostsResponse(gas_connection_savings=gas_connection_savings)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
