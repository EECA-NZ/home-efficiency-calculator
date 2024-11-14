"""
Default answers for the components of a household energy profile.
"""

from ...models.user_answers import CooktopAnswers, YourHomeAnswers


def get_default_your_home_answers():
    """
    Return a default 'your home' answers object.
    """
    return YourHomeAnswers(people_in_house=3, postcode="0000", disconnect_gas=False)


def get_default_cooktop_answers():
    """
    Return a default 'cooktop' answers object.
    """
    return CooktopAnswers(
        cooktop="Electric (coil or ceramic)",
    )
