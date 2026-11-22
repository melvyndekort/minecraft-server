"""Configuration management for minecraft tools."""

import os
from dataclasses import dataclass


@dataclass
class IdleWatcherConfig:
    """Idle watcher configuration."""

    ecs_cluster: str
    ecs_service: str
    rcon_host: str
    rcon_port: int = 25575
    rcon_password: str = ""
    discord_webhook: str = ""
    dns_name: str = ""
    check_interval: int = 300  # 5 minutes
    idle_threshold: int = 600  # 10 minutes

    @classmethod
    def from_env(cls) -> "IdleWatcherConfig":
        """Create config from environment variables."""
        cluster = os.getenv("ECS_CLUSTER")
        service = os.getenv("ECS_SERVICE")
        rcon_host = os.getenv("RCON_HOST")
        rcon_password = os.getenv("RCON_PASSWORD", "")
        discord_webhook = os.getenv("DISCORD_WEBHOOK", "")
        dns_name = os.getenv("DNS_NAME", "")

        if not cluster:
            raise ValueError("ECS_CLUSTER environment variable is required")
        if not service:
            raise ValueError("ECS_SERVICE environment variable is required")
        if not rcon_host:
            raise ValueError("RCON_HOST environment variable is required")

        return cls(
            ecs_cluster=cluster,
            ecs_service=service,
            rcon_host=rcon_host,
            rcon_port=int(os.getenv("RCON_PORT", "25575")),
            rcon_password=rcon_password,
            discord_webhook=discord_webhook,
            dns_name=dns_name,
            check_interval=int(os.getenv("CHECK_INTERVAL", "300")),
            idle_threshold=int(os.getenv("IDLE_THRESHOLD", "600")),
        )
