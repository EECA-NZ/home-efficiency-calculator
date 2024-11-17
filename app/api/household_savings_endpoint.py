"""
Module for the household energy profile endpoint.
"""

from fastapi import APIRouter, HTTPException

from ..models.response_models import HouseholdSavingsResponse, UserGeography
from ..models.user_answers import HouseholdAnswers
from ..services.cost_calculator import (
    assemble_fuel_savings,
    assemble_total_savings,
    calculate_component_savings,
    calculate_fixed_cost_savings,
)
from ..services.energy_calculator import estimate_usage_from_profile
from ..services.get_climate_zone import climate_zone
from ..services.get_energy_plans import postcode_to_edb_zone

router = APIRouter()


@router.post("/household-energy-profile/", response_model=HouseholdSavingsResponse)
def household_energy_profile(profile: HouseholdAnswers):
    """
    Calculate savings and emissions reductions for the household energy profile.

    Returns:
    - Savings and emissions reductions for heating, hot water, cooking, and driving.
    """
    try:
        user_geography = UserGeography(
            climate_zone=climate_zone(profile.your_home.postcode),
            edb_region=postcode_to_edb_zone(profile.your_home.postcode),
        )
        response, totals = calculate_component_savings(profile)
        gas_connection_savings = calculate_fixed_cost_savings(profile)
        total_fuel_savings = assemble_fuel_savings(totals)
        total_savings = assemble_total_savings(totals, gas_connection_savings)
        current_fuel_use_profile = estimate_usage_from_profile(
            profile, round_to_2dp=True
        )
        alternative_fuel_use_profile = estimate_usage_from_profile(
            profile, use_alternatives=True, round_to_2dp=True
        )
        return HouseholdSavingsResponse(
            heating_fuel_savings=response.get("heating", None),
            hot_water_fuel_savings=response.get("hot_water", None),
            cooktop_fuel_savings=response.get("cooktop", None),
            driving_fuel_savings=response.get("driving", None),
            total_fuel_savings=total_fuel_savings,
            gas_connection_savings=gas_connection_savings,
            total_savings=total_savings,
            user_geography=user_geography,
            current_fuel_use=current_fuel_use_profile,
            alternative_fuel_use=alternative_fuel_use_profile,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
