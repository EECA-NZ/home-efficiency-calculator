"""
This module provides functions to optimize the cost of energy for a household.
"""

# pylint: disable=too-many-locals

import logging

import numpy as np

from ..constants import CHECKBOX_BEHAVIOUR, DAYS_IN_YEAR
from ..models.response_models import SavingsData
from ..models.usage_profiles import EnergyCostBreakdown, YearlyFuelUsageProfile
from ..models.user_answers import OtherAnswers
from ..services.energy_calculator import uses_lpg, uses_natural_gas
from ..services.helpers import round_floats_to_2_dp, safe_percentage_reduction
from .energy_calculator import emissions_kg_co2e
from .helpers import safe_percentage_reduction
from .postcode_lookups.get_energy_plans import get_energy_plan

logger = logging.getLogger(__name__)


def costs_and_emissions(answers, your_plan, solar_aware, your_home):
    """
    Calculate the current household energy costs and emissions.

    Args:
    answers: UserAnswers object
    your_plan: HouseholdEnergyPlan object
    your_home: YourHomeAnswers object

    Returns:
    Tuple containing:
    - EnergyCostBreakdown
    - emissions [float] in kg CO2e
    """
    energy_use = (
        answers.energy_usage_pattern(your_home, solar_aware)
        if answers
        else YearlyFuelUsageProfile()
    )
    cost: EnergyCostBreakdown = your_plan.calculate_cost(energy_use)
    my_emissions_kg_co2e = emissions_kg_co2e(energy_use)
    return cost, my_emissions_kg_co2e


def calculate_savings_for_option(option, field, answers, your_home, solar_aware):
    """
    Calculate the savings and emissions reduction for a given option.

    Returns:
    - A dictionary structured to fit into the SavingsData model.
    """

    if type(answers).__name__ == "DrivingAnswers":
        current_plan = get_energy_plan(your_home.postcode, answers.vehicle_type)
        alternative_plan = get_energy_plan(your_home.postcode, option)
    else:
        current_plan = get_energy_plan(your_home.postcode, "None")
        alternative_plan = get_energy_plan(your_home.postcode, "None")
    current_cost, current_emissions_kg_co2e = costs_and_emissions(
        answers, current_plan, solar_aware, your_home
    )

    alternative_answers = answers.model_copy()
    setattr(alternative_answers, field, option)
    alternative_cost, alternative_emissions_kg_co2e = costs_and_emissions(
        alternative_answers, alternative_plan, solar_aware, your_home
    )

    absolute_cost_savings = (
        current_cost.variable_cost_nzd - alternative_cost.variable_cost_nzd
    )
    percentage_cost_reduction = safe_percentage_reduction(
        current_cost.variable_cost_nzd, alternative_cost.variable_cost_nzd
    )
    absolute_emissions_reduction = (
        current_emissions_kg_co2e - alternative_emissions_kg_co2e
    )
    emissions_reduction_percentage = safe_percentage_reduction(
        current_emissions_kg_co2e, alternative_emissions_kg_co2e
    )
    return {
        "variable_cost_nzd": {
            "current": current_cost.variable_cost_nzd,
            "alternative": alternative_cost.variable_cost_nzd,
            "absolute_reduction": absolute_cost_savings,
            "percentage_reduction": percentage_cost_reduction,
        },
        "emissions_kg_co2e": {
            "current": current_emissions_kg_co2e,
            "alternative": alternative_emissions_kg_co2e,
            "absolute_reduction": absolute_emissions_reduction,
            "percentage_reduction": emissions_reduction_percentage,
        },
    }


def generate_savings_options(answers, field, your_home, solar_aware):
    """
    For each fuel switching option, calculate the savings in dollars and the
    percentage reduction in emissions, formatted to fit directly into a Pydantic model.
    """
    if not answers:
        raise ValueError("Answers object is None")
    if not hasattr(answers, field):
        raise ValueError(f"Field {field} not found in answers")

    options = getattr(type(answers).model_fields[field], "annotation").__args__

    logger.info("Generating savings options for %s", field)
    return_dictionary = {}
    for option in options:
        return_dictionary[option] = calculate_savings_for_option(
            option, field, answers, your_home, solar_aware
        )
    current_fuel_use = answers.energy_usage_pattern(your_home, solar_aware)
    return return_dictionary, current_fuel_use


def determine_gas_connection_checkbox(profile):
    """
    Determine the behaviour of the gas connection checkbox.

    Returns:
    - A dictionary of fixed cost savings for each gas connection.
    """
    current_uses_natural_gas = uses_natural_gas(profile)
    current_uses_lpg = uses_lpg(profile)
    alternative_uses_natural_gas = uses_natural_gas(profile, use_alternatives=True)
    alternative_uses_lpg = uses_lpg(profile, use_alternatives=True)

    return CHECKBOX_BEHAVIOUR[
        (
            current_uses_natural_gas,
            current_uses_lpg,
            alternative_uses_natural_gas,
            alternative_uses_lpg,
        )
    ]


def calculate_fixed_cost_savings(profile):
    """
    Calculate the fixed cost savings for the household, by inferring
    the type of gas connection (if any) that could be disconnected.
    If other_answers.fixed_cost_changes is False, no disconnection is assumed.

    Returns:
    - A dictionary of fixed cost savings for each gas connection.
    """
    if profile.driving is not None:
        your_plan = get_energy_plan(
            profile.your_home.postcode, profile.driving.vehicle_type
        )
    else:
        your_plan = get_energy_plan(profile.your_home.postcode, "None")

    other_answers = OtherAnswers(fixed_cost_changes=True)
    current_uses_natural_gas = uses_natural_gas(profile)
    current_uses_lpg = uses_lpg(profile)
    alternative_uses_natural_gas = uses_natural_gas(profile, use_alternatives=True)
    alternative_uses_lpg = uses_lpg(profile, use_alternatives=True)

    current_natural_gas_fixed_cost = (
        your_plan.natural_gas_plan.fixed_rate * DAYS_IN_YEAR
        if current_uses_natural_gas
        else 0
    )
    current_lpg_fixed_cost = (
        your_plan.lpg_plan.fixed_rate * DAYS_IN_YEAR if current_uses_lpg else 0
    )
    alternative_natural_gas_fixed_cost = (
        your_plan.natural_gas_plan.fixed_rate * DAYS_IN_YEAR
        if alternative_uses_natural_gas
        else 0
    )
    alternative_lpg_fixed_cost = (
        your_plan.lpg_plan.fixed_rate * DAYS_IN_YEAR if alternative_uses_lpg else 0
    )

    fixed_cost_savings_dict = {}
    fixed_cost_savings_dict["natural_gas"] = {
        "current": current_natural_gas_fixed_cost,
        "alternative": (
            alternative_natural_gas_fixed_cost
            if other_answers.fixed_cost_changes
            else current_natural_gas_fixed_cost
        ),
        "absolute_reduction": (
            current_natural_gas_fixed_cost - alternative_natural_gas_fixed_cost
            if other_answers.fixed_cost_changes
            else 0
        ),
        "percentage_reduction": (
            safe_percentage_reduction(
                current_natural_gas_fixed_cost, alternative_natural_gas_fixed_cost
            )
            if not np.isnan(
                safe_percentage_reduction(
                    current_natural_gas_fixed_cost, alternative_natural_gas_fixed_cost
                )
            )
            and other_answers.fixed_cost_changes
            else 0
        ),
    }
    fixed_cost_savings_dict["lpg"] = {
        "current": current_lpg_fixed_cost,
        "alternative": (
            alternative_lpg_fixed_cost
            if other_answers.fixed_cost_changes
            else current_lpg_fixed_cost
        ),
        "absolute_reduction": (
            current_lpg_fixed_cost - alternative_lpg_fixed_cost
            if other_answers.fixed_cost_changes
            else 0
        ),
        "percentage_reduction": (
            safe_percentage_reduction(
                current_lpg_fixed_cost, alternative_lpg_fixed_cost
            )
            if not np.isnan(
                safe_percentage_reduction(
                    current_lpg_fixed_cost, alternative_lpg_fixed_cost
                )
            )
            and other_answers.fixed_cost_changes
            else 0
        ),
    }
    fixed_cost_savings_dict = round_floats_to_2_dp(fixed_cost_savings_dict)
    return {
        fuel: {
            "variable_cost_nzd": SavingsData(**data),
            "emissions_kg_co2e": SavingsData(
                current=0, alternative=0, absolute_reduction=0, percentage_reduction=0
            ),
        }
        for fuel, data in fixed_cost_savings_dict.items()
    }
