"""
Classes representing different energy plans for households.
"""

from typing import Dict

from pydantic import BaseModel


class ElectricityPlan(BaseModel):
    """
    Electricity plan for a household.
    """

    name: str
    daily_charge: float
    nzd_per_kwh: Dict[str, float]

    def calculate_cost(self, profile):
        """
        Calculate the cost of electricity for a household based
        on specific patterns of nzd_per_kwh fields.

        Args:
            profile: HouseholdYearlyFuelUsageProfile object
            containing inflexible_day_kwh, flexible_kwh, and other usage data.

        Returns:
            Tuple[float, float]: the fixed and variable cost of
            electricity for the household.
        """
        keys = set(self.nzd_per_kwh.keys())
        variable_cost_nzd = 0

        if keys == {"All inclusive"}:
            variable_cost_nzd += (
                profile.inflexible_day_kwh + profile.flexible_kwh
            ) * self.nzd_per_kwh["All inclusive"]
        elif keys == {"Day", "Night"}:
            variable_cost_nzd += profile.inflexible_day_kwh * self.nzd_per_kwh["Day"]
            variable_cost_nzd += profile.flexible_kwh * self.nzd_per_kwh["Night"]
        elif keys == {"Uncontrolled"}:
            variable_cost_nzd += (
                profile.inflexible_day_kwh + profile.flexible_kwh
            ) * self.nzd_per_kwh["Uncontrolled"]
        elif keys == {"Uncontrolled", "Controlled"}:
            variable_cost_nzd += (
                profile.inflexible_day_kwh * self.nzd_per_kwh["Uncontrolled"]
            )
            variable_cost_nzd += profile.flexible_kwh * self.nzd_per_kwh["Controlled"]
        elif keys == {"Night", "All inclusive"}:
            variable_cost_nzd += profile.flexible_kwh * self.nzd_per_kwh["Night"]
            variable_cost_nzd += (
                profile.inflexible_day_kwh * self.nzd_per_kwh["All inclusive"]
            )
        elif keys == {"Night", "Uncontrolled"}:
            variable_cost_nzd += profile.flexible_kwh * self.nzd_per_kwh["Night"]
            variable_cost_nzd += (
                profile.inflexible_day_kwh * self.nzd_per_kwh["Uncontrolled"]
            )
        else:
            raise ValueError(f"Unexpected nzd_per_kwh keys: {keys}")

        fixed_cost_nzd = profile.elx_connection_days * self.daily_charge
        return (fixed_cost_nzd, variable_cost_nzd)


class NaturalGasPlan(BaseModel):
    """
    Natural gas plan for a household.
    """

    name: str
    per_natural_gas_kwh: float
    daily_charge: float

    def calculate_cost(self, profile):
        """
        Calculate the cost of natural gas for a household.

        Args:
        profile: HouseholdYearlyFuelUsageProfile object

        Returns:
        Tuple[float, float], the variable and fixed cost
        of natural gas for the household
        """
        variable_cost_nzd = profile.natural_gas_kwh * self.per_natural_gas_kwh
        fixed_cost_nzd = profile.natural_gas_connection_days * self.daily_charge
        return (fixed_cost_nzd, variable_cost_nzd)


class LPGPlan(BaseModel):
    """
    LPG plan for a household.
    """

    name: str
    per_lpg_kwh: float
    daily_charge: float

    def calculate_cost(self, profile):
        """
        Calculate the cost of LPG for a household.

        Args:
        profile: HouseholdYearlyFuelUsageProfile object

        Returns:
        Tuple[float, float], the variable and fixed
        cost of LPG for the household
        """
        variable_cost_nzd = profile.lpg_kwh * self.per_lpg_kwh
        fixed_cost_nzd = profile.lpg_tanks_rental_days * self.daily_charge
        return (fixed_cost_nzd, variable_cost_nzd)


class WoodPrice(BaseModel):
    """
    Wood plan for a household.
    """

    name: str
    per_wood_kwh: float

    def calculate_cost(self, profile):
        """
        Calculate the cost of wood for a household.

        Args:
        profile: HouseholdYearlyFuelUsageProfile object

        Returns:
        Tuple[float, float], the variable cost of wood
        for the household and fixed cost (which is 0)
        """
        return (0, profile.wood_kwh * self.per_wood_kwh)


class PetrolPrice(BaseModel):
    """
    Petrol plan for a household.
    """

    name: str
    per_petrol_litre: float

    def calculate_cost(self, profile):
        """
        Calculate the cost of petrol for a household.

        Args:
        profile: HouseholdYearlyFuelUsageProfile object

        Returns:
        Tuple[float, float], the variable cost of petrol
        for the household and fixed cost (which is 0)
        """
        return (0, profile.petrol_litres * self.per_petrol_litre)


class DieselPrice(BaseModel):
    """
    Diesel plan for a household.
    """

    name: str
    per_diesel_litre: float

    def calculate_cost(self, profile):
        """
        Calculate the cost of diesel for a household.

        Args:
        profile: HouseholdYearlyFuelUsageProfile object

        Returns:
        Tuple[float, float], the variable cost of diesel
        for the household and fixed cost (which is 0)
        """
        return (0, profile.diesel_litres * self.per_diesel_litre)


class PublicChargingPrice(BaseModel):
    """
    Public charging plan for a household.
    """

    name: str
    per_kwh: float

    def calculate_cost(self, profile):
        """
        Calculate the cost of public charging for a household.

        Args:
        profile: HouseholdYearlyFuelUsageProfile object

        Returns:
        Tuple[float, float], the variable cost of public charging
        for the household and fixed cost (which is 0)
        """
        return (0, profile.public_ev_charger_kwh * self.per_kwh)


class NonEnergyVehicleCosts(BaseModel):
    """
    Non-energy costs of vehicle ownership for a household.
    """

    name: str

    nzd_per_year_licensing: float
    nzd_per_year_servicing_cost: float
    nzd_per_000_km_road_user_charges: float

    def calculate_cost(self, profile):
        """
        Calculate the cost of vehicle ownership for a household.

        Args:
        profile: HouseholdYearlyFuelUsageProfile object

        Returns:
        Tuple[float, float], the fixed cost of vehicle ownership
        (licensing) and variable cost (servicing and road user charges).

        NOTE: for the time being all costs are being put into the
        "variable" category to make the lookup-table approach simpler.
        """
        return (
            0,
            self.nzd_per_year_licensing
            + self.nzd_per_year_servicing_cost
            + profile.thousand_km * self.nzd_per_000_km_road_user_charges,
        )


class HouseholdEnergyPlan(BaseModel):
    """
    Overall household energy plan.
    """

    name: str
    electricity_plan: ElectricityPlan
    natural_gas_plan: NaturalGasPlan
    lpg_plan: LPGPlan
    wood_price: WoodPrice
    petrol_price: PetrolPrice
    diesel_price: DieselPrice
    public_charging_price: PublicChargingPrice
    other_vehicle_costs: NonEnergyVehicleCosts

    def calculate_cost(self, profile, verbose=False):
        """
        Calculate the total cost of energy for a household.

        Args:
        profile: HouseholdYearlyFuelUsageProfile object

        Returns:
        Tuple[float, float], the total fixed and variable
        cost of energy for the household
        """
        fixed_cost_nzd = 0
        variable_cost_nzd = 0
        for plan in [
            self.electricity_plan,
            self.natural_gas_plan,
            self.lpg_plan,
            self.wood_price,
            self.petrol_price,
            self.diesel_price,
            self.public_charging_price,
            self.other_vehicle_costs,
        ]:
            fixed, variable = plan.calculate_cost(profile)
            if verbose:
                print(f"{plan.name} fixed cost: {fixed}")
                print(f"{plan.name} variable cost: {variable}")
            fixed_cost_nzd += fixed
            variable_cost_nzd += variable

        return (fixed_cost_nzd, variable_cost_nzd)
