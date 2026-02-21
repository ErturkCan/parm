# PARM Privacy Model

## Overview

Privacy in PARM is enforced at the **platform level**, not per-product. This means:

- Single source of truth for privacy policies
- Consistent enforcement across all products
- Centralized audit logging
- Cryptographic guarantees for data protection

## Data Classification

PARM defines four levels of data sensitivity:

### PUBLIC
**Examples**: Public product information, published articles, general announcements

**Restrictions**:
- Allowed operations: read, share
- Requires consent: NO
- Min access level: user
- Retention: indefinite (typically)
- Anonymization: none required

**Use case**: Marketing content, published APIs

### INTERNAL
**Examples**: Internal documentation, employee info, non-sensitive business data

**Restrictions**:
- Allowed operations: read, write
- Requires consent: NO
- Min access level: user (authenticated users)
- Retention: 30 days (default)
- Anonymization: optional

**Use case**: Application configuration, general user profiles

### SENSITIVE
**Examples**: Health data, contact information, behavioral data, email addresses

**Restrictions**:
- Allowed operations: read, write
- Requires consent: YES
- Min access level: admin
- Retention: 7 days (default)
- Anonymization: hash email, mask phone, suppress SSN

**Use case**: User preferences, dietary restrictions, location history

**Applicable Products**:
- Clueat: Allergen profiles, dietary restrictions
- KeepClos: Contact information, relationship history
- CanDelivers: Delivery addresses, phone numbers

### RESTRICTED
**Examples**: Financial data, government IDs, biometric data, passwords

**Restrictions**:
- Allowed operations: read only
- Requires consent: YES
- Min access level: system (administrative)
- Retention: 1 day (default, minimal)
- Anonymization: suppress everything sensitive

**Use case**: Payment information (never stored), authentication credentials

**Note**: PARM explicitly does NOT store restricted data. External payment processors handle financial data.

## Privacy Policies

A PrivacyPolicy declaratively defines rules for data handling:

```python
from parm_privacy import create_sensitive_policy

policy = create_sensitive_policy(
    name="user_allergen_data",
    retention_days=7
)
```

### Policy Components

**name**: Unique policy identifier
- Used when registering and evaluating

**data_classification**: Sensitivity level
- PUBLIC, INTERNAL, SENSITIVE, RESTRICTED

**retention_period**: How long to keep data
- timedelta object
- None = indefinite
- Enforced by scheduled cleanup jobs

**allowed_operations**: Which operations are permitted
- "read", "write", "delete", "share"
- Empty list = deny all

**requires_consent**: Does user consent need to be documented?
- YES for SENSITIVE and RESTRICTED
- NO for PUBLIC and INTERNAL

**anonymization_rules**: Transformations to apply
- Field name → strategy ("hash", "mask", "generalize", "suppress")
- Applied before sharing or backup

**min_access_level**: Minimum role to access
- "user": any authenticated user
- "admin": administrators
- "system": platform only

## Access Control

Access is evaluated at retrieval time using:

1. **Data Classification**: Determines baseline restrictions
2. **Explicit Policy**: Additional rules beyond classification
3. **Accessor Level**: Role/level of requester
4. **Operation**: read, write, delete, share
5. **Consent Status**: Has user consented to this operation?

### Accessor Levels

```
user (rank 1)
  ↓
admin (rank 2)
  ↓
system (rank 3)
```

Higher rank can do anything lower rank can do, plus more.

### Evaluation Logic

```python
# Is this access allowed?
policy = get_policy("user_email")

result = policy_engine.evaluate(
    policy_name="user_email",
    operation="read",
    accessor="analytics_service",
    accessor_level="system"
)

# Decision: YES if all of:
# 1. "read" in policy.allowed_operations
# 2. rank(accessor_level) >= rank(policy.min_access_level)
# 3. NOT policy.requires_consent OR consent_recorded
```

## Encrypted Data Vault

The DataVault provides encrypted storage with cryptographic guarantees:

### Encryption Spec
- **Algorithm**: AES-256-GCM (Galois/Counter Mode)
- **Key Size**: 256 bits
- **IV Size**: 96 bits (12 bytes), randomly generated per encryption
- **Key Derivation**: PBKDF2 with SHA-256, 100,000 iterations

### Usage

```python
from parm_privacy import DataVault, create_sensitive_policy

vault = DataVault(master_password="platform_password")

# Store data
policy = create_sensitive_policy("user_allergies")
vault.store(
    key="user_123_allergies",
    data={"peanuts": True, "tree_nuts": True},
    policy=policy,
    accessor="user_auth_service"
)

# Retrieve data
result = vault.retrieve(
    key="user_123_allergies",
    accessor="clueat_service",
    accessor_level="admin"  # Clueat is an admin service
)

if result.is_success():
    allergies = result.data
```

### Audit Trail

Every access attempt is logged:

```python
audit_log = vault.audit_log()
# [
#   AuditLogEntry(timestamp=..., operation="store", key=...,
#                 accessor="...", success=True),
#   AuditLogEntry(timestamp=..., operation="retrieve", key=...,
#                 accessor="...", success=True),
# ]
```

Logs include:
- Timestamp of operation
- Operation type (store, retrieve, delete)
- Data key accessed
- Accessor identity
- Success/failure
- Error message if failed

**Use Cases for Audit Logs**:
- Compliance reporting (who accessed what, when)
- Security investigation (detect unauthorized access)
- User transparency (show users their data access)

## Data Anonymization

Anonymization is applied when:
- Exporting data for analysis
- Sharing data with external parties
- Creating backups for non-production
- Generating reports

### Anonymization Strategies

#### Hash
One-way cryptographic hash (SHA-256)

```python
Anonymizer().anonymize(
    {"email": "user@example.com"},
    {"email": "hash"}
)
# Result: {"email": "abc123def456..."}
```

**Use for**: Email, phone, identifiers where you need uniqueness but not reversibility

#### Mask
Show only first and last character

```python
Anonymizer().anonymize(
    {"phone": "555-123-4567"},
    {"phone": "mask"}
)
# Result: {"phone": "5***7"}
```

**Use for**: Phone numbers, credit card numbers (PCI-DSS guidance)

#### Generalize
Replace with range or category

```python
Anonymizer().anonymize(
    {"age": "32"},
    {"age": "generalize"}
)
# Result: {"age": "30-39"}
```

**Use for**: Ages, salaries, demographics for statistical analysis

#### Suppress
Replace with placeholder

```python
Anonymizer().anonymize(
    {"ssn": "123-45-6789"},
    {"ssn": "suppress"}
)
# Result: {"ssn": "***"}
```

**Use for**: Sensitive IDs, financial data that shouldn't be visible

### Reusable Rules

Define anonymization rules once, apply many times:

```python
from parm_privacy import AnonymizationRuleSet

rules = AnonymizationRuleSet()
rules.add_rule(AnonymizationRule(
    name="user_for_analytics",
    field_mappings={
        "email": "hash",
        "phone": "mask",
        "age": "generalize",
        "ssn": "suppress"
    }
))

# Apply the rule
anonymized = rules.apply("user_for_analytics", user_data)
```

### Reversible Pseudonymization

For internal use (e.g., generating reports that reference original data):

```python
# Reversible for internal use
pseudonymized, mapping = anonymizer.pseudonymize(
    data={"user_id": "123", "email": "user@example.com"},
    rules={"email": "hash"}
)
# mapping = {"abc123...": "user@example.com"}

# Later, map back to original (only with access to mapping dict)
original_email = mapping[pseudonymized["email"]]
```

**Important**: Pseudonymization mapping should be stored separately and encrypted.

## Consent Management

Some policies require documented consent before data access:

```python
# Consent is required
policy = create_sensitive_policy("user_location")

# Before accessing, check and record consent
if not consent_recorded_for(user_id, "location_tracking"):
    return Result.failure("Consent required")

# After user consents (via UI), record it
record_consent(user_id, "location_tracking", timestamp)

# Now access is allowed
location = vault.retrieve("user_123_location", "tracking_service", "admin")
```

**Consent Lifecycle**:
1. User performs action (e.g., clicks "Allow")
2. Consent is recorded with timestamp
3. Data operations become allowed
4. User can withdraw consent (hard delete)

## Privacy by Product

### CanDelivers
**Data Types**: Delivery addresses, phone numbers, route history
**Classification**: SENSITIVE
**Special Handling**:
- Addresses expire after 30 days
- Phone numbers masked except for delivery
- Route history pseudonymized for analytics

**Policy Example**:
```python
policy = PrivacyPolicy(
    name="delivery_data",
    data_classification=DataClassification.SENSITIVE,
    retention_period=timedelta(days=30),
    allowed_operations=["read", "write"],
    requires_consent=True,
    min_access_level="admin",
    anonymization_rules={
        "phone": "mask",
        "address": "hash",
        "route_history": "suppress"
    }
)
```

### Clueat
**Data Types**: Allergen profiles, dietary restrictions, ingredient info
**Classification**: SENSITIVE
**Special Handling**:
- Critical for health—stricter consent
- Cannot share with third parties
- User has explicit access to all stored data

**Policy Example**:
```python
policy = PrivacyPolicy(
    name="allergen_data",
    data_classification=DataClassification.SENSITIVE,
    retention_period=timedelta(days=7),  # Short retention
    allowed_operations=["read", "write"],
    requires_consent=True,
    min_access_level="admin",
    anonymization_rules={
        "user_id": "suppress",  # No user tracking in backups
        "allergies": "suppress"  # Sensitive health data
    }
)
```

### KeepClos
**Data Types**: Relationship info, contact history, reminder timing
**Classification**: INTERNAL to SENSITIVE
**Special Handling**:
- Contact info is SENSITIVE
- Relationship scoring is INTERNAL
- Interaction history pseudonymized

**Policy Example**:
```python
policy = PrivacyPolicy(
    name="relationship_data",
    data_classification=DataClassification.INTERNAL,
    retention_period=timedelta(days=90),
    allowed_operations=["read", "write"],
    requires_consent=False,  # User consented when connecting
    min_access_level="user",
    anonymization_rules={
        "phone": "mask",
        "email": "hash",
        "relationship_data": "generalize"
    }
)
```

## Compliance & Auditing

### GDPR Considerations
- **Right to be forgotten**: Delete user's personal data from vault
- **Right to access**: Retrieve all data stored about you
- **Right to portability**: Export data in standard format
- **Data minimization**: Only store what's necessary

Implementation:
```python
# Right to be forgotten
vault.delete_by_owner(user_id, accessor_level="system")

# Right to access
user_data = vault.audit_log_for_accessor(user_id)

# Right to portability
export_format = export_user_data(user_id, format="json")
```

### Audit Reporting
```python
# Compliance report: who accessed sensitive data this month?
sensitive_policies = [p for p in policy_engine.list_policies()
                      if p.data_classification == DataClassification.SENSITIVE]

for policy in sensitive_policies:
    access_log = vault.audit_log_for_key(policy.name)
    unauthorized = [entry for entry in access_log
                    if not entry.success]
    print(f"Policy: {policy.name}, Unauthorized attempts: {len(unauthorized)}")
```

### Data Retention Policy
```python
# Enforce retention periods
for key in vault.keys():
    policy = vault.get_policy(key)
    if policy.retention_period:
        age = now() - vault.get_creation_time(key)
        if age > policy.retention_period:
            vault.delete(key)  # Automatic cleanup
```

## Best Practices

1. **Always use DataVault for sensitive data**
   - Never store in logs or config
   - Always reference by key, not value

2. **Apply anonymization for exports**
   - Before sending to analytics
   - Before creating backups
   - Before sharing reports

3. **Document consent**
   - Timestamp when user grants/revokes
   - Keep audit trail for 7 years (GDPR requirement)

4. **Regular audits**
   - Review access logs monthly
   - Check for unauthorized access patterns
   - Validate data retention policies

5. **Classify data correctly**
   - Err on the side of SENSITIVE
   - Upgrade classification if data combines with other data
   - Review classifications quarterly

## Limitations

PARM does NOT:
- Provide encryption in transit (use HTTPS/TLS)
- Handle key management (use external KMS)
- Provide anonymization verification (can't prove data is truly anonymized)
- Support multi-region compliance (all in single region)
- Encrypt backups (wrap vault key separately)

For these, use complementary tools:
- TLS: Load balancer or reverse proxy
- Key management: AWS KMS, HashiCorp Vault
- Anonymization testing: ARX Data Anonymization
- Regional compliance: Kubernetes DaemonSets per region
- Backup encryption: Sealed Secrets, SOPS
