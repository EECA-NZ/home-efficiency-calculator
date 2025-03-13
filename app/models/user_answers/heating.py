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
    STANDARD_HOME_KWH_HEATING_DEMAND_PER_HEATING_DEGREE_DAY,
    THERMAL_ENVELOPE_QUALITY,
)
from ...services import get_climate_zone
from ...services.helpers import heating_frequency_factor
from ...services.usage_profile_helpers.heating import space_heating_profile
from ..usage_profiles import ElectricityUsageTimeseries, HeatingYearlyFuelUsageProfile


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
        self, your_home, solar, use_alternative: bool = False
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
        # solar is currently unused here but required for signature
        # compatibility with other components, which are assumed
        # to alter their electricity consumption patterns based
        # on presence or absence of solar.
        _ = solar
        main_heating_source = (
            self.alternative_main_heating_source
            if use_alternative
            else self.main_heating_source
        )
        climate_zone = get_climate_zone.climate_zone(your_home.postcode)
        heating_energy_service_demand = (
            HEATING_DEGREE_DAYS[climate_zone]
            * STANDARD_HOME_KWH_HEATING_DEMAND_PER_HEATING_DEGREE_DAY
            * LIVING_AREA_FRACTION
            * THERMAL_ENVELOPE_QUALITY[self.insulation_quality]
            * heating_frequency_factor(HEATING_DAYS_PER_WEEK[self.heating_during_day])
        )
        fuel_usage = {
            "Piped gas heater": {
                "natural_gas_kwh": heating_energy_service_demand
                / GAS_SPACE_HEATING_EFFICIENCY,
                "natural_gas_connection_days": DAYS_IN_YEAR,
            },
            "Bottled gas heater": {
                "lpg_kwh": heating_energy_service_demand / LPG_SPACE_HEATING_EFFICIENCY,
                "lpg_tanks_rental_days": DAYS_IN_YEAR,
            },
            "Heat pump": {
                "electricity_kwh": ElectricityUsageTimeseries(
                    fixed_time_uncontrolled_kwh=heating_energy_service_demand
                    / HEAT_PUMP_COP_BY_CLIMATE_ZONE[climate_zone]
                    * space_heating_profile(
                        postcode=your_home.postcode,
                        heating_during_day=self.heating_during_day,
                        setpoint=21.0,
                    )
                ),
            },
            "Electric heater": {
                "electricity_kwh": ElectricityUsageTimeseries(
                    fixed_time_uncontrolled_kwh=heating_energy_service_demand
                    / ELECTRIC_HEATER_SPACE_HEATING_EFFICIENCY
                    * space_heating_profile(
                        postcode=your_home.postcode,
                        heating_during_day=self.heating_during_day,
                        setpoint=21.0,
                    )
                ),
            },
            "Wood burner": {
                "wood_kwh": heating_energy_service_demand
                / LOG_BURNER_SPACE_HEATING_EFFICIENCY,
            },
        }
        fuel_usage[main_heating_source]["elx_connection_days"] = DAYS_IN_YEAR
        return HeatingYearlyFuelUsageProfile(**fuel_usage[main_heating_source])
