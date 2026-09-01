"""Running recognizers over a text and weighing the words around a match."""

import re
from typing import Iterable, List, Optional, Sequence

from malaysia_pii_guard.identifiers import RECOGNIZERS
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


class AnalyzerEngine:
    """Runs every recognizer it holds over a text.

    Built with no arguments it loads every recognizer in this package, which is
    what a caller guarding Malaysian text wants. Pass recognizers to narrow it.

    Overlapping claims are left in. Ten digits really is both a mobile number
    and an account number, and anonymize settles it by score.
    """

    def __init__(
        self,
        recognizers: Optional[Iterable[Recognizer]] = None,
        score_threshold: float = 0.0,
    ):
        if recognizers is None:
            recognizers = [recognizer() for recognizer in RECOGNIZERS]
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
