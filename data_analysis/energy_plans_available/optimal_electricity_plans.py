"""
This script calculates the optimal electricity plan for a household by comparing
different electricity plans against a household's yearly fuel usage profile. The
household's profile is generated based on day and night electricity usage data.
"""

import logging
import os

import pandas as pd

from app.constants import DAYS_IN_YEAR
from app.models.energy_plans import ElectricityPlan
from app.models.usage_profiles import YearlyFuelUsageProfile
from data_analysis.energy_plans_available.electricity_plans_analysis import (
    get_filtered_df,
    show_plan,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_household_profiles(usage_csv_file, elx_connection_days):
    """
    Load household profiles from the day/night electricity usage CSV file.

    Args:
    usage_csv_file: str, path to the day/night usage CSV file
    elx_connection_days: float, number of days with an electricity connection

    Returns:
    List of YearlyFuelUsageProfile objects
    """
    df = pd.read_csv(usage_csv_file)
    day_kwh = df[df["Period"] == "Day"]["kWh"].values[0]
    flexible_kwh = df[df["Period"] == "Night"]["kWh"].values[0]

    profiles = [
        YearlyFuelUsageProfile(
            elx_connection_days=elx_connection_days,
            day_kwh=day_kwh * elx_connection_days,
            flexible_kwh=flexible_kwh * elx_connection_days,
            natural_gas_connection_days=0,
            natural_gas_kwh=0,
            lpg_tanks_rental_days=0,
            lpg_kwh=0,
            wood_kwh=0,
            petrol_litres=0,
            diesel_litres=0,
        )
    ]
    return profiles


def calculate_optimal_plan_by_edb(profiles, filtered_df):
    """
    Calculate the optimal electricity plan for each EDB and household profile.

    Args:
    profiles: List of YearlyFuelUsageProfile objects
    filtered_df: pd.DataFrame, filtered electricity plans

    Returns:
    List of tuples containing EDB, profile, and the optimal plan
    """
    results = []

    # Group plans by EDB
    grouped = filtered_df.groupby("EDB")

    # Iterate over each EDB
    for edb, group in grouped:
        logger.info("Processing EDB: %s", edb)

        for profile in profiles:
            best_plan = None
            lowest_cost = float("inf")

            # Iterate over the plans in the group (EDB)
            for _, plan_data in group.iterrows():
                plan = ElectricityPlan(
                    name=str(plan_data["PlanId"]),
                    nzd_per_day_kwh=plan_data["Day"],
                    nzd_per_night_kwh=plan_data["Night"],
                    nzd_per_controlled_kwh=plan_data["Controlled"],
                    daily_charge=plan_data["Daily charge"],
                )

                # Calculate the cost of the plan for the household profile
                fixed_cost, variable_cost = plan.calculate_cost(profile)
                total_cost = fixed_cost + variable_cost

                # Find the cheapest plan
                if total_cost < lowest_cost:
                    lowest_cost = total_cost
                    best_plan = plan

            results.append((edb, profile, best_plan, lowest_cost))

    return results


def save_results_to_csv(results, output_file):
    """
    Save the optimal electricity plans to a CSV file.

    Args:
    results: List of tuples containing EDB, profile, and the optimal plan
    output_file: str, the path to the output CSV file
    """
    rows = []
    for edb, _, best_plan, _ in results:
        rows.append({"EDB": edb, "Optimal PlanId": best_plan.name})

    # Convert to DataFrame and save as CSV
    df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df.to_csv(output_file, index=False)
    logger.info("Results saved to %s", output_file)


def main():
    """
    Main function to load household profiles,
    calculate the optimal electricity plan by EDB,
    and save the results to a CSV file.
    """
    logger.info("Load the filtered electricity plans")
    filtered_df = get_filtered_df()

    logger.info("Load household profiles using the day/night usage data")
    profiles = load_household_profiles(
        usage_csv_file="../electricity_usage_profile/output/day_night_usage.csv",
        elx_connection_days=DAYS_IN_YEAR,
    )

    logger.info("Calculate the optimal electricity plan for each profile and EDB")
    results = calculate_optimal_plan_by_edb(profiles, filtered_df)

    logger.info("Save the results to CSV")
    output_file = "output/selected_electricity_plans.csv"
    save_results_to_csv(results, output_file)

    logger.info("Output the results")
    for edb, profile, plan, cost in results:
        print(f"EDB: {edb}")
        print(f"Household Profile: {profile}")
        print(f"Optimal Plan: {plan.name}")
        print(f"Total Annual Cost: {cost}\n")
        print(show_plan(int(plan.name), filtered_df, dropna=True))


if __name__ == "__main__":
    main()
