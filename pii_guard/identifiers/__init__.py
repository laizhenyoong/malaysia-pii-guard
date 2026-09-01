"""A recognizer for each Malaysian identifier the library knows."""

from pii_guard.analyzer import Analyzer
from pii_guard.identifiers.bank_account import MyBankRecognizer
from pii_guard.identifiers.nric import MyKadRecognizer
from pii_guard.identifiers.passport import MyPassportRecognizer
from pii_guard.identifiers.phone import MyPhoneRecognizer


def malaysian_analyzer(score_threshold: float = 0.0) -> Analyzer:
    """An analyzer holding every recognizer in this package."""
    return Analyzer(
        [
            MyBankRecognizer(),
            MyKadRecognizer(),
            MyPassportRecognizer(),
            MyPhoneRecognizer(),
        ],
        score_threshold=score_threshold,
    )
