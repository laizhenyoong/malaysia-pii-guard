import pytest

from malaysia_pii_guard import AnalyzerEngine, EmailRecognizer


@pytest.fixture(scope="module")
def recognizer():
    return EmailRecognizer()


@pytest.fixture(scope="module")
def analyzer():
    return AnalyzerEngine()


def scores(recognizer, text):
    return [finding.score for finding in recognizer.analyze(text)]


@pytest.mark.parametrize(
    "text",
    [
        "ali@example.com",
        "ali.bin.abu@gmail.com",
        "siti_1990@yahoo.com.my",
        "admin@mail.gov.my",
        "a@b.co",
        "first+tag@sub.domain.co.uk",
        "o'brien@example.org",
        "user@my-company.com.my",
        "user@xn--80ak6aa92e.com",
        "MIXED.Case@Example.COM",
    ],
)
def test_detects_addresses(recognizer, text):
    """The shape vouches for itself, so every match carries the same score."""
    assert scores(recognizer, text) == [pytest.approx(0.5)]


@pytest.mark.parametrize(
    "text, reason",
    [
        ("ali@localhost", "no dot, so no domain to check"),
        ("ali@example", "a bare label is not a domain"),
        ("ali@example.invalidtld", "no such public suffix"),
        ("just.a.sentence.end", "no @ at all"),
        ("@example.com", "no local part"),
        ("ali@.com", "empty label"),
    ],
)
def test_ignores_other_shapes(recognizer, text, reason):
    assert scores(recognizer, text) == [], reason


def test_context_word_raises_the_score(analyzer):
    def score(text):
        return next(
            f.score for f in analyzer.analyze(text) if f.entity_type == "EMAIL_ADDRESS"
        )

    assert score("Email ali@example.com") > score("See ali@example.com")


def test_finds_every_address_in_a_sentence(recognizer):
    text = "Write to ali@example.com, or siti@example.com.my instead."
    findings = recognizer.analyze(text)
    assert [text[f.start : f.end] for f in findings] == [
        "ali@example.com",
        "siti@example.com.my",
    ]


def test_email_and_phone_do_not_steal_each_others_spans(analyzer):
    text = "Reach me at ali@example.com or 012-345 6789."
    found = {
        f.entity_type: text[f.start : f.end]
        for f in analyzer.analyze(text)
        if f.entity_type in ("EMAIL_ADDRESS", "PHONE_NUMBER")
    }
    assert found == {"EMAIL_ADDRESS": "ali@example.com", "PHONE_NUMBER": "012-345 6789"}


def test_clears_the_default_ui_threshold_without_context(analyzer):
    """0.4 is what the UI and the README use, and a bare address must pass it."""
    findings = analyzer.analyze("See ali@example.com", score_threshold=0.4)
    assert [f.entity_type for f in findings] == ["EMAIL_ADDRESS"]


def test_masks_and_restores(analyzer, anonymizer, deanonymizer):
    text = "My email is ali@example.com."
    result = anonymizer.anonymize(text, analyzer.analyze(text))
    assert [item.entity_type for item in result.items] == ["EMAIL_ADDRESS"]
    assert "ali@example.com" not in result.text
    assert deanonymizer.deanonymize(result.text, result.items) == text
