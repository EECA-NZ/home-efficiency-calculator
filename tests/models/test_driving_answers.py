"""
Test energy consumption profile and behaviour of the DrivingAnswers class.
"""

# pylint: disable=no-member

from pytest import approx

import app.services.configuration as cfg
from app.constants import (
    BATTERY_ECONOMY_KWH_PER_100KM,
    DAYS_IN_YEAR,
    EV_PUBLIC_CHARGING_FRACTION,
    FUEL_CONSUMPTION_LITRES_PER_100KM,
)
from app.models.energy_plans import HouseholdEnergyPlan
from app.models.usage_profiles import ElectricityUsage, YearlyFuelUsageProfile
from app.models.user_answers import DrivingAnswers, SolarAnswers, YourHomeAnswers
from app.services.cost_calculator import calculate_savings_for_option
from app.services.get_energy_plans import postcode_to_electricity_plan
from app.services.usage_profile_helpers import flat_day_night_profiles

day_profile, night_profile = flat_day_night_profiles()

MY_ELECTRICITY_PLAN = postcode_to_electricity_plan("6012")

YOUR_HOME = YourHomeAnswers(
    people_in_house=4,
    postcode="6012",
    disconnect_gas=True,
)

DRIVING = DrivingAnswers(
    vehicle_size="Small",
    km_per_week="200",
    vehicle_type="Petrol",
)

SOLAR = SolarAnswers(add_solar=False)


def test_small_electric_car():
    """
    Test the energy usage pattern for a small electric car.
    """
    my_driving_answers = DrivingAnswers(
        vehicle_type="Electric", vehicle_size="Small", km_per_week="200"
    )
    my_driving_energy_usage = my_driving_answers.energy_usage_pattern(YOUR_HOME, SOLAR)
    assert (
        my_driving_energy_usage.electricity_kwh.shift_able_kwh
        + my_driving_energy_usage.public_ev_charger_kwh
    ) / DAYS_IN_YEAR == approx(5.114202500144706)


def manual_calculation_petrol():
    """
    A manual calculation of the annual running
    cost for a small petrol car.
    """
    licensing = 107.09
    ruc = 0
    scheduled_servicing = 1133.15
    fuel_consumption_l_per_100km = FUEL_CONSUMPTION_LITRES_PER_100KM["Petrol"]["Small"]
    nzd_per_petrol_litre = 2.78
    annual_distance_km = float(DRIVING.km_per_week) / 7 * DAYS_IN_YEAR
    annual_fuel_consumption_l = annual_distance_km / 100 * fuel_consumption_l_per_100km
    annual_running_cost = (
        annual_fuel_consumption_l * nzd_per_petrol_litre
        + licensing
        + ruc * annual_distance_km / 1000
        + scheduled_servicing
    )
    return annual_running_cost


def manual_calculation_ev(home_elx_cost_per_kwh):
    """
    A manual calculation of the annual running
    cost for a small electric car.
    """
    licensing = 107.09
    ruc = 76
    scheduled_servicing = 684.4
    battery_economy_kwh_per_100km = BATTERY_ECONOMY_KWH_PER_100KM["Electric"]["Small"]
    ev_public_charging_fraction = 0.2
    public_elx_cost_per_kwh = 0.80
    annual_distance_km = float(DRIVING.km_per_week) / 7 * DAYS_IN_YEAR
    annual_elx_consumption_kwh = (
        annual_distance_km / 100 * battery_economy_kwh_per_100km
    )
    public_elx_consumption_kwh = (
        annual_elx_consumption_kwh * ev_public_charging_fraction
    )
    home_elx_consumption_kwh = annual_elx_consumption_kwh - public_elx_consumption_kwh
    annual_public_elx_cost = public_elx_consumption_kwh * public_elx_cost_per_kwh
    annual_home_elx_cost = home_elx_consumption_kwh * home_elx_cost_per_kwh
    annual_running_cost = (
        annual_public_elx_cost
        + annual_home_elx_cost
        + licensing
        + ruc * annual_distance_km / 1000
        + scheduled_servicing
    )
    return annual_running_cost


def test_savings_calculations():
    """
    Test the savings calculations for a small petrol car
    and a small electric car, comparing with a manual calculation.
    """
    petrol_plan = HouseholdEnergyPlan(
        name="Basic Household Energy Plan",
        electricity_plan=MY_ELECTRICITY_PLAN,
        natural_gas_plan=cfg.get_default_natural_gas_plan(),
        lpg_plan=cfg.get_default_lpg_plan(),
        wood_price=cfg.get_default_wood_price(),
        petrol_price=cfg.get_default_petrol_price(),
        diesel_price=cfg.get_default_diesel_price(),
        public_charging_price=cfg.get_default_public_ev_charger_rate(),
        other_vehicle_costs=cfg.get_default_annual_other_vehicle_costs("Petrol"),
    )

    electric_plan = HouseholdEnergyPlan(
        name="Basic Household Energy Plan",
        electricity_plan=MY_ELECTRICITY_PLAN,
        natural_gas_plan=cfg.get_default_natural_gas_plan(),
        lpg_plan=cfg.get_default_lpg_plan(),
        wood_price=cfg.get_default_wood_price(),
        petrol_price=cfg.get_default_petrol_price(),
        diesel_price=cfg.get_default_diesel_price(),
        public_charging_price=cfg.get_default_public_ev_charger_rate(),
        other_vehicle_costs=cfg.get_default_annual_other_vehicle_costs("Electric"),
    )

    thousand_km = float(DRIVING.km_per_week) / 7 * DAYS_IN_YEAR / 1000
    petrol_litres = (
        float(DRIVING.km_per_week)
        / 7
        * DAYS_IN_YEAR
        / 100
        * FUEL_CONSUMPTION_LITRES_PER_100KM["Petrol"]["Small"]
    )
    petrol_energy_costs = petrol_plan.calculate_cost(
        YearlyFuelUsageProfile(
            elx_connection_days=365.25,
            electricity_kwh=ElectricityUsage(),
            natural_gas_connection_days=0,
            natural_gas_kwh=0,
            lpg_tanks_rental_days=0,
            lpg_kwh=0,
            wood_kwh=0,
            petrol_litres=petrol_litres,
            diesel_litres=0,
            public_ev_charger_kwh=0,
            thousand_km=thousand_km,
        )
    )
    total_kwh = (
        float(DRIVING.km_per_week)
        / 7
        * DAYS_IN_YEAR
        / 100
        * BATTERY_ECONOMY_KWH_PER_100KM["Electric"]["Small"]
    )
    public_ev_charger_kwh = total_kwh * EV_PUBLIC_CHARGING_FRACTION
    anytime_kwh = total_kwh - public_ev_charger_kwh
    electric_energy_costs = electric_plan.calculate_cost(
        YearlyFuelUsageProfile(
            elx_connection_days=365.25,
            electricity_kwh=ElectricityUsage(
                shift_able_kwh=anytime_kwh, shift_able_profile=day_profile
            ),
            natural_gas_connection_days=0,
            natural_gas_kwh=0,
            lpg_tanks_rental_days=0,
            lpg_kwh=0,
            wood_kwh=0,
            petrol_litres=0,
            diesel_litres=0,
            public_ev_charger_kwh=public_ev_charger_kwh,
            thousand_km=thousand_km,
        )
    )
    calculated_savings = calculate_savings_for_option(
        "Electric", "vehicle_type", DRIVING, YOUR_HOME, SOLAR
    )

    assert petrol_energy_costs.variable_cost_nzd == approx(
        calculated_savings["variable_cost_nzd"]["current"]
    )
    assert petrol_energy_costs.variable_cost_nzd == approx(manual_calculation_petrol())
    assert electric_energy_costs.variable_cost_nzd == approx(
        calculated_savings["variable_cost_nzd"]["alternative"]
    )
    assert (
        electric_energy_costs.variable_cost_nzd
        == approx(manual_calculation_ev(0.17204))
    ) or (
        electric_energy_costs.variable_cost_nzd == approx(manual_calculation_ev(0.18))
    )
