"""
Hot water heating profile calculation.
"""

# pylint: disable=too-many-arguments, too-many-positional-arguments

import numpy as np
import pandas as pd

from ...services.get_temperatures import hourly_ta
from .general import flat_day_night_profiles

# Default time window constants
MORNING_WINDOW_START = "09:00:00"  # e.g., start of morning heating window
MORNING_WINDOW_END = "13:00:00"  # e.g., end of morning heating window (4 hours)
NIGHT_WINDOW_START = "21:00:00"  # e.g., start of night heating window
NIGHT_WINDOW_END = "09:00:00"  # e.g., end of night heating window (next day; 12 hours)

HEATING_WINDOWS = {
    "morning": (MORNING_WINDOW_START, MORNING_WINDOW_END),
    "night": (NIGHT_WINDOW_START, NIGHT_WINDOW_END),
}


def default_hot_water_electricity_usage_timeseries() -> np.ndarray:
    """
    Create a default electricity usage profile for hot water heating,
    for use in the absence of solar panels.

    Electricity usage is allocated to daytime hours. The calling function
    will later allocate a portion of this profile to time-shiftable
    part of the demand profile, so that for households on time-of-use
    tariffs, the electricity usage is shifted to off-peak hours.

    The resulting array is normalized so that its sum is 1.
    (An outer function will later rescale the numbers to a target sum.)

    Returns
    -------
    np.ndarray
        A 1D array of shape (8760,) where each element is 1/8760.
    Placeholder for a more realistic profile.
    """
    day_profile, _ = flat_day_night_profiles()
    return day_profile


def carnot_cop(temp_hot: float, temp_cold: float) -> float:
    """
    Compute the Carnot Coefficient of Performance (COP) for a heat pump.
    This is used to estimate the theoretical upper limit of efficiency.

    Parameters
    ----------
    temp_hot : float
        The target hot water temperature in Celsius (e.g., 65°C).
    temp_cold : float
        The inlet water temperature (rolling average) in Celsius.

    Returns
    -------
    float
        The Carnot COP. (Note: This is a theoretical maximum.)
    """
    assert temp_hot > temp_cold, "Hot temperature must exceed cold temperature."
    return (temp_hot + 273.15) / (temp_hot - temp_cold)


def daily_electricity_kwh(
    postcode: str, heat_demand_kwh_per_year: float, hot_water_heating_source: str
) -> pd.Series:
    """
    Estimate the daily hot water energy demand (in kWh) for a
    hot water system, based on ambient temperatures and the
    system type.

    For each day, an inlet water temperature is computed as a
    30-day rolling average of the daily ambient temperature
    (from hourly_ta). For a resistive system, demand scales
    as (65 - T_inlet). For a heat pump system, demand scales
    as (65 - T_inlet) divided by the COP (computed via carnot_cop).

    Parameters
    ----------
    postcode : str
        The postcode to obtain ambient temperature data.
    heat_demand_kwh_per_year : float
        The annual hot water energy demand in kWh.
    hot_water_heating_source : str
        System type, e.g. "Heat pump" or "Resistive".

    Returns
    -------
    pd.Series
        Daily kWh demand (indexed by date).
    """
    temp_df = hourly_ta(postcode)
    daily_temp = temp_df.resample("D").mean()
    inlet_temp = daily_temp.rolling(window=30, min_periods=1).mean()

    if hot_water_heating_source.lower() == "heat pump":
        demand_factor = (65 - inlet_temp).clip(lower=0)
        cop = inlet_temp.apply(lambda T: carnot_cop(65, T))
        effective_factor = demand_factor / cop
    else:
        effective_factor = (65 - inlet_temp).clip(lower=0)

    total_factor = effective_factor.sum()
    if total_factor == 0:
        raise ValueError("Total factor is zero; check input data.")
    normalized_factor = effective_factor / total_factor
    daily_kwh = normalized_factor * heat_demand_kwh_per_year
    return daily_kwh


def daily_heat_output_kw(
    postcode: str,
    heater_input_kw: float,
    hot_water_heating_source: str,
) -> pd.Series:
    """
    Compute the daily effective heat output (in kW).

    For a resistive system, this equals heater_input_kw.
    For a heat pump system, calculate the COP based on
    the daily average temperature (using carnot_cop)
    and then compute effective output = heater_input_kw * COP,
    adjusted by a realism factor (e.g., multiplied by 0.4).

    Parameters
    ----------
    postcode : str
        Postcode for obtaining ambient temperature data.
    heater_input_kw : float
        The electrical input power (kW).
    hot_water_heating_source : str
        System type (e.g., "Heat pump" or "Resistive").

    Returns
    -------
    pd.Series
        Daily effective heat output (kW), indexed by date.
    """
    temp_df = hourly_ta(postcode)
    daily_temp = temp_df.resample("D").mean()

    if hot_water_heating_source.lower() == "heat pump":
        cop = daily_temp.apply(lambda T: carnot_cop(65, T))
        realistic_cop = cop * 0.4
        return heater_input_kw * realistic_cop
    return pd.Series(heater_input_kw, index=daily_temp.index)


# pylint: disable=too-many-locals, too-many-branches
def normalized_solar_friendly_water_heating_profile(
    daily_energy: pd.Series,
    daily_output: pd.Series,
    heating_windows=None,
) -> pd.Series:
    """
    Construct an hourly hot water heating profile for a
    hot water system.

    For each day:
      - Compute required
        heating hours = daily_energy / daily effective heat output.
      - Allocate the available hours uniformly over the
        morning window,
        defined by morning_window_start to morning_window_end.
      - Allocate the remaining required hours uniformly over
      the night window,
        defined by night_window_start to night_window_end (which
        spans into the next day).
      - The energy allocated in each window is distributed uniformly
      over the active hours.

    Finally, stitch together the daily profiles into a full-year
    hourly profile and normalize
    it so that the sum equals 1.

    Parameters
    ----------
    daily_energy : pd.Series
        Daily energy demand in kWh (indexed by date).
    daily_output : pd.Series
        Daily effective heat output in kW (indexed by date),
        computed by daily_heat_output_kw.
    heating_windows : dict, optional
        Dictionary of window start and end times (default HEATING_WINDOWS).

    Returns
    -------
    pd.Series
        An hourly timeseries (8760 hours) normalized so that the sum equals 1.
    """
    if heating_windows is None:
        heating_windows = HEATING_WINDOWS
    year = daily_energy.index[0].year
    hourly_index = pd.date_range(f"{year}-01-01", f"{year}-12-31 23:00", freq="h")
    profile = pd.Series(0.0, index=hourly_index)

    morning_window_start, morning_window_end = heating_windows["morning"]
    night_window_start, night_window_end = heating_windows["night"]

    # Compute window durations (in hours)
    morning_duration = (
        pd.Timedelta(morning_window_end) - pd.Timedelta(morning_window_start)
    ).total_seconds() / 3600
    night_duration = (
        pd.Timedelta("1 day")
        + pd.Timedelta(night_window_end)
        - pd.Timedelta(night_window_start)
    ).total_seconds() / 3600

    for day in daily_energy.index:
        energy = daily_energy.loc[day]
        output_kw = daily_output.loc[day]
        assert output_kw > 0, "Output must be positive."
        required_hours = energy / output_kw

        # Allocate hours within the defined windows.
        morning_hours = min(required_hours, morning_duration)
        night_hours = min(max(required_hours - morning_duration, 0), night_duration)

        morning_energy = morning_hours * output_kw
        night_energy = night_hours * output_kw

        full_morning = int(np.floor(morning_hours))
        frac_morning = morning_hours - full_morning

        full_night = int(np.floor(night_hours))
        frac_night = night_hours - full_night

        # Build time windows using the provided start times.
        morning_window = pd.date_range(
            day + pd.Timedelta(morning_window_start),
            periods=int(morning_duration),
            freq="h",
        )
        night_window = pd.date_range(
            day + pd.Timedelta(night_window_start),
            periods=int(night_duration),
            freq="h",
        )

        if morning_hours > 0:
            energy_per_morning = morning_energy / morning_hours
        else:
            energy_per_morning = 0
        for i, ts in enumerate(morning_window):
            if i < full_morning:
                profile.loc[ts] += energy_per_morning
            elif i == full_morning and frac_morning > 0:
                profile.loc[ts] += energy_per_morning * frac_morning

        if night_hours > 0:
            energy_per_night = night_energy / night_hours
        else:
            energy_per_night = 0
        for i, ts in enumerate(night_window):
            if i < full_night:
                if ts in profile.index:
                    profile.loc[ts] += energy_per_night
            elif i == full_night and frac_night > 0:
                if ts in profile.index:
                    profile.loc[ts] += energy_per_night * frac_night

    total = profile.sum()
    if total > 0:
        profile /= total
    return profile


def solar_friendly_hot_water_electricity_usage_timeseries(
    postcode: str,
    heat_demand_kwh_per_year: float,
    heater_input_kw: float,
    hot_water_heating_source,
    heating_windows=None,
) -> np.ndarray:
    """
    Create a solar-friendly electricity usage profile
    for hot water heating.
    The resulting hourly profile (shape (8760,)) is normalized
    so that its sum is 1.

    The process is as follows:
      1. Compute daily energy demand using ambient temperatures.
         - For resistive systems: demand ∝ (65 - T_inlet).
         - For heat pumps: demand ∝ (65 - T_inlet) / COP.
      2. Compute the daily effective heat output (in kW)
      via daily_heat_output_kw.
      3. For each day, compute
      required heating hours = daily_energy / daily_heat_output.
      4. Allocate the available hours within the morning window
      (e.g., 09:00–13:00) and the night window (e.g.,
      21:00–09:00 of the next day).
      5. Build an hourly profile from these allocations and
      normalize it to sum to 1.

    Parameters
    ----------
    postcode : str
        Postcode for ambient temperature data.
    heat_demand_kwh_per_year : float
        Annual hot water energy demand (kWh).
    heater_input_kw : float
        Electrical input power of the system (kW).
    hot_water_heating_source :
        Heating system type (e.g., "Heat pump" or "Resistive").
    morning_window_start : str, optional
        Start time of the morning window (default "09:00:00").
    morning_window_end : str, optional
        End time of the morning window (default "13:00:00").
    night_window_start : str, optional
        Start time of the night window (default "21:00:00").
    night_window_end : str, optional
        End time of the night window (default "09:00:00" of the
        next day).

    Returns
    -------
    np.ndarray
        A 1D numpy array of shape (8760,) representing the hourly
        profile, normalized to sum to 1.
    """
    if heating_windows is None:
        heating_windows = HEATING_WINDOWS
    daily_energy = daily_electricity_kwh(
        postcode, heat_demand_kwh_per_year, hot_water_heating_source
    )
    daily_output = daily_heat_output_kw(
        postcode,
        heater_input_kw,
        hot_water_heating_source,
    )
    hourly_profile = normalized_solar_friendly_water_heating_profile(
        daily_energy,
        daily_output,
        heating_windows=heating_windows,
    )
    return hourly_profile.to_numpy()
