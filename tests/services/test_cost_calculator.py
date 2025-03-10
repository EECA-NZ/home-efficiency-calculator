"""
Tests for the cost calculator module.
"""

from app.services.configuration import (
    get_default_heating_answers,
    get_default_solar_answers,
    get_default_your_home_answers,
)
from app.services.cost_calculator import generate_savings_options


def test_savings_options():
    """
    Test creating savings options for space heating.
    """
    heating_answers = get_default_heating_answers()
    your_home = get_default_your_home_answers()
    solar = get_default_solar_answers()
    options = generate_savings_options(
        heating_answers, "main_heating_source", your_home, solar
    )
    assert options is not None
