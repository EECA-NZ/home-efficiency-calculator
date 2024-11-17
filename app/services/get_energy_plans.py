"""
Functions relating to spatial data. Map postcodes to
climate zones and EDB zones.

Postcodes are mapped to EDB zones, which are then mapped
to electricity plans. The mapping from EDB to electricity
plan is based on a search for a plan available in the EDB
zone that is favourable to an electrified household: see
(data_analysis.electricity_plans_available.optimal_electricity_plans.py).

Note that this is approximate as not all ICPs served by a
given EDB are eligible for all plans. However, it provides
a good starting point for selecting an electricity plan
based on location, capturing regional variations in pricing.

For other types of energy plans, a default plan is used.
"""

import importlib.resources as pkg_resources

import pandas as pd

from ..constants import DAILY_DUAL_FUEL_DISCOUNT
from ..models.energy_plans import ElectricityPlan, HouseholdEnergyPlan, NaturalGasPlan
from .configuration import get_default_plans

filtered_plans_stub = pd.DataFrame(
    {
        "edb_region": [],
        "name": [],
        "daily_charge": [],
        "nzd_per_kwh.Uncontrolled": [],
        "nzd_per_kwh.Controlled": [],
        "nzd_per_kwh.All inclusive": [],
        "nzd_per_kwh.Day": [],
        "nzd_per_kwh.Night": [],
    }
)

postcode_to_edb_csv_path = (
    pkg_resources.files("data_analysis.postcode_lookup_tables.output")
    / "postcode_to_edb_region.csv"
)
with postcode_to_edb_csv_path.open("r", encoding="utf-8") as csv_file:
    postcode_to_edb = pd.read_csv(csv_file, dtype=str)

try:
    selected_plans_csv_path = (
        pkg_resources.files("data_analysis.electricity_plans_available.output")
        / "selected_electricity_plan_tariffs_by_edb_gst_inclusive.csv"
    )
    with selected_plans_csv_path.open("r", encoding="utf-8") as csv_file:
        edb_to_plan_tariff = pd.read_csv(csv_file, dtype=str)
except (FileNotFoundError, ModuleNotFoundError):
    edb_to_plan_tariff = filtered_plans_stub
except Exception as e:
    print(e)
    raise e

postcode_to_edb_dict = postcode_to_edb.set_index("postcode").to_dict()["edb_region"]
postcode_to_plan_tariff = pd.merge(
    postcode_to_edb, edb_to_plan_tariff, how="inner", on="edb_region"
)

try:
    average_gas_tariff_csv_path = (
        pkg_resources.files("data_analysis.natural_gas_plans.output")
        / "average_charges_gst_inclusive.csv"
    )
    with average_gas_tariff_csv_path.open("r", encoding="utf-8") as csv_file:
        # Apply a discount to the daily charge for dual fuel households.
        # It is assumed that all households have electricity so the discount
        # is applied to the natural gas daily charge.
        average_gas_tariff = pd.read_csv(csv_file, dtype=str)
        per_natural_gas_kwh = (
            average_gas_tariff["nzd_per_kwh.Uncontrolled"].astype("float").loc[0]
        )
        daily_charge = (
            average_gas_tariff["daily_charge"].astype("float").loc[0]
            - DAILY_DUAL_FUEL_DISCOUNT
        )
        NATURAL_GAS_PLAN = NaturalGasPlan(
            name="Average Natural Gas Tariff",
            per_natural_gas_kwh=per_natural_gas_kwh,
            daily_charge=daily_charge,
        )
except (FileNotFoundError, ModuleNotFoundError) as e:
    NATURAL_GAS_PLAN = None


def create_nzd_per_kwh(row):
    """
    Construct a dictionary of nzd_per_kwh values from a row of the dataframe.

    Nan values are excluded from the dictionary.

    Parameters
    ----------
    row : pd.Series
        A row of the dataframe.

    Returns
    -------
    dict
        A dictionary of nzd_per_kwh values.
    """
    keys = ["Uncontrolled", "Controlled", "All inclusive", "Day", "Night"]
    return {
        k: row[f"nzd_per_kwh.{k}"] for k in keys if pd.notna(row[f"nzd_per_kwh.{k}"])
    }


edb_to_electricity_plan_dict = {}
postcode_to_electricity_plan_dict = {}
for idx, current_row in postcode_to_plan_tariff.iterrows():
    nzd_per_kwh = create_nzd_per_kwh(current_row)
    electricity_plan = ElectricityPlan(
        name="Electricity PlanId " + str(current_row["name"]),
        daily_charge=current_row["daily_charge"],
        nzd_per_kwh=nzd_per_kwh,
    )
    edb_to_electricity_plan_dict[current_row["edb_region"]] = electricity_plan
    postcode_to_electricity_plan_dict[current_row["postcode"]] = electricity_plan

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
    postcode : str
        The postcode to lookup.

    Returns
    -------
    HouseholdEnergyPlan
        An energy plan available for the given EDB zone.
    """
    return postcode_to_electricity_plan_dict.get(
        postcode, default_plans["electricity_plan"]
    )


def get_energy_plan(postcode: str, vehicle_type: str) -> HouseholdEnergyPlan:
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
    plans["other_vehicle_costs"] = plans["other_vehicle_costs"][vehicle_type]
    plans["electricity_plan"] = postcode_to_electricity_plan_dict.get(
        postcode, plans["electricity_plan"]
    )
    return HouseholdEnergyPlan(name=f"Plan for {postcode}", **plans)
