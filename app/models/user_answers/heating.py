"""
Class for storing user answers on living room space heating.
"""

from typing import Literal, Optional

from pydantic import BaseModel

from ...constants import (
    DAYS_IN_YEAR,
    ELECTRIC_HEATER_SPACE_HEATING_EFFICIENCY,
    GAS_SPACE_HEATING_EFFICIENCY,
    HEAT_PUMP_COP_BY_CLIMATE_ZONE,
    HEATING_DAYS_PER_WEEK,
    HEATING_DEGREE_DAYS,
    LIVING_AREA_FRACTION,
    LOG_BURNER_SPACE_HEATING_EFFICIENCY,
    LPG_SPACE_HEATING_EFFICIENCY,
    SPACE_HEATING_SETPOINT,
    STANDARD_HOME_KWH_HEATING_DEMAND_PER_HEATING_DEGREE_DAY,
    THERMAL_ENVELOPE_QUALITY,
)
from ...models.hourly_profiles.heating import space_heating_profile
from ...services.helpers import heating_frequency_factor
from ...services.postcode_lookups.get_climate_zone import climate_zone
from ..usage_profiles import ElectricityUsage, YearlyFuelUsageProfile


class HeatingAnswers(BaseModel):
    """
    Answers to questions about the user's space heating.
    """

    main_heating_source: Literal[
        "Piped gas heater",
        "Bottled gas heater",
        "Heat pump",
        "Electric heater",
        "Wood burner",
    ]
    alternative_main_heating_source: Optional[
        Literal[
            "Piped gas heater",
            "Bottled gas heater",
            "Heat pump",
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

    def energy_usage_pattern(
        self, your_home, solar_aware: bool, use_alternative: bool = False
    ) -> YearlyFuelUsageProfile:
        """
        Return the yearly fuel usage profile for space heating.

        This method calculates the annual energy usage for space heating based on
        the user's inputs (main heating source, insulation quality, etc.). The
        calculation provides an hourly usage profile if solar_aware is True. For
        space heating, any electricity demand is assumed to be at time-of-use.

        Parameters
        ----------
        your_home : YourHomeAnswers
            Answers to questions about the user's home (e.g., postcode).
        solar_aware : bool
            If True, produce a detailed usage profile (allocating daytime
            load by hour of the year). If False, a simpler aggregated profile
            is returned (no 8760 data), reducing computational overhead.
        use_alternative : bool, optional
            If True, use the alternative main heating source provided by the user,
            rather than their current source.

        Returns
        -------
        YearlyFuelUsageProfile
            The yearly fuel usage profile for space heating, including fuel or
            electricity consumption as appropriate. If electric, a year's hourly
            usage profile (8760 hours) is provided if solar_aware is True.
        """
        main_heating_source = (
            self.alternative_main_heating_source
            if use_alternative
            else self.main_heating_source
        )
        cz = climate_zone(your_home.postcode)

        # Calculate the total kWh of space heating demand (service energy)
        heating_energy_service_demand = (
            HEATING_DEGREE_DAYS[cz]
            * STANDARD_HOME_KWH_HEATING_DEMAND_PER_HEATING_DEGREE_DAY
            * LIVING_AREA_FRACTION
            * THERMAL_ENVELOPE_QUALITY[self.insulation_quality]
            * heating_frequency_factor(HEATING_DAYS_PER_WEEK[self.heating_during_day])
        )

        # Return early for each main heating source
        if main_heating_source == "Piped gas heater":
            return YearlyFuelUsageProfile(
                natural_gas_kwh=heating_energy_service_demand
                / GAS_SPACE_HEATING_EFFICIENCY,
                natural_gas_connection_days=DAYS_IN_YEAR,
                elx_connection_days=DAYS_IN_YEAR,
            )

        if main_heating_source == "Bottled gas heater":
            return YearlyFuelUsageProfile(
                lpg_kwh=heating_energy_service_demand / LPG_SPACE_HEATING_EFFICIENCY,
                lpg_tanks_rental_days=DAYS_IN_YEAR,
                elx_connection_days=DAYS_IN_YEAR,
            )

        if main_heating_source == "Heat pump":
            heating = YearlyFuelUsageProfile(
                electricity_kwh=ElectricityUsage(
                    fixed_day_kwh=heating_energy_service_demand
                    / HEAT_PUMP_COP_BY_CLIMATE_ZONE[cz],
                    fixed_ngt_kwh=0.0,
                    fixed_profile=(
                        space_heating_profile(
                            postcode=your_home.postcode,
                            heating_during_day=self.heating_during_day,
                            setpoint=SPACE_HEATING_SETPOINT,
                        )
                        if solar_aware
                        else None
                    ),
                    shift_abl_kwh=0.0,
                    shift_profile=None,
                ),
                elx_connection_days=DAYS_IN_YEAR,
            )
            return heating

        if main_heating_source == "Electric heater":
            return YearlyFuelUsageProfile(
                electricity_kwh=ElectricityUsage(
                    fixed_day_kwh=heating_energy_service_demand
                    / ELECTRIC_HEATER_SPACE_HEATING_EFFICIENCY,
                    fixed_ngt_kwh=0.0,
                    fixed_profile=(
                        space_heating_profile(
                            postcode=your_home.postcode,
                            heating_during_day=self.heating_during_day,
                            setpoint=SPACE_HEATING_SETPOINT,
                        )
                        if solar_aware
                        else None
                    ),
                    shift_abl_kwh=0.0,
                    shift_profile=None,
                ),
                elx_connection_days=DAYS_IN_YEAR,
            )

        if main_heating_source == "Wood burner":
            return YearlyFuelUsageProfile(
                wood_kwh=heating_energy_service_demand
                / LOG_BURNER_SPACE_HEATING_EFFICIENCY,
                elx_connection_days=DAYS_IN_YEAR,
            )

        raise ValueError(f"Unknown heating source: {main_heating_source}")
