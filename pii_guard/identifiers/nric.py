"""Recognizer for the Malaysian MyKad / NRIC number (YYMMDD-PB-###G)."""

from datetime import date

from pii_guard.recognizer import Pattern, PatternRecognizer

# Place-of-birth codes JPN has never issued. This does most of the
# false-positive filtering, so audit it against a current JPN source.
NEVER_ISSUED_STATE_CODES = frozenset(
    {"00", "17", "18", "19", "20", "69", "70", "73", "80", "81", "94", "95", "96", "97"}
)


def _is_real_date(yymmdd: str) -> bool:
    """Whether YYMMDD is a real date in either century the two-digit year allows."""
    yy, mm, dd = int(yymmdd[:2]), int(yymmdd[2:4]), int(yymmdd[4:6])
    for century in (1900, 2000):
        try:
            date(century + yy, mm, dd)
        except ValueError:
            continue
        return True
    return False


class MyKadRecognizer(PatternRecognizer):
    """Recognize the Malaysian MyKad / NRIC number.

    There is no check digit, since the trailing digit encodes gender. Precision
    comes from structure instead: the first six digits must be a real date, and
    the place-of-birth code must be one JPN issues.
    """

    ENTITY = "MY_NRIC"

    COUNTRY_CODE = "my"

    # The lookarounds stop a match from being a slice of a longer run of digits
    # and dashes, such as the start of a reference number.
    PATTERNS = [
        Pattern("MyKad (dashed)", r"(?<![\d-])\d{6}-\d{2}-\d{4}(?![\d-])", 0.6),
        Pattern("MyKad (spaced)", r"(?<![\d-])\d{6} \d{2} \d{4}(?![\d-])", 0.4),
        Pattern("MyKad (bare)", r"(?<![\d-])\d{12}(?![\d-])", 0.05),
    ]

    CONTEXT = ["ic", "nric", "mykad", "identity"]

    def invalidate_result(self, pattern_text: str) -> bool:
        """Reject a match that cannot be an issued MyKad number."""
        digits = "".join(c for c in pattern_text if c.isdigit())
        return (
            len(set(digits)) == 1
            or digits[8:] == "0000"
            or digits[6:8] in NEVER_ISSUED_STATE_CODES
            or not _is_real_date(digits[:6])
        )
