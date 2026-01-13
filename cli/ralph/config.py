"""Configuration loading and validation."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """Ralph configuration."""

    # Telegram notifications
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

    # Recovery settings
    recovery_enabled: bool = True
    recovery_delays: list[int] = field(default_factory=lambda: [600, 1200, 1800])
    context_overflow_max_retries: int = 2

    # Paths
    log_dir: Path = field(default_factory=lambda: Path.home() / ".claude/logs")
    scripts_dir: Path = field(default_factory=lambda: Path.home() / ".claude/scripts")
    cli_dir: Path = field(default_factory=lambda: Path.home() / ".claude/cli")

    @property
    def telegram_configured(self) -> bool:
        """Check if Telegram notifications are configured."""
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    @classmethod
    def load(cls, env_path: Optional[Path] = None) -> "Config":
        """Load configuration from .env file.

        Args:
            env_path: Path to .env file. If None, looks in scripts_dir.

        Returns:
            Config instance with loaded values.
        """
        if env_path is None:
            env_path = Path.home() / ".claude/scripts/.env"

        env_vars = _load_env_file(env_path)

        # Parse recovery delays
        delays_str = env_vars.get("RECOVERY_DELAYS", "600,1200,1800")
        try:
            delays = [int(d.strip()) for d in delays_str.split(",") if d.strip()]
        except ValueError:
            delays = [600, 1200, 1800]

        # Parse boolean
        recovery_enabled = env_vars.get("RECOVERY_ENABLED", "true").lower() in (
            "true",
            "1",
            "yes",
        )

        # Parse integer
        try:
            max_retries = int(env_vars.get("CONTEXT_OVERFLOW_MAX_RETRIES", "2"))
        except ValueError:
            max_retries = 2

        return cls(
            telegram_bot_token=env_vars.get("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=env_vars.get("TELEGRAM_CHAT_ID"),
            recovery_enabled=recovery_enabled,
            recovery_delays=delays,
            context_overflow_max_retries=max_retries,
        )


def _load_env_file(env_path: Path) -> dict[str, str]:
    """Load key=value pairs from .env file.

    Args:
        env_path: Path to .env file.

    Returns:
        Dictionary of environment variables.
    """
    env_vars: dict[str, str] = {}

    if not env_path.exists():
        return env_vars

    with open(env_path) as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue
            # Parse key=value
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                # Remove quotes if present
                if value and value[0] in ('"', "'") and value[-1] == value[0]:
                    value = value[1:-1]
                env_vars[key] = value

    return env_vars


# Global config instance (lazy loaded)
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = Config.load()
    return _config
