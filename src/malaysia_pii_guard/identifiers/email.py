"""Recognizer for the email address."""

import tldextract

from malaysia_pii_guard.recognizer import Pattern, PatternRecognizer

# The public suffix list decides whether a domain is real, the way the
# numbering plan decides it for a phone number. It ships with tldextract, and
# suffix_list_urls is emptied so analyzing a text never reaches the network.
_extract = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)


class EmailRecognizer(PatternRecognizer):
    """Recognize the email address.

    Not a Malaysian identifier, but it sits beside every one of them in the
    forms this library is pointed at. The shape vouches for itself, so the
    score clears the threshold on its own and context only adds to it.
    """

    ENTITY = "EMAIL_ADDRESS"

    # Presidio's pattern. The local part takes the punctuation RFC 5322 allows
    # unquoted, and each domain label may carry inner hyphens, so a punycode
    # label such as "xn--80ak6aa92e" matches.
    PATTERNS = [
        Pattern(
            "Email (medium)",
            r"\b((([!#$%&'*+\-/=?^_`{|}~\w])|([!#$%&'*+\-/=?^_`{|}~\w][!#$%&'*+\-/=?^_`{|}~\.\w]{0,}[!#$%&'*+\-/=?^_`{|}~\w]))[@]\w+(?:-+\w+)*(?:\.\w+(?:-+\w+)*)+)\b",
            0.5,
        ),
    ]

    CONTEXT = ["email", "mail", "contact"]

    def invalidate_result(self, pattern_text: str) -> bool:
        """Reject a match whose domain ends in no published suffix."""
        return _extract(pattern_text).fqdn == ""
