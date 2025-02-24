"""
This script generates the lookup tables for the solar generation model.
"""

import logging
import os

import pandas as pd

from app.services.get_climate_zone import postcode_dict
from app.services.get_energy_plans import postcode_to_electricity_plan_dict

# Round numerical outputs to 3 decimal places.
FLOAT_FORMAT = "%.3f"

# Constants for placeholders
EXPORT_RATE = 0.12  # NZD per kWh for exported electricity
ANNUAL_TOTAL_KWH_PLACEHOLDER = 9999.0
TIMESERIES_SUM = 1000.0  # Sum of hour columns for each row

# Constant for the lookup directory. Relative to the script location.
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
climate_zones = list(set(postcode_dict.values()))
climate_zones = [1, 2, 3, 4, 5, 6]

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

# Climate zones for the solar_generation_lookup_table
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


def hourly_values_summing_to_1000() -> dict:
    """
    Returns a dict of hour columns (strings "1".."8760")
    whose values sum to TIMESERIES_SUM (1000).
    We'll do a uniform distribution: each hour = 1000 / 8760.
    """
    hour_dict = {}
    per_hour = TIMESERIES_SUM / 8760.0  # e.g. ~0.114155
    for hour in range(1, 8761):
        hour_dict[str(hour)] = per_hour
    return hour_dict


# ----------------------------------------------------------------------
# 1) Generate Vehicle Table
# ----------------------------------------------------------------------
def generate_vehicle_solar_lookup_table(output_dir="."):
    """
    Creates solar_vehicle_lookup_table.csv with columns:
      vehicle_type, vehicle_size, km_per_week, annual_total_kwh,
      plus 8760 hourly columns (1..8760) whose sum = 1000.
    """
    rows = []
    for vt in vehicle_types:
        for size in vehicle_sizes:
            for km in km_per_week_options:
                row = {
                    "vehicle_type": vt,
                    "vehicle_size": size,
                    "km_per_week": km,
                    # Place a placeholder for the annual total kWh
                    "annual_total_kwh": ANNUAL_TOTAL_KWH_PLACEHOLDER,
                }
                # Add the 8760-hour shape that sums to 1000
                row.update(hourly_values_summing_to_1000())
                rows.append(row)

    df = pd.DataFrame(rows)
    out_path = os.path.join(output_dir, "solar_vehicle_lookup_table.csv")
    df.to_csv(out_path, float_format=FLOAT_FORMAT, index=False)
    logging.info("Wrote %s rows to %s", len(df), out_path)


# ----------------------------------------------------------------------
# 2) Generate Hot Water Table
# ----------------------------------------------------------------------
def generate_hot_water_solar_lookup_table(output_dir="."):
    """
    Creates solar_hot_water_lookup_table.csv with columns:
      climate_zone, people_in_house, hot_water_usage, hot_water_heating_source,
      annual_total_kwh,
      plus 8760 hourly columns (1..8760) summing to 1000.
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
                    row.update(hourly_values_summing_to_1000())
                    rows.append(row)

    df = pd.DataFrame(rows)
    out_path = os.path.join(output_dir, "solar_hot_water_lookup_table.csv")
    df.to_csv(out_path, float_format=FLOAT_FORMAT, index=False)
    logging.info("Wrote %s rows to %s", len(df), out_path)


# ----------------------------------------------------------------------
# 3) Generate Space Heating Table
# ----------------------------------------------------------------------
def generate_space_heating_solar_lookup_table(output_dir="."):
    """
    Creates solar_space_heating_lookup_table.csv with columns:
      climate_zone, main_heating_source, heating_during_day, insulation_quality,
      annual_total_kwh,
      plus 8760 hourly columns (1..8760) summing to 1000.
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
                    row.update(hourly_values_summing_to_1000())
                    rows.append(row)

    df = pd.DataFrame(rows)
    out_path = os.path.join(output_dir, "solar_space_heating_lookup_table.csv")
    df.to_csv(out_path, float_format=FLOAT_FORMAT, index=False)
    logging.info("Wrote %s rows to %s", len(df), out_path)


# ----------------------------------------------------------------------
# 4) Generate Solar Generation Table
# ----------------------------------------------------------------------
def generate_solar_generation_lookup_table(output_dir="."):
    """
    Creates solar_generation_lookup_table.csv with columns:
      climate_zone, annual_total_kwh,
      plus 8760 columns (1..8760) whose sum = 1000.
    One row per climate zone; 18 zones.
    """
    rows = []
    for zone in full_climate_zones_for_solar:
        row = {
            "climate_zone": zone,
            "annual_total_kwh": ANNUAL_TOTAL_KWH_PLACEHOLDER,
        }
        row.update(hourly_values_summing_to_1000())
        rows.append(row)

    df = pd.DataFrame(rows)
    out_path = os.path.join(output_dir, "solar_generation_lookup_table.csv")
    df.to_csv(out_path, float_format=FLOAT_FORMAT, index=False)
    logging.info("Wrote %s rows to %s", len(df), out_path)


# ----------------------------------------------------------------------
# 5) Generate Other Electricity Usage Table
# ----------------------------------------------------------------------
def generate_other_electricity_usage_lookup_table(output_dir="."):
    """
    Creates solar_other_electricity_usage_lookup_table.csv with:
      annual_total_kwh,
      plus 8760 hourly columns (1..8760) summing to 1000.
    This table has just one row (other usage).
    """
    row = {"annual_total_kwh": ANNUAL_TOTAL_KWH_PLACEHOLDER}
    row.update(hourly_values_summing_to_1000())

    df = pd.DataFrame([row])
    out_path = os.path.join(
        output_dir, "solar_other_electricity_usage_lookup_table.csv"
    )
    df.to_csv(out_path, float_format=FLOAT_FORMAT, index=False)
    logging.info("Wrote 1 row to %s", out_path)


# ----------------------------------------------------------------------
# 6) Generate Electricity Plans Lookup Table
# ----------------------------------------------------------------------
def generate_electricity_plans_lookup_table(output_dir="."):
    """
    Creates electricity_plans_lookup_table.csv with columns:
      electricity_plan_name, daily_charge, nzd_per_kwh_day, nzd_per_kwh_night,
      kg_co2e_per_kwh
    (The last column is a constant 0.1072 for all plans.)
    """
    df = transform_plans_to_dataframe()
    out_path = os.path.join(output_dir, "electricity_plans_lookup_table.csv")
    df.to_csv(out_path, float_format=FLOAT_FORMAT, index=False)
    logging.info("Wrote %s rows to %s", len(df), out_path)


def transform_plans_to_dataframe():
    """
    Build a DataFrame of electricity plans with columns:
      electricity_plan_name, daily_charge, nzd_per_kwh_day, nzd_per_kwh_night,
      kg_co2e_per_kwh (all 0.1072).
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
    df = df[desired_cols]
    return df


def main():
    """
    Main entry point: generate all lookup tables.
    """
    logging.basicConfig(level=logging.INFO)
    os.makedirs(LOOKUP_DIR, exist_ok=True)

    # Generate each lookup table
    generate_vehicle_solar_lookup_table(LOOKUP_DIR)
    generate_hot_water_solar_lookup_table(LOOKUP_DIR)
    generate_space_heating_solar_lookup_table(LOOKUP_DIR)
    generate_other_electricity_usage_lookup_table(LOOKUP_DIR)
    generate_solar_generation_lookup_table(LOOKUP_DIR)
    generate_electricity_plans_lookup_table(LOOKUP_DIR)


if __name__ == "__main__":
    main()
