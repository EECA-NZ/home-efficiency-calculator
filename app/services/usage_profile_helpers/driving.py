"""
Hot water heating profile calculation.
"""

import numpy as np

from .general import flat_day_night_profiles


def ev_charging_profile() -> np.ndarray:
    """
    Create a default electricity usage profile for electric vehicle charging.
    The resulting array is normalized so that its sum is 1.

    Returns
    -------
    np.ndarray
        A 1D array of shape (8760,), with constant non-zero values in night-time
        hours.
    Placeholder for a more realistic profile.
    """
    _, night_profile = flat_day_night_profiles()
    return night_profile
