"""A recognizer for each identifier the library knows."""

from malaysia_pii_guard.identifiers.bank_account import MyBankRecognizer
from malaysia_pii_guard.identifiers.email import EmailRecognizer
from malaysia_pii_guard.identifiers.nric import MyKadRecognizer
from malaysia_pii_guard.identifiers.passport import MyPassportRecognizer
from malaysia_pii_guard.identifiers.phone import MyPhoneRecognizer

# What an AnalyzerEngine loads when it is not handed its own recognizers.
RECOGNIZERS = (
    EmailRecognizer,
    MyBankRecognizer,
    MyKadRecognizer,
    MyPassportRecognizer,
    MyPhoneRecognizer,
)
