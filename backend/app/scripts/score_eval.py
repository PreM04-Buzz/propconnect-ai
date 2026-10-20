"""Score the blind ratings once both raters have filled in docs/eval/rating-sheet.csv.

Each rater adds their rows (one per answer) with 1-4 on the four criteria and
their name in the "rater" column. This unblinds them with data/eval/rating-key.csv
and writes the comparison table to docs/eval/scores.md.

Run from backend/:  python -m app.scripts.score_eval
"""
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[3]
CRITERIA = ["grounded_1to4", "right_action_1to4", "specific_1to4", "draft_quality_1to4"]


def label(avg: float, grounded_ok: bool) -> str:
    out = "Very Good" if avg >= 3.5 else "Good" if avg >= 2.75 else "Acceptable" if avg >= 2.0 else "Poor"
    if not grounded_ok and out in ("Very Good", "Good"):
        return "Acceptable"  # an invented fact caps the rating
    return out


def main() -> None:
    key = {row["scenario"]: row for row in csv.DictReader(open(ROOT / "data/eval/rating-key.csv", encoding="utf-8"))}
    raw = json.loads((ROOT / "data/eval/results.json").read_text(encoding="utf-8"))
    titles = {str(r["n"]): r["title"] for r in raw["results"]}
    scores: dict[tuple[str, str], list[float]] = defaultdict(list)
    grounded: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in csv.DictReader(open(ROOT / "docs/eval/rating-sheet.csv", encoding="utf-8")):
        if not row["rater"].strip():
            continue
        who = key[row["scenario"]][row["answer"]]
        vals = [float(row[c]) for c in CRITERIA]
        scores[(row["scenario"], who)].append(mean(vals))
        grounded[(row["scenario"], who)].append(vals[0])
    if not scores:
        raise SystemExit("No ratings yet: fill in docs/eval/rating-sheet.csv (put your name in the rater column).")

    lines = ["# AI evaluation: scores", "", "Average of both raters, 1 to 4. An invented fact caps an answer at Acceptable.", "",
             "| # | Scenario | Rule-based | AI | Better |", "| --- | --- | --- | --- | --- |"]
    totals = defaultdict(list)
    labels = defaultdict(list)
    for n in sorted(titles, key=int):
        cells = {}
        for who in ("rules", "ai"):
            if (n, who) in scores:
                avg = mean(scores[(n, who)])
                lab = label(avg, min(grounded[(n, who)]) >= 3)
                totals[who].append(avg)
                labels[who].append(lab)
                cells[who] = (avg, f"{avg:.2f} ({lab})")
        better = "–"
        if "rules" in cells and "ai" in cells:
            d = cells["ai"][0] - cells["rules"][0]
            better = "AI" if d >= 0.25 else "Rules" if d <= -0.25 else "Tie"
        lines.append(f"| {n} | {titles[n]} | {cells.get('rules', (0, '–'))[1]} | {cells.get('ai', (0, '–'))[1]} | {better} |")
    lines += ["", "| Measure | Rule-based | AI |", "| --- | --- | --- |"]
    fmt = lambda xs: f"{mean(xs):.2f}" if xs else "–"  # noqa: E731
    good = lambda who: sum(l in ("Very Good", "Good") for l in labels[who])  # noqa: E731
    lines.append(f"| Average score (out of 4) | {fmt(totals['rules'])} | {fmt(totals['ai'])} |")
    lines.append(f"| Rated Very Good or Good | {good('rules')} of {len(labels['rules'])} | {good('ai')} of {len(labels['ai'])} |")
    (ROOT / "docs/eval/scores.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Wrote docs/eval/scores.md")


if __name__ == "__main__":
    main()
