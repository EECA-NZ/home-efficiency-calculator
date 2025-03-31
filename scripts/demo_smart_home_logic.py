"""
Solar generation calculation of solar self-consumption
vs export for various input profiles. Starting point.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from app.services.get_climate_zone import climate_zone
from app.services.get_energy_plans import get_energy_plan
from app.services.helpers import load_lookup_timeseries

profile = {
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
    "user_decisions": {"fixed_cost_changes": True, "adding_solar": True},
}

profile = {
    "your_home": {"people_in_house": 4, "postcode": "2471"},
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
    "user_decisions": {"fixed_cost_changes": True, "adding_solar": True},
}

lookup_tables_path = Path("../resources/lookup_tables")

energy_plan = get_energy_plan(profile["your_home"]["postcode"], "Petrol")
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

print("\nClimate zone:")
print(climate_zone(profile["your_home"]["postcode"]))

print("\nElectricity plan:")
print("Electricity plan name:", electricity_plan_name)
print("NZ$ per kWh (day):", nzd_per_kwh_day)
print("NZ$ per kWh (night):", nzd_per_kwh_night)
print("NZ$ per kWh (export):", nzd_per_kwh_export)
print("kg CO2e per kWh:", kg_co2e_per_kwh)

CZ = climate_zone(profile["your_home"]["postcode"])
PPL = profile["your_home"]["people_in_house"]
HWUS = profile["hot_water"]["hot_water_usage"]
HW = profile["hot_water"]["alternative_hot_water_heating_source"]
SH = profile["heating"]["alternative_main_heating_source"]
SHUS = profile["heating"]["heating_during_day"]
INS = profile["heating"]["insulation_quality"]
VEH = profile["driving"]["alternative_vehicle_type"]
VSZ = profile["driving"]["vehicle_size"]
KM = profile["driving"]["km_per_week"]
CT = profile["cooktop"]["alternative_cooktop"]

solar_generation_timeseries = load_lookup_timeseries(
    lookup_tables_path / "solar_generation_lookup_table.csv", f"{CZ}"
)
hot_water_timeseries = load_lookup_timeseries(
    lookup_tables_path / "solar_hot_water_lookup_table.csv",
    f"{CZ},{PPL},{HWUS},{HW}",
)
space_heating_timeseries = load_lookup_timeseries(
    lookup_tables_path / "solar_space_heating_lookup_table.csv",
    f"{CZ},{SH},{SHUS},{INS}",
)
vehicle_charging_timeseries = load_lookup_timeseries(
    lookup_tables_path / "solar_vehicle_lookup_table.csv", f"{VEH},{VSZ},{KM}"
)
other_electricity_timeseries = load_lookup_timeseries(
    lookup_tables_path / "solar_other_electricity_usage_lookup_table.csv", ""
)
cooktop_timeseries = load_lookup_timeseries(
    lookup_tables_path / "solar_cooktop_lookup_table.csv", f"{PPL},{CT}"
)

assert len(solar_generation_timeseries) == 8760
assert len(hot_water_timeseries) == 8760
assert len(space_heating_timeseries) == 8760
assert len(cooktop_timeseries) == 8760
assert len(vehicle_charging_timeseries) == 8760
assert len(other_electricity_timeseries) == 8760

print("\nSolar generation:")
print("Sum of solar_generation_timeseries (kWh):", sum(solar_generation_timeseries))
print("---------------------------------------------------------")

total_inflexible_loads = (
    space_heating_timeseries
    + cooktop_timeseries
    + other_electricity_timeseries
    + 0.2 * hot_water_timeseries
)
total_flexible_loads = 0.8 * hot_water_timeseries + vehicle_charging_timeseries

print("\nInflexible loads:")
print("Sum of space_heating_timeseries (kWh):", sum(space_heating_timeseries))
print("Sum of cooktop_timeseries (kWh):", sum(cooktop_timeseries))
print("Sum of other_electricity_timeseries (kWh):", sum(other_electricity_timeseries))
print("---------------------------------------------------------")
print("Sum of total_inflexible_loads (kWh):", sum(total_inflexible_loads))

print("\nFlexible loads:")
print("Sum of hot_water_timeseries (kWh):", sum(hot_water_timeseries))
print("Sum of vehicle_charging_timeseries (kWh):", sum(vehicle_charging_timeseries))
print("---------------------------------------------------------")
print("Sum of total_flexible_loads (kWh):", sum(total_flexible_loads))

inflexible_self_consumption = np.minimum(
    total_inflexible_loads, solar_generation_timeseries
)
print("\nInflexible self-consumption (kWh):")
print("Sum of inflexible_self_consumption (kWh):", sum(inflexible_self_consumption))

residual_solar = solar_generation_timeseries - inflexible_self_consumption
flexible_self_consumption = np.minimum(total_flexible_loads, residual_solar)
print("\nFlexible self-consumption (kWh):")
print("Sum of flexible_self_consumption (kWh):", sum(flexible_self_consumption))

total_self_consumption_timeseries = (
    inflexible_self_consumption + flexible_self_consumption
)
print("\nTotal self-consumption (kWh):")
print(
    "Sum of total_self_consumption_timeseries (kWh):",
    sum(total_self_consumption_timeseries),
)

export_timeseries = np.maximum(0, residual_solar - total_flexible_loads)
print("\nExport:")
print("Sum of export_timeseries (kWh):", sum(export_timeseries))

annual_kwh_generated = sum(solar_generation_timeseries)
annual_kwh_exported = sum(export_timeseries)
annual_kwh_self_consumed_flexible = sum(flexible_self_consumption)
annual_kwh_self_consumed_inflexible = sum(inflexible_self_consumption)

annual_kg_co2e_saving = annual_kwh_generated * kg_co2e_per_kwh
annual_earnings_solar_export = annual_kwh_exported * nzd_per_kwh_export
annual_savings_solar_self_consumption = (
    annual_kwh_self_consumed_inflexible * nzd_per_kwh_day
) + (annual_kwh_self_consumed_flexible * nzd_per_kwh_night)

print("\nAnnual totals:")
print("---------------------------------------------------------")
print("Annual kWh generated:", annual_kwh_generated)
print("Annual kWh exported:", annual_kwh_exported)
print("Annual kWh self-consumed (flexible):", annual_kwh_self_consumed_flexible)
print("Annual kWh self-consumed (inflexible):", annual_kwh_self_consumed_inflexible)
print("---------------------------------------------------------")

print("\nAnnual savings:")
print("---------------------------------------------------------")
print("Annual NZ$ earnings from solar export:", annual_earnings_solar_export)
print(
    "Annual NZ$ savings from solar self-consumption:",
    annual_savings_solar_self_consumption,
)
print("Annual kg CO2e saving:", annual_kg_co2e_saving)
print("---------------------------------------------------------")
