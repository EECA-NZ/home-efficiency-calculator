"""
Test the energy plan service
"""

import re
import unittest

from pytest import approx

from app.constants import DAYS_IN_YEAR
from app.models.energy_plans import ElectricityPlan
from app.models.usage_profiles import (
    ElectricityUsageDetailed,
    HouseholdYearlyFuelUsageProfile,
)
from app.services.get_energy_plans import (
    edb_zone_to_electricity_plan,
    get_energy_plan,
    postcode_to_edb_zone,
    postcode_to_electricity_plan,
)
from app.services.usage_profile_helpers import flat_day_night_profiles

day_profile, night_profile = flat_day_night_profiles()


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
    assert re.match(r"Electricity PlanId [0-9]+|Default Electricity Plan", plan.name)
    assert plan.fixed_rate in (2.4172999999999996, 2.0)
    assert plan.import_rates in (
        {"Day": 0.21228999999999998, "Night": 0.17204},
        {"Day": 0.242, "Night": 0.18},
    )


def test_postcode_to_electricity_plan():
    """
    Test the postcode_to_electricity_plan function.
    """
    plan = postcode_to_electricity_plan("6012")
    assert re.match(r"Electricity PlanId [0-9]+|Default Electricity Plan", plan.name)
    assert plan.fixed_rate in (2.4172999999999996, 2.0)
    assert plan.import_rates in (
        {"Day": 0.21228999999999998, "Night": 0.17204},
        {"Day": 0.242, "Night": 0.18},
    )


def test_get_energy_plan():
    """
    Test the get_energy_plan function.
    """
    plan = get_energy_plan("6012", "None")
    assert plan.name in ("Plan for 6012", "Default Electricity Plan")
    assert re.match(
        r"Electricity PlanId [0-9]+|Default Electricity Plan",
        plan.electricity_plan.name,
    )
    assert plan.electricity_plan.fixed_rate in (2.4172999999999996, 2.0)
    assert plan.electricity_plan.import_rates in (
        {"Day": 0.21228999999999998, "Night": 0.17204},
        {"Day": 0.242, "Night": 0.18},
    )
    assert (
        "Methane" in plan.natural_gas_plan.name
        or "Default Natural Gas Plan" in plan.natural_gas_plan.name
    )
    # Plan tariffs are either RA numbers or averages from Powerswitch dataset
    assert plan.natural_gas_plan.import_rates["Uncontrolled"] == approx(
        0.11
    ) or plan.natural_gas_plan.import_rates["Uncontrolled"] == approx(
        0.21389999999999998
    )
    assert plan.natural_gas_plan.fixed_rate == approx(
        1.6
    ) or plan.natural_gas_plan.fixed_rate == approx(1.01449)
    assert plan.lpg_plan.name == "Default LPG Plan"
    assert plan.lpg_plan.per_lpg_kwh == 0.244
    assert plan.lpg_plan.fixed_rate == 0.37782340862423
    assert plan.wood_price.name == "Default Wood Price"
    assert plan.wood_price.per_wood_kwh == approx(0.1148, rel=1e-4)
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
            electricity_kwh=ElectricityUsageDetailed(
                fixed_time_uncontrolled_kwh=300 * day_profile,
                shift_able_controllable_kwh=100 * night_profile,
            ),
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
        self.high_fixed_rate = 1.5
        self.fixed_rate = 1.0
        self.feed_in_tariff = 0.12

        self.electricity_plan = ElectricityPlan(
            name="TestPlan",
            fixed_rate=self.high_fixed_rate,
            import_rates={
                "Day": self.day,
                "Night": self.night,
                "Controlled": self.controlled,
            },
            export_rates={"Uncontrolled": self.feed_in_tariff},
        )
        self.electricity_plan_all_inclusive = ElectricityPlan(
            name="AllInclusivePlan",
            fixed_rate=self.fixed_rate,
            import_rates={"All inclusive": self.all_inclusive},
            export_rates={"Uncontrolled": self.feed_in_tariff},
        )
        self.electricity_plan_day_night = ElectricityPlan(
            name="AllInclusivePlan",
            fixed_rate=self.fixed_rate,
            import_rates={"Day": self.day, "Night": self.night},
            export_rates={"Uncontrolled": self.feed_in_tariff},
        )
        self.electricity_plan_uncontrolled = ElectricityPlan(
            name="UncontrolledPlan",
            fixed_rate=self.fixed_rate,
            import_rates={"Uncontrolled": self.uncontrolled},
            export_rates={"Uncontrolled": self.feed_in_tariff},
        )
        self.electricity_plan_uncontrolled_controlled = ElectricityPlan(
            name="UncontrolledPlan",
            fixed_rate=self.fixed_rate,
            import_rates={
                "Uncontrolled": self.uncontrolled,
                "Controlled": self.controlled,
            },
            export_rates={"Uncontrolled": self.feed_in_tariff},
        )
        self.electricity_plan_night_all_inclusive = ElectricityPlan(
            name="UncontrolledPlan",
            fixed_rate=self.fixed_rate,
            import_rates={"Night": self.night, "All inclusive": self.all_inclusive},
            export_rates={"Uncontrolled": self.feed_in_tariff},
        )
        self.electricity_plan_night_uncontrolled = ElectricityPlan(
            name="UncontrolledPlan",
            fixed_rate=self.fixed_rate,
            import_rates={"Night": self.night, "Uncontrolled": self.uncontrolled},
            export_rates={"Uncontrolled": self.feed_in_tariff},
        )

    def test_all_inclusive_plan(self):
        """
        Test electricity plan with variable pricing pattern
        {"All inclusive"}.
        """
        cost = self.electricity_plan_all_inclusive.calculate_cost(self.profile)
        self.assertAlmostEqual(cost.fixed_cost_nzd, self.fixed_rate * DAYS_IN_YEAR)
        self.assertAlmostEqual(cost.variable_cost_nzd, (300 + 100) * self.all_inclusive)

    def test_day_night_plan(self):
        """
        Test electricity plan with variable pricing pattern
        {"Day", "Night"}.
        """
        cost = self.electricity_plan_day_night.calculate_cost(self.profile)
        self.assertAlmostEqual(cost.fixed_cost_nzd, self.fixed_rate * DAYS_IN_YEAR)
        self.assertAlmostEqual(
            cost.variable_cost_nzd, 300 * self.day + 100 * self.night
        )

    def test_uncontrolled(self):
        """
        Test electricity plan with variable pricing pattern
        {"Uncontrolled"}.
        """
        cost = self.electricity_plan_uncontrolled.calculate_cost(self.profile)
        self.assertAlmostEqual(cost.fixed_cost_nzd, self.fixed_rate * DAYS_IN_YEAR)
        self.assertAlmostEqual(cost.variable_cost_nzd, (300 + 100) * self.uncontrolled)

    def test_uncontrolled_controlled(self):
        """
        Test electricity plan with variable pricing pattern
        {"Uncontrolled", "Controlled"}.
        """
        cost = self.electricity_plan_uncontrolled_controlled.calculate_cost(
            self.profile
        )
        self.assertAlmostEqual(cost.fixed_cost_nzd, self.fixed_rate * DAYS_IN_YEAR)
        self.assertAlmostEqual(
            cost.variable_cost_nzd, 300 * self.uncontrolled + 100 * self.controlled
        )

    def test_unexpected_keys(self):
        """
        Test with an unexpected key scenario
        """
        self.electricity_plan_night_uncontrolled.import_rates = {"Unexpected": 0.30}
        with self.assertRaises(ValueError):
            self.electricity_plan_night_uncontrolled.calculate_cost(self.profile)
