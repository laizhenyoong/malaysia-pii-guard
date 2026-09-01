# Changelog

## Unreleased

- Moved the package under `src/`, so the tests read an installed package rather
  than the working tree.
- Shipped `py.typed`, so type checkers see the annotations the package already
  carries.
- Added an MIT license, PyPI metadata, and CI across Python 3.9 to 3.13.

## 0.1.0

- Detect MyKad, phone, passport, and bank account numbers in Malaysian text.
- `anonymize` masks each finding behind a numbered label and `rehydrate` puts
  the originals back.
