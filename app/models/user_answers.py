"""
Classes for storing user answers to the questions provided by online users.
"""

from typing import Literal, Optional
from pydantic import BaseModel, constr, conint
from .usage_profiles import (
    HeatingYearlyFuelUsageProfile,
    HotWaterYearlyFuelUsageProfile,
    CooktopYearlyFuelUsageProfile,
    DrivingYearlyFuelUsageProfile,
    SolarYearlyFuelGenerationProfile,
)
from ..services import get_climate_zone
from ..services.helpers import heating_frequency_factor
from ..constants import (
    DAYS_IN_YEAR,
    AVERAGE_HOUSEHOLD_SIZE,
    SOLAR_RESOURCE_KWH_PER_DAY,
    HEATING_DEGREE_DAYS,
    STANDARD_HOME_KWH_HEATING_DEMAND_PER_HEATING_DEGREE_DAY,
    LIVING_AREA_FRACTION,
    THERMAL_ENVELOPE_QUALITY,
    HEATING_DAYS_PER_WEEK,
    HEAT_PUMP_COP_BY_CLIMATE_ZONE,
)


class YourHomeAnswers(BaseModel):
    """
    Answers to questions about the user's home.
    """

    people_in_house: conint(ge=1, le=6)
    postcode: constr(strip_whitespace=True, pattern=r"^\d{4}$")
    disconnect_gas: bool
    user_provided: bool


class HeatingAnswers(BaseModel):
    """
    Answers to questions about the user's space heating.
    """

    main_heating_source: Literal[
        "Piped gas heater",
        "Bottled gas heater",
        "Heat pump",
        "Heat pump (ducted)",
        "Electric heater",
        "Wood burner",
    ]
    alternative_main_heating_source: Optional[
        Literal[
            "Piped gas heater",
            "Bottled gas heater",
            "Heat pump",
            "Heat pump (ducted)",
            "Electric heater",
            "Wood burner",
        ]
    ] = None
    heating_during_day: Literal[
        "Never",
        "1-2 days a week",
        "3-4 days a week",
        "5-7 days a week",
    ]
    insulation_quality: Literal[
        "Not well insulated", "Moderately insulated", "Well insulated"
    ]
    user_provided: bool

    def energy_usage_pattern(
        self, your_home, use_alternative: bool = False
    ) -> HeatingYearlyFuelUsageProfile:
        """
        Return the yearly fuel usage profile for space heating.

        The profile is based on the answers provided by the user.

        Parameters
        ----------
        your_home : YourHomeAnswers
            Answers to questions about the user's home.

        Returns
        -------
        HeatingYearlyFuelUsageProfile
            The yearly fuel usage profile for space heating.
        """
        main_heating_source = (
            self.alternative_main_heating_source
            if use_alternative
            else self.main_heating_source
        )
        climate_zone = get_climate_zone.climate_zone(your_home.postcode)
        heat_pump_cop = HEAT_PUMP_COP_BY_CLIMATE_ZONE[climate_zone]
        heating_energy_service_demand = (
            HEATING_DEGREE_DAYS[climate_zone]
            * STANDARD_HOME_KWH_HEATING_DEMAND_PER_HEATING_DEGREE_DAY
            * LIVING_AREA_FRACTION
            * THERMAL_ENVELOPE_QUALITY[self.insulation_quality]
            * heating_frequency_factor(HEATING_DAYS_PER_WEEK[self.heating_during_day])
        )
        fuel_usage = {
            "Piped gas heater": {
                "natural_gas_kwh": heating_energy_service_demand,
                "natural_gas_connection_days": DAYS_IN_YEAR,
            },
            "Bottled gas heater": {
                "lpg_kwh": heating_energy_service_demand,
                "lpg_tank_rental_days": 2 * DAYS_IN_YEAR,
            },
            "Heat pump": {
                "day_kwh": heating_energy_service_demand / heat_pump_cop,
            },
            "Heat pump (ducted)": {
                "day_kwh": heating_energy_service_demand / heat_pump_cop,
            },
            "Electric heater": {
                "day_kwh": heating_energy_service_demand,
            },
            "Wood burner": {
                "wood_kwh": heating_energy_service_demand,
            },
        }
        return HeatingYearlyFuelUsageProfile(
            elx_connection_days=DAYS_IN_YEAR,
            day_kwh=fuel_usage[main_heating_source].get("day_kwh", 0),
            flexible_kwh=0,
            natural_gas_connection_days=fuel_usage[main_heating_source].get(
                "natural_gas_connection_days", 0
            ),
            natural_gas_kwh=fuel_usage[main_heating_source].get("natural_gas_kwh", 0),
            lpg_tank_rental_days=fuel_usage[main_heating_source].get(
                "lpg_tank_rental_days", 0
            ),
            lpg_kwh=fuel_usage[main_heating_source].get("lpg_kwh", 0),
            wood_kwh=fuel_usage[main_heating_source].get("wood_kwh", 0),
            petrol_litres=0,
            diesel_litres=0,
        )


class HotWaterAnswers(BaseModel):
    """
    Answers to questions about the user's hot water heating.
    """

    hot_water_usage: Literal["Low", "Average", "High"]
    hot_water_heating_source: Literal[
        "Electric hot water cylinder",
        "Piped gas hot water cylinder",
        "Piped gas instantaneous",
        "Bottled gas instantaneous",
        "Hot water heat pump",
    ]
    alternative_hot_water_heating_source: Optional[
        Literal[
            "Electric hot water cylinder",
            "Piped gas hot water cylinder",
            "Piped gas instantaneous",
            "Bottled gas instantaneous",
            "Hot water heat pump",
        ]
    ] = None
    user_provided: bool

    def energy_usage_pattern(
        self, your_home, use_alternative: bool = True
    ) -> HotWaterYearlyFuelUsageProfile:
        """
        Return the yearly fuel usage profile for hot water heating.

        The profile is based on the answers provided by the user.

        Parameters
        ----------
        your_home : YourHomeAnswers
            Answers to questions about the user's home.

        Returns
        -------
        HotWaterYearlyFuelUsageProfile
            The yearly fuel usage profile for hot water heating.
        """
        hot_water_heating_source = (
            self.alternative_hot_water_heating_source
            if use_alternative
            else self.hot_water_heating_source
        )
        total_kwh = {"Hot water heat pump": 3000}.get(
            hot_water_heating_source, 0
        ) * your_home.people_in_house
        day_night = {"Low": (0.6, 0.4), "Average": (0.7, 0.3), "High": (0.8, 0.2)}
        day_kwh = total_kwh * day_night[self.hot_water_usage][0]
        flexible_kwh = total_kwh * day_night[self.hot_water_usage][1]
        return HotWaterYearlyFuelUsageProfile(
            elx_connection_days=365,
            day_kwh=day_kwh,
            flexible_kwh=flexible_kwh,
            natural_gas_connection_days=0,
            natural_gas_kwh=0,
            lpg_tank_rental_days=0,
            lpg_kwh=0,
            wood_kwh=0,
            petrol_litres=0,
            diesel_litres=0,
        )


class CooktopAnswers(BaseModel):
    """
    Answers to questions about the user's stove.
    """

    cooktop: Literal[
        "Electric induction", "Piped gas", "Bottled gas", "Electric (coil or ceramic)"
    ]
    alternative_cooktop: Optional[
        Literal[
            "Electric induction",
            "Piped gas",
            "Bottled gas",
            "Electric (coil or ceramic)",
        ]
    ] = None
    user_provided: bool

    def energy_usage_pattern(
        self, your_home, use_alternative: bool = False
    ) -> CooktopYearlyFuelUsageProfile:
        """
        Return the yearly fuel usage profile for cooking.

        Parameters
        ----------
        your_home : YourHomeAnswers
            Answers to questions about the user's home.

        Returns
        -------
        CooktopYearlyFuelUsageProfile
            The yearly fuel usage profile for cooking.
        """
        usage_factors = {
            "Electric induction": {
                "standard_household_kwh": 294,
                "elx_connection_days": DAYS_IN_YEAR,
            },
            "Electric (coil or ceramic)": {
                "standard_household_kwh": 325,
                "elx_connection_days": DAYS_IN_YEAR,
            },
            "Piped gas": {
                "standard_household_kwh": 760,
                "natural_gas_connection_days": DAYS_IN_YEAR,
            },
            "Bottled gas": {
                "standard_household_kwh": 760,
                "lpg_tank_rental_days": 2 * DAYS_IN_YEAR,
            },
        }
        cooktop_type = self.alternative_cooktop if use_alternative else self.cooktop
        if cooktop_type not in usage_factors:
            raise ValueError(f"Unknown cooktop type: {cooktop_type}")

        factor = usage_factors[cooktop_type]
        total_kwh = (
            factor["standard_household_kwh"]
            * (1 + your_home.people_in_house)
            / (1 + AVERAGE_HOUSEHOLD_SIZE)
        )

        return CooktopYearlyFuelUsageProfile(
            elx_connection_days=factor.get("elx_connection_days", 0),
            day_kwh=total_kwh if "Electric" in cooktop_type else 0,
            flexible_kwh=0,
            natural_gas_connection_days=factor.get("natural_gas_connection_days", 0),
            natural_gas_kwh=total_kwh if cooktop_type == "Piped gas" else 0,
            lpg_tank_rental_days=factor.get("lpg_tank_rental_days", 0),
            lpg_kwh=total_kwh if cooktop_type == "Bottled gas" else 0,
            wood_kwh=0,
            petrol_litres=0,
            diesel_litres=0,
        )


class DrivingAnswers(BaseModel):
    """
    Answers to questions about the user's vehicle and driving patterns.
    """

    vehicle_type: Literal["Petrol", "Diesel", "Hybrid", "Plug-in hybrid", "Electric"]
    alternative_vehicle_type: Optional[
        Literal["Petrol", "Diesel", "Hybrid", "Plug-in hybrid", "Electric"]
    ] = None
    vehicle_size: Literal["Small", "Medium", "Large"]
    km_per_week: Literal["50 or less", "100", "200", "300", "400 or more"]
    user_provided: bool

    def energy_usage_pattern(
        self, your_home, use_alternative: bool = False
    ) -> DrivingYearlyFuelUsageProfile:
        """
        Return the yearly fuel usage profile for driving.

        The profile is based on the answers provided by the user.

        Parameters
        ----------
        your_home : YourHomeAnswers
            Answers to questions about the user's home.

        Returns
        -------
        DrivingYearlyFuelUsageProfile
            The yearly fuel usage profile for driving.
        """
        vehicle_type = (
            self.alternative_vehicle_type if use_alternative else self.vehicle_type
        )
        petrol_usage = {"Petrol": 1000}.get(vehicle_type, 0) * your_home.people_in_house
        return DrivingYearlyFuelUsageProfile(
            elx_connection_days=0,
            day_kwh=0,
            flexible_kwh=0,
            natural_gas_connection_days=0,
            natural_gas_kwh=0,
            lpg_tank_rental_days=0,
            lpg_kwh=0,
            wood_kwh=0,
            petrol_litres=petrol_usage,
            diesel_litres=0,
        )


class SolarAnswers(BaseModel):
    """
    Does the house include solar panels?
    """

    hasSolar: bool
    user_provided: bool

    def energy_generation(self, your_home) -> SolarYearlyFuelGenerationProfile:
        """
        Return the yearly energy generation profile for solar energy generation.

        The profile is based on the answers provided by the user.

        Parameters
        ----------
        your_home : YourHomeAnswers
            Answers to questions about the user's home.

        Returns
        -------
        SolarYearlyFuelUsageProfile
            The yearly fuel usage profile for solar energy generation.
        """
        my_climate_zone = get_climate_zone.climate_zone(your_home.postcode)
        annual_generation_kwh = 0
        if self.hasSolar:
            annual_generation_kwh = (
                SOLAR_RESOURCE_KWH_PER_DAY[my_climate_zone] * DAYS_IN_YEAR
            )

        return SolarYearlyFuelGenerationProfile(
            elx_connection_days=0,
            day_kwh=-annual_generation_kwh,
            flexible_kwh=0,
            natural_gas_connection_days=0,
            natural_gas_kwh=0,
            lpg_tank_rental_days=0,
            lpg_kwh=0,
            wood_kwh=0,
            petrol_litres=0,
            diesel_litres=0,
        )


class HouseholdEnergyProfileAnswers(BaseModel):
    """
    Answers to all questions about the user's household energy usage.

    This class is used to store all the answers provided by the user.
    """

    your_home: Optional[YourHomeAnswers] = None
    heating: Optional[HeatingAnswers] = None
    hot_water: Optional[HotWaterAnswers] = None
    cooktop: Optional[CooktopAnswers] = None
    driving: Optional[DrivingAnswers] = None
    solar: Optional[SolarAnswers] = None
