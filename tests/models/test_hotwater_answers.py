"""
Test energy consumption profile and behaviour of the HotWaterAnswers class.
"""

from pytest import approx

from app.constants import DAYS_IN_YEAR, HOT_WATER_FLEXIBLE_KWH_FRACTION
from app.models.usage_profiles import HotWaterYearlyFuelUsageProfile
from app.models.user_answers import HotWaterAnswers
from app.services.configuration import get_default_household_answers


def test_water_heating_energy_usage():
    """
    Test the energy usage pattern for water heating.
    Example used:
        hot_water_usage='Average',
        hot_water_heating_source='Electric hot water cylinder',
        people_in_house=4
        climate_zone = 'Wellington'

    Expected values:

    """
    profile = get_default_household_answers()
    total_kwh = 2665.7668670365156  # This is 2666.15 in the spreadsheet
    flexible_kwh = total_kwh * HOT_WATER_FLEXIBLE_KWH_FRACTION
    inflexible_day_kwh = total_kwh - flexible_kwh
    hot_water_sources = {
        "Electric hot water cylinder": HotWaterYearlyFuelUsageProfile(
            elx_connection_days=DAYS_IN_YEAR,
            inflexible_day_kwh=inflexible_day_kwh,
            flexible_kwh=flexible_kwh,
            natural_gas_connection_days=0,
            natural_gas_kwh=0,
            lpg_tanks_rental_days=0,
            lpg_kwh=0,
            wood_kwh=0,
            petrol_litres=0,
            diesel_litres=0,
            public_ev_charger_kwh=0,
            thousand_km_petrol=0,
            thousand_km_diesel=0,
            thousand_km_hybrid=0,
            thousand_km_plug_in_hybrid=0,
            thousand_km_electric=0,
        ),
    }
    for hot_water_source, expected_energy_profile in hot_water_sources.items():
        hot_water = HotWaterAnswers(
            hot_water_usage=profile["hot_water"].hot_water_usage,
            hot_water_heating_source=hot_water_source,
        )
        hot_water_energy_use = hot_water.energy_usage_pattern(profile["your_home"])
        assert hot_water_energy_use == approx(expected_energy_profile)
