"""
Tests for the hourly profile helper functions in app/models/hourly_profiles.
"""

import numpy as np
import pandas as pd
import pytest

from app.constants import HOT_WATER_POWER_INPUT_KW
from app.models.hourly_profiles.cooktop import cooktop_hourly_usage_profile
from app.models.hourly_profiles.driving import solar_friendly_ev_charging_profile
from app.models.hourly_profiles.general import flat_day_night_profiles
from app.models.hourly_profiles.heating import space_heating_profile
from app.models.hourly_profiles.hot_water import (
    daily_electricity_kwh,
    default_hot_water_electricity_usage_timeseries,
    solar_friendly_hot_water_electricity_usage_timeseries,
)


def test_cooktop_profile_length_and_sum():
    """
    Cooktop profile should have 8760 hourly values and sum to 1.0.
    """
    arr = cooktop_hourly_usage_profile()
    assert isinstance(arr, np.ndarray)
    assert arr.shape == (8760,), "Cooktop profile must have 8760 hourly values"
    assert np.isclose(
        arr.sum(), 1.0, atol=1e-6
    ), f"Sum of cooktop profile is {arr.sum()}"


def test_default_hot_water_profile_length_and_sum():
    """
    Default hot water profile should have 8760 hourly values and sum to 1.0,
    matching the daytime mask profile.
    """
    arr = default_hot_water_electricity_usage_timeseries()
    assert isinstance(arr, np.ndarray)
    assert arr.shape == (8760,), "Hot water default profile must have 8760 hours"
    assert np.isclose(arr.sum(), 1.0, atol=1e-6)
    # Should match daytime mask from general.flat_day_night_profiles
    day_profile, _ = flat_day_night_profiles()
    assert np.allclose(arr, day_profile)


def test_space_heating_profile_shape_and_sum_non_heatpump():
    """
    Space heating profile for electric heater (non-heatpump) should cover 8760 hours,
    have all non-negative values, and a positive total.
    """
    series = space_heating_profile(
        postcode="6012",
        heating_during_day="Never",
        main_heating_source="Electric heater",
        cop_calculation="constant",
    )
    assert isinstance(series, pd.Series)
    assert series.shape[0] == 8760, "Space heating profile must cover 8760 hours"
    # Profile should be non-negative and have positive total
    total = series.sum()
    assert total > 0, f"Sum of heating profile must be positive, got {total}"
    assert series.min() >= 0.0, "Heating profile contains negative values"


def test_space_heating_profile_invalid_cop_method():
    """
    Invalid COP calculation method should raise a ValueError.
    """
    with pytest.raises(ValueError):
        space_heating_profile(
            postcode="6012",
            heating_during_day="Never",
            main_heating_source="Heat pump",
            cop_calculation="invalid_method",
        )


def test_ev_charging_profile_length_and_sum():
    """
    EV charging profile should have 8760 hourly values and sum to 1.0.
    """
    arr = solar_friendly_ev_charging_profile(
        annual_kwh=365.0, charger_kw=7.0, year=2019
    )
    assert isinstance(arr, np.ndarray)
    assert arr.shape == (8760,), "EV charging profile must have 8760 hours"
    assert np.isclose(arr.sum(), 1.0, atol=1e-6), f"Sum of EV profile is {arr.sum()}"


@pytest.mark.parametrize(
    "total_kwh, source",
    [
        (1000.0, "Electric hot water cylinder"),
        (1000.0, "Hot water heat pump"),
    ],
)
def test_solar_friendly_hot_water_profile_length_and_sum(
    monkeypatch, total_kwh, source
):
    """
    Solar-friendly hot water hourly profile should have 8760 values and sum to 1.0.
    """

    # Patch hourly_ta to return a constant temperature to avoid external data
    def dummy_hourly_ta(_postcode):
        idx = pd.date_range("2000-01-01", periods=8760, freq="h")
        return pd.Series(10.0, index=idx)

    monkeypatch.setattr(
        "app.models.hourly_profiles.hot_water.hourly_ta",
        dummy_hourly_ta,
    )
    # Create daily demand series
    daily = daily_electricity_kwh(
        postcode="6012",
        heat_demand_kwh_per_year=total_kwh,
        hot_water_heating_source=source,
        cop_calculation="constant",
    )
    assert isinstance(daily, pd.Series)
    # Build hourly profile with correct heater input
    arr = solar_friendly_hot_water_electricity_usage_timeseries(
        "6012",
        total_kwh,
        HOT_WATER_POWER_INPUT_KW,
        source,
    )
    assert isinstance(arr, np.ndarray)
    assert arr.shape == (8760,), "Hot water hourly profile must have 8760 hours"
    assert np.isclose(
        arr.sum(), 1.0, atol=1e-6
    ), f"Sum of hot water profile is {arr.sum()}"
