"""
Utility functions for analysing and comparing electricity and
natural gas plans
"""

import logging
from typing import Union

import numpy as np
import pandas as pd

from app.models.energy_plans import ElectricityPlan
from data_analysis.plan_choice_helpers.constants import locations_to_edb

logger = logging.getLogger(__name__)


def map_locations_to_edb(locations_str: str) -> str:
    """
    Map a string of locations to the corresponding EDB name.

    Parameters
    ----------
    locations_str : str
        A comma-separated string of location names.

    Returns
    -------
    str
        The EDB name if a single EDB is found, otherwise "Unknown".
    """
    locations = [loc.strip() for loc in locations_str.split(",")]
    edbs_found = set()
    for loc in locations:
        edb = locations_to_edb.get(loc)
        if edb:
            edbs_found.add(edb)
    if len(edbs_found) == 1:
        return edbs_found.pop()
    if len(edbs_found) > 1:
        logger.warning(
            "Multiple EDBs found for locations %s: %s", locations, edbs_found
        )
    return "Ignore"


def show_plan(
    plan_id: Union[str, int], full_df: pd.DataFrame, dropna: bool = True
) -> Union[pd.Series, None]:
    """
    Retrieve and display the details of a plan given its PlanId.

    Parameters
    ----------
    plan_id : str or int
        The PlanId to search for.

    full_df : pd.DataFrame
        The DataFrame containing the plans.

    dropna : bool, optional
        Whether to drop NaN values from the output. Default is True.

    Returns
    -------
    pd.Series or None
        The plan details as a Series, or None if the plan is not found.
    """
    matches = full_df[full_df["PlanId"] == plan_id]
    if matches.empty:
        logger.info("PlanId %s not found.", plan_id)
        return None
    idx = matches.index[0]
    if dropna:
        return full_df.loc[idx].dropna()
    return full_df.loc[idx]


def row_to_plan(row: pd.Series) -> ElectricityPlan:
    """
    Convert a DataFrame row to an ElectricityPlan instance.

    Parameters
    ----------
    row : pd.Series
        A row from the electricity plan DataFrame.

    Returns
    -------
    ElectricityPlan
        An instantiated ElectricityPlan object.
    """
    pricing_dict = {}
    for key in [
        "Uncontrolled",
        "All inclusive",
        "Day",
        "Night",
        "Controlled",
    ]:
        if not pd.isna(row.get(key)):
            pricing_dict[key] = row[key]

    return ElectricityPlan(
        name=str(row["PlanId"]),
        daily_charge=row["Daily charge"],
        nzd_per_kwh=pricing_dict,
    )


def add_gst(plan: ElectricityPlan) -> ElectricityPlan:
    """
    Add GST (Goods and Services Tax) to the plan's charges.

    Parameters
    ----------
    plan : ElectricityPlan
        The electricity plan to which GST will be added.

    Returns
    -------
    ElectricityPlan
        The plan with GST included in the charges.
    """
    gst_multiplier = 1.15
    plan.daily_charge *= gst_multiplier
    plan.nzd_per_kwh = {k: v * gst_multiplier for k, v in plan.nzd_per_kwh.items()}
    return plan


def calculate_optimal_plan_by_edb(profile, filtered_df):
    """
    Calculate the optimal electricity plan for each EDB and household profile.
    """
    results = []
    edb_plans = filtered_df.groupby("EDB")

    for edb, plans in edb_plans:
        logger.info("Processing EDB: %s", edb)
        best_plan = None
        lowest_cost = float("inf")

        for _, plan_data in plans.iterrows():
            plan = row_to_plan(plan_data)
            fixed_cost, variable_cost = plan.calculate_cost(profile)
            total_cost = fixed_cost + variable_cost

            if total_cost < lowest_cost:
                lowest_cost = total_cost
                best_plan = plan

        results.append((edb, profile, best_plan, lowest_cost))

    return results


def extract_plan_details(plan):
    """
    Extract the name, daily charge, and tariff rates from the plan.
    """
    dump = plan.model_dump()
    plan_details = {
        "name": dump.get("name", np.nan),
        "daily_charge": dump.get("daily_charge", np.nan),
    }
    expected_rates = ["Controlled", "Uncontrolled", "All inclusive", "Day", "Night"]
    for rate in expected_rates:
        plan_details[f"nzd_per_kwh.{rate}"] = dump["nzd_per_kwh"].get(rate, np.nan)
    return plan_details
