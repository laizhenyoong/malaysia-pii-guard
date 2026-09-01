"""Base types for every recognizer in this package."""

import re
from dataclasses import dataclass
from typing import ClassVar, List, Sequence


@dataclass(frozen=True)
class Pattern:
    """A named regex and the confidence a bare match on it earns."""

    name: str
    regex: str
    score: float


@dataclass
class Finding:
    """One span a recognizer claims, and its confidence."""

    entity_type: str
    start: int
    end: int
    score: float

    def overlaps(self, other: "Finding") -> bool:
        """Whether the two spans share at least one character."""
        return self.start < other.end and other.start < self.end


def best_per_span(findings: List[Finding]) -> List[Finding]:
    """Keep the strongest claim on each span so patterns cannot double up."""
    best = {}
    for finding in findings:
        span = (finding.start, finding.end)
        if span not in best or finding.score > best[span].score:
            best[span] = finding
    return sorted(best.values(), key=lambda finding: finding.start)


class Recognizer:
    """Base for anything that claims spans of a text.

    CONTEXT holds words that, sitting near a match, argue it is what it looks
    like. The analyzer weighs them, not the recognizer.
    """

    ENTITY: ClassVar[str] = ""
    CONTEXT: ClassVar[Sequence[str]] = ()

    def __init__(self):
        self.entity = self.ENTITY
        self.context = [word.lower() for word in self.CONTEXT]

    def analyze(self, text: str) -> List[Finding]:
        """Every span of the text this recognizer claims."""
        raise NotImplementedError


class PatternRecognizer(Recognizer):
    """A recognizer whose claims come from regular expressions.

    A pattern's score is what a bare match is worth before context is weighed,
    so an ambiguous shape is scored near zero on purpose. Where the digits carry
    checkable structure, invalidate_result throws out the impossible ones.
    """

    PATTERNS: ClassVar[Sequence[Pattern]] = ()

    def analyze(self, text: str) -> List[Finding]:
        """Every span matched by a pattern and not thrown out."""
        findings = []
        for pattern in self.PATTERNS:
            for match in re.finditer(pattern.regex, text):
                if self.invalidate_result(match.group()):
                    continue
                findings.append(
                    Finding(
                        entity_type=self.entity,
                        start=match.start(),
                        end=match.end(),
                        score=pattern.score,
                    )
                )
        return best_per_span(findings)

    def invalidate_result(self, matched_text: str) -> bool:
        """Whether a match cannot be what its pattern took it for."""
        return False
