"""
Module containing helper functions for creating and manipulating
8760-hour electricity usage profiles in a non-leap year (365 days).
"""

from typing import Any, Tuple

import numpy as np

# Create one global zero array for re-use
_GLOBAL_ZERO_8760 = np.zeros(8760, dtype=float)
_GLOBAL_ZERO_8760.setflags(write=False)  # Make it read-only.


def flat_allday_profile() -> np.ndarray:
    """
    Create a flat electricity usage profile for all-day usage.
    The resulting array is normalized so that its sum is 1.

    Returns
    -------
    np.ndarray
        A 1D array of shape (8760,) where each element is 1/8760.
    """
    return np.ones(8760, dtype=float) / 8760


def zeros_8760():
    """
    Just return a *reference* to the same global array:
    a zero-filled NumPy array with shape (8760,).

    Returns
    -------
    np.ndarray
        A 1D array of shape (8760,) filled with zeros.
    """
    return _GLOBAL_ZERO_8760


def ensure_8760_array(value: Any) -> np.ndarray:
    """
    Converts `value` into a float64 NumPy array and checks that it has shape (8760,).

    Parameters
    ----------
    value : Any
        The object or array-like to be converted into a (8760,) NumPy array.

    Returns
    -------
    np.ndarray
        A float64 array of shape (8760,).

    Raises
    ------
    ValueError
        If the resulting array is not of shape (8760,).
    """
    if isinstance(value, np.ndarray):
        arr = value.astype(float)
    else:
        arr = np.array(value, dtype=float)

    if arr.shape != (8760,):
        raise ValueError(f"Expected array of shape (8760,), got {arr.shape} instead.")

    return arr


def day_night_flag() -> np.ndarray:
    """
    Creates a binary array of shape (8760,) where each element is 1 for daytime hours
    (07:00–21:00) and 0 for nighttime hours (21:00–07:00).

    We use the same definition as the Vector Electricity Pricing Methodology 2025: see
    https://blob-static.vector.co.nz/blob/vector/media/vector-2024/electricity-pricing-methodology-2025.pdf

    Returns
    -------
    np.ndarray
        A binary array of shape (8760,) where each element is 1 for daytime hours.
    """
    hours = np.arange(8760)
    hour_of_day = hours % 24
    return (hour_of_day >= 7) & (hour_of_day < 21)


def flat_day_night_profiles() -> Tuple[np.ndarray, np.ndarray]:
    """
    Creates two arrays (dayrate_profile, nightrate_profile), each of length 8760.
    - dayrate_profile[i] = 1 during 07:00–21:00, else 0
    - nightrate_profile[i] = 1 for 21:00–07:00, else 0
    Both arrays are then normalized so that each individually sums to 1.

    Returns
    -------
    dayrate_profile : np.ndarray
        A float array of shape (8760,), normalized so it sums to 1.

    nightrate_profile : np.ndarray
        A float array of shape (8760,), normalized so it sums to 1.
    """
    day_mask = day_night_flag()
    dayrate_profile = day_mask.astype(float)
    nightrate_profile = (~day_mask).astype(float)
    dayrate_profile /= dayrate_profile.sum()
    nightrate_profile /= nightrate_profile.sum()
    return dayrate_profile, nightrate_profile


def night_shift(usage_profile: np.ndarray) -> np.ndarray:
    """
    Given an 8760-long 1D numpy array (usage_profile),
    shifts all daytime usage (7 AM to 9 PM) into the corresponding
    nighttime hours for each day, distributing it evenly among
    the night hours. Vectorized approach (no explicit for-loop).

    Edited to put the daytime usage into the hours between
    11pm and 4am to avoid overlap with sunrise/sunset.

    Parameters
    ----------
    usage_profile : np.ndarray
        A 1D array of shape (8760,) with hourly usage values.

    Returns
    -------
    shifted_profile : np.ndarray
        A copy of the original usage profile, but with
        all day usage zeroed out and added (equally) to the
        corresponding night's usage for that same day.
    """
    # Copy so we don't mutate the original.
    shifted_profile = usage_profile.copy()

    # Reshape into 365 days x 24 hours
    profile_2d = shifted_profile.reshape(365, 24)

    # Daytime hours: 7..20
    daytime_hours = np.arange(7, 21)
    # Nighttime hours: [0..3, 23..23] => 5 hours total
    nighttime_hours = np.concatenate([np.arange(0, 4), np.arange(23, 24)])

    # Sum the daytime usage for each day
    day_sums = profile_2d[:, daytime_hours].sum(axis=1)  # shape: (365,)

    # Zero out daytime usage
    profile_2d[:, daytime_hours] = 0.0

    # Evenly distribute each day's daytime sum across that day's night hours
    profile_2d[:, nighttime_hours] += day_sums[:, None] / nighttime_hours.size

    # Flatten to return shape (8760,)
    return profile_2d.ravel()


def daytime_total_usage(usage_profile: np.ndarray) -> np.ndarray:
    """
    Given an 8760-long 1D numpy array (usage_profile),
    returns a copy of the array with all nighttime usage zeroed out.

    Parameters
    ----------
    usage_profile : np.ndarray
        A 1D array of shape (8760,) with hourly usage values.

    Returns
    -------
    daytime_profile : np.ndarray
        A copy of the original usage profile, but with all nighttime
        usage zeroed out.
    """
    day_mask = day_night_flag()
    return usage_profile * day_mask


def nighttime_total_usage(usage_profile: np.ndarray) -> np.ndarray:
    """
    Given an 8760-long 1D numpy array (usage_profile),
    returns a copy of the array with all daytime usage zeroed out.

    Parameters
    ----------
    usage_profile : np.ndarray
        A 1D array of shape (8760,) with hourly usage values.

    Returns
    -------
    nighttime_profile : np.ndarray
        A copy of the original usage profile, but with all daytime
        usage zeroed out.
    """
    day_mask = day_night_flag()
    return usage_profile * ~day_mask


day_flag = day_night_flag()
night_flag = ~day_flag
