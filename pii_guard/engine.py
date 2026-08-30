"""Running the recognizers over a text, and settling what the overlaps mean."""

import re
from typing import Iterable, List, Optional, Sequence

from pii_guard.core import Finding, Recognizer

# A shape scored near zero needs the floor as well as the boost -- adding 0.35
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
    "Maybank". Short words are the cost of that: "tel" is found in "hotel".
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


def anonymize(text: str, findings: Iterable[Finding]) -> str:
    """Replace every surviving span with its entity label."""
    for finding in sorted(resolve(findings), key=lambda finding: -finding.start):
        text = f"{text[: finding.start]}<{finding.entity_type}>{text[finding.end :]}"
    return text


class Analyzer:
    """Runs every recognizer it holds over a text.

    Overlapping claims are left in -- ten digits really is both a mobile number
    and an account number. anonymize settles it by score.
    """

    def __init__(self, recognizers: Iterable[Recognizer]):
        self.recognizers = list(recognizers)

    def analyze(
        self, text: str, entities: Optional[Sequence[str]] = None
    ) -> List[Finding]:
        """Every claim on the text, strongest first."""
        findings = []
        for recognizer in self.recognizers:
            if entities and recognizer.entity not in entities:
                continue
            for finding in recognizer.analyze(text):
                findings.append(_weigh_context(text, finding, recognizer.context))
        return sorted(findings, key=lambda finding: (-finding.score, finding.start))
