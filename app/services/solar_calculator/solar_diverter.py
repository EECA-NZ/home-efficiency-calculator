"""
This module provides a function to simulate
the operation of a hot water diverter, which
shifts excess solar energy into a hot water
cylinder while maintaining thermal balance.
The same logic is applied to hot water heat
pumps, on the basis that similar behaviour
can be obtained with a smart controller.
"""

# pylint: disable=too-few-public-methods, too-many-locals
# pylint: disable=too-many-arguments, too-many-positional-arguments

import numpy as np

from app.constants.hot_water_energy import HOT_WATER_POWER_INPUT_KW
from app.models.usage_profiles import ElectricityUsage, SolarGeneration
from app.services.usage_calculation.hot_water_helpers import (
    HEAT_PUMP_WATER_CYLINDER_SIZES,
    TANK_SIZE_BY_HOUSEHOLD_SIZE,
    hot_water_heating_efficiency,
)

HOURS_IN_YEAR = 8760


class HotWaterDiverterResult:
    """
    Class to hold the results of the hot water diverter simulation.
    """

    def __init__(
        self,
        load_profile: np.ndarray,
        rebuilt_hot_water_load: np.ndarray,
        tank_energy_state: np.ndarray,
    ):
        self.load_profile = load_profile
        self.rebuilt_hot_water_load = rebuilt_hot_water_load
        self.tank_energy_state = tank_energy_state


def apply_solar_diverter_energy_model(
    load_hw_kwh: np.ndarray,
    load_less_hw_kwh: np.ndarray,
    solar_generation_kwh: np.ndarray,
    non_hw_electricity_demand: np.ndarray,
    cylinder_volume_litres: int,
    system_power_kw: float,
    heating_efficiency: float,
) -> HotWaterDiverterResult:
    """
    Simulates a hot water diverter that shifts
    exportable solar into a hot water cylinder,
    while preserving thermal balance and
    optionally reheating at night.

    Parameters:
    - load_hw_kwh: original hot water electricity usage
        (np.ndarray of shape [8760])
    - load_less_hw_kwh: rest of household load profile
        excluding hot water (np.ndarray of shape [8760])
    - solar_generation_kwh: solar generation profile
        (np.ndarray of shape [8760])
    - non_hw_electricity_demand: full non-HW electricity
        usage (np.ndarray of shape [8760])
    - cylinder_volume_litres: tank size in litres
    - system_power_kw: rated power of hot water system (kW)
    - heating_efficiency: COP of the hot water system

    Returns:
    - HotWaterDiverterResult containing the new demand
        profile and tank state over time.
    """
    assert (
        len(load_hw_kwh) == HOURS_IN_YEAR
        and len(load_less_hw_kwh) == HOURS_IN_YEAR
        and len(solar_generation_kwh) == HOURS_IN_YEAR
        and len(non_hw_electricity_demand) == HOURS_IN_YEAR
    )

    exported_energy_kwh = np.maximum(
        0, solar_generation_kwh - non_hw_electricity_demand
    )

    kg_per_litre = 1.000028
    # kg/litre (density of water)
    specific_heat_j_per_kg_c = 4184
    # J/(kg*C)
    j_per_kwh = 3.6e6
    k = j_per_kwh / (kg_per_litre * specific_heat_j_per_kg_c)
    # C per kWh per litre

    t_min = 40
    t_min_to_raise = 40.5
    t_max = 73
    t_init = 60

    max_tank_energy = (t_max - t_min) * cylinder_volume_litres / k
    min_to_raise_energy = (t_min_to_raise - t_min) * cylinder_volume_litres / k
    init_tank_energy = (t_init - t_min) * cylinder_volume_litres / k

    tank_energy = init_tank_energy
    rebuilt_hw_load = np.zeros(HOURS_IN_YEAR)
    tank_energy_state = np.zeros(HOURS_IN_YEAR)

    for hour in range(HOURS_IN_YEAR):
        tank_energy -= load_hw_kwh[hour]

        if exported_energy_kwh[hour] > 0 and tank_energy < max_tank_energy:
            available = min(
                exported_energy_kwh[hour],
                max_tank_energy - tank_energy,
                system_power_kw,
            )
            rebuilt_hw_load[hour] += available
            tank_energy += available * heating_efficiency

        if tank_energy <= 0:
            top_up = min_to_raise_energy - tank_energy
            rebuilt_hw_load[hour] += top_up
            tank_energy = min_to_raise_energy

        tank_energy_state[hour] = tank_energy

    new_load_profile = load_less_hw_kwh + rebuilt_hw_load

    return HotWaterDiverterResult(
        load_profile=new_load_profile,
        rebuilt_hot_water_load=rebuilt_hw_load,
        tank_energy_state=tank_energy_state,
    )


def reroute_hot_water_to_solar_if_applicable(
    hw_electricity_kwh: ElectricityUsage,
    solar_generation_kwh: SolarGeneration,
    other_electricity_kwh: ElectricityUsage,
    hot_water_heating_source: str,
    household_size: int,
    climate_zone: str,
    system_power_kw: float = HOT_WATER_POWER_INPUT_KW,
) -> ElectricityUsage:
    """
    Adjust hot water electricity usage profile to maximize solar self-consumption.

    Returns a new ElectricityUsage object with the same total energy but
    a profile reshaped to align with exportable solar.
    """
    cylinder_volume_litres = HEAT_PUMP_WATER_CYLINDER_SIZES[
        TANK_SIZE_BY_HOUSEHOLD_SIZE[household_size]
    ]
    heating_efficiency = hot_water_heating_efficiency(
        hot_water_heating_source, climate_zone
    )

    total_hw_kwh = hw_electricity_kwh.annual_kwh
    fixed_day_khw = hw_electricity_kwh.fixed_day_kwh
    shift_abl_kwh = hw_electricity_kwh.shift_abl_kwh

    if total_hw_kwh == 0 or solar_generation_kwh is None:
        return hw_electricity_kwh

    other_demand_ts = other_electricity_kwh.total_usage

    result = apply_solar_diverter_energy_model(
        load_hw_kwh=hw_electricity_kwh.total_usage,
        load_less_hw_kwh=other_demand_ts,
        solar_generation_kwh=solar_generation_kwh.timeseries,
        non_hw_electricity_demand=other_demand_ts,
        cylinder_volume_litres=cylinder_volume_litres,
        system_power_kw=system_power_kw,
        heating_efficiency=heating_efficiency,
    )

    if result.rebuilt_hot_water_load.sum() == 0:
        return hw_electricity_kwh

    profile = result.rebuilt_hot_water_load / result.rebuilt_hot_water_load.sum()

    return ElectricityUsage(
        fixed_day_kwh=fixed_day_khw,
        fixed_ngt_kwh=0.0,
        shift_abl_kwh=shift_abl_kwh,
        fixed_profile=profile,
        shift_profile=profile,
    )
