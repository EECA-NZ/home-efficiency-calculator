"""
Tests for the hot water usage profile helper functions.
"""

import numpy as np
import pandas as pd
import pytest

# Import functions and constants from the module
from app.services.usage_profile_helpers.hot_water import (
    MORNING_WINDOW_END,
    MORNING_WINDOW_START,
    carnot_cop,
    daily_electricity_kwh,
    default_hot_water_electricity_usage_timeseries,
    normalized_solar_friendly_water_heating_profile,
    solar_friendly_hot_water_electricity_usage_timeseries,
)


def dummy_hourly_ta(postcode):
    """
    Dummy hourly_ta returns a Series with constant temperature (10°C)
    """
    index = pd.date_range("2023-01-01", "2023-12-31 23:00", freq="h")
    _ = postcode  # Unused as we return a constant value
    return pd.Series(10.0, index=index, name="temperature")


@pytest.fixture(autouse=True)
def patch_hourly_ta(request, monkeypatch):
    """
    Monkeypatch hourly_ta to use our dummy implementation,
    unless the test is marked with @pytest.mark.no_dummy
    """
    if request.node.get_closest_marker("no_dummy"):
        return
    monkeypatch.setattr(
        "app.services.usage_profile_helpers.hot_water.hourly_ta", dummy_hourly_ta
    )


def test_default_usage_timeseries():
    """
    Test the default hot water electricity usage timeseries.
    """
    arr = default_hot_water_electricity_usage_timeseries()
    assert isinstance(arr, np.ndarray)
    assert arr.shape[0] == 8760
    np.testing.assert_almost_equal(arr.sum(), 1.0)


def test_carnot_cop():
    """
    Test the Carnot COP calculation.

    For T_hot = 65°C and T_cold = 10°C, compute expected COP.
    """
    expected = (65 + 273.15) / (65 - 10)
    result = carnot_cop(65, 10)
    np.testing.assert_almost_equal(result, expected, decimal=2)
    with pytest.raises(AssertionError):
        carnot_cop(65, 70)  # Should assert because T_hot is not > T_cold.


def test_daily_electricity_kwh_resistive():
    """
    Test the daily electricity demand for a resistive heater.
    """
    postcode = "dummy"
    heat_demand = 365  # kWh per year, so 1 kWh/day if equally distributed
    series = daily_electricity_kwh(
        postcode, heat_demand, "Resistive", "scaled_carnot_cop"
    )
    expected = np.full(len(series), 1.0)  # 1 kWh each day
    np.testing.assert_allclose(series.values, expected, rtol=1e-5)


def test_daily_electricity_kwh_heatpump_constant_temps():
    """
    Test the daily electricity demand for a heat pump.
    """
    postcode = "dummy"
    heat_demand = 365
    series = daily_electricity_kwh(
        postcode, heat_demand, "Heat pump", "scaled_carnot_cop"
    )
    # With the patched version of hourly_ta, the temperature
    # is constant. Thus even for a heat pump, the normalized
    # daily demand should be equally distributed.
    expected = np.full(len(series), 1.0)
    np.testing.assert_allclose(series.values, expected, rtol=1e-5)


@pytest.mark.no_dummy
def test_daily_electricity_kwh_heatpump_non_constant_temps():
    """
    Test the daily electricity demand for a heat pump.
    """
    postcode = "dummy"
    heat_demand = 365
    series = daily_electricity_kwh(
        postcode, heat_demand, "Heat pump", "scaled_carnot_cop"
    )
    # Without using the dummy_hourly_ta, the temperature is not constant.
    # The expected values are not known, but the series should be non-constant.
    assert not np.allclose(series.values, series.values[0])


def test_normalized_solar_friendly_water_heating_profile_morning_only():
    """
    Test the normalized solar-friendly water heating profile.
    """
    # Create dummy daily data for 10 days.
    dates = pd.date_range("2023-01-01", periods=10, freq="D")
    # Each day: 5 kWh demand and effective heat output of
    # 2 kW yields required_hours=2.5 (<morning window of 4 hours)
    daily_energy = pd.Series(5.0, index=dates)
    daily_output = pd.Series(2.0, index=dates)
    profile = normalized_solar_friendly_water_heating_profile(
        daily_energy, daily_output
    )
    np.testing.assert_almost_equal(profile.sum(), 1.0)
    # For each day, verify that allocation within the morning window is nonzero.
    for day in dates:
        morning_start = pd.Timestamp(
            f"{day.strftime('%Y-%m-%d')} {MORNING_WINDOW_START}"
        )
        morning_end = pd.Timestamp(f"{day.strftime('%Y-%m-%d')} {MORNING_WINDOW_END}")
        allocated = profile[morning_start:morning_end].sum()
        assert allocated > 0, f"No energy allocated for morning on {day}"


def test_solar_friendly_hot_water_electricity_usage_timeseries_resistive():
    """
    Test the solar-friendly hot water electricity usage timeseries for a resistive
    heater.
    """
    postcode = "dummy"
    heat_demand = 365  # kWh per year
    heater_input_kw = 3.0
    arr = solar_friendly_hot_water_electricity_usage_timeseries(
        postcode, heat_demand, heater_input_kw, "Resistive"
    )
    assert isinstance(arr, np.ndarray)
    assert arr.shape[0] == 8760
    np.testing.assert_almost_equal(arr.sum(), 1.0)


def test_solar_friendly_hot_water_electricity_usage_timeseries_heatpump():
    """
    Test the solar-friendly hot water electricity usage timeseries for a heat pump.
    """
    postcode = "dummy"
    heat_demand = 365
    heater_input_kw = 3.0
    arr = solar_friendly_hot_water_electricity_usage_timeseries(
        postcode, heat_demand, heater_input_kw, "Heat pump"
    )
    assert isinstance(arr, np.ndarray)
    assert arr.shape[0] == 8760
    np.testing.assert_almost_equal(arr.sum(), 1.0)
