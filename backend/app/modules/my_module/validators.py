"""Validation rules contributed by My Module.

Built-in rule sets live in ``app.core.validation.rules.__init__``; community
modules register their own rules from their startup hook so the rule_registry
discovers them at boot.
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


def _get_items(context: ValidationContext) -> list[dict[str, Any]]:
    data = context.data
    if isinstance(data, dict):
        return data.get("items", [])
    if isinstance(data, list):
        return data
    return []


class ItemNameRequired(ValidationRule):
    """Every Item must have a non-blank name."""

    rule_id = "my_module.item_name_required"
    name = "Item name required"
    standard = "my_module"
    severity = Severity.ERROR
    category = RuleCategory.COMPLETENESS
    description = "Items must have a non-empty name."

    async def validate(self, context: ValidationContext) -> list[RuleResult]:
        results: list[RuleResult] = []
        for item in _get_items(context):
            value = item.get("name")
            passed = bool(value) and bool(str(value).strip())
            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    rule_name=self.name,
                    severity=self.severity,
                    category=self.category,
                    passed=passed,
                    message="OK" if passed else "Item name must not be blank",
                    element_ref=item.get("id"),
                ),
            )
        return results


class ItemNameMaxLength(ValidationRule):
    """Item names must be 255 characters or fewer."""

    rule_id = "my_module.item_name_max_length"
    name = "Item name length"
    standard = "my_module"
    severity = Severity.WARNING
    category = RuleCategory.QUALITY
    description = "Item names should be 255 characters or fewer."

    async def validate(self, context: ValidationContext) -> list[RuleResult]:
        results: list[RuleResult] = []
        for item in _get_items(context):
            value = item.get("name") or ""
            passed = len(str(value)) <= 255
            results.append(
                RuleResult(
                    rule_id=self.rule_id,
                    rule_name=self.name,
                    severity=self.severity,
                    category=self.category,
                    passed=passed,
                    message="OK" if passed else "Item name exceeds 255 characters",
                    element_ref=item.get("id"),
                ),
            )
        return results


def register_my_module_rules() -> None:
    """Register My Module's validation rules with the global registry."""
    rule_registry.register(ItemNameRequired(), rule_sets=["my_module"])
    rule_registry.register(ItemNameMaxLength(), rule_sets=["my_module"])
