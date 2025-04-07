"""
General constants used in the calculations

Note: a 'documentation' excel workbook is to be created, and we
intend to add it into the repository and link to it from this
docstring. Links to supporting literature will be added here.

Sources for emissions factors as follows:
# Electricity grid emission factor:
#   a five-year average (2019-2023) of MBIE numbers
"""

CALENDAR_YEAR = 2019

DAYS_IN_YEAR = 365.25

AVERAGE_HOUSEHOLD_SIZE = 2.69

DEFAULT_SAVINGS_AND_EMISSIONS_RESPONSE = {
    "average_household_savings": 1000,
    "average_household_emissions_percentage_reduction": 85,
}

EMISSIONS_FACTORS = {
    "electricity_kg_co2e_per_kwh": 0.1072,
    "natural_gas_kg_co2e_per_kwh": 0.195,
    "lpg_kg_co2e_per_kwh": 0.214,
    "wood_kg_co2e_per_kwh": 0.005,
    "petrol_kg_co2e_per_litre": 2.41,
    "diesel_kg_co2e_per_litre": 2.67,
}

DAILY_DUAL_FUEL_DISCOUNT = 0.15

EXCLUDE_POSTCODES = {
    "Chatham Islands": ["8016"],
    "Stewart Island": ["9818", "9846"],
}


# The CHECKBOX_BEHAVIOUR lookup logic is as follows:
#
# - First determine whether piped gas or bottled gas is used
# in the current and alternative scenario. Then, determine:
#
#    - Checkbox Visibility:
#        The checkbox is not visible only when there is no
#        gas usage in either the current or alternative states.
#        Otherwise, the checkbox is visible.
#    - Checkbox Text:
#        The text depends on the differences between the
#        current and alternative gas usage.
#        Possible actions include adding or removing a gas
#        connection or gas bottle rental, or replacing one
#        with the other.
#    - Checkbox Greyed Out:
#        The checkbox is greyed out when there is no change
#        in the gas usage. In this case the checkbox is
#        defaulted off.
#        Otherwise, it is active (not greyed out).
#    - Checkbox Default On:
#        The checkbox is defaulted on for actions that add
#        or remove services.
#        As per above, if the checkbox is greyed out, it is
#        defaulted off (and can't be toggled).
# We simply enumerate all cases
# because it takes more code to
# do it programmatically.
# Below, the key stands for:
#   (
#    current_uses_piped_gas,
#    current_uses_bottled_gas,
#    alternative_uses_piped_gas,
#    alternative_uses_bottled_gas
#   )
CHECKBOX_BEHAVIOUR = {
    (False, False, False, False): {
        "checkbox_visible": False,
        "checkbox_text": None,
        "checkbox_greyed_out": None,
        "checkbox_default_on": None,
    },
    (False, False, False, True): {
        "checkbox_visible": True,
        "checkbox_text": "Extra costs associated with adding a gas bottle rental",
        "checkbox_greyed_out": False,
        "checkbox_default_on": True,
    },
    (False, False, True, False): {
        "checkbox_visible": True,
        "checkbox_text": "Extra costs associated with adding a gas connection",
        "checkbox_greyed_out": False,
        "checkbox_default_on": True,
    },
    (False, False, True, True): {
        "checkbox_visible": True,
        "checkbox_text": "Extra costs associated with"
        + " adding a gas connection and gas bottle rental",
        "checkbox_greyed_out": False,
        "checkbox_default_on": True,
    },
    (False, True, False, False): {
        "checkbox_visible": True,
        "checkbox_text": "Savings associated with removing your gas bottle rental",
        "checkbox_greyed_out": False,
        "checkbox_default_on": True,
    },
    (False, True, False, True): {
        "checkbox_visible": True,
        "checkbox_text": "Savings associated with removing your gas bottle rental",
        "checkbox_greyed_out": True,
        "checkbox_default_on": False,
    },
    (False, True, True, False): {
        "checkbox_visible": True,
        "checkbox_text": "Fixed cost changes associated with"
        + " replacing your gas bottle rental with a gas connection",
        "checkbox_greyed_out": False,
        "checkbox_default_on": True,
    },
    (False, True, True, True): {
        "checkbox_visible": True,
        "checkbox_text": "Extra costs associated with adding a gas connection",
        "checkbox_greyed_out": False,
        "checkbox_default_on": True,
    },
    (True, False, False, False): {
        "checkbox_visible": True,
        "checkbox_text": "Savings associated with removing your gas connection",
        "checkbox_greyed_out": False,
        "checkbox_default_on": True,
    },
    (True, False, False, True): {
        "checkbox_visible": True,
        "checkbox_text": "Fixed cost changes associated with"
        + " replacing your gas connection with a gas bottle rental",
        "checkbox_greyed_out": False,
        "checkbox_default_on": True,
    },
    (True, False, True, False): {
        "checkbox_visible": True,
        "checkbox_text": "Savings associated with removing your gas connection",
        "checkbox_greyed_out": True,
        "checkbox_default_on": False,
    },
    (True, False, True, True): {
        "checkbox_visible": True,
        "checkbox_text": "Extra costs associated with adding a gas bottle rental",
        "checkbox_greyed_out": False,
        "checkbox_default_on": True,
    },
    (True, True, False, False): {
        "checkbox_visible": True,
        "checkbox_text": "Savings associated with"
        + " removing your gas connection and gas bottle rental",
        "checkbox_greyed_out": False,
        "checkbox_default_on": True,
    },
    (True, True, False, True): {
        "checkbox_visible": True,
        "checkbox_text": "Savings associated with removing your gas connection",
        "checkbox_greyed_out": False,
        "checkbox_default_on": True,
    },
    (True, True, True, False): {
        "checkbox_visible": True,
        "checkbox_text": "Savings associated with removing your gas bottle rental",
        "checkbox_greyed_out": False,
        "checkbox_default_on": True,
    },
    (True, True, True, True): {
        "checkbox_visible": True,
        "checkbox_text": "Savings associated with"
        + " removing your gas connection and gas bottle rental",
        "checkbox_greyed_out": True,
        "checkbox_default_on": False,
    },
}
