"""
Functions relating to solar electricity generation. Map climate zones to
hourly generation profiles.
"""

import importlib.resources as pkg_resources
import logging
import os

import pandas as pd

from .get_climate_zone import climate_zone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------
# Preload solar generation data into memory for faster subsequent lookups.
# ------------------------------------------------------------------------


def _load_all_zone_solar_data(data_dir) -> dict[str, pd.Series]:
    """
    Load all CSV files in 'data_dir' and return a dict mapping each file's
    lowercase stem (filename without extension) -> pd.Series of hourly pmax.
    Adjust pmax values assuming a 5kW system instead of 4kW.
    """
    zone_data = {}
    for csv_file in data_dir.iterdir():
        if csv_file.suffix.lower() == ".csv":
            df = pd.read_csv(csv_file, dtype={"Hour": int, "pmax": float})
            df["pmax"] = 5 / 4 * df["pmax"]  # Adjust pmax values for a 5kW system
            zone_data[csv_file.stem.lower()] = df["pmax"]
    return zone_data


# Load data once at import time for both production and test modes:
_prod_data_dir = pkg_resources.files(
    "resources.supplementary_data.hourly_solar_generation_by_climate_zone"
)
_test_data_dir = pkg_resources.files(
    "resources.test_data.hourly_solar_generation_by_climate_zone"
)

_prod_mode_data = _load_all_zone_solar_data(_prod_data_dir)
_test_mode_data = _load_all_zone_solar_data(_test_data_dir)


def hourly_pmax(postcode: str) -> pd.Series:
    """
    Return the hourly timeseries for pmax for the given climate zone.
    The CSV is identified by searching preloaded data for a filename
    that *contains* the `zone` substring (case-insensitive).

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
        Hourly pmax values (one row per hour).

    Raises
    ------
    ValueError
        If no matching CSV file is found.
    """
    test_mode = os.getenv("TEST_MODE", "False").lower() == "true"

    zone = climate_zone(postcode).replace(" ", "_").lower()
    data_lookup = _test_mode_data if test_mode else _prod_mode_data

    for zone_key, pmax_series in data_lookup.items():
        if zone in zone_key:
            logger.info(
                "Found preloaded data for climate zone matching '%s' in key '%s'.",
                zone,
                zone_key,
            )
            return pmax_series

    raise ValueError(f"No CSV file found for climate zone containing '{zone}'.")
