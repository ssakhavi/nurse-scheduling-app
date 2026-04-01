# CLAUDE.md — Nurse Scheduling Demo

## Running the App

```bash
uv run streamlit run app.py
```

Requires a `.env` file (or environment variable) with:
```
ANTHROPIC_API_KEY=sk-ant-...
```

If the key is missing or the API call fails, the app falls back to a pre-verified OR-Tools example.

## Package Management

This project uses **uv** with **pyproject.toml**. Do not use pip directly.

```bash
# Install all dependencies (including dev tools)
uv sync --extra dev

# Add a new dependency
uv add <package>

# Add a dev-only dependency
uv add --optional dev <package>
```

## Linting and Formatting

**Ruff must be run after every code modification to `app.py`.**

```bash
# Check for lint errors
uv run ruff check app.py

# Auto-fix fixable errors
uv run ruff check --fix app.py

# Format
uv run ruff format app.py
```

Ruff is configured in `pyproject.toml` under `[tool.ruff]`.

## Architecture

### Workflow
```
Step 1: Nurse manager describes the problem in plain English
Step 2: Claude generates OR-Tools CP-SAT Python code from the description
Step 3: OR-Tools solver runs the generated code and finds the optimal schedule
Step 4: (Optional) Rescheduler re-solves with minimal changes when a nurse is unavailable
```

### Key Design Decisions

**Dynamic code execution (`exec`):**
The LLM generates a Python string containing OR-Tools code. This string is executed via `exec(code, ns)` in an isolated namespace `ns`. The namespace is then inspected for the standard variable names (`nurses`, `days`, `shift_names`, `assignment`, `solver`, `status`) to extract results. The `SYSTEM_PROMPT` enforces these variable names so extraction is reliable.

**Deterministic rescheduler (no LLM for Step 4):**
`_build_reschedule_model` builds a new CP-SAT model entirely from the solved namespace of Step 3. It reads coverage requirements directly from the original solved DataFrame (not from re-parsing the problem text), replicates hard constraints structurally, and minimises the number of assignment changes from the original. No LLM call is made — this guarantees feasibility and consistent results.

**Deviation objective:**
For each cell not forced-off by the unavailability constraint, a `dev` BoolVar is introduced. `dev = 1` if the cell changed from the original. The model minimises `sum(dev)`. Forced-off cells (the sick nurse's days) are excluded from the count — those are inputs, not disruption.

**Session state flow:**
```
st.session_state.generated_code  — OR-Tools Python string
st.session_state.llm_used        — bool (True = LLM, False = fallback)
st.session_state.solver_result   — (status, obj, df, summary)
st.session_state.original_ns     — full exec() namespace from Step 3
st.session_state.reschedule_result — (status, obj, df, summary) from Step 4
```

`original_ns` is preserved so Step 4 can access the live `CpSolver` instance and `assignment` BoolVars to read the original solved values via `solver.value(assignment[(n, d, s)])`.

### Key Functions

| Function | File | Purpose |
|----------|------|---------|
| `_call_anthropic` | app.py | LLM call to generate OR-Tools code |
| `_run_solver_code` | app.py | exec() the code, return 5-tuple including namespace |
| `_extract_results_from_ns` | app.py | Reconstruct (status, obj, df, summary) from namespace |
| `_build_reschedule_model` | app.py | Deterministic rescheduler — no LLM |
| `_parse_unavailability` | app.py | Free-text → {nurse: [days]} dict |
| `_diff_schedules` | app.py | Boolean DataFrame of changes |
| `_style_schedule_with_diff` | app.py | Amber highlighting for changed cells |
| `_verify_schedule` | app.py | Regex-based constraint verification on the output table |
