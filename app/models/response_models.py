"""
Module for endpoint response objects
"""

from typing import Optional

from pydantic import BaseModel


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