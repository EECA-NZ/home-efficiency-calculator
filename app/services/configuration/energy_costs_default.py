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

from ...models.energy_plans import (
    DieselPrice,
    ElectricityPlan,
    LPGPlan,
    NaturalGasPlan,
    NonEnergyVehicleCosts,
    PetrolPrice,
    PublicChargingPrice,
    WoodPrice,
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
        daily_charge=2.0,
        nzd_per_kwh={
            "Day": 0.242,
            "Night": 0.18,
        },
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


def get_default_public_ev_charger_rate():
    """
    Return a default public EV charger rate.

    Placeholder value of 80c/kWh. (ChargeNet price for Destination chargers)
    """
    return PublicChargingPrice(
        name="Default Public EV Charger Rate",
        per_kwh=0.80,
    )


def get_default_annual_non_energy_no_vehicle_costs():
    """
    Return a default set of annual non-energy costs
    for no vehicle.
    """
    return NonEnergyVehicleCosts(
        name="Vehicle Other Costs for no Vehicle",
        nzd_per_year_licensing=0.0,
        nzd_per_year_servicing_cost=0.0,
        nzd_per_000_km_road_user_charges=0.0,
    )


def get_default_annual_non_energy_petrol_vehicle_costs():
    """
    Return a default set of annual non-energy costs
    for a petrol vehicle.
    """
    return NonEnergyVehicleCosts(
        name="Default Petrol Vehicle Other Costs",
        nzd_per_year_licensing=107.09,
        nzd_per_year_servicing_cost=1133.15,
        nzd_per_000_km_road_user_charges=0,
    )


def get_default_annual_non_energy_diesel_vehicle_costs():
    """
    Return a default set of annual non-energy costs
    for a diesel vehicle.
    """
    return NonEnergyVehicleCosts(
        name="Default Diesel Vehicle Other Costs",
        nzd_per_year_licensing=174.92,
        nzd_per_year_servicing_cost=1133.15,
        nzd_per_000_km_road_user_charges=76,
    )


def get_default_annual_non_energy_hybrid_vehicle_costs():
    """
    Return a default set of annual non-energy costs
    for a hybrid vehicle.
    """
    return NonEnergyVehicleCosts(
        name="Default Hybrid Vehicle Other Costs",
        nzd_per_year_licensing=107.09,
        nzd_per_year_servicing_cost=1133.15,
        nzd_per_000_km_road_user_charges=0,
    )


def get_default_annual_non_energy_phev_costs():
    """
    Return a default set of annual non-energy costs
    for a plug-in hybrid vehicle.
    """
    return NonEnergyVehicleCosts(
        name="Default Plug-In-Hybrid Vehicle Other Costs",
        nzd_per_year_licensing=107.09,
        nzd_per_year_servicing_cost=1133.15,
        nzd_per_000_km_road_user_charges=53,
    )


def get_default_annual_non_energy_electric_vehicle_costs():
    """
    Return a default set of annual non-energy costs
    for an electric vehicle.
    """
    return NonEnergyVehicleCosts(
        name="Default Electric Vehicle Other Costs",
        nzd_per_year_licensing=107.09,
        nzd_per_year_servicing_cost=684.4,
        nzd_per_000_km_road_user_charges=76,
    )


def get_default_annual_other_vehicle_costs(vehicle_type):
    """
    Return a default set of annual non-energy costs
    for the provided vehicle type.
    """
    if vehicle_type == "None":
        return get_default_annual_non_energy_no_vehicle_costs()
    if vehicle_type == "Petrol":
        return get_default_annual_non_energy_petrol_vehicle_costs()
    if vehicle_type == "Diesel":
        return get_default_annual_non_energy_diesel_vehicle_costs()
    if vehicle_type == "Hybrid":
        return get_default_annual_non_energy_hybrid_vehicle_costs()
    if vehicle_type == "Plug-in hybrid":
        return get_default_annual_non_energy_phev_costs()
    if vehicle_type == "Electric":
        return get_default_annual_non_energy_electric_vehicle_costs()
    raise ValueError(f"Unknown vehicle type: {vehicle_type}")


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
        "public_charging_price": get_default_public_ev_charger_rate(),
        "other_vehicle_costs": {
            "None": get_default_annual_non_energy_no_vehicle_costs(),
            "Petrol": get_default_annual_non_energy_petrol_vehicle_costs(),
            "Diesel": get_default_annual_non_energy_diesel_vehicle_costs(),
            "Hybrid": get_default_annual_non_energy_hybrid_vehicle_costs(),
            "Plug-in hybrid": get_default_annual_non_energy_phev_costs(),
            "Electric": get_default_annual_non_energy_electric_vehicle_costs(),
        },
    }