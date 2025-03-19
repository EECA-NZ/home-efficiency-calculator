"""
Test solar generation calculation of solar self-consumption
vs export for various input profiles. Starting point.
"""

import numpy as np
import pandas as pd
from pytest import approx

# pylint: disable=fixme, too-many-locals


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


profile1 = {
    "your_home": {"people_in_house": 4, "postcode": "6012", "disconnect_gas": True},
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


def compare_api_calculation_with_manual_calculation(
    input_profile: dict, expected_values: dict
):
    """
    Compare the API calculation with the manual calculation.
    """

    _ = (input_profile, expected_values)

    ##########################################
    # TODO: load these from ..\..\lookup\solar_electricity_plans_lookup_table.csv
    kg_co2e_per_kwh = 0.1072
    nzd_per_kwh_export = 0.12
    nzd_per_kwh_day = 0.21229
    ##########################################

    ##########################################
    # TODO: determine match strings from input_profile dict.
    solar_generation_timeseries = load_lookup_timeseries(
        "../../lookup/solar_generation_lookup_table.csv", "Wellington"
    )
    hot_water_timeseries = load_lookup_timeseries(
        "../../lookup/solar_hot_water_lookup_table.csv",
        "Wellington,4,High,Hot water heat pump",
    )
    space_heating_timeseries = load_lookup_timeseries(
        "../../lookup/solar_space_heating_lookup_table.csv",
        "Wellington,Heat pump,3-4 days a week,Not well insulated",
    )
    vehicle_charging_timeseries = load_lookup_timeseries(
        "../../lookup/solar_vehicle_lookup_table.csv", "Electric,Small,200"
    )
    other_electricity_timeseries = load_lookup_timeseries(
        "../../lookup/solar_other_electricity_usage_lookup_table.csv", ""
    )
    cooktop_timeseries = load_lookup_timeseries(
        "../../lookup/solar_cooktop_lookup_table.csv", "4,Electric induction"
    )
    ##########################################

    assert len(solar_generation_timeseries) == 8760
    assert len(hot_water_timeseries) == 8760
    assert len(space_heating_timeseries) == 8760
    assert len(cooktop_timeseries) == 8760
    assert len(vehicle_charging_timeseries) == 8760
    assert len(other_electricity_timeseries) == 8760

    total_kwh_timeseries = (
        hot_water_timeseries
        + space_heating_timeseries
        + cooktop_timeseries
        + vehicle_charging_timeseries
        + other_electricity_timeseries
    )

    export_timeseries = np.maximum(
        0, solar_generation_timeseries - total_kwh_timeseries
    )
    self_consumption_timeseries = solar_generation_timeseries - export_timeseries
    grid_purchase_timeseries = total_kwh_timeseries - self_consumption_timeseries

    annual_kwh_generated = sum(solar_generation_timeseries)
    annual_kwh_exported = sum(export_timeseries)
    annual_kwh_imported = sum(grid_purchase_timeseries)
    annual_kwh_self_consumed = sum(self_consumption_timeseries)

    annual_kg_co2e_saving = annual_kwh_generated * kg_co2e_per_kwh
    annual_savings_solar_export = annual_kwh_exported * nzd_per_kwh_export
    annual_savings_solar_self_consumption = annual_kwh_self_consumed * nzd_per_kwh_day

    ##########################################
    # TODO: determine the expected values from the expected_values dict.
    assert total_kwh_timeseries.sum() == approx(6785.70)
    assert solar_generation_timeseries.sum() == approx(6779.137959)

    assert (self_consumption_timeseries + grid_purchase_timeseries).sum() == approx(
        6785.70
    )
    assert (export_timeseries + self_consumption_timeseries).sum() == approx(6779.14)

    assert (annual_kwh_self_consumed + annual_kwh_imported) == approx(6785.70)
    assert (annual_kwh_exported + annual_kwh_self_consumed) == approx(6779.14)

    assert annual_kg_co2e_saving == approx(726.72356)
    assert annual_savings_solar_export == approx(466.22422)
    assert annual_savings_solar_self_consumption == approx(614.35366)
    ##########################################
