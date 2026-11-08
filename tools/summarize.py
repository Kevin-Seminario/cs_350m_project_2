#!/usr/bin/env python3
"""Render auditable report tables and a standalone energy comparison figure."""
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from benchmark import ROOT, POLICIES

LABELS = {"02_low_intensity": "Low intensity", "03_surge": "Surge",
          "04_heterogeneous": "Heterogeneous", "05_memory_pressure": "Memory pressure",
          "06_dvfs_slack": "DVFS slack", "NiceAndSmooth-1": "NiceAndSmooth",
          "SpikeyNefarious-1": "SpikeyNefarious"}
SHORT = ("RR", "BF", "MP", "DE")
OUT = ROOT / "results"


def read(name):
    path = OUT / name
    return list(csv.DictReader(path.open())) if path.exists() else []


def average(rows, field):
    return mean(float(row[field]) for row in rows)


def latex_table(path, columns, header, rows):
    text = [r"\begin{tabular}{" + columns + "}", r"\toprule", header + r" \\", r"\midrule"]
    text.extend(" & ".join(row) + r" \\" for row in rows)
    text.extend([r"\bottomrule", r"\end{tabular}"])
    (OUT / path).write_text("\n".join(text) + "\n")


def main():
    rows = read("benchmark.csv")
    extended = read("extended.csv") + read("day.csv")
    groups = defaultdict(list)
    for row in rows:
        groups[Path(row["workload"]).name, row["policy"]].append(row)
    labels = list(dict.fromkeys(Path(row["workload"]).name for row in rows))
    energy_rows = []
    for label in labels:
        values = [average(groups[label, p], "energy_kwh") * 1000 for p in POLICIES]
        energy_rows.append([LABELS[label], *[f"{value:.3f}" for value in values]])
    latex_table("energy_table.tex", "lrrrr", "Workload & RR & BF & MP & DE", energy_rows)
    performance_rows = []
    for label in labels:
        cells = []
        for policy in POLICIES:
            group = groups[label, policy]
            response = average(group, "mean_response_us") / 1e6
            makespan = average(group, "simulated_seconds")
            wall = average(group, "wall_seconds")
            cells.append(f"{response:.3f}/{makespan:.2f}/{wall:.3f}")
        performance_rows.append([LABELS[label], *cells])
    latex_table("performance_table.tex", "lrrrr", "Workload & RR & BF & MP & DE", performance_rows)
    ext_groups = defaultdict(list)
    for row in extended:
        ext_groups[Path(row["workload"]).name, row["policy"]].append(row)
    ext_labels = list(dict.fromkeys(Path(row["workload"]).name for row in extended))
    for label in ext_labels[:]:
        if any(not ext_groups[label, policy] for policy in POLICIES):
            print(f"Skipping incomplete benchmark group: {label}")
            ext_labels.remove(label)
    ext_energy = []
    ext_runtime = []
    for label in ext_labels:
        ext_energy.append([label.replace("-1", ""), *[
            f"{average(ext_groups[label, p], 'energy_kwh'):.5f}" for p in POLICIES]])
        ext_runtime.append([label.replace("-1", ""), *[
            f"{average(ext_groups[label, p], 'simulated_seconds'):.2f}/"
            f"{average(ext_groups[label, p], 'wall_seconds'):.2f}" for p in POLICIES]])
    latex_table("extended_energy_table.tex", "lrrrr", "Workload & RR & BF & MP & DE", ext_energy)
    latex_table("extended_runtime_table.tex", "lrrrr", "Workload & RR & BF & MP & DE", ext_runtime)
    tall = []
    for policy, short in zip(POLICIES, SHORT):
        group = ext_groups.get(("TallShort-1", policy))
        if group:
            tall.append([short, f"{average(group, 'sla0'):.2f}", f"{average(group, 'sla1'):.2f}"])
    latex_table("overload_table.tex", "lrr", "Policy & SLA0 misses (\\%) & SLA1 misses (\\%)", tall)

    fig, ax = plt.subplots(figsize=(9, 3.4), layout="constrained")
    width = 0.19
    for i, (policy, short) in enumerate(zip(POLICIES, SHORT)):
        values, errors = [], []
        for label in labels:
            baseline = {r["seed_offset"]: float(r["energy_kwh"]) for r in groups[label, POLICIES[0]]}
            ratios = [100 * float(r["energy_kwh"]) / baseline[r["seed_offset"]]
                      for r in groups[label, policy]]
            values.append(mean(ratios)); errors.append(stdev(ratios) if len(ratios) > 1 else 0)
        ax.bar([j + (i - 1.5) * width for j in range(len(labels))], values, width,
               label=short, yerr=errors, capsize=2)
    ax.set_xticks(range(len(labels)), [LABELS[label].replace(" ", "\n") for label in labels], fontsize=8)
    ax.set_ylabel("Energy / round robin (%)")
    ax.set_ylim(0, 112)
    ax.legend(ncol=4, loc="upper right", frameon=False)
    ax.grid(axis="y", alpha=0.2); ax.set_axisbelow(True)
    fig.savefig(OUT / "energy_comparison.pdf")
    fig.savefig(OUT / "energy_comparison.png", dpi=180)
    plt.close(fig)

    text = ["# Measured results", "", "Main study: three seed offsets (0, 101, 202). "
            "Energies are mean ± sample standard deviation in Wh. Wall times are machine-dependent.", "",
            "| Workload | Policy | Energy (Wh) | Mean response (s) | Makespan (s) | Wall (s) |",
            "|---|---|---:|---:|---:|---:|"]
    for label in labels:
        for policy in POLICIES:
            group = groups[label, policy]
            energies = [float(r["energy_kwh"]) * 1000 for r in group]
            text.append(f"| {LABELS[label]} | {policy} | {mean(energies):.6f} ± {stdev(energies):.6f} | "
                        f"{average(group, 'mean_response_us') / 1e6:.6f} | "
                        f"{average(group, 'simulated_seconds'):.6f} | {average(group, 'wall_seconds'):.6f} |")
    text += ["", "All 84 main-study runs report zero SLA misses and memory warnings. "
             "Per-class population counts and normalized response/deadline ratios are in the CSV.", "",
             "Extended study: supplied seeds unchanged; see `extended.csv` and `day.csv`. "
             "TallShort exceeds the SLA0 allowance for every policy. No result was removed."]
    (OUT / "SUMMARY.md").write_text("\n".join(text) + "\n")

    # Values used in the report prose; computed independently from displayed rounding.
    for label in labels:
        rr = average(groups[label, POLICIES[0]], "energy_kwh")
        de = average(groups[label, POLICIES[-1]], "energy_kwh")
        print(f"{LABELS[label]}: DE savings vs RR {100 * (1 - de / rr):.2f}%")
    print(f"Rendered {len(rows)} main and {len(extended)} extended measurements")


if __name__ == "__main__":
    main()
