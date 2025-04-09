"""
Solar Calculator Module

This module provides a function to calculate solar savings based on
input parameters (your_home, heating, hot_water, and driving). For
demonstration purposes, the function returns dummy values.
"""

# pylint: disable=no-member

# import logging and instantiate a logger
import logging

from app.services.helpers import get_vehicle_type
from app.services.postcode_lookups.get_energy_plans import get_energy_plan

from ...constants import EMISSIONS_FACTORS
from ...models.user_answers import HouseholdAnswers, SolarAnswers
from ...services.energy_calculator import estimate_usage_from_answers

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_solar_savings(profile):
    """
    Calculate the benefit of adding solar PV based on the provided answer objects.

    It is assumed that the home does not have solar PV installed yet. The benefits
    of solar depend on the energy usage profile of the household. Variations in the
    overall savings are attributed entirely to solar, i.e. the benefits of switching
    the heating, hot water, and cooking sources are calculated as
        energy_costs(alternatives, no solar) - energy_costs(current, no solar)
    and then the solar savings are calculated as
        energy_costs(alternatives, with solar) - energy_costs(alternatives, no solar)

    :param profile

    :return: A dictionary with the calculated solar benefit metrics:
             - 'annual_kwh_generated'
             - 'annual_kg_co2e_saving'
             - 'annual_earnings_solar_export'
             - 'annual_savings_solar_self_consumption'
    """
    if (
        profile.heating is None
        or profile.heating.alternative_main_heating_source is None
    ):
        logger.warning(
            "No heating source selected. Self-consumption may be underestimated."
        )
    if (
        profile.hot_water is None
        or profile.hot_water.alternative_hot_water_heating_source is None
    ):
        logger.warning(
            "No hot water heating source selected. "
            "Self-consumption may be underestimated."
        )
    if profile.cooktop is None or profile.cooktop.alternative_cooktop is None:
        logger.warning("No cooktop selected. Self-consumption may be underestimated.")
    if profile.driving is None or profile.driving.alternative_vehicle_type is None:
        logger.warning(
            "No vehicle type selected. Self-consumption may be underestimated."
        )

    profile_with_solar = HouseholdAnswers(
        your_home=profile.your_home,
        heating=profile.heating,
        hot_water=profile.hot_water,
        cooktop=profile.cooktop,
        driving=profile.driving,
        solar=SolarAnswers(add_solar=True),
    )
    with_solar_energy_usage_profile = estimate_usage_from_answers(
        profile_with_solar,
        use_alternatives=True,
        include_other_electricity=True,
    )

    annual_solar_kwh_generated = (
        with_solar_energy_usage_profile.solar_generation_kwh.total
    )
    annual_kg_co2e_saving = (
        annual_solar_kwh_generated * EMISSIONS_FACTORS["electricity_kg_co2e_per_kwh"]
    )

    energy_plan = get_energy_plan(
        profile.your_home.postcode, get_vehicle_type(profile, use_alternatives=True)
    )
    electricity_plan = energy_plan.electricity_plan

    solar_breakdown = electricity_plan.calculate_cost(
        with_solar_energy_usage_profile
    ).solar
    total_solar_self_consumption_savings = solar_breakdown.self_consumption_savings_nzd
    total_solar_export_earnings = solar_breakdown.export_earnings_nzd

    return {
        "annual_kwh_generated": annual_solar_kwh_generated,
        "annual_kg_co2e_saving": annual_kg_co2e_saving,
        "annual_earnings_solar_export": total_solar_export_earnings,
        "annual_savings_solar_self_consumption": total_solar_self_consumption_savings,
    }
