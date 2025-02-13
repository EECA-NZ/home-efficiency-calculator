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
        self, your_home, use_alternative: bool = False
    ) -> CooktopYearlyFuelUsageProfile:
        """
        Return the yearly fuel usage profile for cooking.

        Parameters
        ----------
        your_home : YourHomeAnswers
            Answers to questions about the user's home.

        Returns
        -------
        CooktopYearlyFuelUsageProfile
            The yearly fuel usage profile for cooking.
        """
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
            factor.pop("standard_household_kwh")
            * (1 + your_home.people_in_house)
            / (1 + AVERAGE_HOUSEHOLD_SIZE)
        )
        factor["day_kwh"] = (
            ElectricityUsage(uncontrolled=total_kwh)
            if "Electric" in cooktop_type
            else ElectricityUsage(uncontrolled=0)
        )
        factor["natural_gas_kwh"] = total_kwh if cooktop_type == "Piped gas" else 0
        factor["lpg_kwh"] = total_kwh if cooktop_type == "Bottled gas" else 0

        return CooktopYearlyFuelUsageProfile(**factor)
