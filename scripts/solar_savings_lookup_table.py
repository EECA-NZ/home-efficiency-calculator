"""
This script generates a lookup table for the solar kWh reduction benefit.

To avoid a combinatorial explosion of the lookup table, we use a nested
iteration strategy to collapse the table into a more manageable size,
only considering the relevant combinations of input variables.
"""

import logging
import os

import pandas as pd

from app.models.user_answers import (
    DrivingAnswers,
    HeatingAnswers,
    HotWaterAnswers,
    YourHomeAnswers,
)
from app.services.get_climate_zone import climate_zone, postcode_dict
from app.services.get_energy_plans import get_energy_plan
from app.services.solar_calculator import calculate_solar_savings

# -----------------------------------------------------------------------------
# Logging configuration and output directory setup
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)

LOOKUP_DIR = os.path.join(os.path.dirname(__file__), "..", "lookup")
os.makedirs(LOOKUP_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# Global Constants
# -----------------------------------------------------------------------------
OUTPUT_FILE = "solar_savings_lookup_table.csv"
REPORT_EVERY_N_ROWS = 1e5
DEFAULT_VEHICLE_TYPE = "None"
people_in_house_options = [1, 2, 3, 4, 5, 6]

# Heating constants and options
HEATING_ELECTRIC = "Electric heater"
HEATING_HEAT_PUMP = "Heat pump"
HEATING_OTHER = "other_heating"
heating_electric = [HEATING_ELECTRIC, HEATING_HEAT_PUMP]
heating_categories = [HEATING_ELECTRIC, HEATING_HEAT_PUMP, HEATING_OTHER]
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

# Hot water constants and options
HOT_WATER_ELECTRIC = "Electric hot water cylinder"
HOT_WATER_HEAT_PUMP = "Hot water heat pump"
HOT_WATER_OTHER = "other_hot_water"
hot_water_electric = [HOT_WATER_ELECTRIC, HOT_WATER_HEAT_PUMP]
hot_water_categories = [HOT_WATER_ELECTRIC, HOT_WATER_HEAT_PUMP, HOT_WATER_OTHER]
hot_water_usage_options = ["Low", "Average", "High"]

# Driving constants and options
DRIVING_ELECTRIC = "Electric"
DRIVING_PLUGIN_HYBRID = "Plug-in hybrid"
DRIVING_OTHER = "other_vehicle"
driving_electric = [DRIVING_ELECTRIC, DRIVING_PLUGIN_HYBRID]
driving_categories = [DRIVING_ELECTRIC, DRIVING_PLUGIN_HYBRID, DRIVING_OTHER]
km_per_week_options = ["50 or less", "100", "200", "300", "400 or more"]
size_options = ["Small", "Medium", "Large"]

# Fossil-fuel default instances for "other" categories
DEFAULT_FOSSIL_HEATING = HeatingAnswers(
    main_heating_source="Piped gas heater",
    heating_during_day="Never",
    insulation_quality="Moderately insulated",
)
DEFAULT_FOSSIL_HOT_WATER = HotWaterAnswers(
    hot_water_usage="Average", hot_water_heating_source="Piped gas hot water cylinder"
)
DEFAULT_FOSSIL_VEHICLE = DrivingAnswers(
    vehicle_type="Petrol", vehicle_size="Medium", km_per_week="100"
)


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def uniquify_rows_and_write_to_csv(raw_df, filename):
    """
    Write unique rows to a CSV file.
    """
    final_df = raw_df.drop_duplicates().reset_index(drop=True)
    logging.info("Deduplicating: %s distinct rows.", len(final_df))
    final_df.to_csv(filename, index=False)
    return final_df


def get_representative_postcode_for_each_climate_zone_plan():
    """
    Iterate over all known postcodes and pick one representative postcode
    for each unique (climate_zone, electricity_plan_name) pair.
    Returns a list of tuples: (postcode, climate_zone, electricity_plan_name)
    """
    pair_to_postcode = {}
    for p_code in postcode_dict.keys():
        cz_value = climate_zone(p_code)
        energy_plan = get_energy_plan(p_code, DEFAULT_VEHICLE_TYPE)
        plan_name = energy_plan.electricity_plan.name
        key = (cz_value, plan_name)
        if key not in pair_to_postcode:
            pair_to_postcode[key] = p_code
    return [(postcode, cz, plan) for (cz, plan), postcode in pair_to_postcode.items()]


def all_heating_combinations():
    """
    Yield tuples of (heating_category, heating_during_day, insulation_quality).
    For electric heaters and heat pumps, yield all sub-combinations;
    for 'other_heating', yield one combo with None values.
    """
    for cat in heating_categories:
        if cat in heating_electric:
            for day_opt in heating_during_day_options:
                for ins_opt in insulation_quality_options:
                    yield (cat, day_opt, ins_opt)
        else:
            yield (cat, None, None)


def all_hot_water_combinations():
    """
    Yield tuples of (hot_water_category, hot_water_usage).
    For certain categories, yield sub-combinations;
    otherwise yield one combo with usage=None.
    """
    for cat in hot_water_categories:
        if cat in hot_water_electric:
            for usage_opt in hot_water_usage_options:
                yield (cat, usage_opt)
        else:
            yield (cat, None)


def all_driving_combinations():
    """
    Yield tuples of (driving_category, vehicle_size, km_per_week).
    For Electric and Plug-in hybrid, iterate over km_per_week;
    otherwise yield one combo with km_per_week=None.
    """
    for cat in driving_categories:
        if cat in driving_electric:
            for size_opt in size_options:
                for km_opt in km_per_week_options:
                    yield (cat, size_opt, km_opt)
        else:
            yield (cat, None, None)


# -----------------------------------------------------------------------------
# Main Generation Function
# -----------------------------------------------------------------------------
def generate_solar_kwh_reduction_lookup_table():
    """
    Generate a CSV lookup table that includes:
      - climate_zone
      - electricity_plan_name
      - people_in_house
      - heating (category, day, insulation)
      - hot water (category, usage)
      - driving (category, vehicle size, km per week)
      - solar benefit results (kWh generated, kg CO2e saving,
            export & self-consumption dollar values)
    """
    # pylint: disable=too-many-locals,too-many-nested-blocks
    rows = []
    total_count = 0

    # Get one representative postcode for each unique (climate_zone, plan) pair.
    rep_entries = get_representative_postcode_for_each_climate_zone_plan()

    for postcode, cz_value, plan_name in rep_entries:
        for num_people in people_in_house_options:
            for heat_cat, heat_day, ins_qual in all_heating_combinations():
                for hw_cat, hw_usage in all_hot_water_combinations():
                    for drive_cat, drive_size, drive_km in all_driving_combinations():
                        # Create the answer objects.
                        your_home = YourHomeAnswers(
                            people_in_house=num_people,
                            postcode=postcode,
                            disconnect_gas=False,
                        )
                        if heat_cat == HEATING_OTHER:
                            heating_obj = DEFAULT_FOSSIL_HEATING
                        else:
                            heating_obj = HeatingAnswers(
                                main_heating_source=heat_cat,
                                heating_during_day=heat_day,
                                insulation_quality=ins_qual,
                            )
                        if hw_cat == HOT_WATER_OTHER:
                            hot_water_obj = DEFAULT_FOSSIL_HOT_WATER
                        else:
                            hot_water_obj = HotWaterAnswers(
                                hot_water_usage=hw_usage,
                                hot_water_heating_source=hw_cat,
                            )
                        if drive_cat == DRIVING_OTHER:
                            driving_obj = DEFAULT_FOSSIL_VEHICLE
                        else:
                            driving_obj = DrivingAnswers(
                                vehicle_type=drive_cat,
                                vehicle_size=drive_size,
                                km_per_week=drive_km,
                            )
                        # Build the CSV row.
                        row = {
                            "climate_zone": cz_value,
                            "electricity_plan_name": plan_name,
                            "people_in_house": num_people,
                            "heating_category": heat_cat,
                            "heating_during_day": heat_day,
                            "insulation_quality": ins_qual,
                            "hot_water_category": hw_cat,
                            "hot_water_usage": hw_usage,
                            "driving_category": drive_cat,
                            "vehicle_size": drive_size,
                            "km_per_week": drive_km,
                        }
                        # Calculate the solar benefit and add to the row.
                        result = calculate_solar_savings(
                            your_home, heating_obj, hot_water_obj, driving_obj
                        )
                        row.update(result)
                        # Append the row to the list.
                        rows.append(row)
                        total_count += 1
                        if total_count % REPORT_EVERY_N_ROWS == 0:
                            logging.info("Appended %s rows...", total_count)

    df = pd.DataFrame(rows)
    logging.info("Final row count = %s", len(df))
    out_path = os.path.join(LOOKUP_DIR, OUTPUT_FILE)
    uniquify_rows_and_write_to_csv(df, out_path)
    logging.info("Wrote CSV to %s", out_path)
    return df


# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------
def main():
    """
    Main entry point for the script. Generates and saves lookup table.
    """
    logging.info("Generating solar kWh reduction lookup table...")
    df = generate_solar_kwh_reduction_lookup_table()
    logging.info("Done.")
    return df


if __name__ == "__main__":
    main()
