import pytest
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

from pii_guard import MyBankRecognizer, malaysian_registry


@pytest.fixture(scope="module")
def recognizer():
    return MyBankRecognizer()


@pytest.fixture(scope="module")
def analyzer():
    """A Malaysian deployment, put together the way malaysian_registry does it."""
    provider = NlpEngineProvider(
        nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
        }
    )
    nlp_engine = provider.create_engine()
    return AnalyzerEngine(
        nlp_engine=nlp_engine,
        registry=malaysian_registry(nlp_engine),
        supported_languages=["en"],
    )


def scores(recognizer, text):
    return [r.score for r in recognizer.analyze(text, ["MY_BANK_ACCOUNT"], nlp_artifacts=None)]


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
    """The pattern is deliberately weak -- the context words do the rest."""
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
        return next(r.score for r in analyzer.analyze(text, language="en")
                    if r.entity_type == "MY_BANK_ACCOUNT")

    assert score(text) > score("Ref 512345678901.")


def test_account_and_mykad_do_not_steal_each_others_spans(analyzer):
    text = "IC 850312-08-5431, account 512345678901."
    found = {
        r.entity_type: text[r.start : r.end]
        for r in analyzer.analyze(text, language="en")
        if r.entity_type in ("MY_NRIC", "MY_BANK_ACCOUNT")
    }
    assert found == {"MY_NRIC": "850312-08-5431", "MY_BANK_ACCOUNT": "512345678901"}


def test_a_mobile_number_outscores_the_account_reading(analyzer):
    """Ten digits is both shapes, so the score has to settle it."""
    text = "My mobile is 0123456789."
    results = analyzer.analyze(text, language="en")
    assert max(results, key=lambda r: r.score).entity_type == "PHONE_NUMBER"
    assert AnonymizerEngine().anonymize(text, results).text == "My mobile is <PHONE_NUMBER>."


def test_masks_under_the_right_label(analyzer):
    text = "My account is 512345678901."
    masked = AnonymizerEngine().anonymize(text, analyzer.analyze(text, language="en")).text
    assert masked == "My account is <MY_BANK_ACCOUNT>."
