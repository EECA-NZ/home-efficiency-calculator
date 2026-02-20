"""
Tests for the energy_costs module.
"""

# pylint: disable=no-member, too-many-locals

import os

import pytest
from pytest import approx

from app.models.energy_plans import HouseholdEnergyPlan
from app.models.user_answers import HouseholdAnswers, SolarAnswers
from app.services.configuration import (
    get_default_annual_other_vehicle_costs,
    get_default_answer_section,
    get_default_household_answers,
    get_default_plan,
    get_default_usage_profile,
)
from app.services.energy_calculator import estimate_usage_from_answers

EXPECTED_COSTS_DEFAULT = (730.5, 2855.7396, 0.0, 0.0, 0.0)


@pytest.fixture(autouse=True, scope="session")
def set_test_environment_variable():
    """
    Set the TEST_MODE environment variable to True.
    This will ensure that the test data is used, allowing
    the tests to run without the need for data files that
    are not licensed for sharing publicly.
    """
    os.environ["TEST_MODE"] = "True"


def test_calculate_annual_costs():
    """
    Test the annual cost calculation logic.
    """
    my_answers = get_default_household_answers()
    my_profile = get_default_usage_profile()
    my_plan = HouseholdEnergyPlan(
        name="Basic Household Energy Plan",
        electricity_plan=get_default_plan("electricity_plan"),
        natural_gas_plan=get_default_plan("natural_gas_plan"),
        lpg_plan=get_default_plan("lpg_plan"),
        wood_price=get_default_plan("wood_price"),
        petrol_price=get_default_plan("petrol_price"),
        diesel_price=get_default_plan("diesel_price"),
        public_charging_price=get_default_plan("public_charging_price"),
        other_vehicle_costs=get_default_annual_other_vehicle_costs(
            my_answers.driving.vehicle_type
        ),
    )
    my_costs = my_plan.calculate_cost(my_profile)
    expected = EXPECTED_COSTS_DEFAULT
    actual = (
        my_costs.fixed_cost_nzd,
        my_costs.variable_cost_nzd,
        my_costs.solar.self_consumption_savings_nzd if my_costs.solar else 0.0,
        my_costs.solar.export_earnings_nzd if my_costs.solar else 0.0,
        my_costs.solar.self_consumption_pct if my_costs.solar else 0.0,
    )
    assert actual == approx(expected, rel=1e-4)


def test_create_household_energy_profile_to_cost():
    """
    Test constructing a profile and plan, and doing a cost calculation.
    """
    my_answers = HouseholdAnswers(
        your_home=get_default_answer_section("your_home"),
        heating=get_default_answer_section("heating"),
        hot_water=get_default_answer_section("hot_water"),
        cooktop=get_default_answer_section("cooktop"),
        driving=get_default_answer_section("driving"),
        solar=get_default_answer_section("solar"),
    )
    my_plan = HouseholdEnergyPlan(
        name="Basic Household Energy Plan",
        electricity_plan=get_default_plan("electricity_plan"),
        natural_gas_plan=get_default_plan("natural_gas_plan"),
        lpg_plan=get_default_plan("lpg_plan"),
        wood_price=get_default_plan("wood_price"),
        petrol_price=get_default_plan("petrol_price"),
        diesel_price=get_default_plan("diesel_price"),
        public_charging_price=get_default_plan("public_charging_price"),
        other_vehicle_costs=get_default_annual_other_vehicle_costs(
            my_answers.driving.vehicle_type
        ),
    )
    household_energy_use = estimate_usage_from_answers(my_answers)
    total_energy_costs = my_plan.calculate_cost(household_energy_use)
    assert (
        total_energy_costs.fixed_cost_nzd + total_energy_costs.variable_cost_nzd
    ) > 0


def test_create_household_energy_profile_to_cost_with_solar():
    """
    Test constructing a profile and plan, and doing a cost calculation.
    """
    my_answers_with_solar = HouseholdAnswers(
        your_home=get_default_answer_section("your_home"),
        heating=get_default_answer_section("heating"),
        hot_water=get_default_answer_section("hot_water"),
        cooktop=get_default_answer_section("cooktop"),
        driving=get_default_answer_section("driving"),
        solar=SolarAnswers(add_solar=True),
    )
    my_plan = HouseholdEnergyPlan(
        name="Basic Household Energy Plan",
        electricity_plan=get_default_plan("electricity_plan"),
        natural_gas_plan=get_default_plan("natural_gas_plan"),
        lpg_plan=get_default_plan("lpg_plan"),
        wood_price=get_default_plan("wood_price"),
        petrol_price=get_default_plan("petrol_price"),
        diesel_price=get_default_plan("diesel_price"),
        public_charging_price=get_default_plan("public_charging_price"),
        other_vehicle_costs=get_default_annual_other_vehicle_costs(
            my_answers_with_solar.driving.vehicle_type
        ),
    )
    household_energy_use_with_solar = estimate_usage_from_answers(
        my_answers_with_solar, include_other_electricity=True, use_solar_diverter=True
    )
    result = my_plan.calculate_cost(household_energy_use_with_solar)
    solar = result.solar
    assert solar is not None

    solar_self_consumption_savings_nzd = solar.self_consumption_savings_nzd
    solar_export_earnings_nzd = solar.export_earnings_nzd
    self_consumption_percentage = solar.self_consumption_pct

    total_solar_savings_2 = (
        solar_self_consumption_savings_nzd + solar_export_earnings_nzd
    )

    total_solar_generation = household_energy_use_with_solar.solar_generation_kwh.total

    day_tariff = my_plan.electricity_plan.import_rates["Day"]
    export_tariff = my_plan.electricity_plan.export_rates["Uncontrolled"]
    total_solar_revenue_if_exported = total_solar_generation * export_tariff
    total_solar_savings_if_self_consumed = total_solar_generation * day_tariff

    assert total_solar_generation == approx(6779.145125, rel=1e-4)
    assert day_tariff == approx(0.242)
    assert export_tariff == approx(0.136)
    assert total_solar_revenue_if_exported <= total_solar_savings_2
    assert total_solar_savings_2 <= total_solar_savings_if_self_consumed
    assert self_consumption_percentage == approx(46.55, rel=1e-3)
