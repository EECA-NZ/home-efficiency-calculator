"""
Module for the checkbox behaviour endpoint.
"""

from fastapi import APIRouter, HTTPException

from ..models.response_models import CheckboxData
from ..models.user_answers import BasicHouseholdAnswers
from ..services.cost_calculator import determine_gas_connection_checkbox

router = APIRouter()


@router.post("/checkbox-behaviour", response_model=CheckboxData)
def gas_connection_checkbox_details(answers: BasicHouseholdAnswers) -> CheckboxData:
    """
    Determine the checkbox behaviour based on the user's home answers.
    """
    try:
        checkbox = determine_gas_connection_checkbox(answers)
        if checkbox is None:
            raise HTTPException(status_code=400, detail="Checkbox data not found")
        if not isinstance(checkbox, dict):
            raise HTTPException(status_code=400, detail="Invalid checkbox data format")
        return CheckboxData(**checkbox)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
