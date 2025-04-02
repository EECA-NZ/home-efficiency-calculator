"""
Map climate zones to hourly 'other' electricity demand profiles.
"""

import importlib.resources as pkg_resources
import os

import numpy as np
import pandas as pd

from app.models.usage_profiles import ElectricityUsage, HouseholdOtherElectricityUsage

from ..constants import DAYS_IN_YEAR, OTHER_ELX_KWH_PER_DAY
from .get_climate_zone import climate_zone

# --------------------------------------------------------------------------------
# In-memory cache for base demands from CSV files. We build two dictionaries:
# one for production data, one for test data. Each dictionary's keys are the
# lowercase filename stems. We then do a substring match to find the correct zone.
# --------------------------------------------------------------------------------


def _load_all_zone_data(data_dir) -> dict[str, pd.Series]:
    """
    Load all CSV files in 'data_dir' and return a dict mapping each file's
    lowercase stem (filename without extension) -> pd.Series of hourly base demand.
    """
    zone_data = {}
    for csv_file in data_dir.iterdir():
        if csv_file.suffix.lower() == ".csv":
            df = pd.read_csv(csv_file, dtype={"Hour": int, "power_model": float})
            df.rename(columns={"power_model": "base_demand"}, inplace=True)
            df["datetime"] = pd.date_range("2019-01-01", periods=len(df), freq="h")
            df.set_index("datetime", inplace=True)
            zone_data[csv_file.stem.lower()] = df["base_demand"]
    return zone_data


# ------------------------------------------------------------------------------
# Pre-load all CSV data for production and test modes:
# ------------------------------------------------------------------------------
_prod_data_dir = pkg_resources.files(
    "resources.supplementary_data.hourly_solar_generation_by_climate_zone"
)
_test_data_dir = pkg_resources.files(
    "resources.test_data.hourly_solar_generation_by_climate_zone"
)

_prod_mode_data = _load_all_zone_data(_prod_data_dir)
_test_mode_data = _load_all_zone_data(_test_data_dir)


def base_demand(postcode: str) -> pd.Series:
    """
    Return an hourly 'other' electricity demand timeseries.

    Here 'other' electricity demand covers household electricity
    demand for appliances/uses not covered by the home efficiency
    calculator. This includes home electronics, lighting, white
    goods (including refrigeration) and other uses.

    The CSV is identified by searching the dictionary of loaded zone data
    for a filename that *contains* the `zone` substring (case-insensitive).

    Assumes that the data is from 2019. Specification of the 2019
    calendar year means that the 1st of January is a Tuesday. This
    alignment between day number (1) and day type (Tuesday) is
    relevant to demand patterns, which vary between weekdays and
    weekends.

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
    test_mode = os.getenv("TEST_MODE", "False").lower() == "true"

    zone = climate_zone(postcode).replace(" ", "_").lower()
    data_lookup = _test_mode_data if test_mode else _prod_mode_data

    # Perform partial (substring) matching on the filename keys:
    for zone_key, base_dem_series in data_lookup.items():
        if zone in zone_key:
            return base_dem_series

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

    return HouseholdOtherElectricityUsage(
        elx_connection_days=DAYS_IN_YEAR,
        electricity_kwh=ElectricityUsage(
            fixed_time_kwh=np.array(uncontrolled_fixed_kwh)
        ),
    )
