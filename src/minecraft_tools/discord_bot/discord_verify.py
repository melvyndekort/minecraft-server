"""Verifies Discord's Ed25519 signature on every incoming interaction.

Discord signs every request to a registered Interactions endpoint with the
application's public key. Rejecting anything that doesn't verify is the
entire security boundary against spoofed requests hitting the Function URL
directly -- it is deliberately checked first, before any Discord payload
field is trusted.

Same mechanism as aws-idc-pim's discord_verify.py -- see
https://discord.com/developers/docs/interactions/overview#setting-up-an-endpoint
"""

from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey


def verify_discord_signature(
    public_key_hex: str, signature_hex: str, timestamp: str, body: str
) -> bool:
    """Return True iff (timestamp + body) is validly signed by the Discord app."""
    try:
        verify_key = VerifyKey(bytes.fromhex(public_key_hex))
        verify_key.verify(
            (timestamp + body).encode("utf-8"), bytes.fromhex(signature_hex)
        )
        return True
    except (BadSignatureError, ValueError):
        return False
