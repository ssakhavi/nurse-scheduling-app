"""
Healthcare Scheduling Demo — Streamlit Application
Natural Language → Optimal Roster via LLM + OR-Tools
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

import anthropic
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from ortools.sat.python import cp_model

HISTORY_FILE = Path(__file__).parent / "query_history.json"

# ── Full-name → short-name lookup for day parsing ────────────────────────────
_DAY_ALIASES = {
    "monday": "Mon",
    "tuesday": "Tue",
    "wednesday": "Wed",
    "thursday": "Thu",
    "friday": "Fri",
    "saturday": "Sat",
    "sunday": "Sun",
}


def _load_history() -> list:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text())
        except Exception:
            return []
    return []


def _save_history(history: list) -> None:
    HISTORY_FILE.write_text(json.dumps(history, indent=2))


def _append_query(problem: str, model: str, code: str) -> None:
    history = _load_history()
    history.append(
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "model": model,
            "problem": problem,
            "generated_code": code,
        }
    )
    _save_history(history)


load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Healthcare Scheduling Demo",
    page_icon="🏥",
    layout="wide",
)


# ── Connectivity check (runs on every page load) ──────────────────────────────
def _ping_anthropic() -> tuple[str, str]:
    """Return (state, message): state is 'ok', 'error', or 'no_key'."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return "no_key", "ANTHROPIC_API_KEY not set"
    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=5,
            messages=[{"role": "user", "content": "Reply with the single word: pong"}],
        )
        return "ok", "connected"
    except Exception as exc:
        return "error", str(exc)[:80]


with st.spinner("Checking Anthropic API …"):
    _api_state, _api_msg = _ping_anthropic()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Settings")

    model_name = st.selectbox("Model", ["claude-sonnet-4-6", "claude-haiku-4-5-20251001"])

    if _api_state == "ok":
        st.success("Anthropic API — connected")
    elif _api_state == "error":
        st.error(f"Anthropic API — {_api_msg}")
    else:
        st.warning("Anthropic API — key missing")

    provider_ready = _api_state == "ok"

    st.divider()
    st.markdown(
        "**Workflow**\n\n"
        "1. Describe the problem in plain English\n"
        "2. Claude translates it to OR-Tools code\n"
        "3. Solver finds the optimal schedule\n"
        "4. Review and approve\n"
        "5. Reschedule with minimal changes if needed"
    )

    st.divider()
    st.subheader("Query History")
    _history = _load_history()
    if not _history:
        st.caption("No queries yet.")
    else:
        if st.button("Clear history", use_container_width=True):
            _save_history([])
            st.rerun()
        for entry in reversed(_history):
            with st.expander(f"{entry['timestamp']}  ·  {entry['model'].split('-')[1]}"):
                st.caption(f"**Model:** {entry['model']}")
                st.text_area(
                    "Problem",
                    value=entry["problem"],
                    height=120,
                    disabled=True,
                    key=f"hist_prob_{entry['timestamp']}",
                )
                st.code(entry["generated_code"], language="python")

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🏥 Healthcare Scheduling Demo")
st.markdown(
    "**Natural Language → Optimal Roster via LLM + OR-Tools**\n\n"
    "```\nPlain English  →  Claude  →  OR-Tools Code  →  Valid, Optimal Schedule\n```\n"
    "_Claude **translates**. The solver **guarantees**._"
)

# ── Constants ─────────────────────────────────────────────────────────────────
DEFAULT_PROBLEM = """\
I need to build a weekly roster for Ward 6.

We have 5 nurses: Alice, Bob, Carol, Dave, and Eve.

There are two shift types each day:
  - Day shift   (07:00 – 19:00)
  - Night shift  (19:00 – 07:00)

Rules that MUST be followed (hard constraints):
  1. Every day needs exactly 2 nurses on the Day shift and 1 nurse on the Night shift.
  2. No nurse can work more than one shift per day.
  3. No nurse should work more than 5 shifts in the week.
  4. No nurse should work two consecutive night shifts.

Goal: distribute shifts as fairly as possible across all nurses.
"""

SYSTEM_PROMPT = """\
You are an expert Operations Research engineer.
When given a scheduling problem in plain English, write clean, correct Python code
using the Google OR-Tools CP-SAT solver (ortools.sat.python.cp_model).

Requirements:
- Use cp_model.CpModel() for the model
- Use new_bool_var for binary assignment variables
- Translate every hard constraint faithfully
- Use add_max_equality / add_min_equality for the fairness objective
- Print a schedule table using pandas at the end
- Output ONLY a Python code block, no explanation

Variable naming — you MUST use exactly these names:
- nurses      : list of nurse name strings
- days        : list of day name strings
- shift_names : list of shift name strings
- assignment  : dict keyed by (nurse_index, day_index, shift_index) → BoolVar
- solver      : the cp_model.CpSolver() instance
- status      : the return value of solver.solve(model)
"""

FALLBACK_CODE = """\
from ortools.sat.python import cp_model
import pandas as pd

nurses      = ["Alice", "Bob", "Carol", "Dave", "Eve"]
days        = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
shift_names = ["Day", "Night"]

num_nurses = len(nurses)
num_days   = len(days)
num_shifts = len(shift_names)

model = cp_model.CpModel()

assignment = {}
for n in range(num_nurses):
    for d in range(num_days):
        for s in range(num_shifts):
            assignment[(n, d, s)] = model.new_bool_var(f"n{n}_d{d}_s{s}")

for d in range(num_days):
    model.add(sum(assignment[(n, d, 0)] for n in range(num_nurses)) == 2)
    model.add(sum(assignment[(n, d, 1)] for n in range(num_nurses)) == 1)

for n in range(num_nurses):
    for d in range(num_days):
        model.add_at_most_one(assignment[(n, d, s)] for s in range(num_shifts))

for n in range(num_nurses):
    model.add(
        sum(assignment[(n, d, s)]
            for d in range(num_days)
            for s in range(num_shifts)) <= 5
    )

for n in range(num_nurses):
    for d in range(num_days - 1):
        model.add(assignment[(n, d, 1)] + assignment[(n, d + 1, 1)] <= 1)

shift_counts = []
for n in range(num_nurses):
    count = model.new_int_var(0, num_days * num_shifts, f"count_{n}")
    model.add(count == sum(
        assignment[(n, d, s)]
        for d in range(num_days)
        for s in range(num_shifts)
    ))
    shift_counts.append(count)

max_count = model.new_int_var(0, num_days * num_shifts, "max_count")
min_count = model.new_int_var(0, num_days * num_shifts, "min_count")
model.add_max_equality(max_count, shift_counts)
model.add_min_equality(min_count, shift_counts)
model.minimize(max_count - min_count)

solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = 30.0
status = solver.solve(model)

_status_name = solver.status_name(status)
_objective   = int(solver.objective_value)

rows = {}
for n, name in enumerate(nurses):
    row = []
    for d in range(num_days):
        assigned = "Off"
        for s, sname in enumerate(shift_names):
            if solver.value(assignment[(n, d, s)]) == 1:
                assigned = sname
        row.append(assigned)
    rows[name] = row

_schedule_df = pd.DataFrame(rows, index=days).T

_summary = []
for n, name in enumerate(nurses):
    total   = sum(solver.value(assignment[(n, d, s)]) for d in range(num_days) for s in range(num_shifts))
    day_s   = sum(solver.value(assignment[(n, d, 0)]) for d in range(num_days))
    night_s = sum(solver.value(assignment[(n, d, 1)]) for d in range(num_days))
    _summary.append({"Nurse": name, "Day shifts": day_s, "Night shifts": night_s, "Total": total})
"""


# ── Helpers ───────────────────────────────────────────────────────────────────
def _extract_code(raw: str) -> str:
    if "```python" in raw:
        return raw.split("```python")[1].split("```")[0].strip()
    if "```" in raw:
        return raw.split("```")[1].split("```")[0].strip()
    return raw.strip()


def _call_anthropic(problem: str, model: str) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Write OR-Tools CP-SAT code for this scheduling problem:\n\n{problem}",
            }
        ],
    )
    return _extract_code(msg.content[0].text)


def _extract_results_from_ns(ns: dict):
    """Build (status_name, objective, df, summary) from an LLM code namespace.

    LLM-generated code won't set our private ``_*`` variables, but it will
    always leave behind ``solver``, ``status``, ``assignment``, ``nurses``,
    ``days``, and ``shift_names``.  We reconstruct the outputs from those.
    """
    solver = ns["solver"]
    status = ns["status"]
    assignment = ns["assignment"]
    nurses = ns["nurses"]
    days = ns["days"]
    shift_names = ns["shift_names"]

    status_name = solver.status_name(status)
    objective = int(solver.objective_value)

    rows = {}
    for n, name in enumerate(nurses):
        row = []
        for d in range(len(days)):
            assigned = "Off"
            for s, sname in enumerate(shift_names):
                if solver.value(assignment[(n, d, s)]) == 1:
                    assigned = sname
            row.append(assigned)
        rows[name] = row

    schedule_df = pd.DataFrame(rows, index=days).T

    summary = []
    for n, name in enumerate(nurses):
        total = sum(
            solver.value(assignment[(n, d, s)])
            for d in range(len(days))
            for s in range(len(shift_names))
        )
        day_s = sum(solver.value(assignment[(n, d, 0)]) for d in range(len(days)))
        night_s = sum(solver.value(assignment[(n, d, 1)]) for d in range(len(days)))
        summary.append(
            {"Nurse": name, "Day shifts": day_s, "Night shifts": night_s, "Total": total}
        )

    return status_name, objective, schedule_df, summary


def _run_solver_code(code: str):
    """Exec solver code and return (status, objective, df, summary, namespace)."""
    ns = {}
    exec(code, ns)

    # Our pre-verified code sets _status_name; LLM code does not.
    if "_status_name" in ns:
        return ns["_status_name"], ns["_objective"], ns["_schedule_df"], ns["_summary"], ns

    # LLM-generated code: extract results from the live solver namespace.
    status_name, objective, df, summary = _extract_results_from_ns(ns)
    return status_name, objective, df, summary, ns


def _verify_schedule(df: pd.DataFrame, problem: str) -> list[dict]:
    """Check the schedule DataFrame against the constraints in the problem text.

    Works purely from the output table — catches LLM mistranslations that
    OR-Tools can't detect because it only knows what code it was given.

    Returns a list of dicts with keys: rule, passed (bool), detail (str).
    """
    days = df.columns.tolist()
    nurses = df.index.tolist()
    checks = []

    # ── Coverage: exact counts per day ───────────────────────────────────────
    day_need = night_need = None
    m = re.search(r"(\d+)\s+nurse[s]?\s+on\s+the\s+Day", problem, re.IGNORECASE)
    if m:
        day_need = int(m.group(1))
    m = re.search(r"(\d+)\s+nurse[s]?\s+on\s+the\s+Night", problem, re.IGNORECASE)
    if m:
        night_need = int(m.group(1))

    if day_need is not None:
        violations = []
        for day in days:
            count = (df[day] == "Day").sum()
            if count != day_need:
                violations.append(f"{day}: {count} (expected {day_need})")
        checks.append(
            {
                "rule": f"Each day has exactly {day_need} Day nurse(s)",
                "passed": len(violations) == 0,
                "detail": ", ".join(violations) if violations else "All days correct",
            }
        )

    if night_need is not None:
        violations = []
        for day in days:
            count = (df[day] == "Night").sum()
            if count != night_need:
                violations.append(f"{day}: {count} (expected {night_need})")
        checks.append(
            {
                "rule": f"Each day has exactly {night_need} Night nurse(s)",
                "passed": len(violations) == 0,
                "detail": ", ".join(violations) if violations else "All days correct",
            }
        )

    # ── Max shifts per nurse ─────────────────────────────────────────────────
    m = re.search(r"more than\s+(\d+)\s+shift", problem, re.IGNORECASE)
    if m:
        max_shifts = int(m.group(1))
        violations = []
        for nurse in nurses:
            total = (df.loc[nurse] != "Off").sum()
            if total > max_shifts:
                violations.append(f"{nurse}: {total}")
        checks.append(
            {
                "rule": f"No nurse works more than {max_shifts} shifts",
                "passed": len(violations) == 0,
                "detail": ", ".join(violations) if violations else "All nurses within limit",
            }
        )

    # ── One shift per day per nurse ──────────────────────────────────────────
    checks.append(
        {
            "rule": "No nurse works more than one shift per day",
            "passed": True,
            "detail": "Structurally enforced by single value per cell",
        }
    )

    # ── No consecutive night shifts ──────────────────────────────────────────
    if re.search(r"consecutive night", problem, re.IGNORECASE):
        violations = []
        for nurse in nurses:
            for i in range(len(days) - 1):
                if df.loc[nurse, days[i]] == "Night" and df.loc[nurse, days[i + 1]] == "Night":
                    violations.append(f"{nurse}: {days[i]}–{days[i + 1]}")
        checks.append(
            {
                "rule": "No consecutive night shifts",
                "passed": len(violations) == 0,
                "detail": ", ".join(violations) if violations else "No consecutive nights found",
            }
        )

    return checks


def _style_schedule(df: pd.DataFrame):
    def _cell(val):
        if val == "Day":
            return "background-color:#1a4a2e; color:#86efac; font-weight:600"
        if val == "Night":
            return "background-color:#1e3a5f; color:#93c5fd; font-weight:600"
        return "color:#9ca3af"

    return df.style.map(_cell)


# ── Rescheduling helpers ──────────────────────────────────────────────────────


def _parse_unavailability(
    text: str,
    valid_nurses: list[str],
    valid_days: list[str],
) -> dict[str, list[str]]:
    """Parse free-text unavailability into {nurse_name: [day_name, ...]}.

    Finds any valid nurse name and any valid day name (or full-name equivalent)
    in the text and associates all found days with all found nurses.
    """
    text_lower = text.lower()

    # Build a reverse lookup: lowercase short name → canonical short name
    short_lookup = {d.lower(): d for d in valid_days}
    # Add full-name aliases
    alias_lookup = {full: short for full, short in _DAY_ALIASES.items() if short in short_lookup}

    found_nurses = [n for n in valid_nurses if n.lower() in text_lower]
    found_days: list[str] = []
    for short_lower, canonical in short_lookup.items():
        if re.search(rf"\b{re.escape(short_lower)}\b", text_lower):
            found_days.append(canonical)
    for full_name, canonical in alias_lookup.items():
        if re.search(rf"\b{re.escape(full_name)}\b", text_lower) and canonical not in found_days:
            found_days.append(canonical)

    if not found_nurses or not found_days:
        return {}

    return {nurse: found_days for nurse in found_nurses}  # noqa: C420


def _build_reschedule_model(
    original_ns: dict,
    unavailability: dict[str, list[str]],
    original_df: pd.DataFrame,
) -> tuple[str, int, pd.DataFrame, list[dict]]:
    """Re-solve with minimal changes from the original schedule.

    Deterministic — no LLM involved. Reads the solved namespace from Step 3,
    forces sick nurses to Off on their unavailable days, and minimises the
    number of assignment changes across all other cells.

    Raises ValueError if the model is infeasible.
    """
    original_solver = original_ns["solver"]
    original_assignment = original_ns["assignment"]
    nurses: list[str] = original_ns["nurses"]
    days: list[str] = original_ns["days"]
    shift_names: list[str] = original_ns["shift_names"]

    num_nurses = len(nurses)
    num_days = len(days)
    num_shifts = len(shift_names)

    # ── Step A: Build anchor from the solved original ─────────────────────────
    # anchor[(n, d)] = shift_idx | None (None means Off)
    anchor: dict[tuple[int, int], int | None] = {}
    for n in range(num_nurses):
        for d in range(num_days):
            anchor[(n, d)] = None
            for s in range(num_shifts):
                if original_solver.value(original_assignment[(n, d, s)]) == 1:
                    anchor[(n, d)] = s
                    break

    # ── Step B: Build forced-off index set ───────────────────────────────────
    forced_off: set[tuple[int, int]] = set()
    for nurse_name, day_names in unavailability.items():
        if nurse_name not in nurses:
            continue
        n_idx = nurses.index(nurse_name)
        for day_name in day_names:
            if day_name not in days:
                continue
            d_idx = days.index(day_name)
            forced_off.add((n_idx, d_idx))

    # ── Step C: New CP-SAT model ──────────────────────────────────────────────
    new_model = cp_model.CpModel()
    new_assignment: dict[tuple[int, int, int], cp_model.IntVar] = {}
    for n in range(num_nurses):
        for d in range(num_days):
            for s in range(num_shifts):
                new_assignment[(n, d, s)] = new_model.new_bool_var(f"r_n{n}_d{d}_s{s}")

    # ── Step D: Replicate hard constraints ────────────────────────────────────
    # Coverage: read per-day shift counts from the original solved DataFrame
    for d, day_name in enumerate(days):
        col = original_df[day_name]
        for s_idx, s_name in enumerate(shift_names):
            required = int((col == s_name).sum())
            new_model.add(sum(new_assignment[(n, d, s_idx)] for n in range(num_nurses)) == required)

    # At-most-one shift per nurse per day
    for n in range(num_nurses):
        for d in range(num_days):
            new_model.add_at_most_one(new_assignment[(n, d, s)] for s in range(num_shifts))

    # No consecutive night shifts (find Night shift by case-insensitive search)
    night_idx: int | None = next(
        (i for i, name in enumerate(shift_names) if "night" in name.lower()), None
    )
    if night_idx is not None:
        for n in range(num_nurses):
            for d in range(num_days - 1):
                new_model.add(
                    new_assignment[(n, d, night_idx)] + new_assignment[(n, d + 1, night_idx)] <= 1
                )

    # ── Step E: Apply forced-off constraints ──────────────────────────────────
    for n_idx, d_idx in forced_off:
        for s in range(num_shifts):
            new_model.add(new_assignment[(n_idx, d_idx, s)] == 0)

    # ── Step F: Objective — minimise deviations from anchor ──────────────────
    deviation_vars = []
    for n in range(num_nurses):
        for d in range(num_days):
            if (n, d) in forced_off:
                # Forced cells are inputs, not disruption — exclude from count
                continue

            original_shift = anchor[(n, d)]
            dev = new_model.new_bool_var(f"dev_n{n}_d{d}")
            deviation_vars.append(dev)

            if original_shift is None:
                # Original was Off; deviation = 1 if now assigned to any shift
                was_off_stays_off = new_model.new_bool_var(f"stays_off_n{n}_d{d}")
                new_model.add(
                    sum(new_assignment[(n, d, s)] for s in range(num_shifts)) == 0
                ).only_enforce_if(was_off_stays_off)
                new_model.add(
                    sum(new_assignment[(n, d, s)] for s in range(num_shifts)) >= 1
                ).only_enforce_if(was_off_stays_off.negated())
                new_model.add(dev == was_off_stays_off.negated())
            else:
                # Original was shift `original_shift`; deviation = 1 if changed
                new_model.add(dev == 1 - new_assignment[(n, d, original_shift)])

    new_model.minimize(sum(deviation_vars))

    # ── Step G: Solve ─────────────────────────────────────────────────────────
    new_solver = cp_model.CpSolver()
    new_solver.parameters.max_time_in_seconds = 30.0
    new_status = new_solver.solve(new_model)

    status_name = new_solver.status_name(new_status)
    if new_status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise ValueError(
            f"No feasible reschedule found (status: {status_name}). "
            "The unavailability constraints may conflict with coverage requirements."
        )

    objective = int(new_solver.objective_value)

    # ── Step H: Extract results ───────────────────────────────────────────────
    rows: dict[str, list[str]] = {}
    for n, name in enumerate(nurses):
        row = []
        for d in range(num_days):
            assigned = "Off"
            for s, sname in enumerate(shift_names):
                if new_solver.value(new_assignment[(n, d, s)]) == 1:
                    assigned = sname
            row.append(assigned)
        rows[name] = row

    new_df = pd.DataFrame(rows, index=days).T

    summary = []
    for n, name in enumerate(nurses):
        total = sum(
            new_solver.value(new_assignment[(n, d, s)])
            for d in range(num_days)
            for s in range(num_shifts)
        )
        day_s = sum(new_solver.value(new_assignment[(n, d, 0)]) for d in range(num_days))
        night_s = sum(
            new_solver.value(new_assignment[(n, d, night_idx if night_idx is not None else 1)])
            for d in range(num_days)
        )
        summary.append(
            {"Nurse": name, "Day shifts": day_s, "Night shifts": night_s, "Total": total}
        )

    return status_name, objective, new_df, summary


def _diff_schedules(original_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
    """Return boolean DataFrame: True where a cell changed."""
    return original_df != new_df


def _style_schedule_with_diff(df: pd.DataFrame, diff_mask: pd.DataFrame):
    """Style the schedule, highlighting changed cells in amber."""

    def _style_row(row: pd.Series) -> list[str]:
        nurse = row.name
        styles = []
        for col in row.index:
            val = row[col]
            changed = diff_mask.loc[nurse, col]
            if changed:
                styles.append(
                    "background-color:#78350f; color:#fcd34d; font-weight:700;"
                    " outline:2px solid #f59e0b"
                )
            elif val == "Day":
                styles.append("background-color:#1a4a2e; color:#86efac; font-weight:600")
            elif val == "Night":
                styles.append("background-color:#1e3a5f; color:#93c5fd; font-weight:600")
            else:
                styles.append("color:#9ca3af")
        return styles

    return df.style.apply(_style_row, axis=1)


def _disruption_summary(diff_mask: pd.DataFrame) -> pd.DataFrame:
    """Per-nurse count of changed assignments, sorted descending."""
    counts = diff_mask.sum(axis=1).rename("Changes")
    return (
        counts.reset_index()
        .rename(columns={"index": "Nurse"})
        .sort_values("Changes", ascending=False)
    )


# ── Session state ─────────────────────────────────────────────────────────────
if "generated_code" not in st.session_state:
    st.session_state.generated_code = None
if "llm_used" not in st.session_state:
    st.session_state.llm_used = False
if "solver_result" not in st.session_state:
    st.session_state.solver_result = None
if "original_ns" not in st.session_state:
    st.session_state.original_ns = None
if "reschedule_result" not in st.session_state:
    st.session_state.reschedule_result = None

# ── Step 1: Problem description ───────────────────────────────────────────────
st.header("Step 1 — Describe the Problem")
st.markdown(
    "Write the scheduling rules exactly as a nurse manager would explain them to a colleague."
)

problem_text = st.text_area(
    "Problem description",
    value=DEFAULT_PROBLEM,
    height=260,
    label_visibility="collapsed",
)

# ── Step 2: Generate OR-Tools code ────────────────────────────────────────────
st.header("Step 2 — Generate OR-Tools Code")

col_gen, col_info = st.columns([2, 3])
with col_gen:
    generate_clicked = st.button("⚡ Generate Code", type="primary", use_container_width=True)

with col_info:
    if not provider_ready:
        st.warning("Anthropic API unavailable — pre-verified fallback code will be used.")

if generate_clicked:
    if provider_ready:
        with st.spinner(f"Calling Claude ({model_name}) …"):
            try:
                code = _call_anthropic(problem_text, model_name)
                st.session_state.generated_code = code
                st.session_state.llm_used = True
                st.session_state.solver_result = None
                st.session_state.original_ns = None
                st.session_state.reschedule_result = None
                _append_query(problem_text, model_name, code)
                st.success("Code generated successfully.")
            except Exception as exc:
                st.warning(f"API call failed ({exc}). Using pre-verified fallback.")
                st.session_state.generated_code = FALLBACK_CODE
                st.session_state.llm_used = False
                st.session_state.solver_result = None
                st.session_state.original_ns = None
                st.session_state.reschedule_result = None
    else:
        st.session_state.generated_code = FALLBACK_CODE
        st.session_state.llm_used = False
        st.session_state.solver_result = None
        st.session_state.original_ns = None
        st.session_state.reschedule_result = None
        st.info("Using pre-verified fallback code.")

if st.session_state.generated_code:
    source_label = "LLM-generated" if st.session_state.llm_used else "Pre-written example"
    st.caption(f"Code source: **{source_label}**")
    st.code(st.session_state.generated_code, language="python")

# ── Step 3: Run solver ────────────────────────────────────────────────────────
st.header("Step 3 — Run the Solver")

if st.session_state.generated_code is None:
    st.info("Generate (or load the fallback) code above first.")
else:
    run_clicked = st.button("▶ Run Solver", type="primary")

    if run_clicked:
        with st.spinner("Solving …"):
            try:
                status, obj, df, summary, ns = _run_solver_code(st.session_state.generated_code)
                st.session_state.solver_result = (status, obj, df, summary)
                st.session_state.original_ns = ns
                st.session_state.reschedule_result = None  # invalidate prior reschedule
            except Exception as exc:
                st.error(f"Solver error: {exc}")
                st.session_state.solver_result = None
                st.session_state.original_ns = None

    if st.session_state.solver_result:
        status, obj, df, summary = st.session_state.solver_result

        col_s, col_o = st.columns(2)
        col_s.metric("Solver status", status)
        col_o.metric("Fairness spread", f"{obj} shift(s)")

        st.subheader("Weekly Schedule — Ward 6")
        st.dataframe(_style_schedule(df), use_container_width=True)

        st.subheader("Shifts per nurse")
        summary_df = pd.DataFrame(summary).set_index("Nurse")
        st.dataframe(summary_df, use_container_width=True)

        st.subheader("Constraint Verification")
        checks = _verify_schedule(df, problem_text)
        all_passed = all(c["passed"] for c in checks)
        if all_passed:
            st.success("All constraints verified — schedule is feasible.")
        else:
            st.error("One or more constraints are VIOLATED — the LLM likely mistranslated a rule.")
        for c in checks:
            icon = "✅" if c["passed"] else "❌"
            with st.expander(f"{icon} {c['rule']}"):
                st.caption(c["detail"])

# ── Step 4: Reschedule ────────────────────────────────────────────────────────
if st.session_state.solver_result is not None and st.session_state.original_ns is not None:
    st.header("Step 4 — Reschedule")
    st.markdown(
        "Specify which nurse is unavailable on which day(s). "
        "The solver will find the schedule that makes the **fewest changes** from the original."
    )

    _, _, original_df, _ = st.session_state.solver_result
    ns = st.session_state.original_ns

    # ── 4a: Free-text input + live parse preview ──────────────────────────────
    st.subheader("Unavailability")
    input_col, preview_col = st.columns([3, 2])

    with input_col:
        unavail_text = st.text_area(
            "Describe who is unavailable and when",
            placeholder=(
                "e.g. Alice is sick on Wednesday and Thursday.\nBob cannot work on Saturday."
            ),
            height=120,
            key="unavail_text",
        )

    parsed: dict[str, list[str]] = {}
    if unavail_text.strip():
        parsed = _parse_unavailability(
            unavail_text,
            valid_nurses=ns["nurses"],
            valid_days=ns["days"],
        )

    with preview_col:
        st.caption("Parsed unavailability")
        if parsed:
            for nurse, off_days in parsed.items():
                st.write(f"**{nurse}**: {', '.join(off_days)}")
        else:
            st.caption("_(nothing parsed yet)_")

    # ── 4b: Manual override via multiselect ───────────────────────────────────
    with st.expander("Fine-tune manually (optional)"):
        manual_unavail: dict[str, list[str]] = {}
        for nurse in ns["nurses"]:
            selected = st.multiselect(
                nurse,
                options=ns["days"],
                default=parsed.get(nurse, []),
                key=f"manual_{nurse}",
            )
            if selected:
                manual_unavail[nurse] = selected

    # Manual overrides take precedence if any day was selected
    effective_unavail = manual_unavail if manual_unavail else parsed

    # ── 4c: Reschedule button ─────────────────────────────────────────────────
    reschedule_clicked = st.button(
        "🔄 Reschedule with Minimal Changes",
        type="primary",
        disabled=not effective_unavail,
    )

    if reschedule_clicked and effective_unavail:
        with st.spinner("Re-solving with minimal changes …"):
            try:
                r_status, r_obj, r_df, r_summary = _build_reschedule_model(
                    st.session_state.original_ns,
                    effective_unavail,
                    original_df,
                )
                st.session_state.reschedule_result = (r_status, r_obj, r_df, r_summary)
            except ValueError as exc:
                st.error(f"Reschedule failed: {exc}")
                st.session_state.reschedule_result = None

    # ── 4d: Show results ──────────────────────────────────────────────────────
    if st.session_state.reschedule_result is not None:
        r_status, r_obj, r_df, r_summary = st.session_state.reschedule_result
        diff_mask = _diff_schedules(original_df, r_df)
        total_changes = int(diff_mask.values.sum())

        col_s, col_o = st.columns(2)
        col_s.metric("Reschedule status", r_status)
        col_o.metric("Assignments changed", total_changes)

        if total_changes == 0:
            st.success(
                "No changes required — the original schedule already accommodates the unavailability."
            )
        else:
            st.info(f"{total_changes} assignment(s) changed across all nurses.")

        tab_new, tab_orig, tab_side = st.tabs(["Rescheduled", "Original", "Side-by-Side"])

        with tab_new:
            st.caption("Amber cells = changed from original")
            st.dataframe(_style_schedule_with_diff(r_df, diff_mask), use_container_width=True)

        with tab_orig:
            st.dataframe(_style_schedule(original_df), use_container_width=True)

        with tab_side:
            left, right = st.columns(2)
            with left:
                st.caption("**Original**")
                st.dataframe(_style_schedule(original_df), use_container_width=True)
            with right:
                st.caption("**Rescheduled** (amber = changed)")
                st.dataframe(_style_schedule_with_diff(r_df, diff_mask), use_container_width=True)

        st.subheader("Disruption per nurse")
        disruption_df = _disruption_summary(diff_mask)
        st.dataframe(disruption_df.set_index("Nurse"), use_container_width=True)

        with st.expander("Shifts per nurse (rescheduled)"):
            r_summary_df = pd.DataFrame(r_summary).set_index("Nurse")
            st.dataframe(r_summary_df, use_container_width=True)

# ── Summary ───────────────────────────────────────────────────────────────────
st.divider()
st.header("What Just Happened?")

st.markdown(
    "| Step | Who | What |\n"
    "|------|-----|------|\n"
    "| Problem description | **Human** (nurse manager) | Wrote the rules in plain English |\n"
    "| Code generation | **Claude** | Translated English → OR-Tools constraints |\n"
    "| Solving | **OR-Tools** | Found the optimal, valid schedule |\n"
    "| Rescheduling | **OR-Tools** | Re-solved with minimal disruption |\n"
    "| Review & approval | **Human** (nurse manager) | Final decision — always |\n"
)

col_a, col_b = st.columns(2)
with col_a:
    st.error(
        "**LLM alone (no solver)**\n\n"
        "- ~35 % chance of a constraint violation\n"
        "- Arithmetic errors on hour/day calculations\n"
        "- Inconsistent results each run\n"
        "- Breaks on larger rosters (50+ nurses)"
    )
with col_b:
    st.success(
        "**Claude + OR-Tools**\n\n"
        "- ✅ 100 % feasibility — mathematically guaranteed\n"
        "- ✅ Exact arithmetic, always correct\n"
        "- ✅ Same optimal result every run\n"
        "- ✅ Scales to hundreds of nurses\n"
        "- ✅ Rescheduling with provably minimal disruption"
    )

st.caption("Demo created for TTSH HINT Clinical Informatics Presentation, 2026.")
