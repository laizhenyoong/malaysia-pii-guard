"""The recognizer types every detector in this package is built on."""

import re
from dataclasses import dataclass
from typing import ClassVar, List, Optional, Sequence


@dataclass(frozen=True)
class Pattern:
    """A named regex and the confidence a bare match on it earns."""

    name: str
    regex: str
    score: float


@dataclass
class Finding:
    """One span of a text that a recognizer claims, and how sure it is."""

    entity_type: str
    start: int
    end: int
    score: float
    recognizer: str = ""

    def overlaps(self, other: "Finding") -> bool:
        """Whether the two spans share at least one character."""
        return self.start < other.end and other.start < self.end


def best_per_span(findings: List[Finding]) -> List[Finding]:
    """Keep the strongest claim on each span, so two patterns cannot double up."""
    best = {}
    for finding in findings:
        span = (finding.start, finding.end)
        if span not in best or finding.score > best[span].score:
            best[span] = finding
    return sorted(best.values(), key=lambda finding: finding.start)


class Recognizer:
    """Base for anything that claims spans of a text.

    CONTEXT holds the words that, sitting near a match, argue it is what it
    looks like. The analyzer weighs them, not the recognizer.
    """

    ENTITY: ClassVar[str] = ""
    CONTEXT: ClassVar[Sequence[str]] = ()

    def __init__(
        self,
        entity: Optional[str] = None,
        context: Optional[Sequence[str]] = None,
        name: Optional[str] = None,
    ):
        self.entity = entity or self.ENTITY
        self.context = [word.lower() for word in (context or self.CONTEXT)]
        self.name = name or type(self).__name__

    def analyze(self, text: str) -> List[Finding]:
        """Every span of the text this recognizer claims."""
        raise NotImplementedError


class PatternRecognizer(Recognizer):
    """A recognizer whose claims come from regular expressions.

    A pattern's score is what a bare match is worth before context is weighed,
    so a shape that could be almost anything is scored near zero on purpose.
    Where the digits carry checkable structure, invalidate_result throws out the
    impossible ones.
    """

    PATTERNS: ClassVar[Sequence[Pattern]] = ()

    def __init__(self, patterns: Optional[Sequence[Pattern]] = None, **kwargs):
        self.patterns = list(patterns or self.PATTERNS)
        super().__init__(**kwargs)

    def analyze(self, text: str) -> List[Finding]:
        """Every span matched by a pattern and not thrown out."""
        findings = []
        for pattern in self.patterns:
            for match in re.finditer(pattern.regex, text):
                if self.invalidate_result(match.group()):
                    continue
                findings.append(
                    Finding(
                        entity_type=self.entity,
                        start=match.start(),
                        end=match.end(),
                        score=pattern.score,
                        recognizer=self.name,
                    )
                )
        return best_per_span(findings)

    def invalidate_result(self, matched_text: str) -> bool:
        """Whether a match cannot be what its pattern took it for."""
        return False
