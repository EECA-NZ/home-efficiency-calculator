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
from ...services.usage_profile_helpers import flat_day_night_profiles
from ..usage_profiles import ElectricityUsageTimeseries, HotWaterYearlyFuelUsageProfile


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

    def hot_water_hourly_usage_profile(
        self,
    ):
        """
        Create a default electricity usage profile for hot water heating.
        The resulting array is normalized so that its sum is 1.

        Returns
        -------
        np.ndarray
            A 1D array of shape (8760,) where each element is 1/8760.
        Placeholder for a more realistic profile.
        """
        # anytime_kwh can be shifted to daytime for solar self-consumption
        # or to nighttime for cheaper electricity rates
        day_profile, _ = flat_day_night_profiles()
        return day_profile

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
                hot_water_heating_source, your_home.people_in_house, climate_zone
            )
        )
        efficiency_factor = hot_water_heating_efficiency(
            hot_water_heating_source, climate_zone
        )
        total_kwh = heat_demand_kwh_per_year / efficiency_factor

        # Following breakdown is used if the hot water heating
        # source is electric (hot water cylinder or heat pump)
        anytime_kwh = total_kwh * HOT_WATER_FLEXIBLE_KWH_FRACTION
        fixed_kwh = total_kwh - anytime_kwh

        electricity_kwh = ElectricityUsageTimeseries(
            fixed_time_controllable_kwh=fixed_kwh
            * self.hot_water_hourly_usage_profile(),
            shift_able_controllable_kwh=anytime_kwh
            * self.hot_water_hourly_usage_profile(),
        )

        fuel_usage = {
            "Electric hot water cylinder": {
                "elx_connection_days": DAYS_IN_YEAR,
                "electricity_kwh": electricity_kwh,
            },
            "Hot water heat pump": {
                "elx_connection_days": DAYS_IN_YEAR,
                "electricity_kwh": electricity_kwh,
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
