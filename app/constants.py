"""
Constants used in the calculations
"""

DAYS_IN_YEAR = 365.25

AVERAGE_HOUSEHOLD_SIZE = 2.69

SOLAR_RESOURCE_KWH_PER_DAY = {
    "Northland": 25.0,
    "Auckland": 25.0,
    "Hamilton": 25.0,
    "Bay of Plenty": 25.0,
    "Rotorua": 25.0,
    "Taupo": 25.0,
    "New Plymouth": 25.0,
    "East Coast": 25.0,
    "Manawatu": 25.0,
    "Wairarapa": 25.0,
    "Wellington": 25.0,
    "Nelson-Marlborough": 25.0,
    "West Coast": 25.0,
    "Christchurch": 25.0,
    "Queenstown-Lakes": 25.0,
    "Central Otago": 25.0,
    "Dunedin": 25.0,
    "Invercargill": 25.0,
    "Unknown": 25.0,
}

EMISSIONS_FACTORS = {
    "electricity": 0.077,
    "natural_gas": 0.195,
    "lpg": 0.214,
    "petrol": 2.41,
    "diesel": 2.67,
}

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
    "Morning (per day)": 0.050,
    "Day (per day)": 0.074,
    "Evening (per day)": 0.072,
}

HEAT_PUMP_COP_BY_CLIMATE_ZONE = {
    "Northland": 3.0,
    "Auckland": 3.0,
    "Hamilton": 3.0,
    "Bay of Plenty": 3.0,
    "Rotorua": 3.0,
    "Taupo": 3.0,
    "New Plymouth": 3.0,
    "East Coast": 3.0,
    "Manawatu": 3.0,
    "Wairarapa": 3.0,
    "Wellington": 3.0,
    "Nelson-Marlborough": 3.0,
    "West Coast": 3.0,
    "Christchurch": 3.0,
    "Queenstown-Lakes": 3.0,
    "Central Otago": 3.0,
    "Dunedin": 3.0,
    "Invercargill": 3.0,
    "Unknown": 3.0,
}

HEATING_DAYS_PER_WEEK = {
    "Never": 0,
    "1-2 days a week": 1.5,
    "3-4 days a week": 3.5,
    "5-7 days a week": 6,
}
