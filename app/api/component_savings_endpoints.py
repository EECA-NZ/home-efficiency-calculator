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
from ..models.usage_profiles import YearlyFuelUsageReport
from ..models.user_answers import (
    CooktopAnswers,
    DrivingAnswers,
    HeatingAnswers,
    HotWaterAnswers,
    SolarAnswers,
    YourHomeAnswers,
)
from ..services.cost_calculator import generate_savings_options
from ..services.get_climate_zone import climate_zone
from ..services.get_energy_plans import postcode_to_edb_zone
from ..services.helpers import round_floats_to_2_dp

# Set up logging
logger = logging.getLogger(__name__)

app = FastAPI()


# pylint: disable=broad-exception-caught
async def calculate_component_savings(
    component_answers: Type,
    component_name: str,
    your_home: YourHomeAnswers,
    solar: SolarAnswers,
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
        options_dict, current_fuel_use = generate_savings_options(
            component_answers, component_name, your_home, solar
        )
        current_fuel_use = component_answers.energy_usage_pattern(your_home, solar)
        current_fuel_use_report = YearlyFuelUsageReport(
            current_fuel_use, decimal_places=2
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
            alternative_fuel_use = component_answers.energy_usage_pattern(
                your_home, solar, use_alternative=True
            )
            alternative_fuel_use_report = YearlyFuelUsageReport(
                alternative_fuel_use, decimal_places=2
            )
        else:
            alternative_fuel_use_report = None
        user_geography = {
            "edb_region": postcode_to_edb_zone(your_home.postcode),
            "climate_zone": climate_zone(your_home.postcode),
        }
        return (
            options_dict,
            user_geography,
            current_fuel_use_report,
            alternative_fuel_use_report,
        )
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
    (options_dict, user_geography, current_fuel_use, alternative_fuel_use) = data
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
        alternatives=options_response,
        user_geography=user_geography,
        current_fuel_use=current_fuel_use,
        alternative_fuel_use=alternative_fuel_use,
    )


# Endpoint example using the common function
@app.post("/heating/savings", response_model=ComponentSavingsResponse)
async def heating_savings(heating_answers: HeatingAnswers, your_home: YourHomeAnswers):
    """
    Endpoint to calculate savings for heating.

    If an alternative heating source is provided,
    calculate the savings for that source. Otherwise,
    generate savings options for all possible heating
    sources.

    Parameters
    ----------
    heating_answers : HeatingAnswers
        The user's answers for heating.

    your_home : YourHomeAnswers
        The user's answers for their home.

    Returns
    -------
    SavingsResponse
        The savings for the heating component.
    """
    solar = SolarAnswers(hasSolar=False)
    data = await calculate_component_savings(
        heating_answers, "main_heating_source", your_home, solar
    )
    return await create_response(data, "heating")


# Apply similar changes to other endpoints
@app.post("/hot_water/savings", response_model=ComponentSavingsResponse)
async def hot_water_savings(
    hot_water_answers: HotWaterAnswers, your_home: YourHomeAnswers
):
    """
    Endpoint to calculate savings for hot water.

    If an alternative hot water source is provided,
    calculate the savings for that source. Otherwise,
    generate savings options for all possible hot
    water sources.

    Parameters
    ----------
    hot_water_answers : HotWaterAnswers
        The user's answers for hot water.

    your_home : YourHomeAnswers
        The user's answers for their home.

    Returns
    -------
    SavingsResponse
        The savings for the hot water component.
    """
    solar = SolarAnswers(hasSolar=False)
    data = await calculate_component_savings(
        hot_water_answers, "hot_water_heating_source", your_home, solar
    )
    return await create_response(data, "hot_water")


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
    solar = SolarAnswers(hasSolar=False)
    data = await calculate_component_savings(
        cooktop_answers, "cooktop", your_home, solar
    )
    return await create_response(data, "cooktop")


@app.post("/driving/savings", response_model=ComponentSavingsResponse)
async def driving_savings(driving_answers: DrivingAnswers, your_home: YourHomeAnswers):
    """
    Endpoint to calculate savings for driving.

    If an alternative vehicle type is provided,
    calculate the savings for that vehicle type.
    Otherwise, generate savings options for all
    possible vehicle types.

    Parameters
    ----------
    driving_answers : DrivingAnswers
        The user's answers for driving.

    your_home : YourHomeAnswers
        The user's answers for their home.

    Returns
    -------
    SavingsResponse
        The savings for the driving component.
    """
    solar = SolarAnswers(hasSolar=False)
    data = await calculate_component_savings(
        driving_answers, "vehicle_type", your_home, solar
    )
    return await create_response(data, "driving")
