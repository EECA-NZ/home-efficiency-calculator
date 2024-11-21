"""
Module for filtering functions used to exclude
electricity and natural gas plans based on
specific criteria.
"""

import logging

import pandas as pd

from data_analysis.plan_choice_helpers.constants import NUMERICAL_COLUMNS

logger = logging.getLogger(__name__)


def is_simple_all_inclusive(row: pd.Series) -> bool:
    """
    Check if the plan is a simple all-inclusive plan.

    Parameters
    ----------
    row : pd.Series
        A row from the DataFrame.

    Returns
    -------
    bool
        True if the plan is a simple all-inclusive plan, False otherwise.
    """
    all_inclusive_columns = ["All inclusive", "Daily charge"]
    other_pricing_columns = [
        x for x in NUMERICAL_COLUMNS if x not in all_inclusive_columns
    ]
    return pd.notnull(row["All inclusive"]) and row[other_pricing_columns].isna().all()


def is_simple_uncontrolled(row: pd.Series) -> bool:
    """
    Check if the plan is a simple uncontrolled plan.

    Parameters
    ----------
    row : pd.Series
        A row from the DataFrame.

    Returns
    -------
    bool
        True if the plan is a simple uncontrolled plan, False otherwise.
    """
    uncontrolled_columns = ["Uncontrolled", "Daily charge"]
    other_pricing_columns = [
        x for x in NUMERICAL_COLUMNS if x not in uncontrolled_columns
    ]
    return (
        pd.notnull(row["Uncontrolled"])
        and pd.notnull(row["Daily charge"])
        and row[other_pricing_columns].isna().all()
    )


def is_simple_controlled_uncontrolled(row: pd.Series) -> bool:
    """
    Check if the plan is a simple controlled and uncontrolled plan.

    Parameters
    ----------
    row : pd.Series
        A row from the DataFrame.

    Returns
    -------
    bool
        True if the plan has both 'Controlled' and 'Uncontrolled'
        rates and no other rates.
    """
    controlled_columns = ["Controlled", "Uncontrolled", "Daily charge"]
    other_columns = set(NUMERICAL_COLUMNS) - set(controlled_columns)
    return (
        pd.notnull(row["Controlled"])
        and pd.notnull(row["Uncontrolled"])
        and pd.notnull(row["Daily charge"])
        and row[list(other_columns)].isna().all()
    )


def is_simple_day_night(row: pd.Series) -> bool:
    """
    Check if the plan is a simple day/night plan.

    Parameters
    ----------
    row : pd.Series
        A row from the DataFrame.

    Returns
    -------
    bool
        True if the plan has 'Day' and 'Night' rates and no other rates.
    """
    day_night_columns = ["Day", "Night", "Daily charge"]
    other_columns = set(NUMERICAL_COLUMNS) - set(day_night_columns)
    return (
        pd.notnull(row["Day"])
        and pd.notnull(row["Night"])
        and pd.notnull(row["Daily charge"])
        and row[list(other_columns)].isna().all()
    )


def is_simple_night_all_inclusive(row: pd.Series) -> bool:
    """
    Check if the plan is a simple night and all-inclusive plan.

    Parameters
    ----------
    row : pd.Series
        A row from the DataFrame.

    Returns
    -------
    bool
        True if the plan has 'Night' and 'All inclusive' rates and no other rates.
    """
    night_all_inclusive_columns = ["Night", "All inclusive", "Daily charge"]
    other_columns = set(NUMERICAL_COLUMNS) - set(night_all_inclusive_columns)
    return (
        pd.notnull(row["Night"])
        and pd.notnull(row["All inclusive"])
        and pd.notnull(row["Daily charge"])
        and row[list(other_columns)].isna().all()
    )


def is_simple_night_uncontrolled(row: pd.Series) -> bool:
    """
    Check if the plan is a simple night and uncontrolled plan.

    Parameters
    ----------
    row : pd.Series
        A row from the DataFrame.

    Returns
    -------
    bool
        True if the plan has 'Night' and 'Uncontrolled' rates and no other rates.
    """
    night_uncontrolled_columns = ["Night", "Uncontrolled", "Daily charge"]
    other_columns = set(NUMERICAL_COLUMNS) - set(night_uncontrolled_columns)
    return (
        pd.notnull(row["Night"])
        and pd.notnull(row["Uncontrolled"])
        and pd.notnull(row["Daily charge"])
        and row[list(other_columns)].isna().all()
    )


def open_plans(row: pd.Series) -> bool:
    """
    Check if the plan is open for new customers.

    Parameters
    ----------
    row : pd.Series
        A row from the DataFrame.

    Returns
    -------
    bool
        True if the plan is open, False otherwise.
    """
    return "open" in row["Status"].lower()
