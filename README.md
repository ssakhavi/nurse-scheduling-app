# Nurse Scheduling Demo

A Streamlit application demonstrating a **neuro-symbolic hybrid** approach to healthcare scheduling: Claude (LLM) translates natural language problem descriptions into Google OR-Tools CP-SAT code, and the solver guarantees a mathematically optimal, constraint-satisfying roster.

The central argument: LLMs alone achieve only ~65% feasibility on scheduling benchmarks. Pairing an LLM as a natural language interface with a deterministic solver gives 100% feasibility — every time.

---

## Features

- **Step 1 — Describe the problem** — type the scheduling rules in plain English, or upload a `.txt` file
- **Step 2 — Generate code** — Claude translates the description into OR-Tools CP-SAT Python code
- **Step 3 — Solve** — the solver finds the optimal, constraint-satisfying schedule; constraints are verified against the output table
- **Step 4 — Reschedule** — when a nurse becomes unavailable (e.g. sick leave), re-solve with provably minimal disruption to the rest of the roster

---

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/ssakhavi/nurse-scheduling-app.git
cd nurse-scheduling-app
uv sync
```

Create a `.env` file with your Anthropic API key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

If no key is provided the app falls back to a pre-verified OR-Tools example.

---

## Running

```bash
uv run streamlit run app.py
```

---

## Development

```bash
uv sync --extra dev       # installs ruff

uv run ruff check app.py  # lint
uv run ruff format app.py # format
```

Ruff must pass after every code modification. See `CLAUDE.md` for architecture details.

---

## Repository Layout

| File | Description |
|------|-------------|
| `app.py` | Streamlit application (all app logic) |
| `main.py` | Minimal entry point |
| `pyproject.toml` | Dependencies and Ruff configuration (managed by uv) |
| `uv.lock` | Locked dependency versions |
| `CHANGELOG.md` | Version history |
| `CLAUDE.md` | Architecture notes and development guidelines |
| `LLM-SCHEDULING-HEALTHCARE.md` | Background research: OR foundations, LLM capabilities, case studies |
| `LIMITATIONS.md` | Analysis of LLM limitations in scheduling tasks |

---

## How the Rescheduler Works

After an initial schedule is produced, Step 4 builds a fresh CP-SAT model that:

1. Reads per-day coverage requirements directly from the solved schedule
2. Forces the unavailable nurse to Off on their specified days
3. Introduces a deviation variable for every other cell
4. Minimises `sum(deviation_vars)` — the count of changed assignments

The result is a schedule with the fewest possible changes from the original, guaranteed by the solver.

---

## Further Reading

- `LLM-SCHEDULING-HEALTHCARE.md` — comprehensive background on OR + LLM integration
- `LIMITATIONS.md` — why LLMs alone are unreliable for scheduling, and how neuro-symbolic hybrids address this
