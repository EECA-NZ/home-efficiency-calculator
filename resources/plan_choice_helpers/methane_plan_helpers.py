"""
Helper functions for analyzing and optimizing electricity plans.
"""

import logging

import numpy as np
import pandas as pd

# import app.services.configuration as cfg
from app.models.energy_plans import NaturalGasPlan
from app.models.user_answers import (
    CooktopAnswers,
    DrivingAnswers,
    HeatingAnswers,
    HotWaterAnswers,
    HouseholdAnswers,
    SolarAnswers,
    YourHomeAnswers,
)
from app.services.energy_calculator import estimate_usage_from_answers
from resources.plan_choice_helpers.constants import NUMERICAL_COLUMNS
from resources.plan_choice_helpers.data_loading import eval_or_return
from resources.plan_choice_helpers.plan_filters import (
    is_big_four_retailer,
    is_simple_all_inclusive,
    is_simple_controlled_uncontrolled,
    is_simple_day_night,
    is_simple_night_all_inclusive,
    is_simple_night_uncontrolled,
    is_simple_uncontrolled,
    open_plans,
)
from resources.plan_choice_helpers.plan_utils import map_locations_to_edb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def row_to_plan(row):
    """
    Converts a DataFrame row to an NaturalGasPlan instance.
    Args:
        row: pd.Series, a row from the electricity plan DataFrame

    Returns:
        NaturalGasPlan: an instantiated object of NaturalGasPlan
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

    return NaturalGasPlan(
        name=str(row["PlanId"]),
        fixed_rate=row["Daily charge"],
        import_rates=pricing_dict,
    )


def filter_methane_plans(full_df):
    """
    Load, process, and return a filtered DataFrame based
    on the tariff data. This allows us to focus on the most
    relevant plans that are available to most users in each
    EDB. We are not in a position to identify precisely which
    plans are available to each user, so we make some general
    assumptions to filter the plans. This limitation must be
    made clear in the disclaimers on the public-facing tool.

    Returns:
    --------
    pd.DataFrame : The filtered DataFrame after applying the filters.
    """
    full_df = full_df.loc[full_df["Energy type"] == "gas"].copy()

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

    # Assemble full set of unique retailer and network locations
    all_retailer_locs = full_df["Retailer location name"].unique()
    all_network_locs = full_df["Network location names"].unique()

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
        & (full_df.apply(is_big_four_retailer, axis=1))
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
    dropped_retailer_locs = set(all_retailer_locs) - set(retailer_locs)
    dropped_network_locs = set(all_network_locs) - set(network_locs)
    logger.info("Dropped %s retailer locations", len(dropped_retailer_locs))
    for loc in dropped_retailer_locs:
        logger.info("    Dropped %s", loc)
    logger.info("Dropped %s network locations", len(dropped_network_locs))
    for loc in dropped_network_locs:
        logger.info("    Dropped %s", loc)

    full_df.reset_index(drop=True, inplace=True)
    full_df.drop_duplicates(inplace=True)

    return full_df


def load_gas_using_household_energy_usage_profile():
    """
    Load household fuel usage profile reflecting a typical
    *gas-using household*. This energy profile is used to
    select a representative natural gas plan available in each
    EDB region.

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
            hot_water_heating_source="Piped gas instantaneous",
        ),
        cooktop=CooktopAnswers(
            cooktop="Piped gas",
        ),
        driving=DrivingAnswers(
            vehicle_size="Small",
            km_per_week="200",
            vehicle_type="Petrol",
        ),
        solar=SolarAnswers(
            add_solar=False,
        ),
    )
    return estimate_usage_from_answers(household_profile)
