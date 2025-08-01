"""
Tests for the energy_calculator module.
"""

# pylint: disable=no-member

from pytest import approx

import app.services.configuration as cfg
from app.constants import DAYS_IN_YEAR
from app.models.user_answers import HouseholdAnswers, SolarAnswers
from app.services.energy_calculator import (
    emissions_kg_co2e,
    estimate_usage_from_answers,
)

household_answers = HouseholdAnswers(
    your_home=cfg.get_default_answer_section("your_home"),
    heating=cfg.get_default_answer_section("heating"),
    hot_water=cfg.get_default_answer_section("hot_water"),
    cooktop=cfg.get_default_answer_section("cooktop"),
    driving=cfg.get_default_answer_section("driving"),
    solar=cfg.get_default_answer_section("solar"),
)

household_answers_with_solar = HouseholdAnswers(
    your_home=cfg.get_default_answer_section("your_home"),
    heating=cfg.get_default_answer_section("heating"),
    hot_water=cfg.get_default_answer_section("hot_water"),
    cooktop=cfg.get_default_answer_section("cooktop"),
    driving=cfg.get_default_answer_section("driving"),
    solar=SolarAnswers(add_solar=True),
)


def test_estimate_usage_from_answers():
    """
    Test the energy usage estimation.
    """
    energy_usage = estimate_usage_from_answers(household_answers)
    assert energy_usage.elx_connection_days == DAYS_IN_YEAR
    assert energy_usage.electricity_kwh.shift_abl_kwh == approx(3618.6299, rel=1e-4)
    assert (
        energy_usage.electricity_kwh.fixed_day_kwh
        + energy_usage.electricity_kwh.fixed_ngt_kwh
        == approx(1271.1487, rel=1e-4)
    )
    assert energy_usage.solar_generation_kwh.total == approx(0.0)
    assert energy_usage.natural_gas_connection_days == approx(0.0)
    assert energy_usage.natural_gas_kwh == approx(0.0)
    assert energy_usage.lpg_tanks_rental_days == approx(0.0)
    assert energy_usage.lpg_kwh == approx(0.0)
    assert energy_usage.wood_kwh == approx(0.0)
    assert energy_usage.petrol_litres == approx(0.0)
    assert energy_usage.diesel_litres == approx(0.0)


def test_estimate_usage_from_answers_with_solar():
    """
    Test the energy usage estimation.
    """
    energy_usage = estimate_usage_from_answers(household_answers_with_solar)
    assert energy_usage.elx_connection_days == DAYS_IN_YEAR
    assert energy_usage.electricity_kwh.annual_kwh == approx(4889.778593)
    assert energy_usage.electricity_kwh.shift_abl_kwh == approx(3618.6299, rel=1e-4)
    assert (
        energy_usage.electricity_kwh.fixed_day_kwh
        + energy_usage.electricity_kwh.fixed_ngt_kwh
        == approx(1271.149, rel=1e-4)
    )
    assert energy_usage.solar_generation_kwh.total == approx(6779.137958, rel=1e-4)
    assert energy_usage.natural_gas_connection_days == approx(0.0)
    assert energy_usage.natural_gas_kwh == approx(0.0)
    assert energy_usage.lpg_tanks_rental_days == approx(0.0)
    assert energy_usage.lpg_kwh == approx(0.0)
    assert energy_usage.wood_kwh == approx(0.0)
    assert energy_usage.petrol_litres == approx(0.0)
    assert energy_usage.diesel_litres == approx(0.0)


def test_emissions_kg_co2e():
    """
    Test the emissions calculation.
    """
    energy_usage = estimate_usage_from_answers(household_answers)
    co2_emissions = emissions_kg_co2e(usage_profile=energy_usage)
    assert co2_emissions == approx(566.0142, rel=1e-4)


def test_emissions_kg_co2e_with_solar():
    """
    Test the emissions calculation.
    """
    energy_usage = estimate_usage_from_answers(household_answers_with_solar)
    co2_emissions = emissions_kg_co2e(usage_profile=energy_usage)
    assert co2_emissions == approx(-160.710126476441, rel=1e-4)
