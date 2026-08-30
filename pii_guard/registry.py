"""A Presidio recognizer registry configured for a Malaysian deployment."""

from typing import List, Optional

from presidio_analyzer import RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngine

from pii_guard.my_bank import MyBankRecognizer
from pii_guard.my_kad import MyKadRecognizer
from pii_guard.my_phone import MyPhoneRecognizer


def _drop_date_time(registry: RecognizerRegistry, languages: List[str]) -> None:
    """Silence DATE_TIME, both from the date recognizer and from the NER model."""
    registry.remove_recognizer("DateRecognizer")
    for language in languages:
        for recognizer in registry.get_recognizers(language, ["DATE_TIME"]):
            recognizer.supported_entities = [
                entity
                for entity in recognizer.supported_entities
                if entity != "DATE_TIME"
            ]


def malaysian_registry(
    nlp_engine: NlpEngine,
    languages: Optional[List[str]] = None,
    keep_date_time: bool = False,
) -> RecognizerRegistry:
    """Build a registry holding only the recognizers that make sense in Malaysia.

    Presidio loads every country's by default and they misfire here: a mobile
    number matches UK_NHS at 1.0, an IC number matches US_BANK_NUMBER. DATE_TIME
    goes too, unless asked for -- the NER model reads a mobile number as a date
    and outscores PHONE_NUMBER, taking the span and the mask with it.
    """
    languages = languages or ["en"]
    registry = RecognizerRegistry()
    registry.load_predefined_recognizers(
        languages=languages,
        nlp_engine=nlp_engine,
        countries=[MyKadRecognizer.COUNTRY_CODE],
    )

    # The country filter keeps PhoneRecognizer, which declares no country.
    registry.remove_recognizer("PhoneRecognizer")
    registry.add_recognizer(MyBankRecognizer())
    registry.add_recognizer(MyKadRecognizer())
    registry.add_recognizer(MyPhoneRecognizer())

    if not keep_date_time:
        _drop_date_time(registry, languages)

    return registry
