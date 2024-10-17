"""
Vector have map and downloadable shapefile
Unison have a map
Powerco have a pdf
"""

import ast
import logging
import os
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from data_analysis.energy_plans_available.edb_to_locations import edb_to_locations
from data_analysis.postcode_lookup_tables.geo_utils import load_and_transform_shapefile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


EDB_REGION_SHAPEFILE = "../supplementary_data/EDB_Boundaries/EDBBoundaries.shp"
EXCLUDE_PATTERNS = [
    "Small Capacity",
]  # , 'Rural', 'Remote area', 'Low Density']
# "Marlborough Remote area"
# "South Canterbury (Rural - LCA)"


def eval_or_return(x):
    """Evaluate string as Python expression if possible, otherwise return as is.
    Uses ast.literal_eval to evaluate the string as a Python expression if safe.

    Parameters
    ----------
    x : str or any
        The input string to evaluate or any other type to return as is.

    Returns
    -------
    any
        The evaluated Python expression if x is a string that can be safely evaluated,
        otherwise x as is.
    """
    if isinstance(x, str):
        try:
            return ast.literal_eval(x)
        except (ValueError, SyntaxError):
            return x
    else:
        return x


def contains_exclude_patterns(locations_str):
    """
    Check if any of the exclude patterns are present in the locations string.

    Parameters
    ----------
    locations_str : str

    Returns
    -------
    bool
    """
    locations = [loc.strip() for loc in locations_str.split(",")]
    for loc in locations:
        for pattern in EXCLUDE_PATTERNS:
            if pattern in loc:
                return True
    return False


def map_locations_to_edb(locations_str):
    """
    Map locations string to EDB name.

    Parameters
    ----------
    locations_str : str

    Returns
    -------
    str
        EDB name if a single EDB is found for the locations, otherwise "Unknown".
    """
    locations = [loc.strip() for loc in locations_str.split(",")]
    edbs_found = set()
    for loc in locations:
        edb = locations_to_edb.get(loc)
        if edb:
            edbs_found.add(edb)
    if len(edbs_found) == 1:
        return edbs_found.pop()
    if len(edbs_found) > 1:
        raise ValueError(f"Multiple EDBs found for locations {locations}: {edbs_found}")
    return "Unknown"


def show_plan(plan_id, dropna=True):
    """
    Show the plan with the given PlanId.

    Parameters
    ----------
    plan_id : str
        The PlanId to search for.

    dropna : bool, optional
        Whether to drop columns with NaN values. Default is True.
    """
    matches = full_df[full_df["PlanId"] == plan_id]
    if matches.empty:
        print(f"PlanId {plan_id} not found.")
        return None
    idx = matches.index[0]
    if dropna:
        return full_df.loc[idx].dropna()
    return full_df.loc[idx]


def plot_subset(df, edb=None, hue_column=None, output_dir="scatterplots"):
    """
    Plot an EDB-specific subset of the DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame containing the data to plot.

    edb : str or None, optional
        The EDB name to filter the data by.
        If None, all EDBs are included. Default is None.

    hue_column : str or None, optional
        The column to use for coloring the data points.
        If None, no coloring is applied. Default is None.

    output_dir : str, optional
        The output directory to save the plot image to.
        Default is "scatterplots".

    Returns
    -------
    None
    """
    subset = df.copy()
    if edb is not None:
        subset = subset[subset["EDB"] == edb]
    subset["1/10 x Daily charge"] = subset["Daily charge"] / 10
    scatterplot_vars = [
        "All inclusive",
        "Day",
        "Uncontrolled",
        "Controlled",
        "Night",
        "1/10 x Daily charge",
    ]
    plot_height = 1
    plot_aspect = 2
    if (
        hue_column is not None
        and hue_column in subset.columns
        and subset[hue_column].notnull().any()
    ):
        g = sns.pairplot(
            subset,
            vars=scatterplot_vars,
            hue=hue_column,
            palette="Set1",
            plot_kws={"alpha": 0.6},
            height=plot_height,
            aspect=plot_aspect,
        )
    else:
        if hue_column is not None:
            if hue_column not in subset.columns:
                logger.warning(
                    "Hue_column '%s' not " + "found in subset DataFrame for EDB '%s'.",
                    hue_column,
                    edb,
                )
            elif not subset[hue_column].notnull().any():
                logger.warning(
                    "Hue_column '%s' " + "contains only NaN values for EDB '%s'.",
                    hue_column,
                    edb,
                )
        g = sns.pairplot(
            subset,
            vars=scatterplot_vars,
            plot_kws={"alpha": 0.6},
            height=plot_height,
            aspect=plot_aspect,
        )
    for ax in g.axes.flatten():
        if ax is not None:
            ax.set_xlim(0, 0.5)
            ax.set_ylim(0, 0.5)
    g.fig.suptitle(edb if edb else "All EDBs", fontsize=16, y=0.98)
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{output_dir}/{edb.replace(' ', '_') if edb else 'all'}.png"
    plt.savefig(filename)
    plt.close()


#### MAIN ####

# def main():
# Your code here


full_df = pd.read_csv("../supplementary_data/tariff_data/tariffDataReport_240903.csv")
full_df = full_df.loc[full_df["Energy type"] == "electricity"].copy()
NUMERICAL_COLUMNS = [
    "All inclusive",
    "Night only",
    "Controlled",
    "Day",
    "Night",
    "Day - Controlled",
    "Night - Controlled",
    "Off peak",
    "Shoulder",
    "Peak",
    "NightBoost",
    "Uncontrolled",
    "Daily charge",
    "Discount per unit",
    "Discount per day",
    "Discount from total",
    "Discount - Other",
    "Controlled - Off peak",
    "Controlled - Shoulder",
    "Controlled - Peak",
]

for col in NUMERICAL_COLUMNS:
    full_df[col] = full_df[col].apply(
        lambda x: np.mean(eval_or_return(x)) if pd.notnull(x) else x
    )


my_edb_boundaries_gdf = load_and_transform_shapefile(EDB_REGION_SHAPEFILE)
my_edb_boundaries_gdf.loc[
    my_edb_boundaries_gdf["name"] == "CentraLines Ltd", "name"
] = "Centralines Ltd"

locations_to_edb = {
    location: re.sub(r"\s*\(.*\)$", "", edb)
    for edb, locations in edb_to_locations.items()
    for location in locations
}
full_df["EDB"] = full_df["Network location names"].apply(map_locations_to_edb)


def open_plans(row):
    """Check if the plan is open for new customers."""
    return "open" in row["Status"]


def fixed_term(row):
    """Check if the plan is fixed term."""
    return row["Fixed term"]


def low_user(row):
    """Check if the plan is for low users."""
    return row["Low user"]


def energy_plus(row):
    """Check if the plan is an Energy Plus plan."""
    return "Energy Plus" in row["Name"]


def day_night(row):
    """Check if the plan is a day/night plan."""
    return "Day/night" in row["Plan type"]


def no_discount(row):
    """Check if the plan has no discount."""
    return (
        pd.isna(row["Discount per unit"])
        and pd.isna(row["Discount per day"])
        and pd.isna(row["Discount from total"])
        and pd.isna(row["Discount - Other"])
    )


def has_constant_day_rate(row):
    """Check if the plan has a constant day rate."""
    return isinstance(row.Day, float) or (row.Day.count(",") == 0)


def has_constant_night_rat(row):
    """Check if the plan has a constant night rate."""
    return isinstance(row.Night, float) or (row.Night.count(",") == 0)


def no_hot_water_cylinder(row):
    """Check if the plan requires no electric hot water cylinder."""
    return "no electric hot water cylinder" in row["Name"].lower()


def bundled_broadband(row):
    """Check if the plan includes bundled broadband."""
    return "broadband" in row["Name"].lower()


def issimple(row):
    """
    Check if the plan is a 'simple' plan with
    only the most common tarrif types.
    """
    return (
        pd.isna(row["Day - Controlled"])
        and pd.isna(row["Night - Controlled"])
        and pd.isna(row["Controlled"])
        and pd.isna(row["Off peak"])
        and pd.isna(row["Shoulder"])
        and pd.isna(row["Peak"])
        and pd.isna(row["NightBoost"])
        and pd.isna(row["Discount per unit"])
        and pd.isna(row["Discount per day"])
        and pd.isna(row["Discount from total"])
        and pd.isna(row["Discount - Other"])
        and pd.isna(row["Controlled - Off peak"])
        and pd.isna(row["Controlled - Shoulder"])
        and pd.isna(row["Controlled - Peak"])
    )


full_df = full_df[
    full_df.apply(open_plans, axis=1)
]  # Exclude plans where retailer is not accepting new customers
full_df = full_df[
    ~full_df["Network location names"].apply(contains_exclude_patterns)
]  # Exclude rows where 'Network location names' contain any of the exclude patterns

full_df.loc[:, "Network location names"] = full_df["Network location names"].str.split(
    ","
)
full_df = full_df.explode("Network location names")
full_df.loc[:, "Network location names"] = full_df["Network location names"].str.strip()
full_df = full_df.reset_index(drop=True)

my_df = full_df.copy()
retailer_locs = full_df["Retailer location name"].unique()
network_locs = full_df["Network location names"].unique()
logger.info("there are %s unique retailer locations", len(retailer_locs))
logger.info("there are %s unique network locations", len(network_locs))

filters = (
    (~my_df["Fixed term"])
    & (~my_df["Low user"])
    & (~my_df["Name"].str.contains("Energy Plus", na=False))
    & (my_df["Plan type"].str.contains("Day/night", na=False))
    & (
        ~my_df["Name"]
        .str.lower()
        .str.contains("no electric hot water cylinder", na=False)
    )
    & (~my_df["Name"].str.lower().str.contains("broadband", na=False))
    & my_df.apply(issimple, axis=1)
)

my_df = my_df[filters]

my_df.to_csv("deleteme.csv", index=False)
columns = my_df.columns.to_series().groupby(my_df.dtypes).groups
logger.info(my_df.dropna(axis=1))

for my_edb in sorted(my_edb_boundaries_gdf["name"].unique()):
    if my_edb == "Stewart Island Electrical Supply Authority":
        continue
    logger.info("Processing EDB: %s", my_edb)
    plot_subset(
        full_df, my_edb, hue_column="Network location names", output_dir="bynetwork"
    )

# if __name__ == '__main__':
#    main()
