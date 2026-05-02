"""Tests for the DDC Revit/IFC parameter-validation rule pack.

Covers:
* ParameterPresenceRule  — missing column ⇒ ERROR; column on at least one elem ⇒ pass
* ParameterCompletenessRule — pct >= min ⇒ pass; below ⇒ WARNING
* UniqueValueListRule — always pass; surfaces unique values in details
* Synonym matching — IFC-side category names trigger the same rule
* Empty-category short-circuit — no elements means INFO/skipped, not failure
* register_ddc_revit_ifc_rules — populates the registry under ``ddc_revit_ifc``
"""

from __future__ import annotations

import pytest

from app.core.validation.engine import RuleCategory, Severity, ValidationContext
from app.core.validation.rules.ddc_revit_ifc import (
    ParameterCompletenessRule,
    ParameterPresenceRule,
    UniqueValueListRule,
    register_ddc_revit_ifc_rules,
)


# ── ParameterPresenceRule ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_presence_passes_when_any_element_has_column():
    rule = ParameterPresenceRule("OST_Walls", "Mark")
    ctx = ValidationContext(
        data={
            "elements": [
                {"id": "1", "category": "OST_Walls", "Mark": "W1"},
                {"id": "2", "category": "OST_Walls"},
            ],
        },
    )
    [result] = await rule.validate(ctx)
    assert result.passed is True


@pytest.mark.asyncio
async def test_presence_fails_when_column_absent_on_all():
    rule = ParameterPresenceRule("OST_Walls", "FireRating")
    ctx = ValidationContext(
        data={
            "elements": [
                {"id": "1", "category": "OST_Walls", "Mark": "W1"},
                {"id": "2", "category": "OST_Walls", "Mark": "W2"},
            ],
        },
    )
    [result] = await rule.validate(ctx)
    assert result.passed is False
    assert result.severity == Severity.ERROR
    assert "FireRating" in result.message


@pytest.mark.asyncio
async def test_presence_skipped_when_no_matching_elements():
    rule = ParameterPresenceRule("OST_Doors", "FireRating")
    ctx = ValidationContext(data={"elements": [{"category": "OST_Walls"}]})
    [result] = await rule.validate(ctx)
    assert result.passed is True
    assert result.severity == Severity.INFO
    assert "skipped" in result.message.lower()


# ── ParameterCompletenessRule ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_completeness_passes_at_or_above_threshold():
    rule = ParameterCompletenessRule("OST_Walls", "Mark", min_pct=80.0)
    ctx = ValidationContext(
        data={
            "elements": [
                {"category": "OST_Walls", "Mark": "W1"},
                {"category": "OST_Walls", "Mark": "W2"},
                {"category": "OST_Walls", "Mark": "W3"},
                {"category": "OST_Walls", "Mark": "W4"},
                {"category": "OST_Walls", "Mark": ""},  # 4/5 = 80%
            ],
        },
    )
    [result] = await rule.validate(ctx)
    assert result.passed is True
    assert result.details["pct"] == 80.0


@pytest.mark.asyncio
async def test_completeness_warns_below_threshold():
    rule = ParameterCompletenessRule("OST_Walls", "FireRating", min_pct=95.0)
    ctx = ValidationContext(
        data={
            "elements": [
                {"category": "OST_Walls", "FireRating": "F90"},
                {"category": "OST_Walls", "FireRating": None},
                {"category": "OST_Walls", "FireRating": ""},
                {"category": "OST_Walls"},
            ],
        },
    )
    [result] = await rule.validate(ctx)
    assert result.passed is False
    assert result.severity == Severity.WARNING
    assert result.details["populated"] == 1
    assert result.details["total"] == 4
    assert result.details["pct"] == 25.0


@pytest.mark.asyncio
async def test_completeness_rejects_invalid_min_pct():
    with pytest.raises(ValueError):
        ParameterCompletenessRule("OST_Walls", "Mark", min_pct=120.0)


# ── UniqueValueListRule ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unique_values_lists_distinct():
    rule = UniqueValueListRule("OST_Walls", "FireRating")
    ctx = ValidationContext(
        data={
            "elements": [
                {"category": "OST_Walls", "FireRating": "F30"},
                {"category": "OST_Walls", "FireRating": "F90"},
                {"category": "OST_Walls", "FireRating": "F90"},
                {"category": "OST_Walls", "FireRating": "F30"},
                {"category": "OST_Walls", "FireRating": ""},
                {"category": "OST_Walls"},
            ],
        },
    )
    [result] = await rule.validate(ctx)
    assert result.passed is True
    assert set(result.details["unique_values"]) == {"F30", "F90"}
    assert result.details["truncated"] is False


@pytest.mark.asyncio
async def test_unique_values_truncates_at_max_distinct():
    rule = UniqueValueListRule("OST_Walls", "Mark", max_distinct=3)
    ctx = ValidationContext(
        data={
            "elements": [
                {"category": "OST_Walls", "Mark": f"W{i}"} for i in range(10)
            ],
        },
    )
    [result] = await rule.validate(ctx)
    assert result.passed is True
    assert len(result.details["unique_values"]) == 3
    assert result.details["truncated"] is True


# ── IFC synonym matching ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ifc_synonym_matches_revit_category():
    rule = ParameterPresenceRule(
        "OST_Walls", "Mark", synonyms=("IfcWall", "IfcWallStandardCase"),
    )
    ctx = ValidationContext(
        data={
            "elements": [
                {"category": "IfcWall", "Mark": "W1"},
                {"category": "IfcWallStandardCase", "Mark": "W2"},
            ],
        },
    )
    [result] = await rule.validate(ctx)
    assert result.passed is True


# ── Registry integration ────────────────────────────────────────────────────


def test_register_ddc_revit_ifc_rules_populates_registry():
    from app.core.validation.engine import rule_registry

    register_ddc_revit_ifc_rules()
    rules = rule_registry.list_rules(rule_set="ddc_revit_ifc")
    rule_ids = {r["rule_id"] for r in rules}
    # 12 (cat, param) pairs × 3 rule classes = 36 rules
    assert len(rule_ids) == 36
    # Spot-check a few representative rule ids
    assert "ddc.parameter_present.OST_Walls.Mark" in rule_ids
    assert "ddc.parameter_completeness.OST_Doors.FireRating" in rule_ids
    assert "ddc.unique_values.OST_StructuralFraming.Mark" in rule_ids
