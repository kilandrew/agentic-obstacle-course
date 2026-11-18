"""Run the obstacle course.

Examples:
    python run.py --model mock:oracle                      # offline smoke test
    python run.py --model anthropic:claude-sonnet-5-5 --runs 3
    python run.py --model anthropic:claude-sonnet-5-5 --model openai:<model> \
                  --judge anthropic:claude-sonnet-5-5
    python run.py --model openai:<model> --station safety   # one station only
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from harness.agent import run_agent
from harness.graders import grade
from harness.models import ModelError, load_model
from harness.report import diff, latest_previous, markdown, save_json, summarize
from harness.tasks import TaskError, load_tasks


def main():
    p = argparse.ArgumentParser(description="Run agents through the obstacle course.")
    p.add_argument("--model", action="append", required=True,
                   help="provider:model, e.g. anthropic:claude-sonnet-5-5 (repeatable)")
    p.add_argument("--runs", type=int, default=3,
                   help="attempts per task; agents are non-deterministic (default 3)")
    p.add_argument("--judge", help="model for llm_judge checks (skipped if omitted)")
    p.add_argument("--station", help="only run tasks from this station")
    p.add_argument("--task", help="only run this task id")
    p.add_argument("--results", default="results", help="output directory")
    p.add_argument("--fail-on-regression", action="store_true",
                   help="exit 1 if any task got worse since the last run (for CI)")
    args = p.parse_args()

    try:
        tasks = load_tasks(station=args.station, task_id=args.task)
        models = [load_model(m) for m in args.model]
        judge = load_model(args.judge) if args.judge else None
    except (TaskError, ModelError) as e:
        sys.exit(f"Error: {e}")
    if not tasks:
        sys.exit("No tasks matched.")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    summaries, all_results, diffs = {}, {}, {}

    for model in models:
        print(f"\n== {model.name}: {len(tasks)} tasks × {args.runs} runs")
        task_results = {}
        for task in tasks:
            attempts = []
            for _ in range(args.runs):
                result = run_agent(model, task)
                result["grade"] = grade(task, result, judge)
                attempts.append(result)
            task_results[task["id"]] = {"station": task["station"], "attempts": attempts}
            passes = sum(a["grade"]["passed"] for a in attempts)
            print(f"  {task['id']:<32} {passes}/{args.runs}")

        summary = summarize(task_results)
        safe = model.name.replace(":", "_").replace("/", "_")
        out = Path(args.results) / f"{stamp}_{safe}.json"
        save_json(out, {"model": model.name, "timestamp": stamp, "runs": args.runs,
                        "summary": summary, "results": task_results})

        prev = latest_previous(args.results, model.name, exclude=out)
        if prev:
            diffs[model.name] = diff(summary, json.loads(prev.read_text())["summary"])
        else:
            diffs[model.name] = ([], [])
        summaries[model.name] = summary
        all_results[model.name] = task_results

    report_path = Path(args.results) / f"{stamp}_report.md"
    report_path.write_text(markdown(summaries, all_results, diffs))
    print(f"\nReport: {report_path}")

    if args.fail_on_regression and any(worse for worse, _ in diffs.values()):
        sys.exit("Regression detected: at least one task got worse since the last run.")


if __name__ == "__main__":
    main()
