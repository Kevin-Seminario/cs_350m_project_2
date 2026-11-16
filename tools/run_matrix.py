#!/usr/bin/env python3
"""Run scenario x policy x seed through the simulator and write a CSV.

Usage (from the project root):
    python3 tools/run_matrix.py --inputs inputs \
        --policies round_robin best_fit min_power deadline_energy \
        --out results/runs/v1.csv --label v1 [--env SCHED_DWELL_US=1000000]
    python3 tools/run_matrix.py --provided input_files/provided --out results/runs/provided.csv

--inputs: directory of <scenario>_s<seed>.md files (see tools/gen_inputs.py).
--provided: directory of supplied workloads such as NiceAndSmooth-1 (scenario
    "NiceAndSmooth", seed 1; a name with no -N suffix gets seed 0).
./simulator is rebuilt with `make` first (use --no-build to skip).
Policy is passed as SCHEDULER_POLICY. Scheduler tunables go in with --env KEY=VAL
(repeatable): SCHED_DWELL_US, SCHED_DEEP_STATE, SCHED_DEEP_WAKE_US, SCHED_WAKE_PENALTY,
SCHED_DVFS_GAIN, SCHED_TIMER_MARGIN_US, SCHED_WAKE_US, SCHED_SAFETY (see README).
Each row is parsed from the scheduler's RESULT line; a crash, timeout or missing
RESULT line is recorded as failed=1 rather than aborting the matrix.
"""
import argparse
import csv
import glob
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

NAME_RE = re.compile(r"^(?P<scenario>.+)_s(?P<seed>\d+)\.md$")
PROVIDED_RE = re.compile(r"^(?P<scenario>.+?)(?:-(?P<seed>\d+))?$")
# Only diagnostics the simulator/scheduler really emit; a bare "abort" in a task
# name must not fail a run.
BAD_TEXT = re.compile(r"Simulation ended with unfinished|terminate called|"
                      r"Segmentation fault|Unknown SCHEDULER_POLICY|Invalid value for SCHED|"
                      r"std::\w*exception|Exception:", re.I)


def run_one(job):
    sim, path, scenario, seed, policy, env_extra, timeout, logdir, label = job
    env = {**os.environ, "SCHEDULER_POLICY": policy, **env_extra}
    row = dict(label=label, scenario=scenario, seed=seed, policy=policy,
               rc="", failed=1, note="", wall_s="")
    t0 = time.time()
    try:
        p = subprocess.run([os.path.abspath(sim), os.path.abspath(path)], env=env,
                           capture_output=True, text=True, timeout=timeout, cwd=logdir)
        out = p.stdout + p.stderr
        row["rc"] = p.returncode
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        row["note"] = "timeout"
        row["rc"] = "timeout"
    row["wall_s"] = round(time.time() - t0, 2)
    tag = f"{label}_{scenario}_s{seed}_{policy}".strip("_")
    with open(os.path.join(logdir, tag + ".log"), "w") as f:
        f.write(out)
    res = re.search(r"^RESULT (.*)$", out, re.M)
    if res:
        for kv in res.group(1).split():
            k, _, v = kv.partition("=")
            row[k] = v
    else:
        # Fall back to the supplied human-readable report (works for any scheduler).
        e = re.search(r"Total Energy ([0-9.eE+-]+)", out)
        if e:
            row["energy_kwh"] = e.group(1)
        for i in range(3):
            s = re.search(rf"SLA{i}: ([0-9.eE+-]+)%", out)
            if s:
                row[f"sla{i}"] = s.group(1)
        t = re.search(r"finished in ([0-9.eE+-]+) seconds", out)
        if t:
            row["simulated_seconds"] = t.group(1)
    bad = BAD_TEXT.search(out)
    if bad and not row["note"]:
        row["note"] = "output mentions: " + bad.group(0).lower()
    ok = (row["rc"] == 0 and "energy_kwh" in row and not row["note"])
    row["failed"] = 0 if ok else 1
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", default="./simulator")
    ap.add_argument("--inputs", default="inputs",
                    help="directory of <scenario>_s<seed>.md files ('' to skip)")
    ap.add_argument("--provided", help="directory of supplied workloads (NiceAndSmooth-1, ...)")
    ap.add_argument("--no-build", action="store_true", help="do not run make first")
    ap.add_argument("--policies", nargs="+",
                    default=["round_robin", "best_fit", "min_power", "deadline_energy"])
    ap.add_argument("--scenarios", nargs="*", help="subset of scenario names")
    ap.add_argument("--seeds", type=int, nargs="*", help="subset of seeds")
    ap.add_argument("--out", default="results/baseline.csv")
    ap.add_argument("--env", action="append", default=[], metavar="KEY=VAL")
    ap.add_argument("--label", default="")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    a = ap.parse_args()

    if not a.no_build and os.path.abspath(a.sim) == os.path.abspath("./simulator"):
        if subprocess.run(["make", "-s", "all"], stdout=subprocess.DEVNULL).returncode:
            sys.exit("make failed")
    if not os.access(a.sim, os.X_OK):
        sys.exit(f"simulator not executable: {a.sim}")
    env_extra = dict(kv.split("=", 1) for kv in a.env)
    targets = []  # (path, scenario, seed)
    for f in sorted(glob.glob(os.path.join(a.inputs, "*.md"))) if a.inputs else []:
        m = NAME_RE.match(os.path.basename(f))
        if m:
            targets.append((f, m["scenario"], int(m["seed"])))
    if a.provided:
        for f in sorted(glob.glob(os.path.join(a.provided, "*"))):
            if os.path.isfile(f):
                m = PROVIDED_RE.match(os.path.basename(f))
                targets.append((f, m["scenario"].replace(" ", ""), int(m["seed"] or 0)))
    jobs, logdir = [], os.path.join(os.path.dirname(os.path.abspath(a.out)), "logs")
    os.makedirs(logdir, exist_ok=True)
    for f, scenario, seed in targets:
        if a.scenarios and scenario not in a.scenarios:
            continue
        if a.seeds and seed not in a.seeds:
            continue
        for p in a.policies:
            jobs.append((a.sim, f, scenario, seed, p, env_extra, a.timeout, logdir, a.label))
    if not jobs:
        sys.exit("no input files matched")
    print(f"{len(jobs)} runs on {a.jobs} workers", file=sys.stderr)

    with ThreadPoolExecutor(a.jobs) as ex:
        rows = list(ex.map(run_one, jobs))

    # Cross-policy consistency: every policy must complete the same task count.
    counts = {}
    for r in rows:
        if not r["failed"]:
            counts.setdefault((r["scenario"], r["seed"]), set()).add(r.get("tasks"))
    for r in rows:
        inconsistent = len(counts.get((r["scenario"], r["seed"]), ())) > 1
        r["consistent"] = 0 if inconsistent else 1
        if inconsistent:
            r["failed"] = 1
            r["note"] = (r["note"] + " task-count mismatch across policies").strip()

    first = ["label", "scenario", "seed", "policy", "failed", "rc", "note",
             "consistent", "tasks", "energy_kwh", "simulated_seconds",
             "sla0", "sla1", "sla2", "wall_s"]
    extra = sorted({k for r in rows for k in r} - set(first))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, first + extra, restval="")
        w.writeheader()
        w.writerows(rows)

    bad = [r for r in rows if r["failed"]]
    print(f"wrote {a.out}: {len(rows)} runs, {len(bad)} failed", file=sys.stderr)
    for r in bad:
        print(f"  FAIL {r['scenario']} s{r['seed']} {r['policy']}: rc={r['rc']} {r['note']}",
              file=sys.stderr)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
