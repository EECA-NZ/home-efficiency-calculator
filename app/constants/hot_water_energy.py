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
HOT_WATER_FLEXIBLE_KWH_FRACTION = 0.8

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

HPWH_REFERENCE_CLIMATE_ZONE = "Wairarapa"
HPWH_BASELINE_COP = 3.5
HPWH_CLIMATE_COP_DERATE_FACTOR = 0.5

# The 2026 HPWH update uses the same climate ordering as the earlier
# water-heating model, but de-rates the climate spread relative to
# air-to-air heat pump performance by climate zone.
AIR_TO_AIR_HEAT_PUMP_COP_BY_CLIMATE_ZONE = {
    "Northland": 4.937402580645153,
    "Auckland": 4.938623225806459,
    "Hamilton": 4.306072258064516,
    "Bay of Plenty": 4.783739354838718,
    "Rotorua": 4.2536709677419395,
    "Taupo": 3.874429677419356,
    "New Plymouth": 4.702352258064507,
    "East Coast": 4.5019612903225745,
    "Manawatu": 4.593669677419356,
    "Wairarapa": 3.991598709677423,
    "Wellington": 4.965360000000005,
    "Nelson-Marlborough": 4.45849032258065,
    "West Coast": 4.417089032258067,
    "Christchurch": 3.9340180645161253,
    "Queenstown-Lakes": 3.605394838709677,
    "Central Otago": 3.3033806451612913,
    "Dunedin": 4.646802580645164,
    "Invercargill": 4.304938064516125,
}

HPWH_OUTDOOR_FITTINGS_HEAT_LOSS_MULTIPLIER = 1.0
HPWH_BASELINE_FITTINGS_HEAT_LOSS_KWH_PER_DAY = 0.4
HPWH_BASELINE_CYLINDER_HEAT_LOSS_KWH_PER_DAY_BY_TANK_SIZE = {
    170: 3.0896966368039278,
    250: 3.5037626898851557,
    300: 3.718396418165106,
}


def parameterized_hpwh_cop_from_air_to_air_climate_cop(
    air_to_air_heat_pump_cop: float,
    reference_air_to_air_heat_pump_cop: float,
    baseline_hpwh_cop: float,
    climate_cop_derate_factor: float,
) -> float:
    """
    Convert an air-to-air heat-pump climate COP into a HPWH component COP.

    The 2026 model retains the relative climate ordering from the prior
    water-heating model, but only applies part of that spread.
    """
    climate_ratio = air_to_air_heat_pump_cop / reference_air_to_air_heat_pump_cop
    derated_ratio = 1 + climate_cop_derate_factor * (climate_ratio - 1)
    return baseline_hpwh_cop * derated_ratio


def hpwh_cop_from_air_to_air_climate_cop(
    air_to_air_heat_pump_cop: float,
) -> float:
    """
    Convert an air-to-air heat-pump climate COP into the app's HPWH COP.
    """
    reference_air_to_air_heat_pump_cop = AIR_TO_AIR_HEAT_PUMP_COP_BY_CLIMATE_ZONE[
        HPWH_REFERENCE_CLIMATE_ZONE
    ]
    return parameterized_hpwh_cop_from_air_to_air_climate_cop(
        air_to_air_heat_pump_cop=air_to_air_heat_pump_cop,
        reference_air_to_air_heat_pump_cop=reference_air_to_air_heat_pump_cop,
        baseline_hpwh_cop=HPWH_BASELINE_COP,
        climate_cop_derate_factor=HPWH_CLIMATE_COP_DERATE_FACTOR,
    )


def build_hpwh_cop_by_climate_zone() -> dict[str, float]:
    """
    Build the 2026 HPWH component COP map from explicit model assumptions.
    """
    climate_zone_cops = {
        climate_zone: hpwh_cop_from_air_to_air_climate_cop(air_to_air_heat_pump_cop)
        for climate_zone, air_to_air_heat_pump_cop in (
            AIR_TO_AIR_HEAT_PUMP_COP_BY_CLIMATE_ZONE.items()
        )
    }
    climate_zone_cops["Unknown"] = HPWH_BASELINE_COP
    return climate_zone_cops


HOT_WATER_HEAT_PUMP_COP_BY_CLIMATE_ZONE = build_hpwh_cop_by_climate_zone()

GAS_INSTANTANEOUS_WATER_HEATING_EFFICIENCY = 0.834

GAS_STORAGE_WATER_HEATING_EFFICIENCY = 0.885

ELECTRIC_WATER_HEATING_EFFICIENCY = 1.0

HOT_WATER_POWER_INPUT_KW = 3.0  # kW, assumed for all hot water systems


#### Constants used for hot water hourly energy consumption profiles

# Default time window constants
SOLAR_WINDOW_START = "09:00:00"  # e.g., start of solar energy heating window
SOLAR_WINDOW_END = "18:00:00"  # e.g., end of solar energy heating window (9 hours)
NIGHT_WINDOW_START = "21:00:00"  # e.g., start of night heating window
NIGHT_WINDOW_END = "09:00:00"  # e.g., end of night heating window (next day; 12 hours)

HEATING_WINDOWS = {
    "solar": (SOLAR_WINDOW_START, SOLAR_WINDOW_END),
    "night": (NIGHT_WINDOW_START, NIGHT_WINDOW_END),
}

CYLINDER_HOT_WATER_TEMPERATURE = 65  # Celsius - typical hot water temperature.
DELIVERED_HOT_WATER_TEMPERATURE = 40  # Celsius - typical demand temperature.
# Although the tank is at 65°C, hot water at the tap is usually 40°C via mixing.
# The fraction drawn from the tank is given by (40 - T_inlet) / (65 - T_inlet),
# and the heating per kg to heat from T_inlet to 65°C is proportional to (65 - T_inlet).
# After multiplying fraction by energy per kg, the (65 - T_inlet) terms cancel out.
# Hence, the total heating demand is effectively proportional to (40 - T_inlet).

COP_CALCULATION = "constant"  # Use an annual average COP per climate zone
