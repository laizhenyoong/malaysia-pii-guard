import pytest
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

from pii_guard import MyKadRecognizer


@pytest.fixture(scope="module")
def recognizer():
    return MyKadRecognizer()


@pytest.fixture(scope="module")
def analyzer():
    """The default English recognizers plus MyKad."""
    provider = NlpEngineProvider(
        nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
        }
    )
    engine = AnalyzerEngine(nlp_engine=provider.create_engine(), supported_languages=["en"])
    engine.registry.add_recognizer(MyKadRecognizer())
    return engine


def scores(recognizer, text):
    return [r.score for r in recognizer.analyze(text, ["MY_NRIC"], nlp_artifacts=None)]


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
        return next(r.score for r in analyzer.analyze(text, language="en")
                    if r.entity_type == "MY_NRIC")

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
    """Presidio alone redacted only the birth-date prefix, leaving the rest in the clear."""
    results = analyzer.analyze(text=text, language="en")
    redacted = AnonymizerEngine().anonymize(text=text, analyzer_results=results).text
    assert "5678" not in redacted
    assert "5431" not in redacted
    assert "-14-" not in redacted


def test_mykad_wins_the_span_over_date_time(analyzer):
    """DATE_TIME used to claim the first six digits; MY_NRIC should own the whole span."""
    text = "My IC number is 990101-14-5678."
    winner = next(r for r in analyzer.analyze(text, language="en") if "5678" in text[r.start:r.end])
    assert winner.entity_type == "MY_NRIC"
    assert text[winner.start:winner.end] == "990101-14-5678"
