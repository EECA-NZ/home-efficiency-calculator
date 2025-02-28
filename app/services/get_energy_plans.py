"""
Functions relating to spatial data. Map postcodes to
EDB zones and to electricity and methane plans.

Postcodes are mapped to EDB zones, which are then mapped
to electricity plans. The mapping from EDB to electricity
plan is based on a pre-computed search for a plan available
in the EDB zone and favorable to an electrified household: see
(data_analysis.electricity_plans.optimal_electricity_plans.py).

Note that this is approximate as not all addresses within a
given EDB zone are eligible for all plans. However, it
provides a good starting point for selecting an electricity
plan based on location, capturing regional variations in
pricing.

Natural gas is treated the same way, with postcodes mapped
to EDB zones, which are then mapped to natural gas plans
based on a search for a plan available in the EDB zone that
is favorable to a household that uses natural gas: see
(data_analysis.methane_plans.optimal_methane_plans.py).

For other types of household fuels, a default plan is used.

External Dependencies:
- Data files located in
  'data_analysis.postcode_lookup_tables.output' and
  'data_analysis.{plan_type}_plans.output', where {plan_type}
  is 'electricity' or 'methane'.
"""

import importlib.resources as pkg_resources
import logging

import pandas as pd

from ..constants import DAILY_DUAL_FUEL_DISCOUNT
from ..models.energy_plans import ElectricityPlan, HouseholdEnergyPlan, NaturalGasPlan
from .configuration import get_default_plans

logger = logging.getLogger(__name__)

FIXED_RATE_COLUMN = "fixed_rate"
IMPORT_RATE_PREFIX = "import_rates."
IMPORT_RATE_KEYS = ["Uncontrolled", "Controlled", "All inclusive", "Day", "Night"]


def create_import_rates_tariff_dict(row: pd.Series) -> dict:
    """
    Construct a dictionary of import_rates values from a row of the dataframe.

    NaN values are excluded from the dictionary.

    Parameters
    ----------
    row : pd.Series
        A row of the dataframe.

    Returns
    -------
    dict
        A dictionary of import_rates values.
    """
    return {
        key: row[f"{IMPORT_RATE_PREFIX}{key}"]
        for key in IMPORT_RATE_KEYS
        if pd.notna(row[f"{IMPORT_RATE_PREFIX}{key}"])
    }


# pylint: disable=too-many-locals
def plan_dictionaries(plan_type: str, plan_class):
    """
    Load and process the postcode to EDB region and EDB region to plan dictionaries.

    Parameters
    ----------
    plan_type : str
        Type of the plan ('electricity' or 'methane').
    plan_class : class
        The class of the plan to instantiate (ElectricityPlan or NaturalGasPlan).

    Returns
    -------
    tuple
        A tuple containing:
        - dict mapping postcodes to EDB regions.
        - dict mapping EDB regions to plans.
        - dict mapping postcodes to plans.
    """
    postcode_to_edb_csv_path = (
        pkg_resources.files("data_analysis.postcode_lookup_tables.output")
        / "postcode_to_edb_region.csv"
    )

    try:
        with postcode_to_edb_csv_path.open("r", encoding="utf-8") as csv_file:
            postcode_to_edb = pd.read_csv(csv_file, dtype=str)
    except FileNotFoundError as e:
        logger.error("Postcode to EDB region CSV file not found: %s", e)
        postcode_to_edb = pd.DataFrame(columns=["postcode", "edb_region"])

    try:
        selected_plans_csv_path = (
            pkg_resources.files(f"data_analysis.{plan_type}_plans.output")
            / f"selected_{plan_type}_plan_tariffs_by_edb_gst_inclusive.csv"
        )
        with selected_plans_csv_path.open("r", encoding="utf-8") as csv_file:
            edb_to_plan_tariff = pd.read_csv(csv_file, dtype=str)
    except (FileNotFoundError, ModuleNotFoundError) as e:
        logger.error("Selected %s plans CSV file not found: %s", plan_type, e)
        edb_to_plan_tariff = pd.DataFrame(
            {
                "edb_region": [],
                "name": [],
                FIXED_RATE_COLUMN: [],
                **{f"{IMPORT_RATE_PREFIX}{key}": [] for key in IMPORT_RATE_KEYS},
            }
        )

    _postcode_to_edb_dict = postcode_to_edb.set_index("postcode")[
        "edb_region"
    ].to_dict()
    postcode_to_plan_tariff = pd.merge(
        postcode_to_edb, edb_to_plan_tariff, how="inner", on="edb_region"
    )

    edb_to_plan_dict = {}
    postcode_to_plan_dict = {}

    for _, row in postcode_to_plan_tariff.iterrows():
        import_rates = create_import_rates_tariff_dict(row)
        try:
            fixed_rate = float(row[FIXED_RATE_COLUMN])
            if plan_type == "methane":
                fixed_rate -= DAILY_DUAL_FUEL_DISCOUNT

            plan = plan_class(
                name=f"{plan_type.capitalize()} PlanId {row['name']}",
                fixed_rate=fixed_rate,
                import_rates=import_rates,
            )
            edb_to_plan_dict[row["edb_region"]] = plan
            postcode_to_plan_dict[row["postcode"]] = plan
        except ValueError as e:
            logger.error("Error parsing daily charge for %s: %s", row["name"], e)
            continue

    return _postcode_to_edb_dict, edb_to_plan_dict, postcode_to_plan_dict


# Generate dictionaries for electricity and methane plans
(
    postcode_to_edb_dict,
    edb_to_electricity_plan_dict,
    postcode_to_electricity_plan_dict,
) = plan_dictionaries("electricity", ElectricityPlan)

(
    _,
    edb_to_methane_plan_dict,
    postcode_to_methane_plan_dict,
) = plan_dictionaries("methane", NaturalGasPlan)

default_plans = get_default_plans()


def postcode_to_edb_zone(postcode: str) -> str:
    """
    Return the EDB zone for the given postcode.

    Parameters
    ----------
    postcode : str
        The postcode to look up.

    Returns
    -------
    str
        The EDB zone for the given postcode.
    """
    return postcode_to_edb_dict.get(postcode, "Unknown")


def edb_zone_to_electricity_plan(edb_zone: str) -> ElectricityPlan:
    """
    Return an electricity plan available for the given EDB zone.

    Parameters
    ----------
    edb_zone : str
        The EDB zone to look up.

    Returns
    -------
    ElectricityPlan
        An electricity plan available for the given EDB zone.
        If no plan is found, a default electricity plan is returned.
    """
    return edb_to_electricity_plan_dict.get(edb_zone, default_plans["electricity_plan"])


def postcode_to_electricity_plan(postcode: str) -> ElectricityPlan:
    """
    Return an electricity plan available for the given postcode.

    Parameters
    ----------
    postcode : str
        The postcode to look up.

    Returns
    -------
    ElectricityPlan
        An electricity plan available for the given postcode.
        If no plan is found, a default electricity plan is returned.
    """
    return postcode_to_electricity_plan_dict.get(
        postcode, default_plans["electricity_plan"]
    )


def get_energy_plan(postcode: str, vehicle_type: str) -> HouseholdEnergyPlan:
    """
    Return an energy plan available for the given postcode and vehicle type.

    Parameters
    ----------
    postcode : str
        The postcode to look up.
    vehicle_type : str
        The type of vehicle ('Petrol', 'Electric', etc.).

    Returns
    -------
    HouseholdEnergyPlan
        An energy plan available for the given postcode and vehicle type.
        Where possible, the plan's electricity and natural gas plan
        components are tailored to the postcode. If no match for the
        postcode is found, a default plan is returned.
    """
    plans = get_default_plans()
    plans["other_vehicle_costs"] = plans["other_vehicle_costs"].get(
        vehicle_type, plans["other_vehicle_costs"]
    )
    plans["electricity_plan"] = postcode_to_electricity_plan_dict.get(
        postcode, plans["electricity_plan"]
    )
    plans["natural_gas_plan"] = postcode_to_methane_plan_dict.get(
        postcode, plans["natural_gas_plan"]
    )

    return HouseholdEnergyPlan(name=f"Plan for {postcode}", **plans)
