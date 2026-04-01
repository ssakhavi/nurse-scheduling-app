# Changelog

All notable changes to this project are documented here.
Versioning follows [Semantic Versioning](https://semver.org): MAJOR.MINOR.PATCH.

## [0.1.0] — 2026-04-01

### Added
- Streamlit app with 3-step workflow: describe problem → generate OR-Tools code via Claude → solve
- Step 4 rescheduling: re-solve with minimal changes when a nurse is unavailable
  - Free-text unavailability input with live parse preview
  - Manual multiselect override per nurse
  - Deviation-minimisation objective in CP-SAT (provably minimal disruption)
  - Side-by-side diff with amber highlighting for changed cells
  - Per-nurse disruption summary table
- Project tooling: uv + pyproject.toml, Ruff linting/formatting, CLAUDE.md
