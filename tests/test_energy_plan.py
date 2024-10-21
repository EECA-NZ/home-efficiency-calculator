"""
Test the energy plan service
"""

from app.services.get_energy_plans import (
    edb_zone_to_electricity_plan,
    postcode_to_edb_zone,
    postcode_to_electricity_plan,
    postcode_to_energy_plan,
)


def test_postcode_to_edb_zone():
    """
    Test the get_default_household_energy_profile function.
    """
    edb_zone = postcode_to_edb_zone("6012")
    assert edb_zone == "Wellington Electricity"


def test_edb_zone_to_electricity_plan():
    """
    Test the edb_zone_to_electricity_plan function.
    """
    plan = edb_zone_to_electricity_plan("Wellington Electricity")
    assert plan.name in ("37887", "Default Electricity Plan")
    assert plan.daily_charge in (2.0043, 2.0)
    assert plan.nzd_per_kwh in (
        {"All inclusive": 0.16054166666666667},
        {"Day": 0.242, "Night": 0.18},
    )


def test_postcode_to_electricity_plan():
    """
    Test the postcode_to_electricity_plan function.
    """
    plan = postcode_to_electricity_plan("6012")
    assert plan.name in ("37887", "Default Electricity Plan")
    assert plan.daily_charge in (2.0043, 2.0)
    assert plan.nzd_per_kwh in (
        {"All inclusive": 0.16054166666666667},
        {"Day": 0.242, "Night": 0.18},
    )


def test_postcode_to_energy_plan():
    """
    Test the postcode_to_energy_plan function.
    """
    plan = postcode_to_energy_plan("6012")
    assert plan.name in ("Plan for 6012", "Default Electricity Plan")
    assert plan.electricity_plan.name in ("37887", "Default Electricity Plan")
    assert plan.electricity_plan.daily_charge in (2.0043, 2.0)
    assert plan.electricity_plan.nzd_per_kwh in (
        {"All inclusive": 0.16054166666666667},
        {"Day": 0.242, "Night": 0.18},
    )
    assert plan.natural_gas_plan.name == "Default Natural Gas Plan"
    assert plan.natural_gas_plan.per_natural_gas_kwh == 0.11
    assert plan.natural_gas_plan.daily_charge == 1.6
    assert plan.lpg_plan.name == "Default LPG Plan"
    assert plan.lpg_plan.per_lpg_kwh == 0.244
    assert plan.lpg_plan.daily_charge == 0.37782340862423
    assert plan.wood_price.name == "Default Wood Price"
    assert plan.wood_price.per_wood_kwh == 0.052
    assert plan.petrol_price.name == "Default Petrol Price"
    assert plan.petrol_price.per_petrol_litre == 2.78
    assert plan.diesel_price.name == "Default Diesel Price"
    assert plan.diesel_price.per_diesel_litre == 2.16
