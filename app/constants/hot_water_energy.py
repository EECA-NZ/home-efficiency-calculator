"""
Constants for hot water energy calculations

Note: a 'documentation' excel workbook is to be created, and we
intend to add it into the repository and link to it from this
docstring. Links to supporting literature will be added here.

"""

WATER_SPECIFIC_HEAT_CAPACITY_KWH_PER_KG_K = 0.001162

WATER_DENSITY_KG_PER_L = 1

TEMPERATURE_SHOWER_C = 37

# If hot water is provided by electriciy, this is the fraction of the total
# hot water energy that is assumed can be provided using the night rate.
# In order to work within the constraints imposed by the lookup table approach
# for solar self-consumption calculations, this is set to 1.0 for now.
HOT_WATER_FLEXIBLE_KWH_FRACTION = 1.0

SHOWER_WATER_USAGE_QUANTITIES = {
    "Low": {"showers_per_week": 5, "flow_rate_l_per_min": 5, "duration_min": 5},
    "Average": {"showers_per_week": 6, "flow_rate_l_per_min": 7, "duration_min": 7},
    "High": {"showers_per_week": 7, "flow_rate_l_per_min": 9, "duration_min": 9},
}

OTHER_WATER_USAGE_QUANTITIES = {
    "Washing Machine": {"volume_l_per_day": 10.4038461538462, "temperature": 35},
    "Tap": {"volume_l_per_day": 8.90384615384615, "temperature": 40},
    "High Flow/Outdoor": {"volume_l_per_day": 4.19230769230769, "temperature": 37},
}

AVERAGE_AIR_TEMPERATURE_BY_CLIMATE_ZONE = {
    "Northland": 15.52020547945,
    "Auckland": 15.27431506849,
    "Hamilton": 13.53675799087,
    "Bay of Plenty": 14.93299086758,
    "Rotorua": 12.18413242009,
    "Taupo": 11.66655251142,
    "New Plymouth": 13.59429223744,
    "East Coast": 14.02089041096,
    "Manawatu": 13.15502283105,
    "Wairarapa": 12.44212328767,
    "Wellington": 12.83401826484,
    "Nelson-Marlborough": 12.90593607306,
    "West Coast": 11.41369863014,
    "Christchurch": 11.32351598174,
    "Queenstown-Lakes": 9.49691780822,
    "Central Otago": 9.45582191781,
    "Dunedin": 10.78824200913,
    "Invercargill": 9.99029680365,
}

# Assume that ground temperature and inlet water temperature track air temperature
INLET_WATER_TEMPERATURE_BY_CLIMATE_ZONE = AVERAGE_AIR_TEMPERATURE_BY_CLIMATE_ZONE

HOT_WATER_STORAGE_TEMPERATURE_C = 65

# Consistent with what is used by MBIE in building code calculations
INDOOR_CYLINDER_AMBIENT_TEMPERATURE_C = 18

TANK_SIZE_BY_HOUSEHOLD_SIZE = {
    1: "Small",
    2: "Small",
    3: "Medium",
    4: "Medium",
    5: "Large",
    6: "Large",
}

ELECTRIC_HOT_WATER_CYLINDER_LOSSES_55_DEGREE_DELTA_T_KWH_PER_DAY = {
    130: 1.56,
    180: 1.76,
    250: 2.16,
}

ELECTRIC_HOT_WATER_CYLINDER_SIZES = {
    "Small": 130,
    "Medium": 180,
    "Large": 250,
}

GAS_HOT_WATER_CYLINDER_SIZES = {
    "Small": 130,
    "Medium": 180,
    "Large": 260,
}

HEAT_PUMP_WATER_CYLINDER_SIZES = {
    "Small": 170,
    "Medium": 250,
    "Large": 300,
}

HOT_WATER_HEAT_PUMP_COP_BY_CLIMATE_ZONE = {
    "Northland": 4.12,
    "Auckland": 4.12,
    "Hamilton": 3.60,
    "Bay of Plenty": 3.99,
    "Rotorua": 3.55,
    "Taupo": 3.24,
    "New Plymouth": 3.93,
    "East Coast": 3.76,
    "Manawatu": 3.84,
    "Wairarapa": 3.33,
    "Wellington": 4.15,
    "Nelson-Marlborough": 3.72,
    "West Coast": 3.69,
    "Christchurch": 3.29,
    "Queenstown-Lakes": 3.01,
    "Central Otago": 2.76,
    "Dunedin": 3.88,
    "Invercargill": 3.59,
    "Unknown": 3.0,
}

GAS_INSTANTANEOUS_WATER_HEATING_EFFICIENCY = 0.834

GAS_STORAGE_WATER_HEATING_EFFICIENCY = 0.885

ELECTRIC_WATER_HEATING_EFFICIENCY = 1.0

HOT_WATER_POWER_INPUT_KW = 3.0  # kW, assumed for all hot water systems
