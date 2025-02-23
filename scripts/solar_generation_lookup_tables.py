"""
This module generates CSV lookup tables with monthly JSON timeseries
for solar usage, hot water, vehicle, and space heating, plus an
electricity plans lookup table. Each table uses uniform hourly values
summed to 1000 across the year, grouped by calendar month.
"""

import json
import logging
import os

import pandas as pd

from app.services.get_energy_plans import postcode_to_electricity_plan_dict

# Formatting constants
FLOAT_FORMAT = "%.3f"
TIMESERIES_SUM = 1000.0  # Sum across all 8760 hours
ANNUAL_TOTAL_KWH_PLACEHOLDER = 9999.0
EXPORT_RATE = 0.12  # For electricity plans

# Directory for outputs (relative to this script).
LOOKUP_DIR = os.path.join(os.path.dirname(__file__), "..", "lookup")

VEHICLE_PLUGIN_HYBRID = "Plug-in hybrid"
VEHICLE_ELECTRIC = "Electric"
vehicle_types = [VEHICLE_PLUGIN_HYBRID, VEHICLE_ELECTRIC]
vehicle_sizes = ["Small", "Medium", "Large"]
km_per_week_options = ["50 or less", "100", "200", "300", "400 or more"]

HOT_WATER_HEAT_PUMP = "Hot water heat pump"
HOT_WATER_ELECTRIC = "Electric hot water cylinder"
hot_water_heating_sources = [HOT_WATER_HEAT_PUMP, HOT_WATER_ELECTRIC]
hot_water_usage_options = ["Low", "Average", "High"]
people_in_house_options = [1, 2, 3, 4, 5, 6]

HEATING_HEAT_PUMP = "Heat pump"
HEATING_ELECTRIC = "Electric heater"
main_heating_sources = [HEATING_HEAT_PUMP, HEATING_ELECTRIC]
heating_during_day_options = [
    "Never",
    "1-2 days a week",
    "3-4 days a week",
    "5-7 days a week",
]
insulation_quality_options = [
    "Not well insulated",
    "Moderately insulated",
    "Well insulated",
]

# Climate zones
climate_zones = [1, 2, 3, 4, 5, 6]
full_climate_zones_for_solar = [
    "Northland",
    "Auckland",
    "Hamilton",
    "Rotorua",
    "Bay of Plenty",
    "Taupo",
    "East Coast",
    "New Plymouth",
    "Manawatu",
    "Wairarapa",
    "Wellington",
    "Nelson-Marlborough",
    "Christchurch",
    "West Coast",
    "Central Otago",
    "Dunedin",
    "Queenstown-Lakes",
    "Invercargill",
]


def build_monthly_timeseries() -> dict[str, str]:
    """
    Construct a DataFrame of 8760 hourly rows for a typical non-leap year.
    Each row is labeled with a datetime index from Jan 1 to Dec 31 (inclusive),
    and has a single 'value' column whose sum across the entire year
    is TIMESERIES_SUM (1000).

    Then group by the 'month' (1..12) to build JSON arrays for each month.
    Return a dict of:
      {
        "january_timeseries_json": "[...]", ..., "december_timeseries_json": "[...]"
      }

    We use uniform distribution so that each hour is (1000 / 8760). Summing
    them yields ~1000 total.
    """
    dt_index = pd.date_range("2023-01-01", "2023-12-31 23:00", freq="h")

    df = pd.DataFrame(index=dt_index)
    per_hour = TIMESERIES_SUM / 8760.0
    df["value"] = round(per_hour, 3)

    df["month"] = df.index.month  # integer 1..12

    results = {}
    month_num_to_name = {
        1: "january",
        2: "february",
        3: "march",
        4: "april",
        5: "may",
        6: "june",
        7: "july",
        8: "august",
        9: "september",
        10: "october",
        11: "november",
        12: "december",
    }

    grouped = df.groupby("month")["value"]
    for m in range(1, 13):
        group_values = grouped.get_group(m).tolist()
        month_json = json.dumps(group_values)
        col_name = f"{month_num_to_name[m]}_timeseries_json"
        results[col_name] = month_json

    return results


def build_df_with_monthly_json(rows: list[dict], filename: str) -> None:
    """
    Turn a list of dictionaries into a DataFrame and write as CSV.
    The monthly JSON columns are just strings in the CSV.
    """
    df = pd.DataFrame(rows)
    out_path = os.path.join(LOOKUP_DIR, filename)
    df.to_csv(out_path, float_format=FLOAT_FORMAT, index=False)
    logging.info("Wrote %s rows to %s", len(df), out_path)


def generate_vehicle_solar_lookup_table() -> None:
    """
    Creates solar_vehicle_lookup_table.csv with columns:
      vehicle_type, vehicle_size, km_per_week, annual_total_kwh,
      january_timeseries_json, ..., december_timeseries_json
    """
    rows = []
    for vt in vehicle_types:
        for size in vehicle_sizes:
            for km in km_per_week_options:
                row = {
                    "vehicle_type": vt,
                    "vehicle_size": size,
                    "km_per_week": km,
                    "annual_total_kwh": ANNUAL_TOTAL_KWH_PLACEHOLDER,
                }
                row.update(build_monthly_timeseries())
                rows.append(row)

    build_df_with_monthly_json(rows, "solar_vehicle_lookup_table.csv")


def generate_hot_water_solar_lookup_table() -> None:
    """
    Creates solar_hot_water_lookup_table.csv with columns:
      climate_zone, people_in_house, hot_water_usage, hot_water_heating_source,
      annual_total_kwh,
      january_timeseries_json, ..., december_timeseries_json
    """
    rows = []
    for cz in climate_zones:
        for p in people_in_house_options:
            for usage in hot_water_usage_options:
                for hw_source in hot_water_heating_sources:
                    row = {
                        "climate_zone": cz,
                        "people_in_house": p,
                        "hot_water_usage": usage,
                        "hot_water_heating_source": hw_source,
                        "annual_total_kwh": ANNUAL_TOTAL_KWH_PLACEHOLDER,
                    }
                    row.update(build_monthly_timeseries())
                    rows.append(row)

    build_df_with_monthly_json(rows, "solar_hot_water_lookup_table.csv")


def generate_space_heating_solar_lookup_table() -> None:
    """
    Creates solar_space_heating_lookup_table.csv with columns:
      climate_zone, main_heating_source, heating_during_day, insulation_quality,
      annual_total_kwh,
      january_timeseries_json, ..., december_timeseries_json
    """
    rows = []
    for cz in climate_zones:
        for main_source in main_heating_sources:
            for heat_day in heating_during_day_options:
                for ins_quality in insulation_quality_options:
                    row = {
                        "climate_zone": cz,
                        "main_heating_source": main_source,
                        "heating_during_day": heat_day,
                        "insulation_quality": ins_quality,
                        "annual_total_kwh": ANNUAL_TOTAL_KWH_PLACEHOLDER,
                    }
                    row.update(build_monthly_timeseries())
                    rows.append(row)

    build_df_with_monthly_json(rows, "solar_space_heating_lookup_table.csv")


def generate_solar_generation_lookup_table() -> None:
    """
    Creates solar_generation_lookup_table.csv with columns:
      climate_zone, annual_total_kwh,
      january_timeseries_json, ..., december_timeseries_json
    One row per climate zone in full_climate_zones_for_solar.
    """
    rows = []
    for zone in full_climate_zones_for_solar:
        row = {
            "climate_zone": zone,
            "annual_total_kwh": ANNUAL_TOTAL_KWH_PLACEHOLDER,
        }
        row.update(build_monthly_timeseries())
        rows.append(row)

    build_df_with_monthly_json(rows, "solar_generation_lookup_table.csv")


def generate_other_electricity_usage_lookup_table() -> None:
    """
    Creates solar_other_electricity_usage_lookup_table.csv with columns:
      annual_total_kwh,
      january_timeseries_json, ..., december_timeseries_json
    This table has just one row.
    """
    row = {"annual_total_kwh": ANNUAL_TOTAL_KWH_PLACEHOLDER}
    row.update(build_monthly_timeseries())
    build_df_with_monthly_json([row], "solar_other_electricity_usage_lookup_table.csv")


def transform_plans_to_dataframe() -> pd.DataFrame:
    """
    Build a DataFrame of electricity plans with columns:
      electricity_plan_name, daily_charge, nzd_per_kwh_day, nzd_per_kwh_night,
      nzd_per_kwh_export, kg_co2e_per_kwh
    """
    modified_plans = {}
    for plan in postcode_to_electricity_plan_dict.values():
        plan_name = plan.name
        rate_dict = plan.nzd_per_kwh
        daily_charge = plan.daily_charge

        if "All inclusive" in rate_dict:
            all_val = rate_dict["All inclusive"]
            day_rate = all_val
            night_rate = all_val
        else:
            day_rate = rate_dict.get("Day", None)
            night_rate = rate_dict.get("Night", None)

        modified_plans[plan_name] = {
            "daily_charge": daily_charge,
            "nzd_per_kwh_day": day_rate,
            "nzd_per_kwh_night": night_rate,
            "nzd_per_kwh_export": EXPORT_RATE,
        }

    df = pd.DataFrame.from_dict(modified_plans, orient="index")
    df.index.name = "electricity_plan_name"
    df.reset_index(inplace=True)

    df["kg_co2e_per_kwh"] = 0.1072

    desired_cols = [
        "electricity_plan_name",
        "daily_charge",
        "nzd_per_kwh_day",
        "nzd_per_kwh_night",
        "nzd_per_kwh_export",
        "kg_co2e_per_kwh",
    ]
    return df[desired_cols]


def generate_electricity_plans_lookup_table() -> None:
    """
    Creates electricity_plans_lookup_table.csv with columns:
      electricity_plan_name, daily_charge, nzd_per_kwh_day,
      nzd_per_kwh_night, nzd_per_kwh_export, kg_co2e_per_kwh
    """
    df = transform_plans_to_dataframe()
    out_path = os.path.join(LOOKUP_DIR, "electricity_plans_lookup_table.csv")
    df.to_csv(out_path, float_format=FLOAT_FORMAT, index=False)
    logging.info("Wrote %s rows to %s", len(df), out_path)


def main() -> None:
    """
    Main entry point for generating all lookup tables.
    Ensures output directory exists, then produces each CSV
    with monthly JSON timeseries or simpler plan data.
    """
    logging.basicConfig(level=logging.INFO)
    os.makedirs(LOOKUP_DIR, exist_ok=True)

    generate_vehicle_solar_lookup_table()
    generate_hot_water_solar_lookup_table()
    generate_space_heating_solar_lookup_table()
    generate_other_electricity_usage_lookup_table()
    generate_solar_generation_lookup_table()
    generate_electricity_plans_lookup_table()


if __name__ == "__main__":
    main()
