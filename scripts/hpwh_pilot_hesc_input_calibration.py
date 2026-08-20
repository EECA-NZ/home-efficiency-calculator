"""
Calibrate HPWH tuning parameters against the HESC-input pilot benchmark.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import statistics
from dataclasses import dataclass
from pathlib import Path

from app.constants import DAYS_IN_YEAR
from app.constants.hot_water_energy import (
    AIR_TO_AIR_HEAT_PUMP_COP_BY_CLIMATE_ZONE,
    AVERAGE_AIR_TEMPERATURE_BY_CLIMATE_ZONE,
    HEAT_PUMP_WATER_CYLINDER_SIZES,
    HOT_WATER_HEAT_PUMP_COP_BY_CLIMATE_ZONE,
    HPWH_BASELINE_COP,
    HPWH_BASELINE_CYLINDER_HEAT_LOSS_KWH_PER_DAY_BY_TANK_SIZE,
    HPWH_CLIMATE_COP_DERATE_FACTOR,
    HPWH_OUTDOOR_FITTINGS_HEAT_LOSS_MULTIPLIER,
    HPWH_REFERENCE_CLIMATE_ZONE,
    OTHER_WATER_USAGE_QUANTITIES,
    SHOWER_WATER_USAGE_QUANTITIES,
    TANK_SIZE_BY_HOUSEHOLD_SIZE,
    parameterized_hpwh_cop_from_air_to_air_climate_cop,
)
from app.services.usage_calculation.hot_water_helpers import (
    hpwh_standing_loss_with_fittings_multiplier,
    other_water_kwh_per_year,
    shower_kwh_per_year,
    standing_loss_kwh_per_year,
)

DEFAULT_COMPARISON_CSV_PATH = Path("/tmp/hpwh_pilot_hesc_input_comparison.csv")
DEFAULT_PLOT_DIR = DEFAULT_COMPARISON_CSV_PATH.parent
USAGE_BUCKET_ORDER = ["Low", "Average", "High"]
USAGE_SCENARIO_LABELS = {
    "Low": "Small",
    "Average": "Medium",
    "High": "Large",
}
PILOT_CSV_PATH = (
    Path(__file__).resolve().parents[1]
    / "resources"
    / "hpwh_pilot"
    / "overall_cop_with_site_details_interim.csv"
)
OBSERVED_COP_OUTLIER_THRESHOLD = 5.0
DEFAULT_MIN_DAYS_WITH_DATA = 270.0
VALID_PEOPLE_IN_HOUSE = {1, 2, 3, 4, 5, 6}
TARGET_REFRIGERANT = "R290"
TARGET_SYSTEM_TYPE = "Integral"
VALID_INSTALL_LOCATIONS = {"", "Outdoor"}
LEGACY_HPWH_COP_BY_CLIMATE_ZONE = {
    "Northland": 4.12,
    "Auckland": 4.12,
    "Hamilton": 3.60,
    "Bay of Plenty": 3.99,
    "Rotorua": 3.55,
    "Taupo": 3.24,
    "New Plymouth": 3.93,
    "East Coast": 3.76,
    "Manawatu": 3.84,
    "Wairarapa": 3.33,
    "Wellington": 4.15,
    "Nelson-Marlborough": 3.72,
    "West Coast": 3.69,
    "Christchurch": 3.29,
    "Queenstown-Lakes": 3.01,
    "Central Otago": 2.76,
    "Dunedin": 3.88,
    "Invercargill": 3.59,
    "Unknown": 3.0,
}


@dataclass(frozen=True)
# pylint: disable=too-many-instance-attributes
class PilotSite:
    """
    Filtered pilot-site record with both measured and derived fields.
    """

    pilot_site_id: str
    zone: str
    people: int
    days_with_data: float
    water_l: float
    daily_avg_water_l: float
    hot_outlet_c: float
    cold_inlet_c: float
    ambient_c: float
    climate_zone: str
    tank_volume_l: float
    ua_w_per_k: float
    observed_cop: float
    usage_bucket: str


@dataclass(frozen=True)
class TuningParameters:
    """
    Tunable HPWH model parameters.
    """

    reference_cop: float
    climate_cop_derate_factor: float
    fittings_multiplier: float


LEGACY_REFERENCE_COP = LEGACY_HPWH_COP_BY_CLIMATE_ZONE[HPWH_REFERENCE_CLIMATE_ZONE]
LEGACY_TUNING_PARAMETERS = TuningParameters(
    reference_cop=LEGACY_REFERENCE_COP,
    climate_cop_derate_factor=1.0,
    fittings_multiplier=1.0,
)
MODEL_DEFAULT_TUNING_PARAMETERS = TuningParameters(
    reference_cop=HPWH_BASELINE_COP,
    climate_cop_derate_factor=HPWH_CLIMATE_COP_DERATE_FACTOR,
    fittings_multiplier=HPWH_OUTDOOR_FITTINGS_HEAT_LOSS_MULTIPLIER,
)


def parse_grid(grid_spec: str) -> list[float]:
    """
    Parse an inclusive numeric grid from ``start:stop:step``.
    """
    start, stop, step = (float(part) for part in grid_spec.split(":"))
    values = []
    current = start
    while current <= stop + (step / 10):
        values.append(round(current, 10))
        current += step
    return values


def daily_water_litres_for_usage_bucket(usage_bucket: str, people: int) -> float:
    """
    Return modeled daily water use for one HESC usage bucket.
    """
    shower = SHOWER_WATER_USAGE_QUANTITIES[usage_bucket]
    shower_litres = (
        shower["flow_rate_l_per_min"]
        * shower["duration_min"]
        * shower["showers_per_week"]
        / 7
        * people
    )
    other_litres = (
        OTHER_WATER_USAGE_QUANTITIES["Washing Machine"]["volume_l_per_day"]
        + OTHER_WATER_USAGE_QUANTITIES["Tap"]["volume_l_per_day"]
        + OTHER_WATER_USAGE_QUANTITIES["High Flow/Outdoor"]["volume_l_per_day"]
    ) * people
    return shower_litres + other_litres


def nearest_usage_bucket(daily_avg_water_l: float, people: int) -> str:
    """
    Assign the nearest HESC usage bucket by daily water draw.
    """
    return min(
        SHOWER_WATER_USAGE_QUANTITIES,
        key=lambda usage: abs(
            daily_water_litres_for_usage_bucket(usage, people) - daily_avg_water_l
        ),
    )


def load_pilot_sites(
    observed_cop_field: str,
    min_days_with_data: float = DEFAULT_MIN_DAYS_WITH_DATA,
) -> list[PilotSite]:
    """
    Load sanitized pilot rows and apply the standard row filter.
    """
    sites = []
    with PILOT_CSV_PATH.open(encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            if not row["number_of_people"]:
                continue
            if row["refrigerant"].strip().upper() != TARGET_REFRIGERANT:
                continue
            if row["new_system_type"].strip() != TARGET_SYSTEM_TYPE:
                continue
            if (
                row["new_system_indoor_or_outdoor"].strip()
                not in VALID_INSTALL_LOCATIONS
            ):
                continue
            people = int(row["number_of_people"])
            if people not in VALID_PEOPLE_IN_HOUSE:
                continue
            climate_zone = row["niwa_climate_zone"]
            if climate_zone not in AVERAGE_AIR_TEMPERATURE_BY_CLIMATE_ZONE:
                continue
            observed_cop = float(row[observed_cop_field])
            if not 0 < observed_cop < OBSERVED_COP_OUTLIER_THRESHOLD:
                continue
            days_with_data = float(row["days_with_data"])
            if days_with_data < min_days_with_data:
                continue
            daily_avg_water_l = float(row["daily_avg_water_l"])
            sites.append(
                PilotSite(
                    pilot_site_id=row["pilot_site_id"],
                    zone=row["zone"],
                    people=people,
                    days_with_data=days_with_data,
                    water_l=float(row["water_l"]),
                    daily_avg_water_l=daily_avg_water_l,
                    hot_outlet_c=float(row["avg_hot_outlet_c_corrected"]),
                    cold_inlet_c=float(row["avg_cold_inlet_c_corrected"]),
                    ambient_c=float(row["ambient_temperature_c_system_on"]),
                    climate_zone=climate_zone,
                    tank_volume_l=float(row["tank_volume_l"]),
                    ua_w_per_k=float(row["ua_from_as_nzs_4692_w_per_k"]),
                    observed_cop=observed_cop,
                    usage_bucket=nearest_usage_bucket(daily_avg_water_l, people),
                )
            )
    return sites


def hesc_input_component_cop(climate_zone: str, params: TuningParameters) -> float:
    """
    Predict HPWH component COP from app-style climate information only.
    """
    reference_air_to_air_heat_pump_cop = AIR_TO_AIR_HEAT_PUMP_COP_BY_CLIMATE_ZONE[
        HPWH_REFERENCE_CLIMATE_ZONE
    ]
    return parameterized_hpwh_cop_from_air_to_air_climate_cop(
        air_to_air_heat_pump_cop=AIR_TO_AIR_HEAT_PUMP_COP_BY_CLIMATE_ZONE[climate_zone],
        reference_air_to_air_heat_pump_cop=reference_air_to_air_heat_pump_cop,
        baseline_hpwh_cop=params.reference_cop,
        climate_cop_derate_factor=params.climate_cop_derate_factor,
    )


def hesc_input_standing_loss_kwh(people: int, fittings_multiplier: float) -> float:
    """
    Predict standing loss from app-style household-size tank assumptions only.
    """
    tank_size = HEAT_PUMP_WATER_CYLINDER_SIZES[TANK_SIZE_BY_HOUSEHOLD_SIZE[people]]
    return (
        hpwh_standing_loss_with_fittings_multiplier(
            baseline_cylinder_heat_loss_kwh_per_day=(
                HPWH_BASELINE_CYLINDER_HEAT_LOSS_KWH_PER_DAY_BY_TANK_SIZE[tank_size]
            ),
            fittings_heat_loss_multiplier=fittings_multiplier,
        )
        * DAYS_IN_YEAR
    )


def hesc_input_predicted_cop(
    climate_zone: str,
    people: int,
    usage_bucket: str,
    params: TuningParameters,
) -> float:
    """
    Predict final COP from production-style proxy inputs only.
    """
    delivered_kwh = shower_kwh_per_year(usage_bucket, climate_zone, people) + (
        other_water_kwh_per_year(climate_zone, people)
    )
    standing_loss_kwh = hesc_input_standing_loss_kwh(
        people,
        params.fittings_multiplier,
    )
    component_cop = hesc_input_component_cop(climate_zone, params)
    return delivered_kwh / ((delivered_kwh + standing_loss_kwh) / component_cop)


def legacy_hesc_input_predicted_cop(
    climate_zone: str, people: int, usage_bucket: str
) -> float:
    """
    Predict final COP using the pre-branch settings.
    """
    delivered_kwh = shower_kwh_per_year(usage_bucket, climate_zone, people) + (
        other_water_kwh_per_year(climate_zone, people)
    )
    standing_loss_kwh = hesc_input_standing_loss_kwh(people, 1.0)
    component_cop = LEGACY_HPWH_COP_BY_CLIMATE_ZONE[climate_zone]
    return delivered_kwh / ((delivered_kwh + standing_loss_kwh) / component_cop)


def default_hesc_input_predicted_cop(
    climate_zone: str,
    people: int,
    usage_bucket: str,
) -> float:
    """
    Predict final COP using the checked-in branch settings.
    """
    delivered_kwh = shower_kwh_per_year(usage_bucket, climate_zone, people) + (
        other_water_kwh_per_year(climate_zone, people)
    )
    standing_loss_kwh = standing_loss_kwh_per_year(
        "Hot water heat pump",
        people,
        climate_zone,
    )
    component_cop = HOT_WATER_HEAT_PUMP_COP_BY_CLIMATE_ZONE[climate_zone]
    return delivered_kwh / ((delivered_kwh + standing_loss_kwh) / component_cop)


def hesc_input_site_mae(
    sites,
    params: TuningParameters,
) -> float:
    """
    Compute plain site-level MAE on the HESC-input benchmark.
    """
    return statistics.mean(
        abs(
            site.observed_cop
            - hesc_input_predicted_cop(
                site.climate_zone,
                site.people,
                site.usage_bucket,
                params,
            )
        )
        for site in sites
    )


def hesc_input_stratum_mae(
    sites,
    params: TuningParameters,
) -> float:
    """
    Compute equal-weight MAE across observed climate-zone and usage strata.
    """
    errors_by_stratum: dict[tuple[str, str], list[float]] = {}
    for site in sites:
        prediction = hesc_input_predicted_cop(
            site.climate_zone,
            site.people,
            site.usage_bucket,
            params,
        )
        key = (site.climate_zone, site.usage_bucket)
        errors_by_stratum.setdefault(key, []).append(
            abs(site.observed_cop - prediction)
        )
    return statistics.mean(
        statistics.mean(errors) for errors in errors_by_stratum.values()
    )


def calibrate_parameters(
    sites,
    reference_cop_values: list[float],
    derating_values: list[float],
    fittings_multiplier_values: list[float],
    objective: str,
) -> tuple[TuningParameters, float]:
    """
    Brute-force search for the best HESC-input MAE under one objective.
    """
    objective_functions = {
        "site": hesc_input_site_mae,
        "stratum": hesc_input_stratum_mae,
    }
    objective_function = objective_functions[objective]
    best_params = None
    best_score = None
    for reference_cop in reference_cop_values:
        for climate_cop_derate_factor in derating_values:
            for fittings_multiplier in fittings_multiplier_values:
                params = TuningParameters(
                    reference_cop=reference_cop,
                    climate_cop_derate_factor=climate_cop_derate_factor,
                    fittings_multiplier=fittings_multiplier,
                )
                score = objective_function(sites, params)
                if best_score is None or score < best_score:
                    best_params = params
                    best_score = score
    if best_params is None or best_score is None:
        raise ValueError("At least one parameter combination is required.")
    return best_params, best_score


def prediction_rows(
    sites,
    optimized_params: TuningParameters,
) -> list[dict[str, float | int | str]]:
    """
    Build per-site prediction rows for legacy, default, and optimized models.
    """
    rows = []
    for site in sites:
        legacy_prediction = legacy_hesc_input_predicted_cop(
            site.climate_zone,
            site.people,
            site.usage_bucket,
        )
        default_prediction = default_hesc_input_predicted_cop(
            site.climate_zone,
            site.people,
            site.usage_bucket,
        )
        optimized_prediction = hesc_input_predicted_cop(
            site.climate_zone,
            site.people,
            site.usage_bucket,
            optimized_params,
        )
        rows.append(
            {
                "pilot_site_id": site.pilot_site_id,
                "pilot_zone": site.zone,
                "niwa_climate_zone": site.climate_zone,
                "people": site.people,
                "usage_bucket": site.usage_bucket,
                "observed_cop": site.observed_cop,
                "legacy_hesc_input_prediction": legacy_prediction,
                "default_hesc_input_prediction": default_prediction,
                "optimized_hesc_input_prediction": optimized_prediction,
                "legacy_hesc_input_error": legacy_prediction - site.observed_cop,
                "default_hesc_input_error": default_prediction - site.observed_cop,
                "optimized_hesc_input_error": (
                    optimized_prediction - site.observed_cop
                ),
            }
        )
    return rows


def mean_or_none(values: list[float]) -> float | None:
    """
    Return the mean of a non-empty list, otherwise None.
    """
    if not values:
        return None
    return statistics.mean(values)


def format_optional_cop(value: float | None) -> str:
    """
    Format a COP value for the screen summary table.
    """
    if value is None:
        return "-"
    return f"{value:.3f}"


def format_optional_percent(value: float | None) -> str:
    """
    Format a percentage value for the screen summary table.
    """
    if value is None:
        return "-"
    return f"{value:.1%}"


def model_metrics(
    rows: list[dict[str, float | int | str]],
    prediction_column: str,
) -> tuple[float, float, float, float, float]:
    """
    Return observed mean, predicted mean, bias, MAE, and RMSE for one model.
    """
    observed_values = [float(row["observed_cop"]) for row in rows]
    prediction_values = [float(row[prediction_column]) for row in rows]
    errors = [
        prediction - observed
        for prediction, observed in zip(prediction_values, observed_values)
    ]
    return (
        statistics.mean(observed_values),
        statistics.mean(prediction_values),
        statistics.mean(errors),
        statistics.mean(abs(error) for error in errors),
        math.sqrt(statistics.mean(error**2 for error in errors)),
    )


def print_model_metrics_table(
    rows: list[dict[str, float | int | str]],
    optimized_params: TuningParameters,
) -> None:
    """
    Print overall model-performance metrics for each coefficient set.
    """
    model_specs = [
        ("legacy", LEGACY_TUNING_PARAMETERS, "legacy_hesc_input_prediction"),
        ("default", MODEL_DEFAULT_TUNING_PARAMETERS, "default_hesc_input_prediction"),
        ("optimized", optimized_params, "optimized_hesc_input_prediction"),
    ]
    print("Overall COP performance by coefficient set")
    print(
        f"{'model':<10}  {'ref_cop':>7}  {'derate':>7}  {'fittings':>8}  "
        f"{'obs_avg':>8}  {'calc_avg':>8}  {'bias':>8}  {'mae':>8}  {'rmse':>8}"
    )
    for label, params, prediction_column in model_specs:
        observed_mean, predicted_mean, bias, mae, rmse = model_metrics(
            rows,
            prediction_column,
        )
        print(
            f"{label:<10}  {params.reference_cop:>7.2f}  "
            f"{params.climate_cop_derate_factor:>7.2f}  "
            f"{params.fittings_multiplier:>8.2f}  "
            f"{observed_mean:>8.3f}  {predicted_mean:>8.3f}  "
            f"{bias:>8.3f}  {mae:>8.3f}  {rmse:>8.3f}"
        )


def print_average_cop_table(rows: list[dict[str, float | int | str]]) -> None:
    """
    Print average observed and predicted COP by climate zone and usage scenario.
    """
    climate_zones = sorted({str(row["niwa_climate_zone"]) for row in rows})
    print("Average COP by NIWA climate zone and HESC usage scenario")
    print(
        f"{'climate_zone':<20}  {'usage':<8}  {'n':>3}  "
        f"{'observed':>8}  {'legacy':>8}  {'default':>8}  "
        f"{'optimized':>10}  {'%Δ leg->def':>13}"
    )
    for climate_zone in climate_zones:
        for usage_bucket in USAGE_BUCKET_ORDER:
            stratum_rows = [
                row
                for row in rows
                if row["niwa_climate_zone"] == climate_zone
                and row["usage_bucket"] == usage_bucket
            ]
            observed_mean = mean_or_none(
                [float(row["observed_cop"]) for row in stratum_rows]
            )
            legacy_mean = mean_or_none(
                [float(row["legacy_hesc_input_prediction"]) for row in stratum_rows]
            )
            default_mean = mean_or_none(
                [float(row["default_hesc_input_prediction"]) for row in stratum_rows]
            )
            optimized_mean = mean_or_none(
                [float(row["optimized_hesc_input_prediction"]) for row in stratum_rows]
            )
            default_cop_delta = None
            if legacy_mean and default_mean:
                default_cop_delta = default_mean / legacy_mean - 1
            print(
                f"{climate_zone:<20}  {USAGE_SCENARIO_LABELS[usage_bucket]:<8}  "
                f"{len(stratum_rows):>3}  {format_optional_cop(observed_mean):>8}  "
                f"{format_optional_cop(legacy_mean):>8}  "
                f"{format_optional_cop(default_mean):>8}  "
                f"{format_optional_cop(optimized_mean):>10}  "
                f"{format_optional_percent(default_cop_delta):>13}"
            )


def print_representative_hesc_input_cop_table(
    optimized_params: TuningParameters,
) -> None:
    """
    Print legacy/default/optimized COP for representative HESC input scenarios.
    """
    scenarios = [
        (2, "Low"),
        (4, "Average"),
        (6, "High"),
    ]
    climate_zones = list(AIR_TO_AIR_HEAT_PUMP_COP_BY_CLIMATE_ZONE)
    print("Representative HESC-input effective COP")
    print(
        f"{'climate_zone':<20}  {'people':>6}  {'usage':<8}  "
        f"{'legacy':>8}  {'default':>8}  {'optimized':>10}  {'%Δ leg->def':>13}"
    )
    for climate_zone in climate_zones:
        for people, usage_bucket in scenarios:
            legacy_cop = legacy_hesc_input_predicted_cop(
                climate_zone,
                people,
                usage_bucket,
            )
            default_cop = default_hesc_input_predicted_cop(
                climate_zone,
                people,
                usage_bucket,
            )
            optimized_cop = hesc_input_predicted_cop(
                climate_zone,
                people,
                usage_bucket,
                optimized_params,
            )
            default_cop_delta = default_cop / legacy_cop - 1
            print(
                f"{climate_zone:<20}  {people:>6}  "
                f"{USAGE_SCENARIO_LABELS[usage_bucket]:<8}  "
                f"{legacy_cop:>8.3f}  {default_cop:>8.3f}  "
                f"{optimized_cop:>10.3f}  "
                f"{default_cop_delta:>13.1%}"
            )


def write_comparison_csv(rows: list[dict[str, float | int | str]], output_path: Path):
    """
    Write the per-site legacy/default/optimized comparison CSV.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_observed_scatter_plot(
    rows: list[dict[str, float | int | str]],
    prediction_column: str,
    title: str,
    output_path: Path,
) -> None:
    """
    Write a calculated-vs-observed COP scatter plot.
    """
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-cache")
    # pylint: disable=import-outside-toplevel
    import matplotlib.pyplot as plt

    observed_values = [float(row["observed_cop"]) for row in rows]
    prediction_values = [float(row[prediction_column]) for row in rows]
    axis_min = min(observed_values + prediction_values)
    axis_max = max(observed_values + prediction_values)
    axis_padding = (axis_max - axis_min) * 0.05
    axis_min -= axis_padding
    axis_max += axis_padding

    output_path.parent.mkdir(parents=True, exist_ok=True)
    _, axis = plt.subplots(figsize=(6, 6))
    axis.scatter(observed_values, prediction_values, alpha=0.75, edgecolors="none")
    axis.plot([axis_min, axis_max], [axis_min, axis_max], color="black", linewidth=1)
    axis.set_xlim(axis_min, axis_max)
    axis.set_ylim(axis_min, axis_max)
    axis.set_xlabel("Observed COP")
    axis.set_ylabel("Calculated COP")
    axis.set_title(title)
    axis.grid(True, linewidth=0.4, alpha=0.4)
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def write_observed_scatter_plots(
    rows: list[dict[str, float | int | str]],
    output_dir: Path,
) -> list[Path]:
    """
    Write legacy/default/optimized calculated-vs-observed scatter plots.
    """
    plot_specs = [
        (
            "legacy_hesc_input_prediction",
            "Legacy HESC-input COP vs observed",
            "hpwh_pilot_hesc_input_legacy_vs_observed.png",
        ),
        (
            "default_hesc_input_prediction",
            "Default HESC-input COP vs observed",
            "hpwh_pilot_hesc_input_default_vs_observed.png",
        ),
        (
            "optimized_hesc_input_prediction",
            "Optimized HESC-input COP vs observed",
            "hpwh_pilot_hesc_input_optimized_vs_observed.png",
        ),
    ]
    output_paths = []
    for prediction_column, title, filename in plot_specs:
        output_path = output_dir / filename
        write_observed_scatter_plot(rows, prediction_column, title, output_path)
        output_paths.append(output_path)
    return output_paths


def main() -> None:
    """
    Run the HESC-input calibration analysis.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reference-cop-grid",
        default="2.5:4.5:0.05",
        help="Inclusive grid for reference COP as start:stop:step.",
    )
    parser.add_argument(
        "--derating-grid",
        default="0.5:1.0:0.05",
        help="Inclusive grid for climate derating coefficient as start:stop:step.",
    )
    parser.add_argument(
        "--fittings-multiplier-grid",
        default="1.0:5.0:0.1",
        help="Inclusive grid for fittings multiplier as start:stop:step.",
    )
    parser.add_argument(
        "--comparison-csv",
        default=str(DEFAULT_COMPARISON_CSV_PATH),
        help="Path for the per-site legacy/default/optimized comparison CSV.",
    )
    parser.add_argument(
        "--plot-dir",
        default=str(DEFAULT_PLOT_DIR),
        help="Directory for legacy/default/optimized calculated-vs-observed PNG plots.",
    )
    parser.add_argument(
        "--min-days-with-data",
        type=float,
        default=DEFAULT_MIN_DAYS_WITH_DATA,
        help="Minimum metered days required for a pilot site to be included.",
    )
    args = parser.parse_args()

    all_duration_sites = load_pilot_sites("cop_period", min_days_with_data=0)
    sites = load_pilot_sites("cop_period", min_days_with_data=args.min_days_with_data)
    reference_cop_values = parse_grid(args.reference_cop_grid)
    derating_values = parse_grid(args.derating_grid)
    fittings_multiplier_values = parse_grid(args.fittings_multiplier_grid)
    optimized_params, _optimized_mae = calibrate_parameters(
        sites,
        reference_cop_values,
        derating_values,
        fittings_multiplier_values,
        "stratum",
    )
    comparison_csv_path = Path(args.comparison_csv)
    rows = prediction_rows(sites, optimized_params)
    write_comparison_csv(
        rows,
        comparison_csv_path,
    )
    plot_paths = write_observed_scatter_plots(rows, Path(args.plot_dir))

    print(
        f"Filtered pilot sites: {len(sites)} "
        f"of {len(all_duration_sites)} with at least "
        f"{args.min_days_with_data:g} days of data"
    )
    print(
        "NIWA climate zones: "
        f"{', '.join(sorted({site.climate_zone for site in sites}))}"
    )
    print()
    print(f"optimized_params={optimized_params}")
    print()
    print_model_metrics_table(rows, optimized_params)
    print()
    print_average_cop_table(rows)
    print()
    print_representative_hesc_input_cop_table(optimized_params)
    print()
    print(f"Per-site comparison written to {comparison_csv_path}")
    print("Scatter plots written to:")
    for plot_path in plot_paths:
        print(f"- {plot_path}")


if __name__ == "__main__":
    main()
