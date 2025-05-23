# pylint: disable=no-self-argument
"""
Class for storing user answers on geography and household size.
"""

from pydantic import BaseModel, conint, constr, field_validator, model_validator

from app.constants import EXCLUDE_POSTCODES
from app.services.postcode_lookups.get_climate_zone import postcode_dict

known_postcodes = set(postcode_dict.keys())
exclude_postcodes = [
    postcode for sublist in EXCLUDE_POSTCODES.values() for postcode in sublist
]


class YourHomeAnswers(BaseModel):
    """
    Answers to questions about the user's home.
    """

    people_in_house: conint(ge=1, le=6)
    postcode: constr(strip_whitespace=True, pattern=r"^\d{4}$")

    @field_validator("postcode", mode="before")
    def pad_postcode(cls, value):
        """
        Accept a shorter digit string (1-4 digits)
        and pad with leading zeros if necessary,
        so that the final value is always 4 digits.
        """
        value = value.strip()
        if not value.isdigit():
            raise ValueError("Postcode must be numeric.")
        # Pad with leading zeros if the length is less than 4
        return value.zfill(4)

    @model_validator(mode="after")
    def check_postcode(cls, model):
        """
        Validate that the postcode is recognized (a key from the
        climate zone lookup) and accepted (not in the exclude list).

        Raises:
            ValueError: If the postcode is not in the known list or is excluded.
        """
        if model.postcode in exclude_postcodes:
            raise ValueError(
                f"Postcode '{model.postcode}' is not covered by this tool."
            )
        if model.postcode not in known_postcodes:
            raise ValueError(
                f"Invalid postcode '{model.postcode}'. Please provide a valid postcode."
            )
        return model
