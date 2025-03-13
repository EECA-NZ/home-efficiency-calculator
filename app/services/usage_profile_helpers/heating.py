"""
Space heating profile calculation with heat pump COP logic.

We compute an hourly space heating demand profile for the postcode,
factoring in day-of-week scheduling and optional heat pump COP.

Demand is computed as: max(setpoint - T_outside, 0).
There is always heating in two baseline windows per day:
    - Morning: 7am–9am
    - Evening: 5pm–9pm
And optionally an "all-day" window (7am–9pm) for a certain number
of days per week, determined by the 'heating_during_day' parameter:

  - "Never"            => 0 full-day heating days per week
  - "1-2 days a week"  => 1 day in odd weeks, 2 in even weeks
  - "3-4 days a week"  => 3 days in odd weeks, 4 in even weeks
  - "5-7 days a week"  => 5 days in odd weeks, 7 in even weeks

If main_heating_source == "Heat pump", we reduce the required
energy by dividing by a COP timeseries. By default ("constant"),
this COP is taken from a dictionary keyed by climate zone.
If cop_calculation == "scaled_carnot_cop", we estimate a
scaled Carnot COP based on (21°C - T_outside).

Finally, we normalize to produce a shape factor summing to 1.
"""

import numpy as np
import pandas as pd

from ...constants import HEAT_PUMP_COP_BY_CLIMATE_ZONE
from ..get_climate_zone import climate_zone
from ..get_temperatures import hourly_ta
from .hot_water import carnot_cop

# Time window constants
FULL_DAY_WINDOW = (7, 21)  # "full day" means 7am–9pm
BASELINE_WINDOWS = [(7, 9), (17, 21)]  # "baseline" means 7–9am and 5–9pm

DEFAULT_THERMOSTAT_SETPOINT = 21.0


def _days_for_week(week_num: int, option: str) -> int:
    """
    Return how many "full-day heating" days are used in a given ISO week.

    Parameters
    ----------
    week_num : int
        The ISO week number (1..52 or 53).
    option : str
        One of: "Never", "1-2 days a week", "3-4 days a week", "5-7 days a week".

    Returns
    -------
    int
        Number of days in the given week for which the user wants
        all-day heating (7am–9pm).
    """
    if option == "1-2 days a week":
        return 1 if (week_num % 2 == 1) else 2
    if option == "3-4 days a week":
        return 3 if (week_num % 2 == 1) else 4
    if option == "5-7 days a week":
        return 5 if (week_num % 2 == 1) else 7
    return 0  # Default for "Never"


def _get_heating_cop_series(
    postcode: str,
    temperature_series: pd.Series,
    cop_calculation: str = "constant",
    setpoint: float = DEFAULT_THERMOSTAT_SETPOINT,
) -> pd.Series:
    """
    Return an hourly COP series for space heating.

    If cop_calculation == "constant", we use a single
    climate-zone-specific COP from HEAT_PUMP_COP_BY_CLIMATE_ZONE,
    repeated for every hour.

    If cop_calculation == "scaled_carnot_cop", we use
    carnot_cop(T_hot=setpoint, T_cold=outside_temperature) per hour
    and scale it so that its average matches the climate zone's
    annual COP from the dictionary.

    Parameters
    ----------
    postcode : str
        The postcode to derive the climate zone from.
    temperature_series : pd.Series
        Hourly outside temperatures (°C).
    cop_calculation : str
        "constant" or "scaled_carnot_cop".
    setpoint : float
        Desired indoor temperature in °C for Carnot COP calculation
        (default=21.0).

    Returns
    -------
    pd.Series
        A timeseries of COP values (>=1).
    """
    cz = climate_zone(postcode)
    annual_cop = HEAT_PUMP_COP_BY_CLIMATE_ZONE[cz]

    if cop_calculation == "constant":
        # Single numeric COP repeated
        return pd.Series(annual_cop, index=temperature_series.index, name="COP")

    if cop_calculation == "scaled_carnot_cop":
        # Compute the theoretical Carnot COP for each hour, then scale
        hourly_cop = temperature_series.apply(lambda t: carnot_cop(setpoint, t))
        # Scale so that the mean matches annual_cop
        scale_factor = annual_cop / hourly_cop.mean()
        return (hourly_cop * scale_factor).rename("COP")

    raise ValueError(f"Unknown cop_calculation: {cop_calculation}")


# pylint: disable=too-many-locals
def space_heating_profile(
    postcode: str,
    heating_during_day: str,
    setpoint: float = DEFAULT_THERMOSTAT_SETPOINT,
    main_heating_source: str = "Heat pump",
    cop_calculation: str = "constant",
) -> pd.Series:
    """
    Compute an hourly space heating demand profile for the specified postcode.

    Steps:
      1. Retrieve hourly outside temperatures via hourly_ta(postcode).
      2. Compute raw heating demand = max(setpoint - temperature, 0).
      3. If main_heating_source == "Heat pump", build a COP timeseries
         (either "constant" or "scaled_carnot_cop") and divide raw demand
         by that COP to get net electric demand. Otherwise, net electric
         demand = raw demand.
      4. Determine day scheduling: "baseline" (7–9am, 5–9pm) or
         "full-day" (7am–9pm) on certain days each week.
      5. Apply the active schedule to the net demand.
      6. Normalize so sum(demand) == 1.

    The number of "full-day" heating days per week is determined by
    'heating_during_day', which can be:
      - "Never"
      - "1-2 days a week"
      - "3-4 days a week"
      - "5-7 days a week"

    For each ISO week (week_num), we pick that many days
    in ascending date order to be "full-day" (7am–9pm).
    The rest remain on the baseline schedule.

    Parameters
    ----------
    postcode : str
        The postcode used by hourly_ta() to retrieve outside temps
        and by climate_zone() to retrieve the climate zone.
    heating_during_day : str
        One of: "Never", "1-2 days a week", "3-4 days a week", "5-7 days a week".
    setpoint : float, optional
        Desired indoor temperature in °C (default=21.0).
    main_heating_source : str, optional
        "Heat pump", "Resistive", etc. If "Heat pump", we reduce energy by the COP.
    cop_calculation : str, optional
        "constant" (use dictionary value per climate zone)
        or "scaled_carnot_cop" (compute scaled carnot for each hour).

    Returns
    -------
    pd.Series
        A Series of length 8760 (non-leap year) with an hourly DateTimeIndex,
        representing the normalized space heating demand (kWh fraction).
        Its sum is 1.0.
    """
    # 1. Retrieve outside temperature data
    temperature_series = hourly_ta(postcode).copy()

    # 2. Compute raw heating demand (thermal) for each hour
    demand_raw = np.maximum(setpoint - temperature_series, 0.0)

    # 3. If it's a heat pump, build a COP timeseries and divide
    #    otherwise, net demand = demand_raw
    if main_heating_source.lower() == "heat pump":
        cop_series = _get_heating_cop_series(
            postcode, temperature_series, cop_calculation, setpoint
        )
        net_demand = demand_raw / cop_series
    else:
        net_demand = demand_raw

    # 4. For scheduling, store net_demand in a DataFrame
    df = pd.DataFrame(
        {
            "net_demand": net_demand,
            "temperature": temperature_series,
        },
        index=temperature_series.index,
    )

    df["date"] = df.index.normalize()
    iso_data = df.index.isocalendar()
    df["week"] = iso_data["week"]
    df["dayofweek"] = df.index.weekday  # Monday=0, Sunday=6

    # 5. Mark full-day vs baseline days
    full_heating_dates = {}
    grouped = df.groupby("week")
    for week_val, group in grouped:
        unique_dates = np.sort(group["date"].unique())
        n_full = _days_for_week(week_val, heating_during_day)
        for i, day_val in enumerate(unique_dates):
            full_heating_dates[day_val] = i < n_full

    df["full_heating"] = df["date"].map(full_heating_dates).fillna(False)

    # 6. Build boolean masks for each schedule:
    hours = df.index.hour

    # Full day window: (7, 21)
    mask_full_day = (hours >= FULL_DAY_WINDOW[0]) & (hours < FULL_DAY_WINDOW[1])

    # Baseline window is union of two intervals: (7,9) and (17,21)
    mask_baseline = np.zeros(len(df), dtype=bool)
    for start, end in BASELINE_WINDOWS:
        mask_baseline |= (hours >= start) & (hours < end)

    # Apply schedule: pick mask_full_day if full_heating==True, else mask_baseline
    schedule_mask = np.where(df["full_heating"], mask_full_day, mask_baseline)
    net_scheduled = df["net_demand"] * schedule_mask.astype(float)

    # 7. Normalize sum to 1
    total = net_scheduled.sum()
    if total > 0:
        net_scheduled /= total

    return pd.Series(net_scheduled, index=df.index, name="heating_profile")
