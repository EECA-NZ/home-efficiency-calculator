"""
Space heating profile calculation using regression coefficients.

This revised version computes an hourly heating demand profile using a linear regression
model rather than the original setpoint-based approach. Regression coefficients are loaded
from a CSV file (1970s-house-combined-regression-electricity.csv) which contains:
    • day_type – "Weekday" (no daytime heating) or "Weekend" (daytime heating)
    • local_hour – the hour of the day (0-23)
    • const – the constant for the regression model
    • slope – the slope coefficient (multiplied by the outside temperature)

Additional rules implemented:
    • If the temperature is less than 5°C, use 5°C in the regression calculation.
    • If the actual temperature is above 18°C, set heating_electricity to 0.
    • If the regression prediction (const + temperature*slope) is negative, set to 0.

For each ISO week, the number of days that receive “all-day” heating is determined via
_days_for_week(week_num, heating_during_day). The weekend days are assigned as the last
n_full days of the week (with n_full determined by heating_during_day).

Finally, the hourly timeseries is normalized so that its sum is 1.
"""

import os
import numpy as np
import pandas as pd

from ...constants import HEAT_PUMP_COP_BY_CLIMATE_ZONE  # not used in this revised algorithm
from ..get_climate_zone import climate_zone  # not used here either
from ..get_temperatures import hourly_ta

# Time window constants are no longer used for regression-based calculation,
# but they remain defined in case they are needed elsewhere.
FULL_DAY_WINDOW = (7, 21)
BASELINE_WINDOWS = [(7, 9), (17, 21)]

DEFAULT_SPACE_HEATING_SETPOINT = 20.0

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
        all-day heating.
    """
    if option == "1-2 days a week":
        return 1 if (week_num % 2 == 1) else 2
    if option == "3-4 days a week":
        return 3 if (week_num % 2 == 1) else 4
    if option == "5-7 days a week":
        return 5 if (week_num % 2 == 1) else 7
    return 0  # Default for "Never"

def space_heating_profile(
    postcode: str,
    heating_during_day: str,
    setpoint: float = DEFAULT_SPACE_HEATING_SETPOINT,
    main_heating_source: str = "Heat pump",  # not used in this new approach
    cop_calculation: str = "constant",       # not used in this new approach
) -> pd.Series:
    """
    Compute an hourly space heating demand profile using regression coefficients.

    Steps:
      1. Retrieve hourly outside temperatures via hourly_ta(postcode).
      2. Load regression coefficients from CSV into a DataFrame.
      3. For each day, determine its “day type” (Weekday or Weekend) based on the week
         number and the heating_during_day option. Weekend days are chosen as the last
         n_full days of the week (e.g., if n_full == 1, only Sunday; if n_full == 2, Saturday
         and Sunday; if n_full == 3, Friday, Saturday, and Sunday; etc.).
      4. For each hour, determine the local hour and day type, then look up the corresponding
         regression coefficients (const and slope) and calculate:
             heating_electricity = const + temperature * slope
         with the following modifications:
             - If the temperature is below 5°C, use 5°C instead.
             - If the actual temperature is above 18°C, set heating_electricity to 0.
             - If the computed heating_electricity is negative, set it to 0.
         If no matching coefficients are found, heating_electricity is set to 0.
      5. Normalize the resulting timeseries so that its sum equals 1.

    Parameters
    ----------
    postcode : str
        The postcode used by hourly_ta() to retrieve outside temperatures.
    heating_during_day : str
        One of: "Never", "1-2 days a week", "3-4 days a week", "5-7 days a week".
    setpoint : float, optional
        Desired indoor temperature in °C (not used in regression, but kept for compatibility).
    main_heating_source : str, optional
        Not used in this revised algorithm.
    cop_calculation : str, optional
        Not used in this revised algorithm.

    Returns
    -------
    pd.Series
        A Series of length 8760 (non-leap year) with an hourly DateTimeIndex,
        representing the normalized heating demand (kWh fraction).
        Its sum is 1.0.
    """
    # 1. Retrieve outside temperature data
    temperature_series = hourly_ta(postcode).copy()

    # 2. Load regression coefficients from CSV.
    # Assume the CSV file is in the same directory as this module.
    module_dir = os.path.dirname(__file__)
    reg_csv_path = os.path.join(module_dir, "1970s-house-combined-regression-electricity.csv")
    try:
        reg_df = pd.read_csv(reg_csv_path)
    except Exception as e:
        raise FileNotFoundError(f"Could not load regression coefficients CSV: {reg_csv_path}") from e

    # Ensure that the necessary columns are present
    required_cols = {"day_type", "local_hour", "const", "slope"}
    if not required_cols.issubset(set(reg_df.columns)):
        raise ValueError(f"CSV file must contain columns: {required_cols}")

    # 3. Build a DataFrame with the temperature timeseries and date components.
    df = pd.DataFrame(
        {"temperature": temperature_series},
        index=temperature_series.index,
    )
    df["date"] = df.index.normalize()
    iso_data = df.index.isocalendar()
    df["week"] = iso_data["week"]
    df["dayofweek"] = df.index.weekday  # Monday=0, Sunday=6
    df["local_hour"] = df.index.hour

    # 4. Determine the day type for each day.
    # For each week, decide how many days should be treated as "Weekend" (i.e., with daytime heating)
    # using the _days_for_week function. Here, we treat the last n_full days of the week as weekend days.
    df["n_full"] = df["week"].apply(lambda w: _days_for_week(w, heating_during_day))
    df["reg_day_type"] = np.where(df["dayofweek"] >= (7 - df["n_full"]), "Weekend", "Weekday")

    # 5. Merge with regression coefficients.
    # The regression coefficients in reg_df are keyed by day_type and local_hour.
    merged = pd.merge(
        df,
        reg_df,
        how="left",
        left_on=["reg_day_type", "local_hour"],
        right_on=["day_type", "local_hour"],
    )

    # 6. Compute heating electricity demand.
    # Adjust temperature: if temperature is below 5°C, use 5°C for the regression.
    merged["calc_temperature"] = np.where(merged["temperature"] < 5, 5, merged["temperature"])
    merged["heating_electricity"] = merged["const"].fillna(0) + merged["calc_temperature"] * merged["slope"].fillna(0)
    # If the actual temperature is above 18°C, set heating_electricity to 0.
    merged.loc[merged["temperature"] > 18, "heating_electricity"] = 0
    # If the regression prediction is negative, set heating_electricity to 0.
    merged.loc[merged["heating_electricity"] < 0, "heating_electricity"] = 0

    # 7. Normalize the timeseries so that its sum is 1.
    total = merged["heating_electricity"].sum()
    if total > 0:
        merged["heating_electricity"] /= total

    return pd.Series(merged["heating_electricity"], index=merged.index, name="heating_profile")
