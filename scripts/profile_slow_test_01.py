"""
Profile the test_api_solar_calculation function from
the tests.api.test_solar_savings_endpoint module.
"""

import cProfile
import io
import pstats

# Import the test function and the profiles from your existing test file
from tests.api.test_solar_savings_endpoint import (
    profile0,
    profile1,
    profile2,
    profile3,
    test_api_solar_calculation,
)


def run_profile():
    """
    Run the 'test_api_solar_calculation' function with each profile
    under cProfile, then show which calls take the most time.
    """

    # If your test depends on an environment var, ensure it's set:
    # e.g. if you want to force local solar data usage:
    #   os.environ["LOCAL_SOLAR_DATA"] = "True"

    # Gather all the param profiles
    test_params = [profile0, profile1, profile2, profile3]

    profiler = cProfile.Profile()
    profiler.enable()

    # Loop over all the param profiles
    for param in test_params:
        # This calls your test function just like Pytest would for each param
        test_api_solar_calculation(param)

    profiler.disable()

    # Output the profiler stats
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)

    # Sort by "time" (internal time) or "cumulative" (cum time)
    stats.sort_stats(pstats.SortKey.TIME)
    # Show the top 30 lines
    stats.print_stats(30)

    print(stream.getvalue())


if __name__ == "__main__":
    run_profile()
