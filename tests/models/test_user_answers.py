"""
Test the HouseholdAnswers class.
"""

from app.models.user_answers import HouseholdAnswers
from app.services.configuration import (
    get_default_cooktop_answers,
    get_default_driving_answers,
    get_default_heating_answers,
    get_default_hot_water_answers,
    get_default_solar_answers,
    get_default_your_home_answers,
)


def test_create_household_profile_answers():
    """
    Test the creation of a household profile answers object.
    """
    household_profile = HouseholdAnswers(
        your_home=get_default_your_home_answers(),
        heating=get_default_heating_answers(),
        hot_water=get_default_hot_water_answers(),
        cooktop=get_default_cooktop_answers(),
        driving=get_default_driving_answers(),
        solar=get_default_solar_answers(),
    )
    assert household_profile.your_home.people_in_house == 3
    assert household_profile.your_home.postcode == "0000"
    assert household_profile.driving.vehicle_type == "Electric"
