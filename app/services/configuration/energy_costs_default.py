"""
Configuration functions including default values for
energy plans, usage profiles, and answers.

The Rewiring Aotearoa analysis used the following:
    • Electricity variable cost: 24.2c/kWh or 18c/kWh off-peak/ripple.
    • Electricity connection cost: Not included in any calculations.
        (Homes are assumed on-grid in all cases.)
    • LPG variable cost: 24.4c/kWh.
    • LPG bottle rental (2 x 45kg bottles):
        $5.75 per bottle per month ($138 per year for two bottles).
    • Piped gas variable cost: 11c/kWh.
    • Piped gas connection cost: $1.60 per day ($587 per year).

We use average gst-inclusive costs for natural gas
in a dataset obtained from Powerswitch.

We use postcode -> EDB -> Electricity Plan mapping to determine
electricity plans for a given location using the Powerswitch data.

Petrol and Diesel pricing:

From MBIE: Average Petrol and Diesel Costs from 1/09/2023 to 23/08/2024
    • Diesel_discounted_retail_price_NZc.p.l = 216.1612458
    • Regular_Petrol_discounted_retail_price_NZc.p.l = 278.716297
Source:
    https://www.mbie.govt.nz/building-and-energy/
energy-and-natural-resources/energy-statistics-and-modelling/
energy-statistics/oil-statistics

Wood pricing:
    Figures justified by:

        Typical price per m³ from Consumer NZ:
        NZ$140 (hot mix price) and average of soft and
        hardwood prices (NZ$120 and NZ$160 respectively).

        Density for thrown volume and energy content from:
        Bittermann, W., & Suvorov, M. (2012, May 29).
        Quality standard for statistics on wood fuel
        consumption of households (taking into account
        the relative importance for the 20-20-20 goals):
        Working Group 2: Methodology. Statistics Austria;
        Statistical Office of the Republic of Slovenia.
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
        name="Default Natural Gas Plan",
        daily_charge=1.60,
        nzd_per_kwh={
            "Uncontrolled": 0.11,
        },
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
    Figures justified by:

        Typical price per m³ from Consumer NZ:
        NZ$140 (hot mix price) and average of soft and
        hardwood prices (NZ$120 and NZ$160 respectively).

        Density for thrown volume and energy content from:
        Bittermann, W., & Suvorov, M. (2012, May 29).
        Quality standard for statistics on wood fuel
        consumption of households (taking into account
        the relative importance for the 20-20-20 goals):
        Working Group 2: Methodology. Statistics Austria;
        Statistical Office of the Republic of Slovenia.

        ($/m3)(m3/kg)(kg/MJ)(MJ/kWh) = ($/kWh)
    """
    price_per_cubic_metre = 140
    thrown_density_kg_per_m3 = 300
    net_calorific_value_mj_per_kg = 16
    conversion_factor_mj_per_kwh = 3.6

    return WoodPrice(
        name="Default Wood Price",
        per_wood_kwh=price_per_cubic_metre
        / thrown_density_kg_per_m3
        / net_calorific_value_mj_per_kg
        * conversion_factor_mj_per_kwh,
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
