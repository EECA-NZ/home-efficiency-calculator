"""
Test energy generation profile and behaviour of the SolarAnswers class.
"""

# pylint: disable=no-member

from pytest import approx

from app.models.user_answers import SolarAnswers, YourHomeAnswers
from app.services.get_energy_plans import get_energy_plan

MY_ENERGY_PLAN = get_energy_plan("6012", "None")

YOUR_HOME = YourHomeAnswers(
    people_in_house=4,
    postcode="6012",
    disconnect_gas=True,
)

SOLAR = SolarAnswers(
    has_solar=True,
)


def test_total_generation():
    """
    Test the total solar generation
    for the default your_home which
    is in Wellington.
    """
    total_generation = SOLAR.energy_generation(
        YOUR_HOME
    ).solar_generation_kwh.fixed_time_generation_kwh.sum()
    assert SOLAR.has_solar
    assert total_generation == approx(6779.137958683977)
