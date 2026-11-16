# Online minimum incremental power (MBFD adaptation)

Grading branch: `algorithm-min-power`. Policy: `min_power`.

Choose the feasible host with the least incremental power. Execute at P0 and put idle non-standby hosts into S1. The literature source is cited in Scheduler.cpp and the report.

Run `make all` followed by `./simulator input_files/custom/03_surge`. The policy is compiled in; no environment variable is required. A conflicting SCHEDULER_POLICY is rejected.

Run `make test` for engine unit tests and this branch's eight normal integration workloads, repeatability, invalid inputs and overload checks.

The shared implementation supplies compatibility, memory accounting, VM lifecycle and admission checks. The algorithm-specific placement and power decisions are selected by this branch's algorithm.mk and its matching source-level policy pin. Direct compilation of Scheduler.cpp also selects the same policy.

Use report_updated.pdf for the comparative report. Historical experiments with deep sleep are identified separately; deep sleep is not one of the four algorithms.
