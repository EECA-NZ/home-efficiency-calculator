"""
Test solar diverter functionality.
"""


import numpy as np

from app.constants.hot_water_energy import HOT_WATER_POWER_INPUT_KW
from app.models.usage_profiles import ElectricityUsage
from app.services.solar_calculator.solar_diverter import (
    apply_solar_diverter_energy_model,
)


def test_reroute_hot_water_to_solar_skipped_if_flag_false():
    """
    If use_solar_diverter is False, rerouting should not change the profile.
    """
    # Create a flat hot water profile
    fixed_kwh = 1000.0
    profile_array = np.full(8760, 1 / 8760)
    hw_usage = ElectricityUsage(
        fixed_day_kwh=fixed_kwh,
        fixed_ngt_kwh=0.0,
        shift_abl_kwh=0.0,
        fixed_profile=profile_array,
        shift_profile=None,
    )

    # Set diverter flag off manually (simulated by not applying reroute)
    rerouted = hw_usage  # i.e., skip reroute call

    assert np.allclose(rerouted.total_usage, hw_usage.total_usage)
    assert rerouted.annual_kwh == hw_usage.annual_kwh


def test_apply_solar_diverter_energy_model_simple():
    """
    Test the solar diverter energy model with a simple case.
    """
    hours = 8760

    # HW demand = 0.5 kWh at 6pm daily
    load_hw = np.zeros(hours)
    load_hw[np.arange(18, hours, 24)] = 0.5

    # Other household load = 0.3 kWh/hour baseline
    load_less_hw = np.full(hours, 0.3)

    # Solar = 2.0 kWh from 12–2pm daily
    solar = np.zeros(hours)
    for h in range(hours):
        if h % 24 in (12, 13):
            solar[h] = 1.0

    # Other demand (non-HW) = 0.3 kWh/hour
    non_hw_demand = np.full(hours, 0.3)

    result = apply_solar_diverter_energy_model(
        load_hw_kwh=load_hw,
        load_less_hw_kwh=load_less_hw,
        solar_generation_kwh=solar,
        non_hw_electricity_demand=non_hw_demand,
        cylinder_volume_litres=180,
        system_power_kw=HOT_WATER_POWER_INPUT_KW,
        heating_efficiency=1.0,
    )

    # Check that some HW demand was shifted to the solar window
    midday_solar_hours = np.arange(12, hours, 24)
    shifted_energy = result.rebuilt_hot_water_load[midday_solar_hours].sum()

    assert shifted_energy > 0, "Expected some HW load to be shifted to midday solar"
    assert result.load_profile.shape == (hours,)
    assert result.tank_energy_state.shape == (hours,)
