"""
Module for generic helper functions.
"""

import app.services.configuration as cfg
from app.models.user_answers import OtherAnswers


def get_other_answers(answers) -> OtherAnswers:
    """
    Retrieve the OtherAnswers instance from the given answers object.

    If the answers object contains a non-None 'other'
    attribute, that instance is returned.

    Otherwise, a default OtherAnswers instance is returned.

    Parameters
    ----------
    answers : Any
        An object that is expected to have a 'other' attribute.

    Returns
    -------
    OtherAnswers
        The retrieved or default OtherAnswers instance.
    """
    if hasattr(answers, "other") and answers.other is not None:
        return answers.other
    return cfg.get_default_other_answers()
