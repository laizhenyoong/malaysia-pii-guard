"""The set of recognizers a Malaysian deployment runs."""

from pii_guard.engine import Analyzer
from pii_guard.my_bank import MyBankRecognizer
from pii_guard.my_kad import MyKadRecognizer
from pii_guard.my_passport import MyPassportRecognizer
from pii_guard.my_phone import MyPhoneRecognizer


def malaysian_analyzer() -> Analyzer:
    """An analyzer holding every recognizer in this package."""
    return Analyzer(
        [
            MyBankRecognizer(),
            MyKadRecognizer(),
            MyPassportRecognizer(),
            MyPhoneRecognizer(),
        ]
    )
