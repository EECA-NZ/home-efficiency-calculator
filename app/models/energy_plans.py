"""
Classes representing different energy plans for households.
"""

# pylint: disable=too-many-locals

from typing import Dict, Tuple

import numpy as np
from pydantic import BaseModel

from app.services.usage_profile_helpers import day_night_flag

day_mask = day_night_flag()


class ElectricityPlan(BaseModel):
    """
    Electricity plan for a household.
    Daily charge is in NZD per day.
    Import and export rates are in NZD per kWh.

    Implementation covers three tariff structure types:
        - Day/Night
        - Controlled/Uncontrolled
        - All inclusive (single rate)

    Features:
        1. Supports day/night or controlled/uncontrolled or single-rate.
        2. Allocates solar: first offsets usage, leftover is exported.
        3. Compares Option 1 (no shift) vs. Option 2 (night shift).
        4. Uses NumPy vectorized operations exclusively.
    """

    name: str
    fixed_rate: float  # NZD per day
    import_rates: Dict[str, float]  # e.g. {"Day": 0.25, "Night": 0.15}, or
    # {"Controlled": 0.1, "Uncontrolled": 0.22}, etc.
    export_rates: Dict[str, float]  # e.g. {"Uncontrolled": 0.12}

    def calculate_cost(
        self, profile, compare_shifts: bool = True
    ) -> Tuple[float, float]:
        """
        Calculate the electricity cost for this plan.
        By default (compare_shifts=True), we:
            1) Build Option 1 usage arrays (no shift).
            2) Build Option 2 usage arrays (with night shift).
            3) Compute variable costs for both, pick the cheaper scenario.

        Returns
        -------
        (fixed_cost_nzd,
         variable_cost_nzd,
         solar_self_consumption_savings_nzd,
         solar_export_earnings_nzd)

        Notes
        -----
        - The fixed cost is the daily charge times the number of days in the year.
        - The variable cost is the sum of import costs minus export credits.
        - The total cost borne by the household is the sum of fixed and variable costs.
        - The solar self-consumption savings and export earnings are for information.
        """

        # ------------------------------------------------
        # 1) Identify tariff structure from import_rates
        # ------------------------------------------------
        tariff_structure = set(self.import_rates.keys())

        # ------------------------------------------------
        # 2) Gather usage arrays (all shape (8760,))
        # ------------------------------------------------
        solar_kwh = profile.solar_generation_kwh.fixed_time_generation_kwh

        # Option 1 (no shift): as-is
        uncontrolled_opt1 = profile.electricity_kwh.total_uncontrolled_usage
        controllable_opt1 = profile.electricity_kwh.total_controllable_usage

        # Option 2 (night shift): shift the shiftable portions
        uncontrolled_opt2 = profile.electricity_kwh.total_uncontrolled_night_shifted
        controllable_opt2 = profile.electricity_kwh.total_controllable_night_shifted

        # ------------------------------------------------
        # 3) Compute variable cost for each scenario
        # ------------------------------------------------
        var_cost_opt1 = self._compute_variable_cost(
            tariff_structure, uncontrolled_opt1, controllable_opt1, solar_kwh
        )
        if compare_shifts:
            var_cost_opt2 = self._compute_variable_cost(
                tariff_structure, uncontrolled_opt2, controllable_opt2, solar_kwh
            )
            variable_cost_nzd = min(var_cost_opt1, var_cost_opt2)
        else:
            variable_cost_nzd = var_cost_opt1

        # ------------------------------------------------
        # 4) Fixed cost
        # ------------------------------------------------
        fixed_cost_nzd = profile.elx_connection_days * self.fixed_rate

        return (fixed_cost_nzd, variable_cost_nzd)

    def _compute_variable_cost(
        self,
        tariff_structure,
        uncontrolled_kwh: np.ndarray,
        controlled_kwh: np.ndarray,
        solar_kwh: np.ndarray,
    ) -> float:
        """
        Router method that picks the right helper for the given tariff structure.
        """
        if tariff_structure == {"Day", "Night"}:
            # Combine controlled + uncontrolled for day/night logic
            total_usage = uncontrolled_kwh + controlled_kwh
            return self._compute_variable_cost_day_night(total_usage, solar_kwh)
        if tariff_structure == {"Controlled", "Uncontrolled"}:
            return self._compute_variable_cost_controlled_uncontrolled(
                uncontrolled_kwh, controlled_kwh, solar_kwh
            )
        if tariff_structure == {"All inclusive"}:
            # Single rate
            total_usage = uncontrolled_kwh + controlled_kwh
            return self._compute_variable_cost_single_rate(
                total_usage, solar_kwh, rate_key="All inclusive"
            )
        if tariff_structure == {"Uncontrolled"}:
            # Single rate
            total_usage = uncontrolled_kwh + controlled_kwh
            return self._compute_variable_cost_single_rate(
                total_usage, solar_kwh, rate_key="Uncontrolled"
            )
        # Extend for additional structures as needed
        raise ValueError(f"Unexpected tariff structure: {tariff_structure}")

    # --------------------------------------------------------------------
    #   DAY/NIGHT
    # --------------------------------------------------------------------
    def _compute_variable_cost_day_night(
        self, usage_kwh: np.ndarray, solar_kwh: np.ndarray
    ) -> float:
        """
        For a day/night tariff, do a fully vectorized hour-by-hour net import,
        net export, day vs. night import rates, and subtract export credit.
        """
        export_rate = self.export_rates.get("Uncontrolled", 0.0)
        day_rate = self.import_rates["Day"]
        night_rate = self.import_rates["Night"]

        # Compute net import/export for each hour
        usage_minus_solar = usage_kwh - solar_kwh
        net_import = np.clip(usage_minus_solar, a_min=0, a_max=None)
        net_export = np.clip(-usage_minus_solar, a_min=0, a_max=None)

        day_import = net_import * day_mask
        night_import = net_import * (~day_mask)

        day_cost = day_import * day_rate
        night_cost = night_import * night_rate
        export_credit = net_export * export_rate

        total_import_cost = day_cost.sum() + night_cost.sum()
        total_export_credit = export_credit.sum()

        return total_import_cost - total_export_credit

    # --------------------------------------------------------------------
    #   CONTROLLED/UNCONTROLLED
    # --------------------------------------------------------------------
    def _compute_variable_cost_controlled_uncontrolled(
        self, unctrl_kwh: np.ndarray, ctrl_kwh: np.ndarray, solar_kwh: np.ndarray
    ) -> float:
        """
        Vectorized approach to "allocate solar to uncontrolled first,
        then controlled, leftover is exported," in a single pass.
        """
        export_rate = self.export_rates.get("Uncontrolled", 0.0)
        unctrl_rate = self.import_rates["Uncontrolled"]
        ctrl_rate = self.import_rates["Controlled"]

        # 1) Allocate solar to uncontrolled
        solar_to_uncontrolled = np.minimum(unctrl_kwh, solar_kwh)

        # 2) Remainder of solar (after meeting uncontrolled)
        s_remaining = solar_kwh - solar_to_uncontrolled

        # 3) Allocate to controlled
        solar_to_controlled = np.minimum(ctrl_kwh, s_remaining)

        # 4) Leftover solar => export
        leftover_solar = s_remaining - solar_to_controlled
        leftover_solar = np.clip(leftover_solar, 0, None)  # defensive clip

        # 5) Net import for each usage category
        unctrl_import = unctrl_kwh - solar_to_uncontrolled
        ctrl_import = ctrl_kwh - solar_to_controlled

        import_cost = unctrl_import * unctrl_rate + ctrl_import * ctrl_rate
        export_credit = leftover_solar * export_rate

        total_import_cost = import_cost.sum()
        total_export_credit = export_credit.sum()

        return total_import_cost - total_export_credit

    # --------------------------------------------------------------------
    #  'ALL INCLUSIVE' OR 'UNCONTROLLED' SINGLE RATE
    # --------------------------------------------------------------------
    def _compute_variable_cost_single_rate(
        self, usage_kwh: np.ndarray, solar_kwh: np.ndarray, rate_key: str
    ) -> float:
        """
        Single import rate (e.g. 'All inclusive'), plus optional buy-back export rate.
        """
        export_rate = self.export_rates.get("Uncontrolled", 0.0)
        import_rate = self.import_rates[rate_key]

        usage_minus_solar = usage_kwh - solar_kwh
        net_import = np.clip(usage_minus_solar, 0, None)
        net_export = np.clip(-usage_minus_solar, 0, None)

        import_cost = (net_import * import_rate).sum()
        export_credit = (net_export * export_rate).sum()

        return import_cost - export_credit


class NaturalGasPlan(BaseModel):
    """
    Natural gas plan for a household.
    """

    name: str
    fixed_rate: float
    import_rates: Dict[str, float]

    def calculate_cost(self, profile):
        """
        Calculate the cost of natural gas for a household.

        Args:
        profile: HouseholdYearlyFuelUsageProfile object

        Returns:
        Tuple[float, float], the fixed and variable cost
        of natural gas for the household
        """
        keys = set(self.import_rates.keys())
        variable_cost_nzd = 0

        if keys == {"Uncontrolled"}:
            variable_cost_nzd += (profile.natural_gas_kwh) * self.import_rates[
                "Uncontrolled"
            ]
        else:
            raise ValueError(f"Unexpected import_rates keys: {keys}")

        fixed_cost_nzd = profile.natural_gas_connection_days * self.fixed_rate
        return (fixed_cost_nzd, variable_cost_nzd)


class LPGPlan(BaseModel):
    """
    LPG plan for a household.
    """

    name: str
    per_lpg_kwh: float
    fixed_rate: float

    def calculate_cost(self, profile):
        """
        Calculate the cost of LPG for a household.

        Args:
        profile: HouseholdYearlyFuelUsageProfile object

        Returns:
        Tuple[float, float], the fixed and variable
        cost of LPG for the household
        """
        variable_cost_nzd = profile.lpg_kwh * self.per_lpg_kwh
        fixed_cost_nzd = profile.lpg_tanks_rental_days * self.fixed_rate
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
        Tuple[float, float], the fixed cost of wood
        for the household ($zero) and the variable
        cost (in NZ$ per embodied kWh) of wood.
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
        Tuple[float, float], the fixed cost of petrol
        for the household ($zero) and the variable cost
        (in NZ$ per litre) of petrol.
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
        Tuple[float, float], the fixed cost of diesel
        for the household ($zero) and the variable cost
        (in NZ$ per litre) of diesel.
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
        Tuple[float, float], the fixed cost (which is 0) of
        public charging for the household and the variable cost
        (in NZ$ per kWh) of public charging.
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

        Parameters
        ----------
        profile : HouseholdYearlyFuelUsageProfile
            The yearly fuel usage profile of the household.

        Returns
        -------
        fixed_cost : float
            The fixed cost of vehicle ownership, which is currently set to $0.
        variable_cost : float
            The variable cost of vehicle ownership, including licensing, servicing,
            and road user charges.

        Notes
        -----
        For the time being, all costs are being considered as variable costs,
        treating vehicle ownership as the quantity that varies.
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
