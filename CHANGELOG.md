# Changelog

## Unreleased

- **Breaking.** `AnonymizerEngine` and `DeanonymizeEngine` replace the
  `anonymize` and `rehydrate` functions, and `Item` replaces `Replacement`.
- Masking takes a key now. Without one it writes `<MY_NRIC_0>` labels as before.
  With one it encrypts each value in place and keeps no plaintext. Either way a
  text written about the masked one restores as readily as the masked text.
- **Breaking.** `Analyzer` is `AnalyzerEngine`, and it loads every recognizer
  itself, so `malaysian_analyzer` is gone.
- An engine takes any secret of 16 bytes or more as its key and stretches it
  with HKDF, so a key can come from the environment, a vault, or a KMS.
- Added a `cryptography` dependency for the encryption.
- Moved the package under `src/`, so the tests read an installed package rather
  than the working tree.
- Shipped `py.typed`, so type checkers see the annotations the package already
  carries.
- Added an MIT license, PyPI metadata, and CI across Python 3.9 to 3.13.

## 0.1.0

- Detect MyKad, phone, passport, and bank account numbers in Malaysian text.
- `anonymize` masks each finding behind a numbered label and `rehydrate` puts
  the originals back.
