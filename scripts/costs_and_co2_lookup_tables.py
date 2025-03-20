"""
Script to generate lookup table for the deviate PHP web app.
"""

import itertools
import logging
import os

import pandas as pd

from app.constants import DEFAULT_SAVINGS_AND_EMISSIONS_RESPONSE as D_S_AND_E

# Post-MVP, exclude postcodes - requires coordination with web team
# from app.constants import EXCLUDE_POSTCODES
from app.models.user_answers import (
    CooktopAnswers,
    DrivingAnswers,
    HeatingAnswers,
    HotWaterAnswers,
    SolarAnswers,
    YourHomeAnswers,
)
from app.services.energy_calculator import emissions_kg_co2e
from app.services.get_climate_zone import climate_zone, postcode_dict
from app.services.get_energy_plans import get_energy_plan

# Round numerical outputs to 3 decimal places.
FLOAT_FORMAT = "%.14f"


logging.basicConfig(level=logging.INFO)

# Constant for the lookup directory. Relative to the script location.
LOOKUP_DIR = os.path.join(os.path.dirname(__file__), "..", "resources", "lookup_tables")
DEFAULT_VEHICLE_TYPE = "None"
REPORT_EVERY_N_ROWS = 1e5

# Ensure the directory exists
os.makedirs(LOOKUP_DIR, exist_ok=True)

NO_SOLAR = SolarAnswers(add_solar=False)

people_in_house = [1, 2, 3, 4, 5, 6]
# Post-MVP, exclude postcodes - requires coordination with web team
# exclude_postcodes = [
#    postcode for sublist in EXCLUDE_POSTCODES.values() for postcode in sublist
# ]
# postcodes = list(x for x in postcode_dict.keys() if x not in exclude_postcodes)
postcodes = list(postcode_dict.keys())
disconnect_gas = [True, False]
main_heating_sources = [
    "Piped gas heater",
    "Bottled gas heater",
    "Heat pump",
    "Electric heater",
    "Wood burner",
]
heating_during_day = ["Never", "1-2 days a week", "3-4 days a week", "5-7 days a week"]
insulation_quality = ["Not well insulated", "Moderately insulated", "Well insulated"]
hot_water_usage = ["Low", "Average", "High"]
hot_water_heating_sources = [
    "Electric hot water cylinder",
    "Piped gas hot water cylinder",
    "Piped gas instantaneous",
    "Bottled gas instantaneous",
    "Hot water heat pump",
]
cooktop_types = [
    "Electric induction",
    "Piped gas",
    "Bottled gas",
    "Electric (coil or ceramic)",
]
vehicle_types = ["Petrol", "Diesel", "Hybrid", "Plug-in hybrid", "Electric"]
vehicle_sizes = ["Small", "Medium", "Large"]
km_per_week = ["50 or less", "100", "200", "300", "400 or more"]
add_solar = [True, False]  # Ignored for now

# Cache for expensive functions
energy_plan_cache = {}
climate_zone_cache = {}
cost_emissions_cache = {}


def clear_output_dir(output_dir):
    """
    Clear the output directory.
    """
    for file in os.listdir(output_dir):
        if file.endswith(".csv"):
            os.remove(os.path.join(output_dir, file))


def uniquify_rows_and_write_to_csv(raw_df, filename):
    """
    Write unique rows to a CSV file.
    """
    final_df = raw_df.drop_duplicates().reset_index(drop=True)
    logging.info("Deduplicating: %s distinct rows.", len(final_df))
    final_df.to_csv(filename, float_format=FLOAT_FORMAT, index=False)
    return final_df


def get_energy_plan_cached(postcode, vehicle_type):
    """
    Cached version of energy_plan function.
    """
    if postcode in energy_plan_cache:
        return energy_plan_cache[(postcode, vehicle_type)]
    plan = get_energy_plan(postcode, vehicle_type)
    energy_plan_cache[(postcode, vehicle_type)] = plan
    return plan


def get_climate_zone_cached(postcode):
    """
    Cached version of climate_zone function.
    """
    if postcode in climate_zone_cache:
        return climate_zone_cache[postcode]
    zone = climate_zone(postcode)
    climate_zone_cache[postcode] = zone
    return zone


def calculate_cost_and_emissions(your_home, answers):
    """
    Use the answers and postcode to calculate cost and emissions.
    """
    # Create a cache key based on the attributes of your_home and answers
    cache_key = (
        your_home.people_in_house,
        your_home.postcode,
        your_home.disconnect_gas,
        tuple(sorted(answers.__dict__.items())),
    )

    if cache_key in cost_emissions_cache:
        return cost_emissions_cache[cache_key]

    energy_usage_profile = answers.energy_usage_pattern(your_home, NO_SOLAR)
    if answers.__class__.__name__ == "DrivingAnswers":
        vehicle_type = answers.vehicle_type
    else:
        vehicle_type = DEFAULT_VEHICLE_TYPE
    my_plan = get_energy_plan_cached(your_home.postcode, vehicle_type)
    (_, variable_cost_nzd) = my_plan.calculate_cost(energy_usage_profile)
    my_emissions_kg_co2e = emissions_kg_co2e(energy_usage_profile)
    result = {
        "variable_cost_nzd": variable_cost_nzd,
        "emissions_kg_co2e": my_emissions_kg_co2e,
    }
    cost_emissions_cache[cache_key] = (result, my_plan)
    return (result, my_plan)


def generate_postcode_lookup_table():
    """
    Generate the postcode lookup table.
    """
    rows = []
    for postcode in postcodes:
        my_plan = get_energy_plan_cached(postcode, DEFAULT_VEHICLE_TYPE)
        my_climate_zone = get_climate_zone_cached(postcode)
        row = {
            "postcode": postcode,
            "climate_zone": my_climate_zone,
            "electricity_plan_name": my_plan.electricity_plan.name,
            "natural_gas_plan_name": my_plan.natural_gas_plan.name,
            "lpg_plan_name": my_plan.lpg_plan.name,
            "wood_price_name": my_plan.wood_price.name,
            "petrol_price_name": my_plan.petrol_price.name,
            "diesel_price_name": my_plan.diesel_price.name,
        }
        rows.append(row)
    postcode_df = pd.DataFrame(rows)
    return uniquify_rows_and_write_to_csv(
        postcode_df,
        os.path.join(LOOKUP_DIR, "postcode_to_climate_and_energy_plans.csv"),
    )


def generate_heating_lookup_table():
    """
    Generate the heating lookup table.
    """
    heating_lookup = []
    for combination in itertools.product(
        people_in_house,
        postcodes,
        disconnect_gas,
        main_heating_sources,
        heating_during_day,
        insulation_quality,
    ):
        (
            people,
            postcode,
            disconnect,
            heating_source,
            heating_day,
            insulation,
        ) = combination

        your_home = YourHomeAnswers(
            people_in_house=people,
            postcode=postcode,
            disconnect_gas=disconnect,
        )
        heating = HeatingAnswers(
            main_heating_source=heating_source,
            heating_during_day=heating_day,
            insulation_quality=insulation,
        )
        cost_emissions, my_plan = calculate_cost_and_emissions(your_home, heating)
        my_climate_zone = get_climate_zone_cached(postcode)

        row = {
            "climate_zone": my_climate_zone,
            "electricity_plan_name": my_plan.electricity_plan.name,
            "natural_gas_plan_name": my_plan.natural_gas_plan.name,
            "lpg_plan_name": my_plan.lpg_plan.name,
            "wood_price_name": my_plan.wood_price.name,
            "petrol_price_name": my_plan.petrol_price.name,
            "diesel_price_name": my_plan.diesel_price.name,
            "people_in_house": people,
            "disconnect_gas": disconnect,
            "main_heating_source": heating_source,
            "heating_during_day": heating_day,
            "insulation_quality": insulation,
            "annual_variable_cost": cost_emissions["variable_cost_nzd"],
            "annual_kg_co2e": cost_emissions["emissions_kg_co2e"],
        }
        heating_lookup.append(row)

        if len(heating_lookup) % REPORT_EVERY_N_ROWS == 0:
            logging.info("Appended %s rows to heating_lookup.", len(heating_lookup))

    space_heating_df = pd.DataFrame(heating_lookup)
    return uniquify_rows_and_write_to_csv(
        space_heating_df, os.path.join(LOOKUP_DIR, "space_heating_lookup_table.csv")
    )


def generate_hot_water_lookup_table():
    """
    Generate the hot water lookup table.
    """
    hot_water_rows = []
    for combination in itertools.product(
        people_in_house,
        postcodes,
        disconnect_gas,
        hot_water_usage,
        hot_water_heating_sources,
    ):
        people, postcode, disconnect, usage, heating_source = combination

        your_home = YourHomeAnswers(
            people_in_house=people,
            postcode=postcode,
            disconnect_gas=disconnect,
        )
        hot_water = HotWaterAnswers(
            hot_water_usage=usage,
            hot_water_heating_source=heating_source,
        )
        cost_emissions, my_plan = calculate_cost_and_emissions(your_home, hot_water)
        my_climate_zone = get_climate_zone_cached(postcode)

        row = {
            "climate_zone": my_climate_zone,
            "electricity_plan_name": my_plan.electricity_plan.name,
            "natural_gas_plan_name": my_plan.natural_gas_plan.name,
            "lpg_plan_name": my_plan.lpg_plan.name,
            "wood_price_name": my_plan.wood_price.name,
            "petrol_price_name": my_plan.petrol_price.name,
            "diesel_price_name": my_plan.diesel_price.name,
            "people_in_house": people,
            "disconnect_gas": disconnect,
            "hot_water_usage": usage,
            "hot_water_heating_source": heating_source,
            "annual_variable_cost": cost_emissions["variable_cost_nzd"],
            "annual_kg_co2e": cost_emissions["emissions_kg_co2e"],
        }
        hot_water_rows.append(row)

        if len(hot_water_rows) % REPORT_EVERY_N_ROWS == 0:
            logging.info("Appended %s rows to hot_water_rows.", len(hot_water_rows))

    hot_water_df = pd.DataFrame(hot_water_rows)
    return uniquify_rows_and_write_to_csv(
        hot_water_df, os.path.join(LOOKUP_DIR, "hot_water_lookup_table.csv")
    )


def generate_cooktop_lookup_table():
    """
    Generate the cooktop lookup table.
    """
    cooktop_rows = []
    for combination in itertools.product(
        people_in_house, postcodes, disconnect_gas, cooktop_types
    ):
        people, postcode, disconnect, cooktop_type = combination

        your_home = YourHomeAnswers(
            people_in_house=people,
            postcode=postcode,
            disconnect_gas=disconnect,
        )
        cooktop = CooktopAnswers(
            cooktop=cooktop_type,
        )
        cost_emissions, my_plan = calculate_cost_and_emissions(your_home, cooktop)
        my_climate_zone = get_climate_zone_cached(postcode)

        row = {
            "climate_zone": my_climate_zone,
            "electricity_plan_name": my_plan.electricity_plan.name,
            "natural_gas_plan_name": my_plan.natural_gas_plan.name,
            "lpg_plan_name": my_plan.lpg_plan.name,
            "wood_price_name": my_plan.wood_price.name,
            "petrol_price_name": my_plan.petrol_price.name,
            "diesel_price_name": my_plan.diesel_price.name,
            "people_in_house": people,
            "disconnect_gas": disconnect,
            "cooktop_type": cooktop_type,
            "annual_variable_cost": cost_emissions["variable_cost_nzd"],
            "annual_kg_co2e": cost_emissions["emissions_kg_co2e"],
        }
        cooktop_rows.append(row)

        if len(cooktop_rows) % REPORT_EVERY_N_ROWS == 0:
            logging.info("Appended %s rows to cooktop_rows.", len(cooktop_rows))

    cooktop_df = pd.DataFrame(cooktop_rows)
    return uniquify_rows_and_write_to_csv(
        cooktop_df, os.path.join(LOOKUP_DIR, "cooktop_lookup_table.csv")
    )


def generate_vehicle_lookup_table():
    """
    Generate the vehicle lookup table.
    """
    vehicle_lookup = []
    for combination in itertools.product(
        people_in_house,
        postcodes,
        disconnect_gas,
        vehicle_types,
        vehicle_sizes,
        km_per_week,
    ):
        (
            people,
            postcode,
            disconnect,
            vehicle_type,
            vehicle_size,
            kilometers,
        ) = combination

        your_home = YourHomeAnswers(
            people_in_house=people,
            postcode=postcode,
            disconnect_gas=disconnect,
        )
        driving = DrivingAnswers(
            vehicle_type=vehicle_type,
            vehicle_size=vehicle_size,
            km_per_week=kilometers,
        )
        cost_emissions, my_plan = calculate_cost_and_emissions(your_home, driving)
        my_climate_zone = get_climate_zone_cached(postcode)

        row = {
            "climate_zone": my_climate_zone,
            "electricity_plan_name": my_plan.electricity_plan.name,
            "natural_gas_plan_name": my_plan.natural_gas_plan.name,
            "lpg_plan_name": my_plan.lpg_plan.name,
            "wood_price_name": my_plan.wood_price.name,
            "petrol_price_name": my_plan.petrol_price.name,
            "diesel_price_name": my_plan.diesel_price.name,
            "people_in_house": people,
            "disconnect_gas": disconnect,
            "vehicle_type": vehicle_type,
            "vehicle_size": vehicle_size,
            "km_per_week": kilometers,
            "annual_variable_cost": cost_emissions["variable_cost_nzd"],
            "annual_kg_co2e": cost_emissions["emissions_kg_co2e"],
        }
        vehicle_lookup.append(row)

        if len(vehicle_lookup) % REPORT_EVERY_N_ROWS == 0:
            logging.info("Appended %s rows to vehicle_lookup.", len(vehicle_lookup))

    vehicle_df = pd.DataFrame(vehicle_lookup)
    return uniquify_rows_and_write_to_csv(
        vehicle_df, os.path.join(LOOKUP_DIR, "vehicle_lookup_table.csv")
    )


def generate_natural_gas_fixed_cost_lookup_table():
    """
    Generate the natural gas fixed cost lookup table.
    """
    natural_gas_fixed_cost_rows = []
    for postcode in postcodes:
        my_plan = get_energy_plan_cached(postcode, DEFAULT_VEHICLE_TYPE)
        row = {
            "natural_gas_plan_name": my_plan.natural_gas_plan.name,
            "natural_gas_fixed_rate": my_plan.natural_gas_plan.fixed_rate,
        }
        natural_gas_fixed_cost_rows.append(row)
    natural_gas_fixed_costs_df = pd.DataFrame(natural_gas_fixed_cost_rows)
    return uniquify_rows_and_write_to_csv(
        natural_gas_fixed_costs_df,
        os.path.join(LOOKUP_DIR, "natural_gas_fixed_cost_lookup_table.csv"),
    )


def generate_lpg_fixed_cost_lookup_table():
    """
    Generate the LPG fixed cost lookup table.
    """
    lpg_fixed_cost_rows = []
    for postcode in postcodes:
        my_plan = get_energy_plan_cached(postcode, DEFAULT_VEHICLE_TYPE)
        row = {
            "lpg_plan_name": my_plan.lpg_plan.name,
            "lpg_fixed_rate": my_plan.lpg_plan.fixed_rate,
        }
        lpg_fixed_cost_rows.append(row)
    lpg_fixed_costs_df = pd.DataFrame(lpg_fixed_cost_rows)
    return uniquify_rows_and_write_to_csv(
        lpg_fixed_costs_df,
        os.path.join(LOOKUP_DIR, "lpg_fixed_cost_lookup_table.csv"),
    )


def generate_average_household_savings_lookup_table():
    """
    Generate the average household savings lookup table.
    """
    average_household_savings_rows = [
        {
            "average_household_savings_nzd": D_S_AND_E["average_household_savings"],
            "average_household_emissions_co2e_reduction_percentage": D_S_AND_E[
                "average_household_emissions_percentage_reduction"
            ],
        }
    ]
    average_household_savings_df = pd.DataFrame(average_household_savings_rows)
    return uniquify_rows_and_write_to_csv(
        average_household_savings_df,
        os.path.join(LOOKUP_DIR, "average_household_savings_lookup_table.csv"),
    )


#### MAIN ####

clear_output_dir(LOOKUP_DIR)
logging.info("Generating postcode lookup table...")
postcode_table = generate_postcode_lookup_table()
logging.info("Generating heating lookup table...")
heating_table = generate_heating_lookup_table()
logging.info("Generating hot water lookup table...")
hotwater_table = generate_hot_water_lookup_table()
logging.info("Generating cooktop lookup table...")
cooktop_table = generate_cooktop_lookup_table()
logging.info("Generating vehicle lookup table...")
vehicle_table = generate_vehicle_lookup_table()
logging.info("Generating natural gas fixed cost lookup table...")
natural_gas_fixed_cost_table = generate_natural_gas_fixed_cost_lookup_table()
logging.info("Generating LPG fixed cost lookup table...")
lpg_fixed_cost_table = generate_lpg_fixed_cost_lookup_table()
logging.info("Generating average household savings lookup table...")
average_household_savings_table = generate_average_household_savings_lookup_table()
