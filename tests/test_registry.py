import pytest
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

from pii_guard import malaysian_registry


@pytest.fixture(scope="module")
def nlp_engine():
    return NlpEngineProvider(
        nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
        }
    ).create_engine()


@pytest.fixture(scope="module")
def analyzer(nlp_engine):
    return AnalyzerEngine(
        nlp_engine=nlp_engine,
        registry=malaysian_registry(nlp_engine),
        supported_languages=["en"],
    )


def names(registry):
    return {r.name for r in registry.get_recognizers("en", None, all_fields=True)}


@pytest.mark.parametrize(
    "recognizer, reason",
    [
        ("NhsRecognizer", "matches a Malaysian mobile number at 1.0"),
        ("UsBankRecognizer", "matches an IC number and a MyKad-length run"),
        ("UsLicenseRecognizer", "matches most Malaysian digit runs weakly"),
        ("UsPassportRecognizer", "its pattern is the Malaysian passport format"),
        ("UsItinRecognizer", "United States only"),
        ("UsSsnRecognizer", "United States only"),
        ("MedicalLicenseRecognizer", "United States only"),
        ("PhoneRecognizer", "its region list has no Malaysia in it"),
    ],
)
def test_drops_recognizers_that_misfire_here(nlp_engine, recognizer, reason):
    assert recognizer not in names(malaysian_registry(nlp_engine)), reason


def test_keeps_the_locale_agnostic_recognizers(nlp_engine):
    kept = names(malaysian_registry(nlp_engine))
    assert {
        "CreditCardRecognizer",
        "EmailRecognizer",
        "IbanRecognizer",
        "IpRecognizer",
        "MacAddressRecognizer",
        "UrlRecognizer",
        "CryptoRecognizer",
        "SpacyRecognizer",
    } <= kept


def test_adds_the_malaysian_recognizers(nlp_engine):
    assert {"MyKadRecognizer", "MyPhoneRecognizer"} <= names(malaysian_registry(nlp_engine))


@pytest.mark.parametrize(
    "text, entity, matched",
    [
        ("My hp is 011-1234 5678.", "PHONE_NUMBER", "011-1234 5678"),
        ("Subscriber 60123456789 has an issue.", "PHONE_NUMBER", "60123456789"),
        ("IC 850312-08-5431.", "MY_NRIC", "850312-08-5431"),
        ("Ahmad bin Abdullah called.", "PERSON", "Ahmad bin Abdullah"),
    ],
)
def test_entities_are_typed_and_spanned_correctly(analyzer, text, entity, matched):
    """Stock Presidio called the first two DATE_TIME, one of them over-wide."""
    results = analyzer.analyze(text, language="en")
    assert [(r.entity_type, text[r.start : r.end]) for r in results] == [(entity, matched)]


def test_email_still_detected(analyzer):
    """UrlRecognizer also claims the domain, so this asserts presence, not sole result."""
    text = "Write to ali@example.com."
    results = analyzer.analyze(text, language="en")
    assert ("EMAIL_ADDRESS", "ali@example.com") in [
        (r.entity_type, text[r.start : r.end]) for r in results
    ]


def test_date_time_is_silent_by_default(analyzer):
    """It outscores PHONE_NUMBER on the same span, so it would take the mask."""
    results = analyzer.analyze("Ahmad called on 3 January.", language="en")
    assert [r.entity_type for r in results] == ["PERSON"]


def test_date_time_can_be_kept(nlp_engine):
    engine = AnalyzerEngine(
        nlp_engine=nlp_engine,
        registry=malaysian_registry(nlp_engine, keep_date_time=True),
        supported_languages=["en"],
    )
    results = engine.analyze("Ahmad called on 3 January.", language="en")
    assert "DATE_TIME" in {r.entity_type for r in results}


@pytest.mark.parametrize(
    "text, expected",
    [
        ("My hp is 011-1234 5678.", "My hp is <PHONE_NUMBER>."),
        ("Subscriber 60123456789 has an issue.", "Subscriber <PHONE_NUMBER> has an issue."),
        ("Call me at 012-345 6789.", "Call me at <PHONE_NUMBER>."),
        ("IC 850312-08-5431.", "IC <MY_NRIC>."),
    ],
)
def test_masks_under_the_right_label(analyzer, text, expected):
    """Stock Presidio produced <DATE_TIME>, <UK_NHS>, or left the number in the clear."""
    results = analyzer.analyze(text, language="en")
    assert AnonymizerEngine().anonymize(text=text, analyzer_results=results).text == expected
