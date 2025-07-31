"""
Default answers for the components of a household energy profile.
"""

from ...models.user_answers import (
    CooktopAnswers,
    DrivingAnswers,
    HeatingAnswers,
    HotWaterAnswers,
    HouseholdAnswers,
    OtherAnswers,
    SolarAnswers,
    YourHomeAnswers,
)
from ...services.energy_calculator import estimate_usage_from_answers

_DEFAULT_ANSWER_FACTORIES = {
    "your_home": lambda: YourHomeAnswers(people_in_house=3, postcode="6012"),
    "heating": lambda: HeatingAnswers(
        main_heating_source="Heat pump",
        alternative_main_heating_source="Heat pump",
        heating_during_day="Never",
        insulation_quality="Moderately insulated",
    ),
    "hot_water": lambda: HotWaterAnswers(
        hot_water_usage="Average",
        hot_water_heating_source="Electric hot water cylinder",
        alternative_hot_water_heating_source="Hot water heat pump",
    ),
    "cooktop": lambda: CooktopAnswers(
        cooktop="Electric (coil or ceramic)",
        alternative_cooktop="Electric induction",
    ),
    "driving": lambda: DrivingAnswers(
        vehicle_size="Medium",
        km_per_week="200",
        vehicle_type="Electric",
        alternative_vehicle_type="Electric",
    ),
    "solar": lambda: SolarAnswers(add_solar=False),
    "other": lambda: OtherAnswers(fixed_cost_changes=False),
}


def get_default_answer_section(section_name: str):
    """
    Return the default answer object for a specific section (e.g. 'heating').
    """
    if section_name not in _DEFAULT_ANSWER_FACTORIES:
        raise ValueError(f"No default available for section: {section_name}")
    return _DEFAULT_ANSWER_FACTORIES[section_name]()


def get_default_household_answers() -> HouseholdAnswers:
    """
    Return a default overall household answers object.
    """
    return HouseholdAnswers(
        **{name: factory() for name, factory in _DEFAULT_ANSWER_FACTORIES.items()}
    )


def get_default_usage_profile():
    """
    Return a default household yearly fuel usage profile.
    """
    household_profile = get_default_household_answers()
    return estimate_usage_from_answers(household_profile)
