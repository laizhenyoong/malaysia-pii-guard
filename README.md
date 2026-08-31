# pii-guard

A Python library for detecting and masking Malaysian PII.

It supports MyKad numbers, Malaysian phone numbers, passport numbers, and bank account numbers.

## Install

```bash
pip install -e .
```

Python 3.9 or newer is required.

## Usage

```python
from pii_guard import malaysian_analyzer, anonymize

analyzer = malaysian_analyzer(score_threshold=0.4)
text = "IC 880101-14-5523, mobile 012-345 6789"

findings = analyzer.analyze(text)
result = anonymize(text, findings)

print(result)
# IC <MY_NRIC>, mobile <PHONE_NUMBER>
```

## How it works

```mermaid
flowchart LR
    A[Input text] --> B[Run Malaysian recognizers]

    subgraph B[Run Malaysian recognizers]
        B1[MyKad]
        B2[Phone]
        B3[Passport]
        B4[Bank account]
    end

    B --> C[Apply context score]
    C --> D{Meets threshold?}
    D -->|No| E[Ignore finding]
    D -->|Yes| F[Resolve overlaps]
    F --> G[Replace PII with entity label]

    style A fill:#f8fafc,stroke:#64748b
    style C fill:#eff6ff,stroke:#3b82f6
    style D fill:#fff7ed,stroke:#f97316
    style E fill:#fef2f2,stroke:#ef4444
    style F fill:#f0fdf4,stroke:#22c55e
    style G fill:#f0fdf4,stroke:#22c55e
```

Each recognizer finds possible PII and gives it a confidence score. Nearby words such as `IC`, `mobile`, or `account` can increase that score. Findings below the selected threshold are ignored. When findings overlap, the strongest one is used.

## Supported entities

| Entity | Detects | Validation |
|---|---|---|
| `MY_NRIC` | MyKad and NRIC numbers | Checks the date and state code |
| `PHONE_NUMBER` | Malaysian phone numbers | Uses the Malaysian numbering plan |
| `MY_PASSPORT` | Malaysian passport numbers | Checks the format and prefix |
| `MY_BANK_ACCOUNT` | Bank account numbers | Uses format and nearby context |

## Tests

```bash
pip install -e '.[test]'
pytest -q
```
