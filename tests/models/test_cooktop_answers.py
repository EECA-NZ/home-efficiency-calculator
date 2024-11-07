"""
Test energy consumption profile and behaviour of the CooktopAnswers class.
"""

from pytest import approx, raises

from app.constants import DAYS_IN_YEAR
from app.models.user_answers import CooktopAnswers, YourHomeAnswers
from app.services.configuration import (
    get_default_cooktop_answers,
    get_default_your_home_answers,
)


def test_invalid_cooktop_type():
    """
    Test that an invalid cooktop type raises a ValueError.
    """
    your_home = YourHomeAnswers(
        people_in_house=3,
        postcode="1234",
        disconnect_gas=True,
    )
    cooktop_answers = CooktopAnswers(
        cooktop="Piped gas",
        alternative_cooktop="Piped gas",
    )
    setattr(cooktop_answers, "cooktop", "Invalid type")
    setattr(cooktop_answers, "alternative_cooktop", "Invalid type")
    with raises(ValueError, match="Unknown cooktop type: Invalid type"):
        cooktop_answers.energy_usage_pattern(your_home)


def test_cooking_energy_usage():
    """
    Test the energy usage pattern for cooking.
    """
    your_home = get_default_your_home_answers()
    cooktop = get_default_cooktop_answers()

    # Modeled energy use in kWh for each cooktop type. This is based
    # on a linearized energy use model that preserves the average
    # household energy use for cooking. (See 'Cooking' sheet of
    # supporting workbook.)
    expected_energy_use = {
        "Electric induction": [159, 239, 319, 398, 478, 558],
        "Piped gas": [412, 618, 824, 1030, 1236, 1442],
        "Bottled gas": [412, 618, 824, 1030, 1236, 1442, 1648],
        "Electric (coil or ceramic)": [176, 264, 352, 440, 528, 617],
    }

    # Expected field values based on cooktop type
    expected_values = {
        "Electric induction": {
            "elx_connection_days": DAYS_IN_YEAR,
            "flexible_kwh": 0,
            "natural_gas_kwh": 0,
            "lpg_kwh": 0,
            "natural_gas_connection_days": 0,
            "lpg_tanks_rental_days": 0,
        },
        "Piped gas": {
            "elx_connection_days": 0,
            "inflexible_day_kwh": 0,
            "flexible_kwh": 0,
            "lpg_kwh": 0,
            "natural_gas_connection_days": DAYS_IN_YEAR,
            "lpg_tanks_rental_days": 0,
        },
        "Bottled gas": {
            "elx_connection_days": 0,
            "inflexible_day_kwh": 0,
            "flexible_kwh": 0,
            "natural_gas_connection_days": 0,
            "lpg_tanks_rental_days": DAYS_IN_YEAR,
        },
        "Electric (coil or ceramic)": {
            "elx_connection_days": DAYS_IN_YEAR,
            "flexible_kwh": 0,
            "natural_gas_kwh": 0,
            "lpg_kwh": 0,
            "natural_gas_connection_days": 0,
            "lpg_tanks_rental_days": 0,
        },
    }

    for cooktop_type, energy_use_values in expected_energy_use.items():
        cooktop.cooktop = cooktop_type
        for i, expected_kwh in enumerate(energy_use_values):
            your_home.people_in_house = i + 1
            cooktop_energy_use = cooktop.energy_usage_pattern(your_home)

            # Assertions for expected energy usage (day_kwh, lpg_kwh, natural_gas_kwh)
            if cooktop_type in ["Electric induction", "Electric (coil or ceramic)"]:
                assert cooktop_energy_use.inflexible_day_kwh == approx(
                    expected_kwh, rel=1e-2
                )
            elif cooktop_type == "Piped gas":
                assert cooktop_energy_use.natural_gas_kwh == approx(
                    expected_kwh, rel=1e-2
                )
            elif cooktop_type == "Bottled gas":
                assert cooktop_energy_use.lpg_kwh == approx(expected_kwh, rel=1e-2)

            # General assertions based on the cooktop type
            for field, expected_value in expected_values[cooktop_type].items():
                assert (
                    getattr(cooktop_energy_use, field) == expected_value
                ), f"{field} failed for {cooktop_type}"
