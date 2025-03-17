"""
Tests for the configuration module.
"""

from app.services.configuration import (
    get_default_cooktop_answers,
    get_default_driving_answers,
    get_default_electricity_plan,
    get_default_heating_answers,
    get_default_hot_water_answers,
    get_default_household_answers,
    get_default_lpg_plan,
    get_default_natural_gas_plan,
    get_default_solar_answers,
    get_default_your_home_answers,
)


def test_get_default_household_answers():
    """
    Test the get_default_household_answers function.
    """
    household_energy_profile = get_default_household_answers()
    assert household_energy_profile["your_home"].people_in_house == 3


def test_get_default_electricity_plan():
    """
    Test the get_default_electricity_plan function.
    """
    electricity_plan = get_default_electricity_plan()
    assert electricity_plan.name == "Default Electricity Plan"


def test_get_default_natural_gas_plan():
    """
    Test the get_default_natural_gas_plan function.
    """
    natural_gas_plan = get_default_natural_gas_plan()
    assert natural_gas_plan.name == "Default Natural Gas Plan"


def test_get_default_lpg_plan():
    """
    Test the get_default_lpg_plan function.
    """
    lpg_plan = get_default_lpg_plan()
    assert lpg_plan.name == "Default LPG Plan"


def test_get_default_your_home_answers():
    """
    Test the get_default_your_home_answers function.
    """
    your_home_answers = get_default_your_home_answers()
    assert your_home_answers.people_in_house == 3


def test_get_default_heating_answers():
    """
    Test the get_default_heating_answers function.
    """
    heating_answers = get_default_heating_answers()
    assert heating_answers.main_heating_source == "Heat pump"


def test_get_default_hot_water_answers():
    """
    Test the get_default_hot_water_answers function.
    """
    hot_water_answers = get_default_hot_water_answers()
    assert hot_water_answers.hot_water_heating_source == "Electric hot water cylinder"


def test_get_default_cooktop_answers():
    """
    Test the get_default_cooktop_answers function.
    """
    cooktop_answers = get_default_cooktop_answers()
    assert cooktop_answers.cooktop == "Electric (coil or ceramic)"


def test_get_default_driving_answers():
    """
    Test the get_default_driving_answers function.
    """
    driving_answers = get_default_driving_answers()
    assert driving_answers.vehicle_type == "Electric"


def test_get_default_solar_answers():
    """
    Test the get_default_solar_answers function.
    """
    solar_answers = get_default_solar_answers()
    assert solar_answers.has_solar is False
