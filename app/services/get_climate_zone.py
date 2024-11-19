"""
Functions relating to spatial data. Map postcodes to climate zones
"""

import importlib.resources as pkg_resources

import pandas as pd

csv_path = (
    pkg_resources.files("data_analysis.postcode_lookup_tables.output")
    / "postcode_to_climate_zone.csv"
)

with csv_path.open("r", encoding="utf-8") as csv_file:
    postcode_dict = (
        pd.read_csv(csv_file, dtype=str).set_index("postcode").to_dict()["climate_zone"]
    )


def climate_zone(postcode: str) -> str:
    """
    Return the climate zone for the given postcode.

    Parameters
    ----------
    postcode : str
        The postcode to lookup.

    Returns
    -------
    str
        The climate zone for the given postcode.
        If the postcode is not found, return "Wellington".
    """
    return postcode_dict.get(postcode, "Wellington")
