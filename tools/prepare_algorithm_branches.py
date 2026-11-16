#!/usr/bin/env python3
"""Prepare and verify four branch contents without changing Git refs or committing.

The previews contain the current files, including uncommitted corrections. Each
pins a separate algorithm in algorithm.mk. They are reviewable local directories,
not published Git branches. See SUBMISSION_SETUP.md for the later Git steps.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ALGORITHMS = {
    "round_robin": ("algorithm-round-robin", "Capacity-aware round robin",
                    "Cyclic placement among compatible hosts with a free core and sufficient memory. All hosts remain in S0/P0."),
    "best_fit": ("algorithm-best-fit", "Best-fit consolidation",
                 "Choose the fullest feasible host. Execute at P0 and put idle non-standby hosts into S1."),
    "min_power": ("algorithm-min-power", "Online minimum incremental power (MBFD adaptation)",
                  "Choose the feasible host with the least incremental power. Execute at P0 and put idle non-standby hosts into S1. The literature source is cited in Scheduler.cpp and the report."),
    "deadline_energy": ("algorithm-deadline-energy", "Deadline-aware energy placement and DVFS",
                        "Minimize predicted execution energy while protecting admitted deadlines; select P-states dynamically. Optional deep sleep is disabled by default."),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true", help="build and run each branch's complete tests")
    args = parser.parse_args()
    output = ROOT / "branch_previews"
    output.mkdir(exist_ok=True)
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    new = ["algorithm.mk", "SUBMISSION_SETUP.md", "submission.md", "submission.tex", "submission.pdf",
           "tools/prepare_algorithm_branches.py", "tests/submission_branches.py", "tests/tooling.py"]
    new += [str(p.relative_to(ROOT)) for p in (ROOT / "submission_configs").glob("*.mk")]
    # Copy source, supplied objects, evidence and docs. Rebuild generated executables.
    exclude = {"Scheduler.o", "simulator", "tests/scheduler_test", "scheduler"}
    files = sorted(set(tracked + new) - exclude - {""})
    manifest = {"status": "prepared locally; no Git branches, commits or pushes created",
                "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "algorithms": []}
    for policy, (branch, title, description) in ALGORITHMS.items():
        destination = output / branch
        if destination.exists():
            shutil.rmtree(destination)
        destination.mkdir()
        for name in files:
            source = ROOT / name
            if not source.is_file() or name.endswith((".aux", ".log", ".out")) and not name.startswith("results/"):
                continue
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        shutil.copyfile(ROOT / "submission_configs" / (policy + ".mk"), destination / "algorithm.mk")
        # Pin the source too: grading must work even when the course compiles
        # Scheduler.cpp directly rather than using our Makefile.
        source_path = destination / "Scheduler.cpp"
        source_path.write_text(
            "// Grading branch: " + branch + "\n"
            "#if !defined(SCHEDULER_ENGINE_TEST) && !defined(SCHEDULER_FIXED_POLICY)\n"
            '#define SCHEDULER_FIXED_POLICY "' + policy + '"\n'
            "#endif\n\n" + source_path.read_text())
        (destination / "ALGORITHM.md").write_text(
            f"# {title}\n\nGrading branch: `{branch}`. Policy: `{policy}`.\n\n{description}\n\n"
            "Run `make all` followed by `./simulator input_files/custom/03_surge`. "
            "The policy is compiled in; no environment variable is required. "
            "A conflicting SCHEDULER_POLICY is rejected.\n\n"
            "Run `make test` for engine unit tests and this branch's eight normal integration workloads, "
            "repeatability, invalid inputs and overload checks.\n\n"
            "The shared implementation supplies compatibility, memory accounting, VM lifecycle and "
            "admission checks. The algorithm-specific placement and power decisions are selected "
            "by this branch's algorithm.mk and its matching source-level policy pin. "
            "Direct compilation of Scheduler.cpp also selects the same policy.\n\n"
            "Use report_updated.pdf for the comparative report. Historical experiments with deep sleep "
            "are identified separately; deep sleep is not one of the four algorithms.\n")
        with (destination / "README.md").open("r+") as handle:
            original = handle.read()
            handle.seek(0)
            handle.write(f"# Grading branch: {title}\n\nSee [ALGORITHM.md](ALGORITHM.md). "
                         f"This branch always runs `{policy}`.\n\n" + original)
        if args.build:
            for target in ("all", "test"):
                process = subprocess.run(["make", target], cwd=destination, text=True, capture_output=True)
                (output / f"{branch}-{target}.log").write_text(process.stdout + process.stderr)
                if process.returncode:
                    raise SystemExit(f"{branch}: make {target} failed; see branch_previews/{branch}-{target}.log")
        manifest["algorithms"].append({"branch": branch, "policy": policy, "path": str(destination),
            "algorithm_mk_sha256": hashlib.sha256((destination / "algorithm.mk").read_bytes()).hexdigest(),
            "scheduler_sha256": hashlib.sha256((destination / "Scheduler.cpp").read_bytes()).hexdigest(),
            "tested": args.build})
        print(f"Prepared {branch}: {policy}" + ("; build and tests passed" if args.build else ""), flush=True)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("No Git branches, commits, pushes or repository settings were changed.")


if __name__ == "__main__":
    main()
