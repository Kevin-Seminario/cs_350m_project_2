# Cloud management for energy and performance

Four selectable scheduling policies for the supplied CloudSim simulator. All public
headers and supplied simulator objects are unchanged. The implementation, custom
workloads, tests, and report were developed with OpenAI Codex; the literature
adaptation is attributed in `Scheduler.cpp` and the report.

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
- `report.pdf`: the short comparative report; `report.tex` is its editable source.
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
