"""Settling the overlaps, masking a text, and putting the originals back.

Masking without a key writes a numbered label, so the masked text stays readable
and a text written about it restores too. Masking with a key encrypts each value
instead, so the masked text carries no plaintext and only the key undoes it.
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
    """Where one masked value sits in the anonymized text, and what it stands for.

    original is filled by keyless masking only. Encrypting keeps no plaintext,
    which is the point of it.
    """

    entity_type: str
    start: int
    end: int
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
    """Replaces every span a finding claims.

    Built without a key it writes numbered labels and keeps the originals on the
    items. Built with one it encrypts instead and keeps none.
    """

    def __init__(self, key: Optional[Union[bytes, str]] = None):
        self._fernet = _cipher(key) if key is not None else None

    def anonymize(self, text: str, findings: Iterable[Finding]) -> Anonymized:
        """Mask every span that survives the overlap check.

        Built left to right, tracking where each token lands in the text being
        written, because that is the offset a keyed undo reads back.
        """
        parts: List[str] = []
        items: List[Item] = []
        labels: Dict[Tuple[str, str], str] = {}
        counts: Dict[str, int] = defaultdict(int)
        read = 0
        written = 0
        for finding in resolve(findings):
            entity = finding.entity_type
            original = text[finding.start : finding.end]
            head = text[read : finding.start]

            if self._fernet is not None:
                token, kept = self._fernet.encrypt(original.encode()).decode(), None
            else:
                # Each distinct value earns one label, so a repeat reads alike.
                if (entity, original) not in labels:
                    labels[(entity, original)] = f"<{entity}_{counts[entity]}>"
                    counts[entity] += 1
                token, kept = labels[(entity, original)], original

            parts += [head, token]
            written += len(head)
            items.append(Item(entity, written, written + len(token), token, kept))
            written += len(token)
            read = finding.end
        parts.append(text[read:])
        return Anonymized("".join(parts), items)


class DeanonymizeEngine:
    """Puts the originals back, however the AnonymizerEngine put them away.

    Built without a key it swaps each label for what it stood for wherever the
    label turns up, so a text written about the masked one restores too. Built
    with one it decrypts by offset, which needs the very text anonymize returned.
    """

    def __init__(self, key: Optional[Union[bytes, str]] = None):
        self._fernet = _cipher(key) if key is not None else None

    def deanonymize(self, text: str, items: Iterable[Item]) -> str:
        """Undo the masking every item records."""
        if self._fernet is None:
            for item in items:
                text = text.replace(item.label, item.original)
            return text

        # Splice right to left, so a replacement cannot move the spans before it.
        for item in sorted(items, key=lambda item: item.start, reverse=True):
            original = self._fernet.decrypt(
                text[item.start : item.end].encode()
            ).decode()
            text = f"{text[: item.start]}{original}{text[item.end :]}"
        return text
