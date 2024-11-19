"""
Script to generate lookup table for the deviate PHP web app.

Logic is as follows:

- First determine whether piped gas or bottled gas is used
in the current and alternative scenario. Then, determine:

    - Checkbox Visibility:
        The checkbox is not visible only when there is no
        gas usage in either the current or alternative states.
        Otherwise, the checkbox is visible.
    - Checkbox Text:
        The text depends on the differences between the
        current and alternative gas usage.
        Possible actions include adding or removing a gas
        connection or gas bottle rental, or replacing one
        with the other.
    - Checkbox Greyed Out:
        The checkbox is greyed out when there is no change
        in the gas usage. In this case the checkbox is
        defaulted off.
        Otherwise, it is active (not greyed out).
    - Checkbox Default On:
        The checkbox is defaulted on for actions that add
        or remove services.
        As per above, if the checkbox is greyed out, it is
        defaulted off (and can't be toggled).

"""

import itertools
import logging
import os

import pandas as pd

logging.basicConfig(level=logging.INFO)

# Constant for the lookup directory. Relative to the script location.
LOOKUP_DIR = os.path.join(os.path.dirname(__file__), "..", "lookup")
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


# Below, the key stands for:
#   (
#    current_uses_piped_gas,
#    current_uses_bottled_gas,
#    alternative_uses_piped_gas,
#    alternative_uses_bottled_gas
#   )
checkbox_behaviour = {
    (False, False, False, False): {
        "checkbox_visible": False,
        "checkbox_text": None,
        "checkbox_greyed_out": None,
        "checkbox_default_on": None,
    },
    (False, False, False, True): {
        "checkbox_visible": True,
        "checkbox_text": "Adding a gas bottle rental",
        "checkbox_greyed_out": False,
        "checkbox_default_on": True,
    },
    (False, False, True, False): {
        "checkbox_visible": True,
        "checkbox_text": "Adding a gas connection",
        "checkbox_greyed_out": False,
        "checkbox_default_on": True,
    },
    (False, False, True, True): {
        "checkbox_visible": True,
        "checkbox_text": "Adding a gas connection and gas bottle rental",
        "checkbox_greyed_out": False,
        "checkbox_default_on": True,
    },
    (False, True, False, False): {
        "checkbox_visible": True,
        "checkbox_text": "Removing your gas bottle rental",
        "checkbox_greyed_out": False,
        "checkbox_default_on": True,
    },
    (False, True, False, True): {
        "checkbox_visible": True,
        "checkbox_text": "Removing your gas bottle rental",
        "checkbox_greyed_out": True,
        "checkbox_default_on": False,
    },
    (False, True, True, False): {
        "checkbox_visible": True,
        "checkbox_text": "Replacing your gas bottle rental with a gas connection",
        "checkbox_greyed_out": False,
        "checkbox_default_on": True,
    },
    (False, True, True, True): {
        "checkbox_visible": True,
        "checkbox_text": "Adding a gas connection",
        "checkbox_greyed_out": False,
        "checkbox_default_on": True,
    },
    (True, False, False, False): {
        "checkbox_visible": True,
        "checkbox_text": "Removing your gas connection",
        "checkbox_greyed_out": False,
        "checkbox_default_on": True,
    },
    (True, False, False, True): {
        "checkbox_visible": True,
        "checkbox_text": "Replacing your gas connection with a gas bottle rental",
        "checkbox_greyed_out": False,
        "checkbox_default_on": True,
    },
    (True, False, True, False): {
        "checkbox_visible": True,
        "checkbox_text": "Removing your gas connection",
        "checkbox_greyed_out": True,
        "checkbox_default_on": False,
    },
    (True, False, True, True): {
        "checkbox_visible": True,
        "checkbox_text": "Adding a gas bottle rental",
        "checkbox_greyed_out": False,
        "checkbox_default_on": True,
    },
    (True, True, False, False): {
        "checkbox_visible": True,
        "checkbox_text": "Removing your gas connection and gas bottle rental",
        "checkbox_greyed_out": False,
        "checkbox_default_on": True,
    },
    (True, True, False, True): {
        "checkbox_visible": True,
        "checkbox_text": "Removing your gas connection",
        "checkbox_greyed_out": False,
        "checkbox_default_on": True,
    },
    (True, True, True, False): {
        "checkbox_visible": True,
        "checkbox_text": "Removing your gas bottle rental",
        "checkbox_greyed_out": False,
        "checkbox_default_on": True,
    },
    (True, True, True, True): {
        "checkbox_visible": True,
        "checkbox_text": "Removing your gas connection and gas bottle rental",
        "checkbox_greyed_out": True,
        "checkbox_default_on": False,
    },
}

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

    checkbox = checkbox_behaviour[
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
