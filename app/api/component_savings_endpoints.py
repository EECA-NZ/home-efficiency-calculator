"""
This module provides functions to estimate savings for individual
components of the home.
"""

import logging
from typing import Type

from fastapi import FastAPI, HTTPException

from ..models.response_models import (
    ComponentSavingsResponse,
    SavingsData,
    SavingsResponse,
    UserGeography,
)
from ..models.user_answers import CooktopAnswers, YourHomeAnswers
from ..services.cost_calculator import generate_savings_options
from ..services.get_climate_zone import climate_zone
from ..services.get_energy_plans import postcode_to_edb_zone
from ..services.helpers import round_floats_to_2_dp

# Set up logging
logger = logging.getLogger(__name__)

app = FastAPI()


# pylint: disable=broad-exception-caught
async def calculate_component_savings(
    component_answers: Type, component_name: str, your_home: YourHomeAnswers
):
    """
    Calculate the savings for a given component.

    Parameters
    ----------
    component_answers : Type
        The user's answers for the component.

    component_name : str
        The name of the component.

    your_home : YourHomeAnswers
        The user's answers for their home.

    Returns
    -------
    ComponentSavingsResponse
        The savings for the component.
    """
    try:
        options_dict = generate_savings_options(
            component_answers, component_name, your_home
        )
        options_dict = round_floats_to_2_dp(options_dict)
        if getattr(component_answers, f"alternative_{component_name}", None):
            specific_alternative = getattr(
                component_answers, f"alternative_{component_name}"
            )
            options_dict = {
                key: val
                for key, val in options_dict.items()
                if key == specific_alternative
            }
        user_geography = {
            "edb_region": postcode_to_edb_zone(your_home.postcode),
            "climate_zone": climate_zone(your_home.postcode),
        }
        return options_dict, user_geography
    except Exception as e:
        logger.error("Error calculating %s savings: %s", component_name, e)
        return {"error": f"Error calculating {component_name} savings: {e}"}


# Common function to handle the response creation
async def create_response(data, component_name):
    """
    Create the response for a given household component.

    Parameters
    ----------
    data : dict
        The data to be used in the response.

    component_name : str
        The name of the household component.

    Returns
    -------
    ComponentSavingsResponse
        The response for the household component.
    """
    (options_dict, user_geography) = data
    if "error" in options_dict:
        logger.error("Error calculating %s savings: %s", component_name, data["error"])
        raise HTTPException(status_code=500, detail=data["error"])
    options_response = {
        key: SavingsResponse(
            variable_cost_nzd=SavingsData(**val["variable_cost_nzd"]),
            emissions_kg_co2e=SavingsData(**val["emissions_kg_co2e"]),
        )
        for key, val in options_dict.items()
    }
    user_geography = UserGeography(**user_geography)
    return ComponentSavingsResponse(
        alternatives=options_response, user_geography=user_geography
    )


@app.post("/cooktop/savings", response_model=ComponentSavingsResponse)
async def cooktop_savings(cooktop_answers: CooktopAnswers, your_home: YourHomeAnswers):
    """
    Endpoint to calculate savings for the cooktop

    If an alternative cooktop is provided,
    calculate the savings for that cooktop.
    Otherwise, generate savings options for
    all possible cooktops.

    Parameters
    ----------
    cooktop_answers : CooktopAnswers
        The user's answers for the cooktop.

    your_home : YourHomeAnswers
        The user's answers for their home.

    Returns
    -------
    SavingsResponse
        The savings for the cooktop component.
    """
    data = await calculate_component_savings(cooktop_answers, "cooktop", your_home)
    return await create_response(data, "cooktop")
