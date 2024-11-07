"""
Classes for storing user answers to the questions provided by online users.
"""

from typing import Optional

from pydantic import BaseModel

from .cooktop import CooktopAnswers
from .your_home import YourHomeAnswers


class HouseholdAnswers(BaseModel):
    """
    Answers to all questions about the user's household energy usage.

    This class is used to store all the answers provided by the user.

    The only required field is `your_home`, which contains the answers to questions
    about the number of occupants and the approximate location of the user's home.
    """

    your_home: YourHomeAnswers
    cooktop: Optional[CooktopAnswers] = None
