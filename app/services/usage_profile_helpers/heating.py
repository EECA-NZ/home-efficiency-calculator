"""
Space heating electricity usage profile calculation.
"""

import numpy as np

from .general import flat_day_night_profiles


def heating_hourly_profile() -> np.ndarray:
    """
    Create a default electricity usage profile for space heating.
    The resulting array is normalized so that its sum is 1.

    Returns
    -------
    np.ndarray
        A 1D array of shape (8760,), with constant non-zero values in
        day-time hours.
    Placeholder for a more realistic profile.
    """
    day_profile, _ = flat_day_night_profiles()
    return day_profile
