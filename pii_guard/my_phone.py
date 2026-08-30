"""Recognizer for the Malaysian phone number (+60, national 0X or 01X)."""

from typing import List, Optional, Tuple

import phonenumbers

from presidio_analyzer import (
    AnalysisExplanation,
    EntityRecognizer,
    LocalRecognizer,
    RecognizerResult,
)
from presidio_analyzer.nlp_engine import NlpArtifacts


class MyPhoneRecognizer(LocalRecognizer):
    """Recognize the Malaysian phone number.

    python-phonenumbers carries the allocated numbering plan, so precision comes
    from the library rather than from a pattern: at leniency 1 a MyKad number, a
    bank account and an LHDN reference are all rejected for not being phone
    numbers at all. Presidio recognizes them the same way, but its default region
    list omits Malaysia, so 011-1234 5678 and 60123456789 are missed outright.
    """

    COUNTRY_CODE = "my"

    SCORE = 0.4

    DEFAULT_SUPPORTED_REGIONS = ("MY",)

    # Presidio's own context words plus their Malay equivalents. Context matches
    # as a substring, so "tel" is left out -- it would fire on "hotel".
    CONTEXT = [
        "phone", "number", "telephone", "cell", "cellphone", "mobile", "call",
        "telefon", "handphone", "hp", "nombor", "talian", "hubungi",
    ]

    def __init__(
        self,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "PHONE_NUMBER",
        supported_regions: Optional[Tuple[str, ...]] = None,
        leniency: int = 1,
        name: Optional[str] = None,
    ):
        self.supported_regions = supported_regions or self.DEFAULT_SUPPORTED_REGIONS
        self.leniency = leniency
        super().__init__(
            supported_entities=[supported_entity],
            supported_language=supported_language,
            context=context or self.CONTEXT,
            name=name,
        )

    def load(self) -> None:
        """Nothing to load -- python-phonenumbers ships its own metadata."""

    def analyze(
        self, text: str, entities: List[str], nlp_artifacts: NlpArtifacts = None
    ) -> List[RecognizerResult]:
        """Find every allocated phone number in the text."""
        results = []
        for region in self.supported_regions:
            for match in phonenumbers.PhoneNumberMatcher(
                text, region, leniency=self.leniency
            ):
                results.append(self._to_result(match))

        return EntityRecognizer.remove_duplicates(results)

    def _to_result(self, match) -> RecognizerResult:
        """Build a result from the parsed match, keeping the number's own region."""
        region = phonenumbers.region_code_for_number(match.number)
        return RecognizerResult(
            entity_type=self.supported_entities[0],
            start=match.start,
            end=match.end,
            score=self.SCORE,
            analysis_explanation=AnalysisExplanation(
                recognizer=self.name,
                original_score=self.SCORE,
                textual_explanation=f"Recognized as a {region} phone number",
            ),
            recognition_metadata={
                RecognizerResult.RECOGNIZER_NAME_KEY: self.name,
                RecognizerResult.RECOGNIZER_IDENTIFIER_KEY: self.id,
            },
        )
