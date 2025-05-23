"""
Map climate zones to hourly temperature profiles.
"""

import importlib.resources as pkg_resources
import logging
import os

import pandas as pd

from ..postcode_lookups.get_climate_zone import climate_zone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# -------------------------------------------------------------------------
# Preload temperature data into memory for faster subsequent lookups.
# -------------------------------------------------------------------------


def _load_all_zone_temp_data(data_dir) -> dict[str, pd.Series]:
    """
    Load all CSV files in 'data_dir' and return a dict mapping each file's
    lowercase stem (filename without extension) -> pd.Series of hourly temperatures.
    """
    zone_data = {}
    for csv_file in data_dir.iterdir():
        if csv_file.suffix.lower() == ".csv":
            logger.warning("READING %s", csv_file)
            df = pd.read_csv(csv_file, dtype={"Hour": int, "niwaTA": float})
            df.rename(columns={"niwaTA": "TA"}, inplace=True)
            df["datetime"] = pd.date_range("2019-01-01", periods=len(df), freq="h")
            df.set_index("datetime", inplace=True)
            zone_data[csv_file.stem.lower()] = df["TA"]
    return zone_data


# Load data once at import time for both production and test modes:
_prod_data_dir = pkg_resources.files(
    "resources.supplementary_data.hourly_solar_generation_by_climate_zone"
)
_test_data_dir = pkg_resources.files(
    "resources.test_data.hourly_solar_generation_by_climate_zone"
)

_prod_mode_data = _load_all_zone_temp_data(_prod_data_dir)
_test_mode_data = _load_all_zone_temp_data(_test_data_dir)


def hourly_ta(postcode: str) -> pd.Series:
    """
    Return a Typical Meteorological Year hourly ambient temperature
    timeseries for the given climate zone. The CSV is identified by
    searching preloaded data for a filename that *contains* the `zone`
    substring (case-insensitive).

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
        Hourly ambient temperature values (one row per hour).

    Raises
    ------
    ValueError
        If no matching CSV file is found.
    """
    # Determine whether to use test data or production data
    test_mode = os.getenv("TEST_MODE", "False").lower() == "true"

    zone = climate_zone(postcode).replace(" ", "_").lower()
    data_lookup = _test_mode_data if test_mode else _prod_mode_data

    for zone_key, ta_series in data_lookup.items():
        if zone in zone_key:
            return ta_series

    raise ValueError(f"No CSV file found for climate zone containing '{zone}'.")
