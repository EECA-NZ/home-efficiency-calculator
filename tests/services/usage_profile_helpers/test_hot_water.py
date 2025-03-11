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
    daily_heat_output_kw,
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
def patch_hourly_ta(monkeypatch):
    """
    Monkeypatch hourly_ta to use our dummy implementation
    """
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
    series = daily_electricity_kwh(postcode, heat_demand, "Resistive")
    expected = np.full(len(series), 1.0)  # 1 kWh each day
    np.testing.assert_allclose(series.values, expected, rtol=1e-5)


def test_daily_electricity_kwh_heatpump():
    """
    Test the daily electricity demand for a heat pump.
    """
    postcode = "dummy"
    heat_demand = 365
    series = daily_electricity_kwh(postcode, heat_demand, "Heat pump")
    # Even for a heat pump, the normalized daily demand should be equally distributed.
    expected = np.full(len(series), 1.0)
    np.testing.assert_allclose(series.values, expected, rtol=1e-5)


def test_daily_heat_output_kw_resistive():
    """
    Test the daily heat output for a resistive heater.
    """
    postcode = "dummy"
    heater_input_kw = 3.0
    series = daily_heat_output_kw(postcode, heater_input_kw, "Resistive")
    expected = np.full(len(series), 3.0)
    np.testing.assert_allclose(series.values, expected, rtol=1e-5)


def test_daily_heat_output_kw_heatpump():
    """
    Test the daily heat output for a heat pump.
    """
    postcode = "dummy"
    heater_input_kw = 3.0
    # Calculate expected output using the dummy temperature (10°C)
    cop = carnot_cop(65, 10)
    realistic_cop = cop * 0.4
    expected_output = 3.0 * realistic_cop
    series = daily_heat_output_kw(postcode, heater_input_kw, "Heat pump")
    expected = np.full(len(series), expected_output)
    np.testing.assert_allclose(series.values, expected, rtol=1e-5)


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
