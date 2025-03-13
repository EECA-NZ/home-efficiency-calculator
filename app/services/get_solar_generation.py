"""
Functions relating to solar electricity generation. Map climate zones to
hourly generation profiles.
"""

import importlib.resources as pkg_resources
import os

import pandas as pd

from .get_climate_zone import climate_zone


def hourly_pmax(postcode: str, test_mode: bool = False) -> pd.Series:
    """
    Return the hourly timeseries for pmax for the given climate zone.
    The CSV is identified by searching the directory for a filename
    that *contains* the `zone` substring (case-insensitive).

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
            # If the zone text appears in the filename (case-insensitive)
            if zone_lower in csv_file.stem.lower():
                df = pd.read_csv(csv_file, dtype={"Hour": int, "pmax": float})
                # Adjust pmax values: assume a 5kW system instead of 4kW
                df["pmax"] = 5 / 4 * df["pmax"]
                return df["pmax"]

    # If we exhaust the directory without finding a match, raise an error
    raise ValueError(f"No CSV file found for climate zone containing '{zone}'.")
