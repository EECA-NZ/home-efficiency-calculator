"""
General constants used in the calculations
"""

DAYS_IN_YEAR = 365.25

AVERAGE_HOUSEHOLD_SIZE = 2.69

DEFAULT_SAVINGS_AND_EMISSIONS_RESPONSE = {
    "average_household_savings": 1000,
    "average_household_emissions_percentage_reduction": 85,
}

EMISSIONS_FACTORS = {
    "electricity_kg_co2e_per_kwh": 0.077,
    "natural_gas_kg_co2e_per_kwh": 0.195,
    "lpg_kg_co2e_per_kwh": 0.214,
    "wood_kg_co2e_per_kwh": 0.05,
    "petrol_kg_co2e_per_litre": 2.41,
    "diesel_kg_co2e_per_litre": 2.67,
}