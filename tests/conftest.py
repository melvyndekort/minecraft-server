"""Module-level env vars discord_bot.handler reads at import time."""

import os

os.environ.setdefault("DISCORD_PUBLIC_KEY", "0" * 64)
os.environ.setdefault("DISCORD_APPLICATION_ID", "123456789")
os.environ.setdefault("ECS_CLUSTER", "minecraft-cluster")
os.environ.setdefault("ECS_SERVICE", "minecraft-service")
