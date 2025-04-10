"""
Tests for the cost calculator module.
"""

from app.services.configuration import get_default_answer_section
from app.services.cost_calculator import generate_savings_options


def test_savings_options():
    """
    Test creating savings options for space heating.
    """
    heating_answers = get_default_answer_section("heating")
    your_home = get_default_answer_section("your_home")
    solar = get_default_answer_section("solar")
    options = generate_savings_options(
        heating_answers, "main_heating_source", your_home, solar
    )
    assert options is not None
