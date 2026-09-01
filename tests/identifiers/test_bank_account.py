import pytest

from malaysia_pii_guard import MyBankRecognizer, anonymize, malaysian_analyzer


@pytest.fixture(scope="module")
def recognizer():
    return MyBankRecognizer()


@pytest.fixture(scope="module")
def analyzer():
    return malaysian_analyzer()


def scores(recognizer, text):
    return [finding.score for finding in recognizer.analyze(text)]


@pytest.mark.parametrize(
    "text",
    [
        "3141592653",
        "51234567890",
        "512345678901",
        "21412345678901",
        "1234567890123456",
    ],
)
def test_detects_account_numbers(recognizer, text):
    """The pattern is deliberately weak. The context words do the rest."""
    assert scores(recognizer, text) == [pytest.approx(0.05)]


@pytest.mark.parametrize(
    "text, reason",
    [
        ("123456789", "nine digits is below the band"),
        ("12345678901234567", "seventeen digits is above the band"),
    ],
)
def test_ignores_runs_outside_the_band(recognizer, text, reason):
    assert scores(recognizer, text) == [], reason


@pytest.mark.parametrize(
    "text",
    [
        "My account is 512345678901.",
        "Transfer to 512345678901 today.",
        "Maybank 512345678901.",  # "bank" matches as a substring of "Maybank"
        "CIMB 512345678901.",
    ],
)
def test_context_word_raises_the_score(analyzer, text):
    def score(text):
        return next(
            f.score for f in analyzer.analyze(text) if f.entity_type == "MY_BANK_ACCOUNT"
        )

    assert score(text) > score("Ref 512345678901.")


def test_account_and_mykad_do_not_steal_each_others_spans(analyzer):
    text = "IC 850312-08-5431, account 512345678901."
    found = {
        f.entity_type: text[f.start : f.end]
        for f in analyzer.analyze(text)
        if f.entity_type in ("MY_NRIC", "MY_BANK_ACCOUNT")
    }
    assert found == {"MY_NRIC": "850312-08-5431", "MY_BANK_ACCOUNT": "512345678901"}


def test_a_mobile_number_outscores_the_account_reading(analyzer):
    """Ten digits is both shapes, so the score has to settle it."""
    text = "My mobile is 0123456789."
    findings = analyzer.analyze(text)
    assert max(findings, key=lambda f: f.score).entity_type == "PHONE_NUMBER"
    assert anonymize(text, findings).text == "My mobile is <PHONE_NUMBER_0>."


def test_masks_under_the_right_label(analyzer):
    text = "My account is 512345678901."
    assert anonymize(text, analyzer.analyze(text)).text == (
        "My account is <MY_BANK_ACCOUNT_0>."
    )
