"""A self-contained HTML report you can open in any browser.

Written automatically by run.py next to the markdown report. You can also
build one from results files you already have:

    python -m harness.html_report results/20261127T212306Z_anthropic_claude-sonnet-5-5.json
    python -m harness.html_report results/*_anthropic_*.json --out compare.html

The page has no external dependencies, so it works offline and can be
attached to a CI run or emailed as a single file.
"""

import argparse
import json
from html import escape
from pathlib import Path

from .report import diff

STATUS_ORDER = {"FAIL": 0, "FLAKY": 1, "PASS": 2}

CSS = """
:root{--bg:#f7f7f5;--card:#fff;--ink:#1d1d1b;--muted:#6b6b66;--line:#e4e3de;
--pass:#1f7a3d;--pass-bg:#e3f3e7;--flaky:#8a5a00;--flaky-bg:#fbefd5;
--fail:#b3261e;--fail-bg:#fbe5e3;--skip:#6b6b66;--skip-bg:#eeede9;
--user:#eef2fb;--tool:#f3f2ee;--accent:#3a5bd9}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--card:#1e1e1c;--ink:#ecebe6;
--muted:#9b9a94;--line:#33322f;--pass:#7fd49a;--pass-bg:#1c3324;--flaky:#f0c36a;
--flaky-bg:#3a2e14;--fail:#f19b93;--fail-bg:#3d1f1c;--skip:#9b9a94;--skip-bg:#2a2a27;
--user:#1f2638;--tool:#262623;--accent:#8ea6ff}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
main{max-width:1100px;margin:0 auto;padding:32px 16px 80px}
h1{font-size:28px;margin:0 0 4px}h2{font-size:19px;margin:36px 0 12px}
.sub{color:var(--muted);margin:0 0 24px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px}
.card h3{margin:0 0 10px;font-size:15px;word-break:break-all}
.counts{display:flex;gap:16px;margin-bottom:8px}
.counts div{font-size:13px;color:var(--muted)}
.counts b{display:block;font-size:26px;line-height:1.1}
.c-pass b{color:var(--pass)}.c-flaky b{color:var(--flaky)}.c-fail b{color:var(--fail)}
.meta{font-size:13px;color:var(--muted)}
.pill{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;
font-weight:600;white-space:nowrap}
.PASS{color:var(--pass);background:var(--pass-bg)}
.FLAKY{color:var(--flaky);background:var(--flaky-bg)}
.FAIL{color:var(--fail);background:var(--fail-bg)}
.SKIP{color:var(--skip);background:var(--skip-bg)}
table{width:100%;border-collapse:collapse;background:var(--card);
border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{text-align:left;padding:8px 12px;border-bottom:1px solid var(--line);font-size:14px}
th{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
tr:last-child td{border-bottom:none}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.scroll{overflow-x:auto;border-radius:10px}
.changes{list-style:none;padding:0;margin:0}
.changes li{padding:6px 0}
.toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 12px}
.toolbar button{border:1px solid var(--line);background:var(--card);color:var(--ink);
padding:5px 12px;border-radius:999px;font:inherit;font-size:13px;cursor:pointer}
.toolbar button.on{border-color:var(--accent);color:var(--accent);font-weight:600}
.toolbar input{flex:1;min-width:160px;border:1px solid var(--line);background:var(--card);
color:var(--ink);padding:6px 12px;border-radius:8px;font:inherit;font-size:14px}
details.task{background:var(--card);border:1px solid var(--line);border-radius:10px;
margin-bottom:10px}
details.task>summary{padding:12px 16px;cursor:pointer;display:flex;gap:10px;
align-items:center;flex-wrap:wrap}
details.task>summary .id{font-weight:600;font-family:ui-monospace,Menlo,Consolas,monospace}
details.task>summary .station{color:var(--muted);font-size:13px}
.tbody{padding:0 16px 16px}
.input{background:var(--user);border-radius:8px;padding:10px 12px;white-space:pre-wrap;
font-size:14px;margin:0 0 12px}
.model{margin:14px 0 6px;font-weight:600;font-size:14px}
details.attempt{border:1px solid var(--line);border-radius:8px;margin:6px 0}
details.attempt>summary{padding:8px 12px;cursor:pointer;font-size:14px;display:flex;
gap:10px;align-items:center;flex-wrap:wrap}
.abody{padding:4px 12px 12px}
.checks{list-style:none;padding:0;margin:0 0 12px}
.checks li{font-size:13px;padding:3px 0;display:flex;gap:8px;align-items:baseline}
.checks code{font-size:12px}
.checks .d{color:var(--muted);word-break:break-word}
.msg{border-radius:8px;padding:8px 12px;margin:6px 0;font-size:14px}
.msg .who{font-size:11px;text-transform:uppercase;letter-spacing:.05em;
color:var(--muted);margin-bottom:2px}
.msg .t{white-space:pre-wrap;word-break:break-word}
.m-user{background:var(--user)}.m-assistant{border:1px solid var(--line)}
.m-tool{background:var(--tool)}
.call{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;
background:var(--tool);border-radius:6px;padding:4px 8px;margin-top:6px;
white-space:pre-wrap;word-break:break-all}
.m-tool pre{margin:0;font-size:12px;white-space:pre-wrap;word-break:break-all;
max-height:260px;overflow:auto}
.err{color:var(--fail);font-size:13px;margin:0 0 8px}
.empty{color:var(--muted);font-style:italic}
"""

JS = """
const tasks=[...document.querySelectorAll('details.task')];
let filter='all';
function apply(){
  const q=document.getElementById('q').value.toLowerCase();
  tasks.forEach(t=>{
    const okS=filter==='all'||t.dataset.status.split(' ').includes(filter);
    const okQ=!q||t.dataset.search.includes(q);
    t.style.display=okS&&okQ?'':'none';
  });
}
document.querySelectorAll('.toolbar button').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('.toolbar button').forEach(x=>x.classList.remove('on'));
  b.classList.add('on');filter=b.dataset.f;apply();
});
document.getElementById('q').oninput=apply;
"""


def _pill(status):
    return f'<span class="pill {status}">{status}</span>'


def _check_icon(passed):
    if passed is True:
        return '<span class="pill PASS">✓</span>'
    if passed is False:
        return '<span class="pill FAIL">✗</span>'
    return '<span class="pill SKIP">–</span>'


def _transcript(messages):
    out = []
    for m in messages:
        role = m["role"]
        if role == "user":
            out.append(f'<div class="msg m-user"><div class="who">User</div>'
                       f'<div class="t">{escape(m["content"])}</div></div>')
        elif role == "assistant":
            body = (f'<div class="t">{escape(m["text"])}</div>' if m.get("text")
                    else "")
            for tc in m.get("tool_calls", []):
                args = json.dumps(tc.get("args", {}), ensure_ascii=False)
                body += f'<div class="call">→ {escape(tc["name"])}({escape(args)})</div>'
            out.append(f'<div class="msg m-assistant"><div class="who">Agent</div>'
                       f'{body or "<div class=empty>(empty reply)</div>"}</div>')
        elif role == "tool":
            content = m["content"]
            try:  # pretty-print JSON tool results
                content = json.dumps(json.loads(content), indent=2, ensure_ascii=False)
            except (json.JSONDecodeError, TypeError):
                pass
            out.append(f'<div class="msg m-tool"><div class="who">Tool result · '
                       f'{escape(m.get("name", ""))}</div><pre>{escape(content)}</pre></div>')
    return "".join(out)


def _attempt(i, a):
    passed = a["grade"]["passed"]
    status = "PASS" if passed else "FAIL"
    tokens = a["usage"]["input"] + a["usage"]["output"]
    checks = "".join(
        f'<li>{_check_icon(c["passed"])}<code>{escape(c["type"])}</code>'
        f'<span class="d">{escape(str(c["detail"]))}</span></li>'
        for c in a["grade"]["checks"])
    err = f'<p class="err">Run error: {escape(a["error"])}</p>' if a.get("error") else ""
    return (f'<details class="attempt"{"" if passed else " open"}><summary>'
            f'{_pill(status)}<span>Run {i}</span>'
            f'<span class="meta">{a["latency_s"]}s · {tokens:,} tokens · '
            f'{len(a["tool_calls"])} tool calls</span></summary>'
            f'<div class="abody">{err}<ul class="checks">{checks}</ul>'
            f'{_transcript(a["transcript"])}</div></details>')


def render(runs, diffs=None, title="Obstacle course report"):
    """runs: list of results-file dicts ({"model","timestamp","runs","summary","results"})."""
    diffs = diffs or {}
    stamps = sorted({r["timestamp"] for r in runs})
    models = [r["model"] for r in runs]

    # Model cards
    cards = []
    for r in runs:
        s = r["summary"]
        counts = {k: sum(1 for t in s.values() if t["status"] == k) for k in STATUS_ORDER}
        tokens = sum(t["tokens"] for t in s.values())
        lat = [t["avg_latency_s"] for t in s.values()]
        avg = round(sum(lat) / len(lat), 1) if lat else 0
        cards.append(
            f'<div class="card"><h3>{escape(r["model"])}</h3><div class="counts">'
            f'<div class="c-pass"><b>{counts["PASS"]}</b>pass</div>'
            f'<div class="c-flaky"><b>{counts["FLAKY"]}</b>flaky</div>'
            f'<div class="c-fail"><b>{counts["FAIL"]}</b>fail</div></div>'
            f'<div class="meta">{len(s)} tasks × {r["runs"]} runs · {tokens:,} tokens · '
            f'avg {avg}s per attempt</div></div>')

    # Changes since last run
    changes = []
    for model, (worse, better) in diffs.items():
        for task_id, a, b in worse:
            changes.append(f'<li>⚠️ <b>{escape(model)}</b> · <a href="#t-{escape(task_id)}">'
                           f'{escape(task_id)}</a>: {_pill(a)} → {_pill(b)}</li>')
        for task_id, a, b in better:
            changes.append(f'<li>✅ {escape(model)} · <a href="#t-{escape(task_id)}">'
                           f'{escape(task_id)}</a>: {_pill(a)} → {_pill(b)}</li>')
    changes_html = (f'<ul class="changes">{"".join(changes)}</ul>' if changes
                    else '<p class="meta">No changes, or no earlier run to compare against.</p>')

    # Task grid, worst first
    task_ids = sorted({t for r in runs for t in r["summary"]})

    def worst(tid):
        return min(STATUS_ORDER[r["summary"][tid]["status"]]
                   for r in runs if tid in r["summary"])

    task_ids.sort(key=lambda t: (worst(t), t))
    rows = []
    for tid in task_ids:
        station = next(r["summary"][tid]["station"] for r in runs if tid in r["summary"])
        cells = "".join(
            f'<td>{_pill(r["summary"][tid]["status"])} '
            f'<span class="meta">{r["summary"][tid]["passes"]}/{r["summary"][tid]["runs"]}</span></td>'
            if tid in r["summary"] else "<td>–</td>" for r in runs)
        rows.append(f'<tr><td><a href="#t-{escape(tid)}">{escape(tid)}</a></td>'
                    f'<td class="meta">{escape(station)}</td>{cells}</tr>')
    head = "".join(f"<th>{escape(m)}</th>" for m in models)
    grid = (f'<div class="scroll"><table><thead><tr><th>Task</th><th>Station</th>{head}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')

    # Task details
    details = []
    for tid in task_ids:
        statuses, station, first_input, body = [], "", "", []
        for r in runs:
            if tid not in r["summary"]:
                continue
            s = r["summary"][tid]
            statuses.append(s["status"])
            station = s["station"]
            attempts = r["results"][tid]["attempts"]
            if not first_input and attempts and attempts[0]["transcript"]:
                first_input = attempts[0]["transcript"][0].get("content", "")
            body.append(f'<div class="model">{escape(r["model"])} {_pill(s["status"])} '
                        f'<span class="meta">{s["passes"]}/{s["runs"]} passed</span></div>')
            body += [_attempt(i, a) for i, a in enumerate(attempts, 1)]
        overall = min(statuses, key=STATUS_ORDER.get)
        search = escape(f"{tid} {station}".lower())
        details.append(
            f'<details class="task" id="t-{escape(tid)}" data-status="{" ".join(set(statuses))}" '
            f'data-search="{search}"{"" if overall == "PASS" else " open"}><summary>'
            f'{_pill(overall)}<span class="id">{escape(tid)}</span>'
            f'<span class="station">{escape(station)}</span></summary><div class="tbody">'
            f'<div class="meta" style="margin-bottom:4px">Task input</div>'
            f'<div class="input">{escape(first_input)}</div>{"".join(body)}</div></details>')

    def fmt(st):  # 20261127T212306Z -> 2026-11-27 21:23 UTC
        return f"{st[0:4]}-{st[4:6]}-{st[6:8]} {st[9:11]}:{st[11:13]} UTC" if len(st) >= 13 else st

    when = " – ".join(dict.fromkeys([fmt(stamps[0]), fmt(stamps[-1])])) if stamps else ""
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title><style>{CSS}</style></head>
<body><main>
<h1>{escape(title)}</h1>
<p class="sub">Run {escape(when)} · {len(task_ids)} tasks · {len(runs)} model{'s' if len(runs) != 1 else ''}.
A task passes only if every attempt passes; some passes means flaky.</p>
<div class="cards">{"".join(cards)}</div>
<h2>Changes since last run</h2>{changes_html}
<h2>By task</h2>{grid}
<h2>Attempts and transcripts</h2>
<div class="toolbar">
<button class="on" data-f="all">All</button><button data-f="FAIL">Fail</button>
<button data-f="FLAKY">Flaky</button><button data-f="PASS">Pass</button>
<input id="q" type="search" placeholder="Filter by task or station">
</div>
{"".join(details)}
</main><script>{JS}</script></body></html>
"""


def write_html(path, runs, diffs=None):
    Path(path).write_text(render(runs, diffs), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="Build an HTML report from results JSON files.")
    p.add_argument("files", nargs="+", help="results/<time>_<model>.json files")
    p.add_argument("--out", help="output file (default: next to the first input)")
    args = p.parse_args()

    runs, diffs = [], {}
    for f in args.files:
        path = Path(f)
        run = json.loads(path.read_text(encoding="utf-8"))
        runs.append(run)
        # Compare against the run of the same model just before this one.
        safe = run["model"].replace(":", "_").replace("/", "_")
        earlier = [x for x in sorted(path.parent.glob(f"*_{safe}.json")) if x.name < path.name]
        if earlier:
            prev = json.loads(earlier[-1].read_text(encoding="utf-8"))
            diffs[run["model"]] = diff(run["summary"], prev["summary"])

    out = Path(args.out) if args.out else Path(args.files[0]).with_suffix(".html")
    write_html(out, runs, diffs)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
