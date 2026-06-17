"""
Tests for the helpers module.
"""

# pylint: disable=no-member

from pytest import approx

from app.constants import (
    DAY_NIGHT_FRAC,
    DAYS_IN_YEAR,
    HPWH_CLIMATE_PROXY_SPACE_HEATING_COP_BY_CLIMATE_ZONE,
    HPWH_EXISTING_STANDING_LOSS_KWH_PER_DAY_BY_TANK_SIZE,
    HPWH_REFERENCE_CLIMATE_ZONE,
    HPWH_REFERENCE_COP,
    HPWH_STANDING_LOSS_DAYS_PER_YEAR,
    OTHER_ELX_KWH_PER_DAY,
    adjusted_hpwh_standing_loss_kwh_per_day,
    derated_hpwh_cop_from_space_heating_proxy,
)
from app.models.hourly_profiles.get_base_demand_profile import (
    other_electricity_energy_usage_profile,
)
from app.models.usage_profiles import ElectricityUsage, YearlyFuelUsageProfile
from app.models.user_answers import SolarAnswers
from app.services.configuration import get_default_plan
from app.services.helpers import add_gst, get_solar_answers
from app.services.usage_calculation.hot_water_helpers import (
    hot_water_heating_efficiency,
    other_water_kwh_per_year,
    shower_kwh_per_year,
    standing_loss_kwh_per_year,
)


def test_add_gst():
    """
    Test the add_gst function.
    """
    electricity_plan = get_default_plan("electricity_plan")
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
            1: 486.911,
            2: 486.911,
            3: 549.336,
            4: 549.336,
            5: 674.185,
            6: 674.185,
        },
        "Piped gas hot water cylinder": {
            1: 2831.232,
            2: 2831.232,
            3: 3147.479,
            4: 3147.479,
            5: 3597.966,
            6: 3597.966,
        },
        "Hot water heat pump": {
            1: 1274.6117,
            2: 1274.6117,
            3: 1425.8493,
            4: 1425.8493,
            5: 1504.2443,
            6: 1504.2443,
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


def test_hot_water_heat_pump_efficiency_uses_2026_model():
    """
    Test that the HPWH component COPs now follow the 2026 model update.
    """
    assert hot_water_heating_efficiency("Hot water heat pump", "Wellington") == approx(
        3.9269172284110274
    )
    assert hot_water_heating_efficiency(
        "Hot water heat pump", "Christchurch"
    ) == approx(3.4747554460352017)


def test_hpwh_cop_settings_match_sheet_final_values():
    """
    Test the final 2026 spreadsheet settings for the COP de-rating calculation.
    """
    reference_proxy_cop = HPWH_CLIMATE_PROXY_SPACE_HEATING_COP_BY_CLIMATE_ZONE[
        HPWH_REFERENCE_CLIMATE_ZONE
    ]

    wellington_cop = derated_hpwh_cop_from_space_heating_proxy(
        space_heating_cop=HPWH_CLIMATE_PROXY_SPACE_HEATING_COP_BY_CLIMATE_ZONE[
            "Wellington"
        ],
        reference_space_heating_cop=reference_proxy_cop,
        reference_hpwh_cop=HPWH_REFERENCE_COP,
        derating_coefficient=0.5,
    )
    christchurch_cop = derated_hpwh_cop_from_space_heating_proxy(
        space_heating_cop=HPWH_CLIMATE_PROXY_SPACE_HEATING_COP_BY_CLIMATE_ZONE[
            "Christchurch"
        ],
        reference_space_heating_cop=reference_proxy_cop,
        reference_hpwh_cop=HPWH_REFERENCE_COP,
        derating_coefficient=0.5,
    )

    assert wellington_cop == approx(3.9269172284110274)
    assert christchurch_cop == approx(3.4747554460352017)


def test_hpwh_cop_settings_match_sheet_old_values():
    """
    Test the pre-2026 spreadsheet settings using the same proxy calculation.
    """
    reference_proxy_cop = HPWH_CLIMATE_PROXY_SPACE_HEATING_COP_BY_CLIMATE_ZONE[
        HPWH_REFERENCE_CLIMATE_ZONE
    ]

    wellington_cop = derated_hpwh_cop_from_space_heating_proxy(
        space_heating_cop=HPWH_CLIMATE_PROXY_SPACE_HEATING_COP_BY_CLIMATE_ZONE[
            "Wellington"
        ],
        reference_space_heating_cop=reference_proxy_cop,
        reference_hpwh_cop=3.3333333333333335,
        derating_coefficient=1.0,
    )
    christchurch_cop = derated_hpwh_cop_from_space_heating_proxy(
        space_heating_cop=HPWH_CLIMATE_PROXY_SPACE_HEATING_COP_BY_CLIMATE_ZONE[
            "Christchurch"
        ],
        reference_space_heating_cop=reference_proxy_cop,
        reference_hpwh_cop=3.3333333333333335,
        derating_coefficient=1.0,
    )

    assert wellington_cop == approx(4.1465090064971957)
    assert christchurch_cop == approx(3.2852484686384797)


def test_hpwh_standing_loss_settings_match_sheet_final_values():
    """
    Test the final 2026 spreadsheet settings for HPWH standing loss uplift.
    """
    small_daily_loss = adjusted_hpwh_standing_loss_kwh_per_day(
        HPWH_EXISTING_STANDING_LOSS_KWH_PER_DAY_BY_TANK_SIZE[170]
    )
    large_daily_loss = adjusted_hpwh_standing_loss_kwh_per_day(
        HPWH_EXISTING_STANDING_LOSS_KWH_PER_DAY_BY_TANK_SIZE[300]
    )

    assert small_daily_loss == approx(3.4896966368039277)
    assert small_daily_loss * HPWH_STANDING_LOSS_DAYS_PER_YEAR == approx(
        1274.6116965926346
    )
    assert large_daily_loss == approx(4.118396418165106)
    assert large_daily_loss * HPWH_STANDING_LOSS_DAYS_PER_YEAR == approx(
        1504.2442917348048
    )


def test_hpwh_standing_loss_settings_match_sheet_old_values():
    """
    Test the legacy spreadsheet standing-loss settings before the outdoor uplift.
    """
    small_daily_loss = adjusted_hpwh_standing_loss_kwh_per_day(
        HPWH_EXISTING_STANDING_LOSS_KWH_PER_DAY_BY_TANK_SIZE[170],
        fittings_heat_loss_multiplier=1.0,
    )
    medium_daily_loss = adjusted_hpwh_standing_loss_kwh_per_day(
        HPWH_EXISTING_STANDING_LOSS_KWH_PER_DAY_BY_TANK_SIZE[250],
        fittings_heat_loss_multiplier=1.0,
    )

    assert small_daily_loss == approx(3.4896966368039277)
    assert small_daily_loss * HPWH_STANDING_LOSS_DAYS_PER_YEAR == approx(
        1274.6116965926346
    )
    assert medium_daily_loss == approx(3.9037626898851556)
    assert medium_daily_loss * HPWH_STANDING_LOSS_DAYS_PER_YEAR == approx(
        1425.8493224805532
    )


def test_other_electricity_energy_usage_profile_1():
    """
    Test that other_electricity_energy_usage_profile() returns
    a YearlyFuelUsageProfile with the correct
    allocation of day vs. night usage and total kWh.
    """
    profile = other_electricity_energy_usage_profile()

    # 1. Check that the returned object is the correct type
    assert isinstance(profile, YearlyFuelUsageProfile)

    # 2. Check connection days
    assert profile.elx_connection_days == DAYS_IN_YEAR

    # 3. The .electricity_kwh attribute should be an ElectricityUsage
    assert isinstance(profile.electricity_kwh, ElectricityUsage)

    # 4. The usage array should have 8760 elements
    usage_array = (
        profile.electricity_kwh.total_fixed_time_usage
        + profile.electricity_kwh.total_shift_able_usage
    )
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
    a YearlyFuelUsageProfile with the correct
    allocation of day vs. night usage and total kWh.
    """
    profile = other_electricity_energy_usage_profile()

    # 1. Check that the returned object is the correct type
    assert isinstance(profile, YearlyFuelUsageProfile)

    # 2. Check connection days
    assert profile.elx_connection_days == DAYS_IN_YEAR

    # 3. The .electricity_kwh attribute should be an ElectricityUsage
    assert isinstance(profile.electricity_kwh, ElectricityUsage)

    # 4. The usage array should have 8760 elements
    usage_array = (
        profile.electricity_kwh.total_fixed_time_usage
        + profile.electricity_kwh.total_shift_able_usage
    )
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

        solar = SolarAnswers(add_solar=True)

    dummy = DummyAnswers()
    solar_instance = get_solar_answers(dummy)
    assert solar_instance["add_solar"] is True


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
    assert solar_instance["add_solar"] is False
