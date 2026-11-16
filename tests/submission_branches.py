#!/usr/bin/env python3
"""Verify each prepared grading branch runs its own algorithm without env setup."""
import csv
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from prepare_algorithm_branches import ALGORITHMS


def result(executable, path, policy=None):
    environment = {k: v for k, v in os.environ.items()
                   if not k.startswith("SCHED_") and k != "SCHEDULER_POLICY"}
    if policy:
        environment["SCHEDULER_POLICY"] = policy
    process = subprocess.run([str(executable), str(path)], capture_output=True,
                             text=True, env=environment, timeout=30)
    if process.returncode:
        raise AssertionError(process.stdout + process.stderr)
    lines = [line for line in process.stdout.splitlines() if line.startswith("RESULT ")]
    assert len(lines) == 1
    return dict(token.split("=", 1) for token in lines[0].split()[1:])


def main():
    inputs = [ROOT / "input_files/custom" / name for name in
              ("03_surge", "04_heterogeneous", "06_dvfs_slack")]
    records = []
    with tempfile.TemporaryDirectory(prefix="cloudsim-branch-check-") as tmp:
        reference = Path(tmp) / "simulator"
        object_path = Path(tmp) / "Scheduler.o"
        subprocess.run(["g++", "-O2", "-std=c++17", "-I", str(ROOT), "-c",
                        str(ROOT / "Scheduler.cpp"), "-o", str(object_path)], check=True)
        subprocess.run(["g++", "-o", str(reference), str(object_path),
                        *[str(ROOT / n) for n in
                          ("Init.o", "Machine.o", "main.o", "Simulator.o", "Task.o", "VM.o")]], check=True)
        for policy, (branch, _, _) in ALGORITHMS.items():
            executable = ROOT / "branch_previews" / branch / "simulator"
            assert executable.exists(), "Run tools/prepare_algorithm_branches.py --build first"
            direct_object = Path(tmp) / (policy + ".o")
            direct_executable = Path(tmp) / policy
            subprocess.run(["g++", "-O2", "-std=c++17", "-I", str(ROOT), "-c",
                            str(executable.parent / "Scheduler.cpp"), "-o", str(direct_object)], check=True)
            subprocess.run(["g++", "-o", str(direct_executable), str(direct_object),
                            *[str(ROOT / n) for n in
                              ("Init.o", "Machine.o", "main.o", "Simulator.o", "Task.o", "VM.o")]], check=True)
            for path in inputs:
                default = result(executable, path)
                expected = result(reference, path, policy)
                assert default["policy"] == policy, (branch, default)
                assert default == expected, (branch, path.name, default, expected)
                assert result(direct_executable, path) == expected, "Direct compilation selected the wrong policy"
                assert default["memory_warnings"] == "0" and default["deep_sleeps"] == "0"
                if policy != "deadline_energy":
                    assert default["dvfs_changes"] == "0"
                elif path.name == "06_dvfs_slack":
                    assert int(default["dvfs_changes"]) > 0
                records.append({"branch": branch, "workload": str(path.relative_to(ROOT)),
                                "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), **default})
            wrong_policy = "best_fit" if policy == "round_robin" else "round_robin"
            process = subprocess.run([str(executable), str(inputs[0])], capture_output=True,
                                     text=True, env={**os.environ, "SCHEDULER_POLICY": wrong_policy})
            assert process.returncode != 0 and "this branch implements" in process.stdout + process.stderr
            print(f"{branch}: correct default under Makefile and direct compilation; paired results match; conflicting policy rejected")
    destination = ROOT / "results/submission_branches.csv"
    with destination.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(records)
    print("Verified 12 paired branch runs; wrote results/submission_branches.csv")


if __name__ == "__main__":
    main()
