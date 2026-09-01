# Changelog

## Unreleased

- **Breaking.** Masking is reversible by encryption now, following Presidio.
  `AnonymizerEngine(key).anonymize` and `DeanonymizeEngine(key).deanonymize`
  replace the `anonymize` and `rehydrate` functions, and `Item` offsets replace
  `Replacement` labels. A masked text can no longer be rewritten before it is
  restored, and masked values no longer read as `<MY_NRIC_0>`.
- **Breaking.** `Analyzer` is `AnalyzerEngine`, and it loads every recognizer
  itself, so `malaysian_analyzer` is gone.
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
