"""
This module provides functions to estimate a household's yearly fuel usage profile.
"""

# pylint: disable=too-many-locals

from app.constants import DAYS_IN_YEAR, EMISSIONS_FACTORS
from app.models.usage_profiles import (
    HouseholdYearlyFuelUsageProfile,
    YearlyFuelUsageProfile,
)
from app.models.user_answers import HouseholdAnswers
from app.services.helpers import round_floats_to_2_dp


def uses_electricity(profile: HouseholdAnswers) -> bool:
    """
    Return True if the household uses electricity.
    """
    return profile is not None


def uses_natural_gas(profile: HouseholdAnswers, use_alternatives: bool = False) -> bool:
    """
    Return True if the household uses natural gas, handling missing sections.
    """
    main_heating_source = (
        profile.heating.main_heating_source
        if profile.heating is not None and not use_alternatives
        else (
            profile.heating.alternative_main_heating_source
            if profile.heating is not None
            else None
        )
    )
    hot_water_heating_source = (
        profile.hot_water.hot_water_heating_source
        if profile.hot_water is not None and not use_alternatives
        else (
            profile.hot_water.alternative_hot_water_heating_source
            if profile.hot_water is not None
            else None
        )
    )
    cooktop = (
        profile.cooktop.cooktop
        if profile.cooktop is not None and not use_alternatives
        else (
            profile.cooktop.alternative_cooktop if profile.cooktop is not None else None
        )
    )

    return any(
        [
            main_heating_source == "Piped gas heater",
            hot_water_heating_source
            in ["Piped gas hot water cylinder", "Piped gas instantaneous"],
            cooktop == "Piped gas",
        ]
    )


def uses_lpg(profile: HouseholdAnswers, use_alternatives: bool = False) -> bool:
    """
    Return True if the household uses LPG, handling missing sections.
    """
    main_heating_source = (
        profile.heating.main_heating_source
        if profile.heating is not None and not use_alternatives
        else (
            profile.heating.alternative_main_heating_source
            if profile.heating is not None
            else None
        )
    )
    hot_water_heating_source = (
        profile.hot_water.hot_water_heating_source
        if profile.hot_water is not None and not use_alternatives
        else (
            profile.hot_water.alternative_hot_water_heating_source
            if profile.hot_water is not None
            else None
        )
    )
    cooktop = (
        profile.cooktop.cooktop
        if profile.cooktop is not None and not use_alternatives
        else (
            profile.cooktop.alternative_cooktop if profile.cooktop is not None else None
        )
    )

    return any(
        [
            main_heating_source == "Bottled gas heater",
            hot_water_heating_source == "Bottled gas instantaneous",
            cooktop == "Bottled gas",
        ]
    )


def estimate_usage_from_profile(
    answers: HouseholdAnswers,
    use_alternatives: bool = False,
    round_to_2dp: bool = False,
) -> HouseholdYearlyFuelUsageProfile:
    """
    Estimate the household's yearly fuel usage profile.
    """
    your_home = answers.your_home
    heating = answers.heating
    hot_water = answers.hot_water
    cooktop = answers.cooktop
    driving = answers.driving
    solar = answers.solar

    # Initialize the profiles with default empty profiles to handle None scenarios
    heating_profile = (
        heating.energy_usage_pattern(your_home, use_alternative=use_alternatives)
        if heating is not None
        and (
            not use_alternatives or heating.alternative_main_heating_source is not None
        )
        else YearlyFuelUsageProfile()
    )
    hot_water_profile = (
        hot_water.energy_usage_pattern(your_home, use_alternative=use_alternatives)
        if hot_water is not None
        and (
            not use_alternatives
            or hot_water.alternative_hot_water_heating_source is not None
        )
        else YearlyFuelUsageProfile()
    )
    cooktop_profile = (
        cooktop.energy_usage_pattern(your_home, use_alternative=use_alternatives)
        if cooktop is not None
        and (not use_alternatives or cooktop.alternative_cooktop is not None)
        else YearlyFuelUsageProfile()
    )
    driving_profile = (
        driving.energy_usage_pattern(your_home, use_alternative=use_alternatives)
        if driving is not None
        and (not use_alternatives or driving.alternative_vehicle_type is not None)
        else YearlyFuelUsageProfile()
    )
    # Assume solar_profile is handled similarly if needed
    # pylint: disable=unused-variable
    solar_profile = (
        solar.energy_generation(your_home) if solar else YearlyFuelUsageProfile()
    )

    # Determine fixed charges
    elx_connection_days = DAYS_IN_YEAR if uses_electricity(answers) else 0
    lpg_tanks_rental_days = DAYS_IN_YEAR if uses_lpg(answers, use_alternatives) else 0
    natural_gas_connection_days = (
        DAYS_IN_YEAR if uses_natural_gas(answers, use_alternatives) else 0
    )

    profiles = [heating_profile, hot_water_profile, cooktop_profile, driving_profile]

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

    return HouseholdYearlyFuelUsageProfile(**result)


def emissions_kg_co2e(usage_profile: YearlyFuelUsageProfile) -> float:
    """
    Return the household's yearly CO2 emissions in kg.
    """
    # List of emissions components
    components = [
        (-usage_profile.solar_generation_kwh.total, "electricity_kg_co2e_per_kwh"),
        (
            usage_profile.electricity_kwh.total_usage.sum(),
            "electricity_kg_co2e_per_kwh",
        ),
        (usage_profile.natural_gas_kwh, "natural_gas_kg_co2e_per_kwh"),
        (usage_profile.lpg_kwh, "lpg_kg_co2e_per_kwh"),
        (usage_profile.wood_kwh, "wood_kg_co2e_per_kwh"),
        (usage_profile.petrol_litres, "petrol_kg_co2e_per_litre"),
        (usage_profile.diesel_litres, "diesel_kg_co2e_per_litre"),
        (usage_profile.public_ev_charger_kwh, "electricity_kg_co2e_per_kwh"),
    ]

    # Calculate emissions with a default of 0 if the emission factor is missing
    total_emissions = sum(
        usage * EMISSIONS_FACTORS.get(emissions_factor_name, 0)
        for usage, emissions_factor_name in components
    )

    return total_emissions
