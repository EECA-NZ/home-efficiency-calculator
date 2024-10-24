"""
This module provides functions to optimize the cost of energy for a household.
"""

from .energy_calculator import emissions_kg_co2e
from .get_energy_plans import postcode_to_energy_plan
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
    energy_use = answers.energy_usage_pattern(your_home)
    (fixed_cost_nzd, variable_cost_nzd) = your_plan.calculate_cost(energy_use)
    my_emissions_kg_co2e = emissions_kg_co2e(energy_use)
    return fixed_cost_nzd, variable_cost_nzd, my_emissions_kg_co2e


def calculate_savings_for_option(option, field, answers, your_plan, your_home):
    """
    Calculate the savings and emissions reduction for a given option.
    """
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
    # Calculate the savings and emissions reduction percentage
    variable_cost_savings = current_variable_costs - alternative_variable_costs
    emissions_reduction_percentage = safe_percentage_reduction(
        current_emissions_kg_co2e, alternative_emissions_kg_co2e
    )
    return {
        "variable_cost_nzd": {
            "current": current_variable_costs,
            "alternative": alternative_variable_costs,
            "savings": variable_cost_savings,
        },
        "emissions_kg_co2e": {
            "current": current_emissions_kg_co2e,
            "alternative": alternative_emissions_kg_co2e,
            "percentage_reduction": emissions_reduction_percentage,
        },
    }


def generate_savings_options(answers, field, your_home):
    """
    For each fuel switching option, calculate the savings in dollars and the
    percentage reduction in emissions.
    """
    result = {}
    # Retrieve the current energy plan based on the user's postcode
    your_plan = postcode_to_energy_plan(your_home.postcode)
    # Get all the possible options for the given field (e.g., 'main_heating_source')
    options = getattr(type(answers).model_fields[field], "annotation").__args__
    # current = getattr(answers, field)
    for option in options:
        # Calculate savings for each option
        result[option] = calculate_savings_for_option(
            option, field, answers, your_plan, your_home
        )
    # Reduce redundancy
    return_dictionary = {}
    for option, details in result.items():
        return_dictionary[option] = {}
        return_dictionary[option]["variable_cost_nzd"] = {}
        return_dictionary[option]["variable_cost_nzd"]["value"] = details[
            "variable_cost_nzd"
        ]["alternative"]
        return_dictionary[option]["variable_cost_nzd"]["savings"] = details[
            "variable_cost_nzd"
        ]["savings"]
        return_dictionary[option]["emissions_kg_co2e"] = {}
        return_dictionary[option]["emissions_kg_co2e"]["value"] = details[
            "emissions_kg_co2e"
        ]["alternative"]
        return_dictionary[option]["emissions_kg_co2e"][
            "percentage_reduction"
        ] = details["emissions_kg_co2e"]["percentage_reduction"]
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
    your_plan = postcode_to_energy_plan(your_home.postcode)
    return calculate_savings_for_option(option, field, answers, your_plan, your_home)
