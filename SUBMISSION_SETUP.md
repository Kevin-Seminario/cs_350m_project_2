# Submission guide

The submission document is `submission.pdf`. The comparative report is
`report_updated.pdf` (five pages). Both have editable source files beside them.

## Grading branches

Repository: https://github.com/Kevin-Seminario/cs_350m_project_2

| Branch | Algorithm |
|---|---|
| `algorithm-round-robin` | Capacity-aware round robin |
| `algorithm-best-fit` | Best-fit consolidation |
| `algorithm-min-power` | Online minimum incremental power (MBFD adaptation) |
| `algorithm-deadline-energy` | Deadline-aware energy placement and DVFS |

Each branch has an `ALGORITHM.md` description. Its `algorithm.mk` and matching
source-level policy pin select that branch's algorithm automatically, including
when `Scheduler.cpp` is compiled directly. A conflicting `SCHEDULER_POLICY`
setting is rejected. Shared code handles task/VM compatibility, memory,
admission, and callbacks.

On any grading branch:

```sh
make all
./simulator input_files/custom/03_surge
make test
```

The normal integration suite tests the algorithm compiled into that branch.
Engine unit tests exercise common infrastructure and all four policy paths.
Deep sleep remains off for grading. Historical deep-sleep experiments and their
limitations are reported separately; deep sleep is not an additional algorithm.

## Comparative development and verification

`update_latex` retains the shared development version, which supports all four
policies for comparative experiments. `main` and `attempt-one` retain earlier
history. The submission document lists only the four grading branches.

To regenerate local grading copies and verify their policy selection:

```sh
python3 tools/prepare_algorithm_branches.py --build
python3 tests/submission_branches.py
```

Local copies are written to the ignored `branch_previews/` directory. The script
does not stage, commit, push, or change Git refs. Verification checks each default
algorithm, direct compilation, rejection of conflicting selections, and paired
results on surge, heterogeneous, and DVFS workloads. The retained measurements
are in `results/submission_branches.csv`.

## Repository access

This repository remains a public fork. That does not meet the instructor's
private-repository requirement. No visibility, ownership, or deletion changes
were made. Public source is readable without a collaborator invitation; private
staff access has not been configured or verified.
