"""
Test energy consumption profile and behaviour of the HeatingAnswers class.
"""

from pytest import approx

from app.models.user_answers import HeatingAnswers
from app.services.configuration import get_default_household_answers, get_default_plans


def test_space_heating_energy_usage():
    """
    Test the energy usage pattern for space heating.
    """
    answers = get_default_household_answers()
    plans = get_default_plans()

    main_heating_sources = [
        "Heat pump",
        "Electric heater",
        "Wood burner",
        "Piped gas heater",
        "Bottled gas heater",
    ]

    expected_energy_cost = {
        "Heat pump": {"electricity_variable_cost_nzd": approx(148.8459)},
        "Electric heater": {"electricity_variable_cost_nzd": approx(739.7639)},
        "Wood burner": {"wood_variable_cost_nzd": approx(501.34405)},
        "Piped gas heater": {"natural_gas_variable_cost_nzd": approx(420.3204)},
        "Bottled gas heater": {"lpg_variable_cost_nzd": approx(932.3471)},
    }

    for main_heating_source in main_heating_sources:
        heating = HeatingAnswers(
            main_heating_source=main_heating_source,
            alternative_main_heating_source="Heat pump",
            heating_during_day="5-7 days a week",
            insulation_quality="Moderately insulated",
        )
        # determine energy usage pattern
        heating_energy_use = heating.energy_usage_pattern(
            answers["your_home"], answers["solar"]
        )

        # calculate costs by fuel
        heating_electricity_variable_cost = (
            plans["electricity_plan"]
            .calculate_cost(heating_energy_use)
            .variable_cost_nzd
        )

        heating_lpg_variable_cost = (
            plans["lpg_plan"].calculate_cost(heating_energy_use).variable_cost_nzd
        )

        heating_natural_gas_variable_cost = (
            plans["natural_gas_plan"]
            .calculate_cost(heating_energy_use)
            .variable_cost_nzd
        )

        heating_wood_variable_cost = (
            plans["wood_price"].calculate_cost(heating_energy_use).variable_cost_nzd
        )

        # compare with expected costs
        expected_electricity = expected_energy_cost[main_heating_source].get(
            "electricity_variable_cost_nzd", 0
        )
        expected_lpg = expected_energy_cost[main_heating_source].get(
            "lpg_variable_cost_nzd", 0
        )
        expected_natural_gas = expected_energy_cost[main_heating_source].get(
            "natural_gas_variable_cost_nzd", 0
        )
        expected_wood = expected_energy_cost[main_heating_source].get(
            "wood_variable_cost_nzd", 0
        )

        assert heating_electricity_variable_cost == approx(expected_electricity)
        assert heating_lpg_variable_cost == approx(expected_lpg)
        assert heating_natural_gas_variable_cost == approx(expected_natural_gas)
        assert heating_wood_variable_cost == approx(expected_wood)
