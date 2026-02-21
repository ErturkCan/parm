"""Privacy policy definitions and enforcement."""

from dataclasses import dataclass, field
from typing import Any, Optional

from parm_core import DataClassification, PrivacyPolicy as CorePrivacyPolicy, Result


class PolicyEngine:
    """Evaluates policies against data access requests."""

    def __init__(self) -> None:
        """Initialize the policy engine."""
        self._policies: dict[str, CorePrivacyPolicy] = {}

    def register_policy(self, policy: CorePrivacyPolicy) -> None:
        """
        Register a privacy policy.

        Args:
            policy: PrivacyPolicy instance
        """
        self._policies[policy.name] = policy

    def get_policy(self, name: str) -> Optional[CorePrivacyPolicy]:
        """Get a policy by name."""
        return self._policies.get(name)

    def evaluate(
        self,
        policy_name: str,
        operation: str,
        accessor: str,
        accessor_level: str = "user",
    ) -> Result[bool]:
        """
        Evaluate whether an operation is allowed under a policy.

        Args:
            policy_name: Policy name
            operation: Operation to perform (read, write, delete, share)
            accessor: ID of entity requesting access
            accessor_level: Access level of accessor (user, admin, system)

        Returns:
            Result with True if allowed, False otherwise
        """
        policy = self._policies.get(policy_name)
        if not policy:
            return Result.failure(f"Policy '{policy_name}' not found")

        # Check if operation is allowed
        if policy.allowed_operations and operation not in policy.allowed_operations:
            return Result.failure(f"Operation '{operation}' not allowed by policy")

        # Check access level
        if self._get_access_level_rank(accessor_level) < self._get_access_level_rank(policy.min_access_level):
            return Result.failure(f"Access level '{accessor_level}' insufficient for policy")

        return Result.success(True)

    def check_requires_consent(self, policy_name: str) -> bool:
        """Check if a policy requires consent."""
        policy = self._policies.get(policy_name)
        return policy.requires_consent if policy else False

    def check_data_classification(self, classification: DataClassification) -> dict[str, Any]:
        """
        Get restrictions for a data classification.

        Args:
            classification: Data classification level

        Returns:
            Dictionary with restrictions
        """
        restrictions = {
            DataClassification.PUBLIC: {
                "allowed_operations": ["read", "share"],
                "requires_consent": False,
                "min_access_level": "user",
            },
            DataClassification.INTERNAL: {
                "allowed_operations": ["read", "write"],
                "requires_consent": False,
                "min_access_level": "user",
            },
            DataClassification.SENSITIVE: {
                "allowed_operations": ["read", "write"],
                "requires_consent": True,
                "min_access_level": "admin",
            },
            DataClassification.RESTRICTED: {
                "allowed_operations": ["read"],
                "requires_consent": True,
                "min_access_level": "system",
            },
        }
        return restrictions.get(classification, {})

    @staticmethod
    def _get_access_level_rank(level: str) -> int:
        """Get numeric rank of access level."""
        ranks = {
            "user": 1,
            "admin": 2,
            "system": 3,
        }
        return ranks.get(level, 0)

    def list_policies(self) -> list[CorePrivacyPolicy]:
        """Get all registered policies."""
        return list(self._policies.values())

    def clear(self) -> None:
        """Clear all policies."""
        self._policies.clear()


# Common policy templates
def create_public_policy(name: str) -> CorePrivacyPolicy:
    """Create a public data policy."""
    return CorePrivacyPolicy(
        name=name,
        data_classification=DataClassification.PUBLIC,
        allowed_operations=["read", "share"],
        requires_consent=False,
        min_access_level="user",
    )


def create_internal_policy(name: str, retention_days: int = 30) -> CorePrivacyPolicy:
    """Create an internal data policy."""
    from datetime import timedelta
    return CorePrivacyPolicy(
        name=name,
        data_classification=DataClassification.INTERNAL,
        retention_period=timedelta(days=retention_days),
        allowed_operations=["read", "write"],
        requires_consent=False,
        min_access_level="user",
    )


def create_sensitive_policy(name: str, retention_days: int = 7) -> CorePrivacyPolicy:
    """Create a sensitive data policy."""
    from datetime import timedelta
    return CorePrivacyPolicy(
        name=name,
        data_classification=DataClassification.SENSITIVE,
        retention_period=timedelta(days=retention_days),
        allowed_operations=["read", "write"],
        requires_consent=True,
        min_access_level="admin",
        anonymization_rules={
            "email": "hash",
            "phone": "mask",
            "ssn": "suppress",
        },
    )


def create_restricted_policy(name: str, retention_days: int = 1) -> CorePrivacyPolicy:
    """Create a restricted data policy."""
    from datetime import timedelta
    return CorePrivacyPolicy(
        name=name,
        data_classification=DataClassification.RESTRICTED,
        retention_period=timedelta(days=retention_days),
        allowed_operations=["read"],
        requires_consent=True,
        min_access_level="system",
        anonymization_rules={
            "ssn": "suppress",
            "credit_card": "suppress",
            "bank_account": "suppress",
        },
    )
