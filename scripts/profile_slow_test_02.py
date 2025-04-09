"""
Profile the test_hot_water_savings_specific_alternative function
"""

import cProfile
import io
import pstats

# 1) Import your specific test function
from tests.api.test_component_savings_endpoints import (
    test_hot_water_savings_specific_alternative_2,
)


def run_profile():
    """
    Profile the function test_hot_water_savings_specific_alternative
    and display the top time-consuming calls.
    """
    profiler = cProfile.Profile()
    profiler.enable()

    # 2) Call the test function directly, timing it each time
    print("Running test_hot_water_savings_specific_alternative... A")
    test_hot_water_savings_specific_alternative_2()
    print("Running test_hot_water_savings_specific_alternative... B")
    test_hot_water_savings_specific_alternative_2()
    print("Running test_hot_water_savings_specific_alternative... C")
    test_hot_water_savings_specific_alternative_2()
    print("Running test_hot_water_savings_specific_alternative... D")
    test_hot_water_savings_specific_alternative_2()
    print("Running test_hot_water_savings_specific_alternative... E")
    test_hot_water_savings_specific_alternative_2()

    profiler.disable()

    # 3) Sort and display stats
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats(pstats.SortKey.TIME)  # or .CUMULATIVE
    stats.print_stats(30)  # show the top 30 lines

    print(stream.getvalue())


if __name__ == "__main__":
    run_profile()
