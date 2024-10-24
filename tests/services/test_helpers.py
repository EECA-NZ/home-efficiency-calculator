"""
Tests for the helpers module.
"""

from app.services.configuration import get_default_electricity_plan
from app.services.helpers import add_gst


def test_add_gst():
    """
    Test the add_gst function.
    """
    electricity_plan = get_default_electricity_plan()
    adjusted_electricity_plan = add_gst(electricity_plan)
    assert adjusted_electricity_plan.name == electricity_plan.name
    assert (
        adjusted_electricity_plan.daily_charge == electricity_plan.daily_charge * 1.15
    )
    assert (
        adjusted_electricity_plan.nzd_per_kwh["Day"]
        == electricity_plan.nzd_per_kwh["Day"] * 1.15
    )
    assert (
        adjusted_electricity_plan.nzd_per_kwh["Night"]
        == electricity_plan.nzd_per_kwh["Night"] * 1.15
    )
