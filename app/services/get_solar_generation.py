"""
Functions relating to solar electricity generation. Map climate zones to
hourly generation profiles.
"""

import importlib.resources as pkg_resources

import pandas as pd


def hourly_pmax(zone: str) -> pd.Series:
    """
    Return the hourly timeseries for pmax for the given climate zone.
    The CSV is identified by searching the directory for a filename
    that *contains* the `zone` substring (case-insensitive).

    Parameters
    ----------
    zone : str
        The climate zone name (e.g. 'Wellington' or 'Christchurch').

    Returns
    -------
    pd.Series
        Hourly pmax values (one row per hour).

    Raises
    ------
    ValueError
        If no matching CSV file is found.
    """

    # Directory containing your CSV files:
    data_dir = pkg_resources.files(
        "data_analysis.supplementary_data.hourly_solar_generation_by_climate_zone"
    )

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
