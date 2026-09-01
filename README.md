# malaysia-pii-guard

Detect, mask, and restore Malaysian MyKad, phone, passport, and bank account numbers.

## Install

Requires Python 3.9 or newer.

```bash
python -m pip install .
```

## Usage

```python
from malaysia_pii_guard import AnalyzerEngine, anonymize, rehydrate

text = "IC 880101-14-5523, mobile 012-345 6789"
analyzer = AnalyzerEngine(score_threshold=0.4)
result = anonymize(text, analyzer.analyze(text))

print(result.text)
# IC <MY_NRIC_0>, mobile <PHONE_NUMBER_0>

print(rehydrate(result.text, result.replacements))
# IC 880101-14-5523, mobile 012-345 6789
```

## Flow

```mermaid
flowchart LR
    A[Input text] --> B[Detect PII]
    B --> C[Mask PII]
    C --> D[Process masked text]
    D --> E[Restore PII]
```

> Keep `result.replacements` private because it contains the original PII.

## License

MIT
