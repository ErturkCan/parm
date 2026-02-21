"""Context frame implementation."""

from datetime import datetime, timedelta
from typing import Any

from parm_core import ContextFrame as CoreContextFrame


def create_context_frame(
    entity_id: str,
    entity_type: str,
    timestamp: datetime,
    temporal_info: dict[str, Any],
    spatial_info: dict[str, Any],
    relational_info: dict[str, Any],
    domain_data: dict[str, Any],
    source: str = "unknown",
    ttl: timedelta = None,
) -> CoreContextFrame:
    """
    Create a context frame.

    Args:
        entity_id: ID of the entity
        entity_type: Type of entity
        timestamp: Timestamp of context
        temporal_info: When-related data
        spatial_info: Where-related data
        relational_info: Who-related data
        domain_data: Domain-specific data
        source: Source of context
        ttl: Time to live

    Returns:
        ContextFrame instance
    """
    return CoreContextFrame(
        entity_id=entity_id,
        entity_type=entity_type,
        timestamp=timestamp,
        temporal_info=temporal_info,
        spatial_info=spatial_info,
        relational_info=relational_info,
        domain_data=domain_data,
        source=source,
        ttl=ttl,
    )
