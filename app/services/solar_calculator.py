"""
Solar Calculator Module

This module provides a function to calculate solar savings based on
input parameters (your_home, heating, hot_water, and driving). For
demonstration purposes, the function returns dummy values.
"""

from ..constants import EMISSIONS_FACTORS

ASSUMED_SELF_CONSUMPTION = 0.0


def calculate_solar_savings(profile):
    """
    Calculate the benefit of adding solar PV based on the provided answer objects.

    It is assumed that the home does not have solar PV installed yet. The benefits
    of solar depend on the energy usage profile of the household. Variations in the
    overall savings are attributed entirely to solar, i.e. the solar savings are
    calculated as
        energy_costs(alternatives, including solar) - energy_costs(current, no solar)

    :param profile

    :return: A dictionary with the calculated solar benefit metrics:
             - 'annual_kwh_generated'
             - 'annual_kg_co2e_saving'
             - 'annual_earnings_solar_export'
             - 'annual_savings_solar_self_consumption'
    """
    _ = profile

    add_solar = False
    if profile.solar is not None:
        add_solar = profile.solar.add_solar

    if add_solar:
        annual_kwh_generated = profile.solar.energy_generation(
            profile.your_home
        ).solar_generation_kwh.fixed_time_generation_kwh.sum()
        annual_kg_co2e_saving = (
            annual_kwh_generated * EMISSIONS_FACTORS["electricity_kg_co2e_per_kwh"]
        )
    else:
        annual_kwh_generated = 0
        annual_kg_co2e_saving = 0

    # Distribute generated energy between 'exported' and 'self-consumed'
    annual_savings_solar_self_consumption = (
        annual_kwh_generated * ASSUMED_SELF_CONSUMPTION * 0.25
    )
    annual_earnings_solar_export = (
        annual_kwh_generated * (1 - ASSUMED_SELF_CONSUMPTION) * 0.12
    )

    return {
        "annual_kwh_generated": annual_kwh_generated,
        "annual_kg_co2e_saving": annual_kg_co2e_saving,
        "annual_earnings_solar_export": annual_earnings_solar_export,
        "annual_savings_solar_self_consumption": annual_savings_solar_self_consumption,
    }
