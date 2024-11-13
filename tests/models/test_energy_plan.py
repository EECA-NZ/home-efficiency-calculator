"""
Test the energy plan service
"""

import unittest

from app.constants import DAYS_IN_YEAR
from app.models.energy_plans import ElectricityPlan
from app.models.usage_profiles import YearlyFuelUsageProfile
from app.services.get_energy_plans import (
    edb_zone_to_electricity_plan,
    get_energy_plan,
    postcode_to_edb_zone,
    postcode_to_electricity_plan,
)


def test_postcode_to_edb_zone():
    """
    Test the get_default_household_answers function.
    """
    edb_zone = postcode_to_edb_zone("6012")
    assert edb_zone == "Wellington Electricity"


def test_edb_zone_to_electricity_plan():
    """
    Test the edb_zone_to_electricity_plan function.
    """
    plan = edb_zone_to_electricity_plan("Wellington Electricity")
    assert plan.name == "Electricity PlanId 172954"
    assert plan.daily_charge in (1.787445, 2.0)
    assert plan.nzd_per_kwh in (
        {"Day": 0.29324999999999996, "Night": 0.14662499999999998},
        {"Day": 0.242, "Night": 0.18},
    )


def test_postcode_to_electricity_plan():
    """
    Test the postcode_to_electricity_plan function.
    """
    plan = postcode_to_electricity_plan("6012")
    assert plan.name == "Electricity PlanId 172954"
    assert plan.daily_charge in (1.787445, 2.0)
    assert plan.nzd_per_kwh in (
        {"Day": 0.29324999999999996, "Night": 0.14662499999999998},
        {"Day": 0.242, "Night": 0.18},
    )


def test_get_energy_plan():
    """
    Test the get_energy_plan function.
    """
    plan = get_energy_plan("6012", "None")
    assert plan.name == "Plan for 6012"
    assert plan.electricity_plan.name == "Electricity PlanId 172954"
    assert plan.electricity_plan.daily_charge in (1.787445, 2.0)
    assert plan.electricity_plan.nzd_per_kwh in (
        {"Day": 0.29324999999999996, "Night": 0.14662499999999998},
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
        self.profile = YearlyFuelUsageProfile(
            elx_connection_days=DAYS_IN_YEAR,
            inflexible_day_kwh=300,
            flexible_kwh=100,
            natural_gas_connection_days=0,
            natural_gas_kwh=0,
            lpg_tanks_rental_days=0,
            lpg_kwh=0,
            wood_kwh=0,
            petrol_litres=0,
            diesel_litres=0,
            public_ev_charger_kwh=0,
            thousand_km_petrol=0,
            thousand_km_diesel=0,
            thousand_km_hybrid=0,
            thousand_km_plug_in_hybrid=0,
            thousand_km_electric=0,
        )

        self.day = 0.25
        self.night = 0.15
        self.controlled = 0.20
        self.uncontrolled = 0.22
        self.all_inclusive = 0.18
        self.high_daily_charge = 1.5
        self.daily_charge = 1.0

        self.electricity_plan = ElectricityPlan(
            name="TestPlan",
            daily_charge=self.high_daily_charge,
            nzd_per_kwh={
                "Day": self.day,
                "Night": self.night,
                "Controlled": self.controlled,
            },
        )
        self.electricity_plan_all_inclusive = ElectricityPlan(
            name="AllInclusivePlan",
            daily_charge=self.daily_charge,
            nzd_per_kwh={"All inclusive": self.all_inclusive},
        )
        self.electricity_plan_day_night = ElectricityPlan(
            name="AllInclusivePlan",
            daily_charge=self.daily_charge,
            nzd_per_kwh={"Day": self.day, "Night": self.night},
        )
        self.electricity_plan_uncontrolled = ElectricityPlan(
            name="UncontrolledPlan",
            daily_charge=self.daily_charge,
            nzd_per_kwh={"Uncontrolled": self.uncontrolled},
        )
        self.electricity_plan_uncontrolled_controlled = ElectricityPlan(
            name="UncontrolledPlan",
            daily_charge=self.daily_charge,
            nzd_per_kwh={
                "Uncontrolled": self.uncontrolled,
                "Controlled": self.controlled,
            },
        )
        self.electricity_plan_uncontrolled_all_inclusive = ElectricityPlan(
            name="UncontrolledPlan",
            daily_charge=self.daily_charge,
            nzd_per_kwh={
                "Uncontrolled": self.uncontrolled,
                "All inclusive": self.all_inclusive,
            },
        )
        self.electricity_plan_night_controlled_day = ElectricityPlan(
            name="UncontrolledPlan",
            daily_charge=self.daily_charge,
            nzd_per_kwh={
                "Night": self.night,
                "Controlled": self.controlled,
                "Day": self.day,
            },
        )
        self.electricity_plan_night_all_inclusive = ElectricityPlan(
            name="UncontrolledPlan",
            daily_charge=self.daily_charge,
            nzd_per_kwh={"Night": self.night, "All inclusive": self.all_inclusive},
        )
        self.electricity_plan_night_uncontrolled_controlled = ElectricityPlan(
            name="UncontrolledPlan",
            daily_charge=self.daily_charge,
            nzd_per_kwh={
                "Night": self.night,
                "Uncontrolled": self.uncontrolled,
                "Controlled": self.controlled,
            },
        )
        self.electricity_plan_night_uncontrolled = ElectricityPlan(
            name="UncontrolledPlan",
            daily_charge=self.daily_charge,
            nzd_per_kwh={"Night": self.night, "Uncontrolled": self.uncontrolled},
        )

    def test_all_inclusive_plan(self):
        """
        Test electricity plan with variable pricing pattern
        {"All inclusive"}.
        """
        cost = self.electricity_plan_all_inclusive.calculate_cost(self.profile)
        self.assertEqual(
            cost, (self.daily_charge * DAYS_IN_YEAR, (300 + 100) * self.all_inclusive)
        )

    def test_day_night_plan(self):
        """
        Test electricity plan with variable pricing pattern
        {"Day", "Night"}.
        """
        cost = self.electricity_plan_day_night.calculate_cost(self.profile)
        self.assertEqual(
            cost, (self.daily_charge * DAYS_IN_YEAR, 300 * self.day + 100 * self.night)
        )

    def test_uncontrolled(self):
        """
        Test electricity plan with variable pricing pattern
        {"Uncontrolled"}.
        """
        cost = self.electricity_plan_uncontrolled.calculate_cost(self.profile)
        self.assertEqual(
            cost, (self.daily_charge * DAYS_IN_YEAR, (300 + 100) * self.uncontrolled)
        )

    def test_uncontrolled_controlled(self):
        """
        Test electricity plan with variable pricing pattern
        {"Uncontrolled", "Controlled"}.
        """
        cost = self.electricity_plan_uncontrolled_controlled.calculate_cost(
            self.profile
        )
        self.assertEqual(
            cost,
            (
                self.daily_charge * DAYS_IN_YEAR,
                300 * self.uncontrolled + 100 * self.controlled,
            ),
        )

    def test_uncontrolled_all_inclusive(self):
        """
        Test electricity plan with variable pricing pattern
        {"Uncontrolled", "All inclusive"}.
        """
        cost = self.electricity_plan_uncontrolled_all_inclusive.calculate_cost(
            self.profile
        )
        self.assertEqual(
            cost, (self.daily_charge * DAYS_IN_YEAR, (300 + 100) * self.all_inclusive)
        )

    def test_night_controlled_day(self):
        """
        Test electricity plan with variable pricing pattern
        {"Night", "Controlled", "Day"}.
        """
        cost = self.electricity_plan_night_controlled_day.calculate_cost(self.profile)
        self.assertEqual(
            cost, (self.daily_charge * DAYS_IN_YEAR, 300 * self.day + 100 * self.night)
        )

    def test_night_all_inclusive(self):
        """
        Test electricity plan with variable pricing pattern
        {"Night", "All inclusive"}.
        """
        cost = self.electricity_plan_night_all_inclusive.calculate_cost(self.profile)
        self.assertEqual(
            cost,
            (
                self.daily_charge * DAYS_IN_YEAR,
                300 * self.all_inclusive + 100 * self.night,
            ),
        )

    def test_night_uncontrolled_controlled(self):
        """
        Test electricity plan with variable pricing pattern
        {"Night", "Uncontrolled", "Controlled"}.
        Since the Controlled rate is more expensive than the Night rate,
        the Controlled rate is used for the flexible kwh.
        """
        cost = self.electricity_plan_night_uncontrolled_controlled.calculate_cost(
            self.profile
        )
        self.assertEqual(
            cost,
            (
                self.daily_charge * DAYS_IN_YEAR,
                300 * self.uncontrolled + 100 * self.night,
            ),
        )

    def test_night_uncontrolled(self):
        """
        Test electricity plan with variable pricing pattern
        {"Night", "Uncontrolled"}.
        """
        cost = self.electricity_plan_night_uncontrolled.calculate_cost(self.profile)
        self.assertEqual(
            cost,
            (
                self.daily_charge * DAYS_IN_YEAR,
                300 * self.uncontrolled + 100 * self.night,
            ),
        )

    def test_unexpected_keys(self):
        """
        Test with an unexpected key scenario
        """
        self.electricity_plan_night_uncontrolled.nzd_per_kwh = {"Unexpected": 0.30}
        with self.assertRaises(ValueError):
            self.electricity_plan_night_uncontrolled.calculate_cost(self.profile)
