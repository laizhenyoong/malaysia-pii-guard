"""Settling the overlaps, masking a text, and putting the originals back.

Without a key each value becomes a numbered label, with one it becomes
ciphertext. Either way the undo swaps back what was written, wherever it turns
up, so a text written about the masked one restores too.
"""

import secrets
from base64 import urlsafe_b64encode
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple, Union

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from malaysia_pii_guard.recognizer import Finding

# 128 bits, which is the shortest key AES has and the shortest presidio takes.
_MIN_KEY_BYTES = 16

_KEY_INFO = b"malaysia-pii-guard fernet key"


def generate_key() -> str:
    """A fresh secret for an engine, for callers who have none of their own."""
    return secrets.token_urlsafe(32)


def _cipher(key: Union[bytes, str]) -> Fernet:
    """A cipher from whatever secret the caller already has.

    Fernet wants 32 url-safe base64 bytes, which no secret store hands you, so
    the material is stretched to that shape rather than demanded in it.
    """
    material = key.encode() if isinstance(key, str) else key
    if len(material) < _MIN_KEY_BYTES:
        raise ValueError(f"key must be at least {_MIN_KEY_BYTES} bytes")
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
    """What one masked value was replaced by, and what it stood for.

    original is filled by keyless masking only; encrypting keeps no plaintext.
    """

    entity_type: str
    label: str
    original: Optional[str] = None


@dataclass
class Anonymized:
    """A masked text and the items a DeanonymizeEngine needs to undo it."""

    text: str
    items: List[Item]

    def __str__(self) -> str:
        """The masked text, so printing a result cannot spill the originals."""
        return self.text


class AnonymizerEngine:
    """Masks every span a finding claims, with labels or, given a key, ciphertext."""

    def __init__(self, key: Optional[Union[bytes, str]] = None):
        self._fernet = _cipher(key) if key is not None else None

    def anonymize(self, text: str, findings: Iterable[Finding]) -> Anonymized:
        """Mask every span that survives the overlap check."""
        parts: List[str] = []
        items: List[Item] = []
        labels: Dict[Tuple[str, str], str] = {}
        counts: Dict[str, int] = defaultdict(int)
        read = 0
        for finding in resolve(findings):
            entity = finding.entity_type
            original = text[finding.start : finding.end]

            if self._fernet is not None:
                token, kept = self._fernet.encrypt(original.encode()).decode(), None
            else:
                # Each distinct value earns one label, so a repeat reads alike.
                if (entity, original) not in labels:
                    labels[(entity, original)] = f"<{entity}_{counts[entity]}>"
                    counts[entity] += 1
                token, kept = labels[(entity, original)], original

            parts += [text[read : finding.start], token]
            items.append(Item(entity, token, kept))
            read = finding.end
        parts.append(text[read:])
        return Anonymized("".join(parts), items)


class DeanonymizeEngine:
    """Puts the originals back wherever what replaced them turns up.

    Without a key it reads each original off its item, with one it decrypts the
    label. Neither reads an offset.
    """

    def __init__(self, key: Optional[Union[bytes, str]] = None):
        self._fernet = _cipher(key) if key is not None else None

    def deanonymize(self, text: str, items: Iterable[Item]) -> str:
        """Undo the masking every item records."""
        for item in items:
            if self._fernet is None:
                original = item.original
            else:
                original = self._fernet.decrypt(item.label.encode()).decode()
            text = text.replace(item.label, original)
        return text
