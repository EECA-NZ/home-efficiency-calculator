"""
This script illustrates how to use a household's energy usage profile
to calculate the total annual cost of energy for the household.
"""

import app.services.configuration as cfg
from app.models.energy_plans import HouseholdEnergyPlan

my_plan = HouseholdEnergyPlan(
    name="Basic Household Energy Plan",
    electricity_plan=cfg.get_default_electricity_plan(),
    natural_gas_plan=cfg.get_default_natural_gas_plan(),
    lpg_plan=cfg.get_default_lpg_plan(),
    wood_price=cfg.get_default_wood_price(),
    petrol_price=cfg.get_default_petrol_price(),
    diesel_price=cfg.get_default_diesel_price(),
    public_charging_price=cfg.get_default_public_ev_charger_rate(),
    other_vehicle_costs=cfg.get_default_annual_other_vehicle_costs("None"),
)

your_home_answers = cfg.get_default_your_home_answers()
cooking_answers = cfg.get_default_cooktop_answers()
energy_profile = cooking_answers.energy_usage_pattern(your_home_answers)

print(energy_profile)
print(my_plan.calculate_cost(energy_profile))
