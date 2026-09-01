# malaysia-pii-guard

Detect, mask, and restore Malaysian MyKad, phone, passport, and bank account numbers.

## Install

Requires Python 3.9 or newer.

```bash
python -m pip install .
```

## Usage

```python
from malaysia_pii_guard import AnalyzerEngine, AnonymizerEngine, DeanonymizeEngine

text = "IC 880101-14-5523, mobile 012-345 6789"

analyzer = AnalyzerEngine(score_threshold=0.4)
result = AnonymizerEngine().anonymize(text, analyzer.analyze(text))

print(result.text)
# IC <MY_NRIC_0>, mobile <PHONE_NUMBER_0>

print(DeanonymizeEngine().deanonymize(result.text, result.items))
# IC 880101-14-5523, mobile 012-345 6789
```

Labels are swapped back wherever they turn up, so a text written *about* the
masked one restores too. The originals ride along on `result.items`, so keep
those private.

## Encrypting instead

Give the engines a key and each value is encrypted in place, so the masked text
holds no plaintext and nothing readable is kept beside it.

```python
import os

key = os.environ["PII_KEY"]
result = AnonymizerEngine(key).anonymize(text, analyzer.analyze(text))

print(DeanonymizeEngine(key).deanonymize(result.text, result.items))
# IC 880101-14-5523, mobile 012-345 6789
```

The key is any secret of 16 bytes or more, so it can come from the environment,
a vault, or a KMS. `generate_key()` makes one if you have none. Decrypting reads
by offset, so restore the text `anonymize` returned rather than one that was
edited in between.

## License

MIT
