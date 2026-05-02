"""DDC Revit/IFC parameter-validation rules.

Port of the Excel-driven validation logic from two DDC reference repos:

* ``Revit-IFC-Verification`` — Excel-driven (``DDC Revit and IFC Validation.xlsx``)
  parameter-presence + completeness checks across Revit/IFC element tables.
* ``Checking-the-quality-of-Revit-and-IFC-projects`` — same concept with a
  larger rule pack and a PDF-report renderer.

Both repos consume a tabular export of a Revit or IFC project (rows = elements,
columns = parameters) and check, for each ``(category, parameter)`` pair listed
in their config, whether:

1. **the parameter exists at all** for elements of that category
2. **what percentage of elements** have a non-empty value
3. **what unique values** appear (surfaces typos and stray strings)

This module exposes those three checks as proper :class:`ValidationRule` subclasses
that plug into the existing OCE validation engine. Rule configuration (which
``(category, parameter)`` pairs to check, completeness thresholds) is supplied
per-rule via the constructor — the registry function below registers a small
default pack covering the most common Revit categories. Project-level
configuration can be loaded from JSON / Excel by the calling service.

Element table shape (``context.data["elements"]``):

    [
        {"id": "...", "category": "OST_Walls", "Mark": "W1", "Comments": "...", ...},
        {"id": "...", "category": "OST_Doors", "Mark": "D1", "FireRating": "F90", ...},
        ...
    ]

The ``category`` key matches both Revit's ``OST_*`` categories and IFC's
``Ifc*`` entity types — ``IfcWall`` is treated the same as ``OST_Walls`` in
the default pack via the ``synonyms`` arg.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.core.validation.engine import (
    RuleCategory,
    RuleResult,
    Severity,
    ValidationContext,
    ValidationRule,
    rule_registry,
)


def _get_elements(context: ValidationContext) -> list[dict[str, Any]]:
    data = context.data
    if isinstance(data, dict):
        return data.get("elements", []) or data.get("items", [])
    if isinstance(data, list):
        return data
    return []


def _matches_category(element: dict[str, Any], category: str, synonyms: Iterable[str]) -> bool:
    raw = element.get("category") or element.get("Category") or ""
    if not raw:
        return False
    targets = {category, *synonyms}
    return raw in targets or raw.lower() in {t.lower() for t in targets}


def _is_populated(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    return True


# ── Rule 1: parameter presence ─────────────────────────────────────────────


class ParameterPresenceRule(ValidationRule):
    """Does the named parameter appear as a column on any element of the given category?

    Failure mode: zero elements of ``category`` have any non-null value for
    ``parameter``. This catches the case where the parameter wasn't shared
    into the project at all — a hard error in DDC's quality report.
    """

    severity = Severity.ERROR
    category = RuleCategory.COMPLETENESS
    standard = "ddc_revit_ifc"

    def __init__(
        self,
        category: str,
        parameter: str,
        synonyms: Iterable[str] = (),
    ) -> None:
        self._cat = category
        self._param = parameter
        self._synonyms = tuple(synonyms)
        # Stable rule id so the registry can identify each instance
        slug_cat = category.replace(" ", "_").replace("/", "_")
        slug_param = parameter.replace(" ", "_").replace("/", "_")
        self.rule_id = f"ddc.parameter_present.{slug_cat}.{slug_param}"
        self.name = f"Parameter '{parameter}' present on {category}"
        self.description = (
            f"Every {category} element should have the '{parameter}' parameter "
            "as a column. Missing column means the shared parameter was never "
            "imported into the project."
        )

    async def validate(self, context: ValidationContext) -> list[RuleResult]:
        elements = [
            e for e in _get_elements(context)
            if _matches_category(e, self._cat, self._synonyms)
        ]
        if not elements:
            return [
                RuleResult(
                    rule_id=self.rule_id,
                    rule_name=self.name,
                    severity=Severity.INFO,
                    category=self.category,
                    passed=True,
                    message=f"No {self._cat} elements in project — rule skipped",
                ),
            ]
        any_present = any(self._param in e for e in elements)
        return [
            RuleResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                severity=self.severity,
                category=self.category,
                passed=any_present,
                message=(
                    "OK"
                    if any_present
                    else f"Parameter '{self._param}' is not a column on any "
                    f"{self._cat} element"
                ),
                details={"category": self._cat, "parameter": self._param},
            ),
        ]


# ── Rule 2: parameter completeness ─────────────────────────────────────────


class ParameterCompletenessRule(ValidationRule):
    """What percentage of category elements have a populated value for parameter?

    Failure mode: completeness percentage falls below ``min_pct``. Default 95%.
    Severity is WARNING (not ERROR) because partial population is normal during
    early design phases.
    """

    severity = Severity.WARNING
    category = RuleCategory.COMPLETENESS
    standard = "ddc_revit_ifc"

    def __init__(
        self,
        category: str,
        parameter: str,
        min_pct: float = 95.0,
        synonyms: Iterable[str] = (),
    ) -> None:
        if not 0 <= min_pct <= 100:
            raise ValueError(f"min_pct must be in [0, 100], got {min_pct}")
        self._cat = category
        self._param = parameter
        self._min_pct = float(min_pct)
        self._synonyms = tuple(synonyms)
        slug_cat = category.replace(" ", "_").replace("/", "_")
        slug_param = parameter.replace(" ", "_").replace("/", "_")
        self.rule_id = f"ddc.parameter_completeness.{slug_cat}.{slug_param}"
        self.name = f"Parameter '{parameter}' completeness on {category}"
        self.description = (
            f"At least {min_pct:.0f}% of {category} elements must have a "
            f"populated '{parameter}' value."
        )

    async def validate(self, context: ValidationContext) -> list[RuleResult]:
        elements = [
            e for e in _get_elements(context)
            if _matches_category(e, self._cat, self._synonyms)
        ]
        if not elements:
            return [
                RuleResult(
                    rule_id=self.rule_id,
                    rule_name=self.name,
                    severity=Severity.INFO,
                    category=self.category,
                    passed=True,
                    message=f"No {self._cat} elements in project — rule skipped",
                ),
            ]
        populated = sum(1 for e in elements if _is_populated(e.get(self._param)))
        pct = (populated / len(elements)) * 100.0
        passed = pct >= self._min_pct
        return [
            RuleResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                severity=self.severity,
                category=self.category,
                passed=passed,
                message=(
                    f"{pct:.1f}% populated ({populated}/{len(elements)})"
                    + ("" if passed else f" — below {self._min_pct:.0f}% threshold")
                ),
                details={
                    "category": self._cat,
                    "parameter": self._param,
                    "populated": populated,
                    "total": len(elements),
                    "pct": round(pct, 2),
                    "min_pct": self._min_pct,
                },
            ),
        ]


# ── Rule 3: unique-value listing ───────────────────────────────────────────


class UniqueValueListRule(ValidationRule):
    """Surfaces unique parameter values for a category — never fails.

    Always returns ``passed=True``. Used to drive the unique-values section
    of DDC's PDF report. The list is in ``details["unique_values"]`` so the
    report renderer can pick it up and the UI can show "did you mean…?"
    suggestions.
    """

    severity = Severity.INFO
    category = RuleCategory.QUALITY
    standard = "ddc_revit_ifc"

    def __init__(
        self,
        category: str,
        parameter: str,
        max_distinct: int = 50,
        synonyms: Iterable[str] = (),
    ) -> None:
        self._cat = category
        self._param = parameter
        self._max_distinct = int(max_distinct)
        self._synonyms = tuple(synonyms)
        slug_cat = category.replace(" ", "_").replace("/", "_")
        slug_param = parameter.replace(" ", "_").replace("/", "_")
        self.rule_id = f"ddc.unique_values.{slug_cat}.{slug_param}"
        self.name = f"Unique values of '{parameter}' on {category}"
        self.description = (
            f"Lists distinct values of '{parameter}' across all {category} elements "
            "(informational; surfaces typos and stale values for review)."
        )

    async def validate(self, context: ValidationContext) -> list[RuleResult]:
        elements = [
            e for e in _get_elements(context)
            if _matches_category(e, self._cat, self._synonyms)
        ]
        if not elements:
            return [
                RuleResult(
                    rule_id=self.rule_id,
                    rule_name=self.name,
                    severity=self.severity,
                    category=self.category,
                    passed=True,
                    message=f"No {self._cat} elements in project — rule skipped",
                ),
            ]
        seen: list[Any] = []
        seen_set: set[Any] = set()
        for e in elements:
            v = e.get(self._param)
            if not _is_populated(v):
                continue
            key = v if isinstance(v, str | int | float | bool) else str(v)
            if key not in seen_set:
                seen_set.add(key)
                seen.append(v)
                if len(seen) >= self._max_distinct:
                    break
        return [
            RuleResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                severity=self.severity,
                category=self.category,
                passed=True,
                message=f"{len(seen)} unique value(s)" + (
                    f" (truncated at {self._max_distinct})"
                    if len(seen) >= self._max_distinct
                    else ""
                ),
                details={
                    "category": self._cat,
                    "parameter": self._param,
                    "unique_values": seen,
                    "truncated": len(seen) >= self._max_distinct,
                },
            ),
        ]


# ── Default rule pack ──────────────────────────────────────────────────────


# (category, parameter, [synonyms]) — pack covering the most common Revit
# categories that DDC's bundled validation Excel ships with. The
# ``synonyms`` are IFC-side equivalents so the same rule fires on either an
# RVT or IFC export.
_DEFAULT_PACK: list[tuple[str, str, tuple[str, ...]]] = [
    ("OST_Walls", "Mark", ("IfcWall", "IfcWallStandardCase")),
    ("OST_Walls", "Comments", ("IfcWall", "IfcWallStandardCase")),
    ("OST_Walls", "FireRating", ("IfcWall", "IfcWallStandardCase")),
    ("OST_Doors", "Mark", ("IfcDoor",)),
    ("OST_Doors", "FireRating", ("IfcDoor",)),
    ("OST_Windows", "Mark", ("IfcWindow",)),
    ("OST_Floors", "Mark", ("IfcSlab",)),
    ("OST_Floors", "Comments", ("IfcSlab",)),
    ("OST_Roofs", "Mark", ("IfcRoof", "IfcSlab")),
    ("OST_Columns", "Mark", ("IfcColumn",)),
    ("OST_StructuralColumns", "Mark", ("IfcColumn",)),
    ("OST_StructuralFraming", "Mark", ("IfcBeam",)),
]


def register_ddc_revit_ifc_rules() -> None:
    """Register the default DDC Revit/IFC rule pack with the global registry.

    Three rule instances per ``(category, parameter)`` triple — presence,
    completeness, and unique-value listing.
    """
    for cat, param, synonyms in _DEFAULT_PACK:
        rule_registry.register(
            ParameterPresenceRule(cat, param, synonyms=synonyms),
            rule_sets=["ddc_revit_ifc"],
        )
        rule_registry.register(
            ParameterCompletenessRule(cat, param, synonyms=synonyms),
            rule_sets=["ddc_revit_ifc"],
        )
        rule_registry.register(
            UniqueValueListRule(cat, param, synonyms=synonyms),
            rule_sets=["ddc_revit_ifc"],
        )
