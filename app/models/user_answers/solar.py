"""
Class for storing user answers on solar generation.
"""

from pydantic import BaseModel

from ...constants import DAYS_IN_YEAR, SOLAR_RESOURCE_KWH_PER_DAY
from ...services import get_climate_zone
from ..usage_profiles import SolarYearlyFuelGenerationProfile


class SolarAnswers(BaseModel):
    """
    Does the house include solar panels?
    """

    hasSolar: bool

    def energy_generation(
        self,
        your_home,
    ) -> SolarYearlyFuelGenerationProfile:
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
            inflexible_day_kwh=-annual_generation_kwh,
            flexible_kwh=0,
            natural_gas_connection_days=0,
            natural_gas_kwh=0,
            lpg_tanks_rental_days=0,
            lpg_kwh=0,
            wood_kwh=0,
            petrol_litres=0,
            diesel_litres=0,
            public_ev_charger_kwh=0,
            thousand_km_petrol=0,
            thousand_km_diesel=0,
            thousand_km_hybrid=0,
            thousand_km_plug_in_hybrid=0,
            thousand_km_electric=0,
        )
