"""
This module provides an endpoint to retrieve geographic data
(the climate zone and EDB region) based on the reported postcode.
"""

import logging

from fastapi import APIRouter, HTTPException

from ..models.response_models import UserGeography
from ..models.user_answers import YourHomeAnswers
from ..services.postcode_lookups.get_climate_zone import climate_zone
from ..services.postcode_lookups.get_energy_plans import postcode_to_edb_zone

router = APIRouter()

# Configure logger
logger = logging.getLogger(__name__)


@router.post("/user/geography", response_model=UserGeography)
async def get_user_geography(your_home: YourHomeAnswers):
    """
    Retrieve the geographic data for a given user's home based on the postcode.
    """
    try:
        edb_region = postcode_to_edb_zone(your_home.postcode)
        climate_zone_name = climate_zone(your_home.postcode)
        user_geography = UserGeography(
            edb_region=edb_region, climate_zone=climate_zone_name
        )
        return user_geography
    except Exception as e:
        logger.error("Failed to retrieve geography data: %s", e)
        raise HTTPException(
            status_code=500, detail="Failed to process the provided postcode."
        ) from e
