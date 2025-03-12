"""
Cooktop electricity usage profile calculation.

Placeholder for when we move to the API. The lookup
table implementation bundles cooktop usage with "other"
electricity usage.
"""

import numpy as np

from .general import flat_day_night_profiles


def cooktop_hourly_usage_profile() -> np.ndarray:
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
    day_profile, _ = flat_day_night_profiles()
    return day_profile
