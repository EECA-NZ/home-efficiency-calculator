"""
Module for generic helper functions.
"""

import importlib.resources as pkg_resources

import numpy as np
import pandas as pd
from pydantic import BaseModel

from app.models.usage_profiles import (
    ElectricityUsageTimeseries,
    HouseholdOtherElectricityUsageTimeseries,
)

from ..constants import DAYS_IN_YEAR, HEATING_PERIOD_FACTOR, OTHER_ELX_KWH_PER_DAY


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


def other_electricity_energy_usage_profile():
    """
    Create an electricity usage profile for appliances not considered by the app.
    This is used for determining the percentage of solar-generated electricity
    that is consumed by the household.
    """
    total_annual_kwh = DAYS_IN_YEAR * (
        OTHER_ELX_KWH_PER_DAY["Refrigeration"]["kWh/day"]
        + OTHER_ELX_KWH_PER_DAY["Lighting"]["kWh/day"]
        + OTHER_ELX_KWH_PER_DAY["Laundry"]["kWh/day"]
        + OTHER_ELX_KWH_PER_DAY["Other"]["kWh/day"]
    )
    other_electricity_energy_usage_csv = (
        pkg_resources.files("resources.power_demand_by_time_of_use_data.output")
        / "it_light_other_white_tou_8760.csv"
    )
    with other_electricity_energy_usage_csv.open("r", encoding="utf-8") as csv_file:
        other_electricity_usage_df = pd.read_csv(csv_file, dtype=str)
    value_col = "Power IT Light Other White"
    uncontrolled_fixed_kwh = other_electricity_usage_df[value_col].astype(float)
    uncontrolled_fixed_kwh *= total_annual_kwh / uncontrolled_fixed_kwh.sum()
    return HouseholdOtherElectricityUsageTimeseries(
        elx_connection_days=DAYS_IN_YEAR,
        electricity_kwh=ElectricityUsageTimeseries(
            fixed_time_uncontrolled_kwh=np.array(uncontrolled_fixed_kwh)
        ),
    )
