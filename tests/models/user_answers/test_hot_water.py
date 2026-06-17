"""
Test energy consumption profile and behaviour of the HotWaterAnswers class.
"""

# pylint: disable=no-member
import csv
from pathlib import Path

from pytest import approx

from app.constants import DAYS_IN_YEAR, HOT_WATER_FLEXIBLE_KWH_FRACTION
from app.models.hourly_profiles import flat_day_night_profiles
from app.models.usage_profiles import ElectricityUsage, YearlyFuelUsageProfile
from app.models.user_answers import HotWaterAnswers, YourHomeAnswers
from app.services.configuration import get_default_household_answers
from app.services.energy_calculator import emissions_kg_co2e
from app.services.postcode_lookups.get_climate_zone import climate_zone
from app.services.postcode_lookups.get_energy_plans import get_energy_plan
from app.services.usage_calculation.hot_water_helpers import (
    other_water_kwh_per_year,
    shower_kwh_per_year,
)

# Energy usage is summed over profiles in the tests
# so we can use a flat daytime profile
day_profile, _ = flat_day_night_profiles()
RESOURCE_DIR = Path(__file__).resolve().parents[3] / "resources"
LOOKUP_TABLES_DIRS = [
    RESOURCE_DIR / "lookup_tables",
    RESOURCE_DIR / "test_data" / "lookup_tables",
]


def lookup_row_by_fields(lookup_table_name, expected_fields):
    """
    Find a single row in a lookup table by exact column/value matches.
    """
    lookup_path = next(
        (
            lookup_dir / lookup_table_name
            for lookup_dir in LOOKUP_TABLES_DIRS
            if (lookup_dir / lookup_table_name).exists()
        ),
        None,
    )
    if lookup_path is None:
        raise AssertionError(f"Could not find lookup table {lookup_table_name}")
    with lookup_path.open(encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        matched_rows = [
            row
            for row in reader
            if all(
                str(row[field]) == str(value)
                for field, value in expected_fields.items()
            )
        ]

    if len(matched_rows) != 1:
        raise AssertionError(
            f"Expected exactly one row in {lookup_table_name} for {expected_fields}, "
            f"found {len(matched_rows)}"
        )
    return matched_rows[0]


def test_water_heating_energy_usage():
    """
    Test the energy usage pattern for water heating.
    Example used:
        hot_water_usage='Average',
        hot_water_heating_source='Electric hot water cylinder',
        people_in_house=4
        climate_zone = 'Wellington'

    Expected values:

    """
    answers = get_default_household_answers()
    total_kwh = 2572.2628670365157
    anytime_kwh = total_kwh * HOT_WATER_FLEXIBLE_KWH_FRACTION
    fixed_kwh = total_kwh - anytime_kwh

    electricity_kwh = ElectricityUsage(
        fixed_day_kwh=0.0,
        fixed_ngt_kwh=fixed_kwh,
        fixed_profile=day_profile,
        shift_abl_kwh=anytime_kwh,
        shift_profile=day_profile,
    )

    hot_water_sources = {
        "Electric hot water cylinder": YearlyFuelUsageProfile(
            elx_connection_days=DAYS_IN_YEAR,
            electricity_kwh=electricity_kwh,
            natural_gas_connection_days=0,
            natural_gas_kwh=0,
            lpg_tanks_rental_days=0,
            lpg_kwh=0,
            wood_kwh=0,
            petrol_litres=0,
            diesel_litres=0,
            public_ev_charger_kwh=0,
            thousand_km=0,
        ),
    }
    for hot_water_source, expected_energy_profile in hot_water_sources.items():
        hot_water = HotWaterAnswers(
            hot_water_usage=answers.hot_water.hot_water_usage,
            hot_water_heating_source=hot_water_source,
        )
        hot_water_energy_use = hot_water.energy_usage_pattern(
            answers.your_home, answers.solar
        )
        assert (
            hot_water_energy_use.elx_connection_days
            == expected_energy_profile.elx_connection_days
        )
        assert (
            hot_water_energy_use.electricity_kwh.fixed_day_kwh
            + hot_water_energy_use.electricity_kwh.fixed_ngt_kwh
            == approx(
                expected_energy_profile.electricity_kwh.total_fixed_time_usage.sum()
            )
        )
        assert hot_water_energy_use.electricity_kwh.shift_abl_kwh == approx(
            expected_energy_profile.electricity_kwh.total_shift_able_usage.sum()
        )
        assert (
            hot_water_energy_use.natural_gas_connection_days
            == expected_energy_profile.natural_gas_connection_days
        )
        assert hot_water_energy_use.natural_gas_kwh == approx(
            expected_energy_profile.natural_gas_kwh
        )
        assert (
            hot_water_energy_use.lpg_tanks_rental_days
            == expected_energy_profile.lpg_tanks_rental_days
        )
        assert hot_water_energy_use.lpg_kwh == approx(expected_energy_profile.lpg_kwh)
        assert hot_water_energy_use.wood_kwh == approx(expected_energy_profile.wood_kwh)
        assert hot_water_energy_use.petrol_litres == approx(
            expected_energy_profile.petrol_litres
        )
        assert hot_water_energy_use.diesel_litres == approx(
            expected_energy_profile.diesel_litres
        )
        assert hot_water_energy_use.public_ev_charger_kwh == approx(
            expected_energy_profile.public_ev_charger_kwh
        )
        assert hot_water_energy_use.thousand_km == approx(
            expected_energy_profile.thousand_km
        )


def test_hpwh_energy_usage_matches_2026_system_model_example():
    """
    Test the 2026 HPWH system model against the Wellington spreadsheet example.
    """
    hot_water = HotWaterAnswers(
        hot_water_usage="Average",
        hot_water_heating_source="Hot water heat pump",
    )
    your_home = YourHomeAnswers(people_in_house=4, postcode="6012")

    hot_water_energy_use = hot_water.energy_usage_pattern(your_home, solar_aware=False)

    assert hot_water_energy_use.electricity_kwh.annual_kwh == approx(
        1049.9546859214693, abs=0.25
    )


def test_hpwh_effective_cop_matches_2026_sheet_examples():
    """
    Test whole-system delivered COP against representative spreadsheet examples.
    """
    scenarios = [
        ("6012", 1, "Low", 0.984873504732831),
        ("6012", 4, "Average", 2.5689068860606925),
        ("6012", 6, "High", 3.1839049300995725),
        ("8011", 1, "Average", 1.2501648558854266),
        ("8011", 4, "Average", 2.320148199416599),
        ("8011", 6, "High", 2.8489383240911152),
    ]

    for postcode, people, usage, expected_effective_cop in scenarios:
        hot_water = HotWaterAnswers(
            hot_water_usage=usage,
            hot_water_heating_source="Hot water heat pump",
        )
        your_home = YourHomeAnswers(people_in_house=people, postcode=postcode)
        climate = climate_zone(postcode)

        hot_water_energy_use = hot_water.energy_usage_pattern(
            your_home, solar_aware=False
        )
        delivered_energy = shower_kwh_per_year(usage, climate, people) + (
            other_water_kwh_per_year(climate, people)
        )
        effective_cop = (
            delivered_energy / hot_water_energy_use.electricity_kwh.annual_kwh
        )

        assert effective_cop == approx(expected_effective_cop, abs=0.001)


def test_hpwh_runtime_matches_solar_lookup_table_outputs():
    """
    Test HPWH annual electricity use against the solar hot water lookup table.
    """
    scenarios = [
        ("6012", 4, "Average"),
        ("8022", 1, "Low"),
        ("9016", 6, "High"),
    ]

    for postcode, people, usage in scenarios:
        your_home = YourHomeAnswers(people_in_house=people, postcode=postcode)
        hot_water = HotWaterAnswers(
            hot_water_usage=usage,
            hot_water_heating_source="Hot water heat pump",
        )
        energy_use = hot_water.energy_usage_pattern(your_home, solar_aware=True)
        row = lookup_row_by_fields(
            "solar_hot_water_lookup_table.csv",
            {
                "climate_zone": climate_zone(postcode),
                "people_in_house": people,
                "hot_water_usage": usage,
                "hot_water_heating_source": "Hot water heat pump",
            },
        )

        assert float(row["annual_total_kwh"]) == approx(
            energy_use.electricity_kwh.annual_kwh, abs=1e-6
        )


def test_hpwh_runtime_matches_cost_and_emissions_lookup_table_outputs():
    """
    Test HPWH annual cost and emissions against the hot water lookup table.
    """
    scenarios = [
        ("6012", 4, "Average"),
        ("8022", 1, "Low"),
        ("9016", 6, "High"),
    ]

    for postcode, people, usage in scenarios:
        your_home = YourHomeAnswers(people_in_house=people, postcode=postcode)
        hot_water = HotWaterAnswers(
            hot_water_usage=usage,
            hot_water_heating_source="Hot water heat pump",
        )
        energy_use = hot_water.energy_usage_pattern(your_home, solar_aware=False)
        energy_plan = get_energy_plan(postcode, "None")
        cost_breakdown = energy_plan.calculate_cost(energy_use)
        row = lookup_row_by_fields(
            "hot_water_lookup_table.csv",
            {
                "climate_zone": climate_zone(postcode),
                "electricity_plan_name": energy_plan.electricity_plan.name,
                "natural_gas_plan_name": energy_plan.natural_gas_plan.name,
                "lpg_plan_name": energy_plan.lpg_plan.name,
                "wood_price_name": energy_plan.wood_price.name,
                "petrol_price_name": energy_plan.petrol_price.name,
                "diesel_price_name": energy_plan.diesel_price.name,
                "people_in_house": people,
                "disconnect_gas": False,
                "hot_water_usage": usage,
                "hot_water_heating_source": "Hot water heat pump",
            },
        )

        assert float(row["annual_variable_cost"]) == approx(
            cost_breakdown.variable_cost_nzd, abs=1e-6
        )
        assert float(row["annual_kg_co2e"]) == approx(
            emissions_kg_co2e(energy_use), abs=1e-6
        )
