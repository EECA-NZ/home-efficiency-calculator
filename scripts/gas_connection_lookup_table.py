"""
Script to generate lookup table for the deviate PHP web app.
"""

import itertools
import logging
import os

import pandas as pd

from app.constants import CHECKBOX_BEHAVIOUR

logging.basicConfig(level=logging.INFO)

# Constant for the lookup directory. Relative to the script location.
LOOKUP_DIR = os.path.join(os.path.dirname(__file__), "..", "resources", "lookup_tables")
REPORT_EVERY_N_ROWS = 1e5
OUTPUT_FILE = "gas_connection_lookup_table.csv"

# Ensure the directory exists
os.makedirs(LOOKUP_DIR, exist_ok=True)

main_heating_sources = [
    "Piped gas heater",
    "Bottled gas heater",
    "Heat pump",
    "Electric heater",
    "Wood burner",
    None,
]
hot_water_heating_sources = [
    "Electric hot water cylinder",
    "Piped gas hot water cylinder",
    "Piped gas instantaneous",
    "Bottled gas instantaneous",
    "Hot water heat pump",
    None,
]
cooktop_types = [
    "Electric induction",
    "Piped gas",
    "Bottled gas",
    "Electric (coil or ceramic)",
    None,
]
vehicle_types = ["Petrol", "Diesel", "Hybrid", "Plug-in hybrid", "Electric", None]

alternative_main_heating_sources = main_heating_sources.copy()
alternative_hot_water_heating_sources = hot_water_heating_sources.copy()
alternative_cooktop_types = cooktop_types.copy()
alternative_vehicle_types = vehicle_types.copy()


# Cache for expensive functions
energy_plan_cache = {}
climate_zone_cache = {}
cost_emissions_cache = {}

fixed_cost_lookup = []
for combination in itertools.product(
    main_heating_sources,
    alternative_main_heating_sources,
    hot_water_heating_sources,
    alternative_hot_water_heating_sources,
    cooktop_types,
    alternative_cooktop_types,
):
    (
        main_heating_source,
        alternative_main_heating_source,
        hot_water_heating_source,
        alternative_hot_water_heating_source,
        cooktop_type,
        alternative_cooktop_type,
    ) = combination

    current_sources = [
        main_heating_source,
        hot_water_heating_source,
        cooktop_type,
    ]
    alternative_sources = [
        alternative_main_heating_source,
        alternative_hot_water_heating_source,
        alternative_cooktop_type,
    ]

    current_uses_piped_gas = any(
        "piped gas" in source.lower() for source in current_sources if source
    )
    current_uses_bottled_gas = any(
        "bottled gas" in source.lower() for source in current_sources if source
    )
    alternative_uses_piped_gas = any(
        "piped gas" in source.lower() for source in alternative_sources if source
    )
    alternative_uses_bottled_gas = any(
        "bottled gas" in source.lower() for source in alternative_sources if source
    )

    checkbox = CHECKBOX_BEHAVIOUR[
        (
            current_uses_piped_gas,
            current_uses_bottled_gas,
            alternative_uses_piped_gas,
            alternative_uses_bottled_gas,
        )
    ]

    row = {
        "main_heating_source": main_heating_source,
        "hot_water_heating_source": hot_water_heating_source,
        "cooktop_type": cooktop_type,
        "alternative_main_heating_source": alternative_main_heating_source,
        "alternative_hot_water_heating_source": alternative_hot_water_heating_source,
        "alternative_cooktop_type": alternative_cooktop_type,
        "current_uses_piped_gas": current_uses_piped_gas,
        "current_uses_bottled_gas": current_uses_bottled_gas,
        "alternative_uses_piped_gas": alternative_uses_piped_gas,
        "alternative_uses_bottled_gas": alternative_uses_bottled_gas,
        "checkbox_text": checkbox["checkbox_text"],
        "checkbox_visible": checkbox["checkbox_visible"],
        "checkbox_greyed_out": checkbox["checkbox_greyed_out"],
        "checkbox_default_on": checkbox["checkbox_default_on"],
    }
    fixed_cost_lookup.append(row)

    if len(fixed_cost_lookup) % REPORT_EVERY_N_ROWS == 0:
        logging.info("Appended %s rows to fixed_cost_lookup.", len(fixed_cost_lookup))

fixed_cost_df = pd.DataFrame(fixed_cost_lookup)

fixed_cost_df.to_csv(os.path.join(LOOKUP_DIR, OUTPUT_FILE), index=False)
