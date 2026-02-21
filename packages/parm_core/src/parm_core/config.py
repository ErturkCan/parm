"""Configuration management for PARM."""

import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@dataclass
class EventsConfig:
    """Event bus configuration."""
    enabled: bool = True
    max_history_size: int = 1000
    async_dispatch: bool = True


@dataclass
class AgentConfig:
    """Agent orchestration configuration."""
    max_concurrent_agents: int = 10
    default_timeout_seconds: int = 60
    retry_max_attempts: int = 3
    retry_backoff_factor: float = 2.0


@dataclass
class WorkflowConfig:
    """Workflow execution configuration."""
    max_concurrent_workflows: int = 5
    default_step_timeout_seconds: int = 30
    enable_step_caching: bool = False
    enable_parallel_steps: bool = True


@dataclass
class ContextConfig:
    """Context resolution configuration."""
    default_ttl_seconds: int = 3600
    enable_caching: bool = True
    max_cache_size: int = 1000


@dataclass
class PrivacyConfig:
    """Privacy and data handling configuration."""
    enable_encryption: bool = True
    encryption_algorithm: str = "AES-256-GCM"
    enable_audit_logging: bool = True
    audit_log_retention_days: int = 365
    enable_anonymization: bool = True


@dataclass
class IntegrationConfig:
    """Integration configuration."""
    http_timeout_seconds: int = 30
    http_max_retries: int = 3
    http_retry_backoff_factor: float = 2.0
    enable_circuit_breaker: bool = True
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout_seconds: int = 60


@dataclass
class ParmConfig:
    """Root PARM configuration."""
    environment: str = "development"
    debug: bool = False
    version: str = "0.1.0"

    logging: LoggingConfig = field(default_factory=LoggingConfig)
    events: EventsConfig = field(default_factory=EventsConfig)
    agents: AgentConfig = field(default_factory=AgentConfig)
    workflows: WorkflowConfig = field(default_factory=WorkflowConfig)
    context: ContextConfig = field(default_factory=ContextConfig)
    privacy: PrivacyConfig = field(default_factory=PrivacyConfig)
    integrations: IntegrationConfig = field(default_factory=IntegrationConfig)

    @classmethod
    def from_toml(cls, path: str) -> "ParmConfig":
        """
        Load configuration from a TOML file.

        Args:
            path: Path to TOML configuration file

        Returns:
            ParmConfig instance
        """
        with open(path, "rb") as f:
            config_dict = tomllib.load(f)

        return cls.from_dict(config_dict)

    @classmethod
    def from_env(cls) -> "ParmConfig":
        """
        Load configuration from environment variables.
        Environment variables should be prefixed with PARM_ and use __ for nested keys.
        Example: PARM_AGENTS__MAX_CONCURRENT_AGENTS=20

        Returns:
            ParmConfig instance
        """
        config_dict = {}

        for key, value in os.environ.items():
            if not key.startswith("PARM_"):
                continue

            # Remove PARM_ prefix and convert to lowercase
            key = key[5:].lower()

            # Parse nested keys (e.g., agents__max_concurrent_agents)
            parts = key.split("__")

            # Convert value to appropriate type
            if value.lower() in ("true", "false"):
                value = value.lower() == "true"
            elif value.isdigit():
                value = int(value)
            else:
                try:
                    value = float(value)
                except ValueError:
                    pass  # Keep as string

            # Build nested dictionary
            current = config_dict
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            current[parts[-1]] = value

        return cls.from_dict(config_dict)

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> "ParmConfig":
        """
        Create configuration from a dictionary.

        Args:
            config_dict: Configuration dictionary

        Returns:
            ParmConfig instance
        """
        # Extract top-level settings
        environment = config_dict.get("environment", "development")
        debug = config_dict.get("debug", False)
        version = config_dict.get("version", "0.1.0")

        # Extract sub-configurations
        logging_config = LoggingConfig(**config_dict.get("logging", {}))
        events_config = EventsConfig(**config_dict.get("events", {}))
        agents_config = AgentConfig(**config_dict.get("agents", {}))
        workflows_config = WorkflowConfig(**config_dict.get("workflows", {}))
        context_config = ContextConfig(**config_dict.get("context", {}))
        privacy_config = PrivacyConfig(**config_dict.get("privacy", {}))
        integrations_config = IntegrationConfig(**config_dict.get("integrations", {}))

        return cls(
            environment=environment,
            debug=debug,
            version=version,
            logging=logging_config,
            events=events_config,
            agents=agents_config,
            workflows=workflows_config,
            context=context_config,
            privacy=privacy_config,
            integrations=integrations_config,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return asdict(self)

    @classmethod
    def load(cls, config_file: Optional[str] = None) -> "ParmConfig":
        """
        Load configuration from file, environment, or use defaults.

        Priority:
        1. Explicit config file
        2. PARM_CONFIG environment variable
        3. Environment variables with PARM_ prefix
        4. Default configuration

        Args:
            config_file: Optional explicit config file path

        Returns:
            ParmConfig instance
        """
        if config_file:
            return cls.from_toml(config_file)

        env_config = os.getenv("PARM_CONFIG")
        if env_config and Path(env_config).exists():
            return cls.from_toml(env_config)

        # Try to load from environment variables
        config_dict = {}
        for key, value in os.environ.items():
            if key.startswith("PARM_"):
                config_dict[key] = value

        if config_dict:
            return cls.from_env()

        # Return default configuration
        return cls()


# Global configuration instance
_global_config: Optional[ParmConfig] = None


def get_config() -> ParmConfig:
    """Get the global PARM configuration."""
    global _global_config
    if _global_config is None:
        _global_config = ParmConfig.load()
    return _global_config


def set_config(config: ParmConfig) -> None:
    """Set the global PARM configuration."""
    global _global_config
    _global_config = config


def load_config(config_file: Optional[str] = None) -> ParmConfig:
    """Load and set the global PARM configuration."""
    config = ParmConfig.load(config_file)
    set_config(config)
    return config
