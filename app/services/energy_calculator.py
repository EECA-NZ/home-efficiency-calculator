"""
This module provides functions to estimate a household's yearly fuel usage profile.
"""

# pylint: disable=too-many-locals

from app.constants import DAYS_IN_YEAR, EMISSIONS_FACTORS
from app.models.hourly_profiles.get_base_demand_profile import (
    other_electricity_energy_usage_profile,
)
from app.models.usage_profiles import YearlyFuelUsageProfile
from app.models.user_answers import HouseholdAnswers, SolarAnswers
from app.services.helpers import (
    get_attr_with_fallback,
    get_profile_or_empty,
    get_solar_answers,
    round_floats_to_2_dp,
)
from app.services.postcode_lookups.get_climate_zone import climate_zone
from app.services.solar_calculator.solar_diverter import (
    reroute_hot_water_to_solar_if_applicable,
)


def uses_electricity(answers: HouseholdAnswers) -> bool:
    """
    Return True if the household uses electricity.
    """
    return answers is not None


def uses_natural_gas(answers: HouseholdAnswers, use_alternatives: bool = False) -> bool:
    """
    Return True if the household uses natural gas, handling missing sections.
    """
    main_heating_source = get_attr_with_fallback(
        answers.heating, "main_heating_source", use_alternatives
    )
    hot_water_heating_source = get_attr_with_fallback(
        answers.hot_water, "hot_water_heating_source", use_alternatives
    )
    cooktop = get_attr_with_fallback(answers.cooktop, "cooktop", use_alternatives)

    return any(
        [
            main_heating_source == "Piped gas heater",
            hot_water_heating_source
            in ["Piped gas hot water cylinder", "Piped gas instantaneous"],
            cooktop == "Piped gas",
        ]
    )


def uses_lpg(answers: HouseholdAnswers, use_alternatives: bool = False) -> bool:
    """
    Return True if the household uses LPG, handling missing sections.
    """
    main_heating_source = get_attr_with_fallback(
        answers.heating, "main_heating_source", use_alternatives
    )
    hot_water_heating_source = get_attr_with_fallback(
        answers.hot_water, "hot_water_heating_source", use_alternatives
    )
    cooktop = get_attr_with_fallback(answers.cooktop, "cooktop", use_alternatives)

    return any(
        [
            main_heating_source == "Bottled gas heater",
            hot_water_heating_source == "Bottled gas instantaneous",
            cooktop == "Bottled gas",
        ]
    )


def estimate_usage_from_answers(
    answers: HouseholdAnswers,
    use_alternatives: bool = False,
    round_to_2dp: bool = False,
    include_other_electricity: bool = False,
    use_solar_diverter: bool = True,
) -> YearlyFuelUsageProfile:
    """
    Estimate the household's yearly fuel usage profile.
    """
    your_home = answers.your_home
    heating = answers.heating
    hot_water = answers.hot_water
    cooktop = answers.cooktop
    driving = answers.driving
    solar = SolarAnswers(**get_solar_answers(answers))
    solar_aware = solar.add_solar if solar else False
    cz = climate_zone(your_home.postcode)

    # Get energy usage profiles for each section of the household
    heating_profile = get_profile_or_empty(
        heating, your_home, solar_aware, use_alternatives
    )
    hot_water_profile = get_profile_or_empty(
        hot_water, your_home, solar_aware, use_alternatives
    )
    cooktop_profile = get_profile_or_empty(
        cooktop, your_home, solar_aware, use_alternatives
    )
    driving_profile = get_profile_or_empty(
        driving, your_home, solar_aware, use_alternatives
    )
    solar_profile = (
        solar.energy_generation(your_home) if solar else YearlyFuelUsageProfile()
    )
    other_profile = (
        other_electricity_energy_usage_profile()
        if include_other_electricity
        else YearlyFuelUsageProfile()
    )

    # Determine fixed charges
    elx_connection_days = DAYS_IN_YEAR if uses_electricity(answers) else 0
    lpg_tanks_rental_days = DAYS_IN_YEAR if uses_lpg(answers, use_alternatives) else 0
    natural_gas_connection_days = (
        DAYS_IN_YEAR if uses_natural_gas(answers, use_alternatives) else 0
    )

    profiles = [
        heating_profile,
        hot_water_profile,
        cooktop_profile,
        driving_profile,
        solar_profile,
        other_profile,
    ]

    if solar_aware and use_solar_diverter:
        rerouted_hot_water_electricity = reroute_hot_water_to_solar_if_applicable(
            hw_electricity_kwh=hot_water_profile.electricity_kwh,
            solar_generation_kwh=solar_profile.solar_generation_kwh,
            other_electricity_kwh=heating_profile.electricity_kwh
            + cooktop_profile.electricity_kwh
            + driving_profile.electricity_kwh
            + other_profile.electricity_kwh,
            hot_water_heating_source=hot_water.alternative_hot_water_heating_source,
            household_size=your_home.people_in_house,
            climate_zone=cz,
        )
        hot_water_profile.electricity_kwh = rerouted_hot_water_electricity

    # Variable electricity usage
    electricity_kwh = sum(profile.electricity_kwh for profile in profiles)

    # Solar electricity generation
    solar_generation_kwh = sum(profile.solar_generation_kwh for profile in profiles)

    # Natural gas and LPG usage
    natural_gas_kwh = (
        heating_profile.natural_gas_kwh
        + hot_water_profile.natural_gas_kwh
        + cooktop_profile.natural_gas_kwh
        + driving_profile.natural_gas_kwh
    )
    lpg_kwh = (
        heating_profile.lpg_kwh
        + hot_water_profile.lpg_kwh
        + cooktop_profile.lpg_kwh
        + driving_profile.lpg_kwh
    )

    # Wood usage only considered for heating
    wood_kwh = heating_profile.wood_kwh if heating else 0

    result = {
        "elx_connection_days": elx_connection_days,
        "electricity_kwh": electricity_kwh,
        "solar_generation_kwh": solar_generation_kwh,
        "natural_gas_connection_days": natural_gas_connection_days,
        "natural_gas_kwh": natural_gas_kwh,
        "lpg_tanks_rental_days": lpg_tanks_rental_days,
        "lpg_kwh": lpg_kwh,
        "wood_kwh": wood_kwh,
        "petrol_litres": driving_profile.petrol_litres,
        "diesel_litres": driving_profile.diesel_litres,
        "public_ev_charger_kwh": driving_profile.public_ev_charger_kwh,
        "thousand_km": driving_profile.thousand_km,
    }

    if round_to_2dp:
        result = round_floats_to_2_dp(result)

    return YearlyFuelUsageProfile(**result)


def emissions_kg_co2e(usage_profile: YearlyFuelUsageProfile) -> float:
    """
    Return the household's yearly CO2 emissions in kg.
    """
    components = [
        (-usage_profile.solar_generation_kwh.total, "electricity_kg_co2e_per_kwh"),
        (usage_profile.electricity_kwh.annual_kwh, "electricity_kg_co2e_per_kwh"),
        (usage_profile.natural_gas_kwh, "natural_gas_kg_co2e_per_kwh"),
        (usage_profile.lpg_kwh, "lpg_kg_co2e_per_kwh"),
        (usage_profile.wood_kwh, "wood_kg_co2e_per_kwh"),
        (usage_profile.petrol_litres, "petrol_kg_co2e_per_litre"),
        (usage_profile.diesel_litres, "diesel_kg_co2e_per_litre"),
        (usage_profile.public_ev_charger_kwh, "electricity_kg_co2e_per_kwh"),
    ]

    total_emissions = sum(
        usage * EMISSIONS_FACTORS.get(factor_name, 0)
        for usage, factor_name in components
    )
    return total_emissions
