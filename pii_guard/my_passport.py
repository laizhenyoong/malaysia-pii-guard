"""Recognizer for the Malaysian passport number (a letter, then eight digits)."""

from pii_guard.core import Pattern, PatternRecognizer


class MyPassportRecognizer(PatternRecognizer):
    """Recognize the Malaysian passport number.

    Nothing in the number can be checked: no published check digit, no date.
    Both patterns are scored low and the context words carry them. The prefix
    only decides which of the two a match earns.
    """

    ENTITY = "MY_PASSPORT"

    COUNTRY_CODE = "my"

    # A and H are the international series, K the restricted one. A new series
    # still matches the second pattern, so it is scored down, not missed.
    PATTERNS = [
        Pattern("Passport (issued prefix)", r"\b[AHKahk]\d{8}\b", 0.1),
        Pattern("Passport (any prefix)", r"\b[A-Za-z]\d{8}\b", 0.05),
    ]

    CONTEXT = ["passport", "travel", "document", "immigration"]

    def invalidate_result(self, pattern_text: str) -> bool:
        """Reject a match whose digits are all the same."""
        return len(set(pattern_text[1:])) == 1
