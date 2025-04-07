"""
Classes representing different energy plans for households, with minimal
Pydantic overhead by using a 'trusted' base model.
"""

# pylint: disable=too-many-locals

from typing import Dict

from pydantic import BaseModel

from app.models.usage_profiles import EnergyCostBreakdown, SolarSavingsBreakdown
from app.services.solar_calculator.solar_helpers import compute_solar_offset


class ElectricityPlan(BaseModel):
    """
    Electricity plan for a household.
    """

    name: str
    fixed_rate: float  # NZD per day
    import_rates: Dict[
        str, float
    ]  # e.g. {"Day": 0.25, "Night": 0.15, "Uncontrolled": 0.20}
    export_rates: Dict[str, float]  # e.g. {"Uncontrolled": 0.12}

    def calculate_cost(self, usage_profile) -> EnergyCostBreakdown:
        """
        Returns an EnergyCostBreakdown for this electricity plan and usage profile.
        """
        tariff_keys = set(self.import_rates.keys())
        export_rate = self.export_rates.get("Uncontrolled", 0.0)

        # 1) Fixed cost
        fixed_cost_nzd = usage_profile.elx_connection_days * self.fixed_rate

        # 2) Compute solar overlap
        (
            shift_self_consumption_kwh,
            fixed_self_consumption_kwh,
            export_kwh,
        ) = compute_solar_offset(usage_profile)
        total_solar_kwh = usage_profile.solar_generation_kwh.total
        self_consumption_kwh = shift_self_consumption_kwh + fixed_self_consumption_kwh
        export_earnings_nzd = export_kwh * export_rate
        self_consumption_pct = (
            (self_consumption_kwh / total_solar_kwh * 100.0)
            if total_solar_kwh > 0
            else 0.0
        )

        # 3) Bill leftover usage
        day_import_kwh = (
            usage_profile.electricity_kwh.fixed_day_kwh - fixed_self_consumption_kwh
        )
        night_import_kwh = usage_profile.electricity_kwh.fixed_ngt_kwh
        shift_import_kwh = (
            usage_profile.electricity_kwh.shift_abl_kwh - shift_self_consumption_kwh
        )

        if tariff_keys == {"Day", "Night"}:
            variable_cost = (
                day_import_kwh * self.import_rates["Day"]
                + (night_import_kwh + shift_import_kwh) * self.import_rates["Night"]
            )
            self_consumption_savings_nzd = (
                fixed_self_consumption_kwh * self.import_rates["Day"]
                + shift_self_consumption_kwh * self.import_rates["Night"]
            )
        elif tariff_keys == {"All inclusive"}:
            total_import_kwh = day_import_kwh + night_import_kwh + shift_import_kwh
            variable_cost = total_import_kwh * self.import_rates["All inclusive"]
            self_consumption_savings_nzd = (
                self_consumption_kwh * self.import_rates["All inclusive"]
            )
        elif tariff_keys == {"Uncontrolled"}:
            total_import_kwh = day_import_kwh + night_import_kwh + shift_import_kwh
            variable_cost = total_import_kwh * self.import_rates["Uncontrolled"]
            self_consumption_savings_nzd = (
                self_consumption_kwh * self.import_rates["Uncontrolled"]
            )
        else:
            raise ValueError(f"Unexpected tariff keys: {tariff_keys}")

        # 4) Build final breakdown
        return EnergyCostBreakdown(
            fixed_cost_nzd=fixed_cost_nzd,
            variable_cost_nzd=variable_cost,
            solar=SolarSavingsBreakdown(
                self_consumption_kwh=self_consumption_kwh,
                export_kwh=export_kwh,
                self_consumption_savings_nzd=self_consumption_savings_nzd,
                export_earnings_nzd=export_earnings_nzd,
                self_consumption_pct=self_consumption_pct,
            ),
        )


class NaturalGasPlan(BaseModel):
    """
    Natural gas plan for a household.
    """

    name: str
    fixed_rate: float
    import_rates: Dict[str, float]

    def calculate_cost(self, usage_profile) -> EnergyCostBreakdown:
        """
        Returns an EnergyCostBreakdown for this natural gas plan and usage profile.
        """
        keys = set(self.import_rates.keys())
        if keys == {"Uncontrolled"}:
            variable_cost = (
                usage_profile.natural_gas_kwh * self.import_rates["Uncontrolled"]
            )
        else:
            raise ValueError(f"Unexpected import_rates keys: {keys}")
        fixed_cost = usage_profile.natural_gas_connection_days * self.fixed_rate
        return EnergyCostBreakdown(
            fixed_cost_nzd=fixed_cost,
            variable_cost_nzd=variable_cost,
            solar=None,
        )


class LPGPlan(BaseModel):
    """
    LPG plan for a household.
    """

    name: str
    per_lpg_kwh: float
    fixed_rate: float

    def calculate_cost(self, usage_profile) -> EnergyCostBreakdown:
        """
        Returns an EnergyCostBreakdown for this LPG plan and usage profile.
        """
        variable_cost = usage_profile.lpg_kwh * self.per_lpg_kwh
        fixed_cost = usage_profile.lpg_tanks_rental_days * self.fixed_rate
        return EnergyCostBreakdown(
            fixed_cost_nzd=fixed_cost,
            variable_cost_nzd=variable_cost,
            solar=None,
        )


class WoodPrice(BaseModel):
    """
    Wood plan for a household.
    """

    name: str
    per_wood_kwh: float

    def calculate_cost(self, usage_profile) -> EnergyCostBreakdown:
        """
        Returns an EnergyCostBreakdown for this wood plan and usage profile.
        """
        variable_cost = usage_profile.wood_kwh * self.per_wood_kwh
        return EnergyCostBreakdown(
            fixed_cost_nzd=0.0, variable_cost_nzd=variable_cost, solar=None
        )


class PetrolPrice(BaseModel):
    """
    Petrol plan for a household.
    """

    name: str
    per_petrol_litre: float

    def calculate_cost(self, usage_profile) -> EnergyCostBreakdown:
        """
        Returns an EnergyCostBreakdown for this petrol plan and usage profile.
        """
        variable_cost = usage_profile.petrol_litres * self.per_petrol_litre
        return EnergyCostBreakdown(
            fixed_cost_nzd=0.0, variable_cost_nzd=variable_cost, solar=None
        )


class DieselPrice(BaseModel):
    """
    Diesel plan for a household.
    """

    name: str
    per_diesel_litre: float

    def calculate_cost(self, usage_profile) -> EnergyCostBreakdown:
        """
        Returns an EnergyCostBreakdown for this diesel plan and usage profile.
        """
        variable_cost = usage_profile.diesel_litres * self.per_diesel_litre
        return EnergyCostBreakdown(
            fixed_cost_nzd=0.0, variable_cost_nzd=variable_cost, solar=None
        )


class PublicChargingPrice(BaseModel):
    """
    Public charging plan for a household.
    """

    name: str
    per_kwh: float

    def calculate_cost(self, usage_profile) -> EnergyCostBreakdown:
        """
        Returns an EnergyCostBreakdown for this public charging plan and usage profile.
        """
        variable_cost = usage_profile.public_ev_charger_kwh * self.per_kwh
        return EnergyCostBreakdown(
            fixed_cost_nzd=0.0, variable_cost_nzd=variable_cost, solar=None
        )


class NonEnergyVehicleCosts(BaseModel):
    """
    Non-energy costs of vehicle ownership.
    """

    name: str
    nzd_per_year_licensing: float
    nzd_per_year_servicing_cost: float
    nzd_per_000_km_road_user_charges: float

    def calculate_cost(self, usage_profile) -> EnergyCostBreakdown:
        """
        Returns an EnergyCostBreakdown for this
        non-energy vehicle costs and usage profile.
        """
        variable_cost = (
            self.nzd_per_year_licensing
            + self.nzd_per_year_servicing_cost
            + usage_profile.thousand_km * self.nzd_per_000_km_road_user_charges
        )
        return EnergyCostBreakdown(
            fixed_cost_nzd=0.0, variable_cost_nzd=variable_cost, solar=None
        )


class HouseholdEnergyPlan(BaseModel):
    """
    Overall household energy plan.

    Returns an EnergyCostBreakdown across all fuel types for the given profile.
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

    def calculate_cost(self, usage_profile) -> EnergyCostBreakdown:
        """
        Calculate total energy costs for a household across all fuel types.
        """
        # 1) Electricity plan cost
        electricity_cost = self.electricity_plan.calculate_cost(usage_profile)
        total_fixed_cost = electricity_cost.fixed_cost_nzd
        total_variable_cost = electricity_cost.variable_cost_nzd

        # If there's a solar portion, gather it
        if electricity_cost.solar:
            sc_savings = electricity_cost.solar.self_consumption_savings_nzd
            export_earnings = electricity_cost.solar.export_earnings_nzd
            sc_kwh = electricity_cost.solar.self_consumption_kwh
            ex_kwh = electricity_cost.solar.export_kwh
            sc_pct = electricity_cost.solar.self_consumption_pct
        else:
            sc_savings = 0.0
            export_earnings = 0.0
            sc_kwh = 0.0
            ex_kwh = 0.0
            sc_pct = 0.0

        # 2) Add up other fuels
        for plan in [
            self.natural_gas_plan,
            self.lpg_plan,
            self.wood_price,
            self.petrol_price,
            self.diesel_price,
            self.public_charging_price,
            self.other_vehicle_costs,
        ]:
            cost = plan.calculate_cost(usage_profile)
            total_fixed_cost += cost.fixed_cost_nzd
            total_variable_cost += cost.variable_cost_nzd

        # 3) If there's no solar, return none, else build a breakdown
        solar_breakdown = None
        if sc_savings > 0 or export_earnings > 0:
            solar_breakdown = SolarSavingsBreakdown(
                self_consumption_kwh=sc_kwh,
                export_kwh=ex_kwh,
                self_consumption_savings_nzd=sc_savings,
                export_earnings_nzd=export_earnings,
                self_consumption_pct=sc_pct,
            )

        return EnergyCostBreakdown(
            fixed_cost_nzd=total_fixed_cost,
            variable_cost_nzd=total_variable_cost,
            solar=solar_breakdown,
        )
