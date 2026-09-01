# malaysia-pii-guard

Detect, mask, and restore Malaysian MyKad, phone, passport, and bank account numbers.

## Install

Requires Python 3.9 or newer.

```bash
python -m pip install .
```

## Usage

```python
import os

from malaysia_pii_guard import AnalyzerEngine, AnonymizerEngine, DeanonymizeEngine

key = os.environ["PII_KEY"]
text = "IC 880101-14-5523, mobile 012-345 6789"

analyzer = AnalyzerEngine(score_threshold=0.4)
result = AnonymizerEngine(key).anonymize(text, analyzer.analyze(text))

print(result.text)
# IC gAAAAABqlmv9LsH1mBUO3SxW...FA==, mobile gAAAAABqlmv9Nc2DT2WW...ww==

print(DeanonymizeEngine(key).deanonymize(result.text, result.items))
# IC 880101-14-5523, mobile 012-345 6789
```

The key is any secret of 16 bytes or more, so it can come from the environment,
a vault, or a KMS. `generate_key()` makes one if you have none.

Masking encrypts each value in place, so the masked text holds no plaintext and
only the key undoes it. `result.items` holds offsets into that text, so restore
the text `anonymize` returned rather than one that was edited in between.

## License

MIT
