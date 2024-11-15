"""
Class for storing user answers on household driving.
"""

from typing import Literal, Optional

from pydantic import BaseModel

from ...constants import (
    ASSUMED_DISTANCES_PER_WEEK,
    BATTERY_ECONOMY_KWH_PER_100KM,
    DAYS_IN_YEAR,
    EV_PUBLIC_CHARGING_FRACTION,
    FUEL_CONSUMPTION_LITRES_PER_100KM,
)
from ..usage_profiles import DrivingYearlyFuelUsageProfile


class DrivingAnswers(BaseModel):
    """
    Answers to questions about the user's vehicle and driving patterns.
    """

    vehicle_size: Literal["Small", "Medium", "Large"]
    km_per_week: Literal["50 or less", "100", "200", "300", "400 or more"]
    vehicle_type: Literal["Petrol", "Diesel", "Hybrid", "Plug-in hybrid", "Electric"]
    alternative_vehicle_type: Optional[
        Literal["Petrol", "Diesel", "Hybrid", "Plug-in hybrid", "Electric"]
    ] = None

    # pylint: disable=unused-argument
    def energy_usage_pattern(
        self, your_home, use_alternative: bool = False
    ) -> DrivingYearlyFuelUsageProfile:
        """
        Return the yearly fuel usage profile for driving.

        The profile is based on the answers provided by the user.
        """
        vehicle_type = (
            self.alternative_vehicle_type if use_alternative else self.vehicle_type
        )
        daily_distance_km = ASSUMED_DISTANCES_PER_WEEK[self.km_per_week] / 7
        yearly_distance_thousand_km = daily_distance_km * DAYS_IN_YEAR / 1000

        liquid_fuel = None
        if vehicle_type in ["Petrol", "Hybrid", "Plug-in hybrid"]:
            liquid_fuel = "Petrol"
        elif vehicle_type == "Diesel":
            liquid_fuel = "Diesel"
        elif vehicle_type != "Electric":
            raise ValueError(f"Unknown vehicle type: {vehicle_type}")

        if vehicle_type in ["Petrol", "Diesel", "Hybrid", "Plug-in hybrid"]:
            litres_per_100km = FUEL_CONSUMPTION_LITRES_PER_100KM[vehicle_type][
                self.vehicle_size
            ]
            yearly_fuel_litres = (yearly_distance_thousand_km * 10) * litres_per_100km
        else:
            yearly_fuel_litres = 0

        if vehicle_type in ["Plug-in hybrid", "Electric"]:
            kwh_per_100km = BATTERY_ECONOMY_KWH_PER_100KM[vehicle_type][
                self.vehicle_size
            ]
            yearly_battery_kwh = (yearly_distance_thousand_km * 10) * kwh_per_100km
            public_charging_kwh = yearly_battery_kwh * EV_PUBLIC_CHARGING_FRACTION
            home_charging_kwh = yearly_battery_kwh - public_charging_kwh
        else:
            yearly_battery_kwh = 0
            public_charging_kwh = 0
            home_charging_kwh = 0

        return DrivingYearlyFuelUsageProfile(
            elx_connection_days=DAYS_IN_YEAR,
            inflexible_day_kwh=0,
            flexible_kwh=home_charging_kwh,
            natural_gas_connection_days=0,
            natural_gas_kwh=0,
            lpg_tanks_rental_days=0,
            lpg_kwh=0,
            wood_kwh=0,
            petrol_litres=yearly_fuel_litres if liquid_fuel == "Petrol" else 0,
            diesel_litres=yearly_fuel_litres if liquid_fuel == "Diesel" else 0,
            public_ev_charger_kwh=public_charging_kwh,
            thousand_km=yearly_distance_thousand_km,
        )
