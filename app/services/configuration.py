"""
Configuration functions including default values for energy plans, usage profiles, and answers.
"""

from ..models.energy_plans import (
    ElectricityPlan,
    NaturalGasPlan,
    LPGPlan,
    WoodPrice,
    PetrolPrice,
    DieselPrice,
)
from ..models.usage_profiles import HouseholdYearlyFuelUsageProfile
from ..models.user_answers import YourHomeAnswers, HeatingAnswers
from ..models.user_answers import HotWaterAnswers, CooktopAnswers
from ..models.user_answers import DrivingAnswers, SolarAnswers


def get_default_electricity_plan():
    """
    Return a default electricity plan.
    """
    return ElectricityPlan(
        name="Default Electricity Plan",
        nzd_per_day_kwh=0.20,
        nzd_per_night_kwh=0.18,
        nzd_per_controlled_kwh=0.15,
        daily_charge=1.25,
    )


def get_default_natural_gas_plan():
    """
    Return a default natural gas plan.
    """
    return NaturalGasPlan(
        name="Default Natural Gas Plan", per_natural_gas_kwh=0.10, daily_charge=1.5
    )


def get_default_lpg_plan():
    """
    Return a default LPG plan.
    """
    return LPGPlan(name="Default LPG Plan", per_lpg_kwh=0.25, daily_charge=80 / 365.25)


def get_default_wood_price():
    """
    Return a default wood plan.
    """
    return WoodPrice(
        name="Default Wood Price",
        per_wood_kwh=0.05,
    )


def get_default_petrol_price():
    """
    Return a default petrol plan.
    """
    return PetrolPrice(
        name="Default Petrol Price",
        per_petrol_litre=1.50,
    )


def get_default_diesel_price():
    """
    Return a default diesel plan.
    """
    return DieselPrice(
        name="Default Diesel Price",
        per_diesel_litre=1.25,
    )


def get_default_usage_profile():
    """
    Return a default energy usage profile.
    """
    return HouseholdYearlyFuelUsageProfile(
        elx_connection_days=365,
        day_kwh=2000,
        flexible_kwh=1000,
        natural_gas_connection_days=0,
        natural_gas_kwh=0,
        lpg_tank_rental_days=0,
        lpg_kwh=0,
        wood_kwh=0,
        petrol_litres=1000,
        diesel_litres=0,
    )


def get_default_your_home_answers():
    """
    Return a default 'your home' answers object.
    """
    return YourHomeAnswers(
        people_in_house=4, postcode="0000", disconnect_gas=False, user_provided=False
    )


def get_default_heating_answers():
    """
    Return a default 'heating' answers object.
    """
    return HeatingAnswers(
        main_heating_source="Electric heater",
        alternative_main_heating_source="Heat pump",
        heating_during_day="5-7 days a week",
        insulation_quality="Moderately insulated",
        user_provided=False,
    )


def get_default_hot_water_answers():
    """
    Return a default 'hot water' answers object.
    """
    return HotWaterAnswers(
        hot_water_usage="Average",
        hot_water_heating_source="Electric hot water cylinder",
        alternative_hot_water_heating_source="Hot water heat pump",
        user_provided=False,
    )


def get_default_cooktop_answers():
    """
    Return a default 'cooktop' answers object.
    """
    return CooktopAnswers(
        cooktop="Piped gas",
        alternative_cooktop="Electric induction",
        user_provided=False,
    )


def get_default_driving_answers():
    """
    Return a default 'driving' answers object.
    """
    return DrivingAnswers(
        vehicle_type="Petrol",
        alternative_vehicle_type="Electric",
        vehicle_size="Medium",
        km_per_week="200",
        user_provided=False,
    )


def get_default_solar_answers():
    """
    Return a default 'solar' answers object.
    """
    return SolarAnswers(
        hasSolar=False,
        user_provided=False,
    )


def get_default_household_energy_profile():
    """
    Return a default overall household answers object.
    """
    return {
        "your_home": get_default_your_home_answers(),
        "heating": get_default_heating_answers(),
        "hot_water": get_default_hot_water_answers(),
        "cooktop": get_default_cooktop_answers(),
        "driving": get_default_driving_answers(),
        "solar": get_default_solar_answers(),
        "usage_profile": get_default_usage_profile(),
    }
