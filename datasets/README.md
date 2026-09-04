# Patient Report Analyzer Datasets

This folder is an independent export of the datasets currently used by the application.

## Contents

- `reference/normal_ranges.json`: age/gender-aware laboratory reference ranges used for status comparison.
- `reference/supported_parameters.json`: supported test panels, parameter names, and aliases used by the parser.
- `reference/condition_indicators.json`: weighted indicators used by the informational condition-scoring engine.
- `sample_reports/`: 20 text-based sample laboratory reports, two for each supported panel.
- `edge_case_samples/`: 10 parser and analysis edge-case inputs used by the test suite.
- `expected_results.json`: ground-truth outputs used by the accuracy tests.
- `frontend_demo/`: sample result and history JSON used by the frontend demo/test data.

## Original locations

- Reference data: `backend/data/` and `backend/analysis/condition_indicators.json`
- Backend test data: `backend/testing/`
- Frontend demo data: `frontend/src/data/`

This is a copied export. The application continues to read its data from the original locations.
