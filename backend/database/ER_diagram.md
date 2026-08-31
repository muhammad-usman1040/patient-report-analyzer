# Entity Relationship Diagram

## Tables and Relationships

```
Users
  id PK
  email UNIQUE
  password_hash
  created_at
      |
      | 1:N
      v
Reports
  id PK
  user_id FK -> Users.id
  report_date
  patient_gender
  patient_age
  output_format
      |
      | 1:N (two children)
     / \
    /   \
Test_Results       Analysis_Results
  id PK              id PK
  report_id FK       report_id FK
  test_category      result_type
  parameter_name     condition_name
  value              confidence_score
  unit               supporting_indicators
  status             created_at

Normal_Ranges (reference table, no FK)
  id PK
  category
  parameter_name
  gender
  min_value
  max_value
  unit

Condition_Indicators (reference table, no FK)
  id PK
  condition_name
  parameter_name
  direction
  weight
```

## Notes
- `Users` → `Reports`: one user can have many reports.
- `Reports` → `Test_Results`: each report stores one row per extracted parameter.
- `Reports` → `Analysis_Results`: each report stores one or more condition findings.
- `Normal_Ranges` and `Condition_Indicators` are static reference tables loaded from JSON at startup.
- Raw files and raw OCR text are never persisted.
