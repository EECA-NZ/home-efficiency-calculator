"""
Functions relating to spatial data. Map postcodes to climate zones and EDB zones.
"""

from ..models.energy_plans import ElectricityPlan, HouseholdEnergyPlan
from .configuration import get_default_plans


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
    plans = get_default_plans()
    if my_edb_zone == "EDB1":
        plans["electricity_plan"] = ElectricityPlan(
            name="Basic Electricity Plan",
            daily_charge=1.25,
            nzd_per_kwh={"Uncontrolled": 0.25, "Night": 0.18, "Controlled": 0.15},
        )
    return HouseholdEnergyPlan(name=f"Plan for {postcode}", **plans)
