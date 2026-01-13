"""Tests for configuration loading."""

import pytest
from pathlib import Path
from ralph.config import Config, _load_env_file


class TestLoadEnvFile:
    """Tests for _load_env_file function."""

    def test_load_basic(self, temp_dir):
        """Test loading basic key=value pairs."""
        env_file = temp_dir / ".env"
        env_file.write_text("""
KEY1=value1
KEY2=value2
""")
        result = _load_env_file(env_file)
        assert result["KEY1"] == "value1"
        assert result["KEY2"] == "value2"

    def test_load_with_quotes(self, temp_dir):
        """Test loading values with quotes."""
        env_file = temp_dir / ".env"
        env_file.write_text("""
KEY1="double quoted"
KEY2='single quoted'
""")
        result = _load_env_file(env_file)
        assert result["KEY1"] == "double quoted"
        assert result["KEY2"] == "single quoted"

    def test_skip_comments(self, temp_dir):
        """Test that comments are skipped."""
        env_file = temp_dir / ".env"
        env_file.write_text("""
# This is a comment
KEY1=value1
# Another comment
KEY2=value2
""")
        result = _load_env_file(env_file)
        assert len(result) == 2
        assert "# This is a comment" not in result

    def test_skip_empty_lines(self, temp_dir):
        """Test that empty lines are skipped."""
        env_file = temp_dir / ".env"
        env_file.write_text("""
KEY1=value1

KEY2=value2

""")
        result = _load_env_file(env_file)
        assert len(result) == 2

    def test_missing_file(self, temp_dir):
        """Test loading from missing file returns empty dict."""
        env_file = temp_dir / "nonexistent.env"
        result = _load_env_file(env_file)
        assert result == {}


class TestConfig:
    """Tests for Config dataclass."""

    def test_defaults(self):
        """Test default configuration values."""
        config = Config()

        assert config.telegram_bot_token is None
        assert config.telegram_chat_id is None
        assert config.recovery_enabled is True
        assert config.recovery_delays == [600, 1200, 1800]
        assert config.context_overflow_max_retries == 2

    def test_telegram_configured(self):
        """Test telegram_configured property."""
        config = Config()
        assert not config.telegram_configured

        config = Config(telegram_bot_token="token", telegram_chat_id="chat")
        assert config.telegram_configured

        config = Config(telegram_bot_token="token")
        assert not config.telegram_configured

    def test_load_from_env(self, temp_env_file):
        """Test loading configuration from .env file."""
        config = Config.load(temp_env_file)

        assert config.telegram_bot_token == "test_token_123"
        assert config.telegram_chat_id == "test_chat_456"
        assert config.recovery_enabled is True
        assert config.recovery_delays == [60, 120, 180]
        assert config.context_overflow_max_retries == 3

    def test_load_with_invalid_delays(self, temp_dir):
        """Test loading with invalid recovery delays."""
        env_file = temp_dir / ".env"
        env_file.write_text("RECOVERY_DELAYS=invalid,values")

        config = Config.load(env_file)
        # Should fall back to defaults
        assert config.recovery_delays == [600, 1200, 1800]

    def test_load_with_invalid_retries(self, temp_dir):
        """Test loading with invalid max retries."""
        env_file = temp_dir / ".env"
        env_file.write_text("CONTEXT_OVERFLOW_MAX_RETRIES=invalid")

        config = Config.load(env_file)
        # Should fall back to default
        assert config.context_overflow_max_retries == 2

    def test_load_recovery_disabled(self, temp_dir):
        """Test loading with recovery disabled."""
        env_file = temp_dir / ".env"
        env_file.write_text("RECOVERY_ENABLED=false")

        config = Config.load(env_file)
        assert config.recovery_enabled is False
