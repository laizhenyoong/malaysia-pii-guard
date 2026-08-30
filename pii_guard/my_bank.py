"""Recognizer for the Malaysian bank account number."""

from pii_guard.core import Pattern, PatternRecognizer


class MyBankRecognizer(PatternRecognizer):
    """Recognize the Malaysian bank account number.

    No regulator publishes a check digit and there is no IBAN to fall back on,
    so nothing about the number can be verified -- it is only a run of digits.
    The pattern is therefore scored near zero and the context words carry it.
    """

    ENTITY = "MY_BANK_ACCOUNT"

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

