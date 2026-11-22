"""Tests for configuration module."""

import os
from unittest.mock import patch

import pytest

from minecraft_tools.config import IdleWatcherConfig


class TestIdleWatcherConfig:
    """Test idle watcher configuration."""

    def test_from_env_complete(self):
        """Test configuration with all environment variables."""
        env_vars = {
            "ECS_CLUSTER": "test_cluster",
            "ECS_SERVICE": "test_service",
            "RCON_HOST": "mc.example.com",
            "RCON_PORT": "25576",
            "RCON_PASSWORD": "testpass",
            "CHECK_INTERVAL": "120",
            "IDLE_THRESHOLD": "300",
        }

        with patch.dict(os.environ, env_vars):
            config = IdleWatcherConfig.from_env()

        assert config.ecs_cluster == "test_cluster"
        assert config.rcon_host == "mc.example.com"
        assert config.rcon_port == 25576
        assert config.rcon_password == "testpass"
        assert config.discord_webhook == ""
        assert config.dns_name == ""
        assert config.check_interval == 120
        assert config.idle_threshold == 300

    def test_from_env_with_defaults(self):
        """Test configuration with default values."""
        env_vars = {
            "ECS_CLUSTER": "test_cluster",
            "ECS_SERVICE": "test_service",
            "RCON_HOST": "mc.example.com",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = IdleWatcherConfig.from_env()

        assert config.rcon_port == 25575
        assert config.rcon_password == ""
        assert config.discord_webhook == ""
        assert config.dns_name == ""
        assert config.check_interval == 300
        assert config.idle_threshold == 600

    def test_missing_host_raises_error(self):
        """Test error when RCON host is missing."""
        env_vars = {"ECS_CLUSTER": "test", "ECS_SERVICE": "test"}
        with (
            patch.dict(os.environ, env_vars, clear=True),
            pytest.raises(
                ValueError, match="RCON_HOST environment variable is required"
            ),
        ):
            IdleWatcherConfig.from_env()
