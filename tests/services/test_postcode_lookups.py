"""Tests for the postcode lookup service functions."""

# pylint: disable=import-error

import os

import numpy as np
import pandas as pd
import pytest

from app.services.postcode_lookups.get_climate_zone import climate_zone
from app.services.postcode_lookups.get_solar_generation import hourly_pmax
from app.services.postcode_lookups.get_temperatures import hourly_ta


@pytest.fixture(autouse=True)
def ensure_prod_mode(monkeypatch):
    """
    Ensure TEST_MODE is False so the full supplementary data are used in lookups.
    """
    monkeypatch.setenv("TEST_MODE", "False")


def test_climate_zone_known_postcodes():
    """Test that known postcodes map to expected climate zones."""
    assert climate_zone("0110") == "Northland"
    assert climate_zone("9016") == "Dunedin"
    assert climate_zone("6012") == "Wellington"


def test_climate_zone_unknown_postcode_defaults_to_wellington():
    """Test that unknown postcodes default to the Wellington climate zone."""
    assert climate_zone("99999") == "Wellington"


@pytest.mark.skipif(
    os.environ.get("LOCAL_SOLAR_DATA", "True") != "True",
    reason="Skipping solar test because local lookup table data is unavailable.",
)
def test_hourly_pmax_returns_array_length_8760_and_positive_values():
    """Test hourly_pmax returns an array of length 8760 with non-negative values."""
    arr = hourly_pmax("0110")
    # Should be a numpy array of hourly pmax values
    assert isinstance(arr, np.ndarray)
    # Expect one value per hour in a year
    assert arr.shape[0] == 8760
    # All values should be non-negative
    assert np.all(arr >= 0)
    # Sum should be positive (some generation exists)
    assert arr.sum() > 0


@pytest.mark.skipif(
    os.environ.get("LOCAL_SOLAR_DATA", "True") != "True",
    reason="Skipping solar test because local lookup table data is unavailable.",
)
def test_hourly_pmax_unknown_postcode_defaults_to_wellington():
    """Test hourly_pmax for unknown postcodes defaults to Wellington zone mapping."""
    arr_unknown = hourly_pmax("ABCDE")
    arr_default = hourly_pmax("6012")  # 6012 maps to Wellington
    # Arrays should match exactly
    assert isinstance(arr_unknown, np.ndarray)
    assert arr_unknown.shape == arr_default.shape
    assert np.allclose(arr_unknown, arr_default)


@pytest.mark.skipif(
    os.environ.get("LOCAL_SOLAR_DATA", "True") != "True",
    reason="Skipping solar test because local lookup table data is unavailable.",
)
def test_hourly_ta_returns_series_length_8760_and_expected_value():
    """Test hourly_ta returns Series of length 8760 with correct first value."""
    ts = hourly_ta("0110")
    # Should be a pandas Series of ambient temperatures
    assert isinstance(ts, pd.Series)
    # Expect hourly values for a full year
    assert len(ts) == 8760
    # First hour value should match the CSV (Northland.csv first line: 14.8)
    assert ts.iloc[0] == pytest.approx(14.8, rel=1e-6)


@pytest.mark.skipif(
    os.environ.get("LOCAL_SOLAR_DATA", "True") != "True",
    reason="Skipping solar test because local lookup table data is unavailable.",
)
def test_hourly_ta_unknown_postcode_defaults_to_wellington():
    """Test hourly_ta for unknown postcodes defaults to Wellington zone mapping."""
    ts_unknown = hourly_ta("ABCDE")
    ts_default = hourly_ta("6012")  # 6012 maps to Wellington
    assert isinstance(ts_unknown, pd.Series)
    assert len(ts_unknown) == len(ts_default)
    # The first value (and entire series) should match
    assert ts_unknown.iloc[0] == pytest.approx(ts_default.iloc[0])
