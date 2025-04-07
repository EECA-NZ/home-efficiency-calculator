"""
Module for generic helper functions.
"""

import logging

import numpy as np
import pandas as pd
from pydantic import BaseModel

from ..constants import HEATING_PERIOD_FACTOR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


def load_lookup_timeseries(
    lookup_csv_path: str, row_prefix: str, hour_count: int = 8760
) -> np.ndarray:
    """
    Reads a CSV (with headers) and looks for a row where the first N columns
    (N = number of commas in row_prefix + 1) match row_prefix when joined with commas.

    Expects:
      - A column named 'annual_total_kwh'.
      - Hourly fractional columns named '0' .. '8759' (There are
        8760 of them, scaled to sum to 1000).

    Returns:
      A NumPy array of length = hour_count,
      scaled by (annual_total_kwh / 1000).
    """
    logger.warning("READING %s", lookup_csv_path)
    df = pd.read_csv(lookup_csv_path)
    if row_prefix.strip() == "":
        match_len = 0
    else:
        prefix_parts = row_prefix.split(",")
        match_len = len(prefix_parts)
    if match_len > 0:
        leading_col_names = df.columns[:match_len]
        df["_combined"] = df[leading_col_names].astype(str).agg(",".join, axis=1)
        matched_rows = df[df["_combined"] == row_prefix]
    else:
        matched_rows = df

    if len(matched_rows) == 0:
        raise ValueError(f"No rows found matching prefix: '{row_prefix}'")
    if len(matched_rows) > 1:
        raise ValueError(f"Multiple rows found matching prefix: '{row_prefix}'")

    row = matched_rows.iloc[0]

    if "annual_total_kwh" not in row:
        raise ValueError("CSV does not contain a column named 'annual_total_kwh'.")
    annual_total = float(row["annual_total_kwh"])

    frac_cols = [str(i) for i in range(hour_count)]
    if not all(col in row for col in frac_cols):
        missing = [c for c in frac_cols if c not in row]
        raise ValueError(
            f"CSV is missing expected fractional columns, e.g. {missing[:10]}"
        )
    fractions = row[frac_cols].astype(float).to_numpy()
    return (annual_total / 1000.0) * fractions


def get_solar_answers(answers) -> dict:
    """
    Retrieve the SolarAnswers instance from the given answers object.

    If the answers object contains a non-None 'solar'
    attribute, that instance is returned.
    Otherwise, a default SolarAnswers instance with
    add_solar=False is returned.

    Parameters
    ----------
    answers : Any
        An object that is expected to have a 'solar' attribute.

    Returns
    -------
    SolarAnswers
        The retrieved or default SolarAnswers instance.
    """
    # Perform a local import to avoid circular dependencies.

    if hasattr(answers, "solar") and answers.solar is not None:
        return {"add_solar": answers.solar.add_solar}
    return {"add_solar": False}


def get_vehicle_type(answers, use_alternatives=False) -> str:
    """
    Retrieve the vehicle type from the answers.

    Args:
    - answers: The user's answers.
    - use_alternatives: Whether to use the alternative vehicle type.

    Returns:
    - The vehicle type.
    """

    if hasattr(answers, "driving") and answers.driving is not None:
        if use_alternatives:
            if answers.driving.alternative_vehicle_type is not None:
                return answers.driving.alternative_vehicle_type
    return "None"


def get_other_answers(answers) -> dict:
    """
    Retrieve the OtherAnswers instance from the given answers object.

    If the answers object contains a non-None 'other'
    attribute, that instance is returned.

    Otherwise, a default OtherAnswers instance is returned.

    Parameters
    ----------
    answers : Any
        An object that is expected to have a 'other' attribute.

    Returns
    -------
    OtherAnswers
        The retrieved or default OtherAnswers instance.
    """
    if hasattr(answers, "other") and answers.other is not None:
        return {"fixed_cost_changes": answers.other.fixed_cost_changes}
    return {"fixed_cost_changes": False}
