"""
Classes representing yearly fuel usage profiles for different household areas.
For simplicity they all have the same components even though some of them
might not be relevant for some areas.
"""

import functools
from dataclasses import dataclass
from typing import Optional

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.usage_profile_helpers import (
    day_night_flag,
    daytime_total_usage,
    ensure_8760_array,
    night_shift,
    nighttime_total_usage,
)

day_mask = day_night_flag()


class ElectricityUsage(BaseModel):
    """
    Annual electricity usage for a time-slice,
    stored as NumPy arrays, representing hours of the year.

    Attributes:
      fixed_time_kwh: Usage that is fixed to time of use (kWh).
      shift_able_kwh: Usage that can be time-shifted between day and night (kWh).
      fixed_time_profile: Optional dimensionless hourly usage array (8760 elements),
        normalized to sum to 1.0.
      shift_able_profile: Optional dimensionless hourly usage array (8760 elements),
        normalized to sum to 1.0.
    """

    fixed_time_kwh: float = Field(
        0.0,
        description="Usage that is fixed to time of use (kWh).",
    )
    shift_able_kwh: float = Field(
        0.0,
        description="Usage that can be time-shifted between day and night (kWh).",
    )
    fixed_time_profile: np.ndarray | None = Field(
        default=None,
        description="Optional 8760 hourly usage profile for fixed_time_kwh.",
    )
    shift_able_profile: np.ndarray | None = Field(
        default=None,
        description="Optional 8760 hourly usage profile for shift_able_kwh.",
    )

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra="ignore",
    )

    @field_validator("fixed_time_profile", "shift_able_profile", mode="before")
    @classmethod
    def validate_arrays(cls, value):
        """
        Ensure that the value, if provided, is an array of correct shape (8760,).
        Raises a ValueError if it's not None but isn't shaped (8760,).
        """
        if value is None:
            return None
        return ensure_8760_array(value)

    @model_validator(mode="after")
    def set_default_profiles(self):
        """
        Ensure consistency and usability:

        - If a kWh value is zero and its profile is None, but the other profile
          is provided, set a flat profile (uniform distribution summing to 1).
        - If a kWh value is non-zero, the corresponding profile must be provided
          if the other profile is provided.
        - If provided, profiles must sum approximately to 1.
        """

        def flat_profile():
            return np.full(8760, 1 / 8760)

        # Check and handle fixed_time_profile
        if self.fixed_time_kwh == 0:
            if self.fixed_time_profile is None and self.shift_able_profile is not None:
                self.fixed_time_profile = flat_profile()
        else:
            if self.fixed_time_profile is None and self.shift_able_profile is not None:
                raise ValueError("fixed_time_profile should have been provided.")
            if self.fixed_time_profile is not None:
                if not np.isclose(self.fixed_time_profile.sum(), 1.0, atol=1e-6):
                    raise ValueError("fixed_time_profile must sum to 1.")

        # Check and handle shift_able_profile
        if self.shift_able_kwh == 0:
            if self.shift_able_profile is None and self.fixed_time_profile is not None:
                self.shift_able_profile = flat_profile()
        else:
            if self.shift_able_profile is None and self.fixed_time_profile is not None:
                raise ValueError("shift_able_profile should have been provided")
            if self.shift_able_profile is not None:
                if not np.isclose(self.shift_able_profile.sum(), 1.0, atol=1e-6):
                    raise ValueError("shift_able_profile must sum to 1.")

        return self

    def __add__(self, other: "ElectricityUsage") -> "ElectricityUsage":
        """
        Element-wise addition of two ElectricityUsage objects.
        Allows profiles to be None if the corresponding kWh is zero.
        """
        if not isinstance(other, ElectricityUsage):
            raise TypeError(f"Cannot add ElectricityUsage with {type(other)}")

        def normalized_sum_profiles(a_kwh, a_prof, b_kwh, b_prof):
            if a_kwh == 0 and b_kwh == 0:
                return None
            if a_kwh == 0:
                return b_prof
            if b_kwh == 0:
                return a_prof
            combined_profile = a_kwh * a_prof + b_kwh * b_prof
            summed_profile = combined_profile.sum()
            if summed_profile == 0:
                raise ValueError("Sum of profiles is zero, cannot normalize.")
            return combined_profile / summed_profile

        fixed_time_profile = normalized_sum_profiles(
            self.fixed_time_kwh,
            self.fixed_time_profile,
            other.fixed_time_kwh,
            other.fixed_time_profile,
        )
        shift_able_profile = normalized_sum_profiles(
            self.shift_able_kwh,
            self.shift_able_profile,
            other.shift_able_kwh,
            other.shift_able_profile,
        )

        return ElectricityUsage(
            fixed_time_kwh=self.fixed_time_kwh + other.fixed_time_kwh,
            shift_able_kwh=self.shift_able_kwh + other.shift_able_kwh,
            fixed_time_profile=fixed_time_profile,
            shift_able_profile=shift_able_profile,
        )

    def __radd__(self, other):
        """
        Enable sum() to work properly by treating 0 as the additive identity.
        """
        if other == 0:
            return self
        return self.__add__(other)

    @functools.cached_property
    def annual_kwh(self) -> float:
        """
        Total annual kWh, returned as a scalar float.
        This does NOT require that profiles be present.
        """
        return self.fixed_time_kwh + self.shift_able_kwh

    @functools.cached_property
    def total_usage(self) -> np.ndarray:
        """
        Total electricity usage timeseries (kWh) for the year.
        Profiles must be provided; raises AssertionError otherwise.
        """
        assert (
            self.fixed_time_profile is not None and self.shift_able_profile is not None
        ), "Both fixed_time_profile and shift_able_profile must be provided."
        return (
            self.fixed_time_kwh * self.fixed_time_profile
            + self.shift_able_kwh * self.shift_able_profile
        )

    @functools.cached_property
    def total_usage_night_shifted(self) -> np.ndarray:
        """
        Total electricity usage timeseries (kWh) for the year,
        if all shiftable consumption is shifted to night-time.
        """
        assert (
            self.fixed_time_profile is not None and self.shift_able_profile is not None
        ), "Both fixed_time_profile and shift_able_profile must be provided."
        return (
            self.fixed_time_kwh * self.fixed_time_profile
            + self.shift_able_kwh * night_shift(self.shift_able_profile)
        )

    @functools.cached_property
    def total_fixed_time_usage(self) -> np.ndarray:
        """
        Fixed-time electricity usage timeseries (kWh).
        """
        assert (
            self.fixed_time_profile is not None
        ), "fixed_time_profile must be provided."
        return self.fixed_time_kwh * self.fixed_time_profile

    @functools.cached_property
    def total_shift_able_usage(self) -> np.ndarray:
        """
        Shiftable electricity usage timeseries (kWh).
        """
        assert (
            self.shift_able_profile is not None
        ), "shift_able_profile must be provided."
        return self.shift_able_kwh * self.shift_able_profile

    @functools.cached_property
    def daytime_total_usage(self) -> np.ndarray:
        """
        Daytime electricity usage timeseries (kWh).
        """
        return daytime_total_usage(self.total_usage)

    @functools.cached_property
    def nighttime_total_usage(self) -> np.ndarray:
        """
        Nighttime electricity usage timeseries (kWh).
        """
        return nighttime_total_usage(self.total_usage)

    @functools.cached_property
    def daytime_total_usage_night_shifted(self) -> np.ndarray:
        """
        Daytime electricity usage timeseries after shifting (kWh).
        """
        return daytime_total_usage(self.total_usage_night_shifted)

    @functools.cached_property
    def nighttime_total_usage_night_shifted(self) -> np.ndarray:
        """
        Nighttime electricity usage timeseries after shifting (kWh).
        """
        return nighttime_total_usage(self.total_usage_night_shifted)

    @functools.cached_property
    def shift_able_kwh_night_shifted(self) -> np.ndarray:
        """
        Shiftable electricity usage timeseries after night shift (kWh).
        """
        assert (
            self.shift_able_profile is not None
        ), "shift_able_profile must be provided."
        return self.shift_able_kwh * night_shift(self.shift_able_profile)

    @functools.cached_property
    def total_night_shifted(self) -> np.ndarray:
        """
        Total electricity usage timeseries (kWh), shiftable usage night-shifted.
        """
        return self.total_usage_night_shifted


@dataclass
class SolarSavingsBreakdown:
    """
    Stores the financial and energy breakdown of solar savings.
    """

    self_consumption_kwh: float
    export_kwh: float
    self_consumption_savings_nzd: float
    export_earnings_nzd: float
    self_consumption_pct: float


@dataclass
class EnergyCostBreakdown:
    """
    Contains total fixed and variable costs and (optionally) solar interaction results.
    """

    fixed_cost_nzd: float
    variable_cost_nzd: float
    solar: SolarSavingsBreakdown | None = None


class SolarGeneration(BaseModel):
    """
    Annual electricity generation by solar PV in a
    Typical Meteorological Year (TMY). The system
    is assumed to be north-facing and tilted at 30 degrees.
    Each climate zone has a different solar generation
    profile.

    Stored as NumPy arrays, representing each hour of the year.

    Attributes:
        solar_generation_kwh: Optional total generation in kWh for the year.
        solar_generation_profile: Optional hourly profile (dimensionless, length 8760),
            normalized to sum to 1.0.
    """

    solar_generation_kwh: Optional[float] = Field(
        default=None, description="Total annual generation from solar (kWh)."
    )
    solar_generation_profile: Optional[np.ndarray] = Field(
        default=None,
        description="Hourly profile (8760 values), normalized to sum to 1.0.",
    )

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra="ignore",
    )

    @field_validator("solar_generation_profile", mode="before")
    @classmethod
    def validate_arrays(cls, value):
        """
        Ensure that the value, if provided, is an array of correct shape (8760,).
        Raises a ValueError if it's not None but isn't shaped (8760,).
        """
        if value is None:
            return None
        return ensure_8760_array(value)

    @model_validator(mode="after")
    def validate_consistency(self):
        """
        Validation rules:
        - If solar_generation_kwh is None or 0, profile must be None.
        - If solar_generation_kwh > 0, profile must exist and sum to ~1.
        """
        if self.solar_generation_kwh is None or self.solar_generation_kwh == 0:
            if self.solar_generation_profile is not None:
                raise ValueError(
                    "solar_generation_profile must be None"
                    "if solar_generation_kwh is None or 0."
                )
        else:
            if self.solar_generation_profile is not None:
                # pylint: disable=no-member
                if not np.isclose(self.solar_generation_profile.sum(), 1.0, atol=1e-6):
                    raise ValueError("solar_generation_profile must sum to 1.")
            else:
                raise ValueError(
                    "solar_generation_profile must be provided"
                    "when solar_generation_kwh > 0."
                )

        return self

    def __add__(self, other: "SolarGeneration") -> "SolarGeneration":
        """
        Element-wise addition of two SolarGeneration objects.
        Allows profiles to be None if kWh is zero.
        """

        def normalized_sum_profiles(a_kwh, a_prof, b_kwh, b_prof):
            if a_kwh == 0 and b_kwh == 0:
                return None
            if a_kwh == 0:
                return b_prof
            if b_kwh == 0:
                return a_prof
            combined = a_kwh * a_prof + b_kwh * b_prof
            total = combined.sum()
            if total == 0:
                raise ValueError("Sum of profiles is zero, cannot normalize.")
            return combined / total

        a_kwh = self.solar_generation_kwh or 0.0
        b_kwh = other.solar_generation_kwh or 0.0

        return SolarGeneration(
            solar_generation_kwh=a_kwh + b_kwh,
            solar_generation_profile=normalized_sum_profiles(
                a_kwh,
                self.solar_generation_profile,
                b_kwh,
                other.solar_generation_profile,
            ),
        )

    def __radd__(self, other):
        """
        Enable sum() to work properly by treating 0 as the additive identity.
        """
        if other == 0:
            return self
        return self.__add__(other)

    @functools.cached_property
    def total(self) -> float:
        """
        Total electricity generation (kWh) over the year.
        Returns 0.0 if not set.
        """
        return float(self.solar_generation_kwh or 0.0)

    @functools.cached_property
    def timeseries(self) -> np.ndarray:
        """
        Hourly generation timeseries (kWh).
        """
        if self.solar_generation_kwh is None or self.solar_generation_profile is None:
            return np.zeros(8760)
        return self.solar_generation_kwh * self.solar_generation_profile


class YearlyFuelUsageProfile(BaseModel):
    """
    Base class for yearly fuel usage profiles for different household areas.
    In addition to fuel usage, includes associated consumption parameters e.g.
    connection costs + kilometers travelled subject to road user charges.

    Attributes:
    elx_connection_days: float, number of days with electricity connection
    electricity_kwh: ElectricityUsage, electricity consumption
    solar_generation_kwh: SolarGeneration, generation by solar panels
    natural_gas_connection_days: float, number of days with natural gas
        connection
    natural_gas_kwh: float, natural gas usage
    lpg_tanks_rental_days: float, number of days with LPG tanks rental
        (if using bottled gas, we apply a daily cost based on 2 tanks)
    lpg_kwh: float, LPG usage
    wood_kwh: float, wood usage
    petrol_litres: float, petrol usage
    diesel_litres: float, diesel usage
    public_ev_charger_kwh: float, public EV charger usage
    thousand_km: float, thousands of km for RUCs
    """

    elx_connection_days: float = Field(
        default=0.0, description="Number of days with electricity connection"
    )
    electricity_kwh: ElectricityUsage = Field(
        default_factory=ElectricityUsage,
        description="""Electricity consumption breakdown (kWh).""",
    )
    solar_generation_kwh: SolarGeneration = Field(
        default_factory=SolarGeneration,
        description="""Electricity generated by solar panels (kWh).""",
    )
    natural_gas_connection_days: float = Field(
        default=0.0, description="Number of days with natural gas connection"
    )
    natural_gas_kwh: float = Field(default=0.0, description="Natural gas usage")
    lpg_tanks_rental_days: float = Field(
        default=0.0, description="Number of days with LPG tanks rental"
    )
    lpg_kwh: float = Field(default=0.0, description="LPG usage")
    wood_kwh: float = Field(default=0.0, description="Wood usage")
    petrol_litres: float = Field(default=0.0, description="Petrol usage")
    diesel_litres: float = Field(default=0.0, description="Diesel usage")
    public_ev_charger_kwh: float = Field(
        default=0.0, description="Public EV charger usage"
    )
    thousand_km: float = Field(default=0.0, description="Thousands of km for RUCs")

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra="ignore",
    )

    def __add__(self, other: "YearlyFuelUsageProfile") -> "YearlyFuelUsageProfile":
        """
        Add two YearlyFuelUsageProfile objects together. This is used to
        combine the usage profiles of different household areas.

        To avoid double-counting, fixed cost attributes (e.g. connection days) are
        taken as the maximum of the two profiles, while usage amounts are summed.
        """
        return YearlyFuelUsageProfile(
            elx_connection_days=max(
                self.elx_connection_days, other.elx_connection_days
            ),
            electricity_kwh=self.electricity_kwh + other.electricity_kwh,
            solar_generation_kwh=self.solar_generation_kwh + other.solar_generation_kwh,
            natural_gas_connection_days=max(
                self.natural_gas_connection_days, other.natural_gas_connection_days
            ),
            natural_gas_kwh=self.natural_gas_kwh + other.natural_gas_kwh,
            lpg_tanks_rental_days=max(
                self.lpg_tanks_rental_days, other.lpg_tanks_rental_days
            ),
            lpg_kwh=self.lpg_kwh + other.lpg_kwh,
            wood_kwh=self.wood_kwh + other.wood_kwh,
            petrol_litres=self.petrol_litres + other.petrol_litres,
            diesel_litres=self.diesel_litres + other.diesel_litres,
            public_ev_charger_kwh=self.public_ev_charger_kwh
            + other.public_ev_charger_kwh,
            thousand_km=self.thousand_km + other.thousand_km,
        )

    def __radd__(self, other):
        """
        This allows sum() to work properly
        by treating 0 as the additive identity.
        """
        if other == 0:
            return self
        return self.__add__(other)


class YearlyFuelUsageReport(BaseModel):
    """
    Report class for yearly fuel usage profiles for different household areas.
    In addition to fuel usage, includes associated consumption parameters e.g.
    connection costs + kilometers travelled subject to road user charges.

    Attributes are same as for YearlyFuelUsageProfile, but with float values
    instead of NumPy arrays, and simplified for reporting:
      electricity_kwh: float
      solar_generation_kwh: float
      natural_gas_kwh: float
      lpg_kwh: float
      wood_kwh: float
      petrol_litres: float
      diesel_litres: float
      public_ev_charger_kwh: float
    """

    electricity_kwh: float
    natural_gas_kwh: float = Field(0.0, description="Natural gas usage")
    lpg_kwh: float = Field(0.0, description="LPG usage")
    wood_kwh: float = Field(0.0, description="Wood usage")
    petrol_litres: float = Field(0.0, description="Petrol usage")
    diesel_litres: float = Field(0.0, description="Diesel usage")
    public_ev_charger_kwh: float = Field(0.0, description="Public EV charger usage")

    def __init__(
        self, profile: YearlyFuelUsageProfile, decimal_places: int = 2, **data
    ):
        def round_float(value: float) -> float:
            return round(value, decimal_places)

        super().__init__(
            electricity_kwh=(
                round_float(
                    profile.electricity_kwh.annual_kwh
                    - profile.solar_generation_kwh.total
                )
                if profile.solar_generation_kwh.solar_generation_kwh is not None
                and profile.solar_generation_kwh.solar_generation_kwh > 0
                else round_float(profile.electricity_kwh.annual_kwh)
            ),
            natural_gas_kwh=round_float(profile.natural_gas_kwh),
            lpg_kwh=round_float(profile.lpg_kwh),
            wood_kwh=round_float(profile.wood_kwh),
            petrol_litres=round_float(profile.petrol_litres),
            diesel_litres=round_float(profile.diesel_litres),
            public_ev_charger_kwh=round_float(profile.public_ev_charger_kwh),
            **data,
        )


class HeatingYearlyFuelUsageProfile(YearlyFuelUsageProfile):
    """
    Space heating yearly fuel usage profile.

    Derived from YearlyFuelUsageProfile with the same attributes.

    Keeping this class distinct allows us to be specific about
    the household function (here, space heating) whose energy
    use is being referred to.
    """


class HotWaterYearlyFuelUsageProfile(YearlyFuelUsageProfile):
    """
    Hot water yearly fuel usage profile.

    Derived from YearlyFuelUsageProfile with the same attributes.

    Keeping this class distinct allows us to be specific about
    the household function (here, hot water heating) whose energy
    use is being referred to.
    """


class CooktopYearlyFuelUsageProfile(YearlyFuelUsageProfile):
    """
    Cooktop yearly fuel usage profile.

    Derived from YearlyFuelUsageProfile with the same attributes.

    Keeping this class distinct allows us to be specific about
    the household function (here, stovetop cooking) whose energy
    use is being referred to.
    """


class DrivingYearlyFuelUsageProfile(YearlyFuelUsageProfile):
    """
    Driving yearly fuel usage profile.

    Derived from YearlyFuelUsageProfile with the same attributes.

    Keeping this class distinct allows us to be specific about
    the household function (here, vehicle driving) whose energy
    use is being referred to.
    """


class SolarYearlyFuelGenerationProfile(YearlyFuelUsageProfile):
    """
    Yearly solar energy generation profile.

    Derived from YearlyFuelUsageProfile with the same attributes.

    Keeping this class distinct allows us to be specific about the
    part of the household whose energy action (here, rooftop solar
    electricity generation) is being referred to.
    """


class HouseholdOtherElectricityUsage(YearlyFuelUsageProfile):
    """
    'Other household electricity' yearly fuel usage profile.

    Derived from YearlyFuelUsageProfile with the same attributes.

    Keeping this class distinct allows us to be specific about the
    part of the household (here, everything except the components
    that we model separately) whose energy use is being referred to.
    """


class HouseholdYearlyFuelUsageProfile(YearlyFuelUsageProfile):
    """
    Overall household yearly fuel usage profile.

    Derived from YearlyFuelUsageProfile with the same attributes.

    Keeping this class distinct class allows us to be specific that
    we are considering the overall household energy use.
    """
