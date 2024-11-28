"""
Module for helper functions related to loading data.
"""

import ast
import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def load_tariff_data(path: str) -> pd.DataFrame:
    """
    Load the tariff data from a CSV file.

    Parameters
    ----------
    path : str
        The path to the CSV file.

    Returns
    -------
    pd.DataFrame
        The loaded DataFrame.

    Raises
    ------
    FileNotFoundError
        If the file at the specified path does not exist.
    """
    try:
        df = pd.read_csv(path)
        logger.info("Tariff data loaded from %s", path)
        return df
    except FileNotFoundError as e:
        logger.error("File not found: %s", path)
        raise e


def eval_or_return(x: Any) -> Any:
    """
    Evaluate a string as a Python literal if possible, otherwise return it as is.

    Parameters
    ----------
    x : Any
        The input value to evaluate.

    Returns
    -------
    Any
        The evaluated Python literal if x is a string that can be evaluated,
        otherwise x unchanged.
    """
    if isinstance(x, str):
        try:
            return ast.literal_eval(x)
        except (ValueError, SyntaxError):
            return x
    else:
        return x
