"""
Tests for the functions defined in app.services.get_energy_plans.py
"""

from app.services.get_energy_plans import get_energy_plan


def test_get_energy_plan():
    """
    Check that the get_energy_plan function returns
    distinct energy plans for postcodes in different parts
    of the country.
    """
    vehicle_type = "Petrol"
    assert (
        get_energy_plan("9013", vehicle_type).other_vehicle_costs.name
        == get_energy_plan("6012", vehicle_type).other_vehicle_costs.name
    )
