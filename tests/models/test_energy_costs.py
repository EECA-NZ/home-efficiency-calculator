"""
Tests for the enests module.
"""

# pylint: disable=no-member

from pytest import approx

from app.models.energy_plans import HouseholdEnergyPlan
from app.models.user_answers import HouseholdAnswers, SolarAnswers
from app.services.configuration import (
    get_default_annual_other_vehicle_costs,
    get_default_cooktop_answers,
    get_default_diesel_price,
    get_default_driving_answers,
    get_default_electricity_plan,
    get_default_heating_answers,
    get_default_hot_water_answers,
    get_default_household_answers,
    get_default_lpg_plan,
    get_default_natural_gas_plan,
    get_default_petrol_price,
    get_default_public_ev_charger_rate,
    get_default_solar_answers,
    get_default_usage_profile,
    get_default_wood_price,
    get_default_your_home_answers,
)
from app.services.energy_calculator import estimate_usage_from_profile

EXPECTED_COSTS_DEFAULT = (730.5, 2855.7395)


def test_calculate_annual_costs():
    """
    Test the annual cost calculation logic.
    """
    my_answers = get_default_household_answers()
    my_profile = get_default_usage_profile()
    my_plan = HouseholdEnergyPlan(
        name="Basic Household Energy Plan",
        electricity_plan=get_default_electricity_plan(),
        natural_gas_plan=get_default_natural_gas_plan(),
        lpg_plan=get_default_lpg_plan(),
        wood_price=get_default_wood_price(),
        petrol_price=get_default_petrol_price(),
        diesel_price=get_default_diesel_price(),
        public_charging_price=get_default_public_ev_charger_rate(),
        other_vehicle_costs=get_default_annual_other_vehicle_costs(
            my_answers["driving"].vehicle_type
        ),
    )
    my_costs = my_plan.calculate_cost(my_profile)
    expected_costs = EXPECTED_COSTS_DEFAULT
    assert my_costs == approx(expected_costs, rel=1e-4)


def test_create_household_energy_profile_to_cost():
    """
    Test constructing a profile and plan, and doing a cost calculation.
    """
    household_profile = HouseholdAnswers(
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
        public_charging_price=get_default_public_ev_charger_rate(),
        other_vehicle_costs=get_default_annual_other_vehicle_costs(
            household_profile.driving.vehicle_type
        ),
    )
    household_energy_use = estimate_usage_from_profile(household_profile)
    total_energy_costs = my_plan.calculate_cost(household_energy_use)
    assert sum(total_energy_costs) > 0


def test_create_household_energy_profile_to_cost_with_solar():
    """
    Test constructing a profile and plan, and doing a cost calculation.
    """
    household_profile = HouseholdAnswers(
        your_home=get_default_your_home_answers(),
        heating=get_default_heating_answers(),
        hot_water=get_default_hot_water_answers(),
        cooktop=get_default_cooktop_answers(),
        driving=get_default_driving_answers(),
        solar=SolarAnswers(has_solar=True),
    )
    my_plan = HouseholdEnergyPlan(
        name="Basic Household Energy Plan",
        electricity_plan=get_default_electricity_plan(),
        natural_gas_plan=get_default_natural_gas_plan(),
        lpg_plan=get_default_lpg_plan(),
        wood_price=get_default_wood_price(),
        petrol_price=get_default_petrol_price(),
        diesel_price=get_default_diesel_price(),
        public_charging_price=get_default_public_ev_charger_rate(),
        other_vehicle_costs=get_default_annual_other_vehicle_costs(
            household_profile.driving.vehicle_type
        ),
    )
    household_energy_use = estimate_usage_from_profile(household_profile)
    total_energy_costs = my_plan.calculate_cost(household_energy_use)
    variable_costs_with_solar = total_energy_costs[1]
    # If the other tests pass, EXPECTED_COSTS_DEFAULT are correct.
    variable_costs_no_solar = EXPECTED_COSTS_DEFAULT[1]
    total_solar_savings = variable_costs_no_solar - variable_costs_with_solar
    total_solar_generation = (
        household_energy_use.solar_generation_kwh.fixed_time_generation_kwh.sum()
    )

    day_tariff = my_plan.electricity_plan.import_rates["Day"]
    export_tariff = my_plan.electricity_plan.export_rates["Uncontrolled"]
    total_solar_revenue_if_exported = total_solar_generation * export_tariff
    total_solar_savings_if_self_consumed = total_solar_generation * day_tariff

    # Use the savings to determine the self-consumption fraction
    self_consumption_percentage = (
        100
        * (total_solar_savings - total_solar_revenue_if_exported)
        / (total_solar_savings_if_self_consumed - total_solar_revenue_if_exported)
    )

    assert total_solar_generation == approx(6779.137958)
    assert day_tariff == approx(0.242)
    assert export_tariff == approx(0.12)
    assert (
        total_solar_revenue_if_exported
        <= total_solar_savings
        <= total_solar_savings_if_self_consumed
    )
    # With the placeholder consumption profiles, the self-consumption
    # fraction comes out at only about 15%.
    assert self_consumption_percentage == approx(15.480805)
