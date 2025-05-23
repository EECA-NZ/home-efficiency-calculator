"""
Processes data from the file power_demand_by_time_of_use_data.csv,
which is the Demand.Data sheet from the 2021 Residential Baseline Study.
We filter the data to Region = NZ and Year = 2025, then sum the power
for the categories IT&HE, Lighting, Other Equipment, and White. The
resulting time series is saved to it_light_other_white_tou_8760.csv.

Source Data:
https://www.energyrating.gov.au/industry-information/publications/report-2021-residential-baseline-study-australia-and-new-zealand-2000-2040
"""

import os

import pandas as pd

# CONSTANTS
REGION = "NZ"
TARGET_YEAR = 2025
INPUT_FILE = os.path.join(
    "../",
    "supplementary_data",
    "power_demand_by_time_of_use_data",
    "power_demand_by_time_of_use_data.csv",
)
OUTPUT_FILE = os.path.join("output", "it_light_other_white_tou_8760.csv")

SEASON_MAP = {
    1: "Summer",
    2: "Summer",
    3: "Autumn",
    4: "Autumn",
    5: "Autumn",
    6: "Winter",
    7: "Winter",
    8: "Winter",
    9: "Spring",
    10: "Spring",
    11: "Spring",
    12: "Summer",
}


def dst_indicator(dt):
    """
    Returns 1 if 'dt' is within NZ daylight saving period, otherwise 0.
    NZ DST schedule (approximate):
      - Jan 1 – Mar 17 => DST = 1
      - Mar 18 – Oct 5 => DST = 0
      - Oct 6 – Dec 31 => DST = 1
    """
    if dt.month < 3 or (dt.month == 3 and dt.day <= 17):
        return 1
    if dt.month > 10 or (dt.month == 10 and dt.day >= 6):
        return 1
    return 0


def map_daytype(day_name):
    """Returns 'WD' for Monday–Friday, otherwise 'WE'."""
    return (
        "WD"
        if day_name in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        else "WE"
    )


def map_season(month):
    """Maps a month integer (1–12) to one of 'Summer', 'Autumn', 'Winter', 'Spring'."""
    return SEASON_MAP.get(month)


# MAIN

# --- Load and filter data ---
power_df = pd.read_csv(INPUT_FILE)
power_df = power_df[(power_df["Region"] == REGION) & (power_df["Year"] == TARGET_YEAR)]

# --- Group by unique combinations and sum power ---
grouped_df = power_df.groupby(
    ["Region", "Season", "DayType", "End Use Category", "Year", "Hour"], as_index=False
).agg({"Power": "sum"})

# --- Verify row count is 1728 (1 * 4 * 2 * 9 * 1 * 24) ---
if len(grouped_df) != 1728:
    raise RuntimeError(
        "Unexpected unique combinations in grouped data: "
        f"{len(grouped_df)} (expected 1728)."
    )

# --- Sum power for specific categories and rename column ---
categories_to_sum = ["IT&HE", "Lighting", "Other Equipment", "White goods"]
filtered_df = grouped_df[grouped_df["End Use Category"].isin(categories_to_sum)]

summed_categories_df = (
    filtered_df.groupby(["Region", "Season", "DayType", "Year", "Hour"], as_index=False)
    .agg({"Power": "sum"})
    .rename(columns={"Power": "Power IT Light Other White"})
)

# --- Construct an hourly time series for 2019 (non-leap year) ---
date_range = pd.date_range("2019-01-01", "2019-12-31 23:00:00", freq="h")
simulation_df = pd.DataFrame({"DateTime": date_range})

simulation_df["Day of Simulation[]"] = simulation_df["DateTime"].dt.dayofyear
simulation_df["Month[]"] = simulation_df["DateTime"].dt.month
simulation_df["Day of Month[]"] = simulation_df["DateTime"].dt.day
simulation_df["DST Indicator[1=yes 0=no]"] = simulation_df["DateTime"].apply(
    dst_indicator
)
simulation_df["Hour[]"] = simulation_df["DateTime"].dt.hour + 1  # Convert 0–23 to 1–24
simulation_df["WeekDay"] = simulation_df["DateTime"].dt.day_name()  # e.g., Tuesday
simulation_df["Season"] = simulation_df["Month[]"].apply(map_season)
simulation_df["DayType"] = simulation_df["WeekDay"].apply(map_daytype)
simulation_df["Region"] = REGION
simulation_df["Year"] = TARGET_YEAR
simulation_df["Hour_lookup"] = simulation_df[
    "DateTime"
].dt.hour  # 0–23 to match dataset

# --- Merge with aggregated data ---
merged_df = pd.merge(
    simulation_df,
    summed_categories_df,
    left_on=["Region", "Season", "DayType", "Year", "Hour_lookup"],
    right_on=["Region", "Season", "DayType", "Year", "Hour"],
    how="left",
)

# --- Fill missing lookups with 0 ---
merged_df["Power IT Light Other White"] = merged_df[
    "Power IT Light Other White"
].fillna(0)

# --- Final time series columns ---
result_df = merged_df[
    [
        "Day of Simulation[]",
        "Month[]",
        "Day of Month[]",
        "DST Indicator[1=yes 0=no]",
        "Hour[]",
        "WeekDay",
        "Power IT Light Other White",
    ]
].rename(
    columns={
        "WeekDay": "DayType",
    },
)

# --- Save to CSV ---
result_df.to_csv(OUTPUT_FILE, float_format="%.3f", index=False)
print(f"Annual time series saved to '{OUTPUT_FILE}'")
