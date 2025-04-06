"""
Class for storing user answers on household driving.
"""

# pylint: disable=too-many-locals

from typing import Literal, Optional

from pydantic import BaseModel

from ...constants import (
    ASSUMED_DISTANCES_PER_WEEK,
    BATTERY_ECONOMY_KWH_PER_100KM,
    CALENDAR_YEAR,
    DAYS_IN_YEAR,
    DEFAULT_CHARGER_KW,
    EV_PUBLIC_CHARGING_FRACTION,
    FUEL_CONSUMPTION_LITRES_PER_100KM,
)
from ...services.profile_helpers import flat_day_night_profiles
from ...services.profile_helpers.driving import solar_friendly_ev_charging_profile
from ..usage_profiles import DrivingYearlyFuelUsageProfile, ElectricityUsage


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

    def ev_charging_profile(
        self,
    ):
        """
        Create a default electricity usage profile for electric vehicle charging.
        The resulting array is normalized so that its sum is 1.

        Returns
        -------
        np.ndarray
            A 1D array of shape (8760,) where each element is 1/8760.
        Placeholder for a more realistic profile.
        """
        _, night_profile = flat_day_night_profiles()
        return night_profile

    # pylint: disable=unused-argument
    def energy_usage_pattern(
        self, your_home, solar_aware: bool, use_alternative: bool = False
    ) -> DrivingYearlyFuelUsageProfile:
        """
        Return the yearly fuel usage profile for driving.

        This method computes the fuel (petrol/diesel) or electricity usage needed
        for the user's driving patterns, including partial electric usage if it's
        a plug-in hybrid. If solar_aware is True, a usage profile is estimated
        for domestic electric vehicle charging that is consistent with the usage
        and also shaped to be 'solar-friendly' (align with solar production).

        Parameters
        ----------
        your_home : YourHomeAnswers
            Answers to questions about the user's home (e.g., location).
        solar_aware : bool
            If True, create a timeseries for EV charging that tries to maximize
            daytime charging to benefit from solar. If False, a simpler aggregated
            profile is returned (no 8760 data), reducing computational overhead.
        use_alternative : bool, optional
            If True, use the alternative vehicle type instead of the current type.

        Returns
        -------
        DrivingYearlyFuelUsageProfile
            The yearly fuel usage profile for driving, including both
            liquid fuel and/or electricity consumption. If electric, a year's
            hourly usage profile (8760 hours) is provided if solar_aware is True.
        """

        _ = solar_aware
        vehicle_type = (
            self.alternative_vehicle_type if use_alternative else self.vehicle_type
        )
        daily_distance_km = ASSUMED_DISTANCES_PER_WEEK[self.km_per_week] / 7
        yearly_distance_thousand_km = daily_distance_km * DAYS_IN_YEAR / 1000

        # Figure out whether we have a petrol or diesel vehicle
        # (including hybrid/plug-in hybrid),
        # so that we can compute yearly fuel usage if needed.
        if vehicle_type in ["Petrol", "Hybrid", "Diesel"]:
            if vehicle_type in ["Petrol", "Hybrid"]:
                liquid_fuel = "Petrol"
            else:
                liquid_fuel = "Diesel"

            # Calculate the litres of liquid fuel
            litres_per_100km = FUEL_CONSUMPTION_LITRES_PER_100KM[vehicle_type][
                self.vehicle_size
            ]
            yearly_fuel_litres = (yearly_distance_thousand_km * 10) * litres_per_100km

            # No battery usage
            yearly_total_kwh = 0
            public_charging_kwh = 0
            home_charging_timeseries = ElectricityUsage()

            # Finally, return the DrivingYearlyFuelUsageProfile.
            return DrivingYearlyFuelUsageProfile(
                elx_connection_days=DAYS_IN_YEAR,
                electricity_kwh=home_charging_timeseries,
                petrol_litres=yearly_fuel_litres if liquid_fuel == "Petrol" else 0,
                diesel_litres=yearly_fuel_litres if liquid_fuel == "Diesel" else 0,
                public_ev_charger_kwh=public_charging_kwh,
                thousand_km=yearly_distance_thousand_km,
            )

        # Calculate the battery usage if needed (i.e. plug-in hybrid or pure electric)
        if vehicle_type in ["Plug-in hybrid", "Electric"]:
            kwh_per_100km = BATTERY_ECONOMY_KWH_PER_100KM[vehicle_type][
                self.vehicle_size
            ]
            yearly_total_kwh = (yearly_distance_thousand_km * 10) * kwh_per_100km
            public_charging_kwh = yearly_total_kwh * EV_PUBLIC_CHARGING_FRACTION
            home_charging_kwh = yearly_total_kwh - public_charging_kwh

            charging_profile = (
                solar_friendly_ev_charging_profile(
                    home_charging_kwh, charger_kw=DEFAULT_CHARGER_KW, year=CALENDAR_YEAR
                )
                if solar_aware
                else None
            )

            home_charging_timeseries = ElectricityUsage(
                fixed_day_kwh=0.0,
                fixed_ngt_kwh=0.0,
                fixed_profile=None,
                shift_abl_kwh=home_charging_kwh,
                shift_profile=charging_profile,
            )

            # If it's plug-in hybrid, we also have fuel usage
            if vehicle_type == "Plug-in hybrid":
                liquid_fuel = "Petrol"
                litres_per_100km = FUEL_CONSUMPTION_LITRES_PER_100KM[vehicle_type][
                    self.vehicle_size
                ]
                yearly_fuel_litres = (
                    yearly_distance_thousand_km * 10
                ) * litres_per_100km
                return DrivingYearlyFuelUsageProfile(
                    elx_connection_days=DAYS_IN_YEAR,
                    electricity_kwh=home_charging_timeseries,
                    petrol_litres=yearly_fuel_litres,
                    diesel_litres=0,
                    public_ev_charger_kwh=public_charging_kwh,
                    thousand_km=yearly_distance_thousand_km,
                )

            # Otherwise it's pure electric
            return DrivingYearlyFuelUsageProfile(
                elx_connection_days=DAYS_IN_YEAR,
                electricity_kwh=home_charging_timeseries,
                petrol_litres=0,
                diesel_litres=0,
                public_ev_charger_kwh=public_charging_kwh,
                thousand_km=yearly_distance_thousand_km,
            )

        raise ValueError(f"Unknown vehicle type: {vehicle_type}")
