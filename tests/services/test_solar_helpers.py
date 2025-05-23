"""
Unit tests for solar_helpers.py
"""

import numpy as np

from app.services.solar_calculator.solar_helpers import compute_solar_offset

# pylint: disable=too-few-public-methods


class MockUsageProfile:
    """
    Mock usage profile for testing solar offset calculation.
    This class simulates the structure of a usage profile
    containing solar generation and electricity usage data.
    It includes methods to initialize the solar generation
    and electricity usage data, and to calculate the total
    generation and usage.
    """

    def __init__(self, solar, fixed, shift):
        """
        Initialize the mock usage profile with solar generation
        and electricity usage data.
        """

        class Solar:
            """
            Simulates solar generation data.
            """

            def __init__(self, ts):
                """
                Initialize solar generation data.
                """
                self.timeseries = ts
                self.total = float(np.sum(ts))

        class Electricity:
            """
            Simulates electricity usage data.
            """

            def __init__(self, fixed_ts, shift_ts):
                """
                Initialize electricity usage data.
                """
                self.total_fixed_time_usage = fixed_ts
                self.total_shift_able_usage = shift_ts

        self.solar_generation_kwh = Solar(solar)
        self.electricity_kwh = Electricity(fixed, shift)


def test_compute_solar_offset_basic():
    """
    Tests solar offset calculation for a mocked profile:
    - 10 kWh solar
    - 6 kWh fixed usage
    - 5 kWh shiftable usage
    Expected: 6 fixed, 4 shift, 0 export
    """
    solar = np.array([10.0])
    fixed = np.array([6.0])
    shift = np.array([5.0])
    usage_profile = MockUsageProfile(solar, fixed, shift)

    shift_sc, fixed_sc, export = compute_solar_offset(usage_profile)

    assert fixed_sc == 6.0
    assert shift_sc == 4.0
    assert export == 0.0
