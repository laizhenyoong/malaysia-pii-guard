"""Running recognizers over a text, settling the overlaps, and masking."""

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from malaysia_pii_guard.recognizer import Finding, Recognizer

# A shape scored near zero needs the floor as well as the boost. Adding 0.35
# to 0.05 still leaves it in the noise.
CONTEXT_BOOST = 0.35
MIN_SCORE_WITH_CONTEXT = 0.4

CONTEXT_WINDOW = 5

_WORD = re.compile(r"\w+")


def _nearby_words(text: str, finding: Finding) -> List[str]:
    """The words flanking the span."""
    before = _WORD.findall(text[: finding.start])[-CONTEXT_WINDOW:]
    after = _WORD.findall(text[finding.end :])[:CONTEXT_WINDOW]
    return [word.lower() for word in before + after]


def _weigh_context(text: str, finding: Finding, context: Sequence[str]) -> Finding:
    """Lift the score when a context word sits near the span.

    A context word counts anywhere inside a nearby word, so "bank" is found in
    "Maybank". Short words are the cost: "tel" is found in "hotel".
    """
    if context and any(
        word in nearby for nearby in _nearby_words(text, finding) for word in context
    ):
        finding.score = min(
            1.0, max(finding.score + CONTEXT_BOOST, MIN_SCORE_WITH_CONTEXT)
        )
    return finding


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


class Analyzer:
    """Runs every recognizer it holds over a text.

    Overlapping claims are left in. Ten digits really is both a mobile number
    and an account number, and anonymize settles it by score.
    """

    def __init__(
        self, recognizers: Iterable[Recognizer], score_threshold: float = 0.0
    ):
        self.recognizers = list(recognizers)
        self.score_threshold = score_threshold

    def analyze(
        self,
        text: str,
        entities: Optional[Sequence[str]] = None,
        score_threshold: Optional[float] = None,
    ) -> List[Finding]:
        """Every claim at or above the threshold, strongest first.

        The threshold defaults to zero, so everything suspect is masked until a
        caller decides otherwise. At MIN_SCORE_WITH_CONTEXT only what a context
        word vouched for survives.
        """
        if score_threshold is None:
            score_threshold = self.score_threshold
        findings = []
        for recognizer in self.recognizers:
            if entities and recognizer.entity not in entities:
                continue
            for finding in recognizer.analyze(text):
                finding = _weigh_context(text, finding, recognizer.context)
                if finding.score >= score_threshold:
                    findings.append(finding)
        return sorted(findings, key=lambda finding: (-finding.score, finding.start))
