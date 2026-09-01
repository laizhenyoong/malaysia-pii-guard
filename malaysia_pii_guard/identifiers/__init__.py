"""A recognizer for each Malaysian identifier the library knows."""

from malaysia_pii_guard.analyzer import Analyzer
from malaysia_pii_guard.identifiers.bank_account import MyBankRecognizer
from malaysia_pii_guard.identifiers.nric import MyKadRecognizer
from malaysia_pii_guard.identifiers.passport import MyPassportRecognizer
from malaysia_pii_guard.identifiers.phone import MyPhoneRecognizer


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
