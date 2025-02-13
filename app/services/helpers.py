"""
Module for generic helper functions.
"""

import numpy as np
from pydantic import BaseModel

from app.models.usage_profiles import (
    ElectricityUsage,
    HouseholdOtherElectricityUsageProfile,
)

from ..constants import (
    AVERAGE_AIR_TEMPERATURE_BY_CLIMATE_ZONE,
    DAY_NIGHT_FRAC,
    DAYS_IN_YEAR,
    ELECTRIC_HOT_WATER_CYLINDER_LOSSES_55_DEGREE_DELTA_T_KWH_PER_DAY,
    ELECTRIC_HOT_WATER_CYLINDER_SIZES,
    ELECTRIC_WATER_HEATING_EFFICIENCY,
    GAS_HOT_WATER_CYLINDER_SIZES,
    GAS_INSTANTANEOUS_WATER_HEATING_EFFICIENCY,
    GAS_STORAGE_WATER_HEATING_EFFICIENCY,
    HEAT_PUMP_WATER_CYLINDER_SIZES,
    HEATING_PERIOD_FACTOR,
    HOT_WATER_HEAT_PUMP_COP_BY_CLIMATE_ZONE,
    HOT_WATER_STORAGE_TEMPERATURE_C,
    INDOOR_CYLINDER_AMBIENT_TEMPERATURE_C,
    INLET_WATER_TEMPERATURE_BY_CLIMATE_ZONE,
    OTHER_ELX_KWH_PER_DAY,
    OTHER_WATER_USAGE_QUANTITIES,
    SHOWER_WATER_USAGE_QUANTITIES,
    TANK_SIZE_BY_HOUSEHOLD_SIZE,
    TEMPERATURE_SHOWER_C,
    WATER_DENSITY_KG_PER_L,
    WATER_SPECIFIC_HEAT_CAPACITY_KWH_PER_KG_K,
)


def answer_options(my_object, field):
    """
    For a given field on a pydantic model, return the possible answer options.
    """
    return type(my_object).model_fields[field].annotation.__args__


def heating_frequency_factor(heating_days_per_week):
    """
    Calculate the heating frequency factor based on the number of heating days per week.
    Assumes that heating occurs every morning and evening.
    Daytime heating is based on the response to the question
    "How often do you heat your home during the day?".

    Parameters
    ----------
    heating_days_per_week : float
        The number of days per week that heating occurs.

    Returns
    -------
    float
        The heating frequency factor.
    """
    heating_mornings = 7
    heating_evenings = 7
    return (
        HEATING_PERIOD_FACTOR["Morning (per day)"] * heating_mornings
        + HEATING_PERIOD_FACTOR["Day (per day)"] * heating_days_per_week
        + HEATING_PERIOD_FACTOR["Evening (per day)"] * heating_evenings
    )


def add_gst(plan: BaseModel) -> BaseModel:
    """
    Adjust all cost-related fields in a plan by adding 15% GST.
    Don't alter the original plan object but manipulate a copy.
    """
    gst_rate = 1.15
    plancopy = plan.model_copy()
    for field, value in plan.model_dump().items():
        if isinstance(value, dict):
            # Apply GST to each value in the dictionary
            adjusted_dict = {k: v * gst_rate for k, v in value.items()}
            setattr(plancopy, field, adjusted_dict)
        elif "charge" in field or "per_" in field:
            # Apply GST to flat rate fields
            setattr(plancopy, field, value * gst_rate)
    return plancopy


def round_floats_to_2_dp(dictionary):
    """
    Round all floats in a dictionary to 2 decimal places.
    Recursively rounds floats in nested dictionaries.
    """
    for key, value in dictionary.items():
        if isinstance(value, float):
            dictionary[key] = round(value, 2)
        elif isinstance(value, dict):
            round_floats_to_2_dp(value)
    return dictionary


def safe_percentage_reduction(current: float, alternative: float) -> float:
    """
    Safely calculate percentage reduction from current to alternative values.
    Handles cases where current is zero to avoid division by zero errors.
    """
    if current == 0:
        return np.nan if alternative != 0 else 0
    return 100 * (current - alternative) / current


def hot_water_heating_kwh(volume_rate, delta_t):
    """
    Calculate the energy usage based on volume and temperature difference.

    Parameters:
    - volume_rate: Litres per unit time (e.g. daily).
    - delta_t: Temperature difference the water is heated over.

    Returns:
    - Energy used in kWh.
    """
    return (
        volume_rate
        * delta_t
        * WATER_DENSITY_KG_PER_L
        * WATER_SPECIFIC_HEAT_CAPACITY_KWH_PER_KG_K
    )


def shower_kwh_per_year(hot_water_usage, climate_zone, household_size):
    """
    Calculate total energy for showering based on usage scenario.

    Parameters:
    - hot_water_usage: User's usage category ('Low', 'Medium', 'High').
    - temperature_inlet: Inlet water temperature.
    - household_size: Number of occupants in the household.

    Returns:
    - Total energy used for showering in kWh/year.
    """
    temperature_inlet = INLET_WATER_TEMPERATURE_BY_CLIMATE_ZONE[climate_zone]
    scenario = SHOWER_WATER_USAGE_QUANTITIES[hot_water_usage]
    delta_t = TEMPERATURE_SHOWER_C - temperature_inlet
    volume_per_shower = scenario["flow_rate_l_per_min"] * scenario["duration_min"]
    daily_volume_per_occupant = volume_per_shower * scenario["showers_per_week"] / 7
    yearly_volume_per_occupant = daily_volume_per_occupant * DAYS_IN_YEAR
    return household_size * hot_water_heating_kwh(yearly_volume_per_occupant, delta_t)


def other_water_kwh_per_year(climate_zone, household_size):
    """
    Calculate total energy for other water usage based on usage scenario.

    Parameters:
    - climate_zone: The climate zone of the household.

    Returns:
    - Total energy used for other water usage in kWh/year.
    """
    temperature_inlet = INLET_WATER_TEMPERATURE_BY_CLIMATE_ZONE[climate_zone]

    washing_machine_litres_per_year = (
        DAYS_IN_YEAR
        * OTHER_WATER_USAGE_QUANTITIES["Washing Machine"]["volume_l_per_day"]
    )
    washing_machine_delta_t = (
        OTHER_WATER_USAGE_QUANTITIES["Washing Machine"]["temperature"]
        - temperature_inlet
    )
    washing_machine_kwh_per_occupant_per_year = hot_water_heating_kwh(
        washing_machine_litres_per_year, washing_machine_delta_t
    )

    tap_litres = DAYS_IN_YEAR * OTHER_WATER_USAGE_QUANTITIES["Tap"]["volume_l_per_day"]
    tap_delta_t = OTHER_WATER_USAGE_QUANTITIES["Tap"]["temperature"] - temperature_inlet
    tap_kwh_per_occupant_per_year = hot_water_heating_kwh(tap_litres, tap_delta_t)

    high_flow_outdoor_litres = (
        DAYS_IN_YEAR
        * OTHER_WATER_USAGE_QUANTITIES["High Flow/Outdoor"]["volume_l_per_day"]
    )
    high_flow_outdoor_delta_t = (
        OTHER_WATER_USAGE_QUANTITIES["High Flow/Outdoor"]["temperature"]
        - temperature_inlet
    )
    high_flow_outdoor_kwh_per_occupant_per_year = hot_water_heating_kwh(
        high_flow_outdoor_litres, high_flow_outdoor_delta_t
    )

    other_kwh_per_year = household_size * (
        washing_machine_kwh_per_occupant_per_year
        + tap_kwh_per_occupant_per_year
        + high_flow_outdoor_kwh_per_occupant_per_year
    )

    return other_kwh_per_year


def standing_loss_kwh_per_year(hot_water_heating_source, household_size, climate_zone):
    """
    Calculate the standing loss for the hot water cylinder.

    Parameters:
    - household_size: Number of occupants in the household.
    - hot_water_heating_source: The source of hot water heating.

    Returns:
    - Standing loss in kWh/year.
    """
    tank_description = TANK_SIZE_BY_HOUSEHOLD_SIZE[household_size]
    outdoor_delta_t = (
        HOT_WATER_STORAGE_TEMPERATURE_C
        - AVERAGE_AIR_TEMPERATURE_BY_CLIMATE_ZONE[climate_zone]
    )
    indoor_delta_t = (
        HOT_WATER_STORAGE_TEMPERATURE_C - INDOOR_CYLINDER_AMBIENT_TEMPERATURE_C
    )
    if hot_water_heating_source == "Electric hot water cylinder":
        return (
            hot_water_cylinder_heat_loss_kwh_per_day(
                ELECTRIC_HOT_WATER_CYLINDER_SIZES[tank_description], indoor_delta_t
            )
            * DAYS_IN_YEAR
        )
    if hot_water_heating_source == "Piped gas hot water cylinder":
        return (
            gas_storage_heat_loss_kwh_per_day(
                GAS_HOT_WATER_CYLINDER_SIZES[tank_description], indoor_delta_t
            )
            * DAYS_IN_YEAR
        )
    if hot_water_heating_source == "Hot water heat pump":
        return (
            heat_pump_cylinder_heat_loss_kwh_per_day(
                HEAT_PUMP_WATER_CYLINDER_SIZES[tank_description], outdoor_delta_t
            )
            * DAYS_IN_YEAR
        )
    return 0


def hot_water_heating_efficiency(hot_water_heating_source, climate_zone):
    """
    Calculate the heating efficiency of the hot water heating system.
    Does not account for standing losses, which are calculated separately.

    Parameters:
    - hot_water_heating_source: The source of hot water heating.
    - climate_zone: The climate zone of the household.

    Returns:
    - Energy conversion efficiency of the hot water heating system.
    """
    if hot_water_heating_source == "Electric hot water cylinder":
        return ELECTRIC_WATER_HEATING_EFFICIENCY
    if hot_water_heating_source == "Piped gas hot water cylinder":
        return GAS_STORAGE_WATER_HEATING_EFFICIENCY
    if hot_water_heating_source == "Piped gas instantaneous":
        return GAS_INSTANTANEOUS_WATER_HEATING_EFFICIENCY
    if hot_water_heating_source == "Bottled gas instantaneous":
        return GAS_INSTANTANEOUS_WATER_HEATING_EFFICIENCY
    if hot_water_heating_source == "Hot water heat pump":
        return HOT_WATER_HEAT_PUMP_COP_BY_CLIMATE_ZONE[climate_zone]
    raise ValueError(f"Unknown hot water heating source: {hot_water_heating_source}")


def hot_water_cylinder_heat_loss_kwh_per_day(tank_size, delta_t=55):
    """
    Calculate the heat loss for a hot water cylinder.
    Based on MEPS level with TPR valve 4692.
    This was based on a 55 degree temperature rise; correct with
    linear scaling if another delta T is appropriate.

    Parameters:
    - tank_size: The size of the hot water cylinder in litres.
    - delta_t: Temperature difference between hot water and ambient.

    Returns:
    - The heat loss in kWh/day.
    """
    if (
        tank_size
        not in ELECTRIC_HOT_WATER_CYLINDER_LOSSES_55_DEGREE_DELTA_T_KWH_PER_DAY
    ):
        raise ValueError(f"Unknown tank size: {tank_size}")
    return ELECTRIC_HOT_WATER_CYLINDER_LOSSES_55_DEGREE_DELTA_T_KWH_PER_DAY.get(
        tank_size
    ) * (delta_t / 55)


def gas_storage_heat_loss_kwh_per_day(tank_size, delta_t=55):
    """
    Calculate the heat loss for a gas storage hot water cylinder.
    6.9.2 based on AS/NZS 4552.2:2010, 45 degree temperature rise,
    corrected to 55 degree temp rise by default; correct with
    linear scaling if another delta T is appropriate.

    (Assumed 30 MJ nominal gas consumption)

    Parameters:
    - tank_size: The size of the hot water cylinder in litres.
    - delta_t: Temperature difference between hot water and ambient.

    Returns:
    - The heat loss in kWh/day.
    """
    return (
        (0.42 + 0.02 * (tank_size ** (2 / 3)) + 0.006 * 30) * 24 / 3.6 * (delta_t / 45)
    )


def heat_pump_cylinder_heat_loss_kwh_per_day(tank_size, delta_t=55):
    """
    Calculate the heat loss for a heat pump hot water cylinder.
    Based on heat exchanger MEPS in AU 4692.
    - This was based on a 55 degree temperature rise; correct with
    linear scaling if another delta T is appropriate.
    - 0.2 added for TPR valve,
    - 0.2 added for two fittings.

    Parameters:
    - tank_size: The size of the hot water cylinder in litres.
    - delta_t: Temperature difference between hot water and ambient.

    Returns:
    - The heat loss in kWh/day.
    """
    return tank_size ** (0.3261) * 0.6099 * (delta_t / 55) + 0.2 + 0.2


def other_electricity_energy_usage_profile():
    """
    Create an electricity usage profile for appliances not considered by the app.

    Returns:
    - A HouseholdOtherElectricityUsageProfile object.
    """
    uncontrolled_day_kwh = DAYS_IN_YEAR * (
        OTHER_ELX_KWH_PER_DAY["Refrigeration"]["kWh/day"]
        * DAY_NIGHT_FRAC["Refrigeration"]["Day"]
        + OTHER_ELX_KWH_PER_DAY["Lighting"]["kWh/day"]
        * DAY_NIGHT_FRAC["Lighting"]["Day"]
        + OTHER_ELX_KWH_PER_DAY["Laundry"]["kWh/day"] * DAY_NIGHT_FRAC["Laundry"]["Day"]
        + OTHER_ELX_KWH_PER_DAY["Other"]["kWh/day"] * DAY_NIGHT_FRAC["Other"]["Day"]
    )
    uncontrolled_night_kwh = DAYS_IN_YEAR * (
        OTHER_ELX_KWH_PER_DAY["Refrigeration"]["kWh/day"]
        * DAY_NIGHT_FRAC["Refrigeration"]["Night"]
        + OTHER_ELX_KWH_PER_DAY["Lighting"]["kWh/day"]
        * DAY_NIGHT_FRAC["Lighting"]["Night"]
        + OTHER_ELX_KWH_PER_DAY["Laundry"]["kWh/day"]
        * DAY_NIGHT_FRAC["Laundry"]["Night"]
        + OTHER_ELX_KWH_PER_DAY["Other"]["kWh/day"] * DAY_NIGHT_FRAC["Other"]["Night"]
    )
    return HouseholdOtherElectricityUsageProfile(
        elx_connection_days=DAYS_IN_YEAR,
        day_kwh=ElectricityUsage(uncontrolled=uncontrolled_day_kwh),
        night_kwh=ElectricityUsage(uncontrolled=uncontrolled_night_kwh),
    )
