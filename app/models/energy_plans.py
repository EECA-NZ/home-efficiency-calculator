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
        2. Determines solar self-consumption and export earnings.
        3. For simplicity and correspondence with lookup-table implementation,
           allocates solar simply: for Day/Night, all solar consumption is
           assumed to offset day tariff imports. For single-rate, solar
           offsets total usage (straight net). Solar is not implemented for
           Controlled/Uncontrolled tariffs.
        4. In “night shift” mode, used if solar is not present, shiftable usage
           is moved to take advantage of off-peak rates.
        5. Uses NumPy vectorized operations for performance.
    """

    name: str
    fixed_rate: float  # NZD per day
    import_rates: Dict[str, float]  # e.g. {"Day": 0.25, "Night": 0.15}
    export_rates: Dict[str, float]  # e.g. {"Uncontrolled": 0.12}

    def calculate_cost(self, usage_profile) -> Tuple[float, float, float, float, float]:
        """
        Calculate the electricity cost for this plan.

        Returns
        -------
        (fixed_cost_nzd,
         variable_cost_nzd,
         solar_self_consumption_savings_nzd,
         solar_export_earnings_nzd,
         solar_self_consumption_pct)

        Notes
        -----
        - We do a simple check: if solar is present, use normal usage. If not, apply
          a “night shift” version of usage.
        - The fixed cost is fixed_rate times the number of connection days.
        - The variable cost is import minus export credits.
        - The solar self-consumption savings and export earnings are informational.
        """
        # Decide whether to use "night shift" usage
        use_night_shift = True
        if usage_profile.solar_generation_kwh is not None:
            if usage_profile.solar_generation_kwh.total > 0:
                use_night_shift = False

        # Identify which tariff structure we have
        tariff_structure = set(self.import_rates.keys())

        # Gather usage arrays (all shape (8760,))
        solar_kwh = usage_profile.solar_generation_kwh.fixed_time_generation_kwh

        if use_night_shift:
            uncontrolled_kwh = (
                usage_profile.electricity_kwh.total_uncontrolled_night_shifted
            )
            controlled_kwh = (
                usage_profile.electricity_kwh.total_controllable_night_shifted
            )
        else:
            uncontrolled_kwh = usage_profile.electricity_kwh.total_uncontrolled_usage
            controlled_kwh = usage_profile.electricity_kwh.total_controllable_usage

        (
            variable_cost_nzd,
            solar_self_consumption_savings_nzd,
            solar_export_earnings_nzd,
            solar_self_consumption_pct,
        ) = self._compute_variable_cost(
            tariff_structure, uncontrolled_kwh, controlled_kwh, solar_kwh
        )

        # Fixed cost
        fixed_cost_nzd = usage_profile.elx_connection_days * self.fixed_rate

        return (
            fixed_cost_nzd,
            variable_cost_nzd,
            solar_self_consumption_savings_nzd,
            solar_export_earnings_nzd,
            solar_self_consumption_pct,
        )

    def _compute_variable_cost(
        self,
        tariff_structure,
        uncontrolled_kwh: np.ndarray,
        controlled_kwh: np.ndarray,
        solar_kwh: np.ndarray,
    ) -> Tuple[float, float, float, float]:
        """
        Router method that picks the appropriate helper for the given tariff structure.

        Returns
        -------
        (net_import_cost_nzd,
         solar_self_consumption_savings_nzd,
         solar_export_earnings_nzd,
         solar_self_consumption_pct)
        """
        if tariff_structure == {"Day", "Night"}:
            total_usage_kwh = uncontrolled_kwh + controlled_kwh
            return self._compute_variable_cost_day_night(total_usage_kwh, solar_kwh)

        if tariff_structure == {"Controlled", "Uncontrolled"}:
            return self._compute_variable_cost_controlled_uncontrolled(
                uncontrolled_kwh, controlled_kwh, solar_kwh
            )

        if tariff_structure == {"All inclusive"}:
            total_usage_kwh = uncontrolled_kwh + controlled_kwh
            return self._compute_variable_cost_single_rate(
                total_usage_kwh, solar_kwh, rate_key="All inclusive"
            )

        if tariff_structure == {"Uncontrolled"}:
            total_usage_kwh = uncontrolled_kwh + controlled_kwh
            return self._compute_variable_cost_single_rate(
                total_usage_kwh, solar_kwh, rate_key="Uncontrolled"
            )

        raise ValueError(f"Unexpected tariff structure: {tariff_structure}")

    # --------------------------------------------------------------------
    #   DAY/NIGHT
    # --------------------------------------------------------------------
    def _compute_variable_cost_day_night(
        self, usage_kwh: np.ndarray, solar_kwh: np.ndarray
    ) -> Tuple[float, float, float, float]:
        """
        For a day/night tariff, we assume all solar generation offsets day usage.

        Returns
        -------
        (net_import_cost_nzd,
         solar_offset_savings_nzd,
         solar_export_earnings_nzd,
         solar_self_consumption_pct)
        """
        export_rate = self.export_rates.get("Uncontrolled", 0.0)
        day_rate = self.import_rates["Day"]
        night_rate = self.import_rates["Night"]

        # Compute net usage and net export
        net_usage_kwh = usage_kwh - solar_kwh
        net_export_kwh = np.clip(-net_usage_kwh, a_min=0, a_max=None)

        # All solar offsets day usage
        solar_self_consumption_kwh = np.minimum(usage_kwh, solar_kwh)

        day_usage_kwh = (usage_kwh * day_mask).sum()
        night_usage_kwh = (usage_kwh * (~day_mask)).sum()
        total_self_consumed_kwh = solar_self_consumption_kwh.sum()

        # Subtract solar from day usage
        net_day_usage_kwh = day_usage_kwh - total_self_consumed_kwh

        day_cost_nzd = net_day_usage_kwh * day_rate
        night_cost_nzd = night_usage_kwh * night_rate
        total_export_credit_nzd = net_export_kwh.sum() * export_rate

        # “Savings” = how much day usage we offset
        solar_offset_savings_nzd = total_self_consumed_kwh * day_rate

        total_import_cost_nzd = day_cost_nzd + night_cost_nzd
        net_import_cost_nzd = total_import_cost_nzd - total_export_credit_nzd
        solar_export_earnings_nzd = total_export_credit_nzd

        total_usage_sum = usage_kwh.sum()
        if total_usage_sum == 0:
            solar_self_consumption_pct = 0.0
        else:
            solar_self_consumption_pct = (
                total_self_consumed_kwh / total_usage_sum
            ) * 100.0

        return (
            net_import_cost_nzd,
            solar_offset_savings_nzd,
            solar_export_earnings_nzd,
            solar_self_consumption_pct,
        )

    # --------------------------------------------------------------------
    #   CONTROLLED/UNCONTROLLED
    # --------------------------------------------------------------------
    def _compute_variable_cost_controlled_uncontrolled(
        self,
        uncontrolled_kwh: np.ndarray,
        controlled_kwh: np.ndarray,
        solar_kwh: np.ndarray,
    ) -> Tuple[float, float, float, float]:
        """
        Allocate solar to uncontrolled usage first (like “day”),
        then to controlled usage, leftover is exported.
        """
        export_rate = self.export_rates.get("Uncontrolled", 0.0)
        unctrl_rate = self.import_rates["Uncontrolled"]
        ctrl_rate = self.import_rates["Controlled"]

        # Cost if no solar:
        baseline_import_cost_nzd = (uncontrolled_kwh * unctrl_rate).sum() + (
            controlled_kwh * ctrl_rate
        ).sum()

        # 1) Allocate solar to uncontrolled
        solar_to_uncontrolled_kwh = np.minimum(uncontrolled_kwh, solar_kwh)
        # 2) Remainder of solar
        leftover_solar_kwh = solar_kwh - solar_to_uncontrolled_kwh
        # 3) Then allocate to controlled
        solar_to_controlled_kwh = np.minimum(controlled_kwh, leftover_solar_kwh)
        # 4) Leftover => export
        leftover_solar_kwh = np.clip(
            leftover_solar_kwh - solar_to_controlled_kwh, 0, None
        )

        # Net import
        net_uncontrolled_kwh = uncontrolled_kwh - solar_to_uncontrolled_kwh
        net_controlled_kwh = controlled_kwh - solar_to_controlled_kwh

        solar_self_consumption_kwh = solar_to_uncontrolled_kwh + solar_to_controlled_kwh
        total_usage_kwh = (uncontrolled_kwh + controlled_kwh).sum()

        if total_usage_kwh == 0:
            solar_self_consumption_pct = 0.0
        else:
            solar_self_consumption_pct = (
                solar_self_consumption_kwh.sum() / total_usage_kwh
            ) * 100.0

        import_cost_nzd = (net_uncontrolled_kwh * unctrl_rate).sum() + (
            net_controlled_kwh * ctrl_rate
        ).sum()
        export_credit_nzd = (leftover_solar_kwh * export_rate).sum()

        net_import_cost_nzd = import_cost_nzd - export_credit_nzd
        solar_export_earnings_nzd = export_credit_nzd
        solar_offset_savings_nzd = baseline_import_cost_nzd - import_cost_nzd

        return (
            net_import_cost_nzd,
            solar_offset_savings_nzd,
            solar_export_earnings_nzd,
            solar_self_consumption_pct,
        )

    # --------------------------------------------------------------------
    #  'ALL INCLUSIVE' OR 'UNCONTROLLED' SINGLE RATE
    # --------------------------------------------------------------------
    def _compute_variable_cost_single_rate(
        self, usage_kwh: np.ndarray, solar_kwh: np.ndarray, rate_key: str
    ) -> Tuple[float, float, float, float]:
        """
        Single import rate plus optional buy-back export rate.
        Solar offsets total usage equally (no day vs. night distinction).
        """
        export_rate = self.export_rates.get("Uncontrolled", 0.0)
        import_rate = self.import_rates[rate_key]

        # Cost if no solar:
        baseline_import_cost_nzd = (usage_kwh * import_rate).sum()

        net_usage_kwh = usage_kwh - solar_kwh
        net_export_kwh = np.clip(-net_usage_kwh, 0, None)
        net_import_kwh = np.clip(net_usage_kwh, 0, None)

        solar_self_consumption_kwh = np.minimum(usage_kwh, solar_kwh)
        total_usage_sum = usage_kwh.sum()
        if total_usage_sum == 0:
            solar_self_consumption_pct = 0.0
        else:
            solar_self_consumption_pct = (
                solar_self_consumption_kwh.sum() / total_usage_sum
            ) * 100.0

        import_cost_nzd = (net_import_kwh * import_rate).sum()
        export_credit_nzd = (net_export_kwh * export_rate).sum()

        net_import_cost_nzd = import_cost_nzd - export_credit_nzd
        solar_export_earnings_nzd = export_credit_nzd
        solar_offset_savings_nzd = baseline_import_cost_nzd - import_cost_nzd

        return (
            net_import_cost_nzd,
            solar_offset_savings_nzd,
            solar_export_earnings_nzd,
            solar_self_consumption_pct,
        )


class NaturalGasPlan(BaseModel):
    """
    Natural gas plan for a household.
    """

    name: str
    fixed_rate: float
    import_rates: Dict[str, float]

    def calculate_cost(self, usage_profile) -> Tuple[float, float, float, float, float]:
        """
        Calculate the cost of natural gas for a household.

        Returns
        -------
        (fixed_cost_nzd,
         variable_cost_nzd,
         0.0,
         0.0,
         0.0)
        """
        keys = set(self.import_rates.keys())
        variable_cost_nzd = 0.0

        if keys == {"Uncontrolled"}:
            variable_cost_nzd += (
                usage_profile.natural_gas_kwh * self.import_rates["Uncontrolled"]
            )
        else:
            raise ValueError(f"Unexpected import_rates keys: {keys}")

        fixed_cost_nzd = usage_profile.natural_gas_connection_days * self.fixed_rate
        return (fixed_cost_nzd, variable_cost_nzd, 0.0, 0.0, 0.0)


class LPGPlan(BaseModel):
    """
    LPG plan for a household.
    """

    name: str
    per_lpg_kwh: float
    fixed_rate: float

    def calculate_cost(self, usage_profile) -> Tuple[float, float, float, float, float]:
        """
        Calculate the cost of LPG.

        Returns
        -------
        (fixed_cost_nzd, variable_cost_nzd, 0.0, 0.0, 0.0)
        """
        variable_cost_nzd = usage_profile.lpg_kwh * self.per_lpg_kwh
        fixed_cost_nzd = usage_profile.lpg_tanks_rental_days * self.fixed_rate
        return (fixed_cost_nzd, variable_cost_nzd, 0.0, 0.0, 0.0)


class WoodPrice(BaseModel):
    """
    Wood plan for a household.
    """

    name: str
    per_wood_kwh: float

    def calculate_cost(self, usage_profile) -> Tuple[float, float, float, float, float]:
        """
        Calculate the cost of wood.

        Returns
        -------
        (0, variable_cost_nzd, 0.0, 0.0, 0.0)
        """
        variable_cost_nzd = usage_profile.wood_kwh * self.per_wood_kwh
        return (0.0, variable_cost_nzd, 0.0, 0.0, 0.0)


class PetrolPrice(BaseModel):
    """
    Petrol plan for a household.
    """

    name: str
    per_petrol_litre: float

    def calculate_cost(self, usage_profile) -> Tuple[float, float, float, float, float]:
        """
        Calculate the cost of petrol.

        Returns
        -------
        (0, variable_cost_nzd, 0.0, 0.0, 0.0)
        """
        variable_cost_nzd = usage_profile.petrol_litres * self.per_petrol_litre
        return (0.0, variable_cost_nzd, 0.0, 0.0, 0.0)


class DieselPrice(BaseModel):
    """
    Diesel plan for a household.
    """

    name: str
    per_diesel_litre: float

    def calculate_cost(self, usage_profile) -> Tuple[float, float, float, float, float]:
        """
        Calculate the cost of diesel.

        Returns
        -------
        (0, variable_cost_nzd, 0.0, 0.0, 0.0)
        """
        variable_cost_nzd = usage_profile.diesel_litres * self.per_diesel_litre
        return (0.0, variable_cost_nzd, 0.0, 0.0, 0.0)


class PublicChargingPrice(BaseModel):
    """
    Public charging plan for a household.
    """

    name: str
    per_kwh: float

    def calculate_cost(self, usage_profile) -> Tuple[float, float, float, float, float]:
        """
        Calculate the cost of public EV charging.

        Returns
        -------
        (0, variable_cost_nzd, 0.0, 0.0, 0.0)
        """
        variable_cost_nzd = usage_profile.public_ev_charger_kwh * self.per_kwh
        return (0.0, variable_cost_nzd, 0.0, 0.0, 0.0)


class NonEnergyVehicleCosts(BaseModel):
    """
    Non-energy costs of vehicle ownership.
    """

    name: str
    nzd_per_year_licensing: float
    nzd_per_year_servicing_cost: float
    nzd_per_000_km_road_user_charges: float

    def calculate_cost(self, usage_profile) -> Tuple[float, float, float, float, float]:
        """
        Calculate all non-energy vehicle costs.

        Returns
        -------
        (0,
         variable_cost_nzd,
         0.0,
         0.0,
         0.0)
        """
        variable_cost_nzd = (
            self.nzd_per_year_licensing
            + self.nzd_per_year_servicing_cost
            + usage_profile.thousand_km * self.nzd_per_000_km_road_user_charges
        )
        return (0.0, variable_cost_nzd, 0.0, 0.0, 0.0)


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

    def calculate_cost(self, usage_profile) -> Tuple[float, float, float, float, float]:
        """
        Calculate total costs across all energy types.

        Returns
        -------
        (fixed_cost_nzd,
         variable_cost_nzd,
         total_solar_self_consumption_savings,
         total_solar_export_earnings,
         overall_solar_self_consumption_pct)
        """
        total_fixed_cost_nzd = 0.0
        total_variable_cost_nzd = 0.0
        total_solar_self_consumption_savings = 0.0
        total_solar_export_earnings = 0.0

        # Since only ElectricityPlan has non-zero solar %,
        # we just capture that single value
        overall_solar_self_consumption_pct = 0.0

        for energy_plan in [
            self.electricity_plan,
            self.natural_gas_plan,
            self.lpg_plan,
            self.wood_price,
            self.petrol_price,
            self.diesel_price,
            self.public_charging_price,
            self.other_vehicle_costs,
        ]:
            (
                fixed_cost_nzd,
                variable_cost_nzd,
                sc_savings_nzd,
                export_earnings_nzd,
                sc_percentage,
            ) = energy_plan.calculate_cost(usage_profile)

            total_fixed_cost_nzd += fixed_cost_nzd
            total_variable_cost_nzd += variable_cost_nzd
            total_solar_self_consumption_savings += sc_savings_nzd
            total_solar_export_earnings += export_earnings_nzd

            # Only update from the electricity plan
            if isinstance(energy_plan, ElectricityPlan):
                overall_solar_self_consumption_pct = sc_percentage

        return (
            total_fixed_cost_nzd,
            total_variable_cost_nzd,
            total_solar_self_consumption_savings,
            total_solar_export_earnings,
            overall_solar_self_consumption_pct,
        )
