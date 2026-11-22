"""Tests for the Lambda-based Discord bot: signature verify + event dispatch."""

# pylint: disable=missing-function-docstring,protected-access

import json
from unittest.mock import MagicMock, patch

from nacl.signing import SigningKey

from minecraft_tools.discord_bot import handler
from minecraft_tools.discord_bot.discord_verify import verify_discord_signature


def _keypair():
    signing_key = SigningKey.generate()
    return signing_key, signing_key.verify_key.encode().hex()


def _sign(signing_key, timestamp, body):
    return signing_key.sign((timestamp + body).encode("utf-8")).signature.hex()


def _signed_request(signing_key, body_dict):
    body = json.dumps(body_dict)
    timestamp = "1700000000"
    signature = _sign(signing_key, timestamp, body)
    return {
        "headers": {
            "x-signature-ed25519": signature,
            "x-signature-timestamp": timestamp,
        },
        "body": body,
    }


# --- discord_verify -----------------------------------------------------


def test_valid_signature_verifies():
    signing_key, public_key_hex = _keypair()
    timestamp = "1700000000"
    body = '{"type":1}'
    signature_hex = _sign(signing_key, timestamp, body)

    assert verify_discord_signature(public_key_hex, signature_hex, timestamp, body)


def test_tampered_body_fails():
    signing_key, public_key_hex = _keypair()
    timestamp = "1700000000"
    signature_hex = _sign(signing_key, timestamp, '{"type":1}')

    assert not verify_discord_signature(
        public_key_hex, signature_hex, timestamp, '{"type":2}'
    )


def test_wrong_key_fails():
    signing_key, _ = _keypair()
    _, other_public_key_hex = _keypair()
    timestamp = "1700000000"
    body = '{"type":1}'
    signature_hex = _sign(signing_key, timestamp, body)

    assert not verify_discord_signature(
        other_public_key_hex, signature_hex, timestamp, body
    )


def test_malformed_signature_fails_cleanly():
    _, public_key_hex = _keypair()
    assert not verify_discord_signature(public_key_hex, "not-hex", "1700000000", "{}")


# --- handler: dispatch + signature gate ----------------------------------


def test_rejects_invalid_signature():
    event = {
        "headers": {"x-signature-ed25519": "00", "x-signature-timestamp": "1700000000"},
        "body": "{}",
    }
    response = handler.lambda_handler(event, MagicMock())
    assert response["statusCode"] == 401


@patch("minecraft_tools.discord_bot.handler.DISCORD_PUBLIC_KEY")
def test_ping_returns_pong(_unused_module_level_key):
    signing_key, public_key_hex = _keypair()
    with patch(
        "minecraft_tools.discord_bot.handler.DISCORD_PUBLIC_KEY", public_key_hex
    ):
        event = _signed_request(signing_key, {"type": handler.PING})
        response = handler.lambda_handler(event, MagicMock())

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"type": handler.PONG}


def test_unrecognized_event_shape_raises():
    try:
        handler.lambda_handler({"nonsense": True}, MagicMock())
    except ValueError:
        return
    raise AssertionError("expected ValueError")


# --- handler: mc-help answers immediately ---------------------------------


def test_mc_help_answers_immediately():
    signing_key, public_key_hex = _keypair()
    interaction = {
        "type": handler.APPLICATION_COMMAND,
        "channel_id": "1",
        "data": {"name": "mc-help"},
    }
    with patch(
        "minecraft_tools.discord_bot.handler.DISCORD_PUBLIC_KEY", public_key_hex
    ):
        event = _signed_request(signing_key, interaction)
        response = handler.lambda_handler(event, MagicMock())

    body = json.loads(response["body"])
    assert body["type"] == handler.CHANNEL_MESSAGE_WITH_SOURCE
    assert "mc-start" in body["data"]["content"]


# --- handler: mc-start/stop/status defer + self-invoke --------------------


@patch("minecraft_tools.discord_bot.handler.boto3")
def test_mc_start_defers_and_self_invokes(mock_boto3):
    signing_key, public_key_hex = _keypair()
    interaction = {
        "type": handler.APPLICATION_COMMAND,
        "channel_id": "1",
        "data": {"name": "mc-start"},
    }
    mock_lambda_client = MagicMock()
    mock_boto3.client.return_value = mock_lambda_client

    with patch(
        "minecraft_tools.discord_bot.handler.DISCORD_PUBLIC_KEY", public_key_hex
    ):
        event = _signed_request(signing_key, interaction)
        context = MagicMock(
            invoked_function_arn="arn:aws:lambda:eu-west-1:1:function:minecraft-discord-bot"
        )
        response = handler.lambda_handler(event, context)

    assert json.loads(response["body"]) == {
        "type": handler.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE
    }
    mock_lambda_client.invoke.assert_called_once()
    invoke_payload = json.loads(mock_lambda_client.invoke.call_args.kwargs["Payload"])
    assert invoke_payload["action"] == "process_command"


@patch("minecraft_tools.discord_bot.handler.DISCORD_CHANNEL_ID", "42")
def test_channel_restriction_rejects_wrong_channel():
    signing_key, public_key_hex = _keypair()
    interaction = {
        "type": handler.APPLICATION_COMMAND,
        "channel_id": "99",
        "data": {"name": "mc-status"},
    }
    with patch(
        "minecraft_tools.discord_bot.handler.DISCORD_PUBLIC_KEY", public_key_hex
    ):
        event = _signed_request(signing_key, interaction)
        response = handler.lambda_handler(event, MagicMock())

    body = json.loads(response["body"])
    assert body["type"] == handler.CHANNEL_MESSAGE_WITH_SOURCE
    assert "42" in body["data"]["content"]


# --- handler: _process_command does the real ECS work --------------------


@patch("minecraft_tools.discord_bot.handler.discord_api")
@patch("minecraft_tools.discord_bot.handler.ecs_control")
@patch("minecraft_tools.discord_bot.handler.boto3")
def test_process_command_status_posts_followup(
    _mock_boto3, mock_ecs_control, mock_discord_api
):
    mock_ecs_control.get_service_status.return_value = {
        "desired": 1,
        "running": 1,
        "ips": ["1.2.3.4"],
    }
    mock_ecs_control.format_status.return_value = "status message"
    event = {
        "action": "process_command",
        "interaction": {"token": "interaction-token", "data": {"name": "mc-status"}},
    }

    handler._process_command(event)

    mock_discord_api.followup_message.assert_called_once_with(
        handler.DISCORD_APPLICATION_ID, "interaction-token", "status message"
    )


@patch("minecraft_tools.discord_bot.handler.discord_api")
@patch("minecraft_tools.discord_bot.handler.ecs_control")
@patch("minecraft_tools.discord_bot.handler.boto3")
def test_process_command_handles_unexpected_error(
    _mock_boto3, mock_ecs_control, mock_discord_api
):
    mock_ecs_control.get_service_status.side_effect = RuntimeError("boom")
    event = {
        "action": "process_command",
        "interaction": {"token": "interaction-token", "data": {"name": "mc-status"}},
    }

    handler._process_command(event)

    args = mock_discord_api.followup_message.call_args.args
    assert "unexpected error" in args[2].lower()
