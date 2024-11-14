"""
Class for storing user answers on geography, household size and gas disconnection.
"""

from pydantic import BaseModel, conint, constr


class YourHomeAnswers(BaseModel):
    """
    Answers to questions about the user's home.
    """

    people_in_house: conint(ge=1, le=6)
    postcode: constr(strip_whitespace=True, pattern=r"^\d{4}$")
    disconnect_gas: bool
