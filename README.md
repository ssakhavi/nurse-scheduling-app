# LLMs in Healthcare Scheduling — TTSH HINT

Talk materials for the TTSH HINT session on the strategic integration of Large Language Models (LLMs) and Operations Research (OR) for optimized clinical scheduling.

**Audience:** Clinicians, nurse managers, and hospital administrators (non-technical)
**Format:** 40-minute presentation

---

## Overview

Healthcare scheduling — from nurse rostering to OR management — is an NP-hard combinatorial optimization problem. Traditional manual and spreadsheet-based approaches cannot scale with modern clinical complexity. This talk explores how LLMs and Operations Research can work together to reduce administrative burden, improve fairness, and restore clinical staff's focus on patient care.

The central argument: LLMs alone are insufficient for reliable scheduling (see [LIMITATIONS.md](LIMITATIONS.md)), but a **neuro-symbolic hybrid** — LLM as natural language interface + deterministic solver for optimization — offers a practical and deployable path forward.

---

## Contents

| File | Description |
|------|-------------|
| `presentation.html` | Self-contained HTML slide deck (open in any browser) |
| `presentation.key` | Keynote source file |
| `ttsh-hint-llm4scheduling.pdf` | Exported PDF of the slides |
| `LLM-SCHEDULING-HEALTHCARE.md` | Full research writeup: OR foundations, LLM capabilities, case studies, and a 40-minute presentation blueprint |
| `LIMITATIONS.md` | Deep-dive into current LLM limitations in scheduling and rostering (feasibility rates, tokenization barriers, scalability, etc.) |

---

## Talk Structure (40 minutes)

| Section | Time | Topic |
|---------|------|-------|
| 1 | 0–5 min | **The Hook** — The 3 AM sick call: the human cost of chaotic staffing |
| 2 | 5–15 min | **Operations Research** — Variables, constraints, and objectives explained without equations |
| 3 | 15–25 min | **LLMs as Translators** — ReAct, Chain-of-Thought, and neuro-symbolic architectures |
| 4 | 25–35 min | **Practical Tools** — Off-the-shelf and open-source options (Heidi AI, USolver, Taskade, Meditron) |
| 5 | 35–40 min | **Governance & Next Steps** — HIPAA compliance, bias management, and a mini-pilot roadmap |

---

## Key Concepts Covered

**Operations Research**
- Nurse Rostering Problem (NRP) — why it's NP-hard
- Mixed Integer Programming (MIP), Column Generation, Constraint Programming
- Hard vs. soft constraints; objective functions for cost, fairness, and safety

**LLM Capabilities & Architecture**
- Constraint extraction from natural language (zero-shot / few-shot prompting)
- ReAct (Reasoning + Acting) frameworks and agentic workflows
- Neuro-symbolic hybrid: LLM → structured model → OR solver (OR-Tools, Gurobi, Z3)

**LLM Limitations** *(covered honestly)*
- ~65% feasibility rate on scheduling benchmarks (ConstraintBench)
- Tokenization barriers to arithmetic and temporal reasoning
- "Lost-in-the-middle" degradation over long horizons
- Latency and cost trade-offs for real-time deployment

**Case Studies**
- Apollo Hospitals: AI-driven admin automation targeting 30% attrition reduction
- Urban ED (85k patients/year): 93% self-scheduled shifts, 85% reduction in scheduling workload
- Duke Health: 20% reduction in note-taking time, 30% less after-hours clerical work

---

## Viewing the Presentation

Open `presentation.html` directly in any modern browser — no server or dependencies required. Navigate with **arrow keys** or **click**.

---

## Setup (Python tooling)

Requires Python 3.9.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # if applicable
python main.py
```

---

## Further Reading

- `LLM-SCHEDULING-HEALTHCARE.md` — comprehensive background on OR + LLM integration for clinicians
- `LIMITATIONS.md` — systematic analysis of where current LLMs fall short in scheduling tasks, and the path toward reliability via neuro-symbolic hybrids
