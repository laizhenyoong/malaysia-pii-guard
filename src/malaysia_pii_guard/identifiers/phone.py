"""Recognizer for the Malaysian phone number (+60, national 0X or 01X)."""

from typing import List

import phonenumbers

from malaysia_pii_guard.recognizer import Finding, Recognizer, best_per_span


class MyPhoneRecognizer(Recognizer):
    """Recognize the Malaysian phone number.

    phonenumbers carries the allocated numbering plan, so precision comes from
    that data rather than a pattern of ours, and a MyKad number, a bank account
    and an LHDN reference are turned away with no exclusion rules to maintain.
    """

    ENTITY = "PHONE_NUMBER"

    SCORE = 0.4

    REGION = "MY"

    # VALID means the plan actually allocates the block. POSSIBLE checks only
    # the length, and lets an IC number through.
    LENIENCY = phonenumbers.Leniency.VALID

    CONTEXT = ["phone", "number", "telephone", "cell", "cellphone", "mobile", "call"]

    def analyze(self, text: str) -> List[Finding]:
        """Every allocated phone number in the text."""
        findings = [
            Finding(
                entity_type=self.entity,
                start=match.start,
                end=match.end,
                score=self.SCORE,
            )
            for match in phonenumbers.PhoneNumberMatcher(
                text, self.REGION, leniency=self.LENIENCY
            )
        ]
        return best_per_span(findings)
