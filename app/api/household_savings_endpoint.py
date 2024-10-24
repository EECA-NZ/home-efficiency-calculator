"""
Module for the household energy profile endpoint.
"""

from fastapi import APIRouter

from ..models.user_answers import HouseholdEnergyProfileAnswers
from ..services.cost_calculator import calculate_savings_for_option_provided
from ..services.helpers import round_floats_to_2_dp, safe_percentage_reduction

router = APIRouter()


@router.post("/household-energy-profile/")
def household_energy_profile(profile: HouseholdEnergyProfileAnswers):
    """
    Calculate savings and emissions reductions for the household energy profile.
    Returns:
    - Savings and emissions reductions for heating, hot water, cooking, and driving.
    """
    components = [
        ("heating", "main_heating_source"),
        ("hot_water", "hot_water_heating_source"),
        ("cooktop", "cooktop"),
        ("driving", "vehicle_type"),
    ]
    response = {}
    household = {
        "total_nzd_savings": 0,
        "co2_per_year_current": 0,
        "co2_per_year_alternative": 0,
    }

    for component, field in components:
        component_attr = getattr(profile, component, None)
        if component_attr and getattr(component_attr, f"alternative_{field}", None):
            savings = calculate_savings_for_option_provided(
                component_attr, profile.your_home
            )
            household["total_nzd_savings"] += savings["variable_cost_nzd"]["savings"]
            household["co2_per_year_current"] += savings["emissions_kg_co2e"]["current"]
            household["co2_per_year_alternative"] += savings["emissions_kg_co2e"][
                "alternative"
            ]
            response[component] = savings

    # Calculate overall savings and emissions reduction
    household["cost_nzd_current"] = sum(
        s["variable_cost_nzd"]["current"] for s in response.values()
    )
    household["cost_nzd_alternative"] = sum(
        s["variable_cost_nzd"]["alternative"] for s in response.values()
    )
    household["cost_nzd_percentage_savings"] = safe_percentage_reduction(
        household["cost_nzd_current"], household["cost_nzd_alternative"]
    )
    household["co2_per_year_percentage_reduction"] = safe_percentage_reduction(
        household["co2_per_year_current"], household["co2_per_year_alternative"]
    )

    response["overall"] = household
    return round_floats_to_2_dp(response)
