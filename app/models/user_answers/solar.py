"""
Class for storing user answers on solar generation.
"""

import numpy as np
from pydantic import BaseModel

from ...services import get_solar_generation
from ..usage_profiles import SolarGenerationTimeseries, SolarYearlyFuelGenerationProfile


class SolarAnswers(BaseModel):
    """
    Should the calculations include adding solar panels?

    Note that it is assumed that the user does not have solar panels.
    """

    add_solar: bool

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
        if self.add_solar:
            hourly_solar_generation_kwh = SolarGenerationTimeseries(
                fixed_time_generation_kwh=get_solar_generation.hourly_pmax(
                    your_home.postcode
                )
            )
        else:
            hourly_solar_generation_kwh = SolarGenerationTimeseries(
                fixed_time_generation_kwh=np.zeros(8760)
            )
        return SolarYearlyFuelGenerationProfile(
            solar_generation_kwh=hourly_solar_generation_kwh,
        )
