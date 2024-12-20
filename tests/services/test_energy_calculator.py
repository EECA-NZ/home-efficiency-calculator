"""
Tests for the energy_calculator module.
"""

from pytest import approx

import app.services.configuration as cfg
from app.constants import DAYS_IN_YEAR
from app.models.user_answers import HouseholdAnswers
from app.services.energy_calculator import (
    emissions_kg_co2e,
    estimate_usage_from_profile,
)

household_profile = HouseholdAnswers(
    your_home=cfg.get_default_your_home_answers(),
    heating=cfg.get_default_heating_answers(),
    hot_water=cfg.get_default_hot_water_answers(),
    cooktop=cfg.get_default_cooktop_answers(),
    driving=cfg.get_default_driving_answers(),
    solar=cfg.get_default_solar_answers(),
)


def test_estimate_usage_from_profile():
    """
    Test the energy usage estimation.
    """
    energy_usage = estimate_usage_from_profile(household_profile)
    assert energy_usage.elx_connection_days == DAYS_IN_YEAR
    assert energy_usage.flexible_kwh == approx(3618.6299, rel=1e-4)
    assert energy_usage.inflexible_day_kwh == approx(1271.1487, rel=1e-4)
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
    energy_usage = estimate_usage_from_profile(household_profile)
    co2_emissions = emissions_kg_co2e(usage_profile=energy_usage)
    assert co2_emissions == approx(566.0142, rel=1e-4)
