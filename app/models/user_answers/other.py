"""
Class for storing user answers to 'other' questions:
Whether to include changes to gas connection fixed costs
"""

from pydantic import BaseModel


class OtherAnswers(BaseModel):
    """
    Should changes to gas connection fixed costs be included in the calculations?
    """

    fixed_cost_changes: bool
