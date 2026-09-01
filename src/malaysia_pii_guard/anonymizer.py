"""Settling the overlaps, masking a text, and putting the originals back."""

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from malaysia_pii_guard.recognizer import Finding


def resolve(findings: Iterable[Finding]) -> List[Finding]:
    """Drop the weaker claim wherever two spans overlap."""
    kept: List[Finding] = []
    for finding in sorted(findings, key=lambda f: (-f.score, f.start)):
        if not any(finding.overlaps(other) for other in kept):
            kept.append(finding)
    return sorted(kept, key=lambda finding: finding.start)


@dataclass(frozen=True)
class Replacement:
    """A label and the value it stands for."""

    entity_type: str
    label: str
    original: str


@dataclass
class Anonymized:
    """A masked text and the replacements that undo it."""

    text: str
    replacements: List[Replacement]

    def __str__(self) -> str:
        """The masked text, so printing a result cannot spill the originals."""
        return self.text


def anonymize(text: str, findings: Iterable[Finding]) -> Anonymized:
    """Replace every surviving span with a numbered label.

    Each distinct value earns one label, which is what lets rehydrate undo the
    masking wherever that label later turns up.
    """
    spans = [
        (finding, text[finding.start : finding.end]) for finding in resolve(findings)
    ]

    # Number left to right, so the labels read in the order they appear.
    labels: Dict[Tuple[str, str], str] = {}
    counts: Dict[str, int] = defaultdict(int)
    replacements: List[Replacement] = []
    for finding, original in spans:
        entity = finding.entity_type
        if (entity, original) not in labels:
            label = f"<{entity}_{counts[entity]}>"
            counts[entity] += 1
            labels[(entity, original)] = label
            replacements.append(Replacement(entity, label, original))

    # Splice right to left, so a replacement cannot move the spans before it.
    masked = text
    for finding, original in reversed(spans):
        label = labels[(finding.entity_type, original)]
        masked = f"{masked[: finding.start]}{label}{masked[finding.end :]}"
    return Anonymized(masked, replacements)


def rehydrate(text: str, replacements: Iterable[Replacement]) -> str:
    """Put the original values back wherever their labels appear.

    Any text carrying the labels works, not only the one anonymize returned, so
    an answer written about a masked text rehydrates too.
    """
    for replacement in replacements:
        text = text.replace(replacement.label, replacement.original)
    return text
