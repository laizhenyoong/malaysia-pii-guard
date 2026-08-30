"""Recognizer for the Malaysian passport number (a letter, then eight digits)."""

from pii_guard.core import Pattern, PatternRecognizer


class MyPassportRecognizer(PatternRecognizer):
    """Recognize the Malaysian passport number.

    The number carries no check digit of its own -- the one printed on a
    passport belongs to the machine-readable zone -- so the prefix and the digit
    count are the whole of the structure.
    """

    ENTITY = "MY_PASSPORT"

    COUNTRY_CODE = "my"

    # A and H are the international series, K the restricted one. An unlisted
    # letter still matches the second pattern, so a series issued after this was
    # written is scored down rather than missed.
    PATTERNS = [
        Pattern("Passport (issued prefix)", r"\b[AHKahk]\d{8}\b", 0.4),
        Pattern("Passport (any prefix)", r"\b[A-Za-z]\d{8}\b", 0.05),
    ]

    CONTEXT = ["passport", "travel", "document", "immigration"]

    def invalidate_result(self, pattern_text: str) -> bool:
        """Reject a match whose digits are all the same."""
        return len(set(pattern_text[1:])) == 1
