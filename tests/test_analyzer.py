import pytest

from cryptography.fernet import InvalidToken

from malaysia_pii_guard import (
    AnalyzerEngine,
    AnonymizerEngine,
    DeanonymizeEngine,
    Finding,
    Pattern,
    PatternRecognizer,
    generate_key,
)
from malaysia_pii_guard.anonymizer import resolve
from malaysia_pii_guard.analyzer import CONTEXT_WINDOW, MIN_SCORE_WITH_CONTEXT


class Digits(PatternRecognizer):
    ENTITY = "DIGITS"
    PATTERNS = [Pattern("digits", r"\b\d{4}\b", 0.05)]
    CONTEXT = ["invoice"]


class Weak(PatternRecognizer):
    ENTITY = "WEAK"
    PATTERNS = [Pattern("wide", r"\b\d{4,6}\b", 0.02)]


@pytest.fixture
def analyzer():
    return AnalyzerEngine([Digits()])


def test_a_bare_match_keeps_its_pattern_score(analyzer):
    (finding,) = analyzer.analyze("Order 1234 shipped.")
    assert finding.score == pytest.approx(0.05)


def test_a_context_word_lifts_a_weak_match_to_the_floor(analyzer):
    (finding,) = analyzer.analyze("Invoice 1234 shipped.")
    assert finding.score == pytest.approx(0.4)


def test_a_context_word_adds_to_a_score_already_above_the_floor():
    class Strong(Digits):
        PATTERNS = [Pattern("digits", r"\b\d{4}\b", 0.6)]

    (finding,) = AnalyzerEngine([Strong()]).analyze("Invoice 1234 shipped.")
    assert finding.score == pytest.approx(0.95)


def test_a_context_word_matches_inside_a_longer_word(analyzer):
    """This is what lets "bank" find Maybank without listing every bank."""
    (finding,) = analyzer.analyze("Reinvoiced 1234 today.")
    assert finding.score == pytest.approx(0.4)


def test_a_context_word_beyond_the_window_is_not_counted(analyzer):
    far = " ".join(["padding"] * (CONTEXT_WINDOW + 1))
    (finding,) = analyzer.analyze(f"Invoice {far} 1234")
    assert finding.score == pytest.approx(0.05)


def test_the_score_never_passes_one():
    class Certain(Digits):
        PATTERNS = [Pattern("digits", r"\b\d{4}\b", 0.9)]

    (finding,) = AnalyzerEngine([Certain()]).analyze("Invoice 1234 shipped.")
    assert finding.score == pytest.approx(1.0)


def test_entities_can_be_narrowed(analyzer):
    assert analyzer.analyze("Order 1234", entities=["OTHER"]) == []
    assert analyzer.analyze("Order 1234", entities=["DIGITS"]) != []


def test_overlapping_claims_are_both_returned():
    findings = AnalyzerEngine([Digits(), Weak()]).analyze("Order 1234 shipped.")
    assert {f.entity_type for f in findings} == {"DIGITS", "WEAK"}


def test_resolve_keeps_the_stronger_of_two_overlapping_claims():
    findings = AnalyzerEngine([Digits(), Weak()]).analyze("Invoice 1234 shipped.")
    assert [f.entity_type for f in resolve(findings)] == ["DIGITS"]


def test_touching_spans_do_not_count_as_overlapping():
    left = Finding("A", 0, 4, 0.5)
    right = Finding("B", 4, 8, 0.4)
    assert not left.overlaps(right)
    assert len(resolve([left, right])) == 2


def test_anonymize_encrypts_every_span(anonymizer):
    text = "Order 1234 then 5678."
    result = anonymizer.anonymize(text, AnalyzerEngine([Digits()]).analyze(text))
    assert "1234" not in result.text
    assert "5678" not in result.text
    assert [item.entity_type for item in result.items] == ["DIGITS", "DIGITS"]


def test_anonymize_leaves_a_text_with_no_findings_alone(anonymizer):
    result = anonymizer.anonymize("Nothing here.", [])
    assert result.text == "Nothing here."
    assert result.items == []


def test_an_item_carries_what_was_written_into_the_text(anonymizer):
    text = "Order 1234 then 5678."
    result = anonymizer.anonymize(text, AnalyzerEngine([Digits()]).analyze(text))
    first, second = result.items
    assert result.text == f"Order {first.label} then {second.label}."


def test_a_repeated_value_earns_a_fresh_ciphertext(anonymizer):
    """Encryption is randomized, so a repeat does not collapse into one token."""
    text = "Order 1234, again 1234."
    result = anonymizer.anonymize(text, AnalyzerEngine([Digits()]).analyze(text))
    first, second = result.items
    assert first.label != second.label


def test_an_anonymized_result_reads_as_its_masked_text(anonymizer):
    text = "Order 1234."
    result = anonymizer.anonymize(text, AnalyzerEngine([Digits()]).analyze(text))
    assert str(result) == result.text
    assert "1234" not in str(result)


def test_deanonymize_undoes_anonymize(anonymizer, deanonymizer):
    text = "Order 1234 then 5678."
    result = anonymizer.anonymize(text, AnalyzerEngine([Digits()]).analyze(text))
    assert deanonymizer.deanonymize(result.text, result.items) == text


def test_deanonymize_undoes_every_span_of_a_long_text(anonymizer, deanonymizer):
    text = " ".join(str(1000 + n) for n in range(11))
    result = anonymizer.anonymize(text, AnalyzerEngine([Digits()]).analyze(text))
    assert deanonymizer.deanonymize(result.text, result.items) == text


def test_a_keyed_undo_restores_a_text_the_masking_never_saw(anonymizer, deanonymizer):
    """A key buys secrecy, not the offsets: a rewritten text still restores."""
    text = "Order 1234 then 5678."
    result = anonymizer.anonymize(text, AnalyzerEngine([Digits()]).analyze(text))
    first, second = result.items
    restored = deanonymizer.deanonymize(f"{second.label} shipped before {first.label}.", result.items)
    assert restored == "5678 shipped before 1234."


def test_another_key_cannot_undo_the_masking(anonymizer):
    text = "Order 1234."
    result = anonymizer.anonymize(text, AnalyzerEngine([Digits()]).analyze(text))
    with pytest.raises(InvalidToken):
        DeanonymizeEngine(generate_key()).deanonymize(result.text, result.items)


def test_masking_without_a_key_writes_numbered_labels():
    text = "Order 1234 then 5678."
    result = AnonymizerEngine().anonymize(text, AnalyzerEngine([Digits()]).analyze(text))
    assert result.text == "Order <DIGITS_0> then <DIGITS_1>."


def test_a_repeated_value_earns_one_label():
    text = "Order 1234, again 1234."
    result = AnonymizerEngine().anonymize(text, AnalyzerEngine([Digits()]).analyze(text))
    assert result.text == "Order <DIGITS_0>, again <DIGITS_0>."


def test_a_keyless_masking_keeps_the_original_on_its_item():
    text = "Order 1234."
    result = AnonymizerEngine().anonymize(text, AnalyzerEngine([Digits()]).analyze(text))
    assert [(i.label, i.original) for i in result.items] == [("<DIGITS_0>", "1234")]


def test_encrypting_keeps_no_original(anonymizer):
    """The point of a key: nothing readable is retained beside the masked text."""
    text = "Order 1234."
    result = anonymizer.anonymize(text, AnalyzerEngine([Digits()]).analyze(text))
    assert [item.original for item in result.items] == [None]


def test_a_keyless_undo_restores_the_masked_text():
    text = "Order 1234 then 5678."
    result = AnonymizerEngine().anonymize(text, AnalyzerEngine([Digits()]).analyze(text))
    assert DeanonymizeEngine().deanonymize(result.text, result.items) == text


def test_a_keyless_undo_restores_a_text_the_masking_never_saw():
    """This is the point of it: an answer written about the masked text."""
    text = "Order 1234 then 5678."
    result = AnonymizerEngine().anonymize(text, AnalyzerEngine([Digits()]).analyze(text))
    restored = DeanonymizeEngine().deanonymize(
        "<DIGITS_1> shipped before <DIGITS_0>.", result.items
    )
    assert restored == "5678 shipped before 1234."


def test_any_secret_the_caller_already_has_serves_as_a_key():
    key = "the-secret-out-of-your-vault"
    text = "Order 1234."
    result = AnonymizerEngine(key).anonymize(text, AnalyzerEngine([Digits()]).analyze(text))
    assert DeanonymizeEngine(key).deanonymize(result.text, result.items) == text


def test_the_same_secret_derives_the_same_key_from_bytes_or_str():
    text = "Order 1234."
    result = AnonymizerEngine("a-secret-long-enough-to-pass").anonymize(
        text, AnalyzerEngine([Digits()]).analyze(text)
    )
    undone = DeanonymizeEngine(b"a-secret-long-enough-to-pass").deanonymize(
        result.text, result.items
    )
    assert undone == text


def test_a_secret_too_short_to_be_a_key_is_refused():
    with pytest.raises(ValueError, match="at least 16 bytes"):
        AnonymizerEngine("too-short")


def test_a_pattern_can_throw_its_own_match_out():
    class Picky(Digits):
        def invalidate_result(self, matched_text):
            return matched_text.startswith("0")

    analyzer = AnalyzerEngine([Picky()])
    assert analyzer.analyze("Order 0123") == []
    assert analyzer.analyze("Order 1234") != []


def test_the_strongest_pattern_wins_a_span_it_shares():
    class Twice(PatternRecognizer):
        ENTITY = "TWICE"
        PATTERNS = [
            Pattern("weak", r"\b\d{4}\b", 0.1),
            Pattern("strong", r"\b\d{4}\b", 0.7),
        ]

    (finding,) = AnalyzerEngine([Twice()]).analyze("Order 1234")
    assert finding.score == pytest.approx(0.7)


def test_score_threshold_drops_what_no_context_vouched_for():
    analyzer = AnalyzerEngine()
    text = "Build v20250101 shipped."
    assert analyzer.analyze(text)
    assert analyzer.analyze(text, score_threshold=MIN_SCORE_WITH_CONTEXT) == []


def test_score_threshold_is_applied_after_context_is_weighed():
    """A weak match a context word rescued has to survive the threshold."""
    analyzer = AnalyzerEngine()
    findings = analyzer.analyze(
        "Her travel document is Z12345678.", score_threshold=MIN_SCORE_WITH_CONTEXT
    )
    assert [f.entity_type for f in findings] == ["MY_PASSPORT"]


def test_threshold_set_on_the_analyzer_applies_to_every_call():
    analyzer = AnalyzerEngine(score_threshold=MIN_SCORE_WITH_CONTEXT)
    assert analyzer.analyze("Build v20250101 shipped.") == []


def test_the_call_overrides_the_analyzers_threshold():
    analyzer = AnalyzerEngine(score_threshold=MIN_SCORE_WITH_CONTEXT)
    assert analyzer.analyze("Build v20250101 shipped.", score_threshold=0.0)
