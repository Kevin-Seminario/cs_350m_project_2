# Grading branch: Online minimum incremental power (MBFD adaptation)

See [ALGORITHM.md](ALGORITHM.md). This branch always runs `min_power`.

# Cloud management for energy and performance

Four selectable scheduling policies for the supplied CloudSim simulator. All public
headers and supplied simulator objects are unchanged. The literature-based policy
is attributed in `Scheduler.cpp` and the report.

## Instructor clarification: four grading branches

The development branch contains shared scheduler infrastructure and supports all
four policies for comparative experiments. Each proposed grading branch pins one
algorithm at compile time through `algorithm.mk`; plain `make all` and
`./simulator INPUT` run that algorithm. A conflicting `SCHEDULER_POLICY` is rejected.

| Grading branch | Algorithm |
|---|---|
| `algorithm-round-robin` | Capacity-aware round robin |
| `algorithm-best-fit` | Best-fit consolidation |
| `algorithm-min-power` | Online minimum incremental power (MBFD adaptation) |
| `algorithm-deadline-energy` | Deadline-aware execution-energy placement and DVFS |

The submission document links the four grading branches. Run
`python3 tools/prepare_algorithm_branches.py --build` to regenerate tested local
copies in `branch_previews/`. See `SUBMISSION_SETUP.md` for build and verification
instructions. The repository remains public; the course's private-repository
requirement has not been met.

Deep sleep is an optional experiment, not one of the four algorithms. It remains
off in every grading configuration. Its historical default wake estimate is 2 s,
while S3 wake-up takes about 6 s in the supplied simulator; do not enable it for
these graded runs. The report identifies those experiments separately.

## Build and run

```sh
make all
./simulator input_files/custom/03_surge
SCHEDULER_POLICY=min_power ./simulator input_files/provided/NiceAndSmooth-1
./simulator -v 4 input_files/custom/04_heterogeneous
```

`SCHEDULER_POLICY` selects `round_robin`, `best_fit`, `min_power`, or
`deadline_energy` (default). No recompilation is needed. Unknown policy names and
requests that no installed machine can support fail with an explicit diagnostic.
Inputs must use the original simulator's format and legal CPU/OS combinations.

- **round_robin:** cyclic placement on compatible available hosts; all machines
  stay at S0/P0. This is the performance baseline.
- **best_fit:** pack the fullest host with a free core and enough memory, then
  open another host. Uses P0 and S1 for idle hosts.
- **min_power:** choose the host with the least incremental power, an online
  adaptation of Beloglazov, Abawajy, and Buyya's MBFD placement rule. Uses P0/S1.
- **deadline_energy:** predict execution energy including machine static power;
  select placement and P-state while checking all admitted task deadlines.
  GPU-capable hosts receive a placement preference for GPU-capable work.

The energy policies prefer hosts that pass the conservative deadline bound;
if none pass, they favor the fastest candidate. All policies enforce CPU/OS compatibility, one admitted task per core, and memory
capacity including 8 MB per distinct VM image. Overflow waits in an EDF admission
queue with aging for best-effort work. These are common safeguards, so this round
robin baseline intentionally differs from the unsafe supplied starter. Idle VMs
are reclaimed. The three energy policies retain one S0 standby per CPU family and
put other empty hosts in S1; VM attachments wait for state-completion callbacks.
They do not use migration. The fixed 120 ms scheduling margin and 420 ms wake
estimate are conservative heuristics for the provided 60 ms timer, not guarantees
for another simulator implementation or an infeasible workload.

`make clean` removes only build products that can be regenerated. It preserves
`Init.o`, `Machine.o`, `main.o`, `Simulator.o`, `Task.o`, and `VM.o`, whose source
files were not provided. A C++17 compiler and Python 3 are required. Regenerating the report also needs
Matplotlib and pdfLaTeX; neither is needed to build or run the scheduler. The supplied
objects require a compatible x86-64 Linux C++ ABI.

## Deliverables and verification

- `Scheduler.cpp`: implementation, without changes to the provided headers.
- `input_files/custom/02_low_intensity` through `06_dvfs_slack`: five new scenarios.
  `04_heterogeneous` is the suggested input-file submission; it covers all four
  CPU families, all four VM types, GPU affinity, and mixed SLA classes.
- `report_updated.pdf`: the current comparative report; `report_updated.tex` is its source.
- `submission.pdf`: submission document listing the four grading branches.
- `SUBMISSION_SETUP.md`: branch mapping, build commands, and verification instructions.
- `results/*.csv` and `results/*_logs/`: measured results and raw simulator output.

```sh
make test
make benchmark
# Regenerate the five custom workloads exactly:
python3 tools/generate_workloads.py
# Reproduce the larger supplied workloads (one seed each):
python3 tools/benchmark.py input_files/provided/BigSmall-1 \
  input_files/provided/SpikeyMean-1 input_files/provided/TallShort-1 \
  input_files/provided/GentlerHour-1 input_files/provided/AnHour \
  --seed-offsets 0 --output results/extended.csv --timeout 180
python3 tools/benchmark.py input_files/provided/Day-1 \
  --seed-offsets 0 --output results/day.csv --timeout 300
# Regenerate report tables/figure and compile the report:
python3 tools/summarize.py
pdflatex -interaction=nonstopmode -halt-on-error report.tex
```

`make test` exercises strict mock-interface behavior and 32 real simulator runs,
repeatability, invalid inputs, and intentionally insufficient capacity. The normal
integration suite asserts the per-class SLA limits (5%, 10%, 20%) and zero memory
warnings. The supplied `TallShort-1` is reported separately because all four
policies exceed the SLA0 allowance under its sustained overload; the report keeps
those violations visible. No tasks are discarded to improve reported SLAs.

The default benchmark runs seven workloads with three seed offsets (0, 101, 202)
and all four policies, producing 84 measurements. Each CSV records the actual
seed offset, input SHA-256, policy, completion count, per-class task counts, energy
(kWh), simulated makespan (seconds), wall time (seconds), mean response time
(microseconds), and mean response/deadline-budget ratio for SLA0–SLA2 tasks.
A zero SLA percentage for an absent class means there were no observations;
consult the corresponding task count. SLA3 is best effort and excluded from the
normalized deadline ratio. Raw `RESULT` records make these measurements auditable.

The simulator objects supply initialization, random task generation, event queues,
and CPU/VM execution. Those components are already implemented; the assignment's
later general description does not require replacing the provided infrastructure.
See the assignment PDF for the original specification and course contact details.

## Experiment tools and scheduler tunables (added after the first submission)

All scripts live in `tools/` and are run from the project root.

| Script | Purpose |
|---|---|
| `tools/gen_inputs.py` | Generates `inputs/<scenario>_s<seed>.md` (12 scenarios, 5 seeds by default, incl. `overload`, `near_capacity`, `tight_deadline`). `--list` shows them. |
| `tools/run_matrix.py` | Rebuilds `./simulator`, runs scenario x seed x policy in parallel, writes a CSV plus raw logs. `--provided input_files/provided` adds the supplied workloads. |
| `tools/report.py` | Aggregates a CSV: paired savings with 95% CI, SLA verdicts, plots, Markdown, a LaTeX table (`--tex`), and `--compare old.csv` regression checks. |
| `tools/benchmark.py`, `tools/summarize.py` | Original 84-run study and its tables. |

Optional environment variables (defaults reproduce the original behavior except
`SCHED_WAKE_PENALTY`; pass them with `run_matrix.py --env KEY=VAL`):

| Variable | Default | Meaning |
|---|---|---|
| `SCHED_TIMER_MARGIN_US` | 120000 | Scheduling-tick margin in the deadline bound |
| `SCHED_WAKE_US` | 420000 | Wake-from-S1 estimate |
| `SCHED_SAFETY` | 1.10 | Multiplier on predicted service time |
| `SCHED_DVFS_GAIN` | 0 | Minimum fractional saving required to leave P0 |
| `SCHED_WAKE_PENALTY` | 40 | DE score penalty (J) for waking a sleeping host (old value 0.01) |
| `SCHED_DWELL_US` | 0 (off) | Idle time before an empty host goes from S1 to deep sleep |
| `SCHED_DEEP_STATE` | 4 | Simulator enum: 3=S2, 4=S3, 5=S4, 6=S5 (integer only) |
| `SCHED_DEEP_WAKE_US` | 2000000 | Wake estimate used by the deadline bound for deep-sleeping hosts |

Invalid values stop the run with an explicit error. The RESULT line also reports `deep_sleeps`.

Deep-sleep caveat (measured, 5 seeds): `SCHED_DWELL_US=1000000` cut `deadline_energy` energy by
roughly 50-59% on diurnal, long_idle, NiceAndSmooth, Day and the Hour workloads with no SLA failures,
but raised energy 43% on `mem_pressure` (makespan +177%) and worsened SLA misses on `TallShort`
(SLA0 about 34% -> 72%). It is therefore off by default.

## Appending results to the report

```sh
make all
python3 tools/gen_inputs.py                       # 12 scenarios x 5 seeds -> inputs/
python3 tools/run_matrix.py --provided input_files/provided --label after --timeout 900 --out results/runs/after.csv
python3 tools/run_matrix.py --provided input_files/provided --label after_deep --timeout 900 \
    --env SCHED_DWELL_US=1000000 --out results/runs/after_deep.csv
python3 tools/report.py results/runs/after_deep.csv --compare results/runs/before.csv   # regression check
python3 tools/make_revision_table.py --before results/runs/before.csv --after results/runs/after.csv \
    --deep results/runs/after_deep.csv --no-matrix   # writes results/revision_table.tex
pdflatex -interaction=nonstopmode -halt-on-error report_updated.tex   # needs pdfLaTeX
```

`results/runs/before.csv` was produced by the pre-change scheduler (`results/runs/simulator_before`).
The Day workload makes a full run take roughly 15 minutes; add `--scenarios` to subset.
`report_updated.tex` inputs `results/revision_table.tex` as Table 5; the original `report.tex` is unchanged.
