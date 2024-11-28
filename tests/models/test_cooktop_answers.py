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
from app.services.cost_calculator import calculate_savings_for_option
from app.services.get_energy_plans import get_energy_plan

MY_ENERGY_PLAN = get_energy_plan("6012", "None")

YOUR_HOME = YourHomeAnswers(
    people_in_house=4,
    postcode="6012",
    disconnect_gas=True,
)

COOKTOP = CooktopAnswers(
    cooktop="Piped gas",
    alternative_cooktop="Electric induction",
)


def test_invalid_cooktop_type():
    """
    Test that an invalid cooktop type raises a ValueError.
    """
    your_home = YourHomeAnswers(
        people_in_house=3,
        postcode="9016",
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
    # household energy use for cooking, by the linearity of expectation.
    # (See 'Cooking' sheet of supporting workbook.)
    expected_energy_use = {
        "Electric induction": [159, 239, 319, 398, 478, 558],
        "Piped gas": [412, 618, 824, 1030, 1236, 1442],
        "Bottled gas": [412, 618, 824, 1030, 1236, 1442],
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


def manual_cost_calculation_natural_gas():
    """
    A manual calculation of the annual running
    cost for a natural gas cooktop
    """
    energy_plan = get_energy_plan("6012", "None")
    natural_gas_kwh = COOKTOP.energy_usage_pattern(YOUR_HOME).natural_gas_kwh
    natural_gas_cost_per_kwh = energy_plan.natural_gas_plan.nzd_per_kwh["Uncontrolled"]
    annual_running_cost = natural_gas_kwh * natural_gas_cost_per_kwh
    return annual_running_cost


def manual_cost_calculation_electric_induction():
    """
    A manual calculation of the annual running
    cost for an electric induction cooktop
    """
    energy_plan = get_energy_plan("6012", "None")
    inflexible_day_kwh = COOKTOP.energy_usage_pattern(
        YOUR_HOME, use_alternative=True
    ).inflexible_day_kwh
    inflexible_kwh_cost_per_kwh = energy_plan.electricity_plan.nzd_per_kwh["Day"]
    annual_running_cost = inflexible_day_kwh * inflexible_kwh_cost_per_kwh
    return annual_running_cost


def test_cost_savings_calculations():
    """
    Test the savings calculations for a small petrol car
    and a small electric car, comparing with a manual calculation.
    """
    gas_energy_costs = MY_ENERGY_PLAN.calculate_cost(
        COOKTOP.energy_usage_pattern(YOUR_HOME)
    )
    induction_energy_costs = MY_ENERGY_PLAN.calculate_cost(
        COOKTOP.energy_usage_pattern(YOUR_HOME, use_alternative=True)
    )
    calculated_savings = calculate_savings_for_option(
        "Electric induction", "cooktop", COOKTOP, YOUR_HOME
    )
    assert gas_energy_costs[1] == approx(
        calculated_savings["variable_cost_nzd"]["current"]
    )
    assert gas_energy_costs[1] == approx(manual_cost_calculation_natural_gas())
    assert induction_energy_costs[1] == approx(
        calculated_savings["variable_cost_nzd"]["alternative"]
    )
    assert induction_energy_costs[1] == approx(
        manual_cost_calculation_electric_induction()
    )
