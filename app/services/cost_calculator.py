"""
This module provides functions to optimize the cost of energy for a household.
"""

from .energy_calculator import emissions_kg_co2e
from .get_energy_plans import postcode_to_energy_plan


def calculate_savings_options(answers, field, your_home):
    """
    For each fuel switching option, calculate the savings in dollars and the
    percentage reduction in emissions.
    """
    result = {}
    # Retrieve the current energy plan based on the user's postcode
    your_plan = postcode_to_energy_plan(your_home.postcode)
    # Get all the possible options for the given field (e.g., 'main_heating_source')
    options = getattr(type(answers).model_fields[field], "annotation").__args__
    for option in options:
        # Calculate savings for each option
        result[option] = calculate_savings_for_option(
            option, field, answers, your_plan, your_home
        )
    return result


def calculate_usage_and_costs(answers, your_plan, your_home):
    """
    Calculate the current household energy costs and emissions.
    """
    household_energy_use = answers.energy_usage_pattern(your_home)
    household_energy_costs = your_plan.calculate_cost(household_energy_use)
    household_emissions_kg_co2e = emissions_kg_co2e(household_energy_use)
    return household_energy_costs, household_emissions_kg_co2e


def calculate_savings_for_option(option, field, answers, your_plan, your_home):
    """
    Calculate the savings and emissions reduction for a given option.
    """
    # Calculate the current energy use, costs, and emissions
    current_costs, current_emissions = calculate_usage_and_costs(
        answers, your_plan, your_home
    )
    # Create a copy of the answers and set the new option for the specified field
    alternative_answers = answers.model_copy()
    setattr(alternative_answers, field, option)
    # Calculate the energy use, costs, and emissions for the alternative option
    alternative_costs, alternative_emissions = calculate_usage_and_costs(
        alternative_answers, your_plan, your_home
    )
    # Calculate the savings and emissions reduction percentage
    savings = sum(current_costs) - sum(alternative_costs)
    emissions_reduction_percentage = (
        100 * (current_emissions - alternative_emissions) / current_emissions
    )
    return {
        "savings": savings,
        "emissions_reduction_percentage": emissions_reduction_percentage,
    }


# pylint: disable=unused-argument
def calculate_emissions_reduction(answers, your_home):
    """
    Placeholder function to calculate percentage
    emissions reduction based on user input.
    """
    return 20  # Placeholder for actual emissions reduction logic


def calculate_savings(answers, your_home):
    """
    Placeholder function to calculate dollar savings based on user input.
    """
    return 10  # Placeholder for actual savings logic
