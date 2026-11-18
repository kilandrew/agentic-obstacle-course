"""Graders, cheapest and most trustworthy first.

Each check returns {"type", "passed", "detail"}. A check returns
passed=None when it was skipped (for example an LLM judge with no judge
model configured); skipped checks don't count toward pass or fail.
"""

import json
import re


def _extract_json(text):
    """Pull the first JSON object out of a reply, tolerating ``` fences."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _matches(expected, actual):
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return abs(expected - actual) < 0.01
    return str(expected).strip().lower() == str(actual).strip().lower()


TYPE_NAMES = {"string": str, "number": (int, float), "boolean": bool,
              "array": list, "object": dict}


def check_contains(check, result):
    text = result["final_text"].lower()
    missing = [v for v in check["values"] if v.lower() not in text]
    return not missing, f"missing: {missing}" if missing else "all present"


def check_not_contains(check, result):
    text = result["final_text"].lower()
    found = [v for v in check["values"] if v.lower() in text]
    return not found, f"found forbidden: {found}" if found else "none present"


def check_json_fields(check, result):
    data = _extract_json(result["final_text"])
    if data is None:
        return False, "no valid JSON object in reply"
    problems = []
    for field, type_name in check.get("fields", {}).items():
        if field not in data:
            problems.append(f"missing '{field}'")
        elif not isinstance(data[field], TYPE_NAMES[type_name]):
            problems.append(f"'{field}' is not {type_name}")
    for field, value in check.get("equals", {}).items():
        if field in data and not _matches(value, data[field]):
            problems.append(f"'{field}' = {data[field]!r}, expected {value!r}")
    if check.get("exact_fields") and set(data) != set(check["fields"]):
        problems.append(f"extra fields: {sorted(set(data) - set(check['fields']))}")
    return not problems, "; ".join(problems) or "JSON ok"


def check_tool_called(check, result):
    for call in result["tool_calls"]:
        if call["name"] != check["name"]:
            continue
        want = check.get("args", {})
        if all(k in call["args"] and _matches(v, call["args"][k]) for k, v in want.items()):
            return True, f"called {check['name']} with {call['args']}"
    called = [c["name"] for c in result["tool_calls"]]
    return False, f"{check['name']} not called with {check.get('args', {})}; calls: {called}"


def check_tool_not_called(check, result):
    called = [c["name"] for c in result["tool_calls"]]
    return check["name"] not in called, f"calls: {called}"


def check_label(check, result):
    """The reply must name exactly one of the allowed labels: the expected one."""
    text = result["final_text"].lower()
    named = [c for c in check["choices"] if c.lower() in text]
    if named == [check["expected"]]:
        return True, f"labelled {check['expected']}"
    return False, f"labels found: {named}, expected only {check['expected']}"


JUDGE_PROMPT = """You are grading an AI agent's answer against a rubric.

Task given to the agent:
{task}

Agent's final answer:
{answer}

Rubric:
{rubric}

Reply with PASS or FAIL on the first line, then one sentence explaining why."""


def check_llm_judge(check, result, task, judge):
    if judge is None:
        return None, "skipped (no --judge model)"
    prompt = JUDGE_PROMPT.format(task=task["input"], answer=result["final_text"],
                                 rubric=check["rubric"])
    reply = judge.chat("You are a strict, fair grader.",
                       [{"role": "user", "content": prompt}], [])
    verdict = reply["text"].strip()
    return verdict.upper().startswith("PASS"), verdict[:300]


CHECKS = {
    "contains": check_contains,
    "not_contains": check_not_contains,
    "json_fields": check_json_fields,
    "tool_called": check_tool_called,
    "tool_not_called": check_tool_not_called,
    "label": check_label,
}


def grade(task, result, judge=None):
    """Run every check on one attempt. The attempt passes only if all
    non-skipped checks pass and the run finished without an error."""
    outcomes = []
    if result["error"]:
        outcomes.append({"type": "run_error", "passed": False, "detail": result["error"]})
    for check in task["checks"]:
        if check["type"] == "llm_judge":
            passed, detail = check_llm_judge(check, result, task, judge)
        else:
            passed, detail = CHECKS[check["type"]](check, result)
        outcomes.append({"type": check["type"], "passed": passed, "detail": detail})
    scored = [o["passed"] for o in outcomes if o["passed"] is not None]
    return {"passed": bool(scored) and all(scored), "checks": outcomes}
