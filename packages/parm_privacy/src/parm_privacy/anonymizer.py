"""Data anonymization strategies."""

import hashlib
from typing import Any, Callable, dict, Optional


class Anonymizer:
    """
    Transforms data according to policy rules.
    Supports multiple anonymization strategies.
    """

    def __init__(self) -> None:
        """Initialize the anonymizer."""
        self._strategies: dict[str, Callable[[str], str]] = {
            "hash": self._hash,
            "mask": self._mask,
            "generalize": self._generalize,
            "suppress": self._suppress,
        }

    def anonymize(
        self,
        data: dict[str, Any],
        rules: dict[str, str],
    ) -> dict[str, Any]:
        """
        Anonymize data according to rules.

        Args:
            data: Data to anonymize
            rules: Mapping of field names to anonymization strategies

        Returns:
            Anonymized data
        """
        anonymized = data.copy()

        for field_name, strategy in rules.items():
            if field_name in anonymized:
                value = anonymized[field_name]
                if value is not None:
                    anonymized[field_name] = self._apply_strategy(strategy, str(value))

        return anonymized

    def anonymize_nested(
        self,
        data: dict[str, Any],
        rules: dict[str, str],
    ) -> dict[str, Any]:
        """
        Anonymize data with support for nested fields (using dot notation).

        Args:
            data: Data to anonymize
            rules: Mapping of field paths to strategies (e.g., "user.email": "hash")

        Returns:
            Anonymized data
        """
        anonymized = data.copy()

        for field_path, strategy in rules.items():
            parts = field_path.split(".")
            self._set_nested_value(anonymized, parts, strategy)

        return anonymized

    def pseudonymize(
        self,
        data: dict[str, Any],
        rules: dict[str, str],
        salt: str = "parm_salt",
    ) -> tuple[dict[str, Any], dict[str, str]]:
        """
        Reversible pseudonymization (for internal use).

        Args:
            data: Data to pseudonymize
            rules: Anonymization rules
            salt: Salt for pseudonymization

        Returns:
            Tuple of (pseudonymized_data, mapping_dict)
        """
        pseudonymized = data.copy()
        mapping = {}

        for field_name, strategy in rules.items():
            if field_name in pseudonymized:
                value = pseudonymized[field_name]
                if value is not None:
                    original = str(value)
                    hashed = hashlib.sha256(f"{original}{salt}".encode()).hexdigest()[:16]
                    mapping[hashed] = original
                    pseudonymized[field_name] = hashed

        return pseudonymized, mapping

    def _apply_strategy(self, strategy: str, value: str) -> str:
        """Apply a single anonymization strategy."""
        if strategy in self._strategies:
            return self._strategies[strategy](value)
        return value

    @staticmethod
    def _hash(value: str) -> str:
        """Hash a value."""
        return hashlib.sha256(value.encode()).hexdigest()[:16]

    @staticmethod
    def _mask(value: str) -> str:
        """Mask a value (show first and last char only)."""
        if len(value) <= 2:
            return "*" * len(value)
        return value[0] + "*" * (len(value) - 2) + value[-1]

    @staticmethod
    def _generalize(value: str) -> str:
        """Generalize a value (e.g., age ranges)."""
        try:
            num = int(value)
            # Generalize to ranges of 10
            range_start = (num // 10) * 10
            return f"{range_start}-{range_start + 9}"
        except ValueError:
            # For non-numeric, suppress
            return "***"

    @staticmethod
    def _suppress(value: str) -> str:
        """Suppress a value completely."""
        return "***"

    def _set_nested_value(
        self,
        data: dict[str, Any],
        path: list[str],
        strategy: str,
    ) -> None:
        """Set value in nested dictionary."""
        current = data
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        final_key = path[-1]
        if final_key in current and current[final_key] is not None:
            current[final_key] = self._apply_strategy(strategy, str(current[final_key]))


class AnonymizationRule:
    """Defines an anonymization rule."""

    def __init__(
        self,
        name: str,
        field_mappings: dict[str, str],
        is_reversible: bool = False,
    ) -> None:
        """
        Initialize an anonymization rule.

        Args:
            name: Rule name
            field_mappings: Mapping of field names to strategies
            is_reversible: Whether this rule is reversible (pseudonymization)
        """
        self.name = name
        self.field_mappings = field_mappings
        self.is_reversible = is_reversible

    def apply(self, data: dict[str, Any], anonymizer: Anonymizer) -> dict[str, Any]:
        """Apply this rule to data."""
        if self.is_reversible:
            result, _ = anonymizer.pseudonymize(data, self.field_mappings)
            return result
        return anonymizer.anonymize(data, self.field_mappings)


class AnonymizationRuleSet:
    """Collection of anonymization rules."""

    def __init__(self) -> None:
        """Initialize the rule set."""
        self._rules: dict[str, AnonymizationRule] = {}
        self._anonymizer = Anonymizer()

    def add_rule(self, rule: AnonymizationRule) -> None:
        """Add a rule to the set."""
        self._rules[rule.name] = rule

    def apply(self, rule_name: str, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        """
        Apply a rule by name.

        Args:
            rule_name: Name of rule to apply
            data: Data to anonymize

        Returns:
            Anonymized data or None if rule not found
        """
        rule = self._rules.get(rule_name)
        if rule:
            return rule.apply(data, self._anonymizer)
        return None

    def apply_all(self, data: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """
        Apply all rules to data.

        Args:
            data: Data to anonymize

        Returns:
            Dictionary mapping rule names to anonymized data
        """
        results = {}
        for rule_name, rule in self._rules.items():
            results[rule_name] = rule.apply(data, self._anonymizer)
        return results

    def get_rule(self, name: str) -> Optional[AnonymizationRule]:
        """Get a rule by name."""
        return self._rules.get(name)

    def list_rules(self) -> list[AnonymizationRule]:
        """Get all rules."""
        return list(self._rules.values())
