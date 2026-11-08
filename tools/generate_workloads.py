#!/usr/bin/env python3
"""Generate the team's repeatable, independent stress scenarios (Codex assisted)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def machine(n=8, cpu="X86", cores=4, memory=2048, gpu=False,
            mips=(3000, 2400, 1800, 1000), power=(24, 14, 8, 4),
            base=(100, 75, 40, 20, 8, 2, 0)):
    return stanza("machine", {
        "Number of machines": n, "CPU type": cpu, "Number of cores": cores,
        "Memory": memory, "S-States": list(base), "P-States": list(power),
        "C-States": [power[0], 3, 1, 0], "MIPS": list(mips),
        "GPUs": "yes" if gpu else "no"})


def task(start=100000, end=12000000, interval=400000, runtime=800000,
         memory=32, vm="LINUX", cpu="X86", gpu=False, sla="SLA1", seed=1701):
    return stanza("task", {
        "Start time": start, "End time": end, "Inter arrival": interval,
        "Expected runtime": runtime, "Memory": memory, "VM type": vm,
        "GPU enabled": "yes" if gpu else "no", "SLA type": sla,
        "CPU type": cpu, "Task type": "AI" if gpu else "WEB", "Seed": seed})


def stanza(kind, fields):
    return kind + " class:\n{\n" + "".join(
        f"    {key}: {value}\n" for key, value in fields.items()) + "}\n\n"


def workloads():
    return {
        "02_low_intensity": machine() + task(interval=900000, runtime=300000, sla="SLA2"),
        "03_surge": machine(n=12) + task(interval=500000) +
            task(start=3000000, end=5000000, interval=12000, runtime=2000000,
                 sla="SLA0", seed=1702) +
            task(start=8000000, end=10000000, interval=12000, runtime=2000000,
                 sla="SLA0", seed=1703),
        "04_heterogeneous":
            machine(n=3, mips=(4000, 3000, 2000, 1200)) +
            machine(n=3, gpu=True, mips=(2000, 1600, 1200, 800)) +
            machine(n=2, cpu="ARM") + machine(n=2, cpu="POWER") +
            machine(n=2, cpu="RISCV") +
            task(interval=80000, seed=1704) +
            task(gpu=True, interval=90000, vm="WIN", sla="SLA0", seed=1705) +
            task(cpu="ARM", vm="LINUX_RT", interval=200000, sla="SLA1", seed=1706) +
            task(cpu="POWER", vm="AIX", interval=200000, sla="SLA2", seed=1707) +
            task(cpu="RISCV", vm="LINUX", interval=200000, sla="SLA3", seed=1708),
        "05_memory_pressure": machine(n=3, memory=96) +
            task(end=6000000, interval=120000, runtime=800000, memory=48, seed=1709) +
            task(end=6000000, interval=200000, runtime=800000, memory=48,
                 vm="WIN", sla="SLA2", seed=1710),
        "06_dvfs_slack":
            machine(n=4, cores=8, power=(80, 24, 10, 4), base=(30, 25, 15, 10, 5, 1, 0)) +
            task(end=15000000, interval=100000, runtime=1200000, sla="SLA2", seed=1711),
    }


def main():
    directory = ROOT / "input_files" / "custom"
    directory.mkdir(parents=True, exist_ok=True)
    for name, contents in workloads().items():
        (directory / name).write_text(contents)
    print(f"Generated {len(workloads())} workloads in {directory.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
