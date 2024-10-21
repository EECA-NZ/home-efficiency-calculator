"""
Functions relating to spatial data. Map postcodes to climate zones and EDB zones.
"""

import importlib.resources as pkg_resources

import pandas as pd

from data_analysis.energy_plans_available.electricity_plans_analysis import (
    get_filtered_df,
    row_to_plan,
)

from ..models.energy_plans import ElectricityPlan, HouseholdEnergyPlan
from .configuration import get_default_plans

filtered_plans_stub = pd.DataFrame(
    {"PlanId": [], "Daily charge": [], "nzd_per_kwh": []}
)

postcode_to_edb_csv_path = (
    pkg_resources.files("data_analysis.postcode_lookup_tables.output")
    / "postcode_to_edb_region.csv"
)
with postcode_to_edb_csv_path.open("r", encoding="utf-8") as csv_file:
    postcode_to_edb = pd.read_csv(csv_file, dtype=str)

selected_plans_csv_path = (
    pkg_resources.files("data_analysis.energy_plans_available.output")
    / "selected_electricity_plans.csv"
)
with selected_plans_csv_path.open("r", encoding="utf-8") as csv_file:
    edb_to_plan_id = pd.read_csv(csv_file, dtype=str)

try:
    all_plans_csv_path = (
        pkg_resources.files("data_analysis.supplementary_data.tariff_data")
        / "tariffDataReport_240903.csv"
    )
    filtered_plans = get_filtered_df(path=all_plans_csv_path)
except FileNotFoundError:
    filtered_plans = filtered_plans_stub

joined_df = pd.merge(
    postcode_to_edb, edb_to_plan_id, how="inner", left_on="edb_region", right_on="EDB"
)

joined_df["PlanId"] = joined_df["PlanId"].astype(int)
filtered_plans["PlanId"] = filtered_plans["PlanId"].astype(int)

joined_df = pd.merge(
    joined_df,
    filtered_plans,
    how="inner",
    on="PlanId",
)

joined_df["electricity_plan"] = joined_df.apply(row_to_plan, axis=1)

postcode_to_edb_dict = postcode_to_edb.set_index("postcode").to_dict()["edb_region"]
edb_to_electricity_plan_dict = joined_df.set_index("edb_region").to_dict()[
    "electricity_plan"
]
postcode_to_electricity_plan_dict = joined_df.set_index("postcode").to_dict()[
    "electricity_plan"
]

default_plans = get_default_plans()


def postcode_to_edb_zone(postcode: str) -> str:
    """
    Return the EDB zone for the given postcode.

    Parameters
    ----------
    postcode : str
        The postcode to lookup.

    Returns
    -------
    str
        The EDB zone for the given postcode.
    """
    return postcode_to_edb_dict.get(postcode, "Unknown")


def edb_zone_to_electricity_plan(edb_zone: str) -> ElectricityPlan:
    """
    Return an energy plan available for the given EDB zone.

    Parameters
    ----------
    edb_zone : str
        The EDB zone to lookup.

    Returns
    -------
    HouseholdEnergyPlan
        An energy plan available for the given EDB zone.
    """
    return edb_to_electricity_plan_dict.get(edb_zone, default_plans["electricity_plan"])


def postcode_to_electricity_plan(postcode: str) -> ElectricityPlan:
    """
    Return an energy plan available for the given EDB zone.

    Parameters
    ----------
    edb_zone : str
        The EDB zone to lookup.

    Returns
    -------
    HouseholdEnergyPlan
        An energy plan available for the given EDB zone.
    """
    return postcode_to_electricity_plan_dict.get(
        postcode, default_plans["electricity_plan"]
    )


def postcode_to_energy_plan(postcode: str) -> HouseholdEnergyPlan:
    """
    Return an energy plan available for the given postcode.

    Parameters
    ----------
    postcode : str
        The postcode to lookup.

    Returns
    -------
    HouseholdEnergyPlan
        An energy plan available for the given postcode.
    """
    plans = get_default_plans()
    plans["electricity_plan"] = postcode_to_electricity_plan_dict.get(
        postcode, plans["electricity_plan"]
    )
    return HouseholdEnergyPlan(name=f"Plan for {postcode}", **plans)
