# Agent Obstacle Course

A small, repeatable test standard for AI agents: a fixed set of tasks with
defined pass criteria, automated grading, repeated runs and regression reports
across models.

Most agent "benchmarks" on a team are a list of tasks someone eyeballs after a
change. This turns that into something closer to a hardware verification
suite: every task has an expected outcome, every run is graded the same way,
and a nightly job flags anything that got worse.

## Quick start

```bash
pip install -r requirements.txt

# Offline smoke test (no API key, no cost): checks the harness itself
python run.py --model mock:oracle

# Real run: one model, 3 attempts per task
export ANTHROPIC_API_KEY=...
python run.py --model anthropic:claude-sonnet-5-5 --runs 3

# Compare two providers, with an LLM judge for open-ended checks
export OPENAI_API_KEY=...
python run.py --model anthropic:claude-sonnet-5-5 --model openai:<model-name> \
              --judge anthropic:claude-sonnet-5-5
```

Each run writes `results/<time>_<model>.json` (full transcripts, tool calls,
tokens, latency) and `results/<time>_report.md`.

## How it works

```
tasks/*.yaml ──► agent loop ──► graders ──► report
 (what to do,    (one loop,     (cheapest    (pass / flaky / fail,
  what counts     any model)     first)       diff vs. last run)
  as success)
```

**Task specs.** One YAML file per task: the input, which tools the agent may
use, and the checks that define success. Tasks are versioned in git like test
cases.

**Agent loop.** `harness/agent.py` asks the model, runs the tools it calls,
and repeats. Adapters in `harness/models.py` give OpenAI and Anthropic the
same interface, using only the standard library.

**Graders, cheapest and most trustworthy first.**

| Check | What it verifies |
|---|---|
| `contains` / `not_contains` | Required or forbidden text in the answer |
| `json_fields` | Valid JSON, required fields and types, exact values |
| `tool_called` / `tool_not_called` | The right tool with the right arguments, or a tool that must not be used |
| `label` | Exactly one correct category named |
| `llm_judge` | Open-ended quality against a written rubric (skipped unless `--judge` is set) |

**Repeated runs.** Agents are non-deterministic, so each task runs several
times. A task that passes 2 of 3 times is reported as **FLAKY**, not as a pass.

**Regression diff.** Each report compares against the previous run of the same
model and lists tasks that got worse. `--fail-on-regression` makes the run exit
with an error, which is what the nightly CI job uses.

## The stations

| Station | Tests | Sample task |
|---|---|---|
| `instruction_following` | Exact format and constraints | `if_json_summary` |
| `tool_use` | Right tool, right arguments | `tool_refund_calc` |
| `multi_step` | Planning across several calls | `multi_combined_total` |
| `ambiguity` | Asking instead of guessing | `amb_missing_order` |
| `messy_input` | Finding the signal in noise | `messy_terminal_log` |
| `safety` | Ignoring instructions injected into data | `safety_injected_ticket` |
| `domain` | Triage of POS and payments issues | `domain_triage_host_unavailable` |

All data is synthetic. Never add real client data.

## Adding a task

Copy a file in `tasks/`, change the `id`, and write the checks first: decide
what a correct answer must contain before you see what any model does. The
optional `mock` block scripts the offline mock model so you can test your
checks without API calls.

```yaml
id: tool_order_status
station: tool_use
difficulty: easy
input: Is order A-1003 still active?
tools: [lookup_order]
checks:
  - type: tool_called
    name: lookup_order
    args: {order_id: "A-1003"}
  - type: contains
    values: ["cancelled"]
```

## Nightly runs

`.github/workflows/nightly.yml` reruns the suite every night, keeps the
previous results for comparison, and fails if anything regressed. Set the
`ANTHROPIC_API_KEY` and `OPENAI_API_KEY` repository secrets and the
`ANTHROPIC_MODEL` and `OPENAI_MODEL` repository variables to turn it on.

## Known limitations

- The LLM judge is itself a model, so its verdicts need checking. Hand-label a
  sample of runs and measure how often you and the judge agree before trusting it.
- Seven tasks is a starting set; the target is about 30, spread across stations.
- Tools run against small in-memory fixtures, not real systems.
