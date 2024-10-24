"""
Tests for the energy costs module.
"""

from app.models.energy_plans import HouseholdEnergyPlan
from app.models.user_answers import HouseholdEnergyProfileAnswers
from app.services.configuration import (
    get_default_cooktop_answers,
    get_default_diesel_price,
    get_default_driving_answers,
    get_default_electricity_plan,
    get_default_heating_answers,
    get_default_hot_water_answers,
    get_default_lpg_plan,
    get_default_natural_gas_plan,
    get_default_petrol_price,
    get_default_solar_answers,
    get_default_usage_profile,
    get_default_wood_price,
    get_default_your_home_answers,
)
from app.services.energy_calculator import estimate_usage_from_profile


def test_calculate_annual_costs():
    """
    Test the annual cost calculation logic.
    """
    my_plan = HouseholdEnergyPlan(
        name="Basic Household Energy Plan",
        electricity_plan=get_default_electricity_plan(),
        natural_gas_plan=get_default_natural_gas_plan(),
        lpg_plan=get_default_lpg_plan(),
        wood_price=get_default_wood_price(),
        petrol_price=get_default_petrol_price(),
        diesel_price=get_default_diesel_price(),
    )
    my_profile = get_default_usage_profile()
    my_costs = my_plan.calculate_cost(my_profile)
    expected_costs = (730.0, 3444.0)
    assert my_costs == expected_costs


def test_create_household_energy_profile_to_cost():
    """
    Test constructing a profile and plan, and doing a cost calculation.
    """
    household_profile = HouseholdEnergyProfileAnswers(
        your_home=get_default_your_home_answers(),
        heating=get_default_heating_answers(),
        hot_water=get_default_hot_water_answers(),
        cooktop=get_default_cooktop_answers(),
        driving=get_default_driving_answers(),
        solar=get_default_solar_answers(),
    )
    my_plan = HouseholdEnergyPlan(
        name="Basic Household Energy Plan",
        electricity_plan=get_default_electricity_plan(),
        natural_gas_plan=get_default_natural_gas_plan(),
        lpg_plan=get_default_lpg_plan(),
        wood_price=get_default_wood_price(),
        petrol_price=get_default_petrol_price(),
        diesel_price=get_default_diesel_price(),
    )
    household_energy_use = estimate_usage_from_profile(household_profile)
    total_energy_costs = my_plan.calculate_cost(household_energy_use)
    assert sum(total_energy_costs) > 0
