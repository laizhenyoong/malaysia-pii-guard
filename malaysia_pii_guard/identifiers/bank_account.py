"""Recognizer for the Malaysian bank account number."""

from malaysia_pii_guard.recognizer import Pattern, PatternRecognizer


class MyBankRecognizer(PatternRecognizer):
    """Recognize the Malaysian bank account number.

    No regulator publishes a check digit and there is no IBAN to fall back on,
    so nothing can be verified. The pattern is scored near zero and the context
    words carry it.
    """

    ENTITY = "MY_BANK_ACCOUNT"

    COUNTRY_CODE = "my"

    # Ten to sixteen digits covers the banks and product vintages we see. Check
    # the band against your own transaction data.
    PATTERNS = [
        Pattern("Bank Account (weak)", r"\b[0-9]{10,16}\b", 0.05),
    ]

    # Only the banks whose names do not contain "bank" need listing.
    CONTEXT = [
        "account", "acct", "bank", "beneficiary", "deposit", "payee", "transfer",
        "cimb", "rhb", "ocbc", "uob", "hsbc", "bsn",
    ]

