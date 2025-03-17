"""
Module for generic helper functions.
"""

import numpy as np
from pydantic import BaseModel

from ..constants import HEATING_PERIOD_FACTOR


def answer_options(my_object, field):
    """
    For a given field on a pydantic model, return the possible answer options.
    """
    return type(my_object).model_fields[field].annotation.__args__


def heating_frequency_factor(heating_days_per_week):
    """
    Calculate the heating frequency factor based on the number of heating days per week.
    Assumes that heating occurs every morning and evening.
    Daytime heating is based on the response to the question
    "How often do you heat your home during the day?".

    Parameters
    ----------
    heating_days_per_week : float
        The number of days per week that heating occurs.

    Returns
    -------
    float
        The heating frequency factor.
    """
    heating_mornings = 7
    heating_evenings = 7
    return (
        HEATING_PERIOD_FACTOR["Morning (per day)"] * heating_mornings
        + HEATING_PERIOD_FACTOR["Day (per day)"] * heating_days_per_week
        + HEATING_PERIOD_FACTOR["Evening (per day)"] * heating_evenings
    )


def add_gst(plan: BaseModel) -> BaseModel:
    """
    Adjust all cost-related fields in a plan by adding 15% GST.
    Don't alter the original plan object but manipulate a copy.
    """
    gst_rate = 1.15
    plancopy = plan.model_copy()
    for field, value in plan.model_dump().items():
        # Exclude export rates from GST application
        if isinstance(value, dict) and field != "export_rates":
            # Apply GST to each value in the dictionary
            adjusted_dict = {k: v * gst_rate for k, v in value.items()}
            setattr(plancopy, field, adjusted_dict)
        elif "charge" in field or "nzd_per_" in field or field.endswith("_rate"):
            # Apply GST to flat rate fields
            setattr(plancopy, field, value * gst_rate)
    return plancopy


def round_floats_to_2_dp(dictionary):
    """
    Round all floats in a dictionary to 2 decimal places.
    Recursively rounds floats in nested dictionaries.
    """
    for key, value in dictionary.items():
        if isinstance(value, float):
            dictionary[key] = round(value, 2)
        elif isinstance(value, dict):
            round_floats_to_2_dp(value)
    return dictionary


def safe_percentage_reduction(current: float, alternative: float) -> float:
    """
    Safely calculate percentage reduction from current to alternative values.
    Handles cases where current is zero to avoid division by zero errors.
    """
    if current == 0:
        return np.nan if alternative != 0 else 0
    return 100 * (current - alternative) / current
