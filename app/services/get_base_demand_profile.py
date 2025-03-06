"""
Map climate zones to hourly temperature profiles.
"""

import importlib.resources as pkg_resources

import pandas as pd

from .get_climate_zone import climate_zone


def base_demand(postcode: str) -> pd.Series:
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
        Hourly base demand kWh values (one row per hour).

    Raises
    ------
    ValueError
        If no matching CSV file is found.
    """

    # Directory containing generation CSV files:
    data_dir = pkg_resources.files(
        "data_analysis.supplementary_data.hourly_solar_generation_by_climate_zone"
    )

    zone = climate_zone(postcode).replace(" ", "_")
    zone_lower = zone.lower()

    for csv_file in data_dir.iterdir():
        if csv_file.suffix.lower() == ".csv":
            # If the zone text appears in the filename (case-insensitive)
            if zone_lower in csv_file.stem.lower():
                df = pd.read_csv(csv_file, dtype={"Hour": int, "power_model": float})
                df.rename(columns={"power_model": "base_demand"}, inplace=True)
                return df["base_demand"]

    # If we exhaust the directory without finding a match, raise an error
    raise ValueError(f"No CSV file found for climate zone containing '{zone}'.")
