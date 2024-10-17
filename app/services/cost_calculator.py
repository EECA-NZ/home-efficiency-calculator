"""
This module provides functions to optimize the cost of energy for a household.
"""

from .energy_calculator import emissions, estimate_usage_from_profile
from .get_energy_plans import energy_plan


def find_lowest_cost(profiles, pricing_structures):
    """
    Find the lowest cost energy plan for a household

    Args:
    profiles: list of HouseholdEnergyProfileAnswers objects
    pricing_structures: list of HouseholdEnergyPlan objects

    Returns:
    min_cost: float, the lowest cost found
    """
    min_cost = float("inf")
    best_plan = None
    best_profile = None
    for plan in pricing_structures:
        for profile in profiles:
            usage_profile = estimate_usage_from_profile(profile)
            cost = plan.calculate_cost(usage_profile)
            if cost < min_cost:
                min_cost = cost
                best_plan = plan
                best_profile = profile
    return min_cost, best_plan, best_profile


def calculate_savings_options(answers, field, your_home):
    """
    For each fuel switching option, calculate the savings in dollars and the
    percentage reduction in emissions.
    """
    result = {}
    # Retrieve the current energy plan based on the user's postcode
    your_plan = energy_plan(your_home.postcode)
    # Get all the possible options for the given field (e.g., 'main_heating_source')
    options = getattr(type(answers).model_fields[field], "annotation").__args__
    for option in options:
        # Calculate savings for each option
        result[option] = calculate_savings_for_option(
            option, field, answers, your_plan, your_home
        )
    return result


def calculate_current_usage_and_costs(answers, your_plan, your_home):
    """
    Calculate the current household energy costs and emissions.
    """
    household_energy_use = answers.energy_usage_pattern(your_home)
    household_energy_costs = your_plan.calculate_cost(household_energy_use)
    household_emissions = emissions(household_energy_use)
    return household_energy_costs, household_emissions


def calculate_savings_for_option(option, field, answers, your_plan, your_home):
    """
    Calculate the savings and emissions reduction for a given option.
    """

    # Calculate the current energy use, costs, and emissions
    current_costs, current_emissions = calculate_current_usage_and_costs(
        answers, your_plan, your_home
    )

    # Create a copy of the answers and set the new option for the specified field
    alternative_answers = answers.model_copy()
    setattr(alternative_answers, field, option)

    # Calculate the energy use, costs, and emissions for the alternative option
    alternative_use = alternative_answers.energy_usage_pattern(your_home)
    alternative_costs = your_plan.calculate_cost(alternative_use)
    alternative_emissions = emissions(alternative_use)

    # Calculate the savings and emissions reduction percentage
    savings = current_costs - alternative_costs
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
