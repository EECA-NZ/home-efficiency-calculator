"""
Functions relating to spatial data. Map postcodes to climate zones and EDB zones.
"""

from ..models.energy_plans import HouseholdEnergyPlan, ElectricityPlan
from .configuration import (
    get_default_natural_gas_plan,
    get_default_lpg_plan,
    get_default_wood_price,
    get_default_petrol_price,
    get_default_diesel_price,
)


def edb_zone(postcode: str) -> str:
    """
    Return the EDB zone for the given postcode.

    Parameters
    ----------
    postcode : str
        The postcode to lookup.

    Returns
    -------
    str
        The EDB zone for the given postcode.
    """
    if postcode == "0000":
        return "EDB1"
    return "EDB2"


def energy_plan(postcode: str) -> HouseholdEnergyPlan:
    """
    Return an energy plan available for the given postcode.

    Parameters
    ----------
    postcode : str
        The postcode to lookup.

    Returns
    -------
    HouseholdEnergyPlan
        An energy plan available for the given postcode.
    """
    my_edb_zone = edb_zone(postcode)
    nzd_per_day_kwh = 2000
    if my_edb_zone == "EDB1":
        nzd_per_day_kwh = 1500
    electricity_plan = ElectricityPlan(
        name="Basic Electricity Plan",
        nzd_per_day_kwh=nzd_per_day_kwh,
        nzd_per_night_kwh=0.18,
        nzd_per_controlled_kwh=0.15,
        daily_charge=1.25,
    )
    return HouseholdEnergyPlan(
        name=f"Plan for {postcode}",
        electricity_plan=electricity_plan,
        natural_gas_plan=get_default_natural_gas_plan(),
        lpg_plan=get_default_lpg_plan(),
        wood_price=get_default_wood_price(),
        petrol_price=get_default_petrol_price(),
        diesel_price=get_default_diesel_price(),
    )
