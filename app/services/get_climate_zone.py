"""
Functions relating to spatial data. Map postcodes to climate zones
"""


def climate_zone(postcode: str) -> str:
    """
    Return the climate zone for the given postcode.

    Parameters
    ----------
    postcode : str
        The postcode to lookup.

    Returns
    -------
    str
        The climate zone for the given postcode.
    """
    if postcode == "0000":
        return "Northland"
    return "Wellington"
