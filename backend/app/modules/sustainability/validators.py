"""Validation rules contributed by the sustainability / CO₂ module.

Rules:

* ``sustainability.element_group_quantity_positive`` — every element group
  must have a strictly-positive quantity (a zero-volume group cannot
  contribute meaningfully to a footprint and is almost always a data error).
* ``sustainability.element_group_has_epd`` — every element group should be
  matched to an EPD code OR have a known ``material_category`` that the
  fallback resolver can match. Severity WARNING — unmatched groups still
  produce a report, but they are flagged.
"""

from typing import Any

from app.core.validation.engine import (
    RuleCategory,
    RuleResult,
    Severity,
    ValidationContext,
    ValidationRule,
    rule_registry,
)


_KNOWN_CATEGORIES = {
    "concrete",
    "steel",
    "timber",
    "glass",
    "asphalt",
    "aluminum",
    "masonry",
    "insulation",
    "gypsum",
    "other",
}


def _get_groups(context: ValidationContext) -> list[dict[str, Any]]:
    data = context.data
    if isinstance(data, dict):
        return data.get("groups", []) or data.get("items", [])
    if isinstance(data, list):
        return data
    return []


class ElementGroupQuantityPositive(ValidationRule):
    rule_id = "sustainability.element_group_quantity_positive"
    name = "Element group quantity positive"
    standard = "sustainability"
    severity = Severity.ERROR
    category = RuleCategory.COMPLETENESS
    description = "Every element group must have a strictly-positive quantity."

    async def validate(self, context: ValidationContext) -> list[RuleResult]:
        results: list[RuleResult] = []
        for g in _get_groups(context):
            try:
                q = float(g.get("quantity", 0))
            except (TypeError, ValueError):
                q = 0.0
            passed = q > 0
            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    rule_name=self.name,
                    severity=self.severity,
                    category=self.category,
                    passed=passed,
                    message="OK" if passed else f"Quantity must be > 0 (got {q})",
                    element_ref=g.get("id") or g.get("name"),
                ),
            )
        return results


class ElementGroupHasEpdOrCategory(ValidationRule):
    rule_id = "sustainability.element_group_has_epd"
    name = "Element group has EPD code or known category"
    standard = "sustainability"
    severity = Severity.WARNING
    category = RuleCategory.QUALITY
    description = (
        "Every element group should have an ``epd_code`` or a ``material_category`` "
        "that can be resolved to an emission factor."
    )

    async def validate(self, context: ValidationContext) -> list[RuleResult]:
        results: list[RuleResult] = []
        for g in _get_groups(context):
            epd = g.get("epd_code")
            cat = (g.get("material_category") or "").lower()
            passed = bool(epd) or cat in _KNOWN_CATEGORIES
            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    rule_name=self.name,
                    severity=self.severity,
                    category=self.category,
                    passed=passed,
                    message="OK"
                    if passed
                    else f"No EPD code, and category '{cat}' not in known set",
                    element_ref=g.get("id") or g.get("name"),
                ),
            )
        return results


def register_sustainability_rules() -> None:
    rule_registry.register(ElementGroupQuantityPositive(), rule_sets=["sustainability"])
    rule_registry.register(ElementGroupHasEpdOrCategory(), rule_sets=["sustainability"])
