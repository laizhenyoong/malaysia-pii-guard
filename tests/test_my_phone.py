import pytest
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.predefined_recognizers import PhoneRecognizer
from presidio_anonymizer import AnonymizerEngine

from pii_guard import MyPhoneRecognizer, malaysian_registry


@pytest.fixture(scope="module")
def recognizer():
    return MyPhoneRecognizer()


@pytest.fixture(scope="module")
def analyzer():
    """A Malaysian deployment, put together the way malaysian_registry does it."""
    nlp_engine = NlpEngineProvider(
        nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
        }
    ).create_engine()
    return AnalyzerEngine(
        nlp_engine=nlp_engine,
        registry=malaysian_registry(nlp_engine),
        supported_languages=["en"],
    )


def scores(recognizer, text):
    return [r.score for r in recognizer.analyze(text, ["PHONE_NUMBER"], nlp_artifacts=None)]


@pytest.mark.parametrize(
    "text",
    [
        # International.
        "+60123456789",
        "+60 12-345 6789",
        "0060123456789",
        "60123456789",
        # Mobile, national.
        "012-345 6789",
        "012-3456789",
        "0123456789",
        "011-1234 5678",
        "01112345678",
        "013-222 3333",
        # Fixed line.
        "03-7712 3456",
        "03 2382 8888",
        "082-234567",
        "088-234567",
        # Service numbers. Presidio makes no distinction, so these are PII too.
        "1300-88-1234",
        "1800-88-1234",
    ],
)
def test_detects_malaysian_numbers(recognizer, text):
    """Every match carries PhoneRecognizer's flat score."""
    assert scores(recognizer, text) == [pytest.approx(PhoneRecognizer.SCORE)]


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
    """leniency=VALID is what buys this: leniency=POSSIBLE matches several of these."""
    assert scores(recognizer, text) == [], reason


def test_finds_every_number_in_a_sentence(recognizer):
    text = "Call 012-345 6789 or 013-222 3333, office 03-7712 3456."
    results = recognizer.analyze(text, ["PHONE_NUMBER"], nlp_artifacts=None)
    assert [text[r.start : r.end] for r in results] == [
        "012-345 6789",
        "013-222 3333",
        "03-7712 3456",
    ]


def test_trailing_punctuation_is_not_part_of_the_span(recognizer):
    text = "tel: 0123456789."
    (result,) = recognizer.analyze(text, ["PHONE_NUMBER"], nlp_artifacts=None)
    assert text[result.start : result.end] == "0123456789"


def test_default_presidio_misses_numbers_this_recognizer_catches(recognizer):
    """The regression this recognizer exists for: MY is not in the default regions."""
    stock = PhoneRecognizer()
    assert "MY" not in stock.supported_regions
    for missed in ("011-1234 5678", "60123456789"):
        assert stock.analyze(missed, ["PHONE_NUMBER"], nlp_artifacts=None) == []
        assert scores(recognizer, missed) != []


def test_context_word_raises_the_score(analyzer):
    def score(text):
        return next(
            r.score for r in analyzer.analyze(text, language="en")
            if r.entity_type == "PHONE_NUMBER"
        )

    assert score("My hp is 0123456789.") > score("Order 0123456789.")


def test_phone_and_mykad_do_not_steal_each_others_spans(analyzer):
    text = "IC 850312-08-5431, hp 012-345 6789."
    found = {
        r.entity_type: text[r.start : r.end]
        for r in analyzer.analyze(text, language="en")
        if r.entity_type in ("MY_NRIC", "PHONE_NUMBER")
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
    results = analyzer.analyze(text=text, language="en")
    redacted = AnonymizerEngine().anonymize(text=text, analyzer_results=results).text
    assert digits not in redacted
