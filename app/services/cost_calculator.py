"""
This module provides functions to optimize the cost of energy for a household.
"""

from ..models.response_models import SavingsData, SavingsResponse
from ..models.usage_profiles import YearlyFuelUsageProfile
from .energy_calculator import emissions_kg_co2e
from .get_energy_plans import get_energy_plan
from .helpers import round_floats_to_2_dp, safe_percentage_reduction


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
    # Assume no vehicle for now (so no fixed vehicle ownership costs)
    your_plan = get_energy_plan(your_home.postcode, "None")

    # Calculate the current energy use, costs, and emissions
    _, current_variable_costs, current_emissions_kg_co2e = costs_and_emissions(
        answers, your_plan, your_home
    )

    # Create a copy of the answers and set the new option for the specified field
    alternative_answers = answers.model_copy()
    setattr(alternative_answers, field, option)

    # Calculate the energy use, costs, and emissions for the alternative option
    _, alternative_variable_costs, alternative_emissions_kg_co2e = costs_and_emissions(
        alternative_answers, your_plan, your_home
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
    options = getattr(type(answers).model_fields[field], "annotation").__args__

    return_dictionary = {}
    for option in options:
        return_dictionary[option] = calculate_savings_for_option(
            option, field, answers, your_home
        )

    return return_dictionary


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
        ("cooktop", "cooktop"),
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
