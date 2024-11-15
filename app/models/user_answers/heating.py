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
from ..usage_profiles import HeatingYearlyFuelUsageProfile


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
                "inflexible_day_kwh": heating_energy_service_demand
                / HEAT_PUMP_COP_BY_CLIMATE_ZONE[climate_zone],
            },
            "Electric heater": {
                "inflexible_day_kwh": heating_energy_service_demand
                / ELECTRIC_HEATER_SPACE_HEATING_EFFICIENCY,
            },
            "Wood burner": {
                "wood_kwh": heating_energy_service_demand
                / LOG_BURNER_SPACE_HEATING_EFFICIENCY,
            },
        }
        return HeatingYearlyFuelUsageProfile(
            elx_connection_days=DAYS_IN_YEAR,
            inflexible_day_kwh=fuel_usage[main_heating_source].get(
                "inflexible_day_kwh", 0
            ),
            flexible_kwh=0,
            natural_gas_connection_days=fuel_usage[main_heating_source].get(
                "natural_gas_connection_days", 0
            ),
            natural_gas_kwh=fuel_usage[main_heating_source].get("natural_gas_kwh", 0),
            lpg_tanks_rental_days=fuel_usage[main_heating_source].get(
                "lpg_tanks_rental_days", 0
            ),
            lpg_kwh=fuel_usage[main_heating_source].get("lpg_kwh", 0),
            wood_kwh=fuel_usage[main_heating_source].get("wood_kwh", 0),
            petrol_litres=0,
            diesel_litres=0,
            public_ev_charger_kwh=0,
            thousand_km_petrol=0,
            thousand_km_diesel=0,
            thousand_km_hybrid=0,
            thousand_km_plug_in_hybrid=0,
            thousand_km_electric=0,
        )
