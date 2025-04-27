"""
Tests for the Pydantic response models in app/models/response_models.py
"""

import pytest
from pydantic import ValidationError

from app.models.response_models import (
    CheckboxData,
    ComponentSavingsResponse,
    FixedCostsResponse,
    SavingsData,
    SavingsResponse,
    SolarSavingsResponse,
    UserGeography,
)
from app.models.usage_profiles import YearlyFuelUsageProfile, YearlyFuelUsageReport


def make_dummy_yearly_report():
    """
    Construct a minimal YearlyFuelUsageReport using an empty YearlyFuelUsageProfile.
    """
    profile = YearlyFuelUsageProfile()
    return YearlyFuelUsageReport(profile)


class TestUserGeography:
    """Tests for the UserGeography pydantic model."""

    def test_valid(self):
        """Valid UserGeography input yields expected attribute values."""
        geog = UserGeography(edb_region="East", climate_zone="Zone1")
        assert geog.edb_region == "East"
        assert geog.climate_zone == "Zone1"

    def test_missing_field(self):
        """Missing climate_zone field should raise ValidationError."""
        with pytest.raises(ValidationError):
            UserGeography(edb_region="East")

    def test_wrong_type(self):
        """Wrong type for edb_region should raise ValidationError."""
        with pytest.raises(ValidationError):
            UserGeography(edb_region=123, climate_zone="Zone1")


class TestSavingsData:
    """Tests for the SavingsData pydantic model."""

    def test_valid(self):
        """SavingsData accepts valid numeric inputs."""
        data = SavingsData(
            current=1.23,
            alternative=4.56,
            absolute_reduction=3.33,
            percentage_reduction=10.0,
        )
        assert data.current == 1.23

    def test_missing_optional(self):
        """All fields optional should default to None."""
        # All fields optional
        data = SavingsData()
        assert data.current is None

    def test_wrong_type(self):
        """Non-float current field should raise ValidationError."""
        with pytest.raises(ValidationError):
            SavingsData(current="not a float")


class TestSavingsResponse:
    """Tests for the SavingsResponse pydantic model."""

    def test_valid(self):
        """Valid SavingsResponse should accept SavingsData instances."""
        sd = SavingsData(current=1.0)
        resp = SavingsResponse(variable_cost_nzd=sd, emissions_kg_co2e=sd)
        assert isinstance(resp.variable_cost_nzd, SavingsData)

    def test_missing_field(self):
        """Missing required field should raise ValidationError."""
        # missing one required field
        with pytest.raises(ValidationError):
            SavingsResponse(variable_cost_nzd=SavingsData())

    def test_wrong_type(self):
        """Wrong type for variable_cost_nzd should raise ValidationError."""
        with pytest.raises(ValidationError):
            SavingsResponse(variable_cost_nzd=1.0, emissions_kg_co2e=SavingsData())


class TestComponentSavingsResponse:
    """Tests for the ComponentSavingsResponse pydantic model."""

    def test_valid(self):
        """Valid ComponentSavingsResponse should include alternatives."""
        alt = {
            "opt1": SavingsResponse(
                variable_cost_nzd=SavingsData(), emissions_kg_co2e=SavingsData()
            )
        }
        geog = UserGeography(edb_region="R", climate_zone="C")
        cur = make_dummy_yearly_report()
        obj = ComponentSavingsResponse(
            alternatives=alt,
            user_geography=geog,
            current_fuel_use=cur,
            alternative_fuel_use=None,
        )
        assert "opt1" in obj.alternatives

    def test_missing_required(self):
        """Missing required fields should raise ValidationError."""
        with pytest.raises(ValidationError):
            ComponentSavingsResponse(
                alternatives={},
                user_geography=UserGeography(edb_region="R", climate_zone="C"),
            )

    def test_wrong_type(self):
        """Invalid alternatives mapping should raise ValidationError."""
        with pytest.raises(ValidationError):
            ComponentSavingsResponse(
                alternatives={"opt": {"bad": 1}},
                user_geography=UserGeography(edb_region="R", climate_zone="C"),
                current_fuel_use=make_dummy_yearly_report(),
            )


class TestSolarSavingsResponse:
    """Tests for the SolarSavingsResponse pydantic model."""

    def test_valid(self):
        """Valid SolarSavingsResponse should accept all required fields."""
        resp = SolarSavingsResponse(
            annual_kwh_generated=100.0,
            annual_kg_co2e_saving=50.0,
            annual_earnings_solar_export=20.0,
            annual_savings_solar_self_consumption=30.0,
        )
        assert resp.annual_kwh_generated == 100.0

    def test_missing_field(self):
        """Missing one solar savings field should raise ValidationError."""
        with pytest.raises(ValidationError):
            SolarSavingsResponse(
                annual_kwh_generated=100.0,
                annual_kg_co2e_saving=50.0,
                annual_earnings_solar_export=20.0,
            )

    def test_wrong_type(self):
        """Non-coercible type for a field should raise ValidationError."""
        # Provide a non-coercible type for a float field
        with pytest.raises(ValidationError):
            SolarSavingsResponse(
                annual_kwh_generated={},
                annual_kg_co2e_saving=50.0,
                annual_earnings_solar_export=20.0,
                annual_savings_solar_self_consumption=30.0,
            )


class TestCheckboxData:
    """Tests for the CheckboxData pydantic model."""

    def test_valid_all(self):
        """CheckboxData accepts all boolean and text fields when provided."""
        box = CheckboxData(
            checkbox_visible=True,
            checkbox_text="text",
            checkbox_greyed_out=False,
            checkbox_default_on=True,
        )
        assert box.checkbox_visible is True

    def test_missing_optional(self):
        """All CheckboxData fields are optional and default to None."""
        # All fields optional
        box = CheckboxData()
        assert box.checkbox_visible is None

    def test_wrong_type(self):
        """Invalid type for checkbox_visible should raise ValidationError."""
        # Provide a value that cannot be coerced to bool
        with pytest.raises(ValidationError):
            CheckboxData(checkbox_visible=["not a bool"])


class TestFixedCostsResponse:
    """Tests for the FixedCostsResponse pydantic model."""

    def test_valid(self):
        """Valid FixedCostsResponse should contain gas connection savings."""
        gps = {
            "nat_gas": SavingsResponse(
                variable_cost_nzd=SavingsData(), emissions_kg_co2e=SavingsData()
            )
        }
        resp = FixedCostsResponse(gas_connection_savings=gps)
        assert "nat_gas" in resp.gas_connection_savings

    def test_missing_field(self):
        """Missing gas_connection_savings should raise ValidationError."""
        with pytest.raises(ValidationError):
            FixedCostsResponse()

    def test_wrong_type(self):
        """Non-dict type for gas_connection_savings should raise ValidationError."""
        with pytest.raises(ValidationError):
            FixedCostsResponse(gas_connection_savings={"nat": 123})
