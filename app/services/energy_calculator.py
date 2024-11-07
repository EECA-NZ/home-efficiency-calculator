"""
This module provides functions to estimate a household's yearly fuel usage profile.
"""

# pylint: disable=too-many-locals

from app.constants import EMISSIONS_FACTORS
from app.models.usage_profiles import YearlyFuelUsageProfile


def emissions_kg_co2e(usage_profile: YearlyFuelUsageProfile) -> float:
    """
    Return the household's yearly CO2 emissions in kg.
    """
    # List of emissions components
    components = [
        (usage_profile.inflexible_day_kwh, "electricity_kg_co2e_per_kwh"),
        (usage_profile.flexible_kwh, "electricity_kg_co2e_per_kwh"),
        (usage_profile.natural_gas_kwh, "natural_gas_kg_co2e_per_kwh"),
        (usage_profile.lpg_kwh, "lpg_kg_co2e_per_kwh"),
        (usage_profile.wood_kwh, "wood_kg_co2e_per_kwh"),
        (usage_profile.petrol_litres, "petrol_kg_co2e_per_litre"),
        (usage_profile.diesel_litres, "diesel_kg_co2e_per_litre"),
        (usage_profile.public_ev_charger_kwh, "electricity_kg_co2e_per_kwh"),
    ]

    # Calculate emissions with a default of 0 if the emission factor is missing
    total_emissions = sum(
        usage * EMISSIONS_FACTORS.get(emissions_factor_name, 0)
        for usage, emissions_factor_name in components
    )

    return total_emissions
