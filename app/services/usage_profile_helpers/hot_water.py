"""
Hot water heating profile calculation.
"""

import numpy as np
import pandas as pd

from app.services.get_temperatures import hourly_ta


def hot_water_electricity_by_day(region: str, annual_kwh: float) -> pd.Series:
    """
    Distribute the annual hot water energy (kWh) across 365 days,
    weighting each day by a load factor based on the ambient temperature.

    The load factor is (65 - t_roll), where t_roll is a 30-day rolling average
    of daily ambient temperature (niwaTA). If t_roll > 65, the factor is 0.
    """
    temp_df = hourly_ta(region)
    daily_temp = temp_df["niwaTA"].resample("D").mean()
    t_roll = daily_temp.rolling(window=30, min_periods=1).mean()
    target = 65.0
    load_factor = (target - t_roll).clip(lower=0)
    total_factor = load_factor.sum()
    daily_kwh = load_factor / total_factor * annual_kwh
    return daily_kwh


def daytime_water_heating_duration(
    daily_energy: pd.Series,
    heater_kw: float,
    desired_day_fraction: float = 0.80,
    max_day_hours: float = 5.0,
) -> tuple[pd.Series, pd.Series]:
    """
    For each day, determine the actual hours of hot water heating in the daytime window.

    The desired daytime energy is daily_energy * desired_day_fraction.
    The required hours = desired_day_energy / heater_kw, capped at max_day_hours.

    Returns (day_hours, delivered_day_energy).
    """
    desired_day_energy = daily_energy * desired_day_fraction
    required_hours = desired_day_energy / heater_kw
    day_hours = required_hours.clip(upper=max_day_hours)
    delivered_day_energy = day_hours * heater_kw
    return day_hours, delivered_day_energy


def nighttime_water_heating_duration(
    daily_energy: pd.Series,
    delivered_day_energy: pd.Series,
    heater_kw: float,
    max_night_hours: float = 3.0,
) -> tuple[pd.Series, pd.Series]:
    """
    Compute the required nighttime heating duration for each day.

    nighttime_energy = daily_energy - delivered_day_energy,
    required_hours_night = nighttime_energy / heater_kw, capped at max_night_hours.

    Returns (night_hours, delivered_night_energy).
    """
    residual_energy = daily_energy - delivered_day_energy
    required_night_hours = residual_energy / heater_kw
    night_hours = required_night_hours.clip(upper=max_night_hours, lower=0)
    delivered_night_energy = night_hours * heater_kw
    return night_hours, delivered_night_energy


def normalized_water_heating_profile(
    day_hours: pd.Series,
    night_hours: pd.Series,
    day_energy: pd.Series,
    night_energy: pd.Series,
) -> pd.Series:
    """
    Build an hourly hot water heating profile from daily durations and energy splits,
    normalized so the total sum = 1.
    """
    # pylint: disable=too-many-locals,too-many-branches
    hourly_index = pd.date_range("2023-01-01", "2023-12-31 23:00", freq="h")
    profile = pd.Series(0.0, index=hourly_index)

    days = day_hours.index
    max_day_hrs = 5
    max_night_hrs = 3

    for day_dt in days:
        morning_window = pd.date_range(
            day_dt + pd.Timedelta("08:00:00"), periods=max_day_hrs, freq="h"
        )
        evening_window = pd.date_range(
            day_dt + pd.Timedelta("21:00:00"), periods=max_night_hrs, freq="h"
        )

        active_day_hours = day_hours.loc[day_dt]
        if active_day_hours > 0:
            energy_per_hour_day = day_energy.loc[day_dt] / active_day_hours
        else:
            energy_per_hour_day = 0

        active_night_hours = night_hours.loc[day_dt]
        if active_night_hours > 0:
            energy_per_hour_night = night_energy.loc[day_dt] / active_night_hours
        else:
            energy_per_hour_night = 0

        full_hours_day = int(np.floor(active_day_hours))
        frac_day = active_day_hours - full_hours_day
        for i, ts in enumerate(morning_window):
            if i < full_hours_day:
                profile.loc[ts] = energy_per_hour_day
            elif i == full_hours_day and frac_day > 0:
                profile.loc[ts] = energy_per_hour_day * frac_day
            else:
                profile.loc[ts] = 0

        full_hours_night = int(np.floor(active_night_hours))
        frac_night = active_night_hours - full_hours_night
        for i, ts in enumerate(evening_window):
            if i < full_hours_night:
                profile.loc[ts] = energy_per_hour_night
            elif i == full_hours_night and frac_night > 0:
                profile.loc[ts] = energy_per_hour_night * frac_night
            else:
                profile.loc[ts] = 0

    total_energy = profile.sum()
    if total_energy > 0:
        profile /= total_energy
    return profile


def hot_water_heating_profile(
    region: str,
    annual_kwh: float,
    heater_kw: float,
    desired_day_fraction: float = 0.80,
) -> pd.Series:
    """
    Compute an hourly hot water heating profile.

    Steps:
      1. Distribute annual_kwh across days (hot_water_electricity_by_day).
      2. Determine daytime heating duration from the desired fraction, up to 5 hours.
      3. Determine nighttime heating for the residual, up to 3 hours.
      4. Combine into an hourly series via normalized_water_heating_profile().
    """
    daily_energy = hot_water_electricity_by_day(region, annual_kwh)
    day_hours, delivered_day_energy = daytime_water_heating_duration(
        daily_energy, heater_kw, desired_day_fraction, max_day_hours=5
    )
    night_hours, delivered_night_energy = nighttime_water_heating_duration(
        daily_energy, delivered_day_energy, heater_kw, max_night_hours=3
    )
    return normalized_water_heating_profile(
        day_hours, night_hours, delivered_day_energy, delivered_night_energy
    )
