"""
Tests for the energy_calculator module.
"""

import app.services.configuration as cfg
from app.constants import DAYS_IN_YEAR
from app.models.user_answers import HouseholdEnergyProfileAnswers
from app.services.energy_calculator import (
    emissions_kg_co2e,
    estimate_usage_from_profile,
)

household_profile = HouseholdEnergyProfileAnswers(
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
    heating_usage = estimate_usage_from_profile(household_profile)
    assert heating_usage.elx_connection_days == DAYS_IN_YEAR
    assert heating_usage.flexible_kwh == 3600.0
    assert heating_usage.natural_gas_connection_days == 0.0
    assert heating_usage.natural_gas_kwh == 1029.810298102981
    assert heating_usage.lpg_tanks_rental_days == 0.0
    assert heating_usage.lpg_kwh == 0.0
    assert heating_usage.wood_kwh == 0.0
    assert heating_usage.petrol_litres == 4000.0
    assert heating_usage.diesel_litres == 0.0
    assert heating_usage.day_kwh == 11456.87570832


def test_emissions_kg_co2e():
    """
    Test the emissions calculation.
    """
    heating_usage = estimate_usage_from_profile(household_profile)
    co2_emissions = emissions_kg_co2e(usage_profile=heating_usage)
    assert co2_emissions == 11000.192437670721
