"""
Classes representing yearly fuel usage profiles for different household areas.
For simplicity they all have the same components even though some of them
might not be relevant for some areas.
"""

import functools
from dataclasses import dataclass

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.usage_profile_helpers import (
    day_night_flag,
    daytime_total_usage,
    ensure_8760_array,
    night_shift,
    nighttime_total_usage,
    zeros_8760,
)

day_mask = day_night_flag()


class ElectricityUsage(BaseModel):
    """
    Annual electricity usage for a time-slice,
    stored as NumPy arrays, representing each hour of the year
    (not as a pandas Series).

    Attributes:
      fixed_time_kwh: Usage that is fixed to time of use
        and cannot be ripple-controlled (kWh).
      shift_able_kwh: Usage that can be time-shifted
        between day and night but is assumed not to be on the
        ripple-control circuit (kWh) (E.g. we will put some home EV
        charging in this bucket.)
    """

    fixed_time_kwh: np.ndarray = Field(
        default_factory=zeros_8760,
        description="Usage that is fixed to time of use "
        "and cannot be ripple-controlled (kWh)",
    )
    shift_able_kwh: np.ndarray = Field(
        default_factory=zeros_8760,
        description=(
            "Usage that can be time-shifted between day and night but is "
            "assumed not to be on the ripple-control circuit (kWh) "
            "(E.g. we will put some home EV charging in this bucket.)"
        ),
    )

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra="ignore",
    )

    @field_validator(
        "fixed_time_kwh",
        "shift_able_kwh",
        mode="before",
    )
    @classmethod
    def validate_arrays(cls, value):
        """
        Ensure that the value is an array of correct shape.
        Raises a ValueError if not an array or if the array
        is not of shape (8760,).
        """
        return ensure_8760_array(value)

    def __add__(self, other: "ElectricityUsage") -> "ElectricityUsage":
        """
        Element-wise addition of two ElectricityUsage objects.
        """
        if not isinstance(other, ElectricityUsage):
            raise TypeError(f"Cannot add ElectricityUsage with {type(other)}")
        return ElectricityUsage(
            fixed_time_kwh=self.fixed_time_kwh + other.fixed_time_kwh,
            shift_able_kwh=self.shift_able_kwh + other.shift_able_kwh,
        )

    def __radd__(self, other):
        """
        Enable sum() to work properly by treating 0 as the additive identity.
        """
        if other == 0:
            return self
        return self.__add__(other)

    @functools.cached_property
    def total_usage(self) -> np.ndarray:
        """
        Total electricity usage timeseries (kWh) for the year.
        """
        return self.fixed_time_kwh + self.shift_able_kwh

    @functools.cached_property
    def total_usage_night_shifted(self) -> np.ndarray:
        """
        Total electricity usage timeseries (kWh) for the year,
        if all consumption that can be shifted to night-time is shifted.
        """
        return self.fixed_time_kwh + night_shift(self.shift_able_kwh)

    @functools.cached_property
    def total_fixed_time_usage(self) -> np.ndarray:
        """
        Total electricity usage (kWh) that is fixed to a specific time.
        """
        return self.fixed_time_kwh

    @functools.cached_property
    def total_shift_able_usage(self) -> np.ndarray:
        """
        Total electricity usage (kWh) that can be shifted in time.
        """
        return self.shift_able_kwh

    @functools.cached_property
    def daytime_total_usage(self) -> np.ndarray:
        """
        Daytime electricity usage (kWh) time series.
        """
        return daytime_total_usage(self.total_usage)

    @functools.cached_property
    def nighttime_total_usage(self) -> np.ndarray:
        """
        Nighttime electricity usage (kWh) time series.
        """
        return nighttime_total_usage(self.total_usage)

    @functools.cached_property
    def daytime_total_usage_night_shifted(self) -> np.ndarray:
        """
        Daytime electricity usage (kWh) time series after night shift.
        """
        return daytime_total_usage(self.total_usage_night_shifted)

    @functools.cached_property
    def nighttime_total_usage_night_shifted(self) -> np.ndarray:
        """
        Nighttime electricity usage (kWh) time series after night shift.
        """
        return nighttime_total_usage(self.total_usage_night_shifted)

    @functools.cached_property
    def shift_able_kwh_night_shifted(self) -> np.ndarray:
        """
        Shiftable uncontrolled electricity usage timeseries (kWh) for the
        year, if it has been shifted to night-time.
        """
        return night_shift(self.shift_able_kwh)

    @functools.cached_property
    def total_night_shifted(self) -> np.ndarray:
        """
        Total uncontrolled electricity usage (kWh) over the entire year,
        if all consumption that can be shifted to night-time is shifted.
        """
        return self.fixed_time_kwh + night_shift(self.shift_able_kwh)


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

    Stored as NumPy arrays, representing each hour of the year
    (not as a pandas Series).


    Attributes:
        has_solar: bool, indicates whether solar generation is present
        generation_kwh: energy generated in each of the
        8760 hours of a non-leap year based on TMY data.
    """

    has_solar: bool = Field(
        default=False,
        description="Indicates whether solar generation is present.",
    )
    fixed_time_generation_kwh: np.ndarray = Field(
        default_factory=zeros_8760,
        description="Hourly generation timeseries for a year (kWh)",
    )

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra="ignore",
    )

    @field_validator("fixed_time_generation_kwh", mode="before")
    @classmethod
    def validate_arrays(cls, value):
        """
        Ensure that the value is an array of correct shape.
        Raises a ValueError if not an array or if the array
        is not of shape (8760,).
        """
        return ensure_8760_array(value)

    @property
    def total(self) -> float:
        """
        Total electricity usage (kWh) over the entire year.
        """
        return float(np.sum(self.fixed_time_generation_kwh))

    @property
    def timeseries(self) -> np.ndarray:
        """
        Total electricity usage (kWh) over the entire year.
        """
        return self.fixed_time_generation_kwh

    def __add__(self, other: "SolarGeneration") -> "SolarGeneration":
        """
        Element-wise addition of two SolarGeneration objects.
        """
        return SolarGeneration(
            fixed_time_generation_kwh=self.fixed_time_generation_kwh
            + other.fixed_time_generation_kwh,
            has_solar=self.has_solar or other.has_solar,
        )

    def __radd__(self, other):
        """
        Enable sum() to work properly by treating 0 as the additive identity.
        """
        if other == 0:
            return self
        return self.__add__(other)


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
                    profile.electricity_kwh.total_usage.sum()
                    - profile.solar_generation_kwh.total
                )
                if profile.solar_generation_kwh.has_solar
                else round_float(profile.electricity_kwh.total_usage.sum())
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
