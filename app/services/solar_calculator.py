"""
Solar Calculator Module

This module provides a function to calculate solar savings based on
input parameters (your_home, heating, hot_water, and driving). For
demonstration purposes, the function returns dummy values.
"""

from ..constants import EMISSIONS_FACTORS


def calculate_solar_savings(your_home, heating, hot_water, driving):
    """
    Calculate the solar benefit based on the provided answer objects.

    :param your_home: Instance of YourHomeAnswers (provides people_in_house,
                      postcode, etc.)
    :param heating: Instance of HeatingAnswers (provides main_heating_source,
                    heating_during_day, insulation_quality)
    :param hot_water: Instance of HotWaterAnswers (provides hot_water_heating_source,
                      hot_water_usage)
    :param driving: Instance of DrivingAnswers (provides vehicle_type, vehicle_size,
                    km_per_week)
    :return: A dictionary with the calculated solar benefit metrics:
             - 'annual_kwh_generated'
             - 'annual_kg_co2e_saving'
             - 'annual_earnings_solar_export'
             - 'annual_savings_solar_self_consumption'
    """
    _ = (your_home, heating, hot_water, driving)
    # For demonstration, we compute dummy values.
    annual_kwh_generated = 5123.45
    annual_kg_co2e_saving = (
        annual_kwh_generated * EMISSIONS_FACTORS["electricity_kg_co2e_per_kwh"]
    )
    return {
        "annual_kwh_generated": annual_kwh_generated,
        "annual_kg_co2e_saving": annual_kg_co2e_saving,
        "annual_earnings_solar_export": 123.45,
        "annual_savings_solar_self_consumption": 678.90,
    }
