"""
Tests for the helpers module.
"""

# pylint: disable=no-member

from pytest import approx

from app.constants import DAY_NIGHT_FRAC, DAYS_IN_YEAR, OTHER_ELX_KWH_PER_DAY
from app.models.usage_profiles import (
    ElectricityUsageTimeseries,
    HouseholdOtherElectricityUsageTimeseries,
)
from app.models.user_answers import SolarAnswers
from app.services.configuration import get_default_electricity_plan
from app.services.get_base_demand_profile import other_electricity_energy_usage_profile
from app.services.helpers import add_gst
from app.services.hot_water_helpers import (
    other_water_kwh_per_year,
    shower_kwh_per_year,
    standing_loss_kwh_per_year,
)
from app.services.solar_helpers import get_solar_answers


def test_add_gst():
    """
    Test the add_gst function.
    """
    electricity_plan = get_default_electricity_plan()
    adjusted_electricity_plan = add_gst(electricity_plan)
    assert adjusted_electricity_plan.name == electricity_plan.name
    assert adjusted_electricity_plan.fixed_rate == electricity_plan.fixed_rate * 1.15
    assert (
        adjusted_electricity_plan.import_rates["Day"]
        == electricity_plan.import_rates["Day"] * 1.15
    )
    assert (
        adjusted_electricity_plan.import_rates["Night"]
        == electricity_plan.import_rates["Night"] * 1.15
    )
    assert (
        adjusted_electricity_plan.export_rates["Uncontrolled"]
        == electricity_plan.export_rates["Uncontrolled"]
    )


def test_shower_kwh_per_year():
    """
    Test the shower_kwh_per_year hot water energy use function.
    """
    climate_zone = "Wellington"
    usage_to_size_to_annual_kwh = {
        "Low": {1: 183, 2: 366, 3: 550, 4: 733, 5: 916, 6: 1099},
        "Average": {1: 431, 2: 862, 3: 1293, 4: 1723, 5: 2154, 6: 2585},
        "High": {1: 831, 2: 1662, 3: 2493, 4: 3324, 5: 4155, 6: 4986},
    }
    for hot_water_usage, size_to_annual_kwh in usage_to_size_to_annual_kwh.items():
        for household_size, expected_kwh in size_to_annual_kwh.items():
            shower_kwh = shower_kwh_per_year(
                hot_water_usage, climate_zone, household_size
            )
            assert shower_kwh == approx(expected_kwh, rel=1e-1)


def test_other_water_kwh_per_year():
    """
    Test the other_water_kwh_per_year hot water energy use function.
    """
    climate_zone = "Wellington"
    household_size_to_annual_kwh = {
        1: 244,
        2: 487,
        3: 731,
        4: 974,
        5: 1218,
        6: 1461,
    }
    for household_size, expected_kwh in household_size_to_annual_kwh.items():
        other_water_kwh = other_water_kwh_per_year(climate_zone, household_size)
        assert other_water_kwh == approx(expected_kwh, rel=1e-1)


def test_standing_loss_kwh_per_year():
    """
    Test the standing_loss_kwh_per_year hot water energy use function.
    """
    climate_zone = "Wellington"
    tech_to_size_to_annual_kwh = {
        "Electric hot water cylinder": {
            1: approx(486.911),
            2: approx(486.911),
            3: approx(549.336),
            4: approx(549.336),
            5: approx(674.185),
            6: approx(674.185),
        },
        "Piped gas hot water cylinder": {
            1: approx(2831.232),
            2: approx(2831.232),
            3: approx(3147.479),
            4: approx(3147.479),
            5: approx(3597.966),
            6: approx(3597.966),
        },
        "Hot water heat pump": {
            1: approx(1273.8762),
            2: approx(1273.8762),
            3: approx(1425.0153),
            4: approx(1425.0153),
            5: approx(1503.359),
            6: approx(1503.359),
        },
    }
    for (
        hot_water_heating_source,
        size_to_annual_kwh,
    ) in tech_to_size_to_annual_kwh.items():
        for household_size, expected_kwh in size_to_annual_kwh.items():
            standing_loss_kwh = standing_loss_kwh_per_year(
                hot_water_heating_source, household_size, climate_zone
            )
            assert standing_loss_kwh == approx(expected_kwh, abs=10)


def test_other_electricity_energy_usage_profile_1():
    """
    Test that other_electricity_energy_usage_profile() returns
    a HouseholdOtherElectricityUsageTimeseries with the correct
    allocation of day vs. night usage and total kWh.
    """
    profile = other_electricity_energy_usage_profile()

    # 1. Check that the returned object is the correct type
    assert isinstance(profile, HouseholdOtherElectricityUsageTimeseries)

    # 2. Check connection days
    assert profile.elx_connection_days == DAYS_IN_YEAR

    # 3. The .electricity_kwh attribute should be an ElectricityUsageTimeseries
    assert isinstance(profile.electricity_kwh, ElectricityUsageTimeseries)

    # 4. The usage array should have 8760 elements
    usage_array = profile.electricity_kwh.fixed_time_uncontrolled_kwh
    assert usage_array.shape == (8760,)

    # 5. Calculate the expected total annual usage
    #    (sum of day portion + night portion) * 365
    day_daily_sum = (
        OTHER_ELX_KWH_PER_DAY["Refrigeration"]["kWh/day"]
        * DAY_NIGHT_FRAC["Refrigeration"]["Day"]
        + OTHER_ELX_KWH_PER_DAY["Lighting"]["kWh/day"]
        * DAY_NIGHT_FRAC["Lighting"]["Day"]
        + OTHER_ELX_KWH_PER_DAY["Laundry"]["kWh/day"] * DAY_NIGHT_FRAC["Laundry"]["Day"]
        + OTHER_ELX_KWH_PER_DAY["Other"]["kWh/day"] * DAY_NIGHT_FRAC["Other"]["Day"]
    )
    night_daily_sum = (
        OTHER_ELX_KWH_PER_DAY["Refrigeration"]["kWh/day"]
        * DAY_NIGHT_FRAC["Refrigeration"]["Night"]
        + OTHER_ELX_KWH_PER_DAY["Lighting"]["kWh/day"]
        * DAY_NIGHT_FRAC["Lighting"]["Night"]
        + OTHER_ELX_KWH_PER_DAY["Laundry"]["kWh/day"]
        * DAY_NIGHT_FRAC["Laundry"]["Night"]
        + OTHER_ELX_KWH_PER_DAY["Other"]["kWh/day"] * DAY_NIGHT_FRAC["Other"]["Night"]
    )
    expected_annual_kwh = (day_daily_sum + night_daily_sum) * DAYS_IN_YEAR

    # 6. Compare to the actual sum from the returned profile
    actual_annual_kwh = usage_array.sum()
    assert actual_annual_kwh == approx(
        expected_annual_kwh, rel=1e-5
    ), f"Expected ~{expected_annual_kwh:.2f} kWh, got {actual_annual_kwh:.2f} kWh"


def test_other_electricity_energy_usage_profile_2():
    """
    Test that other_electricity_energy_usage_profile() returns
    a HouseholdOtherElectricityUsageTimeseries with the correct
    allocation of day vs. night usage and total kWh.
    """
    profile = other_electricity_energy_usage_profile()

    # 1. Check that the returned object is the correct type
    assert isinstance(profile, HouseholdOtherElectricityUsageTimeseries)

    # 2. Check connection days
    assert profile.elx_connection_days == DAYS_IN_YEAR

    # 3. The .electricity_kwh attribute should be an ElectricityUsageTimeseries
    assert isinstance(profile.electricity_kwh, ElectricityUsageTimeseries)

    # 4. The usage array should have 8760 elements
    usage_array = profile.electricity_kwh.fixed_time_uncontrolled_kwh
    assert usage_array.shape == (8760,)

    # 5. Calculate the expected total annual usage
    #    (sum of day portion + night portion) * 365
    day_daily_sum = (
        OTHER_ELX_KWH_PER_DAY["Refrigeration"]["kWh/day"]
        * DAY_NIGHT_FRAC["Refrigeration"]["Day"]
        + OTHER_ELX_KWH_PER_DAY["Lighting"]["kWh/day"]
        * DAY_NIGHT_FRAC["Lighting"]["Day"]
        + OTHER_ELX_KWH_PER_DAY["Laundry"]["kWh/day"] * DAY_NIGHT_FRAC["Laundry"]["Day"]
        + OTHER_ELX_KWH_PER_DAY["Other"]["kWh/day"] * DAY_NIGHT_FRAC["Other"]["Day"]
    )
    night_daily_sum = (
        OTHER_ELX_KWH_PER_DAY["Refrigeration"]["kWh/day"]
        * DAY_NIGHT_FRAC["Refrigeration"]["Night"]
        + OTHER_ELX_KWH_PER_DAY["Lighting"]["kWh/day"]
        * DAY_NIGHT_FRAC["Lighting"]["Night"]
        + OTHER_ELX_KWH_PER_DAY["Laundry"]["kWh/day"]
        * DAY_NIGHT_FRAC["Laundry"]["Night"]
        + OTHER_ELX_KWH_PER_DAY["Other"]["kWh/day"] * DAY_NIGHT_FRAC["Other"]["Night"]
    )
    expected_annual_kwh = (day_daily_sum + night_daily_sum) * DAYS_IN_YEAR

    # 6. Compare to the actual sum from the returned profile
    actual_annual_kwh = usage_array.sum()
    assert actual_annual_kwh == approx(
        expected_annual_kwh, rel=1e-5
    ), f"Expected ~{expected_annual_kwh:.2f} kWh, got {actual_annual_kwh:.2f} kWh"


def test_get_solar_answers_with_value():
    """
    Test get_solar_answers with a value.
    """

    # pylint: disable=too-few-public-methods
    class DummyAnswers:
        """
        Dummy class to test get_solar_answers.
        """

        solar = SolarAnswers(has_solar=True)

    dummy = DummyAnswers()
    solar_instance = get_solar_answers(dummy)
    assert solar_instance.has_solar is True


def test_get_solar_answers_without_value():
    """
    Test get_solar_answers with no value.
    """

    # pylint: disable=too-few-public-methods
    class DummyAnswers:
        """
        Dummy class to test get_solar_answers.
        """

        solar = None

    dummy = DummyAnswers()
    solar_instance = get_solar_answers(dummy)
    assert solar_instance.has_solar is False
