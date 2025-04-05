"""
Hot water heating profile calculation.

For backward compatibility we use the total annual electricity
demand for hot water heating to reverse-engineer a daily profile.

Demand is distributed over the year based on ambient temperatures.

The duration of water heating required each day is estimated, and
used to construct an hourly profile of hot water electricity usage.
"""

# pylint: disable=too-many-arguments, too-many-positional-arguments

import logging

import numpy as np
import pandas as pd

from ...constants import HOT_WATER_HEAT_PUMP_COP_BY_CLIMATE_ZONE
from ..get_climate_zone import climate_zone
from ..get_temperatures import hourly_ta
from .general import flat_day_night_profiles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default time window constants
MORNING_WINDOW_START = "09:00:00"  # e.g., start of morning heating window
MORNING_WINDOW_END = "13:00:00"  # e.g., end of morning heating window (4 hours)
NIGHT_WINDOW_START = "21:00:00"  # e.g., start of night heating window
NIGHT_WINDOW_END = "09:00:00"  # e.g., end of night heating window (next day; 12 hours)

HEATING_WINDOWS = {
    "morning": (MORNING_WINDOW_START, MORNING_WINDOW_END),
    "night": (NIGHT_WINDOW_START, NIGHT_WINDOW_END),
}

CYLINDER_HOT_WATER_TEMPERATURE = 65  # Celsius - typical hot water temperature.
DELIVERED_HOT_WATER_TEMPERATURE = 40  # Celsius - typical demand temperature.
# Although the tank is at 65°C, hot water at the tap is usually 40°C via mixing.
# The fraction drawn from the tank is given by (40 - T_inlet) / (65 - T_inlet),
# and the heating per kg to heat from T_inlet to 65°C is proportional to (65 - T_inlet).
# After multiplying fraction by energy per kg, the (65 - T_inlet) terms cancel out.
# Hence, the total heating demand is effectively proportional to (40 - T_inlet).

DEFAULT_CARNOT_COP_SCALING_FACTOR = 0.4  # Default scaling factor for COP calculation.

COP_CALCULATION = "constant"  # Use an annual average COP per climate zone


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
    This is the theoretical upper limit of efficiency.

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


def get_daily_temp_series_and_cz(postcode: str) -> tuple[pd.Series, str]:
    """
    Retrieve the hourly temperature data for a postcode,
    resample to daily means, and return (daily_temp, climate_zone).
    """
    temp_df = hourly_ta(postcode)
    climate = climate_zone(postcode)
    daily_temp = temp_df.resample("D").mean()
    return daily_temp, climate


def get_cop_series(daily_temp: pd.Series, climate: str, cop_method: str) -> pd.Series:
    """
    Given a daily average temperature Series, the climate zone name,
    and a cop_method string ("constant" or "scaled_carnot_cop"),
    return a daily COP Series.
    """
    if cop_method == "constant":
        return pd.Series(
            HOT_WATER_HEAT_PUMP_COP_BY_CLIMATE_ZONE[climate],
            index=daily_temp.index,
        )
    if cop_method == "scaled_carnot_cop":
        # first evaluate the carnot COP for each day
        daily_cop = daily_temp.apply(
            lambda T: carnot_cop(CYLINDER_HOT_WATER_TEMPERATURE, T)
        )
        # then rescale so that it matches the annual average COP
        annual_cop = HOT_WATER_HEAT_PUMP_COP_BY_CLIMATE_ZONE[climate]
        return daily_cop * annual_cop / daily_cop.mean()
    raise ValueError(f"Unknown COP calculation method: {cop_method}")


def daily_electricity_kwh(
    postcode: str,
    heat_demand_kwh_per_year: float,
    hot_water_heating_source: str,
    cop_calculation: str,
) -> pd.Series:
    """
    Estimate the daily hot water energy demand (in kWh) for a
    hot water system, based on ambient temperatures and the
    system type.

    For each day, an inlet water temperature is estimated as a
    30-day rolling average of the daily ambient temperature
    (from hourly_ta). For a resistive system, demand scales
    as (DELIVERED_HOT_WATER_TEMPERATURE - T_inlet). For a heat
    pump system, demand scales as
    (DELIVERED_HOT_WATER_TEMPERATURE - T_inlet) divided by COP.


    Parameters
    ----------
    postcode : str
        The postcode to obtain ambient temperature data.
    heat_demand_kwh_per_year : float
        The annual hot water energy demand in kWh.
    hot_water_heating_source : str
        System type, e.g. "Heat pump" or "Resistive".
    cop_calculation : str
        The method to calculate the COP.

    Returns
    -------
    pd.Series
        Daily kWh demand (indexed by date).
    """
    logger.info("HERE IN HOT_WATER USAGE PROFILE HELPERS")
    daily_temp, climate = get_daily_temp_series_and_cz(postcode)
    inlet_temp = daily_temp.rolling(window=30, min_periods=1).mean()

    if hot_water_heating_source.lower() == "heat pump":
        demand_factor = (DELIVERED_HOT_WATER_TEMPERATURE - inlet_temp).clip(lower=0)
        realistic_cop = get_cop_series(daily_temp, climate, cop_calculation)
        effective_factor = demand_factor / realistic_cop
    else:
        effective_factor = (DELIVERED_HOT_WATER_TEMPERATURE - inlet_temp).clip(lower=0)

    total_factor = effective_factor.sum()
    if total_factor == 0:
        raise ValueError("Total factor is zero; check input data.")
    normalized_factor = effective_factor / total_factor
    daily_kwh = normalized_factor * heat_demand_kwh_per_year
    return daily_kwh


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
    cop_calculation=COP_CALCULATION,
    heating_windows=None,
) -> np.ndarray:
    """
    Create a solar-friendly electricity usage profile
    for hot water heating.

    The resulting hourly profile (shape (8760,)) is normalized
    so that its sum is 1.

    Typically we would assume the power input is constant,
    at 3kW for resistive hot water systems and 1kW for hot
    water heat pumps.

    The process is as follows:
      1. Compute daily_energy_demand by distributing annual
      demand using ambient temperatures.
         - For resistive systems: demand ∝ (40 - T_inlet).
         - For heat pumps: demand ∝ (40 - T_inlet) / COP(T_amb).
      2. For each day, compute
      required heating hours = daily_energy_demand / heater_input_kw.
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
        postcode,
        heat_demand_kwh_per_year,
        hot_water_heating_source,
        cop_calculation=cop_calculation,
    )
    heater_input_kw_series = pd.Series(heater_input_kw, index=daily_energy.index)
    hourly_profile = normalized_solar_friendly_water_heating_profile(
        daily_energy,
        heater_input_kw_series,
        heating_windows=heating_windows,
    )
    return hourly_profile.to_numpy()
