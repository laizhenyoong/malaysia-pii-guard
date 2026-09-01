"""Settling the overlaps, masking a text, and putting the originals back.

Masking encrypts each span in place, so a masked text carries no plaintext and
only the key reverses it. The price is that deanonymize reads by offset: it
undoes the text anonymize returned, not one that was rewritten in between.
"""

import secrets
from base64 import urlsafe_b64encode
from dataclasses import dataclass
from typing import Iterable, List, Union

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from malaysia_pii_guard.recognizer import Finding

# 128 bits, which is the shortest key AES has and the shortest presidio takes.
MIN_KEY_BYTES = 16

_KEY_INFO = b"malaysia-pii-guard fernet key"


def generate_key() -> str:
    """A fresh secret for an engine, for callers who have none of their own."""
    return secrets.token_urlsafe(32)


def _cipher(key: Union[bytes, str]) -> Fernet:
    """A cipher from whatever secret the caller already has.

    Fernet wants 32 url-safe base64 bytes, which no secret store hands you, so
    the key material is stretched to that shape instead of being demanded in it.
    The same material always derives the same cipher, which is what lets a
    DeanonymizeEngine undo what an AnonymizerEngine did.
    """
    material = key.encode() if isinstance(key, str) else key
    if len(material) < MIN_KEY_BYTES:
        raise ValueError(f"key must be at least {MIN_KEY_BYTES} bytes")
    derived = HKDF(
        algorithm=hashes.SHA256(), length=32, salt=None, info=_KEY_INFO
    ).derive(material)
    return Fernet(urlsafe_b64encode(derived))


def resolve(findings: Iterable[Finding]) -> List[Finding]:
    """Drop the weaker claim wherever two spans overlap."""
    kept: List[Finding] = []
    for finding in sorted(findings, key=lambda f: (-f.score, f.start)):
        if not any(finding.overlaps(other) for other in kept):
            kept.append(finding)
    return sorted(kept, key=lambda finding: finding.start)


@dataclass(frozen=True)
class Item:
    """Where one masked value sits in the anonymized text."""

    entity_type: str
    start: int
    end: int


@dataclass
class Anonymized:
    """A masked text and the items a DeanonymizeEngine needs to undo it."""

    text: str
    items: List[Item]

    def __str__(self) -> str:
        """The masked text, so printing a result cannot spill the originals."""
        return self.text


class AnonymizerEngine:
    """Replaces every span a finding claims with its ciphertext."""

    def __init__(self, key: Union[bytes, str]):
        self._fernet = _cipher(key)

    def anonymize(self, text: str, findings: Iterable[Finding]) -> Anonymized:
        """Encrypt every span that survives the overlap check.

        Built left to right, tracking where each token lands in the text being
        written, because that is the offset deanonymize will read back.
        """
        parts: List[str] = []
        items: List[Item] = []
        read = 0
        written = 0
        for finding in resolve(findings):
            head = text[read : finding.start]
            token = self._fernet.encrypt(
                text[finding.start : finding.end].encode()
            ).decode()
            parts += [head, token]
            written += len(head)
            items.append(Item(finding.entity_type, written, written + len(token)))
            written += len(token)
            read = finding.end
        parts.append(text[read:])
        return Anonymized("".join(parts), items)


class DeanonymizeEngine:
    """Puts the originals back by decrypting what anonymize left in the text."""

    def __init__(self, key: Union[bytes, str]):
        self._fernet = _cipher(key)

    def deanonymize(self, text: str, items: Iterable[Item]) -> str:
        """Decrypt every item back into place.

        The items carry offsets into the text anonymize returned, so a text
        edited in between no longer lines up and the decryption fails.
        """
        # Splice right to left, so a replacement cannot move the spans before it.
        for item in sorted(items, key=lambda item: item.start, reverse=True):
            original = self._fernet.decrypt(
                text[item.start : item.end].encode()
            ).decode()
            text = f"{text[: item.start]}{original}{text[item.end :]}"
        return text
