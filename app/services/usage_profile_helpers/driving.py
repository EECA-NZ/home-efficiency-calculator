"""
Driving (EV charging) electricity usage profile calculation.
"""

import numpy as np
import pandas as pd

from .general import flat_day_night_profiles


def ev_charging_profile() -> np.ndarray:
    """
    Create a default electricity usage profile for electric vehicle charging.
    The resulting array is normalized so that its sum is 1.

    Returns
    -------
    np.ndarray
        A 1D array of shape (8760,), with constant non-zero values in night-time
        hours.
    Placeholder for a more realistic profile.
    """
    _, night_profile = flat_day_night_profiles()
    return night_profile


def _ev_charging_windows(day_of_week: int) -> list[tuple[str, str]]:
    """
    Return a list of (start_time, end_time) window pairs
    for the given day_of_week (Mon=0, Tue=1, ..., Sun=6).
    The times are strings like '13:00:00' or '21:00:00',
    and we'll later turn the night window into a cross-midnight
    range (21:00 -> 09:00 next day).
    """
    # By default, every day has the same night window
    # from 21:00 of this day to 09:00 of the next day.
    # The day "solar window" differs by day of week:
    #
    #  Monday (0): no solar window
    #  Tuesday (1): 13:00–16:00
    #  Wednesday (2): no solar window
    #  Thursday (3): 13:00–16:00
    #  Friday (4): no solar window
    #  Saturday (5): 13:00–17:00
    #  Sunday (6): no solar window
    #
    # We'll return them in the order we want them used
    # (i.e. solar window first, then night window).
    # Note that for the night window we only store
    # the nominal start time here; the code that allocates
    # hours will handle crossing midnight.

    solar_windows_by_dow = {
        0: [],  # Monday
        1: [("13:00:00", "16:00:00")],  # Tuesday
        2: [],  # Wednesday
        3: [("13:00:00", "16:00:00")],  # Thursday
        4: [],  # Friday
        5: [("13:00:00", "17:00:00")],  # Saturday
        6: [],  # Sunday
    }

    # Collect solar windows (may be empty).
    windows = solar_windows_by_dow[day_of_week]

    # Add the night window last (21:00 -> next day 09:00).
    # We'll store it as ("21:00:00", "09:00:00"), and handle
    # the fact that it crosses midnight in the main loop.
    windows.append(("21:00:00", "09:00:00"))  # crosses midnight
    return windows


# pylint: disable=too-many-locals, too-many-branches
def solar_friendly_ev_charging_profile(
    annual_kwh: float, charger_kw: float, year: int = 2019
) -> np.ndarray:
    """
    Construct an hourly EV charging profile (shape = 8760 for 2019),
    allocating a constant daily charging requirement over windows
    that prioritize "solar" hours (1pm–4pm or 1pm–5pm on certain
    days) and then fill the remainder in a cross-midnight 'night'
    window from 9pm of that day to 9am the next day.

    The output is a 1D numpy array normalized so that it sums to 1.
    If you multiply by `annual_kwh`, you get the absolute kWh
    distribution across the year.

    Parameters
    ----------
    annual_kwh : float
        Total EV charging (kWh/year).
    charger_kw : float
        The power of the charger in kW (e.g. 7 kW).
    year : int, optional
        Year to use (default 2019, which is not a leap year).

    Returns
    -------
    np.ndarray
        An array of length 8760 containing the hourly schedule,
        normalized to sum to 1.
    """
    # For simplicity, we assume daily_kwh is uniform across all 365 days.
    daily_kwh = annual_kwh / 365.0
    hours_required_per_day = daily_kwh / charger_kw

    # Create the full-year hourly time index (non-leap year: 365 days = 8760 hours).
    start_date = f"{year}-01-01 00:00:00"
    end_date = f"{year}-12-31 23:00:00"
    hourly_index = pd.date_range(start=start_date, end=end_date, freq="h")
    profile = pd.Series(0.0, index=hourly_index)

    # We'll iterate day by day:
    daily_index = pd.date_range(start=start_date, end=end_date, freq="D")

    for current_day in daily_index:
        dow = current_day.dayofweek  # Monday=0, Sunday=6
        windows = _ev_charging_windows(dow)

        # We'll track how many hours left to allocate this day:
        remaining_hours = hours_required_per_day

        for window_start, window_end in windows:
            if window_start < window_end:
                # Same-day window, e.g. "13:00:00" -> "16:00:00"
                window_range = pd.date_range(
                    current_day + pd.Timedelta(window_start),
                    current_day + pd.Timedelta(window_end),
                    freq="h",
                    inclusive="left",  # up to but not including last edge
                )
            else:
                # Cross-midnight window, e.g. "21:00:00" -> "09:00:00" next day
                # We'll define the start on 'current_day' + 21:00
                # and the end on 'current_day+1' + 09:00
                # to mimic the approach from the hot water code.
                window_range = pd.date_range(
                    current_day + pd.Timedelta(window_start),
                    (current_day + pd.Timedelta("1D")) + pd.Timedelta(window_end),
                    freq="h",
                    inclusive="left",
                )

            # Number of whole hours in the window:
            window_hours = len(window_range)
            if window_hours <= 0:
                continue

            # If we can fill the entire window with the leftover charging,
            # but we only need 'remaining_hours' total. We'll allocate
            # either the full window or what's left, whichever is smaller.
            hours_to_charge = min(remaining_hours, window_hours)

            # Distribute uniformly across these "hours_to_charge" hours
            # from the start of the window range. For example, if the
            # window has 4 hours, but we only need 2.5, we'll fill the
            # first 2 hours fully, plus 0.5 in the third hour.
            # (Similar to the hot water code approach.)

            full_hours = int(np.floor(hours_to_charge))
            fraction_hour = hours_to_charge - full_hours

            # Each hour in the window gets charger_kw usage, so we
            # translate usage to kWh in each hour. But remember we do
            # a *profile*, so we just store '1' for an hour if it's fully used
            # or a fraction if partially used. We'll handle normalization after.

            # The "power" in each hour we decide to use is 'charger_kw'.
            # The total kWh in that hour is 'charger_kw * 1 hr' = charger_kw.
            # We'll accumulate that in `profile[...]`.
            # At the end, we normalize so that sum is 1 (it effectively
            # becomes a shape factor).

            # Fill up 'full_hours':
            for i in range(full_hours):
                if i < window_hours:
                    h_ts = window_range[i]
                    if h_ts > profile.index[-1]:
                        # This can happen if the window crosses midnight
                        continue
                    profile[h_ts] += charger_kw

            # Then if there's a partial hour:
            if fraction_hour > 0:
                # The partial hour index is 'full_hours' into the window
                if full_hours < window_hours:
                    h_ts = window_range[full_hours]
                    if h_ts > profile.index[-1]:
                        # This can happen if the window crosses midnight
                        continue
                    profile[h_ts] += charger_kw * fraction_hour

            # Subtract out what we allocated:
            remaining_hours -= hours_to_charge

            # If we've allocated all required hours, break out of the windows loop
            if remaining_hours <= 0:
                break

        # Done with this day. If there's leftover (which would be unusual),
        # we simply don't carry it forward. (By design here, we only
        # allocate up to a day’s requirement each day.)

    # Finally, normalize so the total sum is 1
    total_kwh = profile.sum()
    if total_kwh > 0:
        profile /= total_kwh

    return profile.to_numpy()
