"""
This script summarizes the different types of electricity
plans available in the dataset. These are defined by the
stated "Plan type" but also by the columns that have non-null
values. As a result of filtering, we end up with only the 
following distinct patterns of non-NaN columns:
- {'All inclusive'}
- {'Night', 'Day'}
- {'Uncontrolled'}
- {'Uncontrolled', 'Controlled'}
- {'Uncontrolled', 'All inclusive'}
- {'Night', 'Controlled', 'Day'}
- {'Night', 'All inclusive'}
- {'Night', 'Uncontrolled', 'Controlled'}
- {'Night', 'Uncontrolled'}
"""

from data_analysis.electricity_plans_available.electricity_plans_analysis import (
    get_filtered_df,
)

filtered_df = get_filtered_df()

excluded_columns = [
    "Annual estimated cost",
    "Dual fuel only",
    "EDB",
    "Energy type",
    "Fixed term",
    "Low user",
    "Name",
    "Network location names",
    "Online only",
    "Plan type",
    "PlanId",
    "Prices last changed",
    "Retailer location name",
    "Retailer name",
    "Seasonal",
    "Status",
    "Daily charge",
    "Hours",
]

plan_type_columns = {}
no_pricing_info_plans = []

for index, row in filtered_df.iterrows():
    plan_type = row["Plan type"]
    non_nan_columns = row.drop(excluded_columns).dropna().index.tolist()
    non_nan_columns.sort()
    non_nan_columns_tuple = tuple(non_nan_columns)
    if plan_type not in plan_type_columns:
        plan_type_columns[plan_type] = {}
    if non_nan_columns_tuple in plan_type_columns[plan_type]:
        plan_type_columns[plan_type][non_nan_columns_tuple] += 1
    else:
        plan_type_columns[plan_type][non_nan_columns_tuple] = 1

    # Store details of plans with no pricing information
    if not non_nan_columns:
        no_pricing_info_plans.append((index, row.to_dict()))

total_rows = len(filtered_df)

processed_count = sum(
    count for plan_info in plan_type_columns.values() for count in plan_info.values()
)

assert total_rows == processed_count, "There is a discrepancy in the numbers."

for plan_type, columns_info in plan_type_columns.items():
    print(f"\nPlan Type: {plan_type}")
    for columns, count in columns_info.items():
        print(f"Columns: {columns}, Count: {count}")

# Print plans with no pricing information
if no_pricing_info_plans:
    print("\nPlans with no pricing information:")
    for index, plan_details in no_pricing_info_plans:
        print(f"Index: {index}, Details: {plan_details}")
