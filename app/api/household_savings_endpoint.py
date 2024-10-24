"""
Module for the household energy profile endpoint.
"""

import numpy as np
from fastapi import APIRouter

from ..models.user_answers import HouseholdEnergyProfileAnswers
from ..services.cost_calculator import calculate_savings_for_option_provided
from ..services.helpers import round_floats_to_2_dp

router = APIRouter()


@router.post("/household-energy-profile/")
def household_energy_profile(profile: HouseholdEnergyProfileAnswers):
    """
    Calculate savings and emissions reductions for the household energy profile.
    Returns:
    - Savings and emissions reductions for heating, hot water, cooking, and driving.
    """
    response = {"current emissions": 0, "alternative emissions": 0}
    # Calculate heating savings and emissions reduction
    if profile.heating and profile.heating.alternative_main_heating_source:
        heating_savings = calculate_savings_for_option_provided(
            profile.heating, profile.your_home
        )
        response["heating_nzd_savings"] = heating_savings["variable_cost_nzd"][
            "savings"
        ]
        response["current emissions"] += heating_savings["emissions_kg_co2e"]["current"]
        response["alternative emissions"] += heating_savings["emissions_kg_co2e"][
            "alternative"
        ]
    else:
        response["heating_nzd_savings"] = 0

    # Calculate hot water savings and emissions reduction
    if profile.hot_water and profile.hot_water.alternative_hot_water_heating_source:
        hot_water_savings = calculate_savings_for_option_provided(
            profile.hot_water, profile.your_home
        )
        response["hot_water_nzd_savings"] = hot_water_savings["variable_cost_nzd"][
            "savings"
        ]
        response["current emissions"] += hot_water_savings["emissions_kg_co2e"][
            "current"
        ]
        response["alternative emissions"] += hot_water_savings["emissions_kg_co2e"][
            "alternative"
        ]
    else:
        response["hot_water_nzd_savings"] = 0

    # Calculate cooktop savings and emissions reduction
    if profile.cooktop and profile.cooktop.alternative_cooktop:
        cooktop_savings = calculate_savings_for_option_provided(
            profile.cooktop, profile.your_home
        )
        response["cooktop_nzd_savings"] = cooktop_savings["variable_cost_nzd"][
            "savings"
        ]
        response["current emissions"] += cooktop_savings["emissions_kg_co2e"]["current"]
        response["alternative emissions"] += cooktop_savings["emissions_kg_co2e"][
            "alternative"
        ]
    else:
        response["cooktop_nzd_savings"] = 0

    # Calculate driving savings and emissions reduction
    if profile.driving and profile.driving.alternative_vehicle_type:
        driving_savings = calculate_savings_for_option_provided(
            profile.driving, profile.your_home
        )
        response["driving_nzd_savings"] = driving_savings["variable_cost_nzd"][
            "savings"
        ]
        response["current emissions"] += driving_savings["emissions_kg_co2e"]["current"]
        response["alternative emissions"] += driving_savings["emissions_kg_co2e"][
            "alternative"
        ]
    else:
        response["driving_nzd_savings"] = 0

    # Calculate overall savings and emissions reduction
    total_savings = sum(
        value for key, value in response.items() if key.endswith("nzd_savings")
    )

    response["overall_nzd_savings"] = total_savings
    current_emissions = response.pop("current emissions")
    alternative_emissions = response.pop("alternative emissions")

    if current_emissions == 0 and alternative_emissions == 0:
        response["co2_emissions_percent_reduction"] = 0
    elif current_emissions == 0:
        response["co2_emissions_percent_reduction"] = np.nan
    else:
        response["co2_emissions_percent_reduction"] = (
            100 * (current_emissions - alternative_emissions) / current_emissions
        )

    return round_floats_to_2_dp(response)
