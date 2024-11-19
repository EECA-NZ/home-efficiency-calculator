# pylint: disable=no-self-argument
"""
Class for storing user answers on geography, household size and gas disconnection.
"""

from pydantic import BaseModel, conint, constr, model_validator

from app.services.get_climate_zone import postcode_dict

known_postcodes = set(postcode_dict.keys())


class YourHomeAnswers(BaseModel):
    """
    Answers to questions about the user's home.
    """

    people_in_house: conint(ge=1, le=6)
    postcode: constr(strip_whitespace=True, pattern=r"^\d{4}$")
    disconnect_gas: bool

    @model_validator(mode="after")
    def check_postcode(cls, model):
        """
        Validate that the postcode is recognized (a key from the
        climate zone lookup)

        Raises:
            ValueError: If the postcode is not in the known list.
        """
        if f"{model.postcode}" not in known_postcodes:
            raise ValueError(
                f"Invalid postcode '{model.postcode}'. Please provide a valid postcode."
            )
        return model
