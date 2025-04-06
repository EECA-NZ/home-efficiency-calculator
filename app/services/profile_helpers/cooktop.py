"""
Cooktop electricity usage profile calculation.

Placeholder for when we move to the API. The lookup
table implementation bundles cooktop usage with "other"
electricity usage.
"""

import logging

import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def cooktop_hourly_usage_profile() -> np.ndarray:
    """
    Creates an 8760-long 1D numpy array representing a cooktop usage profile.
    The profile is constant between 7 and 9 AM and twice as high between 6 PM and 8 PM.

    Returns
    -------
    np.ndarray
        A 1D array of shape (8760,) with the cooktop usage profile.
    """
    profile = np.zeros(8760, dtype=float)
    hours = np.arange(8760)
    hour_of_day = hours % 24

    # Set usage for 7 AM to 9 AM
    morning_mask = (hour_of_day >= 7) & (hour_of_day < 9)
    profile[morning_mask] = 1.0

    # Set usage for 6 PM to 8 PM (twice as high)
    evening_mask = (hour_of_day >= 18) & (hour_of_day < 20)
    profile[evening_mask] = 2.0

    # Normalize the profile
    profile /= profile.sum()

    logger.info("HERE IN COOKTOP USAGE PROFILE HELPERS")

    return profile
