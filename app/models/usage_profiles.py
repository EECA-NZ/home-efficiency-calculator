"""
Classes representing yearly fuel usage profiles for different household areas.
For simplicity they all have the same components even though some of them
might not be relevant for some areas.
"""

import functools
import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.usage_profile_helpers import (
    day_night_flag,
    ensure_8760_array,
    zeros_8760,
    night_shift,
)

day_mask = day_night_flag()


class ElectricityUsageProfile(BaseModel):
    """
    Annual electricity usage for a time-slice,
    stored as NumPy arrays. Each entry represents
    the usage in a specific hour of the year.

    Attributes:
      fixed_time_uncontrolled: Usage that is fixed to time of use
        and cannot be ripple-controlled (kWh).
      fixed_time_controllable: Usage that can be under ripple
        control (kWh) (E.g. some hot water cylinder load).
      shift_able_uncontrolled: Usage that can be time-shifted
        between day and night but is assumed not to be on the
        ripple-control circuit (kWh) (E.g. we will put some home EV
        charging in this bucket.)
      shift_able_controllable: Flexible electricity consumption (kWh):
        if solar generation is present, the consumption can
        happen during the day, otherwise it can be shifted
        to take advantage of night rates if preferable. Can also
        be under ripple control. (E.g. some hot water cylinder load).
    """

    fixed_time_uncontrolled: np.ndarray = Field(
        default_factory=zeros_8760,
        description="Usage that is fixed to time of use "
        "and cannot be ripple-controlled (kWh)",
    )
    fixed_time_controllable: np.ndarray = Field(
        default_factory=zeros_8760,
        description="Usage that can be under ripple control (kWh) "
        "(E.g. some hot water cylinder load)."
    )
    shift_able_uncontrolled: np.ndarray = Field(
        default_factory=zeros_8760,
        description=(
            "Usage that can be time-shifted between day and night but is "
            "assumed not to be on the ripple-control circuit (kWh) "
            "(E.g. we will put some home EV charging in this bucket.)"
        ),
    )
    shift_able_controllable: np.ndarray = Field(
        default_factory=zeros_8760,
        description=(
            "Flexible electricity consumption (kWh): if solar "
            "generation is present, the consumption can "
            "happen during the day, otherwise it can be shifted "
            "to take advantage of night rates if preferable. "
            "Can also be under ripple control."
            "(E.g. some hot water cylinder load)."
        ),
    )

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra="ignore",
    )

    @field_validator(
        "fixed_time_uncontrolled",
        "fixed_time_controllable",
        "shift_able_uncontrolled",
        "shift_able_controllable",
        mode="before",
    )
    @classmethod
    def validate_arrays(cls, value):
        """
        Ensure that the arrays are the correct shape.
        """
        return ensure_8760_array(value)

    def __add__(self, other: "ElectricityUsageProfile") -> "ElectricityUsageProfile":
        """
        Element-wise addition of two ElectricityUsageProfile objects.
        """
        return ElectricityUsageProfile(
            fixed_time_uncontrolled=self.fixed_time_uncontrolled
            + other.fixed_time_uncontrolled,
            fixed_time_controllable=self.fixed_time_controllable
            + other.fixed_time_controllable,
            shift_able_uncontrolled=self.shift_able_uncontrolled
            + other.shift_able_uncontrolled,
            shift_able_controllable=self.shift_able_controllable
            + other.shift_able_controllable,
        )

    def __radd__(self, other):
        """
        Enable sum() to work properly by treating 0 as the additive identity.
        """
        if other == 0:
            return self
        return self.__add__(other)

    @functools.cached_property
    def total(self) -> np.ndarray:
        """
        Total electricity usage timeseries (kWh) for the year.
        """
        return (
            self.fixed_time_controllable
            + self.fixed_time_uncontrolled
            + self.shift_able_controllable
            + self.shift_able_uncontrolled
        )

    @functools.cached_property
    def total_with_night_shift(self) -> np.ndarray:
        """
        Total electricity usage timeseries (kWh) for the year,
        if all consumption that can be shifted to night-time is shifted.
        """
        return (
            self.fixed_time_controllable
            + self.fixed_time_uncontrolled
            + night_shift(self.shift_able_controllable)
            + night_shift(self.shift_able_uncontrolled)
        )

    @functools.cached_property
    def uncontrolled(self) -> np.ndarray:
        """
        Total uncontrolled electricity usage (kWh) as an array.
        """
        return self.fixed_time_uncontrolled + self.shift_able_uncontrolled

    @functools.cached_property
    def uncontrolled_with_night_shift(self) -> np.ndarray:
        """
        Total uncontrolled electricity usage (kWh) over the entire year,
        if all consumption that can be shifted to night-time is shifted.
        """
        return self.fixed_time_uncontrolled + night_shift(self.shift_able_uncontrolled)

    @functools.cached_property
    def controllable(self) -> np.ndarray:
        """
        Total controllable electricity usage (kWh) over the entire year.
        """
        return self.fixed_time_controllable + self.shift_able_controllable

    @functools.cached_property
    def controllable_with_night_shift(self) -> np.ndarray:
        """
        Total controllable electricity usage (kWh) over the entire year,
        if all consumption that can be shifted to night-time is shifted.
        """
        return self.fixed_time_controllable + night_shift(self.shift_able_controllable)

    @functools.cached_property
    def shift_able(self) -> np.ndarray:
        """
        Total electricity usage (kWh) that can be shifted in time.
        """
        return self.shift_able_uncontrolled + self.shift_able_controllable

    @functools.cached_property
    def fixed_time(self) -> np.ndarray:
        """
        Total electricity usage (kWh) that is fixed to a specific time.
        """
        return self.fixed_time_uncontrolled + self.fixed_time_controllable


class ElectricityUsageReport(BaseModel):
    """
    Annual electricity usage (kwh) by category.
    """

    fixed_time_uncontrolled: float = Field(
        0.0,
        description="Usage that is fixed and cannot be ripple-controlled (kWh)",
    )
    fixed_time_controllable: float = Field(
        0.0,
        description="Usage that can be under ripple control (kWh)",
    )
    shift_able_uncontrolled: float = Field(
        0.0,
        description="PROBABLY REDUNDANT. Usage that can be time-shifted from day "
        "to night but cannot be ripple-controlled (kWh)",
    )
    shift_able_controllable: float = Field(
        0.0,
        description="""Flexible electricity consumption (kWh).:
        if solar generation is present, the consumption can
        happen during the day, otherwise it can be shifted to
        take advantage of night rates if preferable. Can also
        be under ripple control.""",
    )


class SolarGenerationProfile(BaseModel):
    """
    Annual electricity generation by solar PV in a
    Typical Meteorological Year (TMY). The system
    is assumed to be north-facing and tilted at 30 degrees.
    Each climate zone has a different solar generation
    profile.

    Attributes:
        generation_kwh: energy generated in each of the
        8760 hours of a non-leap year based on TMY data.
    """

    generation_kwh: np.ndarray = Field(
        default_factory=zeros_8760,
        description="Hourly generation timeseries for a year (kWh)",
    )

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra="ignore",
    )

    @field_validator("generation_kwh", mode="before")
    @classmethod
    def validate_arrays(cls, value):
        """
        Ensure that the arrays are the correct shape.
        """
        return ensure_8760_array(value)

    @property
    def total(self) -> float:
        """
        Total electricity usage (kWh) over the entire year.
        """
        return float(np.sum(self.generation_kwh))

    def __add__(self, other: "SolarGenerationProfile") -> "SolarGenerationProfile":
        """
        Element-wise addition of two SolarGenerationProfile objects.
        """
        return SolarGenerationProfile(
            generation_kwh=self.generation_kwh + other.generation_kwh
        )

    def __radd__(self, other):
        """
        Enable sum() to work properly by treating 0 as the additive identity.
        """
        if other == 0:
            return self
        return self.__add__(other)


class SolarGenerationReport(BaseModel):
    """
    Annual electricity generation by solar PV.
    """

    generation_kwh: float = Field(
        0.0, description="Total electricity generated by solar panels (kWh)"
    )


class YearlyFuelUsageProfile(BaseModel):
    """
    Base class for yearly fuel usage profiles for different household areas.
    In addition to fuel usage, includes associated consumption parameters e.g.
    connection costs + kilometers travelled subject to road user charges.

    Attributes:
    elx_connection_days: float, number of days with electricity connection
    electricity_kwh: ElectricityUsageProfile, electricity consumption
    solar_generation_kwh: SolarGenerationProfile, electricity generated by solar panels
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
    thousand_km_petrol: float, thousands of km for RUCs
    thousand_km_diesel: float, thousands of km for RUCs
    thousand_km_hybrid: float, thousands of km for RUCs
    thousand_km_plug_in_hybrid: float, thousands of km for RUCs
    thousand_km_electric: float, thousands of km for RUCs
    """

    elx_connection_days: float = Field(
        default=0.0, description="Number of days with electricity connection"
    )
    electricity_kwh: ElectricityUsageProfile = Field(
        default_factory=ElectricityUsageProfile,
        description="""Electricity consumption breakdown (kWh).""",
    )
    solar_generation_kwh: SolarGenerationProfile = Field(
        default_factory=SolarGenerationProfile,
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
    instead of NumPy arrays.
    """

    elx_connection_days: float = Field(
        0.0, description="Number of days with electricity connection"
    )
    electricity_kwh: ElectricityUsageReport
    solar_generation_kwh: SolarGenerationReport
    natural_gas_connection_days: float = Field(
        0.0, description="Number of days with natural gas connection"
    )
    natural_gas_kwh: float = Field(0.0, description="Natural gas usage")
    lpg_tanks_rental_days: float = Field(
        0.0, description="Number of days with LPG tanks rental"
    )
    lpg_kwh: float = Field(0.0, description="LPG usage")
    wood_kwh: float = Field(0.0, description="Wood usage")
    petrol_litres: float = Field(0.0, description="Petrol usage")
    diesel_litres: float = Field(0.0, description="Diesel usage")
    public_ev_charger_kwh: float = Field(0.0, description="Public EV charger usage")
    thousand_km: float = Field(0.0, description="Thousands of km for RUCs")

    def __init__(
        self, profile: YearlyFuelUsageProfile, decimal_places: int = 2, **data
    ):
        def round_float(value: float) -> float:
            return round(value, decimal_places)

        super().__init__(
            elx_connection_days=round_float(profile.elx_connection_days),
            electricity_kwh=ElectricityUsageReport(
                fixed_time_uncontrolled=round_float(
                    profile.electricity_kwh.fixed_time_uncontrolled.sum()
                ),
                fixed_time_controllable=round_float(
                    profile.electricity_kwh.fixed_time_controllable.sum()
                ),
                shift_able_uncontrolled=round_float(
                    profile.electricity_kwh.shift_able_uncontrolled.sum()
                ),
                shift_able_controllable=round_float(
                    profile.electricity_kwh.shift_able_controllable.sum()
                ),
            ),
            solar_generation_kwh=SolarGenerationReport(
                generation_kwh=round_float(profile.solar_generation_kwh.total),
            ),
            natural_gas_connection_days=round_float(
                profile.natural_gas_connection_days
            ),
            natural_gas_kwh=round_float(profile.natural_gas_kwh),
            lpg_tanks_rental_days=round_float(profile.lpg_tanks_rental_days),
            lpg_kwh=round_float(profile.lpg_kwh),
            wood_kwh=round_float(profile.wood_kwh),
            petrol_litres=round_float(profile.petrol_litres),
            diesel_litres=round_float(profile.diesel_litres),
            public_ev_charger_kwh=round_float(profile.public_ev_charger_kwh),
            thousand_km=round_float(profile.thousand_km),
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


class HouseholdOtherElectricityUsageProfile(YearlyFuelUsageProfile):
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
