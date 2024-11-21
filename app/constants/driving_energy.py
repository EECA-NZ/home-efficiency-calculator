"""
Constants for driving cost and energy calculations

Note: a 'documentation' excel workbook is to be created, and we
intend to add it into the repository and link to it from this
docstring. Links to supporting literature will be added here.

"""

EV_PUBLIC_CHARGING_FRACTION = 0.2

GVM_BY_CATEGORY_KG = {
    "Petrol": {"Small": 1000, "Medium": 2000, "Large": 3000},
    "Diesel": {"Small": 1000, "Medium": 2000, "Large": 3000},
    "Hybrid": {"Small": 1000, "Medium": 2000, "Large": 3000},
    "Plug-in hybrid": {"Small": 1000, "Medium": 2000, "Large": 3000},
    "Electric": {"Small": 1000, "Medium": 2000, "Large": 3000},
}

FUEL_CONSUMPTION_MODEL_LITRES_PER_100KM = {
    "Petrol": {"Intercept": 8, "Slope": 0},
    "Diesel": {"Intercept": 8, "Slope": 0},
    "Hybrid": {"Intercept": 5, "Slope": 0},
    "Plug-in hybrid": {"Intercept": 1, "Slope": 0},
    "Electric": {"Intercept": 0, "Slope": 0},
}

BATTERY_ECONOMY_MODEL_KWH_PER_100KM = {
    "Petrol": {"Intercept": 0, "Slope": 0},
    "Diesel": {"Intercept": 0, "Slope": 0},
    "Hybrid": {"Intercept": 0, "Slope": 0},
    "Plug-in hybrid": {"Intercept": 17.5, "Slope": 0},
    "Electric": {"Intercept": 17.5, "Slope": 0},
}

FUEL_CONSUMPTION_LITRES_PER_100KM = {
    vehicle_type: {
        size: model["Intercept"] + model["Slope"] * gvm
        for size, gvm in GVM_BY_CATEGORY_KG[vehicle_type].items()
    }
    for vehicle_type, model in FUEL_CONSUMPTION_MODEL_LITRES_PER_100KM.items()
}

BATTERY_ECONOMY_KWH_PER_100KM = {
    vehicle_type: {
        size: model["Intercept"] + model["Slope"] * gvm
        for size, gvm in GVM_BY_CATEGORY_KG[vehicle_type].items()
    }
    for vehicle_type, model in BATTERY_ECONOMY_MODEL_KWH_PER_100KM.items()
}

ASSUMED_DISTANCES_PER_WEEK = {
    "50 or less": 50,
    "100": 100,
    "200": 200,
    "300": 300,
    "400 or more": 400,
}
