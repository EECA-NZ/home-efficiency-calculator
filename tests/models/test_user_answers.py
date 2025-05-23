"""
Test the HouseholdAnswers class.
"""

from app.models.user_answers import HouseholdAnswers
from app.services.configuration import get_default_answer_section


def test_create_household_answers():
    """
    Test the creation of a houshold answers object.
    """
    household_answers = HouseholdAnswers(
        your_home=get_default_answer_section("your_home"),
        heating=get_default_answer_section("heating"),
        hot_water=get_default_answer_section("hot_water"),
        cooktop=get_default_answer_section("cooktop"),
        driving=get_default_answer_section("driving"),
        solar=get_default_answer_section("solar"),
    )
    assert household_answers.your_home.people_in_house == 3
    assert household_answers.your_home.postcode == "6012"
    assert household_answers.driving.vehicle_type == "Electric"
