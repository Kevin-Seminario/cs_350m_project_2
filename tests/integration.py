#!/usr/bin/env python3
"""Check the real, supplied simulator objects against public scheduler outcomes."""
from pathlib import Path
import argparse
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from benchmark import POLICIES, run
from generate_workloads import machine, task


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", choices=POLICIES, help="the policy pinned by a grading branch")
    args = parser.parse_args()
    policies = [args.policy] if args.policy else POLICIES
    replay_policy = args.policy or "deadline_energy"
    inputs = [ROOT / "Input.md", ROOT / "input_files/custom/01_single_server",
              *sorted((ROOT / "input_files/custom").glob("0[2-6]*")),
              ROOT / "input_files/provided/SpikeyNefarious-1"]
    checks = 0
    for path in inputs:
        populations = set()
        for policy in policies:
            result, _ = run(path, policy)
            populations.add(int(result["tasks"]))
            assert int(result["tasks"]) > 0
            assert sum(int(result[f"sla{i}_tasks"]) for i in range(4)) == int(result["tasks"])
            assert int(result["memory_warnings"]) == 0, (path, policy)
            assert float(result["energy_kwh"]) > 0
            assert float(result["simulated_seconds"]) > 0
            for i, limit in enumerate((5, 10, 20)):
                assert 0 <= float(result[f"sla{i}"]) <= limit, (path, policy, result)
            checks += 1
        assert len(populations) == 1, f"Policies saw different task populations: {path}"
    # Exact reproducibility of simulated metrics; wall-clock time is excluded.
    first, _ = run(inputs[-1], replay_policy)
    second, _ = run(inputs[-1], replay_policy)
    first.pop("wall_seconds"); second.pop("wall_seconds")
    assert first == second
    with tempfile.TemporaryDirectory(prefix="cloudsim-edge-") as directory:
        path = Path(directory) / "input"
        path.write_text(machine(n=1, cores=1) + task(cpu="ARM"))
        invalid = subprocess.run([str(ROOT / "simulator"), str(path)],
                                 capture_output=True, text=True)
        assert invalid.returncode != 0 and "no compatible machine" in invalid.stdout + invalid.stderr
        path.write_text(machine(n=1, cores=1) + task(memory=3000))
        invalid = subprocess.run([str(ROOT / "simulator"), str(path)],
                                 capture_output=True, text=True)
        assert invalid.returncode != 0 and "no compatible machine" in invalid.stdout + invalid.stderr
        path.write_text(machine(n=1, cores=1) + task())
        invalid = subprocess.run([str(ROOT / "simulator"), str(path)], capture_output=True,
                                 text=True, env={**os.environ, "SCHEDULER_POLICY": "typo"})
        assert invalid.returncode != 0 and "Unknown SCHEDULER_POLICY" in invalid.stdout + invalid.stderr
        # Deliberately insufficient CPU capacity: violations must be measured,
        # rather than hidden by dropped tasks or a constant zero-valued summary.
        path.write_text(machine(n=1, cores=1, mips=(100, 80, 60, 40)) +
                        task(end=600000, interval=10000, runtime=200000, sla="SLA0"))
        # run() records paths relative to the repo; this fixture lives in /tmp.
        process = subprocess.run([str(ROOT / "simulator"), str(path)], capture_output=True,
                                 text=True, env={**os.environ, "SCHEDULER_POLICY": replay_policy},
                                 timeout=30)
        assert process.returncode == 0, process.stdout
        record = dict(item.split("=", 1) for item in next(
            line for line in process.stdout.splitlines() if line.startswith("RESULT ")).split()[1:])
        assert int(record["tasks"]) > 20 and float(record["sla0"]) > 5
        assert int(record["memory_warnings"]) == 0
    print(f"Integration checks passed: {checks} normal runs, repeatability, "
          "invalid inputs, and truthful overload reporting")


if __name__ == "__main__":
    main()
