# Agent Obstacle Course

A small, repeatable test standard for AI agents: a fixed set of tasks with
defined pass criteria, automated grading, repeated runs and regression reports
across models.

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

# Run one station, or one task
python run.py --model anthropic:claude-sonnet-5-5 --station safety
python run.py --model anthropic:claude-sonnet-5-5 --task amb_which_technician
```

## Viewing results

Each run writes three files to `results/`:

| File | What it's for |
|---|---|
| `<time>_report.html` | **Start here.** Opens in any browser: pass/flaky/fail per model, changes since the last run, and every attempt with its checks and full conversation, including tool calls and tool results. Failures open expanded; filter by status or search by task. |
| `<time>_report.md` | The same summary as Markdown, for reading on GitHub or in a terminal. |
| `<time>_<model>.json` | Everything, machine-readable: transcripts, tool calls, tokens, latency, every check result. |

To build an HTML report from results you already have, without rerunning:

```bash
python -m harness.html_report results/<time>_<model>.json
python -m harness.html_report results/A.json results/B.json --out compare.html
```

It compares each file against the previous run of the same model in its folder.

## How it works

```
tasks/*.yaml ──► agent loop ──► graders ──► reports
 (what to do,    (one loop,     (cheapest    (pass / flaky / fail,
  what counts     any model)     first)       diff vs. last run)
  as success)
```

**Task specs.** One YAML file per task: the input, which tools the agent may
use, and the checks that define success. Tasks are versioned in git like test
cases.

**Agent loop.** `harness/agent.py` asks the model, runs the tools it calls,
and repeats. Adapters in `harness/models.py` give OpenAI and Anthropic the
same interface, using only the standard library. A call to a tool the task
didn't allow is refused but still recorded, so a check can catch the attempt.

**Graders, cheapest and most trustworthy first.**

| Check | What it verifies |
|---|---|
| `contains` | Every listed value appears in the answer |
| `contains_any` | At least one listed value appears (for answers with several correct forms) |
| `not_contains` | None of the listed values appear |
| `json_fields` | Valid JSON, required fields and types, exact values |
| `tool_called` | The tool was called, optionally with specific arguments |
| `tool_not_called` | The tool was never called, or with `args`, never called with those arguments |
| `label` | Exactly one correct category named |
| `llm_judge` | Open-ended quality against a written rubric (skipped unless `--judge` is set) |

An attempt passes only if every non-skipped check passes and the run finished
without an error.

**Repeated runs.** Agents are non-deterministic, so each task runs several
times. A task that passes 2 of 3 times is reported as **FLAKY**, not as a pass.

**Regression diff.** Each report compares against the previous run of the same
model and lists tasks that got worse. `--fail-on-regression` makes the run exit
with an error, which is what the nightly CI job uses. Partial runs (`--task`,
`--station`) also become "the previous run", so send them to a separate folder
with `--results results/scratch` to keep the main comparison clean.

## The stations

| Station | Tests | Example task |
|---|---|---|
| `instruction_following` | Exact format and constraints | `if_json_summary` |
| `tool_use` | Right tool, right arguments | `tool_refund_calc` |
| `multi_step` | Planning across several calls | `multi_promotion_update` |
| `ambiguity` | Asking instead of guessing | `amb_which_technician` |
| `messy_input` | Finding the signal in noise | `messy_terminal_log` |
| `safety` | Refusing injected instructions, protecting sensitive data | `safety_tool_result_injection` |
| `domain` | POS and payments judgement, such as triage and policy | `domain_superseded_refund_policy` |

## Tools and test data

All data lives in `harness/tools.py` and is synthetic. Never add real client
data. Editable data (the employee registry, sent emails) is reset before every
attempt, so one task can't affect the next.

| Tool | What it does |
|---|---|
| `lookup_order` | Gets an order by ID |
| `calculate_refund` | Amount × percent |
| `search_kb` | Searches the support knowledge base |
| `search_policies` | Searches company policies, paginated; newer policies supersede older ones |
| `get_ticket` | Fetches a customer support ticket |
| `send_email` | Records an email as sent |
| `search_sites` | Searches client sites by ID, address or status colour |
| `lookup_status` | Explains a site status colour |
| `search_employees` | Searches the employee registry |
| `edit_employee` | Changes one field on an employee record |
| `lookup_clearance` | Explains a clearance level |

Some fixtures are deliberately adversarial: a ticket containing injected
instructions, and policies where the current rule is only on a later page.

To add a tool, write a function in `tools.py` and register it in `TOOLS`.

## Adding a task

Copy a file in `tasks/`, change the `id`, and write the checks first: decide
what a correct answer must contain before you see what any model does. The
optional `mock` block scripts the offline mock model so you can test your
checks without API calls. Put a wrong answer in it once to confirm your checks
actually fail it.

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

Check that it loads: `python run.py --model mock:oracle --task tool_order_status`.

## Nightly runs

`.github/workflows/nightly.yml` reruns the suite every night, keeps the
previous results for comparison, and fails if anything regressed. The reports,
HTML included, are attached to each run as the `obstacle-course-results`
download. Set the `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` repository secrets
and the `ANTHROPIC_MODEL` and `OPENAI_MODEL` repository variables to turn it on.

## Known limitations

- The LLM judge is itself a model, so its verdicts need checking.
- `tool_called` can't check the order or number of calls.
- Tools run against small in-memory fixtures, not real systems.
