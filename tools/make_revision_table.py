#!/usr/bin/env python3
"""Write results/revision_table.tex (\\input by report_updated.tex) from run_matrix CSVs.

Usage (project root):
    python3 tools/make_revision_table.py --before results/runs/before.csv \
        --after results/runs/after.csv --deep results/runs/after_deep.csv

Compares deadline_energy across: the original scheduler (before), the new
defaults (after), and the new defaults with SCHED_DWELL_US deep sleep (deep).
Every number is read from the CSVs; nothing is typed in by hand.
"""
import argparse
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import report as R  # noqa: E402

POLICY = "deadline_energy"


def cells(path):
    rows = R.load(path)
    cs, order, *_ = R.summarize(rows, "round_robin")
    return {(c["scenario"], c["variant"]): c for c in cs}, order, len({r["seed"] for r in rows if int(r["seed"]) > 0})


def tex(x):
    return str(x).replace("_", r"\_").replace("%", r"\%")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--deep")
    ap.add_argument("--out", default="results/revision_table.tex")
    ap.add_argument("--no-matrix", action="store_true",
                    help="omit the savings-vs-round-robin matrix (keeps the report short)")
    a = ap.parse_args()
    b, order, _ = cells(a.before)
    n, _, seeds = cells(a.after)
    d = cells(a.deep)[0] if a.deep else {}
    lines = [
             r"\begin{center}\scriptsize\setlength{\tabcolsep}{3pt}\resizebox{\linewidth}{!}{%",
             r"\begin{tabular}{lrrrrrcc}\toprule",
             r"Scenario & Before & After & Change & Deep & Change & SLA after & SLA deep \\ \midrule"]
    for s in order:
        cb, cn, cd = (x.get((s, POLICY)) for x in (b, n, d))
        if not (cb and cn and "e_mean" in cb and "e_mean" in cn):
            continue
        pct = lambda c: f"{100 * (c['e_mean'] - cb['e_mean']) / cb['e_mean']:+.1f}\\%"
        sla = lambda c: "pass" if c["sla_pass"] else "FAIL"
        has = cd and "e_mean" in cd
        lines.append(" & ".join([tex(s), f"{cb['e_mean']:.5f}", f"{cn['e_mean']:.5f}", pct(cn),
                                 f"{cd['e_mean']:.5f}" if has else "-", pct(cd) if has else "-",
                                 sla(cn), sla(cd) if has else "-"]) + r" \\")
    lines += [r"\bottomrule\end{tabular}}\end{center}", ""]
    lines.append(r"\begin{center}\small Table 5. DE cluster energy (kWh, mean over seeds) for the original scheduler "
                 r"(Before), the revised defaults (After) and deep sleep enabled (Deep); SLA columns use the "
                 r"5/10/20\% limits.\end{center}")
    lines.append("")
    if not a.no_matrix:
        lines.append("Savings of the deep-sleep configuration relative to round robin (paired by seed; "
                     "$^*$ = an SLA class was violated):")
        # reuse report.py's savings matrix for the best configuration available
        path = a.deep or a.after
        rows = R.load(path)
        cs, order2, variants, base = R.summarize(rows, "round_robin")
        mh, mrs = R.matrix(cs, order2, variants, base)
        esc = lambda x: tex(x).replace("*", "$^*$")
        lines += [r"\begin{center}\tiny\setlength{\tabcolsep}{2pt}\resizebox{\linewidth}{!}{%",
                  r"\begin{tabular}{l" + "r" * (len(mh) - 1) + r"}\toprule",
                  " & ".join(esc(x) for x in mh) + r" \\ \midrule"]
        lines += [" & ".join(esc(x) for x in r) + r" \\" for r in mrs]
        lines += [r"\bottomrule\end{tabular}}\end{center}"]
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    open(a.out, "w").write("\n".join(lines) + "\n")
    print(f"wrote {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
