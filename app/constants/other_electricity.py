"""
Constants for electricity use for appliances other than those modelled here.

This information is not displayed in the tool at any point, but is used in
the calculation of optimal electricity plans.

The effect of assumptions made here is likely to be small.

Night rate assumed to apply for 8 hours per day. Refrigeration use likely
higher during day due to temperature and frequency of opening door, but some
"other" use likely to be at night (e.g. standby on electronics including
ONT/router) so unders and overs should cancel to some degree.

Note: a 'documentation' excel workbook is to be created, and we
intend to add it into the repository and link to it from this
docstring. Links to supporting literature will be added here.

Refer to the 'Other electricity use' spreadsheet tab for more information.
"""

OTHER_ELX_KWH_PER_DAY = {
    "Refrigeration": {"kWh/day": 2.1},
    "Lighting": {"kWh/day": 0.8},
    "Laundry": {"kWh/day": 0.4},
    "Other": {"kWh/day": 4.3},
}

DAY_NIGHT_FRAC = {
    "Refrigeration": {"Day": 0.67, "Night": 0.33},
    "Lighting": {"Day": 1, "Night": 0},
    "Laundry": {"Day": 1, "Night": 0},
    "Other": {"Day": 1, "Night": 0},
}
