"""
Tests for the driving module in the profile_helpers package.
"""

import numpy as np
import pandas as pd

# Import the function from your new EV charging module
# Adjust import as appropriate for your project
from app.services.profile_helpers.driving import solar_friendly_ev_charging_profile


def test_solar_friendly_ev_charging_profile_shape_and_sum():
    """
    Test that the profile for a normal scenario has the correct shape (8760)
    and sums to 1.0.
    """
    annual_kwh = 365.0
    charger_kw = 7.0
    arr = solar_friendly_ev_charging_profile(annual_kwh, charger_kw, year=2019)
    assert isinstance(arr, np.ndarray)
    assert arr.shape[0] == 8760, "Profile must cover 8760 hours in 2019."
    np.testing.assert_almost_equal(arr.sum(), 1.0, decimal=6)


def test_solar_friendly_ev_charging_profile_minimal_daily_need():
    """
    Test the scenario where daily needed charging hours are so small
    that it should all fit into the solar window on a solar-enabled day.
    For Tuesday (2019-01-01), we expect no spillover into night hours.
    """
    annual_kwh = 73.0  # ~0.2 kWh/day
    charger_kw = 7.0  # => ~0.0286 hours/day (under 2 minutes)
    arr = solar_friendly_ev_charging_profile(annual_kwh, charger_kw, year=2019)

    # Check shape & sum
    assert arr.shape[0] == 8760
    np.testing.assert_almost_equal(arr.sum(), 1.0, decimal=6)

    # Convert array back to a time-series to examine day-of-week usage
    idx = pd.date_range("2019-01-01 00:00:00", "2019-12-31 23:00:00", freq="h")
    profile = pd.Series(arr, index=idx)

    # Jan 1, 2019 was a Tuesday => solar window: 13:00–16:00 (3 hours)
    # We'll slice exactly that day
    day_slice = profile.loc["2019-01-01"]
    # Use between_time instead of partial-string slicing
    solar_period = day_slice.between_time("13:00", "15:59")
    solar_hours = solar_period.sum()

    # Now check the night window for that same day:
    night_period = day_slice.between_time("21:00", "23:59")
    night_hours = night_period.sum()

    assert solar_hours > 0, "Expected some usage in the solar window on Tuesday."
    assert night_hours == 0, "Should not need any night charging if solar is enough."


def test_solar_friendly_ev_charging_profile_spillover():
    """
    Test the scenario where daily charging needs exceed the solar window
    on a solar-enabled day (Tuesday), forcing some spillover to the night window.
    For a 3-hour solar window (13:00-15:59), but we need about 4 hours total.
    """
    # daily_hours_needed ~4 => daily_kwh = 4h * 7kW = 28 => annual = 28*365=10220
    annual_kwh = 10220.0
    charger_kw = 7.0
    arr = solar_friendly_ev_charging_profile(annual_kwh, charger_kw, year=2019)

    # Check shape & sum
    assert arr.shape[0] == 8760
    np.testing.assert_almost_equal(arr.sum(), 1.0, decimal=6)

    # Convert to time-series
    idx = pd.date_range("2019-01-01", "2019-12-31 23:00:00", freq="h")
    profile = pd.Series(arr, index=idx)

    # Jan 1, 2019 => Tuesday
    day_slice = profile.loc["2019-01-01"]
    # Solar window 13:00–15:59 is 3 hours
    solar_hours_kwh = day_slice.between_time("13:00", "15:59").sum()
    night_hours_kwh = day_slice.between_time("21:00", "23:59").sum()
    # Because we need 4 hours total, must spill over
    assert solar_hours_kwh > 0, "Expected usage in the solar window."
    assert (
        night_hours_kwh > 0
    ), "Expected spillover usage at night for large daily demand."


def test_solar_friendly_ev_charging_profile_no_solar_day():
    """
    Check a day with no solar window (Monday) to ensure all usage goes to night.
    2019-01-07 was a Monday.
    """
    annual_kwh = 2000.0
    charger_kw = 7.0
    arr = solar_friendly_ev_charging_profile(annual_kwh, charger_kw, year=2019)

    # Convert to time-series
    idx = pd.date_range("2019-01-01", "2019-12-31 23:00:00", freq="h")
    profile = pd.Series(arr, index=idx)

    # Monday of the first week in 2019: 2019-01-07
    day_slice = profile.loc["2019-01-07"]
    # There's no 13:00–16:00 solar window on Monday
    solar_hours_kwh = day_slice.between_time("13:00", "15:59").sum()
    # Night window extends 21:00 -> 09:00 the next day,
    # but we'll just look at 21:00 -> 23:59 on the same day
    # to see if there's usage there:
    night_hours_kwh = day_slice.between_time("21:00", "23:59").sum()

    # There's also overnight (which bleeds into 01-08 00:00-08:59),
    # but to confirm usage is somewhere in that block, we can do:
    next_morning = profile.loc["2019-01-08"].between_time("00:00", "08:59").sum()

    assert solar_hours_kwh == 0, "Monday has no solar window, so no usage in that slot."
    assert (
        night_hours_kwh + next_morning > 0
    ), "All required usage should appear in the night window (incl. next morning)."
