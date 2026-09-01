# malaysia-pii-guard

Detect, mask, and restore Malaysian MyKad, phone, passport, and bank account numbers.

## Install

Requires Python 3.9 or newer.

```bash
python -m pip install .
```

## Usage

```python
from malaysia_pii_guard import (
    AnalyzerEngine,
    AnonymizerEngine,
    DeanonymizeEngine,
    generate_key,
)

key = generate_key()
text = "IC 880101-14-5523, mobile 012-345 6789"

analyzer = AnalyzerEngine(score_threshold=0.4)
result = AnonymizerEngine(key).anonymize(text, analyzer.analyze(text))

print(result.text)
# IC gAAAAABqlmv9LsH1mBUO3SxW...FA==, mobile gAAAAABqlmv9Nc2DT2WW...ww==

print(DeanonymizeEngine(key).deanonymize(result.text, result.items))
# IC 880101-14-5523, mobile 012-345 6789
```

## Flow

```mermaid
flowchart LR
    A[Input text] --> B[Detect PII]
    B --> C[Encrypt PII in place]
    C --> D[Store or ship the masked text]
    D --> E[Decrypt with the key]
```

The masked text carries no plaintext, so it is safe to keep or send on its own,
and `result.items` holds offsets rather than values. The key is the whole secret:
without it nothing is reversible, and with it anyone can reverse it.

> Deanonymizing reads by offset, so it undoes only the exact text `anonymize`
> returned. A masked text that was edited or rewritten in between cannot be
> restored.

## License

MIT
