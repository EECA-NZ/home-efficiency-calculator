"""
Class for storing user answers on hot water heating.
"""

from typing import Literal, Optional

from pydantic import BaseModel

from ...constants import DAYS_IN_YEAR, HOT_WATER_FLEXIBLE_KWH_FRACTION
from ...services import get_climate_zone
from ...services.helpers import (
    hot_water_heating_efficiency,
    other_water_kwh_per_year,
    shower_kwh_per_year,
    standing_loss_kwh_per_year,
)
from ..usage_profiles import HotWaterYearlyFuelUsageProfile


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

    def energy_usage_pattern(
        self, your_home, use_alternative: bool = False
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
        climate_zone = get_climate_zone.climate_zone(your_home.postcode)
        energy_service_demand_kwh_per_year = shower_kwh_per_year(
            self.hot_water_usage, climate_zone, your_home.people_in_house
        ) + other_water_kwh_per_year(climate_zone, your_home.people_in_house)
        heat_demand_kwh_per_year = (
            energy_service_demand_kwh_per_year
            + standing_loss_kwh_per_year(
                hot_water_heating_source, your_home.people_in_house
            )
        )
        efficiency_factor = hot_water_heating_efficiency(
            hot_water_heating_source, climate_zone
        )
        total_kwh = heat_demand_kwh_per_year / efficiency_factor

        # Following breakdown is used if the hot water heating
        # source is electric (hot water cylinder or heat pump)
        flexible_kwh = total_kwh * HOT_WATER_FLEXIBLE_KWH_FRACTION
        inflexible_day_kwh = total_kwh - flexible_kwh

        fuel_usage = {
            "Electric hot water cylinder": {
                "elx_connection_days": DAYS_IN_YEAR,
                "flexible_kwh": flexible_kwh,
                "inflexible_day_kwh": inflexible_day_kwh,
            },
            "Hot water heat pump": {
                "elx_connection_days": DAYS_IN_YEAR,
                "flexible_kwh": flexible_kwh,
                "inflexible_day_kwh": inflexible_day_kwh,
            },
            "Piped gas hot water cylinder": {
                "natural_gas_connection_days": DAYS_IN_YEAR,
                "natural_gas_kwh": total_kwh,
            },
            "Piped gas instantaneous": {
                "natural_gas_connection_days": DAYS_IN_YEAR,
                "natural_gas_kwh": total_kwh,
            },
            "Bottled gas instantaneous": {
                "lpg_tanks_rental_days": DAYS_IN_YEAR,
                "lpg_kwh": total_kwh,
            },
        }
        return HotWaterYearlyFuelUsageProfile(**fuel_usage[hot_water_heating_source])
