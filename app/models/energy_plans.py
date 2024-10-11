"""
Classes representing different energy plans for households.
"""

from pydantic import BaseModel


class ElectricityPlan(BaseModel):
    """
    Electricity plan for a household.
    """

    name: str
    nzd_per_day_kwh: float
    nzd_per_night_kwh: float
    nzd_per_controlled_kwh: float
    daily_charge: float

    def calculate_cost(self, profile):
        """
        Calculate the cost of electricity for a household.

        Args:
        profile: HouseholdYearlyFuelUsageProfile object

        Returns:
        cost: float, the total cost of electricity for the household
        """
        return (
            profile.day_kwh * self.nzd_per_day_kwh
            + profile.flexible_kwh
            * min(self.nzd_per_night_kwh, self.nzd_per_controlled_kwh)
            + profile.elx_connection_days * self.daily_charge
        )


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
        cost: float, the total cost of natural gas for the household
        """
        return (
            profile.natural_gas_kwh * self.per_natural_gas_kwh
            + profile.natural_gas_connection_days * self.daily_charge
        )


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
        cost: float, the total cost of LPG for the household
        """
        return (
            profile.lpg_kwh * self.per_lpg_kwh
            + profile.lpg_tank_rental_days * self.daily_charge
        )


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
        cost: float, the total cost of wood for the household
        """
        return profile.wood_kwh * self.per_wood_kwh


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
        cost: float, the total cost of petrol for the household
        """
        return profile.petrol_litres * self.per_petrol_litre


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
        cost: float, the total cost of diesel for the household
        """
        return profile.diesel_litres * self.per_diesel_litre


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

    def calculate_cost(self, profile):
        """
        Calculate the total cost of energy for a household.

        Args:
        profile: HouseholdYearlyFuelUsageProfile object

        Returns:
        cost: float, the total cost of energy for the household
        """
        return (
            self.electricity_plan.calculate_cost(profile)
            + self.natural_gas_plan.calculate_cost(profile)
            + self.lpg_plan.calculate_cost(profile)
            + self.wood_price.calculate_cost(profile)
            + self.petrol_price.calculate_cost(profile)
            + self.diesel_price.calculate_cost(profile)
        )
