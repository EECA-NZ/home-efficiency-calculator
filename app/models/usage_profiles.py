"""
Classes representing yearly fuel usage profiles for different household areas.
For simplicity they all have the same components even though some of them
might not be relevant for some areas.
"""

from pydantic import BaseModel, ConfigDict, Field


class ElectricityUsage(BaseModel):
    """
    Annual electricity usage for a time-slice.

    Attributes:
    uncontrolled: float, usage that is fixed and cannot be ripple-controlled
    controllable: float, usage that can be shifted using ripple control mechanisms
    solar_self_consumption: float, usage that is offset by on-site solar production
    """

    uncontrolled: float = Field(
        0.0, description="Usage that is fixed and cannot be ripple-controlled (kWh)"
    )
    controllable: float = Field(
        0.0,
        description="Usage that can be shifted using ripple control mechanisms (kWh)",
    )
    solar_self_consumption: float = Field(
        0.0,
        description="Usage that is immediately met by on-site solar production (kWh)",
    )

    def __add__(self, other: "ElectricityUsage") -> "ElectricityUsage":
        """
        Return a new ElectricityUsage instance
        representing the sum of this usage and another.
        """
        return ElectricityUsage(
            uncontrolled=self.uncontrolled + other.uncontrolled,
            controllable=self.controllable + other.controllable,
            solar_self_consumption=self.solar_self_consumption
            + other.solar_self_consumption,
        )

    def __radd__(self, other):
        """
        Enable sum() to work properly by treating 0
        as the additive identity.
        """
        if other == 0:
            return self
        return self.__add__(other)

    @property
    def total(self) -> float:
        """
        Total electricity usage for this time-slice.
        """
        return self.uncontrolled + self.controllable + self.solar_self_consumption

    @property
    def from_grid(self) -> float:
        """
        Total electricity usage from the grid for this time-slice.
        """
        return self.uncontrolled + self.controllable


class YearlyFuelUsageProfile(BaseModel):
    """
    Base class for yearly fuel usage profiles for different household areas.
    In addition to fuel usage, includes associated consumption parameters e.g.
    connection costs + kilometers travelled subject to road user charges.

    Attributes:
    elx_connection_days: float, number of days with electricity connection
    day_kwh: ElectricityUsage, that must occur during the day
    anytime_kwh: ElectricityUsage, that can happen at night or day
        Note that here, (uncontrolled=0):
        In the "anytime" usage category, the assumption is that all
        electricity usage is flexible. That is, there is no portion
        of the load that is fixed or non-shiftable. Therefore, the
        uncontrolled component is always set to 0. This reflects the
        idea that any consumption in this timeslice can be optimally
        rescheduled based on tariff signals or demand response
        opportunities.
    night_kwh: ElectricityUsage, that must occur at night
        Note that here, (uncontrolled=0, solar_self_consumption=0):
        For the "night" usage category, not only is the uncontrolled
        component set to 0 (again, indicating that there is no fixed
        load during these hours), but solar_self_consumption is also
        assumed to be 0. This is because on-site solar generation is
        not available during the night; hence, there is no immediate
        solar contribution to the load in this period.
    solar_export_kwh: float, electricity exported to the grid from solar panels
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
    day_kwh: ElectricityUsage = Field(
        default_factory=ElectricityUsage,
        description="""Daytime electricity consumption breakdown (kWh).
        Must occur during the day, so solar self-consumption can be non-zero.
        (uncontrolled, controllable, solar_self_consumption)
        """,
    )
    anytime_kwh: ElectricityUsage = Field(
        default_factory=ElectricityUsage,
        description="""Flexible electricity consumption: night rates if available (kWh).
        Can happen at night or day, so solar self-consumption can be non-zero.
        (uncontrolled=0, controllable, solar_self_consumption)
        """,
    )
    night_kwh: ElectricityUsage = Field(
        default_factory=ElectricityUsage,
        description="""Nighttime electricity consumption: night rates if available (kWh)
        Must occur at night, so solar self-consumption is zero.
        (uncontrolled=0, controllable, solar_self_consumption=0)
        """,
    )
    solar_export_kwh: float = Field(
        0.0, description="Electricity exported to the grid from solar panels (kWh)"
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

    model_config = ConfigDict(validate_assignment=True, extra="ignore")

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
            day_kwh=self.day_kwh + other.day_kwh,
            anytime_kwh=self.anytime_kwh + other.anytime_kwh,
            night_kwh=self.night_kwh + other.night_kwh,
            solar_export_kwh=self.solar_export_kwh + other.solar_export_kwh,
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
        # This allows sum() to work properly by treating 0 as the additive identity.
        if other == 0:
            return self
        return self.__add__(other)


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
