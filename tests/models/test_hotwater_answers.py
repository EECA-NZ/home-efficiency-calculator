"""
Test energy consumption profile and behaviour of the HotWaterAnswers class.
"""

# pylint: disable=no-member

from pytest import approx

from app.constants import DAYS_IN_YEAR, HOT_WATER_FLEXIBLE_KWH_FRACTION
from app.models.usage_profiles import (
    ElectricityUsageDetailed,
    HotWaterYearlyFuelUsageProfile,
)
from app.models.user_answers import HotWaterAnswers
from app.services.configuration import get_default_household_answers
from app.services.usage_profile_helpers import flat_day_night_profiles

# Energy usage is summed over profiles in the tests
# so we can use a flat daytime profile
day_profile, _ = flat_day_night_profiles()


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
    total_kwh = 2572.2628670365157
    anytime_kwh = total_kwh * HOT_WATER_FLEXIBLE_KWH_FRACTION
    fixed_kwh = total_kwh - anytime_kwh

    electricity_kwh = ElectricityUsageDetailed(
        shift_able_controllable_kwh=anytime_kwh * day_profile,
        fixed_time_controllable_kwh=fixed_kwh * day_profile,
    )

    hot_water_sources = {
        "Electric hot water cylinder": HotWaterYearlyFuelUsageProfile(
            elx_connection_days=DAYS_IN_YEAR,
            electricity_kwh=electricity_kwh,
            natural_gas_connection_days=0,
            natural_gas_kwh=0,
            lpg_tanks_rental_days=0,
            lpg_kwh=0,
            wood_kwh=0,
            petrol_litres=0,
            diesel_litres=0,
            public_ev_charger_kwh=0,
            thousand_km=0,
        ),
    }
    for hot_water_source, expected_energy_profile in hot_water_sources.items():
        hot_water = HotWaterAnswers(
            hot_water_usage=profile["hot_water"].hot_water_usage,
            hot_water_heating_source=hot_water_source,
        )
        hot_water_energy_use = hot_water.energy_usage_pattern(
            profile["your_home"], profile["solar"]
        )
        assert (
            hot_water_energy_use.elx_connection_days
            == expected_energy_profile.elx_connection_days
        )
        assert (
            hot_water_energy_use.electricity_kwh.total_fixed_time_usage.sum()
            == approx(
                expected_energy_profile.electricity_kwh.total_fixed_time_usage.sum()
            )
        )
        assert (
            hot_water_energy_use.electricity_kwh.total_shift_able_usage.sum()
            == approx(
                expected_energy_profile.electricity_kwh.total_shift_able_usage.sum()
            )
        )
        assert (
            hot_water_energy_use.natural_gas_connection_days
            == expected_energy_profile.natural_gas_connection_days
        )
        assert hot_water_energy_use.natural_gas_kwh == approx(
            expected_energy_profile.natural_gas_kwh
        )
        assert (
            hot_water_energy_use.lpg_tanks_rental_days
            == expected_energy_profile.lpg_tanks_rental_days
        )
        assert hot_water_energy_use.lpg_kwh == approx(expected_energy_profile.lpg_kwh)
        assert hot_water_energy_use.wood_kwh == approx(expected_energy_profile.wood_kwh)
        assert hot_water_energy_use.petrol_litres == approx(
            expected_energy_profile.petrol_litres
        )
        assert hot_water_energy_use.diesel_litres == approx(
            expected_energy_profile.diesel_litres
        )
        assert hot_water_energy_use.public_ev_charger_kwh == approx(
            expected_energy_profile.public_ev_charger_kwh
        )
        assert hot_water_energy_use.thousand_km == approx(
            expected_energy_profile.thousand_km
        )
