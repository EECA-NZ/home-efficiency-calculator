"""
Constants for driving cost and energy calculations

Note: a 'documentation' excel workbook is to be created, and we
intend to add it into the repository and link to it from this
docstring. Links to supporting literature will be added here.

"""

EV_PUBLIC_CHARGING_FRACTION = 0.2

FUEL_CONSUMPTION_LITRES_PER_100KM = {
    "Petrol": {"Small": 8, "Medium": 8, "Large": 8},
    "Diesel": {"Small": 8, "Medium": 8, "Large": 8},
    "Hybrid": {"Small": 5, "Medium": 5, "Large": 5},
    "Plug-in hybrid": {"Small": 1, "Medium": 1, "Large": 1},
    "Electric": {"Small": 0, "Medium": 0, "Large": 0},
}

BATTERY_ECONOMY_KWH_PER_100KM = {
    "Petrol": {"Small": 0, "Medium": 0, "Large": 0},
    "Diesel": {"Small": 0, "Medium": 0, "Large": 0},
    "Hybrid": {"Small": 0, "Medium": 0, "Large": 0},
    "Plug-in hybrid": {"Small": 17.5, "Medium": 17.5, "Large": 17.5},
    "Electric": {"Small": 17.5, "Medium": 17.5, "Large": 17.5},
}

ASSUMED_DISTANCES_PER_WEEK = {
    "50 or less": 50,
    "100": 100,
    "200": 200,
    "300": 300,
    "400 or more": 400,
}
