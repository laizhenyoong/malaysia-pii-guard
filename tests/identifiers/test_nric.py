import pytest

from malaysia_pii_guard import MyKadRecognizer, anonymize, malaysian_analyzer


@pytest.fixture(scope="module")
def recognizer():
    return MyKadRecognizer()


@pytest.fixture(scope="module")
def analyzer():
    return malaysian_analyzer()


def scores(recognizer, text):
    return [finding.score for finding in recognizer.analyze(text)]


@pytest.mark.parametrize(
    "text, score",
    [
        ("IC 990101-14-5678", 0.6),
        ("IC 990101 14 5678", 0.4),
        ("IC 990101145678", 0.05),
        ("IC 000229-14-5678", 0.6),  # leap day
        ("IC 900101-74-5678", 0.6),  # foreign place of birth
    ],
)
def test_detects_valid_numbers(recognizer, text, score):
    assert scores(recognizer, text) == [pytest.approx(score)]


@pytest.mark.parametrize(
    "text, reason",
    [
        ("991301-14-5678", "month 13"),
        ("990230-14-5678", "30 February"),
        ("010229-14-5678", "2001 is not a leap year"),
        ("990101-17-5678", "state code never issued"),
        ("990101-00-5678", "state code never issued"),
        ("111111-11-1111", "repeated-digit filler"),
        ("990101-14-0000", "serial all zeros"),
        ("990101-14-5679-9999", "slice of a longer run"),
        ("990101 14-5678", "inconsistent separators"),
        ("99010114567", "eleven digits"),
    ],
)
def test_ignores_invalid_numbers(recognizer, text, reason):
    assert scores(recognizer, text) == [], reason


def test_context_word_raises_the_score(analyzer):
    def score(text):
        return next(
            f.score for f in analyzer.analyze(text) if f.entity_type == "MY_NRIC"
        )

    assert score("His IC is 900101145671.") > score("Reference 900101145671.")


@pytest.mark.parametrize(
    "text",
    [
        "My IC number is 990101-14-5678 and I live in Kuala Lumpur.",
        "IC 990101-14-5678 belongs to the applicant.",
        "The number 990101-14-5678 was verified.",
        "990101-14-5678",
        "Applicant IC: 850312-08-5431. Bank: Maybank 514288123456.",
    ],
)
def test_no_digits_survive_anonymization(analyzer, text):
    redacted = anonymize(text, analyzer.analyze(text)).text
    assert "5678" not in redacted
    assert "5431" not in redacted
    assert "-14-" not in redacted


def test_the_whole_number_is_claimed_not_just_the_birth_date(analyzer):
    text = "My IC number is 990101-14-5678."
    winner = next(f for f in analyzer.analyze(text) if "5678" in text[f.start : f.end])
    assert winner.entity_type == "MY_NRIC"
    assert text[winner.start : winner.end] == "990101-14-5678"
