"""
Test energy consumption profile and behaviour of the CooktopAnswers class.
"""

# pylint: disable=no-member

import numpy as np
from pytest import approx, raises

from app.constants import DAYS_IN_YEAR
from app.models.user_answers import CooktopAnswers, SolarAnswers, YourHomeAnswers
from app.services.configuration import get_default_answer_section
from app.services.cost_calculator import calculate_savings_for_option
from app.services.postcode_lookups.get_energy_plans import get_energy_plan

MY_ENERGY_PLAN = get_energy_plan("6012", "None")

YOUR_HOME = YourHomeAnswers(
    people_in_house=4,
    postcode="6012",
)

COOKTOP = CooktopAnswers(
    cooktop="Piped gas",
    alternative_cooktop="Electric induction",
)

SOLAR = SolarAnswers(add_solar=False)


def validate_energy_usage_fields(energy_usage, expected_fields, cooktop_type):
    """
    Validate additional fields of the energy usage profile.
    """
    for field, expected_value in expected_fields.items():
        actual_value = getattr(energy_usage, field)
        if isinstance(expected_value, dict):
            for subfield, subexpected in expected_value.items():
                sub_attr = getattr(actual_value, subfield)
                # If sub_attr is an ndarray, use np.sum to get a scalar.
                actual_subvalue = (
                    np.sum(sub_attr) if isinstance(sub_attr, np.ndarray) else sub_attr
                )
                assert (
                    actual_subvalue == subexpected
                ), f"{field}.{subfield} failed for {cooktop_type}"
        else:
            assert actual_value == expected_value, f"{field} failed for {cooktop_type}"


def test_invalid_cooktop_type():
    """
    Test that an invalid cooktop type raises a ValueError.
    """
    your_home = YourHomeAnswers(
        people_in_house=3,
        postcode="9016",
    )
    cooktop_answers = CooktopAnswers(
        cooktop="Piped gas",
        alternative_cooktop="Piped gas",
    )
    setattr(cooktop_answers, "cooktop", "Invalid type")
    setattr(cooktop_answers, "alternative_cooktop", "Invalid type")
    with raises(ValueError, match="Unknown cooktop type: Invalid type"):
        cooktop_answers.energy_usage_pattern(your_home, SOLAR)


def test_cooking_energy_usage():
    """
    Test the energy usage pattern for cooking.
    """
    your_home = get_default_answer_section("your_home")
    cooktop = get_default_answer_section("cooktop")

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

    # Expected field values based on cooktop type.
    expected_values = {
        "Electric induction": {
            "elx_connection_days": DAYS_IN_YEAR,
            "electricity_kwh": {
                "shift_abl_kwh": 0,
            },
            "natural_gas_kwh": 0,
            "lpg_kwh": 0,
            "natural_gas_connection_days": 0,
            "lpg_tanks_rental_days": 0,
        },
        "Piped gas": {
            "elx_connection_days": 0,
            "electricity_kwh": {
                "fixed_day_kwh": 0,
                "shift_abl_kwh": 0,
            },
            "natural_gas_connection_days": DAYS_IN_YEAR,
            "lpg_tanks_rental_days": 0,
        },
        "Bottled gas": {
            "elx_connection_days": 0,
            "electricity_kwh": {
                "fixed_day_kwh": 0,
                "shift_abl_kwh": 0,
            },
            "natural_gas_connection_days": 0,
            "lpg_tanks_rental_days": DAYS_IN_YEAR,
        },
        "Electric (coil or ceramic)": {
            "elx_connection_days": DAYS_IN_YEAR,
            "electricity_kwh": {
                "shift_abl_kwh": 0,
            },
            "natural_gas_kwh": 0,
            "lpg_kwh": 0,
            "natural_gas_connection_days": 0,
            "lpg_tanks_rental_days": 0,
        },
    }

    # Mapping cooktop type to a function that extracts the primary energy use value.
    energy_usage_getters = {
        "Electric induction": lambda usage: np.sum(usage.electricity_kwh.annual_kwh),
        "Electric (coil or ceramic)": lambda usage: np.sum(
            usage.electricity_kwh.annual_kwh
        ),
        "Piped gas": lambda usage: usage.natural_gas_kwh,
        "Bottled gas": lambda usage: usage.lpg_kwh,
    }

    for cooktop_type, energy_use_values in expected_energy_use.items():
        cooktop.cooktop = cooktop_type
        for i, expected_kwh in enumerate(energy_use_values):
            your_home.people_in_house = i + 1
            cooktop_energy_use = cooktop.energy_usage_pattern(your_home, SOLAR)

            energy_value = energy_usage_getters[cooktop_type](cooktop_energy_use)
            assert energy_value == approx(expected_kwh, rel=1e-2)

            validate_energy_usage_fields(
                cooktop_energy_use, expected_values[cooktop_type], cooktop_type
            )


def manual_cost_calculation_natural_gas():
    """
    A manual calculation of the annual running cost for a natural gas cooktop.
    """
    energy_plan = get_energy_plan("6012", "None")
    natural_gas_kwh = COOKTOP.energy_usage_pattern(YOUR_HOME, SOLAR).natural_gas_kwh
    natural_gas_cost_per_kwh = energy_plan.natural_gas_plan.import_rates["Uncontrolled"]
    annual_running_cost = natural_gas_kwh * natural_gas_cost_per_kwh
    return annual_running_cost


def manual_cost_calculation_electric_induction():
    """
    A manual calculation of the annual running cost for an electric induction cooktop.
    """
    energy_plan = get_energy_plan("6012", "None")
    day_usage = COOKTOP.energy_usage_pattern(
        YOUR_HOME, SOLAR, use_alternative=True
    ).electricity_kwh.fixed_day_kwh
    cost_per_kwh_day = energy_plan.electricity_plan.import_rates["All inclusive"]
    annual_running_cost = day_usage * cost_per_kwh_day
    return annual_running_cost


def test_cost_savings_calculations():
    """
    Test the savings calculations for a cooktop, comparing with a manual calculation.
    """
    gas_energy_costs = MY_ENERGY_PLAN.calculate_cost(
        COOKTOP.energy_usage_pattern(YOUR_HOME, SOLAR)
    )
    induction_energy_costs = MY_ENERGY_PLAN.calculate_cost(
        COOKTOP.energy_usage_pattern(YOUR_HOME, SOLAR, use_alternative=True)
    )
    calculated_savings = calculate_savings_for_option(
        "Electric induction", "cooktop", COOKTOP, YOUR_HOME, SOLAR
    )
    assert gas_energy_costs.variable_cost_nzd == approx(
        calculated_savings["variable_cost_nzd"]["current"]
    )
    assert gas_energy_costs.variable_cost_nzd == approx(
        manual_cost_calculation_natural_gas()
    )
    assert induction_energy_costs.variable_cost_nzd == approx(
        calculated_savings["variable_cost_nzd"]["alternative"]
    )
    assert induction_energy_costs.variable_cost_nzd == approx(
        manual_cost_calculation_electric_induction()
    )
