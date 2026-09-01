import pytest

from malaysia_pii_guard import (
    Analyzer,
    Finding,
    Pattern,
    PatternRecognizer,
    anonymize,
    malaysian_analyzer,
    rehydrate,
    resolve,
)
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
    return Analyzer([Digits()])


def test_a_bare_match_keeps_its_pattern_score(analyzer):
    (finding,) = analyzer.analyze("Order 1234 shipped.")
    assert finding.score == pytest.approx(0.05)


def test_a_context_word_lifts_a_weak_match_to_the_floor(analyzer):
    (finding,) = analyzer.analyze("Invoice 1234 shipped.")
    assert finding.score == pytest.approx(0.4)


def test_a_context_word_adds_to_a_score_already_above_the_floor():
    class Strong(Digits):
        PATTERNS = [Pattern("digits", r"\b\d{4}\b", 0.6)]

    (finding,) = Analyzer([Strong()]).analyze("Invoice 1234 shipped.")
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

    (finding,) = Analyzer([Certain()]).analyze("Invoice 1234 shipped.")
    assert finding.score == pytest.approx(1.0)


def test_entities_can_be_narrowed(analyzer):
    assert analyzer.analyze("Order 1234", entities=["OTHER"]) == []
    assert analyzer.analyze("Order 1234", entities=["DIGITS"]) != []


def test_overlapping_claims_are_both_returned():
    findings = Analyzer([Digits(), Weak()]).analyze("Order 1234 shipped.")
    assert {f.entity_type for f in findings} == {"DIGITS", "WEAK"}


def test_resolve_keeps_the_stronger_of_two_overlapping_claims():
    findings = Analyzer([Digits(), Weak()]).analyze("Invoice 1234 shipped.")
    assert [f.entity_type for f in resolve(findings)] == ["DIGITS"]


def test_touching_spans_do_not_count_as_overlapping():
    left = Finding("A", 0, 4, 0.5)
    right = Finding("B", 4, 8, 0.4)
    assert not left.overlaps(right)
    assert len(resolve([left, right])) == 2


def test_anonymize_replaces_every_span_from_the_right():
    text = "Order 1234 then 5678."
    assert anonymize(text, Analyzer([Digits()]).analyze(text)).text == (
        "Order <DIGITS_0> then <DIGITS_1>."
    )


def test_anonymize_leaves_a_text_with_no_findings_alone():
    result = anonymize("Nothing here.", [])
    assert result.text == "Nothing here."
    assert result.replacements == []


def test_a_repeated_value_earns_one_label():
    text = "Order 1234, again 1234."
    result = anonymize(text, Analyzer([Digits()]).analyze(text))
    assert result.text == "Order <DIGITS_0>, again <DIGITS_0>."
    assert [r.original for r in result.replacements] == ["1234"]


def test_a_replacement_carries_the_value_it_stands_for():
    text = "Order 1234 then 5678."
    result = anonymize(text, Analyzer([Digits()]).analyze(text))
    assert [(r.entity_type, r.label, r.original) for r in result.replacements] == [
        ("DIGITS", "<DIGITS_0>", "1234"),
        ("DIGITS", "<DIGITS_1>", "5678"),
    ]


def test_an_anonymized_result_reads_as_its_masked_text():
    text = "Order 1234."
    result = anonymize(text, Analyzer([Digits()]).analyze(text))
    assert str(result) == "Order <DIGITS_0>."


def test_rehydrate_undoes_anonymize():
    text = "Order 1234 then 5678."
    result = anonymize(text, Analyzer([Digits()]).analyze(text))
    assert rehydrate(result.text, result.replacements) == text


def test_rehydrate_restores_a_text_the_masking_never_saw():
    """This is the point of it: an answer written about the masked text."""
    text = "Order 1234 then 5678."
    result = anonymize(text, Analyzer([Digits()]).analyze(text))
    assert rehydrate("<DIGITS_1> shipped before <DIGITS_0>.", result.replacements) == (
        "5678 shipped before 1234."
    )


def test_rehydrate_leaves_a_label_the_text_never_mentions():
    text = "Order 1234 then 5678."
    result = anonymize(text, Analyzer([Digits()]).analyze(text))
    assert rehydrate("Only <DIGITS_0>.", result.replacements) == "Only 1234."


def test_rehydrate_tells_the_tenth_label_from_the_first():
    text = " ".join(str(1000 + n) for n in range(11))
    result = anonymize(text, Analyzer([Digits()]).analyze(text))
    assert rehydrate(result.text, result.replacements) == text


def test_a_pattern_can_throw_its_own_match_out():
    class Picky(Digits):
        def invalidate_result(self, matched_text):
            return matched_text.startswith("0")

    analyzer = Analyzer([Picky()])
    assert analyzer.analyze("Order 0123") == []
    assert analyzer.analyze("Order 1234") != []


def test_the_strongest_pattern_wins_a_span_it_shares():
    class Twice(PatternRecognizer):
        ENTITY = "TWICE"
        PATTERNS = [
            Pattern("weak", r"\b\d{4}\b", 0.1),
            Pattern("strong", r"\b\d{4}\b", 0.7),
        ]

    (finding,) = Analyzer([Twice()]).analyze("Order 1234")
    assert finding.score == pytest.approx(0.7)


def test_score_threshold_drops_what_no_context_vouched_for():
    analyzer = malaysian_analyzer()
    text = "Build v20250101 shipped."
    assert analyzer.analyze(text)
    assert analyzer.analyze(text, score_threshold=MIN_SCORE_WITH_CONTEXT) == []


def test_score_threshold_is_applied_after_context_is_weighed():
    """A weak match a context word rescued has to survive the threshold."""
    analyzer = malaysian_analyzer()
    findings = analyzer.analyze(
        "Her travel document is Z12345678.", score_threshold=MIN_SCORE_WITH_CONTEXT
    )
    assert [f.entity_type for f in findings] == ["MY_PASSPORT"]


def test_threshold_set_on_the_analyzer_applies_to_every_call():
    analyzer = malaysian_analyzer(score_threshold=MIN_SCORE_WITH_CONTEXT)
    assert analyzer.analyze("Build v20250101 shipped.") == []


def test_the_call_overrides_the_analyzers_threshold():
    analyzer = malaysian_analyzer(score_threshold=MIN_SCORE_WITH_CONTEXT)
    assert analyzer.analyze("Build v20250101 shipped.", score_threshold=0.0)
