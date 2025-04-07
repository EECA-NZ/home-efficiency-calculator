"""
Functions relating to spatial data. Map postcodes to climate zones
"""

import importlib.resources as pkg_resources
import logging

import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NIWA_TO_NZBC = {
    "Northland": "1",
    # (Far North, Whangarei, Kaipara all map to 1)
    "Auckland": "1",
    # (Only Thames‑Coromandel and Auckland match (1); others not in NZBC list)
    "Hamilton": "2",
    # (All available TAs map to 2)
    "Taupo": "4",
    # (Taupo District & Ruapehu District both map to 4)
    "Bay of Plenty": "1",
    # (All available TAs map to 1)
    "Rotorua": "4",
    # (Rotorua District → 4)
    "New Plymouth": "2",
    # (New Plymouth, Stratford, South Taranaki, Whanganui all → 2)
    "East Coast": "2",
    # (Gisborne, Wairoa, Hastings, Napier & Central Hawke’s
    # Bay → 2, but Chatham Islands Territory → 3)
    "Manawatu": "3",
    # (Most TAs → 3 but Rangitikei is split between 4 and 3)
    "Wairarapa": "4",
    # (All TAs → 4)
    "Wellington": "3",
    # (Porirua & Lower Hutt give 3 but “Hutt City” is missing)
    "Nelson-Marlborough": "3",
    # (All available TAs map to 3)
    "West Coast": "4",
    # (All available TAs map to 4)
    "Christchurch": "5",
    # (All available TAs map to 5)
    "Queenstown-Lakes": "6",
    # (Queenstown-Lakes District → 6)
    "Central Otago": "6",
    # (Both TAs map to 6)
    "Dunedin": "5",
    # (Dunedin City & Clutha → 5 but Waitaki District is split between 6 and 5)
    "Invercargill": "6",
    # (All available TAs map to 6)
}

csv_path = (
    pkg_resources.files("resources.postcode_lookup_tables.output")
    / "postcode_to_climate_zone.csv"
)

logger.warning("READING %s", csv_path)
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
