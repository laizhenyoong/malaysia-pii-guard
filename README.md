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

## License

MIT
