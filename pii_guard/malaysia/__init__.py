"""The set of recognizers a Malaysian deployment runs."""

from pii_guard.analyzer import Analyzer
from pii_guard.malaysia.bank_account import MyBankRecognizer
from pii_guard.malaysia.nric import MyKadRecognizer
from pii_guard.malaysia.passport import MyPassportRecognizer
from pii_guard.malaysia.phone import MyPhoneRecognizer


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
