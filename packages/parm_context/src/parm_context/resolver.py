"""Context resolution from multiple providers."""

from datetime import datetime, timezone
from typing import Optional

from parm_core import ContextFrame

from .provider import ContextProvider, ContextProviderRegistry


class ContextResolver:
    """
    Gathers relevant context from all registered providers.
    Merges frames and resolves conflicts.
    """

    def __init__(self, registry: Optional[ContextProviderRegistry] = None) -> None:
        """
        Initialize the resolver.

        Args:
            registry: Context provider registry (creates new if not provided)
        """
        self.registry = registry or ContextProviderRegistry()

    def register_provider(self, provider: ContextProvider) -> None:
        """
        Register a context provider.

        Args:
            provider: Provider to register
        """
        self.registry.register(provider)

    def resolve(
        self,
        entity_id: str,
        entity_type: str,
        provider_names: Optional[list[str]] = None,
    ) -> Optional[ContextFrame]:
        """
        Resolve context for an entity from registered providers.

        Args:
            entity_id: Entity ID
            entity_type: Entity type
            provider_names: Optional list of specific providers to use

        Returns:
            Merged ContextFrame or None if no context available
        """
        providers = self.registry.get_all_providers()

        if provider_names:
            # Filter to specific providers
            providers = [
                p for p in providers if p.name in provider_names
            ]

        if not providers:
            return None

        # Collect frames from all providers
        frames = []
        for provider in providers:
            try:
                frame = provider.get_context(entity_id, entity_type)
                if frame and not frame.is_expired():
                    frames.append(frame)
            except Exception:
                # Skip providers that error out
                pass

        if not frames:
            return None

        # Merge frames (most recent wins for conflicts)
        merged = frames[0]
        for frame in frames[1:]:
            merged = merged.merge(frame)

        return merged

    def resolve_with_fallback(
        self,
        entity_id: str,
        entity_type: str,
        default_frame: Optional[ContextFrame] = None,
    ) -> ContextFrame:
        """
        Resolve context with fallback to a default frame.

        Args:
            entity_id: Entity ID
            entity_type: Entity type
            default_frame: Fallback frame if nothing resolves

        Returns:
            ContextFrame (either resolved or default)
        """
        resolved = self.resolve(entity_id, entity_type)

        if resolved:
            return resolved

        if default_frame:
            return default_frame

        # Return minimal frame
        return ContextFrame(
            entity_id=entity_id,
            entity_type=entity_type,
            timestamp=datetime.now(timezone.utc),
            temporal_info={},
            spatial_info={},
            relational_info={},
            domain_data={},
            source="default",
        )

    def resolve_multiple(
        self,
        entities: list[tuple[str, str]],  # [(entity_id, entity_type), ...]
        provider_names: Optional[list[str]] = None,
    ) -> dict[str, ContextFrame]:
        """
        Resolve context for multiple entities.

        Args:
            entities: List of (entity_id, entity_type) tuples
            provider_names: Optional list of specific providers

        Returns:
            Dictionary mapping entity IDs to ContextFrames
        """
        results = {}

        for entity_id, entity_type in entities:
            frame = self.resolve(entity_id, entity_type, provider_names)
            if frame:
                results[entity_id] = frame

        return results
