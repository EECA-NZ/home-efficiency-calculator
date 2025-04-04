"""
Class for storing user answers on stovetop cooking.
"""

from typing import Literal, Optional

from pydantic import BaseModel

from ...constants import (
    AVERAGE_HOUSEHOLD_SIZE,
    DAYS_IN_YEAR,
    STANDARD_HOUSEHOLD_COOKTOP_ENERGY_USAGE_KWH,
)
from ...services.usage_profile_helpers.cooktop import cooktop_hourly_usage_profile
from ..usage_profiles import CooktopYearlyFuelUsageProfile, ElectricityUsage


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

    def energy_usage_pattern(
        self, your_home, solar_aware: bool, use_alternative: bool = False
    ) -> CooktopYearlyFuelUsageProfile:
        """
        Return the yearly fuel usage profile for cooking.

        This method estimates how much energy is needed for stovetop cooking
        (electric or gas) and creates the appropriate usage profile. The
        calculation provides an hourly usage profile if solar_aware is True. For
        cooktop usage, any electricity demand is assumed to be at time-of-use.

        Parameters
        ----------
        your_home : YourHomeAnswers
            Answers to questions about the user's home (e.g., household size).
        solar_aware : bool
            If True, produce a detailed usage profile (allocating daytime
            load by hour of the year). If False, a simpler aggregated profile
            is returned (no 8760 data), reducing computational overhead.
        use_alternative : bool, optional
            If True, use the alternative cooktop type provided by the user,
            rather than the user's current cooktop type.

        Returns
        -------
        CooktopYearlyFuelUsageProfile
            The yearly fuel usage profile for cooking, including any necessary
            electricity, natural gas, or LPG consumption. If electric, a year's
            hourly usage profile (8760 hours) is provided if solar_aware is True.
        """

        _ = solar_aware
        usage_factors = {
            "Electric induction": {
                "standard_household_kwh": STANDARD_HOUSEHOLD_COOKTOP_ENERGY_USAGE_KWH[
                    "Electric induction"
                ],
                "elx_connection_days": DAYS_IN_YEAR,
            },
            "Electric (coil or ceramic)": {
                "standard_household_kwh": STANDARD_HOUSEHOLD_COOKTOP_ENERGY_USAGE_KWH[
                    "Electric (coil or ceramic)"
                ],
                "elx_connection_days": DAYS_IN_YEAR,
            },
            "Piped gas": {
                "standard_household_kwh": STANDARD_HOUSEHOLD_COOKTOP_ENERGY_USAGE_KWH[
                    "Piped gas"
                ],
                "natural_gas_connection_days": DAYS_IN_YEAR,
            },
            "Bottled gas": {
                "standard_household_kwh": STANDARD_HOUSEHOLD_COOKTOP_ENERGY_USAGE_KWH[
                    "Bottled gas"
                ],
                "lpg_tanks_rental_days": DAYS_IN_YEAR,
            },
        }
        cooktop_type = self.alternative_cooktop if use_alternative else self.cooktop
        if cooktop_type not in usage_factors:
            raise ValueError(f"Unknown cooktop type: {cooktop_type}")

        # Modeled energy use in kWh for each cooktop type. This is a
        # linearized energy use model that preserves the average household
        # energy use for cooking, by the linearity of expectation.
        # (See 'Cooking' sheet of supporting workbook.)
        factor = usage_factors[cooktop_type]
        total_kwh = (
            factor["standard_household_kwh"]
            * (1 + your_home.people_in_house)
            / (1 + AVERAGE_HOUSEHOLD_SIZE)
        )

        if cooktop_type in ["Electric induction", "Electric (coil or ceramic)"]:
            electricity_kwh = ElectricityUsage(
                fixed_day_kwh=total_kwh,
                fixed_ngt_kwh=0.0,
                fixed_profile=(cooktop_hourly_usage_profile() if solar_aware else None),
                shift_abl_kwh=0.0,
                shift_profile=None,
            )
            return CooktopYearlyFuelUsageProfile(
                elx_connection_days=factor["elx_connection_days"],
                electricity_kwh=electricity_kwh,
                natural_gas_kwh=0,
                lpg_kwh=0,
            )

        if cooktop_type == "Piped gas":
            return CooktopYearlyFuelUsageProfile(
                natural_gas_connection_days=factor["natural_gas_connection_days"],
                electricity_kwh=ElectricityUsage(),
                natural_gas_kwh=total_kwh,
                lpg_kwh=0,
            )

        if cooktop_type == "Bottled gas":
            return CooktopYearlyFuelUsageProfile(
                lpg_tanks_rental_days=factor["lpg_tanks_rental_days"],
                electricity_kwh=ElectricityUsage(),
                natural_gas_kwh=0,
                lpg_kwh=total_kwh,
            )

        raise ValueError(f"Unknown cooktop type: {cooktop_type}")
