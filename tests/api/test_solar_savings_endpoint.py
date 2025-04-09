"""
Test solar generation calculation of solar self-consumption
vs export for various input profiles. Starting point.
"""

import importlib.resources as pkg_resources
import os

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pytest import approx

from app.api.solar_savings_endpoint import get_solar_savings
from app.main import app
from app.models.user_answers import (
    BasicHouseholdAnswers,
    CooktopAnswers,
    DrivingAnswers,
    HeatingAnswers,
    HotWaterAnswers,
    SolarAnswers,
    YourHomeAnswers,
)
from app.services.postcode_lookups.get_climate_zone import climate_zone
from app.services.postcode_lookups.get_energy_plans import get_energy_plan

# pylint: disable=fixme, too-many-locals, too-many-statements

client = TestClient(app)


@pytest.mark.asyncio
async def test_get_solar_savings_direct_call():
    """
    Direct async test of the get_solar_savings function.
    """
    answers = BasicHouseholdAnswers(
        your_home=YourHomeAnswers(
            people_in_house=4,
            postcode="6012",
        ),
        heating=HeatingAnswers(
            main_heating_source="Piped gas heater",
            alternative_main_heating_source="Heat pump",
            heating_during_day="3-4 days a week",
            insulation_quality="Not well insulated",
        ),
        hot_water=HotWaterAnswers(
            hot_water_usage="High",
            hot_water_heating_source="Electric hot water cylinder",
            alternative_hot_water_heating_source="Hot water heat pump",
        ),
        cooktop=CooktopAnswers(
            cooktop="Electric (coil or ceramic)",
            alternative_cooktop="Electric induction",
        ),
        driving=DrivingAnswers(
            vehicle_size="Small",
            km_per_week="200",
            vehicle_type="Petrol",
            alternative_vehicle_type="Electric",
        ),
        solar=SolarAnswers(add_solar=True),
    )

    result = await get_solar_savings(answers)
    response_data = result.model_dump()

    assert response_data["annual_kwh_generated"] > 0
    assert response_data["annual_earnings_solar_export"] >= 0
    assert response_data["annual_savings_solar_self_consumption"] >= 0
    assert response_data["annual_kg_co2e_saving"] > 0


@pytest.fixture(autouse=True, scope="session")
def set_test_environment_variable():
    """
    Set the TEST_MODE environment variable to True.
    This will ensure that the test data is used, allowing
    the tests to run without the need for data files that
    are not licensed for sharing publicly.
    """
    os.environ["TEST_MODE"] = "False"


def load_lookup_timeseries(
    lookup_csv_path: str, row_prefix: str, hour_count: int = 8760
) -> np.ndarray:
    """
    Reads a CSV (with headers) and looks for a row where the first N columns
    (N = number of commas in row_prefix + 1) match row_prefix when joined with commas.

    Expects:
      - A column named 'annual_total_kwh'.
      - Hourly fractional columns named '0' .. '8759' (There are
        8760 of them, scaled to sum to 1000).

    Returns:
      A NumPy array of length = hour_count,
      scaled by (annual_total_kwh / 1000).
    """
    df = pd.read_csv(lookup_csv_path)
    if row_prefix.strip() == "":
        match_len = 0
    else:
        prefix_parts = row_prefix.split(",")
        match_len = len(prefix_parts)
    if match_len > 0:
        leading_col_names = df.columns[:match_len]
        df["_combined"] = df[leading_col_names].astype(str).agg(",".join, axis=1)
        matched_rows = df[df["_combined"] == row_prefix]
    else:
        matched_rows = df

    if len(matched_rows) == 0:
        raise ValueError(f"No rows found matching prefix: '{row_prefix}'")
    if len(matched_rows) > 1:
        raise ValueError(f"Multiple rows found matching prefix: '{row_prefix}'")

    row = matched_rows.iloc[0]

    if "annual_total_kwh" not in row:
        raise ValueError("CSV does not contain a column named 'annual_total_kwh'.")
    annual_total = float(row["annual_total_kwh"])

    frac_cols = [str(i) for i in range(hour_count)]
    if not all(col in row for col in frac_cols):
        missing = [c for c in frac_cols if c not in row]
        raise ValueError(
            f"CSV is missing expected fractional columns, e.g. {missing[:10]}"
        )
    fractions = row[frac_cols].astype(float).to_numpy()
    return (annual_total / 1000.0) * fractions


profile0 = {
    "your_home": {"people_in_house": 4, "postcode": "6012"},
    "heating": {
        "main_heating_source": "Piped gas heater",
        "alternative_main_heating_source": "Heat pump",
        "heating_during_day": "3-4 days a week",
        "insulation_quality": "Not well insulated",
    },
    "hot_water": {
        "hot_water_usage": "High",
        "hot_water_heating_source": "Electric hot water cylinder",
        "alternative_hot_water_heating_source": "Hot water heat pump",
    },
    "cooktop": {
        "cooktop": "Electric (coil or ceramic)",
        "alternative_cooktop": "Electric induction",
    },
    "driving": {
        "vehicle_size": "Small",
        "km_per_week": "200",
        "vehicle_type": "Petrol",
        "alternative_vehicle_type": "Electric",
    },
    "solar": {"add_solar": True},
}

profile1 = {
    "your_home": {"people_in_house": 4, "postcode": "9016"},
    "heating": {
        "main_heating_source": "Electric heater",
        "alternative_main_heating_source": "Heat pump",
        "heating_during_day": "3-4 days a week",
        "insulation_quality": "Not well insulated",
    },
    "hot_water": {
        "hot_water_usage": "High",
        "hot_water_heating_source": "Electric hot water cylinder",
        "alternative_hot_water_heating_source": "Hot water heat pump",
    },
    "cooktop": {
        "cooktop": "Electric (coil or ceramic)",
        "alternative_cooktop": "Electric induction",
    },
    "driving": {
        "vehicle_size": "Small",
        "km_per_week": "200",
        "vehicle_type": "Petrol",
        "alternative_vehicle_type": "Electric",
    },
    "solar": {"add_solar": True},
}

profile2 = {
    "your_home": {"people_in_house": 4, "postcode": "9016"},
    "heating": {
        "main_heating_source": "Wood burner",
        "alternative_main_heating_source": "Heat pump",
        "heating_during_day": "Never",
        "insulation_quality": "Not well insulated",
    },
    "hot_water": {
        "hot_water_usage": "Low",
        "hot_water_heating_source": "Electric hot water cylinder",
        "alternative_hot_water_heating_source": "Hot water heat pump",
    },
    "cooktop": {
        "cooktop": "Electric (coil or ceramic)",
        "alternative_cooktop": "Electric induction",
    },
    "driving": {
        "vehicle_size": "Small",
        "km_per_week": "100",
        "vehicle_type": "Petrol",
        "alternative_vehicle_type": "Electric",
    },
    "solar": {"add_solar": True},
}

profile3 = {
    "your_home": {"people_in_house": 3, "postcode": "1010"},
    "heating": {
        "main_heating_source": "Piped gas heater",
        "alternative_main_heating_source": "Heat pump",
        "heating_during_day": "5-7 days a week",
        "insulation_quality": "Moderately insulated",
    },
    "hot_water": {
        "hot_water_usage": "High",
        "hot_water_heating_source": "Electric hot water cylinder",
        "alternative_hot_water_heating_source": "Electric hot water cylinder",
    },
    "cooktop": {
        "cooktop": "Electric (coil or ceramic)",
        "alternative_cooktop": "Electric induction",
    },
    "driving": {
        "vehicle_size": "Small",
        "km_per_week": "200",
        "vehicle_type": "Petrol",
        "alternative_vehicle_type": "Plug-in hybrid",
    },
    "solar": {"add_solar": True},
}

profile4 = {
    "your_home": {"people_in_house": 3, "postcode": "4277"},
    "heating": {
        "main_heating_source": "Piped gas heater",
        "alternative_main_heating_source": "Heat pump",
        "heating_during_day": "5-7 days a week",
        "insulation_quality": "Moderately insulated",
    },
    "hot_water": {
        "hot_water_usage": "High",
        "hot_water_heating_source": "Electric hot water cylinder",
        "alternative_hot_water_heating_source": "Electric hot water cylinder",
    },
    "cooktop": {
        "cooktop": "Electric (coil or ceramic)",
        "alternative_cooktop": "Electric induction",
    },
    "driving": {
        "vehicle_size": "Small",
        "km_per_week": "200",
        "vehicle_type": "Petrol",
        "alternative_vehicle_type": "Plug-in hybrid",
    },
    "solar": {"add_solar": True},
}

profile5 = {
    "your_home": {"people_in_house": 4, "postcode": "0182"},
    "heating": {
        "main_heating_source": "Piped gas heater",
        "alternative_main_heating_source": "Heat pump",
        "heating_during_day": "3-4 days a week",
        "insulation_quality": "Not well insulated",
    },
    "hot_water": {
        "hot_water_usage": "Low",
        "hot_water_heating_source": "Electric hot water cylinder",
        "alternative_hot_water_heating_source": "Hot water heat pump",
    },
    "cooktop": {
        "cooktop": "Electric (coil or ceramic)",
        "alternative_cooktop": "Electric induction",
    },
    "driving": {
        "vehicle_size": "Medium",
        "km_per_week": "200",
        "vehicle_type": "Petrol",
        "alternative_vehicle_type": "Electric",
    },
    "solar": {"add_solar": True},
}


def compare_api_calculation_with_manual_calculation(
    input_profile: dict,
):
    """
    Compare the API calculation with the manual calculation.
    """
    lookup_tables_path = pkg_resources.files("resources.lookup_tables")

    energy_plan = get_energy_plan(input_profile["your_home"]["postcode"], "Petrol")
    electricity_plan_name = energy_plan.electricity_plan.name
    electricity_plans = pd.read_csv(
        lookup_tables_path / "solar_electricity_plans_lookup_table.csv"
    )
    elx_plan = electricity_plans.set_index("electricity_plan_name").loc[
        electricity_plan_name
    ]
    nzd_per_kwh_day = elx_plan.import_rates_day
    nzd_per_kwh_night = elx_plan.import_rates_night
    nzd_per_kwh_export = elx_plan.import_rates_export
    kg_co2e_per_kwh = elx_plan.kg_co2e_per_kwh

    cz = climate_zone(input_profile["your_home"]["postcode"])
    ppl = input_profile["your_home"]["people_in_house"]
    hwus = input_profile["hot_water"]["hot_water_usage"]
    hw = input_profile["hot_water"]["alternative_hot_water_heating_source"]
    sh = input_profile["heating"]["alternative_main_heating_source"]
    shus = input_profile["heating"]["heating_during_day"]
    ins = input_profile["heating"]["insulation_quality"]
    veh = input_profile["driving"]["alternative_vehicle_type"]
    vsz = input_profile["driving"]["vehicle_size"]
    km = input_profile["driving"]["km_per_week"]
    ct = input_profile["cooktop"]["alternative_cooktop"]

    solar_generation_timeseries = load_lookup_timeseries(
        lookup_tables_path / "solar_generation_lookup_table.csv", f"{cz}"
    )
    print("\nSolar generation:")
    print("Sum of solar_generation_timeseries (kWh):", sum(solar_generation_timeseries))
    print("---------------------------------------------------------")
    hot_water_timeseries = load_lookup_timeseries(
        lookup_tables_path / "solar_hot_water_lookup_table.csv",
        f"{cz},{ppl},{hwus},{hw}",
    )
    space_heating_timeseries = load_lookup_timeseries(
        lookup_tables_path / "solar_space_heating_lookup_table.csv",
        f"{cz},{sh},{shus},{ins}",
    )
    vehicle_charging_timeseries = load_lookup_timeseries(
        lookup_tables_path / "solar_vehicle_lookup_table.csv", f"{veh},{vsz},{km}"
    )
    other_electricity_timeseries = load_lookup_timeseries(
        lookup_tables_path / "solar_other_electricity_usage_lookup_table.csv", ""
    )
    cooktop_timeseries = load_lookup_timeseries(
        lookup_tables_path / "solar_cooktop_lookup_table.csv", f"{ppl},{ct}"
    )

    assert len(solar_generation_timeseries) == 8760
    assert len(hot_water_timeseries) == 8760
    assert len(space_heating_timeseries) == 8760
    assert len(cooktop_timeseries) == 8760
    assert len(vehicle_charging_timeseries) == 8760
    assert len(other_electricity_timeseries) == 8760

    total_inflexible_loads = (
        space_heating_timeseries
        + cooktop_timeseries
        + other_electricity_timeseries
        + (0.2 * hot_water_timeseries)
    )
    total_flexible_loads = (0.8 * hot_water_timeseries) + vehicle_charging_timeseries
    inflexible_self_consumption = np.minimum(
        total_inflexible_loads, solar_generation_timeseries
    )
    residual_solar = solar_generation_timeseries - inflexible_self_consumption
    flexible_self_consumption = np.minimum(total_flexible_loads, residual_solar)

    export_timeseries = np.maximum(0, residual_solar - total_flexible_loads)
    annual_kwh_generated = sum(solar_generation_timeseries)
    annual_kwh_exported = sum(export_timeseries)
    annual_kwh_self_consumed_flexible = sum(flexible_self_consumption)
    annual_kwh_self_consumed_inflexible = sum(inflexible_self_consumption)
    annual_kg_co2e_saving = annual_kwh_generated * kg_co2e_per_kwh
    annual_earnings_solar_export = annual_kwh_exported * nzd_per_kwh_export
    annual_savings_solar_self_consumption = (
        annual_kwh_self_consumed_inflexible * nzd_per_kwh_day
    ) + (annual_kwh_self_consumed_flexible * nzd_per_kwh_night)

    response = client.post("/solar/savings", json=input_profile)
    assert response.status_code == 200

    response_data = response.json()

    assert response_data["annual_kwh_generated"] == approx(
        annual_kwh_generated, rel=1e-4
    )
    assert response_data["annual_earnings_solar_export"] == approx(
        annual_earnings_solar_export, rel=1e-4
    )
    assert response_data["annual_savings_solar_self_consumption"] == approx(
        annual_savings_solar_self_consumption, rel=1e-4
    )
    assert response_data["annual_kg_co2e_saving"] == approx(
        annual_kg_co2e_saving, rel=1e-4
    )


@pytest.mark.skipif(
    os.environ.get("LOCAL_SOLAR_DATA", "True") != "True",
    reason="Skipping solar test because local lookup table data is unavailable.",
)
@pytest.mark.parametrize(
    "input_profile", [profile0, profile1, profile2, profile3, profile4, profile5]
)
def test_api_solar_calculation(input_profile):
    """
    Parametrized test function that checks
    the solar generation calculation for several profiles.
    """
    compare_api_calculation_with_manual_calculation(input_profile)
