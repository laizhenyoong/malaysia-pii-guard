"""Recognizer for the Malaysian phone number (+60, national 0X or 01X)."""

from typing import List

import phonenumbers

from pii_guard.core import Finding, Recognizer, best_per_span


class MyPhoneRecognizer(Recognizer):
    """Recognize the Malaysian phone number.

    phonenumbers carries the allocated numbering plan, so precision comes from
    that data rather than from a pattern of ours: at leniency VALID a MyKad
    number, a bank account and an LHDN reference are all turned away for not
    being phone numbers at all, with no exclusion rules to maintain.
    """

    ENTITY = "PHONE_NUMBER"

    COUNTRY_CODE = "my"

    SCORE = 0.4

    REGIONS = ("MY",)

    # VALID means the number sits in a block the plan actually allocates.
    # POSSIBLE only checks the length, and lets an IC number through.
    LENIENCY = phonenumbers.Leniency.VALID

    CONTEXT = ["phone", "number", "telephone", "cell", "cellphone", "mobile", "call"]

    def analyze(self, text: str) -> List[Finding]:
        """Every allocated phone number in the text."""
        findings = []
        for region in self.REGIONS:
            for match in phonenumbers.PhoneNumberMatcher(
                text, region, leniency=self.LENIENCY
            ):
                findings.append(
                    Finding(
                        entity_type=self.entity,
                        start=match.start,
                        end=match.end,
                        score=self.SCORE,
                        recognizer=self.name,
                    )
                )
        return best_per_span(findings)
