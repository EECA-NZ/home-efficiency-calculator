"""
Module for generic helper functions.
"""

from app.models.user_answers import SolarAnswers


def get_solar_answers(answers) -> SolarAnswers:
    """
    Retrieve the SolarAnswers instance from the given answers object.

    If the answers object contains a non-None 'solar'
    attribute, that instance is returned.
    Otherwise, a default SolarAnswers instance with
    hasSolar=False is returned.

    Parameters
    ----------
    answers : Any
        An object that is expected to have a 'solar' attribute.

    Returns
    -------
    SolarAnswers
        The retrieved or default SolarAnswers instance.
    """
    # Perform a local import to avoid circular dependencies.

    if hasattr(answers, "solar") and answers.solar is not None:
        return answers.solar
    return SolarAnswers(hasSolar=False)
