import pytest

from malaysia_pii_guard import MyPassportRecognizer, anonymize, malaysian_analyzer


@pytest.fixture(scope="module")
def recognizer():
    return MyPassportRecognizer()


@pytest.fixture(scope="module")
def analyzer():
    return malaysian_analyzer()


def scores(recognizer, text):
    return [finding.score for finding in recognizer.analyze(text)]


@pytest.mark.parametrize(
    "text",
    [
        "A12345678",
        "H12345678",
        "K12345678",
        "h87654321",
    ],
)
def test_detects_issued_prefixes(recognizer, text):
    """An issued letter ranks a match, it does not verify one."""
    assert scores(recognizer, text) == [pytest.approx(0.1)]


@pytest.mark.parametrize(
    "text, reason",
    [
        ("Z12345678", "a series this list has not caught up with"),
        ("B87654321", "not a series we know of"),
    ],
)
def test_unlisted_prefix_is_scored_down_not_dropped(recognizer, text, reason):
    assert scores(recognizer, text) == [pytest.approx(0.05)], reason


@pytest.mark.parametrize(
    "text, reason",
    [
        ("A1234567", "seven digits is too short"),
        ("A123456789", "nine digits is too long"),
        ("12345678", "no prefix at all"),
        ("AB1234567", "two letters is not the shape"),
        ("MYSH12345678", "no boundary before the letter, so it is part of a longer token"),
        ("H12345678A", "no boundary after the digits"),
    ],
)
def test_ignores_other_shapes(recognizer, text, reason):
    assert scores(recognizer, text) == [], reason


@pytest.mark.parametrize("text", ["H00000000", "A11111111"])
def test_rejects_repeated_digits(recognizer, text):
    assert scores(recognizer, text) == []


def test_context_word_raises_the_score(analyzer):
    def score(text):
        return next(
            f.score for f in analyzer.analyze(text) if f.entity_type == "MY_PASSPORT"
        )

    assert score("My passport is Z12345678.") > score("Ref Z12345678.")


def test_an_issued_prefix_outranks_an_unlisted_one(recognizer):
    assert scores(recognizer, "H12345678") > scores(recognizer, "Z12345678")


def test_context_lifts_an_unlisted_prefix_to_the_floor(analyzer):
    (finding,) = [
        f
        for f in analyzer.analyze("Passport Z12345678 expires soon.")
        if f.entity_type == "MY_PASSPORT"
    ]
    assert finding.score == pytest.approx(0.4)


def test_finds_every_number_in_a_sentence(recognizer):
    text = "Travelling on A12345678, previously H87654321."
    findings = recognizer.analyze(text)
    assert [text[f.start : f.end] for f in findings] == ["A12345678", "H87654321"]


def test_passport_and_mykad_do_not_steal_each_others_spans(analyzer):
    text = "IC 850312-08-5431, passport A12345678."
    found = {
        f.entity_type: text[f.start : f.end]
        for f in analyzer.analyze(text)
        if f.entity_type in ("MY_NRIC", "MY_PASSPORT")
    }
    assert found == {"MY_NRIC": "850312-08-5431", "MY_PASSPORT": "A12345678"}


def test_masks_under_the_right_label(analyzer):
    text = "My passport is A12345678."
    assert anonymize(text, analyzer.analyze(text)).text == (
        "My passport is <MY_PASSPORT_0>."
    )
