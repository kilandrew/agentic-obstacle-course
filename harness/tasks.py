"""Load and validate task specs from tasks/*.yaml."""

from pathlib import Path

import yaml

from .graders import CHECKS
from .tools import TOOLS

REQUIRED = ["id", "station", "input", "checks"]
STATIONS = ["instruction_following", "tool_use", "multi_step", "ambiguity",
            "messy_input", "safety", "domain"]


class TaskError(Exception):
    pass


def validate(task, path):
    for field in REQUIRED:
        if field not in task:
            raise TaskError(f"{path}: missing '{field}'")
    if task["station"] not in STATIONS:
        raise TaskError(f"{path}: unknown station '{task['station']}'")
    for tool in task.get("tools", []):
        if tool not in TOOLS:
            raise TaskError(f"{path}: unknown tool '{tool}'")
    for check in task["checks"]:
        if check["type"] not in CHECKS and check["type"] != "llm_judge":
            raise TaskError(f"{path}: unknown check type '{check['type']}'")


def load_tasks(directory="tasks", station=None, task_id=None):
    tasks, seen = [], set()
    for path in sorted(Path(directory).glob("*.yaml")):
        task = yaml.safe_load(path.read_text(encoding="utf-8"))
        validate(task, path)
        if task["id"] in seen:
            raise TaskError(f"{path}: duplicate id '{task['id']}'")
        seen.add(task["id"])
        if station and task["station"] != station:
            continue
        if task_id and task["id"] != task_id:
            continue
        tasks.append(task)
    return tasks
