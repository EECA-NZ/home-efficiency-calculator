"""
Module for driving helper functions.
"""


def get_vehicle_type(answers, use_alternatives=False) -> str:
    """
    Retrieve the vehicle type from the answers.

    Args:
    - answers: The user's answers.
    - use_alternatives: Whether to use the alternative vehicle type.

    Returns:
    - The vehicle type.
    """

    if hasattr(answers, "driving") and answers.driving is not None:
        if use_alternatives:
            if answers.driving.alternative_vehicle_type is not None:
                return answers.driving.alternative_vehicle_type
    return "None"
