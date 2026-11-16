#!/usr/bin/env python3
"""Regression checks for the experiment comparison tool."""
from copy import deepcopy
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import report


def row(failed=0, seed="1", policy="deadline_energy"):
    return dict(scenario="fixture", variant=policy, policy=policy, seed=seed,
                failed=failed, energy_kwh="1", simulated_seconds="1",
                sla0="0", sla1="0", sla2="0")


def problems(new, old):
    return report.compare(new, old, .02, "round_robin")[2]


def main():
    baseline = [row()]
    assert not problems(deepcopy(baseline), baseline)
    assert problems([row(failed=1)], baseline), "all-failed results must fail comparison"
    assert problems([row()], [row(), row(seed="2")]), "missing runs must fail comparison"
    assert problems([row(policy="round_robin")], baseline), "missing groups must fail comparison"
    worse = row(); worse["energy_kwh"] = "1.1"
    assert problems([worse], baseline)
    late = row(); late["sla0"] = "6"
    assert problems([late], baseline)
    print("Experiment regression checks passed")


if __name__ == "__main__":
    main()
