"""
Configuration functions including default values for
energy plans, usage profiles, and answers.

Rewiring Aotearoa:
    • Electricity variable cost: 24.2c/kWh or 18c/kWh off-peak/ripple.
    • Electricity connection cost: Not included in any calculations.
        (Homes are assumed on-grid in all cases.)
    • Piped gas variable cost: 11c/kWh.
    • Piped gas connection cost: $1.60 per day ($587 per year).
    • LPG variable cost: 24.4c/kWh.
    • LPG bottle rental (2 x 45kg bottles):
        $5.75 per bottle per month ($138 per year for two bottles).

Petrol and Diesel pricing:

From MBIE: Average Petrol and Diesel Costs from 1/09/2023 to 23/08/2024
    • Diesel_discounted_retail_price_NZc.p.l = 216.1612458
    • Regular_Petrol_discounted_retail_price_NZc.p.l = 278.716297
Source:
    https://www.mbie.govt.nz/building-and-energy/
energy-and-natural-resources/energy-statistics-and-modelling/
energy-statistics/oil-statistics

Wood pricing:

Base this on:
    • Price per cord: NZD $375
    • Volume of a Cord = 128 cubic feet = 3.62m^3
    • Density of dry pine = 480 kg/m^3
    • Energy content of dry pine = 15 MJ / tonne
        = 15E6 / 3.6 / 1E6 = 4.17 kWh / kg

Exclude the following factor:
    • Efficiency of modern wood stove = 70%
We calculate the price per kWh of heat content in the wood and
account for the efficiency of a modern wood stove separately.
    
kWh per dollar = (
    Volume of a Cord *
    Density of dry pine *
    Energy content of dry pine *
    Efficiency of modern wood stove) / Price per cord
 = (3.62 * 480 * 4.17) / 375
 = 19.32 kWh per dollar

Inverting this gives $0.052 per kWh of heat in the wood.

This works out to $0.074 per kWh of heat output from a modern wood stove.
"""

from ..models.energy_plans import (
    DieselPrice,
    ElectricityPlan,
    LPGPlan,
    NaturalGasPlan,
    PetrolPrice,
    WoodPrice,
)
from ..models.usage_profiles import HouseholdYearlyFuelUsageProfile
from ..models.user_answers import (
    CooktopAnswers,
    DrivingAnswers,
    HeatingAnswers,
    HotWaterAnswers,
    SolarAnswers,
    YourHomeAnswers,
)


def get_default_electricity_plan():
    """
    Return a default electricity plan.

    Rewiring Aotearoa:
    • Electricity variable cost: 24.2c/kWh or 18c/kWh off-peak/ripple.
    • Electricity connection cost: Not included in any calculations.
        (Homes are assumed on-grid in all cases.)
    """
    return ElectricityPlan(
        name="Default Electricity Plan",
        nzd_per_day_kwh=0.242,
        nzd_per_night_kwh=0.18,
        nzd_per_controlled_kwh=0.18,
        daily_charge=2.0,
    )


def get_default_natural_gas_plan():
    """
    Return a default natural gas plan.

    Rewiring Aotearoa:
    • Piped gas variable cost: 11c/kWh.
    • Piped gas connection cost: $1.60 per day ($587 per year).
    """
    return NaturalGasPlan(
        name="Default Natural Gas Plan", per_natural_gas_kwh=0.11, daily_charge=1.6
    )


def get_default_lpg_plan():
    """
    Return a default LPG plan.

    Rewiring Aotearoa:
        • LPG variable cost: 24.4c/kWh.
        • LPG bottle rental (per 45kg bottle): two bottles at
            $5.75 per bottle per month ($69 per year per bottle).
    """
    return LPGPlan(
        name="Default LPG Plan", per_lpg_kwh=0.244, daily_charge=2 * 69 / 365.25
    )


def get_default_wood_price():
    """
    Return a default wood plan.

    Wood price: $0.074 per kWh for a modern wood stove with 70% efficiency.

    This is based on:
        • Price per cord: NZD $375
        • Volume of a Cord = 128 cubic feet = 3.62m^3
        • Density of dry pine = 480 kg/m^3
        • Energy content of dry pine = 15 MJ / tonne = 15E6 / 3.6E6 = 4.17 kWh / kg

    Exclude the following factor:
        • Efficiency of modern wood stove = 70%
    We calculate the price per kWh of heat content in the wood and
    account for the efficiency of a modern wood stove separately.

    kWh per dollar = (
        Volume of a Cord *
        Density of dry pine *
        Energy content of dry pine) / Price per cord

    = (3.62 * 480 * 4.17) / 375
    = 19.32 kWh per dollar

    Inverting this gives $0.052 per kWh of heat in the wood.
    This works out to $0.074 per kWh of heat output from a modern wood stove.
    """
    return WoodPrice(
        name="Default Wood Price",
        per_wood_kwh=0.052,
    )


def get_default_petrol_price():
    """
    Return a default petrol plan.

    From MBIE: Average of Petrol Costs from 1/09/2023 to 23/08/2024
    Regular_Petrol_discounted_retail_price_NZc.p.l = 278.716297
    """
    return PetrolPrice(
        name="Default Petrol Price",
        per_petrol_litre=2.78,
    )


def get_default_diesel_price():
    """
    Return a default diesel plan.

    From MBIE: Average of Diesel Costs from 1/09/2023 to 23/08/2024
    Diesel_discounted_retail_price_NZc.p.l = 216.1612458

    Add in RUCs (Road User Charges) for diesel vehicles.
    """
    return DieselPrice(
        name="Default Diesel Price",
        per_diesel_litre=2.16,
    )


def get_default_plans():
    """
    Return a default set of energy plans.

    Returns
    -------
    dict
        A dictionary of default energy plans.
    """
    return {
        "electricity_plan": get_default_electricity_plan(),
        "natural_gas_plan": get_default_natural_gas_plan(),
        "lpg_plan": get_default_lpg_plan(),
        "wood_price": get_default_wood_price(),
        "petrol_price": get_default_petrol_price(),
        "diesel_price": get_default_diesel_price(),
    }


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
        lpg_tanks_rental_days=0,
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
