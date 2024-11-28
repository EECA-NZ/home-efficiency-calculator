"""
Classes representing yearly fuel usage profiles for different household areas.
For simplicity they all have the same components even though some of them
might not be relevant for some areas.
"""

from pydantic import BaseModel, ConfigDict, Field


class YearlyFuelUsageProfile(BaseModel):
    """
    Base class for yearly fuel usage profiles for different household areas.
    In addition to fuel usage, includes associated consumption parameters e.g.
    connection costs + kilometers travelled subject to road user charges.

    Attributes:
    elx_connection_days: float, number of days with electricity connection
    inflexible_day_kwh: float, electricity usage that must occur during the day
    flexible_kwh: float, electricity usage that can happen at night or on
        controlled rates (whichever is cheaper)
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
    inflexible_day_kwh: float = Field(
        default=0.0, description="Electricity usage that must occur during the day"
    )
    flexible_kwh: float = Field(
        default=0.0,
        description="Electricity usage that can happen at night or on controlled rates",
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
