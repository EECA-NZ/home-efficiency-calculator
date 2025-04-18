"""
Tests for the solar savings calculation function.
"""

import pytest

from app.services.configuration import get_default_household_answers
from app.services.solar_calculator.calculate_solar_savings import (
    calculate_solar_savings,
)


def test_calculate_solar_savings_minimal_profile():
    """
    Given a default household answers profile, calculate_solar_savings should
    return a dict with the expected keys and all values > 0.
    """
    # Use defaults for all sections so that alternative sources are set
    answers = get_default_household_answers()
    result = calculate_solar_savings(answers)

    # Expected output keys
    expected_keys = {
        "annual_kwh_generated",
        "annual_kg_co2e_saving",
        "annual_earnings_solar_export",
        "annual_savings_solar_self_consumption",
    }
    assert set(result.keys()) == expected_keys

    # Each metric should be a positive number
    for key, value in result.items():
        assert isinstance(value, (int, float)), f"{key} is not numeric"
        assert value > 0, f"{key} should be > 0, got {value}"


def test_invalid_profile_raises():
    """
    If profile is missing required your_home.postcode or similar, an error should occur.
    """

    # Construct a minimal profile missing your_home
    # Using a plain object to avoid defining an unused class
    bad = object()
    with pytest.raises(Exception):  # broad exception since type errors may vary
        calculate_solar_savings(bad)
