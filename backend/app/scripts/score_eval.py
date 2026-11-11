"""Score the blind ratings for Task 1: rule-based vs AI on the professor's rubric.

Each rater fills in their own copy of docs/eval/rating-sheet.csv (one row per answer,
1 to 5 on four metrics, their name in the "rater" column). Put all the filled copies in
docs/eval/ratings/ (any file names ending in .csv). This unblinds them with
data/eval/rating-key.csv and writes docs/eval/scores.md.

Run from backend/:  python -m app.scripts.score_eval
"""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[3]
METRICS = [("correctness_1to5", "Correctness"), ("specificity_1to5", "Specificity"),
           ("tone_1to5", "Professional tone"), ("actionability_1to5", "Actionability")]
WHO = {"rules": "Rule-based", "ai": "AI"}


def label(avg: float) -> str:
    return "Very Good" if avg >= 4.5 else "Good" if avg >= 3.5 else "Acceptable" if avg >= 2.5 else "Poor"


def fmt(xs: list[float]) -> str:
    return f"{mean(xs):.2f}" if xs else "–"


def main() -> None:
    key = {r["scenario"]: r for r in csv.DictReader(open(ROOT / "data/eval/rating-key.csv", encoding="utf-8"))}
    raw = json.loads((ROOT / "data/eval/results.json").read_text(encoding="utf-8"))
    titles = {str(r["n"]): r["title"] for r in raw["results"]}

    folder = ROOT / "docs/eval/ratings"
    files = sorted(folder.glob("*.csv")) if folder.exists() else []
    if not files:
        raise SystemExit("No ratings yet. Each rater fills a copy of docs/eval/rating-sheet.csv and saves it in docs/eval/ratings/.")

    # scores[(scenario, who)][metric] -> list of ratings (one per rater)
    scores: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    raters, skipped = set(), 0
    for f in files:
        for row in csv.DictReader(open(f, encoding="utf-8-sig")):
            if not (row.get("rater") or "").strip():
                skipped += 1
                continue
            try:
                vals = {m: float(row[m]) for m, _ in METRICS}
            except (KeyError, ValueError):
                skipped += 1
                continue
            if any(not 1 <= v <= 5 for v in vals.values()):
                raise SystemExit(f"{f.name}: scores must be 1 to 5 (scenario {row['scenario']}, answer {row['answer']}).")
            who = key[row["scenario"]][row["answer"]]
            raters.add(row["rater"].strip())
            for m, v in vals.items():
                scores[(row["scenario"], who)][m].append(v)

    # 1) The professor's table: average per metric.
    lines = ["# Task 1: AI vs rule-based quality", "",
             f"Blind ratings from {len(raters)} rater(s) ({', '.join(sorted(raters))}) on 15 scenarios, prompt "
             f"{raw.get('prompt_version')}, model `{raw.get('model')}`. Scale 1 (poor) to 5 (excellent).", "",
             "## Average score per metric", "", "| Metric | Rule-based | AI | Difference |", "| --- | --- | --- | --- |"]
    overall = {"rules": [], "ai": []}
    for m, name in METRICS:
        r = [v for (s, w), d in scores.items() if w == "rules" for v in d[m]]
        a = [v for (s, w), d in scores.items() if w == "ai" for v in d[m]]
        overall["rules"] += r
        overall["ai"] += a
        diff = f"{mean(a) - mean(r):+.2f}" if r and a else "–"
        lines.append(f"| {name} | {fmt(r)} | {fmt(a)} | {diff} |")
    od = f"{mean(overall['ai']) - mean(overall['rules']):+.2f}" if overall["rules"] and overall["ai"] else "–"
    lines.append(f"| **Overall** | **{fmt(overall['rules'])}** | **{fmt(overall['ai'])}** | **{od}** |")

    # 2) Per scenario.
    lines += ["", "## Per scenario (average of all metrics and raters)", "",
              "| # | Scenario | Rule-based | AI | Better |", "| --- | --- | --- | --- | --- |"]
    wins = Counter()
    for n in sorted(titles, key=int):
        cell, avg = {}, {}
        for who in ("rules", "ai"):
            vals = [v for vs in scores.get((n, who), {}).values() for v in vs]
            if vals:
                avg[who] = mean(vals)
                cell[who] = f"{avg[who]:.2f} ({label(avg[who])})"
        better = "–"
        if len(avg) == 2:
            d = avg["ai"] - avg["rules"]
            better = "AI" if d >= 0.5 else "Rules" if d <= -0.5 else "Tie"
            wins[better] += 1
        lines.append(f"| {n} | {titles[n]} | {cell.get('rules', '–')} | {cell.get('ai', '–')} | {better} |")
    lines += ["", f"AI better in **{wins['AI']}**, rules better in **{wins['Rules']}**, tie in **{wins['Tie']}** "
              "(a difference of half a point or more counts as better)."]

    # 3) Automatic measures from the run itself.
    runs = [x for r in raw["results"] for x in r["ai"]]
    if runs:
        rejected = sum(x["answer"] is None for x in runs)
        consistent = sum(1 for r in raw["results"] if r["ai"] and
                         len({x["answer"]["action_type"] for x in r["ai"] if x["answer"]}) == 1)
        secs = [x["seconds"] for x in runs]
        lines += ["", "## Measured automatically", "", "| Measure | Result |", "| --- | --- |",
                  f"| AI answers rejected by the schema or grounding check | {rejected} of {len(runs)} |",
                  f"| Scenarios where all 3 AI runs chose the same kind of action | {consistent} of {len(raw['results'])} |",
                  f"| AI response time | average {mean(secs):.1f} s, slowest {max(secs):.1f} s |",
                  f"| Rule-based answers that failed the grounding check | "
                  f"{sum(not r['rules_grounded'] for r in raw['results'])} of {len(raw['results'])} |"]

    # 4) Where raters disagreed by more than a point.
    gaps = []
    for (n, who), d in scores.items():
        for m, name in METRICS:
            if len(d[m]) > 1 and max(d[m]) - min(d[m]) > 1:
                gaps.append(f"Scenario {n}, {WHO[who]}, {name}: {sorted(d[m])}")
    lines += ["", "## Ratings to discuss (raters more than 1 point apart)", ""]
    lines += [f"- {g}" for g in sorted(gaps)] or ["None."]
    if skipped:
        lines += ["", f"_{skipped} row(s) skipped because the rater name or a score was missing._"]

    (ROOT / "docs/eval/scores.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote docs/eval/scores.md from {len(files)} file(s), {len(raters)} rater(s).")


if __name__ == "__main__":
    main()
