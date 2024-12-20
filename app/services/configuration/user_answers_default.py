"""
Default answers for the components of a household energy profile.
"""

from ...models.user_answers import (
    CooktopAnswers,
    DrivingAnswers,
    HeatingAnswers,
    HotWaterAnswers,
    HouseholdAnswers,
    SolarAnswers,
    YourHomeAnswers,
)
from ...services.energy_calculator import estimate_usage_from_profile


def get_default_your_home_answers():
    """
    Return a default 'your home' answers object.

    Postcode is for Wellington, New Zealand.
    """
    return YourHomeAnswers(people_in_house=3, postcode="6012", disconnect_gas=False)


def get_default_heating_answers():
    """
    Return a default 'heating' answers object.
    """
    return HeatingAnswers(
        main_heating_source="Heat pump",
        heating_during_day="Never",
        insulation_quality="Moderately insulated",
    )


def get_default_hot_water_answers():
    """
    Return a default 'hot water' answers object.
    """
    return HotWaterAnswers(
        hot_water_usage="Average",
        hot_water_heating_source="Electric hot water cylinder",
    )


def get_default_cooktop_answers():
    """
    Return a default 'cooktop' answers object.
    """
    return CooktopAnswers(
        cooktop="Electric (coil or ceramic)",
    )


def get_default_driving_answers():
    """
    Return a default 'driving' answers object.
    """
    return DrivingAnswers(
        vehicle_size="Medium",
        km_per_week="200",
        vehicle_type="Electric",
    )


def get_default_solar_answers():
    """
    Return a default 'solar' answers object.
    """
    return SolarAnswers(
        hasSolar=False,
    )


def get_default_household_answers():
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
    }


def get_default_usage_profile():
    """
    Return a default household yearly fuel usage profile.
    """
    household_profile = HouseholdAnswers(
        your_home=get_default_your_home_answers(),
        heating=get_default_heating_answers(),
        hot_water=get_default_hot_water_answers(),
        cooktop=get_default_cooktop_answers(),
        driving=get_default_driving_answers(),
        solar=get_default_solar_answers(),
    )
    household_energy_use = estimate_usage_from_profile(household_profile)
    return household_energy_use
