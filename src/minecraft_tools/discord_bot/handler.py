"""Lambda entry point: dispatches on event shape.

Two distinct callers invoke this one function (same pattern as
aws-idc-pim's handler.py -- see
Tech/Homelab/planning/minecraft-subaccount-and-lambda-bot-migration.md):

1. Discord's HTTP Interactions endpoint (Lambda Function URL, synchronous).
   Must ACK within Discord's ~3s budget, so it only verifies the signature
   and returns PONG / an immediate or deferred response, then re-invokes
   itself asynchronously (InvocationType=Event) for anything that needs a
   real ECS call.
2. Its own async self-invocation (`action: process_command`) -- does the
   actual ECS describe/update call and edits the deferred response with
   the real result.
"""

import json
import logging
import os
from typing import Any

import boto3

from minecraft_tools.discord_bot import discord_api, ecs_control
from minecraft_tools.discord_bot.discord_verify import verify_discord_signature

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

DISCORD_PUBLIC_KEY = os.environ["DISCORD_PUBLIC_KEY"]
DISCORD_APPLICATION_ID = os.environ["DISCORD_APPLICATION_ID"]
ECS_CLUSTER = os.environ["ECS_CLUSTER"]
ECS_SERVICE = os.environ["ECS_SERVICE"]
# Optional: restrict commands to one channel, same behaviour as the old
# gateway bot's ChannelRestrictedTree. Unset = no restriction.
DISCORD_CHANNEL_ID = os.environ.get("DISCORD_CHANNEL_ID")

PING = 1
APPLICATION_COMMAND = 2
PONG = 1
CHANNEL_MESSAGE_WITH_SOURCE = 4
DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE = 5

HELP_TEXT = """
🎮 **Minecraft Server Bot Commands**

`/mc-start` - Start the Minecraft server (scale to 1 task)
`/mc-stop` - Stop the Minecraft server (scale to 0 tasks)
`/mc-status` - Check current server status and IP addresses
`/mc-help` - Show this help message

The server runs on AWS ECS Fargate and may take a few minutes to start up.
"""


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Route to the right handler based on which caller invoked this Lambda."""
    if _is_discord_invocation(event):
        return _handle_discord_invocation(event, context)
    if event.get("action") == "process_command":
        _process_command(event)
        return {}
    raise ValueError(f"Unrecognized event shape: {list(event.keys())}")


def _is_discord_invocation(event: dict[str, Any]) -> bool:
    """True iff this invocation came from Discord's Function URL, not a self-invoke."""
    return "headers" in event and "body" in event


def _handle_discord_invocation(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Verify + ACK synchronously; hand slow commands to an async self-invoke."""
    headers = {k.lower(): v for k, v in event.get("headers", {}).items()}
    signature = headers.get("x-signature-ed25519", "")
    timestamp = headers.get("x-signature-timestamp", "")
    body = event.get("body", "")

    if not verify_discord_signature(DISCORD_PUBLIC_KEY, signature, timestamp, body):
        logger.warning("Rejected interaction with invalid signature")
        return {"statusCode": 401, "body": "invalid request signature"}

    interaction = json.loads(body)

    if interaction["type"] == PING:
        return _json_response({"type": PONG})

    if interaction["type"] != APPLICATION_COMMAND:
        return _json_response(
            {
                "type": CHANNEL_MESSAGE_WITH_SOURCE,
                "data": {"content": "Unsupported interaction"},
            }
        )

    if DISCORD_CHANNEL_ID and str(interaction.get("channel_id")) != DISCORD_CHANNEL_ID:
        return _json_response(
            {
                "type": CHANNEL_MESSAGE_WITH_SOURCE,
                "data": {
                    "content": f"❌ Use this bot in <#{DISCORD_CHANNEL_ID}>.",
                    "flags": 64,  # ephemeral
                },
            }
        )

    command = interaction["data"]["name"]

    if command == "mc-help":
        return _json_response(
            {
                "type": CHANNEL_MESSAGE_WITH_SOURCE,
                "data": {"content": HELP_TEXT},
            }
        )

    _invoke_async(context, {"action": "process_command", "interaction": interaction})
    return _json_response({"type": DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE})


def _process_command(event: dict[str, Any]) -> None:
    """Do the real ECS work for a command and post the Discord followup."""
    interaction = event["interaction"]
    token = interaction["token"]
    command = interaction["data"]["name"]

    ecs_client = boto3.client("ecs")
    ec2_client = boto3.client("ec2")

    try:
        if command == "mc-start":
            result = ecs_control.update_service(
                ecs_client, ec2_client, ECS_CLUSTER, ECS_SERVICE, 1
            )
        elif command == "mc-stop":
            result = ecs_control.update_service(
                ecs_client, ec2_client, ECS_CLUSTER, ECS_SERVICE, 0
            )
        elif command == "mc-status":
            status = ecs_control.get_service_status(
                ecs_client, ec2_client, ECS_CLUSTER, ECS_SERVICE
            )
            result = ecs_control.format_status(ECS_SERVICE, status)
        else:
            result = f"❌ Unknown command: {command}"
    except Exception:  # pylint: disable=broad-except
        logger.exception("Unexpected error processing command %s", command)
        result = "❌ An unexpected error occurred. Check CloudWatch Logs."

    discord_api.followup_message(DISCORD_APPLICATION_ID, token, result)


def _invoke_async(context: Any, payload: dict[str, Any]) -> None:
    """Re-invoke this same Lambda asynchronously to do the slow AWS work."""
    lambda_client = boto3.client("lambda")
    lambda_client.invoke(
        FunctionName=context.invoked_function_arn,
        InvocationType="Event",
        Payload=json.dumps(payload).encode("utf-8"),
    )


def _json_response(body: dict[str, Any]) -> dict[str, Any]:
    """Wrap a Discord interaction response body as a Function URL response."""
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
