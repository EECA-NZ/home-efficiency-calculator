"""
Test the energy plan service
"""

import unittest

from app.constants import DAYS_IN_YEAR
from app.models.energy_plans import ElectricityPlan
from app.models.usage_profiles import HouseholdYearlyFuelUsageProfile
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
    assert plan.daily_charge in (2.304945, 2.0)
    assert plan.nzd_per_kwh in (
        {"All inclusive": 0.18462291666666666},
        {"Day": 0.242, "Night": 0.18},
    )


def test_postcode_to_electricity_plan():
    """
    Test the postcode_to_electricity_plan function.
    """
    plan = postcode_to_electricity_plan("6012")
    assert plan.name in ("37887", "Default Electricity Plan")
    assert plan.daily_charge in (2.304945, 2.0)
    assert plan.nzd_per_kwh in (
        {"All inclusive": 0.18462291666666666},
        {"Day": 0.242, "Night": 0.18},
    )


def test_postcode_to_energy_plan():
    """
    Test the postcode_to_energy_plan function.
    """
    plan = postcode_to_energy_plan("6012")
    assert plan.name in ("Plan for 6012", "Default Electricity Plan")
    assert plan.electricity_plan.name in ("37887", "Default Electricity Plan")
    assert plan.electricity_plan.daily_charge in (2.304945, 2.0)
    assert plan.electricity_plan.nzd_per_kwh in (
        {"All inclusive": 0.18462291666666666},
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


# pylint: disable=too-many-instance-attributes
class TestElectricityPlan(unittest.TestCase):
    """
    Test the ElectricityPlan class.
    """

    def setUp(self):
        self.profile = HouseholdYearlyFuelUsageProfile(
            elx_connection_days=DAYS_IN_YEAR,
            day_kwh=300,
            flexible_kwh=100,
            natural_gas_connection_days=0,
            natural_gas_kwh=0,
            lpg_tanks_rental_days=0,
            lpg_kwh=0,
            wood_kwh=0,
            petrol_litres=0,
            diesel_litres=0,
        )

        day = 0.25
        night = 0.15
        controlled = 0.20
        uncontrolled = 0.22
        all_inclusive = 0.18

        self.electricity_plan = ElectricityPlan(
            name="TestPlan",
            daily_charge=1.5,
            nzd_per_kwh={"Day": 0.25, "Night": 0.15, "Controlled": 0.20},
        )
        self.electricity_plan_all_inclusive = ElectricityPlan(
            name="AllInclusivePlan",
            daily_charge=1.0,
            nzd_per_kwh={"All inclusive": all_inclusive},
        )
        self.electricity_plan_day_night = ElectricityPlan(
            name="AllInclusivePlan",
            daily_charge=1.0,
            nzd_per_kwh={"Day": day, "Night": night},
        )
        self.electricity_plan_uncontrolled = ElectricityPlan(
            name="UncontrolledPlan",
            daily_charge=1.0,
            nzd_per_kwh={"Uncontrolled": uncontrolled},
        )
        self.electricity_plan_uncontrolled_controlled = ElectricityPlan(
            name="UncontrolledPlan",
            daily_charge=1.0,
            nzd_per_kwh={"Uncontrolled": uncontrolled, "Controlled": controlled},
        )
        self.electricity_plan_uncontrolled_all_inclusive = ElectricityPlan(
            name="UncontrolledPlan",
            daily_charge=1.0,
            nzd_per_kwh={"Uncontrolled": uncontrolled, "All inclusive": all_inclusive},
        )
        self.electricity_plan_night_controlled_day = ElectricityPlan(
            name="UncontrolledPlan",
            daily_charge=1.0,
            nzd_per_kwh={"Night": night, "Controlled": controlled, "Day": day},
        )
        self.electricity_plan_night_all_inclusive = ElectricityPlan(
            name="UncontrolledPlan",
            daily_charge=1.0,
            nzd_per_kwh={"Night": night, "All inclusive": all_inclusive},
        )
        self.electricity_plan_night_uncontrolled_controlled = ElectricityPlan(
            name="UncontrolledPlan",
            daily_charge=1.0,
            nzd_per_kwh={
                "Night": night,
                "Uncontrolled": uncontrolled,
                "Controlled": controlled,
            },
        )
        self.electricity_plan_night_uncontrolled = ElectricityPlan(
            name="UncontrolledPlan",
            daily_charge=1.0,
            nzd_per_kwh={"Night": night, "Uncontrolled": uncontrolled},
        )

    def test_all_inclusive_plan(self):
        """
        Test electricity plan with variable pricing pattern
        {"All inclusive"}.
        """
        cost = self.electricity_plan_all_inclusive.calculate_cost(self.profile)
        self.assertEqual(cost, (1.0 * DAYS_IN_YEAR, (300 + 100) * 0.18))

    def test_day_night_plan(self):
        """
        Test electricity plan with variable pricing pattern
        {"Day", "Night"}.
        """
        cost = self.electricity_plan_day_night.calculate_cost(self.profile)
        self.assertEqual(cost, (1.0 * DAYS_IN_YEAR, 300 * 0.25 + 100 * 0.15))

    def test_uncontrolled(self):
        """
        Test electricity plan with variable pricing pattern
        {"Uncontrolled"}.
        """
        cost = self.electricity_plan_uncontrolled.calculate_cost(self.profile)
        self.assertEqual(cost, (1.0 * DAYS_IN_YEAR, (300 + 100) * 0.22))

    def test_uncontrolled_controlled(self):
        """
        Test electricity plan with variable pricing pattern
        {"Uncontrolled", "Controlled"}.
        """
        cost = self.electricity_plan_uncontrolled_controlled.calculate_cost(
            self.profile
        )
        self.assertEqual(cost, (1.0 * DAYS_IN_YEAR, 300 * 0.22 + 100 * 0.20))

    def test_uncontrolled_all_inclusive(self):
        """
        Test electricity plan with variable pricing pattern
        {"Uncontrolled", "All inclusive"}.
        """
        cost = self.electricity_plan_uncontrolled_all_inclusive.calculate_cost(
            self.profile
        )
        self.assertEqual(cost, (1.0 * DAYS_IN_YEAR, (300 + 100) * 0.18))

    def test_night_controlled_day(self):
        """
        Test electricity plan with variable pricing pattern
        {"Night", "Controlled", "Day"}.
        """
        cost = self.electricity_plan_night_controlled_day.calculate_cost(self.profile)
        self.assertEqual(cost, (1.0 * DAYS_IN_YEAR, 300 * 0.25 + 100 * 0.15))

    def test_night_all_inclusive(self):
        """
        Test electricity plan with variable pricing pattern
        {"Night", "All inclusive"}.
        """
        cost = self.electricity_plan_night_all_inclusive.calculate_cost(self.profile)
        self.assertEqual(cost, (1.0 * DAYS_IN_YEAR, 300 * 0.18 + 100 * 0.15))

    def test_night_uncontrolled_controlled(self):
        """
        Test electricity plan with variable pricing pattern
        {"Night", "Uncontrolled", "Controlled"}.
        """
        cost = self.electricity_plan_night_uncontrolled_controlled.calculate_cost(
            self.profile
        )
        self.assertEqual(cost, (1.0 * DAYS_IN_YEAR, 300 * 0.22 + 100 * 0.15))

    def test_night_uncontrolled(self):
        """
        Test electricity plan with variable pricing pattern
        {"Night", "Uncontrolled"}.
        """
        cost = self.electricity_plan_night_uncontrolled.calculate_cost(self.profile)
        self.assertEqual(cost, (1.0 * DAYS_IN_YEAR, 300 * 0.22 + 100 * 0.15))


if __name__ == "__main__":
    unittest.main()
