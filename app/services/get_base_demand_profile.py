"""
Map climate zones to hourly 'other' electricity demand profiles.
"""

import importlib.resources as pkg_resources
import os

import numpy as np
import pandas as pd

from app.models.usage_profiles import (
    ElectricityUsageTimeseries,
    HouseholdOtherElectricityUsageTimeseries,
)

from ..constants import DAYS_IN_YEAR, OTHER_ELX_KWH_PER_DAY
from .get_climate_zone import climate_zone


def base_demand(postcode: str, test_mode: bool = False) -> pd.Series:
    """
    Return an hourly 'other' electricity demand timeseries.

    Here 'other' electricity demand covers household electricity
    demand for appliances/uses not covered by the home efficiency
    calculator. This includes home electronics, lighting, white
    goods (including refrigeration) and other uses.

    The CSV is identified by
    searching the directory for a filename that *contains* the `zone`
    substring (case-insensitive).

    The first matching file is read and the hourly base demand
    is returned as a pandas Series.

    Assumes that the data is from 2019.

    Parameters
    ----------
    postcode : str
        The postcode. This will be mapped to NIWA climate zone.

    Returns
    -------
    pd.Series
        Hourly base demand kWh values (one row per hour).

    Raises
    ------
    ValueError
        If no matching CSV file is found.
    """
    # Get test_mode from environment variable
    test_mode = os.getenv("TEST_MODE", "False").lower() == "true"

    # Directory containing generation CSV files:
    if test_mode:
        data_dir = pkg_resources.files(
            "resources.test_data.hourly_solar_generation_by_climate_zone"
        )
    else:
        data_dir = pkg_resources.files(
            "resources.supplementary_data.hourly_solar_generation_by_climate_zone"
        )

    zone = climate_zone(postcode).replace(" ", "_")
    zone_lower = zone.lower()

    for csv_file in data_dir.iterdir():
        if csv_file.suffix.lower() == ".csv":
            # Check if the zone text appears in the filename (case-insensitive)
            if zone_lower in csv_file.stem.lower():
                df = pd.read_csv(csv_file, dtype={"Hour": int, "power_model": float})
                df.rename(columns={"power_model": "base_demand"}, inplace=True)
                df["datetime"] = pd.date_range("2019-01-01", periods=len(df), freq="h")
                df.set_index("datetime", inplace=True)
                return df["base_demand"]

    # If no matching CSV file is found, raise an error
    raise ValueError(
        f"No CSV file found for base demand for climate zone containing '{zone}'."
    )


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
