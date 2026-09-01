# pii-guard

A Python library for detecting and masking Malaysian PII, including MyKad numbers, phone numbers, passport numbers, and bank account numbers.

## Install

Python 3.9 or newer is required.

```bash
python -m pip install .
```

## Usage

```python
from pii_guard import anonymize, malaysian_analyzer, rehydrate

text = "IC 880101-14-5523, mobile 012-345 6789"
analyzer = malaysian_analyzer(score_threshold=0.4)

result = anonymize(text, analyzer.analyze(text))
print(result.text)
# IC <MY_NRIC_0>, mobile <PHONE_NUMBER_0>

answer = "<MY_NRIC_0> belongs to <PHONE_NUMBER_0>."
print(rehydrate(answer, result.replacements))
# 880101-14-5523 belongs to 012-345 6789.
```

`anonymize` replaces detected PII with reusable labels. Repeated values of the same entity type share a label. `rehydrate` restores those labels in any returned text using `result.replacements`.

Keep `result.replacements` private because it contains the original PII. Masking is not encryption.

## Tests

```bash
python -m pip install -e '.[test]'
pytest -q
```
