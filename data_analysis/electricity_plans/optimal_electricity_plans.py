"""
This script calculates the optimal electricity plan for a household by comparing
different electricity plans against a household's yearly fuel usage profile and
produces a final lookup table mapping EDB regions to the optimal plans.
"""

import importlib.resources as pkg_resources
import logging

import pandas as pd

from app.services.helpers import add_gst
from data_analysis.plan_choice_helpers.data_loading import load_tariff_data
from data_analysis.plan_choice_helpers.electricity_plan_helpers import (
    filter_electricity_plans,
    load_electrified_household_energy_usage_profile,
)
from data_analysis.plan_choice_helpers.plan_utils import (
    calculate_optimal_plan_by_edb,
    extract_plan_details,
    show_plan,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LOCAL_TARIFF_DATA_PATH = "../supplementary_data/tariff_data/tariffDataReport_240903.csv"
OUTPUT_FILE = "output/selected_electricity_plan_tariffs_by_edb_gst_inclusive.csv"

POSTCODE_TO_EDB_CSV = (
    pkg_resources.files("data_analysis.postcode_lookup_tables.output")
    / "postcode_to_edb_region.csv"
)
EDB_REGION_SHAPEFILE = "../supplementary_data/EDB_Boundaries/EDBBoundaries.shp"

OUTPUT_COLUMNS = [
    "edb_region",
    "name",
    "fixed_rate",
    "import_rates.Uncontrolled",
    "import_rates.Controlled",
    "import_rates.All inclusive",
    "import_rates.Day",
    "import_rates.Night",
]


def main():
    """
    Main function to calculate optimal plans and generate a lookup table.
    """
    logger.info("Loading and filtering electricity plans")
    all_plans = load_tariff_data(LOCAL_TARIFF_DATA_PATH)
    filtered_df = filter_electricity_plans(all_plans)

    logger.info("Loading household profiles")
    profile = load_electrified_household_energy_usage_profile()

    logger.info("Calculating the optimal electricity plan for each EDB")
    optimal_plan_results = calculate_optimal_plan_by_edb(profile, filtered_df)

    logger.info("Generating EDB-to-electricity-plan lookup table")
    optimal_plans = []

    for edb, _, plan, _ in optimal_plan_results:
        if plan:
            plan = add_gst(plan)
            plan_details = extract_plan_details(plan)
            plan_details["edb_region"] = edb
            optimal_plans.append(plan_details)

    logger.info("Saving results to lookup table")
    lookup_table = pd.DataFrame(optimal_plans)
    lookup_table = lookup_table.drop_duplicates().reset_index(drop=True)
    lookup_table = lookup_table[OUTPUT_COLUMNS]
    lookup_table.to_csv(OUTPUT_FILE, index=False)

    logger.info("Output the optimal electricity plans")
    for edb, profile, plan, cost in optimal_plan_results:
        if plan:
            print("--------------------")
            print(f"EDB: {edb}")
            print(f"Household Profile: {profile}")
            print(f"Optimal Plan: {plan.name}")
            print(f"Total Annual Cost: {cost}\n")
            print(show_plan(int(plan.name), filtered_df, dropna=True))


if __name__ == "__main__":
    main()
