"""Minimal Discord REST calls: interaction responses + followup webhooks.

No discord.py dependency -- this bot only ever responds to slash-command
interactions over HTTP, so the one REST call below (editing the deferred
followup) is all it needs.
"""

import json

import urllib3

DISCORD_API_BASE = "https://discord.com/api/v10"

_http = urllib3.PoolManager()


def followup_message(application_id: str, interaction_token: str, content: str) -> None:
    """Edit the original deferred response with the real result.

    https://discord.com/developers/docs/interactions/receiving-and-responding#followup-messages
    """
    url = f"{DISCORD_API_BASE}/webhooks/{application_id}/{interaction_token}/messages/@original"
    _http.request(
        "PATCH",
        url,
        body=json.dumps({"content": content}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
