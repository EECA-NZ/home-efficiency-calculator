"""
This module provides functions to optimize the cost of energy for a household.
"""

import numpy as np

from ..constants import CHECKBOX_BEHAVIOUR, DAYS_IN_YEAR
from ..models.response_models import SavingsData, SavingsResponse
from ..models.usage_profiles import YearlyFuelUsageProfile
from ..services.energy_calculator import uses_lpg, uses_natural_gas
from ..services.get_energy_plans import get_energy_plan
from ..services.helpers import round_floats_to_2_dp, safe_percentage_reduction
from .energy_calculator import emissions_kg_co2e
from .get_energy_plans import get_energy_plan
from .helpers import safe_percentage_reduction


def costs_and_emissions(answers, your_plan, your_home):
    """
    Calculate the current household energy costs and emissions.

    Args:
    answers: UserAnswers object
    your_plan: HouseholdEnergyPlan object
    your_home: YourHomeAnswers object

    Returns:
    Tuple[float, float, float], the fixed cost, variable cost, and emissions
    for the household. Units are NZD, NZD, and kg CO2e, respectively.
    """
    energy_use = (
        answers.energy_usage_pattern(your_home) if answers else YearlyFuelUsageProfile()
    )
    (fixed_cost_nzd, variable_cost_nzd) = your_plan.calculate_cost(energy_use)
    my_emissions_kg_co2e = emissions_kg_co2e(energy_use)
    return fixed_cost_nzd, variable_cost_nzd, my_emissions_kg_co2e


def calculate_savings_for_option(option, field, answers, your_home):
    """
    Calculate the savings and emissions reduction for a given option.

    Returns:
    - A dictionary structured to fit into the SavingsData model.
    """
    if type(answers).__name__ == "DrivingAnswers":
        current_plan = get_energy_plan(your_home.postcode, answers.vehicle_type)
        alternative_plan = get_energy_plan(your_home.postcode, option)
    else:
        # The other parts of the house aren't affected by 'other vehicle costs'
        # so we can get a plan for any vehicle type
        current_plan = get_energy_plan(your_home.postcode, "None")
        alternative_plan = get_energy_plan(your_home.postcode, "None")

    # Calculate the current energy use, costs, and emissions
    _, current_variable_costs, current_emissions_kg_co2e = costs_and_emissions(
        answers, current_plan, your_home
    )

    # Create a copy of the answers and set the new option for the specified field
    alternative_answers = answers.model_copy()
    setattr(alternative_answers, field, option)

    # Calculate the energy use, costs, and emissions for the alternative option
    _, alternative_variable_costs, alternative_emissions_kg_co2e = costs_and_emissions(
        alternative_answers, alternative_plan, your_home
    )

    # Calculate the absolute and percentage savings and emissions reduction
    absolute_cost_savings = current_variable_costs - alternative_variable_costs
    percentage_cost_reduction = safe_percentage_reduction(
        current_variable_costs, alternative_variable_costs
    )
    absolute_emissions_reduction = (
        current_emissions_kg_co2e - alternative_emissions_kg_co2e
    )
    emissions_reduction_percentage = safe_percentage_reduction(
        current_emissions_kg_co2e, alternative_emissions_kg_co2e
    )

    return {
        "variable_cost_nzd": {
            "current": current_variable_costs,
            "alternative": alternative_variable_costs,
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


def generate_savings_options(answers, field, your_home):
    """
    For each fuel switching option, calculate the savings in dollars and the
    percentage reduction in emissions, formatted to fit directly into a Pydantic model.
    """
    if not answers:
        raise ValueError("Answers object is None")
    if not hasattr(answers, field):
        raise ValueError(f"Field {field} not found in answers")

    # Get all the possible options for the given field (e.g., 'main_heating_source')
    options = getattr(type(answers).model_fields[field], "annotation").__args__

    return_dictionary = {}
    for option in options:
        return_dictionary[option] = calculate_savings_for_option(
            option, field, answers, your_home
        )

    current_fuel_use = answers.energy_usage_pattern(your_home)

    return return_dictionary, current_fuel_use


def calculate_savings_for_option_provided(answers, your_home):
    """
    Calculate the savings and emissions reduction for a given option.
    """
    if type(answers).__name__ == "HeatingAnswers":
        option = answers.alternative_main_heating_source
        field = "main_heating_source"
    elif type(answers).__name__ == "HotWaterAnswers":
        option = answers.alternative_hot_water_heating_source
        field = "hot_water_heating_source"
    elif type(answers).__name__ == "CooktopAnswers":
        option = answers.alternative_cooktop
        field = "cooktop"
    elif type(answers).__name__ == "DrivingAnswers":
        option = answers.alternative_vehicle_type
        field = "vehicle_type"
    else:
        raise ValueError("Invalid answers type")
    return calculate_savings_for_option(option, field, answers, your_home)


def calculate_component_savings(profile):
    """
    Calculate the savings and emissions reductions for each component.

    Returns:
    - A dictionary of savings and emissions reductions for each component.
    """
    response = {}
    total_current_variable_costs = 0
    total_alternative_variable_costs = 0
    total_current_emissions = 0
    total_alternative_emissions = 0

    household_components = [
        ("heating", "main_heating_source"),
        ("hot_water", "hot_water_heating_source"),
        ("cooktop", "cooktop"),
        ("driving", "vehicle_type"),
    ]

    for component, field in household_components:
        component_attr = getattr(profile, component, None)
        if component_attr is None:
            continue

        alternative_field = f"alternative_{field}"
        if (
            hasattr(component_attr, field)
            and hasattr(component_attr, alternative_field)
            and getattr(component_attr, field) is not None
            and getattr(component_attr, alternative_field) is not None
        ):
            savings_dict = calculate_savings_for_option_provided(
                component_attr, profile.your_home
            )

            savings_dict = round_floats_to_2_dp(savings_dict)
            response[component] = SavingsResponse(
                variable_cost_nzd=SavingsData(**savings_dict["variable_cost_nzd"]),
                emissions_kg_co2e=SavingsData(**savings_dict["emissions_kg_co2e"]),
            )

            total_current_variable_costs += savings_dict["variable_cost_nzd"]["current"]
            total_alternative_variable_costs += savings_dict["variable_cost_nzd"][
                "alternative"
            ]
            total_current_emissions += savings_dict["emissions_kg_co2e"]["current"]
            total_alternative_emissions += savings_dict["emissions_kg_co2e"][
                "alternative"
            ]

    totals = {
        "total_current_variable_costs": total_current_variable_costs,
        "total_alternative_variable_costs": total_alternative_variable_costs,
        "total_current_emissions": total_current_emissions,
        "total_alternative_emissions": total_alternative_emissions,
    }
    return response, totals


def assemble_fuel_savings(totals):
    """
    Calculate fuel cost and CO2 savings for the household.

    Returns:
    - A dictionary of fuel cost and CO2 savings for the household.
    """
    variable_costs_savings_dict = {
        "current": totals["total_current_variable_costs"],
        "alternative": totals["total_alternative_variable_costs"],
        "absolute_reduction": totals["total_current_variable_costs"]
        - totals["total_alternative_variable_costs"],
        "percentage_reduction": safe_percentage_reduction(
            totals["total_current_variable_costs"],
            totals["total_alternative_variable_costs"],
        ),
    }
    emissions_savings_dict = {
        "current": totals["total_current_emissions"],
        "alternative": totals["total_alternative_emissions"],
        "absolute_reduction": totals["total_current_emissions"]
        - totals["total_alternative_emissions"],
        "percentage_reduction": safe_percentage_reduction(
            totals["total_current_emissions"], totals["total_alternative_emissions"]
        ),
    }
    variable_costs_savings_dict = round_floats_to_2_dp(variable_costs_savings_dict)
    emissions_savings_dict = round_floats_to_2_dp(emissions_savings_dict)
    return SavingsResponse(
        variable_cost_nzd=SavingsData(**variable_costs_savings_dict),
        emissions_kg_co2e=SavingsData(**emissions_savings_dict),
    )


def assemble_total_savings(totals, gas_disconnection_savings):
    """
    Calculate total cost and CO2 savings for the household.

    Returns:
    - A dictionary of total cost and CO2 savings for the household.
    """
    gas_connection_costs_current = 0
    gas_connection_costs_alternative = 0
    for gas_connection_type in gas_disconnection_savings:
        gas_connection_costs_current += gas_disconnection_savings[gas_connection_type][
            "variable_cost_nzd"
        ].current
        gas_connection_costs_alternative += gas_disconnection_savings[
            gas_connection_type
        ]["variable_cost_nzd"].alternative

    current_cost = totals["total_current_variable_costs"] + gas_connection_costs_current
    alternative_cost = (
        totals["total_alternative_variable_costs"] + gas_connection_costs_alternative
    )
    total_cost_savings_dict = {
        "current": current_cost,
        "alternative": alternative_cost,
        "absolute_reduction": current_cost - alternative_cost,
        "percentage_reduction": safe_percentage_reduction(
            current_cost, alternative_cost
        ),
    }
    emissions_savings_dict = {
        "current": totals["total_current_emissions"],
        "alternative": totals["total_alternative_emissions"],
        "absolute_reduction": totals["total_current_emissions"]
        - totals["total_alternative_emissions"],
        "percentage_reduction": safe_percentage_reduction(
            totals["total_current_emissions"], totals["total_alternative_emissions"]
        ),
    }
    total_cost_savings_dict = round_floats_to_2_dp(total_cost_savings_dict)
    emissions_savings_dict = round_floats_to_2_dp(emissions_savings_dict)
    return SavingsResponse(
        variable_cost_nzd=SavingsData(**total_cost_savings_dict),
        emissions_kg_co2e=SavingsData(**emissions_savings_dict),
    )


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
    If your_home.disconnect_gas is False, no disconnection is assumed.

    Returns:
    - A dictionary of fixed cost savings for each gas connection.
    """
    if profile.driving is not None:
        your_plan = get_energy_plan(
            profile.your_home.postcode, profile.driving.vehicle_type
        )
    else:
        your_plan = get_energy_plan(profile.your_home.postcode, "None")

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
            if profile.your_home.disconnect_gas
            else current_natural_gas_fixed_cost
        ),
        "absolute_reduction": (
            current_natural_gas_fixed_cost - alternative_natural_gas_fixed_cost
            if profile.your_home.disconnect_gas
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
            and profile.your_home.disconnect_gas
            else 0
        ),
    }
    fixed_cost_savings_dict["lpg"] = {
        "current": current_lpg_fixed_cost,
        "alternative": (
            alternative_lpg_fixed_cost
            if profile.your_home.disconnect_gas
            else current_lpg_fixed_cost
        ),
        "absolute_reduction": (
            current_lpg_fixed_cost - alternative_lpg_fixed_cost
            if profile.your_home.disconnect_gas
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
            and profile.your_home.disconnect_gas
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
