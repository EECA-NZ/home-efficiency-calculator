"""
Constants for heating energy calculations

Note: a 'documentation' excel workbook is to be created, and we
intend to add it into the repository and link to it from this
docstring.  Links to supporting literature will be added here.

"""

HEATING_DEGREE_DAYS = {
    "Northland": 1024,
    "Auckland": 1165,
    "Hamilton": 1710,
    "Bay of Plenty": 1274,
    "Rotorua": 2146,
    "Taupo": 2365,
    "New Plymouth": 1646,
    "East Coast": 1604,
    "Manawatu": 1821,
    "Wairarapa": 2100,
    "Wellington": 1930,
    "Nelson-Marlborough": 1912,
    "West Coast": 2416,
    "Christchurch": 2490,
    "Queenstown-Lakes": 3121,
    "Central Otago": 3164,
    "Dunedin": 2657,
    "Invercargill": 2937,
    "Unknown": 2000,
}

STANDARD_HOME_KWH_HEATING_DEMAND_PER_HEATING_DEGREE_DAY = 1.94

LIVING_AREA_FRACTION = 0.63

THERMAL_ENVELOPE_QUALITY = {
    "Not well insulated": 1.4,
    "Moderately insulated": 1.0,
    "Well insulated": 0.61,
}

HEATING_PERIOD_FACTOR = {
    "Morning (per day)": 0.04971,
    "Day (per day)": 0.07398,
    "Evening (per day)": 0.07201,
}

HEAT_PUMP_COP_BY_CLIMATE_ZONE = {
    "Northland": 4.94,
    "Auckland": 4.94,
    "Hamilton": 4.31,
    "Bay of Plenty": 4.78,
    "Rotorua": 4.25,
    "Taupo": 3.87,
    "New Plymouth": 4.70,
    "East Coast": 4.50,
    "Manawatu": 4.59,
    "Wairarapa": 3.99,
    "Wellington": 4.97,
    "Nelson-Marlborough": 4.46,
    "West Coast": 4.42,
    "Christchurch": 3.93,
    "Queenstown-Lakes": 3.61,
    "Central Otago": 3.30,
    "Dunedin": 4.65,
    "Invercargill": 4.30,
    "Unknown": 3.0,
}

HEATING_DAYS_PER_WEEK = {
    "Never": 0,
    "1-2 days a week": 1.5,
    "3-4 days a week": 3.5,
    "5-7 days a week": 6,
}

GAS_SPACE_HEATING_EFFICIENCY = 0.8

LPG_SPACE_HEATING_EFFICIENCY = 0.8

ELECTRIC_HEATER_SPACE_HEATING_EFFICIENCY = 1.0

LOG_BURNER_SPACE_HEATING_EFFICIENCY = 0.7
