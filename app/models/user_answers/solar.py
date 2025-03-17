"""
Class for storing user answers on solar generation.
"""

from typing import Optional

import numpy as np
from pydantic import BaseModel

from ...services import get_climate_zone, get_solar_generation
from ..usage_profiles import SolarGenerationTimeseries, SolarYearlyFuelGenerationProfile


class SolarAnswers(BaseModel):
    """
    Does the house include solar panels?
    """

    has_solar: bool
    alternative_has_solar: Optional[bool] = None

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
        if self.has_solar:
            hourly_solar_generation_kwh = SolarGenerationTimeseries(
                fixed_time_generation_kwh=get_solar_generation.hourly_pmax(
                    my_climate_zone
                )
            )
        else:
            hourly_solar_generation_kwh = SolarGenerationTimeseries(
                fixed_time_generation_kwh=np.zeros(8760)
            )
        return SolarYearlyFuelGenerationProfile(
            solar_generation_kwh=hourly_solar_generation_kwh,
        )
