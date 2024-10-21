"""
Vector have map and downloadable shapefile
Unison have a map
Powerco have a pdf
"""

import ast
import logging
import os
import re

import img2pdf
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from app.models.energy_plans import ElectricityPlan
from data_analysis.energy_plans_available.edb_to_locations import edb_to_locations
from data_analysis.postcode_lookup_tables.geo_utils import load_and_transform_shapefile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LOCAL_TARIFF_DATA_PATH = "../supplementary_data/tariff_data/tariffDataReport_240903.csv"
EDB_REGION_SHAPEFILE = "../supplementary_data/EDB_Boundaries/EDBBoundaries.shp"
EXCLUDE_PATTERNS = ["Small Capacity"]
OUTPUT_DIR = "bynetwork"
locations_to_edb = {
    location: re.sub(r"\s*\(.*\)$", "", edb)
    for edb, locations in edb_to_locations.items()
    for location in locations
}
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


def daily_charge_nan(row):
    """Check if the daily charge is NaN."""
    return pd.isna(row["Daily charge"])


def all_pricing_columns_nan(row):
    """Check if all variable-rate pricing columns are NaN."""
    pricing_columns = [
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
        "Discount per unit",
        "Discount per day",
        "Discount from total",
        "Discount - Other",
        "Controlled - Off peak",
        "Controlled - Shoulder",
        "Controlled - Peak",
    ]
    return row[pricing_columns].isna().all()


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


def has_night_only_rate(row):
    """Check if the plan has a night-only rate."""
    return not pd.isna(row["Night only"])


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


def show_plan(plan_id, full_df, dropna=True):
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


def row_to_plan(row):
    """
    Converts a DataFrame row to an ElectricityPlan instance.
    Args:
        row: pd.Series, a row from the electricity plan DataFrame

    Returns:
        ElectricityPlan: an instantiated object of ElectricityPlan
    """
    pricing_dict = {}
    for key in [
        "Uncontrolled",
        "All inclusive",
        "Day",
        "Night",
        "Controlled",
    ]:
        if not pd.isna(row.get(key)):
            pricing_dict[key] = row[key]

    return ElectricityPlan(
        name=str(row["PlanId"]),
        daily_charge=row["Daily charge"],
        nzd_per_kwh=pricing_dict,
    )


def get_filtered_df(path=LOCAL_TARIFF_DATA_PATH):
    """
    Load, process, and return a filtered DataFrame based on the tariff data.

    Returns:
    --------
    pd.DataFrame : The filtered DataFrame after applying the filters.
    """
    full_df = pd.read_csv(path)

    full_df = full_df.loc[full_df["Energy type"] == "electricity"].copy()

    for col in NUMERICAL_COLUMNS:
        full_df[col] = full_df[col].apply(
            lambda x: np.mean(eval_or_return(x)) if pd.notnull(x) else x
        )

    full_df["EDB"] = full_df["Network location names"].apply(map_locations_to_edb)

    full_df = full_df[
        full_df.apply(open_plans, axis=1)
    ]  # Exclude plans where retailer is not accepting new customers
    full_df = full_df[
        ~full_df["Network location names"].apply(contains_exclude_patterns)
    ]

    full_df.loc[:, "Network location names"] = full_df[
        "Network location names"
    ].str.split(",")
    full_df = full_df.explode("Network location names")
    full_df.loc[:, "Network location names"] = full_df[
        "Network location names"
    ].str.strip()
    full_df = full_df.reset_index(drop=True)

    retailer_locs = full_df["Retailer location name"].unique()
    network_locs = full_df["Network location names"].unique()
    logger.info("There are %s unique retailer locations", len(retailer_locs))
    logger.info("There are %s unique network locations", len(network_locs))

    filters = (
        (~full_df["Fixed term"])
        & (~full_df["Low user"])
        & (~full_df["Name"].str.contains("Energy Plus", na=False))
        & (
            ~full_df["Name"]
            .str.lower()
            .str.contains("no electric hot water cylinder", na=False)
        )
        & (~full_df["Name"].str.lower().str.contains("broadband", na=False))
        & full_df.apply(issimple, axis=1)
        & (~full_df.apply(daily_charge_nan, axis=1))
        & (~full_df.apply(all_pricing_columns_nan, axis=1))
        & (~full_df.apply(has_night_only_rate, axis=1))
    )

    return full_df[filters]


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


def generate_pdf_from_png(output_dir, output_pdf):
    """
    Generate a PDF from a directory of PNG files.

    Parameters
    ----------
    output_dir : str
        The directory containing the PNG files to convert to PDF.

    output_pdf : str
        The output PDF file to generate.

    Returns
    -------
    None
    """
    png_files = [
        os.path.join(output_dir, file)
        for file in os.listdir(output_dir)
        if file.endswith(".png")
    ]
    img2pdf_logger = logging.getLogger("img2pdf")
    img2pdf_logger.setLevel(logging.ERROR)
    with open(output_pdf, "wb") as f:
        f.write(img2pdf.convert(png_files))
    img2pdf_logger.setLevel(logging.WARNING)
    logger.info("PDF generated: %s", output_pdf)


def clear_output_dir(output_dir):
    """
    Attempts to delete all files in the output directory.
    If a file cannot be deleted (e.g., it is open in another process),
    logs an error message indicating the file should be closed.

    Parameters:
    -----------
    output_dir : str
        The directory containing the files to delete.
    """
    for file in os.listdir(output_dir):
        file_path = os.path.join(output_dir, file)
        try:
            os.remove(file_path)
        except PermissionError:
            logger.error(
                "Could not delete %s. Please close the file and try again.", file_path
            )
        except (
            OSError
        ) as os_err:  # Catching specific exception instead of broad Exception
            logger.error("An error occurred while deleting %s: %s", file_path, os_err)


def main():
    """
    Main function to process the electricity tariff data and plot the results.
    """
    my_df = get_filtered_df()

    my_edb_boundaries_gdf = load_and_transform_shapefile(EDB_REGION_SHAPEFILE)
    my_edb_boundaries_gdf.loc[
        my_edb_boundaries_gdf["name"] == "CentraLines Ltd", "name"
    ] = "Centralines Ltd"

    clear_output_dir(OUTPUT_DIR)

    for my_edb in sorted(my_edb_boundaries_gdf["name"].unique()):
        if my_edb == "Stewart Island Electrical Supply Authority":
            continue
        logger.info("Processing EDB: %s", my_edb)
        plot_subset(
            my_df, my_edb, hue_column="Network location names", output_dir=OUTPUT_DIR
        )

    generate_pdf_from_png(OUTPUT_DIR, f"{OUTPUT_DIR}/{OUTPUT_DIR}.pdf")


if __name__ == "__main__":
    main()
