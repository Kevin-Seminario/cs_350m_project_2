#!/usr/bin/env python3
"""Summarize run_matrix.py output for benchmarking and for the written report.

Usage (from the project root):
    python3 tools/report.py results/runs/after.csv
    python3 tools/report.py results/runs/after.csv --md results/report.md --plots results/plots --tex results/matrix_table.tex
    python3 tools/report.py results/runs/after.csv --compare results/runs/before.csv   # regression check

What it does:
  * Aggregates seeds per scenario x policy (mean / min-max; failed runs excluded
    but counted).
  * Energy savings are PAIRED: each run is compared with the baseline policy on
    the same scenario and seed, then averaged.
  * SLA check follows the spec: SLA0 <= 5%, SLA1 <= 10%, SLA2 <= 20% of tasks
    late. A class with no tasks in a run is not evaluated. A cell passes only
    if every seed passes.
  * --compare exits non-zero if energy got worse by more than --energy-tol, an
    SLA cell went pass -> fail, or more runs failed.
  * Prints a note when policies are indistinguishable (identical energy on every
    run), since such rows add nothing to a comparative study.

If the CSV holds several labels, each (label, policy) pair is its own row, so a
new design can be benchmarked next to the old one in a single table.
"""
import argparse
import csv
import statistics as st
import sys
from collections import defaultdict

# Two-sided 95% Student-t critical values by degrees of freedom.
T95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306,
       9: 2.262, 10: 2.228}


def ci95(xs):
    """Half-width of the 95% CI of the mean (None for fewer than two samples)."""
    if len(xs) < 2:
        return None
    return T95.get(len(xs) - 1, 1.96) * st.stdev(xs) / len(xs) ** 0.5


SLA_LIMIT = {0: 5.0, 1: 10.0, 2: 20.0}  # max % of tasks that may miss, per spec


def f(x, default=None):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def load(path, label=None):
    rows = list(csv.DictReader(open(path)))
    if label:
        rows = [r for r in rows if r.get("label") == label]
    if not rows:
        sys.exit(f"{path}: no rows" + (f" for label {label!r}" if label else ""))
    labels = sorted({r.get("label", "") for r in rows})
    for r in rows:
        r["variant"] = r["policy"] if len(labels) == 1 else f"{r.get('label', '')}:{r['policy']}"
        r["failed"] = int(f(r.get("failed"), 1))
    return rows


def sla_ok(r):
    """Per-run SLA verdict: (passed, worst_excess_pct)."""
    ok, worst = True, 0.0
    for i, lim in SLA_LIMIT.items():
        n = f(r.get(f"sla{i}_tasks"), None)
        v = f(r.get(f"sla{i}"), 0.0)
        if n == 0:
            continue  # nothing of that class ran
        if v > lim:
            ok = False
        worst = max(worst, v - lim)
    return ok, worst


def order_variants(rows, baseline):
    seen = []
    for r in rows:
        if r["variant"] not in seen:
            seen.append(r["variant"])
    base = [v for v in seen if v.split(":")[-1] == baseline]
    return base + [v for v in seen if v not in base]


def summarize(rows, baseline):
    scen_order = list(dict.fromkeys(r["scenario"] for r in rows))
    variants = order_variants(rows, baseline)
    base_variant = next((v for v in variants if v.split(":")[-1] == baseline), None)

    by = defaultdict(list)
    for r in rows:
        by[(r["scenario"], r["variant"])].append(r)
    base_energy = {}
    base_time = {}
    if base_variant:
        for r in rows:
            if r["variant"] == base_variant and not r["failed"]:
                base_energy[(r["scenario"], r["seed"])] = f(r["energy_kwh"])
                base_time[(r["scenario"], r["seed"])] = f(r["simulated_seconds"])

    out = []
    for s in scen_order:
        for v in variants:
            rs = by.get((s, v), [])
            if not rs:
                continue
            good = [r for r in rs if not r["failed"]]
            c = dict(scenario=s, variant=v, runs=len(rs), failed=len(rs) - len(good))
            if good:
                e = [f(r["energy_kwh"]) for r in good]
                c.update(e_mean=st.mean(e), e_min=min(e), e_max=max(e),
                         t_mean=st.mean(f(r["simulated_seconds"]) for r in good))
                sav, slow = [], []
                for r in good:
                    be = base_energy.get((s, r["seed"]))
                    bt = base_time.get((s, r["seed"]))
                    if be:
                        sav.append(100.0 * (be - f(r["energy_kwh"])) / be)
                    if bt:
                        slow.append(100.0 * (f(r["simulated_seconds"]) - bt) / bt)
                c["saving"] = st.mean(sav) if sav else None
                c["saving_ci"] = ci95(sav)
                c["slowdown"] = st.mean(slow) if slow else None
                c["sla_worst"] = [max(f(r.get(f"sla{i}"), 0.0) for r in good) for i in range(3)]
                verdicts = [sla_ok(r) for r in good]
                c["sla_pass"] = all(ok for ok, _ in verdicts) and not c["failed"]
                c["sla_seeds_ok"] = sum(ok for ok, _ in verdicts)
                for k in ("wakeups", "queued", "dvfs_changes", "memory_warnings"):
                    vals = [f(r.get(k)) for r in good if f(r.get(k)) is not None]
                    c[k] = st.mean(vals) if vals else None
                dr = [f(r.get("mean_deadline_ratio")) for r in good if f(r.get("mean_deadline_ratio")) is not None]
                c["deadline_ratio"] = st.mean(dr) if dr else None
            else:
                c["sla_pass"] = False
            out.append(c)
    return out, scen_order, variants, base_variant


def fmt(x, spec, dash="-"):
    return dash if x is None else format(x, spec)


def table_rows(cells):
    hdr = ["Scenario", "Policy", "Energy kWh mean [min-max]", "Saved vs base", "Sim s",
           "Slower", "SLA0/1/2 worst %", "SLA", "Wake", "Queued"]
    rows = []
    for c in cells:
        if "e_mean" not in c:
            rows.append([c["scenario"], c["variant"], "ALL RUNS FAILED", "-", "-", "-", "-", "FAIL", "-", "-"])
            continue
        sla = "/".join(f"{x:.1f}" for x in c["sla_worst"])
        verdict = "pass" if c["sla_pass"] else ("FAIL" if not c["failed"] else f"FAIL ({c['failed']} run err)")
        rows.append([c["scenario"], c["variant"],
                     f"{c['e_mean']:.5f} [{c['e_min']:.5f}-{c['e_max']:.5f}]",
                     (fmt(c["saving"], "+.1f") + (f" ±{c['saving_ci']:.1f}" if c.get("saving_ci") is not None else "") + "%")
                     if c["saving"] is not None else "-",
                     f"{c['t_mean']:.1f}", fmt(c["slowdown"], "+.1f") + "%" if c["slowdown"] is not None else "-",
                     sla, verdict, fmt(c["wakeups"], ".0f"), fmt(c["queued"], ".0f")])
    return hdr, rows


def matrix(cells, scen_order, variants, base_variant):
    """policy x scenario matrix of paired energy savings, plus an average column."""
    hdr = ["Policy"] + scen_order + ["Mean"]
    idx = {(c["scenario"], c["variant"]): c for c in cells}
    rows = []
    for v in variants:
        if v == base_variant:
            continue
        vals, row = [], [v]
        for s in scen_order:
            c = idx.get((s, v))
            sv = c.get("saving") if c else None
            if sv is not None and c.get("sla_pass"):
                row.append(f"{sv:+.1f}%")
                vals.append(sv)
            elif sv is not None:
                row.append(f"{sv:+.1f}%*")  # saved energy but broke an SLA
                vals.append(sv)
            else:
                row.append("-")
        row.append(f"{st.mean(vals):+.1f}%" if vals else "-")
        rows.append(row)
    return hdr, rows


def text_table(hdr, rows):
    w = [max(len(str(x)) for x in col) for col in zip(hdr, *rows)]
    line = lambda r: "  ".join(str(x).ljust(w[i]) for i, x in enumerate(r))
    return "\n".join([line(hdr), "  ".join("-" * x for x in w)] + [line(r) for r in rows])


def md_table(hdr, rows):
    esc = lambda x: str(x).replace("|", "\\|")
    return "\n".join(["| " + " | ".join(map(esc, hdr)) + " |",
                      "|" + "|".join("---" for _ in hdr) + "|"] +
                     ["| " + " | ".join(map(esc, r)) + " |" for r in rows])


def notes(rows, cells, variants, base_variant):
    out = []
    # indistinguishable policies
    en = defaultdict(dict)
    for r in rows:
        if not r["failed"]:
            en[r["variant"]][(r["scenario"], r["seed"])] = round(f(r["energy_kwh"]), 12)
    vs = [v for v in variants if v != base_variant]
    for i, a in enumerate(vs):
        for b in vs[i + 1:]:
            keys = set(en[a]) & set(en[b])
            same = [k for k in keys if en[a][k] == en[b][k]]
            if keys and len(same) == len(keys):
                out.append(f"'{a}' and '{b}' gave identical energy on all {len(keys)} runs; "
                           "the scenarios cannot tell them apart.")
            elif keys and len(same) / len(keys) > 0.8:
                out.append(f"'{a}' and '{b}' are identical on {len(same)}/{len(keys)} runs.")
    if cells and all(c.get("sla_pass") for c in cells):
        out.append("No SLA violations anywhere: scenarios may be too easy to test SLA compliance.")
    if cells and all((c.get("dvfs_changes") or 0) == 0 for c in cells if "e_mean" in c):
        out.append("DVFS never fired in any run (dvfs_changes = 0 everywhere).")
    if cells and all((c.get("memory_warnings") or 0) == 0 for c in cells if "e_mean" in c):
        out.append("No memory warnings in any run; memory pressure is not being exercised.")
    bad = sum(c["failed"] for c in cells)
    if bad:
        out.append(f"{bad} run(s) failed and are excluded from means.")
    return out


def plots(cells, scen_order, variants, base_variant, outdir):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping plots", file=sys.stderr)
        return
    import os
    os.makedirs(outdir, exist_ok=True)
    idx = {(c["scenario"], c["variant"]): c for c in cells if "e_mean" in c}
    # Energy is dominated by the long scenarios, so plot energy relative to baseline.
    fig, ax = plt.subplots(figsize=(max(7, 1.3 * len(scen_order)), 4.2))
    w = 0.8 / max(1, len(variants))
    for j, v in enumerate(variants):
        ys, xs = [], []
        for i, s in enumerate(scen_order):
            c = idx.get((s, v))
            b = idx.get((s, base_variant)) if base_variant else None
            if c and b:
                xs.append(i + j * w)
                ys.append(100.0 * c["e_mean"] / b["e_mean"])
        ax.bar(xs, ys, w, label=v)
    ax.axhline(100, color="gray", lw=0.8, ls="--")
    ax.set_xticks([i + 0.4 - w / 2 for i in range(len(scen_order))])
    ax.set_xticklabels(scen_order, rotation=30, ha="right")
    ax.set_ylabel(f"Energy, % of {base_variant}")
    ax.set_title("Energy relative to baseline (lower is better)")
    ax.set_ylim(0, 125)
    ax.legend(fontsize=8, frameon=False, ncol=len(variants), loc="upper center")
    fig.tight_layout()
    fig.savefig(f"{outdir}/energy_relative.png", dpi=200)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(max(7, 1.3 * len(scen_order)), 4.2))
    for j, v in enumerate(variants):
        xs = [i + j * w for i, s in enumerate(scen_order) if (s, v) in idx]
        ys = [max(idx[(s, v)]["sla_worst"]) for s in scen_order if (s, v) in idx]
        ax.bar(xs, ys, w, label=v)
    ax.set_xticks([i + 0.4 - w / 2 for i in range(len(scen_order))])
    ax.set_xticklabels(scen_order, rotation=30, ha="right")
    ax.set_ylabel("Worst SLA violation, % of tasks")
    ax.set_title("SLA violations (limits: SLA0 5%, SLA1 10%, SLA2 20%)")
    ax.set_ylim(0, 25)
    for lim in (5, 10, 20):
        ax.axhline(lim, color="gray", lw=0.6, ls=":")
    ax.legend(fontsize=8, frameon=False, ncol=len(variants), loc="upper center")
    fig.tight_layout()
    fig.savefig(f"{outdir}/sla_violations.png", dpi=200)
    plt.close(fig)
    print(f"plots written to {outdir}/", file=sys.stderr)


def compare(new_rows, old_rows, tol, baseline):
    nc, *_ = summarize(new_rows, baseline)
    oc, *_ = summarize(old_rows, baseline)
    old = {(c["scenario"], c["variant"]): c for c in oc}
    problems, lines = [], []
    for c in nc:
        o = old.get((c["scenario"], c["variant"]))
        if not o:
            continue
        # Check failures before means: an all-failed group has no e_mean.
        flag = ""
        if c["failed"] > o["failed"]:
            flag += " MORE FAILURES"
            problems.append(f"{c['scenario']}/{c['variant']}: {c['failed']} failed runs")
        if c["runs"] < o["runs"]:
            flag += " MISSING RUNS"
            problems.append(f"{c['scenario']}/{c['variant']}: fewer runs than the baseline")
        if "e_mean" not in c or "e_mean" not in o:
            if flag:
                lines.append([c["scenario"], c["variant"], "-", "-", "-", flag.strip()])
            continue
        d = 100.0 * (c["e_mean"] - o["e_mean"]) / o["e_mean"]
        if d > 100 * tol:
            flag = "ENERGY WORSE"
            problems.append(f"{c['scenario']}/{c['variant']}: energy {d:+.1f}%")
        if o["sla_pass"] and not c["sla_pass"]:
            flag += " SLA REGRESSION"
            problems.append(f"{c['scenario']}/{c['variant']}: SLA pass -> fail")
        lines.append([c["scenario"], c["variant"], f"{o['e_mean']:.5f}", f"{c['e_mean']:.5f}", f"{d:+.2f}%", flag.strip()])
    present = {(c["scenario"], c["variant"]) for c in nc}
    for key in old.keys() - present:
        problems.append(f"{key[0]}/{key[1]}: missing from new results")
        lines.append([key[0], key[1], "-", "-", "-", "MISSING GROUP"])
    return ["Scenario", "Policy", "Old kWh", "New kWh", "Change", "Flag"], lines, problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--label", help="only rows with this label")
    ap.add_argument("--baseline", default="round_robin", help="policy used as the reference (default round_robin)")
    ap.add_argument("--md", help="write a Markdown report to this file")
    ap.add_argument("--summary-csv", help="write the aggregated table to this CSV")
    ap.add_argument("--plots", help="directory for PNG charts")
    ap.add_argument("--tex", help="write the savings matrix as a LaTeX table (for report.tex)")
    ap.add_argument("--compare", help="older CSV to check for regressions against")
    ap.add_argument("--energy-tol", type=float, default=0.02, help="allowed energy increase for --compare (default 0.02 = 2%%)")
    a = ap.parse_args()

    rows = load(a.csv, a.label)
    cells, scen_order, variants, base_variant = summarize(rows, a.baseline)
    if base_variant is None:
        print(f"note: baseline policy '{a.baseline}' not found; savings not computed", file=sys.stderr)
    hdr, trs = table_rows(cells)
    mh, mrs = matrix(cells, scen_order, variants, base_variant)
    nts = notes(rows, cells, variants, base_variant)
    nseeds = len({r["seed"] for r in rows})

    print(f"{len(rows)} runs, {len(scen_order)} scenarios, {len(variants)} policies, {nseeds} seeds; "
          f"baseline = {base_variant}\n")
    print(text_table(hdr, trs))
    if mrs:
        print(f"\nEnergy saved vs {base_variant} (paired by seed; * = SLA violated)\n")
        print(text_table(mh, mrs))
    if nts:
        print("\nNotes:")
        for n in nts:
            print(f"  - {n}")

    if a.summary_csv:
        keys = ["scenario", "variant", "runs", "failed", "e_mean", "e_min", "e_max", "t_mean", "saving",
                "saving_ci", "slowdown", "sla_pass", "sla_seeds_ok", "wakeups", "queued", "dvfs_changes",
                "memory_warnings", "deadline_ratio"]
        with open(a.summary_csv, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(keys)
            for c in cells:
                w.writerow([c.get(k, "") for k in keys])
    if a.md:
        with open(a.md, "w") as fh:
            fh.write(f"# Benchmark results\n\n{len(rows)} runs; {len(scen_order)} scenarios; "
                     f"{nseeds} seeds per scenario; baseline: `{base_variant}`.\n\n")
            fh.write("SLA limits (max share of tasks missing their deadline): SLA0 5%, SLA1 10%, SLA2 20%. "
                     "A cell passes only if every seed passes. Savings are paired by scenario and seed.\n\n")
            if mrs:
                fh.write(f"## Energy saved vs `{base_variant}`\n\n" + md_table(mh, mrs) +
                         "\n\n`*` = saved energy but violated an SLA.\n\n")
            fh.write("## Detail\n\n" + md_table(hdr, trs) + "\n\n")
            if nts:
                fh.write("## Caveats\n\n" + "\n".join(f"- {n}" for n in nts) + "\n")
        print(f"\nMarkdown written to {a.md}", file=sys.stderr)
    if a.tex:
        esc = lambda x: str(x).replace("_", r"\_").replace("%", r"\%").replace("*", "$^*$")
        with open(a.tex, "w") as fh:
            fh.write("\\begin{center}\\scriptsize\\setlength{\\tabcolsep}{3pt}\n"
                     "\\resizebox{\\linewidth}{!}{\\begin{tabular}{l" + "r" * (len(mh) - 1) + "}\\toprule\n")
            fh.write(" & ".join(esc(x) for x in mh) + " \\\\\\midrule\n")
            for r in mrs:
                fh.write(" & ".join(esc(x) for x in r) + " \\\\\n")
            fh.write("\\bottomrule\\end{tabular}}\\end{center}\n")
        print(f"LaTeX table written to {a.tex}", file=sys.stderr)
    if a.plots:
        plots(cells, scen_order, variants, base_variant, a.plots)

    if a.compare:
        ch, cl, problems = compare(rows, load(a.compare, None), a.energy_tol, a.baseline)
        print(f"\nRegression check vs {a.compare} (energy tolerance {a.energy_tol:.0%})\n")
        print(text_table(ch, cl))
        if problems:
            print("\nREGRESSIONS:")
            for p in problems:
                print(f"  - {p}")
            sys.exit(1)
        print("\nno regressions")


if __name__ == "__main__":
    main()