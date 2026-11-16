#!/usr/bin/env python3
"""Generate CloudSim input files for the benchmark matrix.

Usage:
    python3 gen_inputs.py --out inputs --seeds 1 2 3 4 5
    python3 gen_inputs.py --list

Writes <out>/<scenario>_s<seed>.md. Machine classes stay fixed per scenario
(16 X86 + 24 ARM, same as the sample; hetero_power adds POWER). The seed changes
every task class's RNG seed, so runs are repeatable but differ across seeds.
"""
import argparse
import os

X86 = dict(n=16, cpu="X86", cores=8, mem=16384, gpu="yes")
ARM = dict(n=24, cpu="ARM", cores=16, mem=16384, gpu="yes")
# Small cluster (4 x 8 + 4 x 16 = 96 cores) used by the stress scenarios.
X86_S = dict(n=4, cpu="X86", cores=8, mem=16384, gpu="yes")
ARM_S = dict(n=4, cpu="ARM", cores=16, mem=16384, gpu="yes")
POWER = dict(n=8, cpu="POWER", cores=8, mem=16384, gpu="no")


def machine(m):
    return f"""machine class:
{{
        Number of machines: {m['n']}
        CPU type: {m['cpu']}
        Number of cores: {m['cores']}
        Memory: {m['mem']}
        S-States: [120, 100, 100, 80, 40, 10, 0]
        P-States: [12, 8, 6, 4]
        C-States: [12, 3, 1, 0]
        MIPS: [1000, 800, 600, 400]
        GPUs: {m['gpu']}
}}
"""


def task(start, end, inter, runtime, sla, cpu="X86", mem=8, vm="LINUX",
         gpu="no", ttype="WEB", seed=0):
    return f"""task class:
{{
        Start time: {start}
        End time: {end}
        Inter arrival: {inter}
        Expected runtime: {runtime}
        Memory: {mem}
        VM type: {vm}
        GPU enabled: {gpu}
        SLA type: {sla}
        CPU type: {cpu}
        Task type: {ttype}
        Seed: {seed}
}}
"""


S = 1_000_000  # one second in microseconds


# Each scenario: (description, machine classes, fn(seed_fn) -> list of task stanzas).
# seed_fn(i) gives a distinct RNG seed for the i-th task class.
def sc_sample(sd):
    return [task(60000, 800000, 6000, 2 * S, "SLA0", seed=sd(0))]


def sc_low(sd):
    return [task(60000, 800000, 60000, 2 * S, "SLA0", seed=sd(0))]


def sc_surge(sd):
    return [task(60000, 2 * S, 40000, 2 * S, "SLA1", seed=sd(0)),
            task(600000, 800000, 1500, 2 * S, "SLA0", seed=sd(1))]


def sc_diurnal(sd):
    # quiet -> ramp -> peak -> ramp down -> quiet, with a long tail
    phases = [(0, 10 * S, 400000), (10 * S, 20 * S, 150000),
              (20 * S, 30 * S, 40000), (30 * S, 40 * S, 150000),
              (40 * S, 50 * S, 400000)]
    return [task(a + 60000, b, i, 2 * S, "SLA1", seed=sd(k))
            for k, (a, b, i) in enumerate(phases)]


def sc_hetero_gpu(sd):
    return [task(60000, 800000, 12000, 2 * S, "SLA0", seed=sd(0)),
            task(60000, 800000, 8000, 3 * S, "SLA2", cpu="ARM", seed=sd(1)),
            task(60000, 800000, 20000, 1 * S, "SLA3", seed=sd(2)),
            task(60000, 800000, 15000, 4 * S, "SLA1", gpu="yes", ttype="AI", seed=sd(3))]


def sc_mem_pressure(sd):
    # ~2.1 GB per task: only 7 fit per 16 GB host even though hosts have 8 cores
    return [task(60000, 1_500_000, 20000, 2 * S, "SLA1", mem=2100, seed=sd(0))]


def sc_slack_mix(sd):
    # long-running tolerant work: gives DVFS and deferral a chance to matter
    return [task(60000, 800000, 15000, 2 * S, "SLA0", seed=sd(0)),
            task(60000, 800000, 15000, 6 * S, "SLA2", ttype="HPC", seed=sd(1)),
            task(60000, 800000, 15000, 6 * S, "SLA3", ttype="HPC", seed=sd(2))]


def sc_long_idle(sd):
    # sparse arrivals over a long horizon: sleep depth / break-even test
    return [task(60000, 120 * S, 3 * S, 2 * S, "SLA1", seed=sd(0))]


def sc_power_aix(sd):
    return [task(60000, 800000, 30000, 2 * S, "SLA1", seed=sd(0)),
            task(60000, 800000, 30000, 2 * S, "SLA1", cpu="POWER", vm="AIX", seed=sd(1))]


def sc_overload(sd):
    # Sustained arrivals above capacity: queues build, SLA0 deadlines come under stress.
    return [task(60000, 3 * S, 2000, 3 * S, "SLA0", seed=sd(0)),
            task(60000, 3 * S, 4000, 3 * S, "SLA1", seed=sd(1))]


def sc_near_capacity(sd):
    # Roughly 85-95% core utilisation for a long stretch.
    return [task(60000, 10 * S, 60000, 2 * S, "SLA0", seed=sd(0)),
            task(60000, 10 * S, 100000, 3 * S, "SLA1", seed=sd(1))]


def sc_tight_deadline(sd):
    # Short SLA0 jobs: little slack, so slow P-states and wake delays should be avoided.
    return [task(60000, 5 * S, 20000, S // 2, "SLA0", seed=sd(0)),
            task(60000, 5 * S, 60000, 1 * S, "SLA0", seed=sd(1))]


SCENARIOS = {
    "sample":       ("given sample input", [X86, ARM], sc_sample),
    "low":          ("low intensity, saves energy", [X86, ARM], sc_low),
    "surge":        ("steady load plus a burst", [X86, ARM], sc_surge),
    "diurnal":      ("50 s ramp up / peak / ramp down", [X86, ARM], sc_diurnal),
    "hetero_gpu":   ("X86+ARM, mixed SLAs, GPU tasks", [X86, ARM], sc_hetero_gpu),
    "mem_pressure": ("memory-bound hosts", [X86, ARM], sc_mem_pressure),
    "slack_mix":    ("SLA2/SLA3 long tasks with slack", [X86, ARM], sc_slack_mix),
    "long_idle":    ("120 s sparse arrivals", [X86, ARM], sc_long_idle),
    "power_aix":    ("POWER hosts with AIX VMs", [X86, ARM, POWER], sc_power_aix),
    "overload":     ("small cluster, arrivals above capacity", [X86_S, ARM_S], sc_overload),
    "near_capacity": ("small cluster, ~90% utilisation", [X86_S, ARM_S], sc_near_capacity),
    "tight_deadline": ("small cluster, short SLA0 jobs", [X86_S, ARM_S], sc_tight_deadline),
}


def build(name, seed):
    _, machines, fn = SCENARIOS[name]
    sd = lambda i: seed * 1000 + 7 * i + 1
    return "".join(machine(m) for m in machines) + "".join(fn(sd))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="inputs")
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3, 4, 5])
    ap.add_argument("--scenarios", nargs="+", default=list(SCENARIOS))
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        for k, (d, _, _) in SCENARIOS.items():
            print(f"{k:14s} {d}")
        return
    os.makedirs(a.out, exist_ok=True)
    for name in a.scenarios:
        if name not in SCENARIOS:
            ap.error(f"unknown scenario {name}")
        for s in a.seeds:
            with open(os.path.join(a.out, f"{name}_s{s}.md"), "w") as f:
                f.write(build(name, s))
    print(f"wrote {len(a.scenarios) * len(a.seeds)} files to {a.out}")


if __name__ == "__main__":
    main()
