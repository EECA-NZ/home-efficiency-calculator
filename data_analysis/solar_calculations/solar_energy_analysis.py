"""
Module that provides various energy analysis functions, including solar data loading,
temperature profiles, demand profiles, water heating, and EV charging profiles.
"""

import logging
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

# Memoization of the niwa data for each region.
# Keys: region names (e.g., "Auckland")
# Values: DataFrame with solar/temperature data.
LOADED_NIWA_DATA = {}

# Path to the directory containing solar CSV files.
SOLAR_PV = "../supplementary_data/hourly_solar_generation_by_climate_zone"

# Mapping of region names to code prefixes used in solar CSV filenames.
CZ = {
    "Northland": "NL",
    "Auckland": "AK",
    "Hamilton": "HN",
    "Rotorua": "RR",
    "Bay of Plenty": "BP",
    "Taupo": "TP",
    "East Coast": "EC",
    "New Plymouth": "NP",
    "Manawatu": "MW",
    "Wairarapa": "WI",
    "Wellington": "WN",
    "Nelson-Marlborough": "NM",
    "Christchurch": "CC",
    "West Coast": "WC",
    "Central Otago": "OC",
    "Dunedin": "DN",
    "Queenstown-Lakes": "QL",
    "Invercargill": "IN",
}


def niwa_data(region: str) -> pd.DataFrame:
    """
    Return a DataFrame of solar data for the specified region.

    The CSV file is selected from the SOLAR_PV directory based on the region code.
    The DataFrame is indexed by a datetime index covering a non-leap year (8760 hours).
    """
    if region in LOADED_NIWA_DATA:
        return LOADED_NIWA_DATA[region]

    code = CZ.get(region)
    if code is None:
        raise ValueError(f"Region {region} not found in CZ mapping.")

    solar_csvs = os.listdir(SOLAR_PV)
    filename = next((f for f in solar_csvs if f.startswith(code + "_")), None)
    if filename is None:
        raise ValueError(f"No solar CSV found for region {region} (code {code}).")

    csv_path = os.path.join(SOLAR_PV, filename)
    df_solar = pd.read_csv(csv_path)

    # Create a datetime index for a non-leap year (e.g. 2023).
    date_range = pd.date_range("2023-01-01", "2023-12-31 23:00", freq="H")
    df_solar.index = date_range
    LOGGER.info(
        "Solar data for %s loaded from %s with %d rows.",
        region,
        csv_path,
        len(df_solar),
    )

    LOADED_NIWA_DATA[region] = df_solar
    return df_solar


def temperature_data(region: str) -> pd.DataFrame:
    """
    Return a DataFrame containing temperature data for the specified region.
    For this prototype, assume temperature is in the 'niwaTA' column.
    """
    df_solar = niwa_data(region)
    return df_solar[["niwaTA"]].copy()


def base_demand_profile(region: str) -> pd.Series:
    """
    Return an hourly base demand profile for the specified region.
    (Assumes 'power_model' column exists in the solar CSV.)
    Normalizes so the sum of the profile equals 1.
    """
    df_solar = niwa_data(region)
    base_demand = df_solar["power_model"]
    total_demand = base_demand.sum()
    if total_demand != 0:
        base_demand = base_demand / total_demand
    return base_demand


def space_heating_profile(
    region: str,
    heating_during_day: str,
    setpoint: float = 21.0,
) -> pd.Series:
    """
    Compute an hourly space heating demand profile
    for the specified region.

    Uses the temperature data ('niwaTA') from
    the region and computes heating demand
    as max(setpoint - niwaTA, 0), but only
    when heating is active. The schedule is
    determined by the 'heating_during_day'parameter.

    Parameters:
      region (str): region name, e.g., "Auckland".
      heating_during_day (str):
         "Never"            - No daytime heating demand.
         "1-2 days a week"  - Daytime heating on 1 day
            in odd weeks, 2 days in even weeks.
         "3-4 days a week"  - Daytime heating on 3 days
            in odd weeks, 4 days in even weeks.
         "5-7 days a week"  - Daytime heating on 5 days
            in odd weeks, 7 days in even weeks.
      setpoint (float): desired indoor temperature in °C.

    Heating is always on 7am-9am, 5pm-9pm.

    On a "full daytime" day, it's 7am-9pm.

    Returns:
      pd.Series (length 8760) with the normalized
      hourly heating demand.
    """
    # pylint: disable=too-many-locals
    temp_df = temperature_data(region).copy()
    temp_df["date"] = temp_df.index.normalize()
    iso = temp_df.index.isocalendar()
    temp_df["week"] = iso["week"]
    temp_df["dayofweek"] = temp_df.index.weekday

    def days_for_week(week_num: int, option: str) -> int:
        """Return how many 'full-day' heating days in a given week."""
        if option == "1-2 days a week":
            return 1 if (week_num % 2 == 1) else 2
        if option == "3-4 days a week":
            return 3 if (week_num % 2 == 1) else 4
        if option == "5-7 days a week":
            return 5 if (week_num % 2 == 1) else 7
        return 0

    full_heating_dates = {}
    grouped = temp_df.groupby("week")
    for week_val, group in grouped:
        unique_dates = np.sort(group["date"].unique())
        n_full = days_for_week(week_val, heating_during_day)
        for i, day_val in enumerate(unique_dates):
            full_heating_dates[day_val] = i < n_full

    temp_df["full_heating"] = temp_df["date"].map(full_heating_dates)

    # pylint: disable=no-member
    hours = temp_df.index.hour  # Known false-positive in some pylint configs
    mask_full = (hours >= 7) & (hours < 21)
    mask_baseline = ((hours >= 7) & (hours < 9)) | ((hours >= 17) & (hours < 21))
    heating_mask = np.where(temp_df["full_heating"], mask_full, mask_baseline)

    demand = np.maximum(setpoint - temp_df["niwaTA"], 0)
    heating_demand = demand * heating_mask.astype(float)
    total_demand = heating_demand.sum()
    if total_demand != 0:
        heating_demand = heating_demand / total_demand

    return pd.Series(heating_demand, index=temp_df.index)


def hot_water_electricity_by_day(region: str, annual_kwh: float) -> pd.Series:
    """
    Distribute the annual hot water energy (kWh) across 365 days,
    weighting each day by a load factor based on the ambient temperature.

    The load factor is (65 - t_roll), where t_roll is a 30-day rolling average
    of daily ambient temperature (niwaTA). If t_roll > 65, the factor is 0.
    """
    temp_df = temperature_data(region)
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
    hourly_index = pd.date_range("2023-01-01", "2023-12-31 23:00", freq="H")
    profile = pd.Series(0.0, index=hourly_index)

    days = day_hours.index
    max_day_hrs = 5
    max_night_hrs = 3

    for day_dt in days:
        morning_window = pd.date_range(
            day_dt + pd.Timedelta("08:00:00"), periods=max_day_hrs, freq="H"
        )
        evening_window = pd.date_range(
            day_dt + pd.Timedelta("21:00:00"), periods=max_night_hrs, freq="H"
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


def ev_charging_profile(annual_kwh: float, charger_kw: float) -> pd.Series:
    """
    Compute an hourly EV charging profile.

    Assumptions:
      - The car is plugged in each night.
      - For weekdays, charging is 22:00-05:00.
      - For weekends, charging is 13:00-20:00.
      - daily required hours = annual_kwh / 365 / charger_kw.

    Returns a Series with length 8760, sum=1.
    """
    # pylint: disable=no-member
    idx = pd.date_range("2023-01-01", "2023-12-31 23:00", freq="H")
    profile = pd.Series(0.0, index=idx)

    # Instead of is_weekday, is_weekend, etc. we can do:
    # weekday = idx.weekday # no-member false positive
    hour_val = idx.hour  # no-member
    is_weekday = idx.weekday < 5  # no-member
    is_weekend = idx.weekday >= 5  # no-member

    # For weekdays: hours 22,23,0..5
    mask_weekday = is_weekday & (
        ((hour_val >= 22) & (hour_val <= 23)) | ((hour_val >= 0) & (hour_val < 6))
    )
    # For weekends: hours 13..20
    mask_weekend = is_weekend & (hour_val >= 13) & (hour_val < 21)

    charging_mask = mask_weekday | mask_weekend
    total_charging_hours = charging_mask.sum()

    required_hours = annual_kwh / charger_kw
    fraction_per_hour = (
        required_hours / total_charging_hours if total_charging_hours > 0 else 0
    )

    profile.loc[charging_mask] = fraction_per_hour
    total_allocated = profile.sum()
    if total_allocated > 0:
        profile /= total_allocated

    return profile


def main() -> None:
    """
    Example usage block demonstrating how to call the above profiles.
    """
    region_name = "Auckland"

    base_profile_data = base_demand_profile(region_name)
    heat_profile_data = space_heating_profile(
        region_name, heating_during_day="5-7 days a week", setpoint=21
    )
    hw_profile_data = hot_water_heating_profile(
        region_name, annual_kwh=5000, heater_kw=1.8
    )
    ev_profile_data = ev_charging_profile(annual_kwh=2000, charger_kw=7.0)

    _, axes = plt.subplots(4, 1, figsize=(10, 8))

    heat_profile_data.plot(ax=axes[0], title="Space Heating Demand Profile")
    axes[0].set_ylabel("Fraction of Annual kWh")

    hw_profile_data.plot(ax=axes[1], title="Hot Water Heating Profile")
    axes[1].set_ylabel("Fraction of Annual kWh")

    ev_profile_data.plot(ax=axes[2], title="EV Charging Profile")
    axes[2].set_ylabel("Fraction of Annual kWh")

    base_profile_data.plot(ax=axes[3], title="Base Demand Profile")
    axes[3].set_ylabel("Base Power Demand (kW)")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
