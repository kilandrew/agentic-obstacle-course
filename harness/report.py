"""Summaries, regression diffs and the markdown report."""

import json
from pathlib import Path


def status(passes, runs):
    if passes == runs:
        return "PASS"
    if passes == 0:
        return "FAIL"
    return "FLAKY"


def summarize(task_results):
    """task_results: {task_id: {"station", "attempts": [{"passed", ...}]}}"""
    summary = {}
    for task_id, tr in task_results.items():
        attempts = tr["attempts"]
        passes = sum(a["grade"]["passed"] for a in attempts)
        summary[task_id] = {
            "station": tr["station"],
            "passes": passes,
            "runs": len(attempts),
            "status": status(passes, len(attempts)),
            "avg_latency_s": round(sum(a["latency_s"] for a in attempts) / len(attempts), 2),
            "tokens": sum(a["usage"]["input"] + a["usage"]["output"] for a in attempts),
        }
    return summary


def latest_previous(results_dir, model_name, exclude):
    """The most recent earlier results file for the same model, if any."""
    safe = model_name.replace(":", "_").replace("/", "_")
    files = sorted(Path(results_dir).glob(f"*_{safe}.json"))
    files = [f for f in files if f.resolve() != Path(exclude).resolve()]
    return files[-1] if files else None


def diff(current, previous):
    """Tasks whose status got worse or better since the previous run."""
    rank = {"FAIL": 0, "FLAKY": 1, "PASS": 2}
    worse, better = [], []
    for task_id, now in current.items():
        before = previous.get(task_id)
        if not before:
            continue
        if rank[now["status"]] < rank[before["status"]]:
            worse.append((task_id, before["status"], now["status"]))
        elif rank[now["status"]] > rank[before["status"]]:
            better.append((task_id, before["status"], now["status"]))
    return worse, better


def markdown(runs_by_model, task_results_by_model, diffs):
    lines = ["# Obstacle course report", ""]

    # Headline table: one row per model.
    lines += ["| Model | Pass | Flaky | Fail | Tokens |", "|---|---|---|---|---|"]
    for model, summary in runs_by_model.items():
        counts = {s: sum(1 for t in summary.values() if t["status"] == s)
                  for s in ("PASS", "FLAKY", "FAIL")}
        tokens = sum(t["tokens"] for t in summary.values())
        lines.append(f"| {model} | {counts['PASS']} | {counts['FLAKY']} | "
                     f"{counts['FAIL']} | {tokens:,} |")
    lines.append("")

    # Per-task grid: tasks down the side, models across.
    models = list(runs_by_model)
    task_ids = sorted({t for s in runs_by_model.values() for t in s})
    lines += ["## By task", "",
              "| Task | Station | " + " | ".join(models) + " |",
              "|---|---|" + "---|" * len(models)]
    for task_id in task_ids:
        cells = []
        station = ""
        for m in models:
            t = runs_by_model[m].get(task_id)
            if t:
                station = t["station"]
                cells.append(f"{t['status']} ({t['passes']}/{t['runs']})")
            else:
                cells.append("–")
        lines.append(f"| {task_id} | {station} | " + " | ".join(cells) + " |")
    lines.append("")

    # Regressions vs. the previous run of each model.
    lines += ["## Changes since last run", ""]
    any_change = False
    for model, (worse, better) in diffs.items():
        for task_id, a, b in worse:
            lines.append(f"- ⚠️ **{model}** · {task_id}: {a} → {b}")
            any_change = True
        for task_id, a, b in better:
            lines.append(f"- ✅ {model} · {task_id}: {a} → {b}")
            any_change = True
    if not any_change:
        lines.append("No changes (or no earlier run to compare against).")
    lines.append("")

    # Why things failed: the first failing check of each non-passing task.
    lines += ["## Failure details", ""]
    for model, task_results in task_results_by_model.items():
        for task_id, tr in task_results.items():
            for i, attempt in enumerate(tr["attempts"], 1):
                if attempt["grade"]["passed"]:
                    continue
                failed = [c for c in attempt["grade"]["checks"] if c["passed"] is False]
                if failed:
                    lines.append(f"- {model} · {task_id} · run {i}: "
                                 f"`{failed[0]['type']}` — {failed[0]['detail']}")
    return "\n".join(lines) + "\n"


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2))
