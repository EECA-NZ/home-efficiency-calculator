"""
Helper functions for analyzing and optimizing electricity plans.
"""

import logging
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# import app.services.configuration as cfg
from app.models.energy_plans import ElectricityPlan
from app.models.user_answers import (
    CooktopAnswers,
    DrivingAnswers,
    HeatingAnswers,
    HotWaterAnswers,
    HouseholdAnswers,
    SolarAnswers,
    YourHomeAnswers,
)
from app.services.energy_calculator import estimate_usage_from_profile
from app.services.helpers import other_electricity_energy_usage_profile
from data_analysis.plan_choice_helpers.constants import NUMERICAL_COLUMNS
from data_analysis.plan_choice_helpers.data_loading import eval_or_return
from data_analysis.plan_choice_helpers.plan_filters import (
    is_simple_all_inclusive,
    is_simple_controlled_uncontrolled,
    is_simple_day_night,
    is_simple_night_all_inclusive,
    is_simple_night_uncontrolled,
    is_simple_uncontrolled,
    open_plans,
)
from data_analysis.plan_choice_helpers.plan_utils import map_locations_to_edb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


def filter_electricity_plans(full_df):
    """
    Load, process, and return a filtered DataFrame based
    on the tariff data. This allows us to focus on the most
    relevant plans that are available to most users in each
    EDB. We are not in a position to identify precisely which
    plans are available to each user, so we make some general
    assumptions to filter the plans. This limitation must be
    made clear in the disclaimers on the public-facing tool.

    We only include electricity plans for networks that are
    identified in the 'edb_to_locations' dictionary in
    plan_choice_helpers/constants.py, excluding, for
    instance, plans for rural / small capacity / low density
    network locations. We also exclude plans that are not
    accepting new customers.

    We apply filters to remove complex / ambiguous plans:
      * Fixed term plans which lock in a user;
      * Low-user plans which are being phased out;
      * "No electric hot water cylinder" plans;
      * Plans that are bundled with Broadband.

    We also exclude plans that don't conform to straightforward
    pricing structures, e.g. plans with complex controlled
    rates that are season-dependent and dual-fuel plans.
    Note however that we make a separate assumption that a
    dual-fuel discount applies to natural gas plans (all
    users assumed to be connected to the electricity grid).

    Returns:
    --------
    pd.DataFrame : The filtered DataFrame after applying the filters.
    """
    full_df = full_df.loc[full_df["Energy type"] == "electricity"].copy()

    for col in NUMERICAL_COLUMNS:
        full_df[col] = full_df[col].apply(
            lambda x: np.mean(eval_or_return(x)) if pd.notnull(x) else x
        )

    # Split the network location names into distinct rows
    full_df.loc[:, "Network location names"] = full_df[
        "Network location names"
    ].str.split(",")
    full_df = full_df.explode("Network location names")
    full_df.loc[:, "Network location names"] = full_df[
        "Network location names"
    ].str.strip()
    full_df = full_df.reset_index(drop=True)

    full_df["EDB"] = full_df["Network location names"].apply(map_locations_to_edb)

    # Drop tariffs for low density network locations
    ignore_networks = full_df.loc[
        full_df.EDB == "Ignore", "Network location names"
    ].unique()
    logger.info("Dropping tariffs for the following networks:")
    for network in ignore_networks:
        logger.info("    Dropping tariffs for %s", network)
    full_df = full_df[full_df["EDB"] != "Ignore"]

    # Exclude plans where retailer is not accepting new customers
    full_df = full_df[full_df.apply(open_plans, axis=1)]

    filters = (
        (~full_df["Fixed term"])
        & (~full_df["Low user"])
        & (
            ~full_df["Name"]
            .str.lower()
            .str.contains("no electric hot water cylinder", na=False)
        )
        & (~full_df["Name"].str.lower().str.contains("broadband", na=False))
        & (
            full_df.apply(is_simple_all_inclusive, axis=1)
            | full_df.apply(is_simple_controlled_uncontrolled, axis=1)
            | full_df.apply(is_simple_day_night, axis=1)
            | full_df.apply(is_simple_uncontrolled, axis=1)
            | full_df.apply(is_simple_night_all_inclusive, axis=1)
            | full_df.apply(is_simple_night_uncontrolled, axis=1)
        )
    )
    full_df = full_df[filters]

    # Log number of unique retailer and network locations
    retailer_locs = full_df["Retailer location name"].unique()
    network_locs = full_df["Network location names"].unique()
    logger.info("There are %s unique retailer locations", len(retailer_locs))
    logger.info("There are %s unique network locations", len(network_locs))

    full_df.reset_index(drop=True, inplace=True)
    full_df.drop_duplicates(inplace=True)

    return full_df


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


def load_electrified_household_energy_usage_profile():
    """
    Load household fuel usage profile reflecting the 'default'
    answers. These correspond to a typical but highly electrified
    household.

    Returns:
    YearlyFuelUsageProfile object representing the household's
    fuel usage profile.
    """
    household_profile = HouseholdAnswers(
        your_home=YourHomeAnswers(
            people_in_house=3,
            postcode="6012",
            disconnect_gas=True,
        ),
        heating=HeatingAnswers(
            main_heating_source="Heat pump",
            heating_during_day="Never",
            insulation_quality="Moderately insulated",
        ),
        hot_water=HotWaterAnswers(
            hot_water_usage="Average",
            hot_water_heating_source="Electric hot water cylinder",
        ),
        cooktop=CooktopAnswers(
            cooktop="Electric (coil or ceramic)",
        ),
        driving=DrivingAnswers(
            vehicle_size="Small",
            km_per_week="200",
            vehicle_type="Electric",
        ),
        solar=SolarAnswers(
            hasSolar=False,
        ),
    )
    household_energy_use = estimate_usage_from_profile(household_profile)
    other_electricity_use = other_electricity_energy_usage_profile()
    household_energy_use.inflexible_day_kwh += other_electricity_use.inflexible_day_kwh
    household_energy_use.flexible_kwh += other_electricity_use.flexible_kwh
    return household_energy_use
