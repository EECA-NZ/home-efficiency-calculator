"""
Module for generic helper functions.
"""

import logging

import numpy as np
from pydantic import BaseModel

from app.models.usage_profiles import YearlyFuelUsageProfile

from ..constants import HEATING_PERIOD_FACTOR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


def get_attr_with_fallback(section, attr_name: str, use_alternative: bool = False):
    """
    Return the value of an attribute or its alternative equivalent from a section.
    """
    if section is None:
        return None
    if use_alternative:
        alt_name = f"alternative_{attr_name}"
        return getattr(section, alt_name, None)
    return getattr(section, attr_name, None)


def get_profile_or_empty(
    section, your_home, solar_aware, use_alternative: bool = False
):
    """
    Return a usage profile from the section if available and relevant;
    otherwise return an empty YearlyFuelUsageProfile.
    """
    if section is None:
        return YearlyFuelUsageProfile()

    has_alternative = any(
        hasattr(section, attr)
        for attr in [
            "alternative_main_heating_source",
            "alternative_hot_water_heating_source",
            "alternative_cooktop",
            "alternative_vehicle_type",
        ]
    )

    if not use_alternative or has_alternative:
        return section.energy_usage_pattern(your_home, solar_aware, use_alternative)

    return YearlyFuelUsageProfile()
