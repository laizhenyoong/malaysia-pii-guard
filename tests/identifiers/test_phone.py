import pytest

from malaysia_pii_guard import MyPhoneRecognizer, anonymize, malaysian_analyzer


@pytest.fixture(scope="module")
def recognizer():
    return MyPhoneRecognizer()


@pytest.fixture(scope="module")
def analyzer():
    return malaysian_analyzer()


def scores(recognizer, text):
    return [finding.score for finding in recognizer.analyze(text)]


@pytest.mark.parametrize(
    "text",
    [
        "+60123456789",
        "+60 12-345 6789",
        "0060123456789",
        "60123456789",
        "012-345 6789",
        "012-3456789",
        "0123456789",
        "011-1234 5678",
        "01112345678",
        "013-222 3333",
        "03-7712 3456",
        "03 2382 8888",
        "082-234567",
        "088-234567",
        "1300-88-1234",  # service number, still PII
        "1800-88-1234",
    ],
)
def test_detects_malaysian_numbers(recognizer, text):
    """Every match carries the same flat score. The plan already vouched for it."""
    assert scores(recognizer, text) == [pytest.approx(MyPhoneRecognizer.SCORE)]


@pytest.mark.parametrize(
    "text, reason",
    [
        ("850312085431", "MyKad number, not a phone number"),
        ("850312-08-5431", "dashed MyKad number"),
        ("990101145678", "MyKad fixture from the MY_NRIC suite"),
        ("990101-14-5678", "dashed MyKad fixture from the MY_NRIC suite"),
        ("514288123456", "twelve-digit bank account"),
        ("601234567890", "twelve digits that happen to start with 60"),
        ("12345678901", "LHDN-shaped reference"),
        ("1234567890", "ten digits outside the numbering plan"),
        ("5142881234567890", "sixteen-digit card-length run"),
    ],
)
def test_ignores_other_malaysian_identifiers(recognizer, text, reason):
    """Leniency VALID buys this. POSSIBLE matches several of these."""
    assert scores(recognizer, text) == [], reason


def test_finds_every_number_in_a_sentence(recognizer):
    text = "Call 012-345 6789 or 013-222 3333, office 03-7712 3456."
    findings = recognizer.analyze(text)
    assert [text[f.start : f.end] for f in findings] == [
        "012-345 6789",
        "013-222 3333",
        "03-7712 3456",
    ]


def test_trailing_punctuation_is_not_part_of_the_span(recognizer):
    text = "tel: 0123456789."
    (finding,) = recognizer.analyze(text)
    assert text[finding.start : finding.end] == "0123456789"


def test_context_word_raises_the_score(analyzer):
    def score(text):
        return next(
            f.score for f in analyzer.analyze(text) if f.entity_type == "PHONE_NUMBER"
        )

    assert score("My mobile is 0123456789.") > score("Order 0123456789.")


def test_phone_and_mykad_do_not_steal_each_others_spans(analyzer):
    text = "IC 850312-08-5431, hp 012-345 6789."
    found = {
        f.entity_type: text[f.start : f.end]
        for f in analyzer.analyze(text)
        if f.entity_type in ("MY_NRIC", "PHONE_NUMBER")
    }
    assert found == {"MY_NRIC": "850312-08-5431", "PHONE_NUMBER": "012-345 6789"}


@pytest.mark.parametrize(
    "text, digits",
    [
        ("Call me at 012-345 6789 please.", "6789"),
        ("My hp is +60 12-345 6789.", "6789"),
        ("Contact 011-1234 5678 or the office at 03-7712 3456.", "5678"),
    ],
)
def test_no_digits_survive_anonymization(analyzer, text, digits):
    assert digits not in anonymize(text, analyzer.analyze(text)).text
