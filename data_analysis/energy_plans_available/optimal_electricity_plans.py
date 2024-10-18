"""
This script calculates the optimal electricity plan for a household by comparing
different electricity plans against a household's yearly fuel usage profile. The
household's profile is generated based on day and night electricity usage data.
"""

import logging

import pandas as pd

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


def calculate_optimal_plan(profiles, filtered_df):
    """
    Calculate the optimal electricity plan for each household profile.

    Args:
    profiles: List of YearlyFuelUsageProfile objects
    filtered_df: pd.DataFrame, filtered electricity plans

    Returns:
    List of tuples containing profile and the optimal plan
    """
    results = []
    for profile in profiles:
        best_plan = None
        lowest_cost = float("inf")

        for _, plan_data in filtered_df.iterrows():
            plan = ElectricityPlan(
                name=str(plan_data["PlanId"]),  # Ensure the PlanId is a string
                nzd_per_day_kwh=plan_data["Day"],
                nzd_per_night_kwh=plan_data["Night"],
                nzd_per_controlled_kwh=plan_data["Controlled"],
                daily_charge=plan_data["Daily charge"],
            )

            fixed_cost, variable_cost = plan.calculate_cost(profile)
            total_cost = fixed_cost + variable_cost

            if total_cost < lowest_cost:
                lowest_cost = total_cost
                best_plan = plan

        results.append((profile, best_plan, lowest_cost))
    return results


def main():
    """
    Main function to load household profiles, calculate the optimal electricity plan,
    and display the results.
    """
    logger.info("Load the filtered electricity plans")
    filtered_df = get_filtered_df()

    logger.info("Load household profiles using the day/night usage data")
    profiles = load_household_profiles(
        usage_csv_file="../electricity_usage_profile/output/day_night_usage.csv",
        elx_connection_days=365.25,  # Assuming a full year of connection
    )

    logger.info("Calculate the optimal electricity plan for each profile")
    results = calculate_optimal_plan(profiles, filtered_df)

    logger.info("Output the results")
    for profile, plan, cost in results:
        print(f"Household Profile: {profile}")
        print(f"Optimal Plan: {plan.name}")
        print(f"Total Annual Cost: {cost}\n")
        print(show_plan(int(plan.name), filtered_df, dropna=True))


if __name__ == "__main__":
    main()
