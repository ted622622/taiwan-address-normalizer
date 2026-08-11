# Contributing

## Before opening an issue

1. Remove names, phone numbers, order IDs, notes, coordinates, and customer identifiers.
2. Reduce the example to the shortest address string that still reproduces the problem.
3. State whether you used `safe` or `aggressive` mode.
4. Include expected and actual output.

Do not upload customer spreadsheets or screenshots containing personal data.

## Development

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e . pytest ruff
python -m pytest
python -m ruff check .
```

Changes to normalization rules must include both a positive case and a regression case showing what the rule must not change.

