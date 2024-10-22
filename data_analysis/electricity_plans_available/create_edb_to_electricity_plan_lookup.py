"""
Functions relating to spatial data. Map postcodes to climate zones and EDB zones.
"""

import importlib.resources as pkg_resources

import numpy as np
import pandas as pd

from app.services.configuration import get_default_plans
from app.services.helpers import add_gst
from data_analysis.electricity_plans_available.electricity_plans_analysis import (
    get_filtered_df,
    row_to_plan,
)

filtered_plans_stub = pd.DataFrame(
    {"PlanId": [], "Daily charge": [], "nzd_per_kwh": []}
)

postcode_to_edb_csv_path = (
    pkg_resources.files("data_analysis.postcode_lookup_tables.output")
    / "postcode_to_edb_region.csv"
)
with postcode_to_edb_csv_path.open("r", encoding="utf-8") as csv_file:
    postcode_to_edb = pd.read_csv(csv_file, dtype=str)

selected_plans_csv_path = (
    pkg_resources.files("data_analysis.electricity_plans_available.output")
    / "selected_electricity_plans.csv"
)
with selected_plans_csv_path.open("r", encoding="utf-8") as csv_file:
    edb_to_plan_id = pd.read_csv(csv_file, dtype=str)

try:
    all_plans_csv_path = (
        pkg_resources.files("data_analysis.supplementary_data.tariff_data")
        / "tariffDataReport_240903.csv"
    )
    filtered_plans = get_filtered_df(path=all_plans_csv_path)
except FileNotFoundError:
    filtered_plans = filtered_plans_stub

joined_df = pd.merge(
    postcode_to_edb, edb_to_plan_id, how="inner", left_on="edb_region", right_on="EDB"
)

joined_df["PlanId"] = joined_df["PlanId"].astype(int)
filtered_plans["PlanId"] = filtered_plans["PlanId"].astype(int)

joined_df = pd.merge(
    joined_df,
    filtered_plans,
    how="inner",
    on="PlanId",
)

joined_df["electricity_plan"] = joined_df.apply(row_to_plan, axis=1)
joined_df["electricity_plan"] = joined_df["electricity_plan"].apply(add_gst)

postcode_to_edb_dict = postcode_to_edb.set_index("postcode").to_dict()["edb_region"]
edb_to_electricity_plan_dict = joined_df.set_index("edb_region").to_dict()[
    "electricity_plan"
]
postcode_to_electricity_plan_dict = joined_df.set_index("postcode").to_dict()[
    "electricity_plan"
]

default_plans = get_default_plans()


plans = joined_df[["postcode", "edb_region", "electricity_plan"]]
plans.loc[:, "name"] = [
    x["name"] for x in plans.electricity_plan.apply(lambda x: x.model_dump())
].copy()
plans.loc[:, "daily_charge"] = [
    x["daily_charge"] for x in plans.electricity_plan.apply(lambda x: x.model_dump())
].copy()
for variable_rate in ["Controlled", "Uncontrolled", "All inclusive", "Day", "Night"]:
    plans.loc[:, variable_rate] = [
        x["nzd_per_kwh"].get(variable_rate, np.nan)
        for x in plans.electricity_plan.apply(lambda x: x.model_dump())
    ].copy()
plans = plans.drop("electricity_plan", axis=1)

plans = plans.drop("postcode", axis=1)
plans = plans.drop_duplicates().reset_index()


plans = joined_df[["postcode", "edb_region", "electricity_plan"]].copy()
expanded_plans = pd.json_normalize(
    plans["electricity_plan"].apply(lambda x: x.model_dump())
)
plans = pd.concat([plans[["postcode", "edb_region"]], expanded_plans], axis=1)
plans = plans.drop("postcode", axis=1).drop_duplicates().reset_index(drop=True)


plans.to_csv("output/selected_electricity_plan_tariffs_by_edb.csv")
