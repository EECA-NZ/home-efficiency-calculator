"""
Classes representing different energy plans for households.
"""

# pylint: disable=too-many-locals

from typing import Dict, Tuple

import numpy as np
from pydantic import BaseModel

from app.models.usage_profiles import EnergyCostBreakdown, SolarSavingsBreakdown
from app.services.usage_profile_helpers import day_night_flag, night_shift

day_mask = day_night_flag()


def _make_usage_array(
    kwh_value: float,
    profile: np.ndarray | None,
    do_night_shift: bool,
) -> np.ndarray:
    """
    Convert a single (kwh_value, profile) pair into a full 8760 array.

    If profile is not None, multiply it by kwh_value to get per-hour usage.
    If do_night_shift is True, apply `night_shift(...)` to the profile first.
    If profile is None, spread kwh_value uniformly across 8760 hours.

    Returns an array of shape (8760,).
    """
    if profile is None:
        # No timeseries => distribute usage evenly
        return np.full(8760, kwh_value / 8760.0)
    # We do have a profile; apply night shift if requested
    arr = night_shift(profile) if do_night_shift else profile
    return kwh_value * arr


class ElectricityPlan(BaseModel):
    """
    Electricity plan for a household.

    Daily charge is in NZD per day.
    Import and export rates are in NZD per kWh.

    Implementation covers three tariff structure types:
        - Day/Night
        - All inclusive (single rate)

    Features:
        1. Supports day/night or or single-rate.
        2. Determines solar self-consumption and export earnings.
        3. For simplicity, in Day/Night we assume solar offsets only day imports;
           in single-rate we do a net offset.
        4. If solar is absent, we optionally shift shiftable usage to night
           for cost savings.
        5. Uses NumPy vectorized operations for performance.
    """

    name: str
    fixed_rate: float  # NZD per day
    import_rates: Dict[str, float]  # e.g. {"Day": 0.25, "Night": 0.15}
    export_rates: Dict[str, float]  # e.g. {"Uncontrolled": 0.12}

    def calculate_cost(self, usage_profile) -> EnergyCostBreakdown:
        """
        Returns an EnergyCostBreakdown for this electricity plan and usage profile.

        Includes:
        - fixed cost: daily connection charge × number of days
        - variable cost: import minus export credits
        - solar savings breakdown (if solar is present)

        If solar_generation_kwh is > 0, we do not shift usage to night;
        otherwise, we do (to realize typical cost savings).
        """
        # Decide whether to use "night shift" usage
        use_night_shift = True
        if usage_profile.solar_generation_kwh is not None:
            if usage_profile.solar_generation_kwh.total > 0:
                use_night_shift = False

        # Identify the tariff structure
        tariff_structure = set(self.import_rates.keys())

        # Convert fixed-time usage and shiftable usage to 8760 arrays
        fixed_time_usage_kwh = _make_usage_array(
            usage_profile.electricity_kwh.fixed_time_kwh,
            usage_profile.electricity_kwh.fixed_time_profile,
            do_night_shift=False,  # fixed-time load doesn't get night-shifted
        )
        shift_able_usage_kwh = _make_usage_array(
            usage_profile.electricity_kwh.shift_able_kwh,
            usage_profile.electricity_kwh.shift_able_profile,
            do_night_shift=use_night_shift,
        )

        # Gather solar array (0 if none)
        solar_kwh = usage_profile.solar_generation_kwh.timeseries

        (
            variable_cost_nzd,
            solar_self_consumption_savings_nzd,
            solar_export_earnings_nzd,
            solar_self_consumption_pct,
        ) = self._compute_variable_cost(
            tariff_structure,
            fixed_time_usage_kwh,
            shift_able_usage_kwh,
            solar_kwh,
        )

        # Fixed cost is daily connection × connection days
        fixed_cost_nzd = usage_profile.elx_connection_days * self.fixed_rate

        # Build the solar savings breakdown if we have any self-consumption or exports
        if solar_self_consumption_savings_nzd > 0 or solar_export_earnings_nzd > 0:
            import_rate = (
                self.import_rates.get("Day")
                or self.import_rates.get("Uncontrolled")
                or 0.0
            )
            export_rate = self.export_rates.get("Uncontrolled") or 0.0

            solar = SolarSavingsBreakdown(
                self_consumption_kwh=(
                    solar_self_consumption_savings_nzd / import_rate
                    if import_rate > 0
                    else 0.0
                ),
                export_kwh=(
                    solar_export_earnings_nzd / export_rate if export_rate > 0 else 0.0
                ),
                self_consumption_savings_nzd=solar_self_consumption_savings_nzd,
                export_earnings_nzd=solar_export_earnings_nzd,
                self_consumption_pct=solar_self_consumption_pct,
            )
        else:
            solar = None

        return EnergyCostBreakdown(
            fixed_cost_nzd=fixed_cost_nzd,
            variable_cost_nzd=variable_cost_nzd,
            solar=solar,
        )

    # pylint: disable=too-many-arguments, too-many-positional-arguments
    def _compute_variable_cost(
        self,
        tariff_structure,
        fixed_time_kwh: np.ndarray,
        shift_able_kwh: np.ndarray,
        solar_kwh: np.ndarray,
    ) -> Tuple[float, float, float, float]:
        """
        Router method that picks the appropriate helper for the given tariff structure.
        """
        if tariff_structure == {"Day", "Night"}:
            return self._compute_variable_cost_day_night(
                fixed_time_kwh, shift_able_kwh, solar_kwh
            )

        if tariff_structure == {"All inclusive"}:
            total_usage_kwh = fixed_time_kwh + shift_able_kwh
            return self._compute_variable_cost_single_rate(
                total_usage_kwh, solar_kwh, rate_key="All inclusive"
            )

        if tariff_structure == {"Uncontrolled"}:
            total_usage_kwh = fixed_time_kwh + shift_able_kwh
            return self._compute_variable_cost_single_rate(
                total_usage_kwh, solar_kwh, rate_key="Uncontrolled"
            )

        raise ValueError(f"Unexpected tariff structure: {tariff_structure}")

    # --------------------------------------------------------------------
    #   DAY/NIGHT
    # --------------------------------------------------------------------
    def _compute_variable_cost_day_night(
        self,
        fixed_time_usage_kwh: np.ndarray,
        shift_able_usage_kwh: np.ndarray,
        solar_kwh: np.ndarray,
    ) -> Tuple[float, float, float, float]:
        """
        For a day/night tariff, we assume all solar generation offsets day usage first.

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

        # Combine total usage (8760 array), then sum up day vs. night usage
        usage_kwh = fixed_time_usage_kwh + shift_able_usage_kwh
        day_usage_kwh = (usage_kwh * day_mask).sum()
        night_usage_kwh = (usage_kwh * (~day_mask)).sum()

        # Self-consumption breakdown:
        #   - offset fixed_time loads first (day import),
        #   - then offset shiftable (assumed night).
        fixed_time_self_consumption_kwh = np.minimum(fixed_time_usage_kwh, solar_kwh)
        residual_solar_kwh = solar_kwh - fixed_time_self_consumption_kwh

        shift_able_self_consumption_kwh = np.minimum(
            shift_able_usage_kwh, residual_solar_kwh
        )

        export_kwh = np.maximum(0, residual_solar_kwh - shift_able_usage_kwh)

        # Sums
        annual_kwh_exported = export_kwh.sum()
        total_self_consumed_kwh = (
            fixed_time_self_consumption_kwh.sum()
            + shift_able_self_consumption_kwh.sum()
        )

        # Net usage after offset
        net_day_usage_kwh = day_usage_kwh - fixed_time_self_consumption_kwh.sum()
        net_night_usage_kwh = night_usage_kwh - shift_able_self_consumption_kwh.sum()

        day_cost_nzd = net_day_usage_kwh * day_rate
        night_cost_nzd = net_night_usage_kwh * night_rate

        total_export_credit_nzd = annual_kwh_exported * export_rate
        total_import_cost_nzd = day_cost_nzd + night_cost_nzd
        net_import_cost_nzd = total_import_cost_nzd - total_export_credit_nzd

        # “Savings” = how much usage we offset (i.e. the avoided cost)
        solar_offset_savings_nzd = (
            fixed_time_self_consumption_kwh.sum() * day_rate
            + shift_able_self_consumption_kwh.sum() * night_rate
        )

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
            total_export_credit_nzd,
            solar_self_consumption_pct,
        )

    # --------------------------------------------------------------------
    #  'ALL INCLUSIVE' OR 'UNCONTROLLED' SINGLE RATE
    # --------------------------------------------------------------------
    def _compute_variable_cost_single_rate(
        self, usage_kwh: np.ndarray, solar_kwh: np.ndarray, rate_key: str
    ) -> Tuple[float, float, float, float]:
        """
        Single import rate + optional buy-back export rate.
        Solar offsets total usage equally (net usage).
        """
        export_rate = self.export_rates.get("Uncontrolled", 0.0)
        import_rate = self.import_rates[rate_key]

        # Cost if no solar:
        baseline_import_cost_nzd = (usage_kwh * import_rate).sum()

        net_usage_kwh = usage_kwh - solar_kwh
        net_export_kwh = np.clip(-net_usage_kwh, 0, None)
        net_import_kwh = np.clip(net_usage_kwh, 0, None)

        # Self-consumption is min(usage, solar) hour by hour
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

    def calculate_cost(self, usage_profile) -> EnergyCostBreakdown:
        """
        Calculate the cost of natural gas for a household.

        Returns an EnergyCostBreakdown object with fixed and variable costs.
        """
        keys = set(self.import_rates.keys())
        variable_cost_nzd = 0.0

        if keys == {"Uncontrolled"}:
            # Just multiply by the usage scalar
            variable_cost_nzd += (
                usage_profile.natural_gas_kwh * self.import_rates["Uncontrolled"]
            )
        else:
            raise ValueError(f"Unexpected import_rates keys: {keys}")

        fixed_cost_nzd = usage_profile.natural_gas_connection_days * self.fixed_rate
        return EnergyCostBreakdown(
            fixed_cost_nzd=fixed_cost_nzd,
            variable_cost_nzd=variable_cost_nzd,
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
        Calculate the cost of LPG for a household.

        Returns an EnergyCostBreakdown object with fixed and variable costs.
        """
        variable_cost_nzd = usage_profile.lpg_kwh * self.per_lpg_kwh
        fixed_cost_nzd = usage_profile.lpg_tanks_rental_days * self.fixed_rate
        return EnergyCostBreakdown(
            fixed_cost_nzd=fixed_cost_nzd,
            variable_cost_nzd=variable_cost_nzd,
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
        Calculate the cost of wood for a household.

        Returns an EnergyCostBreakdown object with fixed and variable costs.
        """
        variable_cost_nzd = usage_profile.wood_kwh * self.per_wood_kwh
        return EnergyCostBreakdown(
            fixed_cost_nzd=0.0, variable_cost_nzd=variable_cost_nzd, solar=None
        )


class PetrolPrice(BaseModel):
    """
    Petrol plan for a household.
    """

    name: str
    per_petrol_litre: float

    def calculate_cost(self, usage_profile) -> EnergyCostBreakdown:
        """
        Calculate the cost of petrol for a household.

        Returns an EnergyCostBreakdown object with fixed and variable costs.
        """
        variable_cost_nzd = usage_profile.petrol_litres * self.per_petrol_litre
        return EnergyCostBreakdown(
            fixed_cost_nzd=0.0, variable_cost_nzd=variable_cost_nzd, solar=None
        )


class DieselPrice(BaseModel):
    """
    Diesel plan for a household.
    """

    name: str
    per_diesel_litre: float

    def calculate_cost(self, usage_profile) -> EnergyCostBreakdown:
        """
        Calculate the cost of diesel for a household.

        Returns an EnergyCostBreakdown object with fixed and variable costs.
        """
        variable_cost_nzd = usage_profile.diesel_litres * self.per_diesel_litre
        return EnergyCostBreakdown(
            fixed_cost_nzd=0.0, variable_cost_nzd=variable_cost_nzd, solar=None
        )


class PublicChargingPrice(BaseModel):
    """
    Public charging plan for a household.
    """

    name: str
    per_kwh: float

    def calculate_cost(self, usage_profile) -> EnergyCostBreakdown:
        """
        Calculate the cost of public charging for a household.

        Returns an EnergyCostBreakdown object with fixed and variable costs.
        """
        variable_cost_nzd = usage_profile.public_ev_charger_kwh * self.per_kwh
        return EnergyCostBreakdown(
            fixed_cost_nzd=0.0, variable_cost_nzd=variable_cost_nzd, solar=None
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
        Calculate the cost of non-energy vehicle ownership for a household.

        Returns an EnergyCostBreakdown object with fixed and variable costs.
        """
        variable_cost_nzd = (
            self.nzd_per_year_licensing
            + self.nzd_per_year_servicing_cost
            + usage_profile.thousand_km * self.nzd_per_000_km_road_user_charges
        )
        return EnergyCostBreakdown(
            fixed_cost_nzd=0.0, variable_cost_nzd=variable_cost_nzd, solar=None
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

        Returns
        -------
        EnergyCostBreakdown
            That includes total fixed/variable energy costs, plus
            solar savings breakdown if solar generation is present
            (only from electricity_plan).
        """
        # 1) Calculate cost from electricity plan first,
        #    as it's the only one that can return a nontrivial solar component.
        electricity_cost = self.electricity_plan.calculate_cost(usage_profile)
        total_fixed_cost_nzd = electricity_cost.fixed_cost_nzd
        total_variable_cost_nzd = electricity_cost.variable_cost_nzd

        # If the electricity cost has solar, grab those fields.
        # Otherwise, set them to zero.
        if electricity_cost.solar:
            total_solar_self_consumption_savings = (
                electricity_cost.solar.self_consumption_savings_nzd
            )
            total_solar_export_earnings = electricity_cost.solar.export_earnings_nzd
            total_self_consumption_kwh = electricity_cost.solar.self_consumption_kwh
            total_export_kwh = electricity_cost.solar.export_kwh
            overall_solar_self_consumption_pct = (
                electricity_cost.solar.self_consumption_pct
            )
        else:
            total_solar_self_consumption_savings = 0.0
            total_solar_export_earnings = 0.0
            total_self_consumption_kwh = 0.0
            total_export_kwh = 0.0
            overall_solar_self_consumption_pct = 0.0

        # 2) Now calculate cost from all other plans, adding up
        #    their fixed/variable costs. None of these typically have solar.
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
            total_fixed_cost_nzd += cost.fixed_cost_nzd
            total_variable_cost_nzd += cost.variable_cost_nzd

        # 3) Build final breakdown
        #    If there's no solar on electricity, solar=None; otherwise fill in.
        solar_breakdown = None
        if total_solar_self_consumption_savings > 0 or total_solar_export_earnings > 0:
            solar_breakdown = SolarSavingsBreakdown(
                self_consumption_kwh=total_self_consumption_kwh,
                export_kwh=total_export_kwh,
                self_consumption_savings_nzd=total_solar_self_consumption_savings,
                export_earnings_nzd=total_solar_export_earnings,
                self_consumption_pct=overall_solar_self_consumption_pct,
            )

        return EnergyCostBreakdown(
            fixed_cost_nzd=total_fixed_cost_nzd,
            variable_cost_nzd=total_variable_cost_nzd,
            solar=solar_breakdown,
        )
