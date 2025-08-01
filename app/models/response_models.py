"""
Module for endpoint response objects
"""

from typing import Optional

from pydantic import BaseModel

from .usage_profiles import YearlyFuelUsageReport


class UserGeography(BaseModel):
    """
    Model for returning derived facts about the user's location.
    """

    edb_region: str
    climate_zone: str


class SavingsData(BaseModel):
    """
    Model for the savings and emissions data for a particular household component.
    """

    current: Optional[float] = None
    alternative: Optional[float] = None
    absolute_reduction: Optional[float] = None
    percentage_reduction: Optional[float] = None


class SavingsResponse(BaseModel):
    """
    Response model for the component savings endpoint.
    """

    variable_cost_nzd: SavingsData
    emissions_kg_co2e: SavingsData


class ComponentSavingsResponse(BaseModel):
    """
    Response model for the component options endpoint.
    """

    alternatives: dict[str, SavingsResponse]
    user_geography: UserGeography
    current_fuel_use: YearlyFuelUsageReport
    alternative_fuel_use: Optional[YearlyFuelUsageReport]


class SolarSavingsResponse(BaseModel):
    """
    Response model for the solar savings endpoint.
    """

    annual_kwh_generated: float
    annual_kg_co2e_saving: float
    annual_earnings_solar_export: float
    annual_savings_solar_self_consumption: float


class CheckboxData(BaseModel):
    """
    Model for configuring the checkbox to configure
    gas connection fixed cost behaviour.
    """

    checkbox_visible: Optional[bool] = None
    checkbox_text: Optional[str] = None
    checkbox_greyed_out: Optional[bool] = None
    checkbox_default_on: Optional[bool] = None


class FixedCostsResponse(BaseModel):
    """
    Response model for the fixed costs endpoint.
    """

    gas_connection_savings: dict[str, SavingsResponse]
