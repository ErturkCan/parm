"""Encrypted data vault for sensitive information."""

import base64
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from os import urandom

from parm_core import PrivacyPolicy, Result


@dataclass
class AuditLogEntry:
    """Entry in the data vault audit log."""
    timestamp: datetime
    operation: str
    key: str
    accessor: str
    success: bool
    error: Optional[str] = None


class DataVault:
    """
    Encrypted storage for sensitive data.
    Uses AES-256-GCM encryption.
    Requires policy evaluation for access.
    Maintains audit log of all operations.
    """

    def __init__(self, master_password: str) -> None:
        """
        Initialize the data vault.

        Args:
            master_password: Master password for encryption key derivation
        """
        self._data: dict[str, dict[str, Any]] = {}
        self._policies: dict[str, PrivacyPolicy] = {}
        self._audit_log: list[AuditLogEntry] = []
        self._master_key = self._derive_key(master_password)

    def store(
        self,
        key: str,
        data: Any,
        policy: PrivacyPolicy,
        accessor: str = "system",
    ) -> Result[None]:
        """
        Store encrypted data in the vault.

        Args:
            key: Unique key for the data
            data: Data to store
            policy: Privacy policy for this data
            accessor: ID of entity storing the data

        Returns:
            Result indicating success or failure
        """
        try:
            # Validate policy
            if policy.requires_consent and accessor == "system":
                return Result.failure("Consent required for sensitive data storage")

            # Serialize data
            json_data = json.dumps(data)
            plaintext = json_data.encode("utf-8")

            # Generate IV
            iv = urandom(12)  # 96-bit IV for GCM

            # Encrypt
            cipher = AESGCM(self._master_key)
            ciphertext = cipher.encrypt(iv, plaintext, None)

            # Store encrypted data with metadata
            self._data[key] = {
                "iv": base64.b64encode(iv).decode("utf-8"),
                "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
                "policy_name": policy.name,
                "stored_at": datetime.now().isoformat(),
                "accessor": accessor,
            }

            self._policies[key] = policy

            # Log operation
            self._log_operation("store", key, accessor, True)

            return Result.success(None)
        except Exception as e:
            self._log_operation("store", key, accessor, False, str(e))
            return Result.failure(f"Failed to store data: {str(e)}")

    def retrieve(
        self,
        key: str,
        accessor: str,
        accessor_level: str = "user",
    ) -> Result[Any]:
        """
        Retrieve and decrypt data from the vault.

        Args:
            key: Key of data to retrieve
            accessor: ID of entity retrieving data
            accessor_level: Access level of accessor

        Returns:
            Result with decrypted data or error
        """
        try:
            if key not in self._data:
                self._log_operation("retrieve", key, accessor, False, "Key not found")
                return Result.failure(f"Data with key '{key}' not found")

            policy = self._policies.get(key)
            if not policy:
                return Result.failure(f"No policy found for key '{key}'")

            # Check access level
            level_rank = {"user": 1, "admin": 2, "system": 3}
            accessor_rank = level_rank.get(accessor_level, 0)
            required_rank = level_rank.get(policy.min_access_level, 0)

            if accessor_rank < required_rank:
                self._log_operation(
                    "retrieve",
                    key,
                    accessor,
                    False,
                    f"Insufficient access level: {accessor_level}",
                )
                return Result.failure("Insufficient access level")

            # Decrypt
            stored_data = self._data[key]
            iv = base64.b64decode(stored_data["iv"])
            ciphertext = base64.b64decode(stored_data["ciphertext"])

            cipher = AESGCM(self._master_key)
            plaintext = cipher.decrypt(iv, ciphertext, None)

            data = json.loads(plaintext.decode("utf-8"))

            # Log operation
            self._log_operation("retrieve", key, accessor, True)

            return Result.success(data)
        except Exception as e:
            self._log_operation("retrieve", key, accessor, False, str(e))
            return Result.failure(f"Failed to retrieve data: {str(e)}")

    def delete(
        self,
        key: str,
        accessor: str,
        accessor_level: str = "admin",
    ) -> Result[None]:
        """
        Delete encrypted data from the vault.

        Args:
            key: Key of data to delete
            accessor: ID of entity deleting data
            accessor_level: Access level of accessor

        Returns:
            Result indicating success or failure
        """
        try:
            if key not in self._data:
                return Result.failure(f"Data with key '{key}' not found")

            # Check access level (deletion requires higher privilege)
            level_rank = {"user": 1, "admin": 2, "system": 3}
            accessor_rank = level_rank.get(accessor_level, 0)

            if accessor_rank < 2:  # Require at least admin
                self._log_operation(
                    "delete",
                    key,
                    accessor,
                    False,
                    "Insufficient access level",
                )
                return Result.failure("Insufficient access level for deletion")

            self._data.pop(key)
            self._policies.pop(key, None)

            self._log_operation("delete", key, accessor, True)
            return Result.success(None)
        except Exception as e:
            self._log_operation("delete", key, accessor, False, str(e))
            return Result.failure(f"Failed to delete data: {str(e)}")

    def audit_log(self) -> list[AuditLogEntry]:
        """Get the audit log."""
        return self._audit_log.copy()

    def audit_log_for_key(self, key: str) -> list[AuditLogEntry]:
        """Get audit log entries for a specific key."""
        return [entry for entry in self._audit_log if entry.key == key]

    def audit_log_for_accessor(self, accessor: str) -> list[AuditLogEntry]:
        """Get audit log entries for a specific accessor."""
        return [entry for entry in self._audit_log if entry.accessor == accessor]

    def clear_audit_log(self) -> None:
        """Clear the audit log (use with caution)."""
        self._audit_log.clear()

    def _log_operation(
        self,
        operation: str,
        key: str,
        accessor: str,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Log an operation in the audit log."""
        entry = AuditLogEntry(
            timestamp=datetime.now(),
            operation=operation,
            key=key,
            accessor=accessor,
            success=success,
            error=error,
        )
        self._audit_log.append(entry)

    @staticmethod
    def _derive_key(password: str, salt: Optional[bytes] = None) -> bytes:
        """Derive encryption key from password."""
        if salt is None:
            salt = b"parm_vault_salt"  # In production, use random salt

        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,  # 256-bit key
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(password.encode("utf-8"))
