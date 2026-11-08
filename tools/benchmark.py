#!/usr/bin/env python3
"""Run all four policies on identical seeded inputs; retain raw logs and CSV."""
import argparse
import csv
import hashlib
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
POLICIES = ("round_robin", "best_fit", "min_power", "deadline_energy")


def run(path, policy, seed_offset=0, timeout=120):
    source = Path(path).read_text()
    source = re.sub(r"(Seed:\s*)(\d+)",
                    lambda m: m[1] + str(int(m[2]) + seed_offset), source)
    with tempfile.TemporaryDirectory(prefix="cloudsim-") as directory:
        input_path = Path(directory) / "input"
        input_path.write_text(source)
        started = time.perf_counter()
        process = subprocess.run([str(ROOT / "simulator"), str(input_path)],
                                 env={**os.environ, "SCHEDULER_POLICY": policy},
                                 text=True, capture_output=True, timeout=timeout)
        wall = time.perf_counter() - started
    if process.returncode != 0 or "RESULT " not in process.stdout:
        raise RuntimeError(f"{path} / {policy}: {process.stdout}\n{process.stderr}")
    result_lines = [line for line in process.stdout.splitlines() if line.startswith("RESULT ")]
    if len(result_lines) != 1:
        raise RuntimeError("Expected exactly one RESULT line")
    record = dict(item.split("=", 1) for item in result_lines[0].split()[1:])
    if record["policy"] != policy:
        raise RuntimeError("Simulator did not use the requested policy")
    try:
        label = str(Path(path).relative_to(ROOT))
    except ValueError:
        label = str(Path(path))
    record.update(workload=label, seed_offset=seed_offset,
                  wall_seconds=f"{wall:.6f}", input_sha256=hashlib.sha256(source.encode()).hexdigest())
    return record, process.stdout + process.stderr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="*", type=Path)
    parser.add_argument("--seed-offsets", nargs="+", type=int, default=[0, 101, 202])
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "benchmark.csv")
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()
    inputs = args.inputs or [*sorted((ROOT / "input_files" / "custom").glob("0[2-6]*")),
                            ROOT / "input_files/provided/NiceAndSmooth-1",
                            ROOT / "input_files/provided/SpikeyNefarious-1"]
    args.output = args.output.resolve()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    logdir = args.output.parent / (args.output.stem + "_logs")
    logdir.mkdir(exist_ok=True)
    records = []
    for path in inputs:
        path = path.resolve()
        for offset in args.seed_offsets:
            for policy in POLICIES:
                record, log = run(path, policy, offset, args.timeout)
                records.append(record)
                (logdir / f"{path.name}_{offset}_{policy}.log").write_text(log)
                print(f"{path.name:24} {offset:3} {policy:16} "
                      f"E={record['energy_kwh']} SLA={record['sla0']}/{record['sla1']}/{record['sla2']}",
                      flush=True)
                # Persist each result, including when a later run fails.
                with args.output.open("w", newline="") as output:
                    writer = csv.DictWriter(output, fieldnames=list(records[0]))
                    writer.writeheader()
                    writer.writerows(records)
    print(f"Wrote {len(records)} measurements to {args.output}")


if __name__ == "__main__":
    main()
