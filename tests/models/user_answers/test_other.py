"""
Tests for the OtherAnswers user-answers model (app/models/user_answers/other.py).
"""

import pytest
from pydantic import ValidationError

from app.models.user_answers.other import OtherAnswers


class TestOtherAnswers:
    """
    Tests for the OtherAnswers Pydantic model validation.
    """

    def test_valid(self):
        """
        OtherAnswers should accept boolean for fixed_cost_changes.
        """
        oa = OtherAnswers(fixed_cost_changes=True)
        assert oa.fixed_cost_changes is True

    def test_missing_field(self):
        """
        Missing fixed_cost_changes field should raise ValidationError.
        """
        with pytest.raises(ValidationError):
            OtherAnswers()

    def test_wrong_type(self):
        """
        Non-boolean input for fixed_cost_changes should be rejected.
        """
        with pytest.raises(ValidationError):
            OtherAnswers(fixed_cost_changes="not a bool")
