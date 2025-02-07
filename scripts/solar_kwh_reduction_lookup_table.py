"""
This script generates a lookup table for the solar kWh reduction benefit.

To avoid a combinatorial explosion of the lookup table, we use a nested
iteration strategy to collapse the table into a more manageable size,
only considering the relevant combinations of input variables.
"""

import logging
import os

import pandas as pd

from app.constants import EMISSIONS_FACTORS
from app.services.get_climate_zone import climate_zone, postcode_dict
from app.services.get_energy_plans import get_energy_plan

logging.basicConfig(level=logging.INFO)

LOOKUP_DIR = os.path.join(os.path.dirname(__file__), "..", "lookup")
os.makedirs(LOOKUP_DIR, exist_ok=True)

OUTPUT_FILE = "solar_kwh_reduction_lookup_table_collapsed.csv"
REPORT_EVERY_N_ROWS = 1e5
DEFAULT_VEHICLE_TYPE = "None"

people_in_house_options = [1, 2, 3, 4, 5, 6]

# ------------------------
# Heating categories
# ------------------------
HEATING_ELECTRIC = "Electric heater"
HEATING_HEAT_PUMP = "Heat pump"
HEATING_OTHER = "other_heating"

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


def all_heating_combinations():
    """
    Yield (heating_category, heating_during_day, insulation_quality).
    If category is electric heater or heat pump, yield the
    cross product of heating_during_day x insulation_quality.
    If 'other_heating', yield just one combo (with None).
    """
    for cat in heating_categories:
        if cat in (HEATING_ELECTRIC, HEATING_HEAT_PUMP):
            for day_opt in heating_during_day_options:
                for ins_opt in insulation_quality_options:
                    yield (cat, day_opt, ins_opt)
        else:
            yield (cat, None, None)


# ------------------------
# Hot water categories
# ------------------------
HOT_WATER_ELECTRIC = "Electric hot water cylinder"
HOT_WATER_HEAT_PUMP = "Hot water heat pump"
HOT_WATER_OTHER = "other_hot_water"

hot_water_categories = [HOT_WATER_ELECTRIC, HOT_WATER_HEAT_PUMP, HOT_WATER_OTHER]
hot_water_usage_options = ["Low", "Average", "High"]


def all_hot_water_combinations():
    """
    Similarly for hot water:
    If cat is 'Electric hot water cylinder' or 'Hot water heat pump',
    yield sub-combos for usage. Otherwise yield one with usage=None.
    """
    for cat in hot_water_categories:
        if cat in (HOT_WATER_ELECTRIC, HOT_WATER_HEAT_PUMP):
            for usage_opt in hot_water_usage_options:
                yield (cat, usage_opt)
        else:
            yield (cat, None)


# ------------------------
# Driving categories
# ------------------------
DRIVING_ELECTRIC = "Electric"
DRIVING_PLUGIN_HYBRID = "Plug-in hybrid"
DRIVING_OTHER = "other_vehicle"

driving_categories = [DRIVING_ELECTRIC, DRIVING_PLUGIN_HYBRID, DRIVING_OTHER]
km_per_week_options = ["50 or less", "100", "200", "300", "400 or more"]


def all_driving_combinations():
    """
    If the category is 'Electric' or 'Plug-in hybrid',
    iterate over km_per_week. Otherwise yield one combo with None.
    """
    for cat in driving_categories:
        if cat in (DRIVING_ELECTRIC, DRIVING_PLUGIN_HYBRID):
            for km_opt in km_per_week_options:
                yield (cat, km_opt)
        else:
            yield (cat, None)


# ------------------------
# Gather (climate_zone, electricity_plan_name) Pairs
# ------------------------
def get_climate_zone_plan_pairs():
    """
    Return a sorted list of (cz_value, electricity_plan_name)
    from all known postcodes.
    """
    all_postcodes = set(postcode_dict.keys())
    cz_plans = set()

    for p_code in all_postcodes:
        cz_value = climate_zone(p_code)
        energy_plan = get_energy_plan(p_code, DEFAULT_VEHICLE_TYPE)
        plan_name = energy_plan.electricity_plan.name
        cz_plans.add((cz_value, plan_name))

    return sorted(cz_plans)


# ------------------------
# The function that calculates the solar benefit
# (placeholder for your real logic)
# ------------------------
def calculate_solar_kwh_reduction(params):
    """
    Return only the 2 columns you need:
      1) electricity_annual_export_nzd
      2) electricity_annual_self_consumption_nzd

    :param params: dictionary with keys:
      'climate_zone', 'plan_name', 'people_in_house',
      'heating_cat', 'heating_day', 'insulation',
      'hot_water_cat', 'hot_water_usage',
      'driving_cat', 'km_per_week'
    """
    # Reference params so that Pylint doesn't complain it's unused
    _ = params

    # For demonstration, we'll compute some dummy results.
    annual_kwh_generated = 5123.45
    annual_kg_co2e_saving = (
        annual_kwh_generated * EMISSIONS_FACTORS["electricity_kg_co2e_per_kwh"]
    )
    return {
        "annual_kwh_generated": annual_kwh_generated,
        "annual_kg_co2e_saving": annual_kg_co2e_saving,
        "electricity_annual_export_nzd": 123.45,
        "electricity_annual_self_consumption_nzd": 678.90,
    }


# ------------------------
# Main generation function
# ------------------------
def generate_solar_kwh_reduction_lookup_table_collapsed():
    """
    Build a CSV with columns:
      - climate_zone
      - electricity_plan_name
      - people_in_house
      - heating_category, heating_during_day, insulation_quality
      - hot_water_category, hot_water_usage
      - driving_category, km_per_week
      - annual_kwh_generated
      - annual_kg_co2e_saving
      - electricity_annual_export_nzd
      - electricity_annual_self_consumption_nzd
    """
    # Disable Pylint warnings about too many locals & nested blocks:
    # pylint: disable=too-many-locals,too-many-nested-blocks

    rows = []
    total_count = 0

    # (1) climate_zone + plan_name
    cz_plan_pairs = get_climate_zone_plan_pairs()

    for cz_value, plan_name in cz_plan_pairs:
        for num_people in people_in_house_options:
            for heat_cat, heat_day, ins_qual in all_heating_combinations():
                for hw_cat, hw_usage in all_hot_water_combinations():
                    for drive_cat, drive_km in all_driving_combinations():
                        # 1) Build a dict of parameters
                        param_dict = {
                            "climate_zone": cz_value,
                            "plan_name": plan_name,
                            "people_in_house": num_people,
                            "heating_cat": heat_cat,
                            "heating_day": heat_day,
                            "insulation": ins_qual,
                            "hot_water_cat": hw_cat,
                            "hot_water_usage": hw_usage,
                            "driving_cat": drive_cat,
                            "km_per_week": drive_km,
                        }

                        # 2) Calculate the solar benefit
                        result = calculate_solar_kwh_reduction(param_dict)

                        # 3) Build row for CSV
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
                            "km_per_week": drive_km,
                            "annual_kwh_generated": result["annual_kwh_generated"],
                            "annual_kg_co2e_saving": result["annual_kg_co2e_saving"],
                            "electricity_annual_export_nzd": result[
                                "electricity_annual_export_nzd"
                            ],
                            "electricity_annual_self_consumption_nzd": result[
                                "electricity_annual_self_consumption_nzd"
                            ],
                        }
                        rows.append(row)

                        total_count += 1
                        if total_count % REPORT_EVERY_N_ROWS == 0:
                            logging.info("Appended %s rows...", total_count)

    df = pd.DataFrame(rows)
    logging.info("Final row count = %s", len(df))
    out_path = os.path.join(LOOKUP_DIR, OUTPUT_FILE)
    df.to_csv(out_path, index=False)
    logging.info("Wrote CSV to %s", out_path)


if __name__ == "__main__":
    logging.info("Generating collapsed solar kWh reduction lookup table...")
    generate_solar_kwh_reduction_lookup_table_collapsed()
    logging.info("Done.")
