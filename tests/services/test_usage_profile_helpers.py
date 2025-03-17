"""
Tests for the usage_profile_helpers module.
"""

import numpy as np
import pytest

from app.services.usage_profile_helpers import (
    day_night_flag,
    daytime_total_usage,
    ensure_8760_array,
    flat_allday_profile,
    flat_day_night_profiles,
    night_shift,
    nighttime_total_usage,
    zeros_8760,
)


def naive_night_shift(usage_profile: np.ndarray) -> np.ndarray:
    """
    Old (naive) for-loop implementation of night_shift for comparison.
    """
    shifted_profile = usage_profile.copy()

    for day in range(365):
        day_start = day * 24
        day_end = day_start + 24
        # Daytime: 7..20
        day_hours = np.arange(day_start + 7, day_start + 21)
        # Nighttime: [0..6, 21..23]
        night_hours = np.concatenate(
            [
                np.arange(day_start, day_start + 7),
                np.arange(day_start + 21, day_end),
            ]
        )
        day_usage = shifted_profile[day_hours].sum()
        shifted_profile[day_hours] = 0.0
        shifted_profile[night_hours] += day_usage / night_hours.size

    return shifted_profile


def test_night_shift_vectorized_matches_naive():
    """
    Test that the vectorized version of night_shift produces
    the same result as the old naive version within a small tolerance.
    """
    # Generate random usage
    usage_profile = np.random.rand(8760)
    # Naive approach
    result_naive = naive_night_shift(usage_profile)
    # Vectorized approach (current night_shift)
    result_vectorized = night_shift(usage_profile)
    # Ensure they match within a very small tolerance
    assert np.allclose(
        result_naive, result_vectorized, atol=1e-12
    ), "Vectorized night_shift does not match naive implementation!"


def test_flat_allday_profile():
    """
    Verify that flat_allday_profile() returns an array of shape (8760,)
    that sums to 1, and that each element is 1/8760.
    """
    profile = flat_allday_profile()
    assert profile.shape == (8760,)
    # Check the sum
    assert abs(profile.sum() - 1.0) < 1e-12, "Flat profile should sum to 1"
    # Check that each element equals 1/8760
    assert abs(profile[0] - 1 / 8760) < 1e-12, "Each element should be 1/8760"


def test_zeros_8760():
    """
    Verify that zeros_8760() returns an array of shape (8760,) containing zeros.
    """
    arr = zeros_8760()
    assert arr.shape == (8760,)
    assert np.count_nonzero(arr) == 0, "All elements must be zero"


def test_ensure_8760_array_correct_shape():
    """
    ensure_8760_array should accept an iterable/array of shape (8760,)
    and return a float64 numpy array of the same shape.
    """
    data = [float(i) for i in range(8760)]
    arr = ensure_8760_array(data)
    assert isinstance(arr, np.ndarray)
    assert arr.dtype == np.float64
    assert arr.shape == (8760,)


def test_ensure_8760_array_incorrect_shape():
    """
    ensure_8760_array should raise ValueError for arrays not of shape (8760,).
    """
    bad_data = [1.0, 2.0, 3.0]  # too short
    with pytest.raises(ValueError):
        ensure_8760_array(bad_data)


def test_day_night_flag():
    """
    day_night_flag() returns an array of shape (8760,) with 1 for daytime (07..20)
    and 0 for nighttime (21..06).
    Check a few key points across multiple days.
    """
    flags = day_night_flag()
    assert flags.shape == (8760,)

    # For day=0 (the first day), check hour=0..6 => nighttime => 0
    assert not any(flags[0:7]), "Hours 0-6 should be night => 0"
    # Check hour=7..20 => daytime => 1
    assert all(flags[7:21]), "Hours 7-20 should be day => 1"
    # Check hour=21..23 => nighttime => 0
    assert not any(flags[21:24]), "Hours 21-23 should be night => 0"

    # Spot-check day=10 (some arbitrary day)
    day10_start = 10 * 24
    # Check hour=7..20 for day 10
    assert all(flags[day10_start + 7 : day10_start + 21]), "Daytime expected => 1"
    # Check hour=0..6 for day 10
    assert not any(flags[day10_start : day10_start + 7]), "Nighttime => 0"


def test_flat_day_night_profiles():
    """
    flat_day_night_profiles() returns (day_profile, night_profile),
    each normalized so they sum to 1, and are 1 where day/night respectively, else 0.
    """
    day_profile, night_profile = flat_day_night_profiles()

    # Both arrays should be 8760
    assert day_profile.shape == (8760,)
    assert night_profile.shape == (8760,)

    # Each should sum to 1.0
    assert abs(day_profile.sum() - 1.0) < 1e-12, "Day profile must sum to 1"
    assert abs(night_profile.sum() - 1.0) < 1e-12, "Night profile must sum to 1"
    for d, n in zip(day_profile, night_profile):
        # Both can't be > 0 simultaneously
        assert not (d > 0 and n > 0)


def test_daytime_total_usage():
    """
    daytime_total_usage should zero out all nighttime hours.
    """
    # Create random usage
    usage_profile = np.random.rand(8760)
    day_profile = daytime_total_usage(usage_profile)

    # For hours 7..20 in each day, we want day_profile to match usage_profile
    # For hours 21..23 and 0..6, we want day_profile = 0
    for day in range(365):
        day_start = day * 24
        # Check daytime
        day_hours = np.arange(day_start + 7, day_start + 21)
        assert np.allclose(day_profile[day_hours], usage_profile[day_hours])
        # Check nighttime
        night_hours = np.concatenate(
            [
                np.arange(day_start, day_start + 7),
                np.arange(day_start + 21, day_start + 24),
            ]
        )
        assert not np.any(day_profile[night_hours]), "Nighttime usage should be zero"


def test_nighttime_total_usage():
    """
    nighttime_total_usage should zero out all daytime hours.
    """
    usage_profile = np.random.rand(8760)
    night_profile = nighttime_total_usage(usage_profile)

    for day in range(365):
        day_start = day * 24
        # Daytime hours 7..20
        day_hours = np.arange(day_start + 7, day_start + 21)
        assert not np.any(night_profile[day_hours]), "Daytime usage should be zero"
        # Nighttime hours
        night_hours = np.concatenate(
            [
                np.arange(day_start, day_start + 7),
                np.arange(day_start + 21, day_start + 24),
            ]
        )
        assert np.allclose(night_profile[night_hours], usage_profile[night_hours])
