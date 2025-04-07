"""
Module for generic helper functions.
"""

from typing import Tuple

import numpy as np


def compute_solar_offset(usage_profile) -> Tuple[float, float, float]:
    """
    Compute how much of the solar generation is self-consumed by
    the household (split into shiftable vs. fixed usage) and how much is exported.

    Returns
    -------
    (shift_self_consumption_kwh, fixed_self_consumption_kwh, export_kwh)
        shift_self_consumption_kwh: kWh of solar used by shiftable household loads
        fixed_self_consumption_kwh: kWh of solar used by fixed (day/night) loads
        export_kwh: kWh of solar exported to the grid
    """
    if (
        usage_profile.solar_generation_kwh is None
        or usage_profile.solar_generation_kwh.total == 0
    ):
        return (0.0, 0.0, 0.0)

    # Get the solar generation timeseries
    solar_ts = usage_profile.solar_generation_kwh.timeseries

    # Get the household electricity usage timeseries
    fixed_usage_ts = usage_profile.electricity_kwh.total_fixed_time_usage
    shift_usage_ts = usage_profile.electricity_kwh.total_shift_able_usage

    # First, offset fixed usage
    fixed_self_consumption_ts = np.minimum(fixed_usage_ts, solar_ts)
    residual_solar_ts = solar_ts - fixed_self_consumption_ts

    # Next, offset shiftable usage with leftover solar
    shift_self_consumption_ts = np.minimum(shift_usage_ts, residual_solar_ts)

    # Whatever remains is exported
    export_ts = np.maximum(0, residual_solar_ts - shift_usage_ts)

    export_kwh = float(export_ts.sum())
    shift_self_consumption_kwh = float(shift_self_consumption_ts.sum())
    fixed_self_consumption_kwh = float(fixed_self_consumption_ts.sum())

    return (shift_self_consumption_kwh, fixed_self_consumption_kwh, export_kwh)
