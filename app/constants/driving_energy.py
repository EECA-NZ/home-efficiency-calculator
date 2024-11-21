"""
Constants for driving cost and energy calculations

Note: a 'documentation' excel workbook is to be created, and we
intend to add it into the repository and link to it from this
docstring. Links to supporting literature will be added here.

"""

EV_PUBLIC_CHARGING_FRACTION = 0.2

GVM_BY_CATEGORY_KG = {
    "Petrol": {"Small": 1825.89, "Medium": 2214.90, "Large": 2607.37},
    "Diesel": {"Small": 1974.95, "Medium": 2386.50, "Large": 2801.70},
    "Hybrid": {"Small": 1861.14, "Medium": 2320.33, "Large": 2665.00},
    "Plug-in hybrid": {"Small": 2282.67, "Medium": 2511.69, "Large": 2808.60},
    "Electric": {"Small": 2282.82, "Medium": 2599.70, "Large": 2914.11},
}

FUEL_CONSUMPTION_MODEL_LITRES_PER_100KM = {
    "Petrol": {"Intercept": -1.1053901194698401, "Slope": 0.004533730312664287},
    "Diesel": {"Intercept": 1.440207858567132, "Slope": 0.002316240341029766},
    "Hybrid": {"Intercept": -0.6910042153218487, "Slope": 0.002706071645616522},
    "Plug-in hybrid": {
        "Intercept": 0.04854051481210342,
        "Slope": 0.0006574946902074077,
    },
    "Electric": {"Intercept": 0, "Slope": 0},
}

BATTERY_ECONOMY_MODEL_KWH_PER_100KM = {
    "Petrol": {"Intercept": 0, "Slope": 0},
    "Diesel": {"Intercept": 0, "Slope": 0},
    "Hybrid": {"Intercept": 0, "Slope": 0},
    "Plug-in hybrid": {"Intercept": -7.440745823105512, "Slope": 0.010746477952209942},
    "Electric": {"Intercept": 12.165713165367453, "Slope": 0.002511803639857288},
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
