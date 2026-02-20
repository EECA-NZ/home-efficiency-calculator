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

from ...constants import DEFAULT_SOLAR_EXPORT_RATE
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


def _electricity():
    """
    Return a default electricity plan.

    Rewiring Aotearoa:
    • Electricity variable cost: 24.2c/kWh or 18c/kWh off-peak/ripple.
    • Electricity connection cost: Not included in any calculations.
      (Homes are assumed on-grid in all cases.)
    """
    return ElectricityPlan(
        name="Default Electricity Plan",
        fixed_rate=2.0,
        import_rates={"Day": 0.242, "Night": 0.18},
        export_rates={"Uncontrolled": DEFAULT_SOLAR_EXPORT_RATE},
    )


def _natural_gas():
    """
    Return a default natural gas plan.

    Rewiring Aotearoa:
    • Piped gas variable cost: 11c/kWh.
    • Piped gas connection cost: $1.60 per day ($587 per year).
    """
    return NaturalGasPlan(
        name="Default Natural Gas Plan",
        fixed_rate=1.60,
        import_rates={"Uncontrolled": 0.11},
    )


def _lpg():
    """
    Return a default LPG plan.

    Rewiring Aotearoa:
    • LPG variable cost: 24.4c/kWh.
    • LPG bottle rental (per 45kg bottle): two bottles at
      $5.75 per bottle per month ($69 per year per bottle).
    """
    return LPGPlan(
        name="Default LPG Plan",
        per_lpg_kwh=0.244,
        fixed_rate=2 * 69 / 365.25,
    )


def _wood():
    """
    Return a default wood price per kWh.

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

    ($/m³)(m³/kg)(kg/MJ)(MJ/kWh) = ($/kWh)
    """
    price_per_cubic_metre = 140
    thrown_density_kg_per_m3 = 307
    net_calorific_value_mj_per_kg = 14.3
    conversion_factor_mj_per_kwh = 3.6

    return WoodPrice(
        name="Default Wood Price",
        per_wood_kwh=price_per_cubic_metre
        / thrown_density_kg_per_m3
        / net_calorific_value_mj_per_kg
        * conversion_factor_mj_per_kwh,
    )


def _petrol():
    """
    Return a default petrol plan.

    From MBIE: Average of Petrol Costs from 1/09/2023 to 23/08/2024
    Regular_Petrol_discounted_retail_price_NZc.p.l = 278.716297
    """
    return PetrolPrice(
        name="Default Petrol Price",
        per_petrol_litre=2.78,
    )


def _diesel():
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


def _public_ev_charger():
    """
    Return a default public EV charger rate.

    Placeholder value of 80c/kWh. (ChargeNet price for Destination chargers)
    """
    return PublicChargingPrice(
        name="Default Public EV Charger Rate",
        per_kwh=0.80,
    )


# ---------------------------------------------------
# Vehicle Non-Energy Cost Defaults (Consolidated)
# ---------------------------------------------------

_DEFAULT_VEHICLE_COSTS = {
    "None": {"licensing": 0.0, "servicing": 0.0, "ruc": 0.0},
    "Petrol": {"licensing": 107.09, "servicing": 1133.15, "ruc": 0},
    "Diesel": {"licensing": 174.92, "servicing": 1133.15, "ruc": 76},
    "Hybrid": {"licensing": 107.09, "servicing": 1133.15, "ruc": 0},
    "Plug-in hybrid": {"licensing": 107.09, "servicing": 1133.15, "ruc": 53},
    "Electric": {"licensing": 107.09, "servicing": 684.4, "ruc": 76},
}


def get_default_annual_other_vehicle_costs(vehicle_type: str) -> NonEnergyVehicleCosts:
    """
    Return a default set of annual non-energy costs
    for the provided vehicle type.
    """
    if vehicle_type not in _DEFAULT_VEHICLE_COSTS:
        raise ValueError(f"Unknown vehicle type: {vehicle_type}")
    c = _DEFAULT_VEHICLE_COSTS[vehicle_type]
    return NonEnergyVehicleCosts(
        name=f"Default {vehicle_type} Vehicle Other Costs",
        nzd_per_year_licensing=c["licensing"],
        nzd_per_year_servicing_cost=c["servicing"],
        nzd_per_000_km_road_user_charges=c["ruc"],
    )


# ---------------------------------------------------
# Factory registry for all plans
# ---------------------------------------------------

_DEFAULT_PLAN_FACTORIES = {
    "electricity_plan": _electricity,
    "natural_gas_plan": _natural_gas,
    "lpg_plan": _lpg,
    "wood_price": _wood,
    "petrol_price": _petrol,
    "diesel_price": _diesel,
    "public_charging_price": _public_ev_charger,
}


def get_default_plan(name: str):
    """
    Return a specific default plan by name.
    Example names:
        - 'electricity_plan'
        - 'natural_gas_plan'
        - 'wood_price'
    """
    if name not in _DEFAULT_PLAN_FACTORIES:
        raise ValueError(f"No default plan registered for: {name}")
    return _DEFAULT_PLAN_FACTORIES[name]()


def get_default_plans():
    """
    Return a default set of energy plans and vehicle cost plans.
    """
    return {
        **{k: get_default_plan(k) for k in _DEFAULT_PLAN_FACTORIES},
        "other_vehicle_costs": {
            vt: get_default_annual_other_vehicle_costs(vt)
            for vt in _DEFAULT_VEHICLE_COSTS
        },
    }
