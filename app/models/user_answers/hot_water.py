"""
Class for storing user answers on hot water heating.
"""

from typing import Literal, Optional

from pydantic import BaseModel

from ...constants import (
    DAYS_IN_YEAR,
    HOT_WATER_FLEXIBLE_KWH_FRACTION,
    HOT_WATER_POWER_INPUT_KW,
)
from ...models.hourly_profiles.hot_water import (
    solar_friendly_hot_water_electricity_usage_timeseries,
)
from ...services.postcode_lookups.get_climate_zone import climate_zone
from ...services.usage_calculation.hot_water_helpers import (
    hot_water_heating_efficiency,
    other_water_kwh_per_year,
    shower_kwh_per_year,
    standing_loss_kwh_per_year,
)
from ..usage_profiles import ElectricityUsage, YearlyFuelUsageProfile

ELECTRIC_SYSTEMS = [
    "Electric hot water cylinder",
    "Hot water heat pump",
]


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
        self, your_home, solar_aware, use_alternative: bool = False
    ) -> YearlyFuelUsageProfile:
        """
        Return the yearly fuel usage profile for hot water heating.

        This method calculates how much energy is required for hot water based on
        user inputs (hot water usage level, heater source, etc.). If solar_aware is
        True, a usage profile is estimated based on the user inputs that also aligns
        with solar generation patterns. This 'solar-friendly' profile can be used to
        estimate the opportunity for solar electricity self-consumption.

        Parameters
        ----------
        your_home : YourHomeAnswers
            Answers to questions about the user's home (e.g., postcode).
        solar_aware : bool
            If True, generate a timeseries that attempts to align hot water heating
            with solar availability. If False, a simpler aggregated profile
            is returned (no 8760 data), reducing computational overhead.
        use_alternative : bool, optional
            If True, use the alternative hot water heating source provided by the
            user, rather than their current source.

        Returns
        -------
        YearlyFuelUsageProfile
            The yearly fuel usage profile for hot water heating. If electric, a year's
            hourly usage profile (8760 hours) is provided if solar_aware is True.
        """
        hot_water_heating_source = (
            self.alternative_hot_water_heating_source
            if use_alternative
            else self.hot_water_heating_source
        )
        cz = climate_zone(your_home.postcode)

        # 1) How much hot water energy the household needs, before heater efficiency
        energy_service_demand_kwh_per_year = shower_kwh_per_year(
            self.hot_water_usage, cz, your_home.people_in_house
        ) + other_water_kwh_per_year(cz, your_home.people_in_house)

        # 2) Add standing losses
        heat_demand_kwh_per_year = (
            energy_service_demand_kwh_per_year
            + standing_loss_kwh_per_year(
                hot_water_heating_source, your_home.people_in_house, cz
            )
        )

        # 3) Factor in heater efficiency (or COP for heat pumps)
        efficiency_factor = hot_water_heating_efficiency(hot_water_heating_source, cz)
        total_kwh = heat_demand_kwh_per_year / efficiency_factor

        # 4) Return early for each source type
        if hot_water_heating_source in ELECTRIC_SYSTEMS:
            synthetic_hourly_profile = (
                solar_friendly_hot_water_electricity_usage_timeseries(
                    your_home.postcode,
                    heat_demand_kwh_per_year,
                    HOT_WATER_POWER_INPUT_KW,
                    hot_water_heating_source,
                )
                if solar_aware
                else None
            )
            anytime_kwh = total_kwh * HOT_WATER_FLEXIBLE_KWH_FRACTION
            fixed_kwh = total_kwh - anytime_kwh
            electricity_kwh = ElectricityUsage(
                fixed_day_kwh=fixed_kwh,
                fixed_ngt_kwh=0.0,  # Night usage is flexible
                fixed_profile=synthetic_hourly_profile,
                shift_abl_kwh=anytime_kwh,
                shift_profile=synthetic_hourly_profile,
            )
            return YearlyFuelUsageProfile(
                elx_connection_days=DAYS_IN_YEAR,
                electricity_kwh=electricity_kwh,
            )

        if hot_water_heating_source in [
            "Piped gas hot water cylinder",
            "Piped gas instantaneous",
        ]:
            return YearlyFuelUsageProfile(
                natural_gas_connection_days=DAYS_IN_YEAR,
                natural_gas_kwh=total_kwh,
            )

        if hot_water_heating_source in ["Bottled gas instantaneous"]:
            return YearlyFuelUsageProfile(
                lpg_tanks_rental_days=DAYS_IN_YEAR,
                lpg_kwh=total_kwh,
            )

        raise ValueError(
            f"Unsupported hot water heating source: {hot_water_heating_source}"
        )
