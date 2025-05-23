"""
Tests for the configuration module.
"""

from app.services.configuration import (
    get_default_answer_section,
    get_default_household_answers,
    get_default_plan,
)


def test_get_default_household_answers():
    """
    Test the get_default_household_answers function.
    """
    household_energy_profile = get_default_household_answers()
    assert household_energy_profile.your_home.people_in_house == 3


def test_get_default_electricity_plan():
    """
    Test the get_default_electricity_plan function.
    """
    electricity_plan = get_default_plan("electricity_plan")
    assert electricity_plan.name == "Default Electricity Plan"


def test_get_default_natural_gas_plan():
    """
    Test the get_default_natural_gas_plan function.
    """
    natural_gas_plan = get_default_plan("natural_gas_plan")
    assert natural_gas_plan.name == "Default Natural Gas Plan"


def test_get_default_lpg_plan():
    """
    Test the get_default_lpg_plan function.
    """
    lpg_plan = get_default_plan("lpg_plan")
    assert lpg_plan.name == "Default LPG Plan"


def test_get_default_answer_section_your_home():
    """
    Test the get_default_your_home_answers function.
    """
    your_home_answers = get_default_answer_section("your_home")
    assert your_home_answers.people_in_house == 3


def test_get_default_answer_section_heating():
    """
    Test the get_default_heating_answers function.
    """
    heating_answers = get_default_answer_section("heating")
    assert heating_answers.main_heating_source == "Heat pump"


def test_get_default_answer_section_hot_water():
    """
    Test the get_default_hot_water_answers function.
    """
    hot_water_answers = get_default_answer_section("hot_water")
    assert hot_water_answers.hot_water_heating_source == "Electric hot water cylinder"


def test_get_default_answer_section_cooktop():
    """
    Test the get_default_cooktop_answers function.
    """
    cooktop_answers = get_default_answer_section("cooktop")
    assert cooktop_answers.cooktop == "Electric (coil or ceramic)"


def test_get_default_answer_section_driving():
    """
    Test the get_default_driving_answers function.
    """
    driving_answers = get_default_answer_section("driving")
    assert driving_answers.vehicle_type == "Electric"


def test_get_default_answer_section_solar():
    """
    Test the get_default_solar_answers function.
    """
    solar_answers = get_default_answer_section("solar")
    assert solar_answers.add_solar is False
