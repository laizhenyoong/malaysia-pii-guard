"""Recognizer for the Malaysian bank account number."""

from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class MyBankRecognizer(PatternRecognizer):
    """Recognize the Malaysian bank account number.

    Malaysia never adopted IBAN and no regulator publishes a check digit, so
    there is nothing to validate against -- the number is only a run of digits.
    The pattern therefore scores near zero and the context words carry it, which
    is how Presidio handles the US account number for the same reason.
    """

    COUNTRY_CODE = "my"

    # Ten to sixteen digits covers the banks and product vintages we see. Check
    # the band against your own transaction data before relying on it.
    PATTERNS = [
        Pattern("Bank Account (weak)", r"\b[0-9]{10,16}\b", 0.05),
    ]

    # Context matches as a substring, so "bank" already covers Maybank, AmBank
    # and Bank Islam. Only the banks whose names do not contain it are listed.
    CONTEXT = [
        "account", "acct", "bank", "beneficiary", "deposit", "payee", "transfer",
        "cimb", "rhb", "ocbc", "uob", "hsbc", "bsn",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "MY_BANK_ACCOUNT",
        name: Optional[str] = None,
    ):
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns or self.PATTERNS,
            context=context or self.CONTEXT,
            supported_language=supported_language,
            name=name,
        )
