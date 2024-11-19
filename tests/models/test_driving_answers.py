"""
Test energy consumption profile and behaviour of the DrivingAnswers class.
"""

from pytest import approx

import app.services.configuration as cfg
from app.constants import DAYS_IN_YEAR
from app.models.energy_plans import HouseholdEnergyPlan
from app.models.usage_profiles import YearlyFuelUsageProfile
from app.models.user_answers import DrivingAnswers, YourHomeAnswers
from app.services.cost_calculator import calculate_savings_for_option
from app.services.get_energy_plans import postcode_to_electricity_plan

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


def test_small_electric_car():
    """
    Test the energy usage pattern for a small electric car.
    """
    my_driving_answers = DrivingAnswers(
        vehicle_type="Electric",
        vehicle_size="Small",
        km_per_week="200",
    )
    my_driving_energy_usage = my_driving_answers.energy_usage_pattern(YOUR_HOME)

    assert (
        my_driving_energy_usage.flexible_kwh
        + my_driving_energy_usage.public_ev_charger_kwh
    ) / DAYS_IN_YEAR == approx(5)


def manual_calculation_petrol():
    """
    A manual calculation of the annual running
    cost for a small petrol car.
    """
    licensing = 107.09
    ruc = 0
    scheduled_servicing = 1133.15
    fuel_consumption_l_per_100km = 8
    assumed_distances_km_per_week = 200
    nzd_per_petrol_litre = 2.78
    annual_distance_km = assumed_distances_km_per_week / 7 * DAYS_IN_YEAR
    annual_fuel_consumption_l = annual_distance_km / 100 * fuel_consumption_l_per_100km
    annual_running_cost = (
        annual_fuel_consumption_l * nzd_per_petrol_litre
        + licensing
        + ruc * annual_distance_km / 1000
        + scheduled_servicing
    )
    return annual_running_cost


def manual_calculation_ev():
    """
    A manual calculation of the annual running
    cost for a small electric car.
    """
    licensing = 107.09
    ruc = 76
    scheduled_servicing = 684.4
    battery_economy_kwh_per_100km = 17.5
    assumed_distance_km_per_week = 200
    ev_public_charging_fraction = 0.2
    public_elx_cost_per_kwh = 0.80
    home_elx_cost_per_kwh = 0.20239999999999997
    annual_distance_km = assumed_distance_km_per_week / 7 * DAYS_IN_YEAR
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

    petrol_energy_costs = petrol_plan.calculate_cost(
        YearlyFuelUsageProfile(
            elx_connection_days=365.25,
            inflexible_day_kwh=0,
            flexible_kwh=0,
            natural_gas_connection_days=0,
            natural_gas_kwh=0,
            lpg_tanks_rental_days=0,
            lpg_kwh=0,
            wood_kwh=0,
            petrol_litres=834.8571428571429,
            diesel_litres=0,
            public_ev_charger_kwh=0,
            thousand_km=10.435714285714287,
        )
    )
    electric_energy_costs = electric_plan.calculate_cost(
        YearlyFuelUsageProfile(
            elx_connection_days=365.25,
            inflexible_day_kwh=0,
            flexible_kwh=1461,
            natural_gas_connection_days=0,
            natural_gas_kwh=0,
            lpg_tanks_rental_days=0,
            lpg_kwh=0,
            wood_kwh=0,
            petrol_litres=0,
            diesel_litres=0,
            public_ev_charger_kwh=365.25,
            thousand_km=10.435714285714287,
        )
    )
    calculated_savings = calculate_savings_for_option(
        "Electric", "vehicle_type", DRIVING, YOUR_HOME
    )

    assert petrol_energy_costs[1] == approx(
        calculated_savings["variable_cost_nzd"]["current"]
    )
    assert petrol_energy_costs[1] == approx(manual_calculation_petrol())
    assert electric_energy_costs[1] == approx(
        calculated_savings["variable_cost_nzd"]["alternative"]
    )
    assert electric_energy_costs[1] == approx(manual_calculation_ev())
