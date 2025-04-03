"""
This script generates the lookup tables for the solar generation model.
"""

# pylint: disable=no-member, too-many-locals

import logging
import os

import pandas as pd

from app.models.user_answers import (
    CooktopAnswers,
    DrivingAnswers,
    HeatingAnswers,
    HotWaterAnswers,
    YourHomeAnswers,
)
from app.services.get_base_demand_profile import other_electricity_energy_usage_profile
from app.services.get_climate_zone import postcode_dict
from app.services.get_energy_plans import (
    get_energy_plan,
    postcode_to_electricity_plan_dict,
)
from app.services.get_solar_generation import hourly_pmax

# set TEST_MODE to True to run the script in test mode
TEST_MODE = False
os.environ["TEST_MODE"] = "True" if TEST_MODE else "False"

# Round numerical outputs
FLOAT_FORMAT = "%.6f"

# Constants for placeholders
DEFAULT_POSTCODE = "6012"
EXPORT_RATE = 0.12  # NZD per kWh for exported electricity
TIMESERIES_SUM = 1000.0  # Sum of hour columns for each row

# Constant for the lookup directory. Relative to the script location.
if TEST_MODE:
    LOOKUP_DIR = os.path.join(
        os.path.dirname(__file__), "..", "resources", "test_data", "lookup_tables"
    )
else:
    LOOKUP_DIR = os.path.join(
        os.path.dirname(__file__), "..", "resources", "lookup_tables"
    )

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
niwa_climate_zones = list(set(postcode_dict.values()))
climate_zones = sorted(niwa_climate_zones)

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

COOKTOP_ELECTRIC = "Electric induction"
COOKTOP_CERAMIC = "Electric (coil or ceramic)"
cooktop_types = [COOKTOP_ELECTRIC, COOKTOP_CERAMIC]

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

representative_postcode_for_niwa_climate_zone = {}
for niwa_climate_zone in niwa_climate_zones:
    for postcode, zone in postcode_dict.items():
        if zone == niwa_climate_zone:
            representative_postcode_for_niwa_climate_zone[zone] = postcode
            break
    else:
        raise ValueError(
            f"Could not find postcode for climate zone {niwa_climate_zone}"
        )


def convert_np_array_to_dict(np_array):
    """
    Convert a numpy array (length 8760) to a dictionary
    with string keys ("0".."8759").
    """
    return {str(i): np_array[i] for i in range(len(np_array))}


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
        print(f"Generating vehicle lookups for {vt}")
        for size in vehicle_sizes:
            for km in km_per_week_options:
                driving = DrivingAnswers(
                    vehicle_type=vt,
                    vehicle_size=size,
                    km_per_week=km,
                )
                energy = driving.energy_usage_pattern(
                    YourHomeAnswers(
                        people_in_house=3,
                        postcode=DEFAULT_POSTCODE,
                    ),
                    solar_aware=True,
                    use_alternative=False,
                )
                total_kwh = energy.electricity_kwh.total_usage.sum()

                if total_kwh > 0:
                    profile = (
                        TIMESERIES_SUM / total_kwh
                    ) * energy.electricity_kwh.total_usage
                    profile_dict = convert_np_array_to_dict(profile)
                else:
                    raise ValueError("Total kWh should be positive")

                row = {
                    "vehicle_type": vt,
                    "vehicle_size": size,
                    "km_per_week": km,
                    "annual_total_kwh": total_kwh,
                }
                row.update(profile_dict)
                rows.append(row)

    df = pd.DataFrame(rows)
    out_path = os.path.join(output_dir, "solar_vehicle_lookup_table.csv")
    df.to_csv(out_path, float_format=FLOAT_FORMAT, index=False)
    logging.info("Wrote %s rows to %s", len(df), out_path)
    return df


# ----------------------------------------------------------------------
# 2) Generate Hot Water Table
# ----------------------------------------------------------------------
def generate_hot_water_solar_lookup_table(output_dir="."):
    """
    Creates solar_hot_water_lookup_table.csv with columns:
      climate_zone, people_in_house, hot_water_usage, hot_water_heating_source,
      annual_total_kwh, plus 8760 hourly columns (1..8760) summing to 1000.
    """
    rows = []
    for cz in climate_zones:
        print(f"Generating hot water lookups for {cz}")
        pc = representative_postcode_for_niwa_climate_zone[cz]
        for p in people_in_house_options:
            for usage in hot_water_usage_options:
                for hw_source in hot_water_heating_sources:
                    hot_water = HotWaterAnswers(
                        hot_water_usage=usage,
                        hot_water_heating_source=hw_source,
                    )
                    your_home = YourHomeAnswers(
                        people_in_house=p,
                        postcode=pc,
                    )
                    energy = hot_water.energy_usage_pattern(your_home, solar_aware=True)
                    total_kwh = energy.electricity_kwh.total_usage.sum()

                    if total_kwh > 0:
                        profile = (
                            TIMESERIES_SUM / total_kwh
                        ) * energy.electricity_kwh.total_usage
                        profile_dict = convert_np_array_to_dict(profile)
                    else:
                        raise ValueError("Total kWh should be positive")

                    row = {
                        "climate_zone": cz,
                        "people_in_house": p,
                        "hot_water_usage": usage,
                        "hot_water_heating_source": hw_source,
                        "annual_total_kwh": total_kwh,
                    }
                    row.update(profile_dict)
                    rows.append(row)

    df = pd.DataFrame(rows)
    out_path = os.path.join(output_dir, "solar_hot_water_lookup_table.csv")
    df.to_csv(out_path, float_format=FLOAT_FORMAT, index=False)
    logging.info("Wrote %s rows to %s", len(df), out_path)
    return df


# ----------------------------------------------------------------------
# 3) Generate Space Heating Table
# ----------------------------------------------------------------------
def generate_space_heating_solar_lookup_table(output_dir="."):
    """
    Creates solar_space_heating_lookup_table.csv with columns:
      climate_zone, main_heating_source, heating_during_day, insulation_quality,
      annual_total_kwh, plus 8760 hourly columns (1..8760) summing to 1000.
    """
    rows = []
    for cz in climate_zones:
        print(f"Generating space heating lookups for {cz}")
        pc = representative_postcode_for_niwa_climate_zone[cz]
        for main_source in main_heating_sources:
            for heat_day in heating_during_day_options:
                for ins_quality in insulation_quality_options:
                    heating = HeatingAnswers(
                        main_heating_source=main_source,
                        heating_during_day=heat_day,
                        insulation_quality=ins_quality,
                    )
                    heating_energy_use = heating.energy_usage_pattern(
                        YourHomeAnswers(
                            people_in_house=3,
                            postcode=pc,
                        ),
                        solar_aware=True,
                    )
                    total_kwh = heating_energy_use.electricity_kwh.total_usage.sum()

                    if total_kwh > 0:
                        profile = (
                            TIMESERIES_SUM / total_kwh
                        ) * heating_energy_use.electricity_kwh.total_usage
                        profile_dict = convert_np_array_to_dict(profile)
                    else:
                        raise ValueError("Total kWh should be positive")

                    row = {
                        "climate_zone": cz,
                        "main_heating_source": main_source,
                        "heating_during_day": heat_day,
                        "insulation_quality": ins_quality,
                        "annual_total_kwh": total_kwh,
                    }
                    row.update(profile_dict)
                    rows.append(row)

    df = pd.DataFrame(rows)
    out_path = os.path.join(output_dir, "solar_space_heating_lookup_table.csv")
    df.to_csv(out_path, float_format=FLOAT_FORMAT, index=False)
    logging.info("Wrote %s rows to %s", len(df), out_path)
    return df


# ----------------------------------------------------------------------
# 4) Generate Cooktop Table
# ----------------------------------------------------------------------
def generate_cooktop_solar_lookup_table(output_dir="."):
    """
    Creates solar_cooktop_lookup_table.csv with columns:
        climate_zone, cooktop, annual_total_kwh,
        plus 8760 hourly columns (1..8760) summing to 1000.
    """
    rows = []

    for p in people_in_house_options:
        print(f"Generating cooktop lookups for {p} people")
        for c in cooktop_types:
            cooktop = CooktopAnswers(
                cooktop=c,
            )
            your_home = YourHomeAnswers(
                people_in_house=p,
                postcode=DEFAULT_POSTCODE,
            )
            energy = cooktop.energy_usage_pattern(your_home, solar_aware=True)
            total_kwh = energy.electricity_kwh.total_usage.sum()

            if total_kwh > 0:
                profile = (
                    TIMESERIES_SUM / total_kwh
                ) * energy.electricity_kwh.total_usage
                profile_dict = convert_np_array_to_dict(profile)
            else:
                raise ValueError("Total kWh should be positive")

            row = {
                "people_in_house": p,
                "cooktop_type": c,
                "annual_total_kwh": total_kwh,
            }
            row.update(profile_dict)
            rows.append(row)

    df = pd.DataFrame(rows)
    out_path = os.path.join(output_dir, "solar_cooktop_lookup_table.csv")
    df.to_csv(out_path, float_format=FLOAT_FORMAT, index=False)
    logging.info("Wrote %s rows to %s", len(df), out_path)
    return df


# ----------------------------------------------------------------------
# 5) Generate Solar Generation Table
# ----------------------------------------------------------------------
def generate_solar_generation_lookup_table(output_dir="."):
    """
    Creates solar_generation_lookup_table.csv with columns:
      climate_zone, annual_total_kwh, plus 8760 columns (1..8760) whose sum = 1000.
    One row per climate zone; 18 zones.
    """
    rows = []
    for cz in full_climate_zones_for_solar:
        print(f"Generating solar generation lookups for {cz}")
        pc = representative_postcode_for_niwa_climate_zone[cz]
        hourly_pmax_values = hourly_pmax(pc)
        total_kwh = sum(hourly_pmax_values)
        profile = (TIMESERIES_SUM / total_kwh) * hourly_pmax_values
        profile_dict = convert_np_array_to_dict(profile)
        row = {
            "climate_zone": cz,
            "annual_total_kwh": total_kwh,
        }
        row.update(profile_dict)
        rows.append(row)

    df = pd.DataFrame(rows)
    out_path = os.path.join(output_dir, "solar_generation_lookup_table.csv")
    df.to_csv(out_path, float_format=FLOAT_FORMAT, index=False)
    logging.info("Wrote %s rows to %s", len(df), out_path)
    return df


# ----------------------------------------------------------------------
# 5) Generate Other Electricity Usage Table
# ----------------------------------------------------------------------
def generate_other_electricity_usage_lookup_table(output_dir="."):
    """
    Creates solar_other_electricity_usage_lookup_table.csv with:
      annual_total_kwh, plus 8760 hourly columns (1..8760) summing to 1000.
    This table has just one row (other usage).
    """
    other_electricity_usage = other_electricity_energy_usage_profile()
    total_kwh = other_electricity_usage.electricity_kwh.total_usage.sum()
    profile = (
        TIMESERIES_SUM / total_kwh
    ) * other_electricity_usage.electricity_kwh.total_usage
    profile_dict = convert_np_array_to_dict(profile)
    row = {"annual_total_kwh": total_kwh}
    row.update(profile_dict)

    df = pd.DataFrame([row])
    out_path = os.path.join(
        output_dir, "solar_other_electricity_usage_lookup_table.csv"
    )
    df.to_csv(out_path, float_format=FLOAT_FORMAT, index=False)
    logging.info("Wrote 1 row to %s", out_path)
    return df


# ----------------------------------------------------------------------
# 6) Generate Electricity Plans Lookup Table
# ----------------------------------------------------------------------
def generate_electricity_plans_lookup_table(output_dir="."):
    """
    Creates electricity_plans_lookup_table.csv with columns:
      electricity_plan_name, fixed_rate, import_rates_day, import_rates_night,
      kg_co2e_per_kwh (The last column is a constant 0.1072 for all plans.)
    """
    df = transform_plans_to_dataframe()
    out_path = os.path.join(output_dir, "solar_electricity_plans_lookup_table.csv")
    df.to_csv(out_path, float_format=FLOAT_FORMAT, index=False)
    logging.info("Wrote %s rows to %s", len(df), out_path)
    return df


def transform_plans_to_dataframe():
    """
    Build a DataFrame of electricity plans with columns:
      electricity_plan_name, fixed_rate, import_rates_day, import_rates_night,
      import_rates_export, kg_co2e_per_kwh.
    """
    modified_plans = {}
    plans = list(postcode_to_electricity_plan_dict.values())
    # Need to include default plan for fallback
    plans.append(get_energy_plan("not_a_postcode", "Petrol").electricity_plan)
    for plan in plans:
        plan_name = plan.name
        rate_dict = plan.import_rates
        fixed_rate = plan.fixed_rate

        if rate_dict.keys() == {"All inclusive"}:
            all_val = rate_dict["All inclusive"]
            day_rate = all_val
            night_rate = all_val
        elif rate_dict.keys() == {"Uncontrolled"}:
            day_rate = rate_dict["Uncontrolled"]
            night_rate = rate_dict["Uncontrolled"]
        elif rate_dict.keys() == {"Day", "Night"}:
            day_rate = rate_dict.get("Day", None)
            night_rate = rate_dict.get("Night", None)
        else:
            raise ValueError("Unexpected rate_dict keys")

        modified_plans[plan_name] = {
            "fixed_rate": fixed_rate,
            "import_rates_day": day_rate,
            "import_rates_night": night_rate,
            "import_rates_export": EXPORT_RATE,
        }

    df = pd.DataFrame.from_dict(modified_plans, orient="index")
    df.index.name = "electricity_plan_name"
    df.reset_index(inplace=True)

    df["kg_co2e_per_kwh"] = 0.1072

    desired_cols = [
        "electricity_plan_name",
        "fixed_rate",
        "import_rates_day",
        "import_rates_night",
        "import_rates_export",
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
    vehicle_df = generate_vehicle_solar_lookup_table(LOOKUP_DIR)
    cooktop_df = generate_cooktop_solar_lookup_table(LOOKUP_DIR)
    hot_water_df = generate_hot_water_solar_lookup_table(LOOKUP_DIR)
    space_heating_df = generate_space_heating_solar_lookup_table(LOOKUP_DIR)
    other_electricity_df = generate_other_electricity_usage_lookup_table(LOOKUP_DIR)
    solar_generation_df = generate_solar_generation_lookup_table(LOOKUP_DIR)
    electricity_plans_df = generate_electricity_plans_lookup_table(LOOKUP_DIR)

    return (
        vehicle_df,
        cooktop_df,
        hot_water_df,
        space_heating_df,
        other_electricity_df,
        solar_generation_df,
        electricity_plans_df,
    )


if __name__ == "__main__":
    (
        my_vehicle,
        my_cooktop,
        my_hot_water,
        my_space_heating,
        my_other_electricity,
        my_solar_generation,
        my_electricity_plans,
    ) = main()
