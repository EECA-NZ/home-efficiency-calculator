"""
Tests for the helpers module.
"""

from pytest import approx

from app.services.configuration import get_default_electricity_plan
from app.services.helpers import (
    add_gst,
    other_water_kwh_per_year,
    shower_kwh_per_year,
    standing_loss_kwh_per_year,
)


def test_add_gst():
    """
    Test the add_gst function.
    """
    electricity_plan = get_default_electricity_plan()
    adjusted_electricity_plan = add_gst(electricity_plan)
    assert adjusted_electricity_plan.name == electricity_plan.name
    assert (
        adjusted_electricity_plan.daily_charge == electricity_plan.daily_charge * 1.15
    )
    assert (
        adjusted_electricity_plan.nzd_per_kwh["Day"]
        == electricity_plan.nzd_per_kwh["Day"] * 1.15
    )
    assert (
        adjusted_electricity_plan.nzd_per_kwh["Night"]
        == electricity_plan.nzd_per_kwh["Night"] * 1.15
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
