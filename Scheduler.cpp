// Energy/performance scheduler for the supplied CloudSim interface.
// Implementation and experiments developed with OpenAI Codex (November 2026).
// min_power adapts the incremental-power placement rule of Beloglazov,
// Abawajy & Buyya, FGCS 28 (2012), Algorithm 1 (MBFD):
// https://clouds.cis.unimelb.edu.au/papers/Energy-Aware-CloudResourceAllocation-FGCS2012.pdf
// This is an online adaptation, not the paper's batch sorting/migration policy.
#include <cstdint> // Supplied headers use uint64_t without including it.
#include "Scheduler.hpp"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <limits>
#include <map>
#include <set>
#include <unordered_map>

namespace {
constexpr MachineId_t NO_HOST = std::numeric_limits<MachineId_t>::max();
// Defaults for tunables; each can be overridden by an environment variable so
// experiments (tools/run_matrix.py --env KEY=VAL) need no recompilation.
constexpr double DEFAULT_TIMER_MARGIN = 120000.0; // Two 60 ms scheduling ticks.
constexpr double DEFAULT_WAKE_ESTIMATE = 420000.0; // Conservative S1 wake + timer alignment.
constexpr double DEFAULT_SAFETY = 1.10;           // Multiplier on predicted service time.

double env_double(const char* key, double fallback, double lo, double hi) {
    const char* text = std::getenv(key);
    if (!text || !*text) return fallback;
    char* end = nullptr;
    const double value = std::strtod(text, &end);
    if (end == text || *end != '\0' || !(value >= lo && value <= hi))
        ThrowException(std::string("Invalid value for ") + key + ": " + text);
    return value;
}
enum class Policy { RoundRobin, BestFit, MinPower, DeadlineEnergy };

struct Host {
    MachineInfo_t hardware{};
    std::vector<TaskId_t> tasks; // Includes reservations while a host wakes.
    std::map<VMType_t, VMId_t> vms;
    bool changing = false;
    MachineState_t requested = S0;
    bool standby = false; // One immediately available host per CPU family.
    Time_t idle_since = 0; // Start of the current empty spell (valid if idle_valid).
    bool idle_valid = false;
};
struct Assignment {
    TaskInfo_t task{};
    MachineId_t host = NO_HOST;
    bool attached = false;
};

class Controller {
public:
    Policy policy = Policy::DeadlineEnergy;
#ifdef SCHEDULER_FIXED_POLICY
    std::string name = SCHEDULER_FIXED_POLICY;
#else
    std::string name = "deadline_energy";
#endif
    std::vector<Host> hosts;
    std::unordered_map<TaskId_t, Assignment> jobs;
    std::vector<TaskId_t> pending;
    size_t cursor = 0;
    bool draining = false;
    unsigned completed = 0, peak_active = 0, wakeups = 0, warnings = 0;
    unsigned dvfs_changes = 0, queued = 0, normalized_count = 0;
    unsigned sla_counts[NUM_SLAS] = {};
    double response_sum = 0.0, normalized_sum = 0.0;
    // Tunables (environment overrides; see init()).
    double timer_margin = DEFAULT_TIMER_MARGIN;  // SCHED_TIMER_MARGIN_US
    double wake_estimate = DEFAULT_WAKE_ESTIMATE; // SCHED_WAKE_US
    double safety = DEFAULT_SAFETY;              // SCHED_SAFETY
    double dwell_us = 0.0;       // SCHED_DWELL_US: idle time before deep sleep; 0 = never
    double deep_wake_us = 2000000.0; // SCHED_DEEP_WAKE_US: wake estimate from deep sleep
    double dvfs_gain = 0.0;      // SCHED_DVFS_GAIN: min fractional saving to leave P0
    MachineState_t deep_state = S3;  // SCHED_DEEP_STATE: enum values 3..6 (S2..S5)
    double wake_penalty = 40.0;  // SCHED_WAKE_PENALTY: DE score cost (J) of waking a host (0.01 = old)
    unsigned deep_sleeps = 0;

    void init() {
        *this = Controller{};
        if (const char* option = std::getenv("SCHEDULER_POLICY")) {
#ifdef SCHEDULER_FIXED_POLICY
            if (name != option)
                ThrowException("Unknown SCHEDULER_POLICY for this grading branch: " +
                               std::string(option) + "; this branch implements " + name);
#else
            name = option;
#endif
        }
        if (name == "round_robin") policy = Policy::RoundRobin;
        else if (name == "best_fit") policy = Policy::BestFit;
        else if (name == "min_power") policy = Policy::MinPower;
        else if (name != "deadline_energy")
            ThrowException("Unknown SCHEDULER_POLICY: " + name);
        timer_margin = env_double("SCHED_TIMER_MARGIN_US", DEFAULT_TIMER_MARGIN, 0, 1e9);
        wake_estimate = env_double("SCHED_WAKE_US", DEFAULT_WAKE_ESTIMATE, 0, 1e9);
        safety = env_double("SCHED_SAFETY", DEFAULT_SAFETY, 1.0, 10.0);
        dwell_us = env_double("SCHED_DWELL_US", 0.0, 0, 1e12);
        deep_wake_us = env_double("SCHED_DEEP_WAKE_US", 2000000.0, 0, 1e9);
        dvfs_gain = env_double("SCHED_DVFS_GAIN", 0.0, 0.0, 1.0);
        const double selected_state = env_double("SCHED_DEEP_STATE", double(S3), double(S2), double(S5));
        if (selected_state != std::floor(selected_state))
            ThrowException("Invalid value for SCHED_DEEP_STATE: expected an integer from 3 through 6");
        deep_state = static_cast<MachineState_t>(int(selected_state));
        wake_penalty = env_double("SCHED_WAKE_PENALTY", 40.0, 0.0, 1e6);
        hosts.resize(Machine_GetTotal());
        std::map<CPUType_t, MachineId_t> standby;
        for (MachineId_t id = 0; id < hosts.size(); ++id) {
            auto& h = hosts[id];
            h.hardware = Machine_GetInfo(id);
            if (h.hardware.num_cpus == 0 || h.hardware.performance.size() < P_STATES ||
                h.hardware.p_states.size() < P_STATES || h.hardware.c_states.size() < C_STATES ||
                h.hardware.s_states.size() < S_STATES || h.hardware.performance[P0] == 0)
                ThrowException("Invalid machine capacity or power tables");
            auto old = standby.find(h.hardware.cpu);
            if (old == standby.end() || efficiency(id) < efficiency(old->second))
                standby[h.hardware.cpu] = id;
        }
        for (const auto& entry : standby) hosts[entry.second].standby = true;
        // Never power off a CPU family based on assumptions about future arrivals.
        // Shallow sleep bounds wake latency; callbacks gate every VM attachment.
        for (MachineId_t id = 0; id < hosts.size(); ++id) {
            if (policy != Policy::RoundRobin && !hosts[id].standby) request(id, S1);
        }
        std::cout << "Scheduler policy: " << name << '\n';
    }

    double efficiency(MachineId_t id) const {
        const auto& m = hosts[id].hardware;
        return (double(m.s_states[S0]) + double(m.num_cpus) * m.p_states[P0]) /
               (double(m.num_cpus) * m.performance[P0]);
    }

    void request(MachineId_t id, MachineState_t state) {
        auto& h = hosts[id];
        if (h.changing || Machine_GetInfo(id).s_state == state) return;
        h.changing = true; // Set before the call: an upcall may be synchronous.
        h.requested = state;
        if (state == S0) ++wakeups;
        Machine_SetState(id, state);
    }

    bool ready(MachineId_t id) const {
        return !hosts[id].changing && Machine_GetInfo(id).s_state == S0;
    }

    // Predicted delay before work placed on this host can start executing.
    double wake_delay(MachineId_t id) const {
        if (ready(id)) return 0.0;
        return Machine_GetInfo(id).s_state > S1 ? std::max(wake_estimate, deep_wake_us)
                                                : wake_estimate;
    }

    uint64_t memory(MachineId_t id, const TaskInfo_t* extra = nullptr) const {
        uint64_t total = 0;
        std::set<VMType_t> types;
        for (const auto& vm : hosts[id].vms) types.insert(vm.first);
        for (auto tid : hosts[id].tasks) {
            const auto& t = jobs.at(tid).task;
            total += t.required_memory;
            types.insert(t.required_vm);
        }
        if (extra) {
            total += extra->required_memory;
            types.insert(extra->required_vm);
        }
        return total + uint64_t(types.size()) * VM_MEMORY_OVERHEAD;
    }

    static bool valid_vm(const TaskInfo_t& t) {
        return t.required_vm != AIX ?
            (t.required_vm != WIN || t.required_cpu == X86 || t.required_cpu == ARM) :
            t.required_cpu == POWER;
    }

    double runtime(const TaskInfo_t& t, const MachineInfo_t& m, unsigned p) const {
        // MIPS is instructions per microsecond. Ignore GPU acceleration in the
        // bound; acceleration improves actual service without risking optimism.
        return double(t.remaining_instructions) / std::max(1u, m.performance[p]);
    }

    bool feasible(MachineId_t id, unsigned p, Time_t now, const TaskInfo_t* extra) const {
        const auto& m = hosts[id].hardware; // Performance tables never change.
        const double delay = wake_delay(id);
        auto fits = [&](const TaskInfo_t& t) {
            if (t.required_sla == SLA3) return true;
            const double available = t.target_completion > now ?
                double(t.target_completion - now) : 0.0;
            return safety * runtime(t, m, p) + timer_margin + delay <= available;
        };
        if (extra && !fits(*extra)) return false;
        for (auto tid : hosts[id].tasks) {
            if (!fits(GetTaskInfo(tid))) return false;
        }
        return true;
    }

    double energy(MachineId_t id, unsigned p, const TaskInfo_t* extra) const {
        const auto& h = hosts[id];
        const auto& m = h.hardware;
        double longest = 0.0, service = 0.0;
        auto add = [&](const TaskInfo_t& t) {
            const double run = runtime(t, m, p);
            longest = std::max(longest, run);
            service += run;
        };
        for (auto tid : h.tasks) add(GetTaskInfo(tid));
        if (extra) add(*extra);
        // Account for static power during execution as well as dynamic power.
        // Ignoring static energy would slow memory-bound/isolated work and
        // extend the simulation's powered-on tail merely to save core watts.
        const double base = double(m.s_states[S0]) +
            double(m.num_cpus) * m.c_states[C1];
        const double dynamic = double(m.p_states[p]) - m.c_states[C1];
        return (base * longest + dynamic * service) / 1000000.0;
    }

    unsigned choose_p(MachineId_t id, Time_t now, const TaskInfo_t* extra) const {
        if (policy != Policy::DeadlineEnergy) return P0;
        unsigned best = P0;
        double cost = std::numeric_limits<double>::infinity();
        for (unsigned p = 0; p < P_STATES; ++p) {
            if (hosts[id].hardware.performance[p] == 0 || !feasible(id, p, now, extra)) continue;
            const double candidate = energy(id, p, extra);
            if (candidate < cost) { cost = candidate; best = p; }
        }
        // Leave P0 only for a worthwhile saving: slower states stretch the powered
        // tail, which the per-host estimate does not see.
        if (best != P0 && dvfs_gain > 0.0 && feasible(id, P0, now, extra)) {
            const double at_p0 = energy(id, P0, extra);
            if (cost > at_p0 * (1.0 - dvfs_gain)) return P0;
        }
        return best; // P0 if no state can satisfy the conservative bound.
    }

    MachineId_t select(const TaskInfo_t& t, Time_t now) const {
        MachineId_t best = NO_HOST;
        double best_score = std::numeric_limits<double>::infinity();
        bool best_feasible = false;
        for (size_t offset = 0; offset < hosts.size(); ++offset) {
            const MachineId_t id = policy == Policy::RoundRobin ?
                MachineId_t((cursor + offset) % hosts.size()) : MachineId_t(offset);
            const auto& h = hosts[id];
            const auto& m = h.hardware;
            if (m.cpu != t.required_cpu || h.tasks.size() >= m.num_cpus ||
                memory(id, &t) > m.memory_size) continue;
            const unsigned p = choose_p(id, now, &t);
            const bool fits = feasible(id, p, now, &t);
            double score = 0.0;
            if (policy == Policy::RoundRobin) return id;
            if (policy == Policy::BestFit) {
                score = h.tasks.empty() ? 2.0 + id * 1e-6 :
                    1.0 - double(h.tasks.size()) / m.num_cpus;
            } else if (policy == Policy::MinPower) {
                score = double(m.p_states[P0]) - m.c_states[C1];
                if (h.tasks.empty() && !h.standby)
                    score += double(m.s_states[S0]) - m.s_states[S1] +
                             double(m.num_cpus) * (double(m.c_states[C1]) - m.c_states[C2]);
            } else {
                score = energy(id, p, &t) - energy(id, Machine_GetInfo(id).p_state, nullptr);
                // Prefer an idle GPU host for GPU work when energy bounds tie.
                if (t.gpu_capable && m.gpus) score *= 0.1;
                if (!ready(id)) score += wake_penalty;
            }
            // CPU slots are hard capacity limits; deadlines are predictions.
            // If every candidate misses, make progress on the fastest one.
            if (!fits) score = wake_delay(id) + runtime(t, m, P0);
            if (best == NO_HOST || (fits && !best_feasible) ||
                (fits == best_feasible && score < best_score)) {
                best = id; best_score = score; best_feasible = fits;
            }
        }
        return best;
    }

    Priority_t priority(const TaskInfo_t& t, Time_t now) const {
        if (t.required_sla == SLA0 ||
            (t.required_sla != SLA3 && t.target_completion <= now)) return HIGH_PRIORITY;
        const double age = now >= t.arrival ? double(now - t.arrival) : 0.0;
        const double service = double(t.total_instructions) / 1000.0;
        if (age > 2.0 * service) return HIGH_PRIORITY; // Aging avoids starvation.
        return t.required_sla == SLA1 ? MID_PRIORITY : LOW_PRIORITY;
    }

    void tune(MachineId_t id, Time_t now) {
        if (!ready(id) || hosts[id].tasks.empty()) return;
        const auto p = static_cast<CPUPerformance_t>(choose_p(id, now, nullptr));
        if (Machine_GetInfo(id).p_state != p) {
            Machine_SetCorePerformance(id, 0, p); // Interface applies to all cores.
            ++dvfs_changes;
        }
    }

    void dispatch(MachineId_t id, Time_t now) {
        if (!ready(id)) return;
        auto& h = hosts[id];
        for (auto tid : h.tasks) {
            auto& job = jobs.at(tid);
            if (job.attached) continue;
            auto vm = h.vms.find(job.task.required_vm);
            if (vm == h.vms.end()) {
                const auto vid = VM_Create(job.task.required_vm, job.task.required_cpu);
                VM_Attach(vid, id);
                vm = h.vms.emplace(job.task.required_vm, vid).first;
            }
            VM_AddTask(vm->second, tid, priority(job.task, now));
            job.attached = true;
        }
        tune(id, now);
    }

    void drain(Time_t now) {
        if (draining) return;
        draining = true;
        // EDF among guaranteed classes; best-effort jobs gain rank with age.
        std::stable_sort(pending.begin(), pending.end(), [&](TaskId_t a, TaskId_t b) {
            auto key = [&](TaskId_t id) {
                const auto& t = jobs.at(id).task;
                if (t.required_sla == SLA3)
                    return priority(t, now) == HIGH_PRIORITY ? now :
                        std::numeric_limits<Time_t>::max();
                return t.target_completion;
            };
            return key(a) < key(b);
        });
        std::vector<TaskId_t> waiting;
        for (auto tid : pending) {
            auto& job = jobs.at(tid);
            const auto id = select(job.task, now);
            if (id == NO_HOST) { waiting.push_back(tid); continue; }
            job.host = id;
            hosts[id].tasks.push_back(tid);
            hosts[id].idle_valid = false;
            cursor = (size_t(id) + 1) % hosts.size();
            if (ready(id)) dispatch(id, now);
            else if (!hosts[id].changing) request(id, S0);
        }
        pending.swap(waiting);
        draining = false;
    }

    void arrival(Time_t now, TaskId_t tid) {
        const auto t = GetTaskInfo(tid);
        bool possible = false;
        for (const auto& h : hosts)
            if (valid_vm(t) && h.hardware.cpu == t.required_cpu &&
                uint64_t(t.required_memory) + VM_MEMORY_OVERHEAD <= h.hardware.memory_size)
                possible = true;
        if (!possible)
            ThrowException("Task " + std::to_string(tid) +
                " has no compatible machine with enough memory (including VM overhead)");
        jobs.emplace(tid, Assignment{t, NO_HOST, false});
        peak_active = std::max(peak_active, unsigned(jobs.size()));
        pending.push_back(tid);
        drain(now);
        if (jobs.at(tid).host == NO_HOST) ++queued;
    }

    void completion(Time_t now, TaskId_t tid) {
        auto job = jobs.find(tid);
        if (job == jobs.end()) return;
        const auto id = job->second.host;
        const auto& t = job->second.task;
        const double response = double(now - t.arrival);
        response_sum += response;
        if (t.required_sla != SLA3 && t.target_completion > t.arrival) {
            normalized_sum += response / double(t.target_completion - t.arrival);
            ++normalized_count;
        }
        ++completed;
        ++sla_counts[t.required_sla];
        auto& tasks = hosts.at(id).tasks;
        tasks.erase(std::remove(tasks.begin(), tasks.end(), tid), tasks.end());
        jobs.erase(job);
        // Defer VM reclamation until the simulator finishes its completion event.
        // The periodic callback checks VM_GetInfo before shutting an empty VM down.
        drain(now);
        tune(id, now);
    }

    void state_complete(Time_t now, MachineId_t id) {
        if (id >= hosts.size()) return;
        auto& h = hosts[id];
        h.changing = false;
        if (!h.tasks.empty()) {
            if (Machine_GetInfo(id).s_state != S0) request(id, S0);
            else dispatch(id, now);
        }
    }

    void check(Time_t now) {
        for (MachineId_t id = 0; id < hosts.size(); ++id) {
            auto& h = hosts[id];
            for (auto vm = h.vms.begin(); vm != h.vms.end();) {
                if (VM_GetInfo(vm->second).active_tasks.empty()) {
                    VM_Shutdown(vm->second);
                    vm = h.vms.erase(vm);
                } else ++vm;
            }
        }
        drain(now);
        for (MachineId_t id = 0; id < hosts.size(); ++id) {
            auto& h = hosts[id];
            if (!h.tasks.empty()) {
                dispatch(id, now);
                for (auto tid : h.tasks)
                    if (jobs.at(tid).attached)
                        SetTaskPriority(tid, priority(GetTaskInfo(tid), now));
                h.idle_valid = false;
            } else if (policy != Policy::RoundRobin && !h.standby && h.vms.empty() &&
                       Machine_GetInfo(id).active_tasks == 0) {
                const auto state = Machine_GetInfo(id).s_state;
                if (!h.idle_valid) { h.idle_valid = true; h.idle_since = now; }
                if (dwell_us > 0.0 && !h.changing && state == S1 &&
                    double(now - h.idle_since) >= dwell_us) {
                    h.changing = true;
                    h.requested = deep_state;
                    ++deep_sleeps;
                    Machine_SetState(id, deep_state);
                } else if (state == S0) {
                    request(id, S1);
                }
            }
        }
    }

    void warning(Time_t now, TaskId_t tid) {
        auto job = jobs.find(tid);
        if (job == jobs.end() || !job->second.attached || GetTaskInfo(tid).completed) return;
        SetTaskPriority(tid, HIGH_PRIORITY);
        const auto id = job->second.host;
        if (ready(id)) Machine_SetCorePerformance(id, 0, P0);
        (void)now;
    }

    void shutdown(Time_t now) {
        if (!jobs.empty() || !pending.empty() || completed != GetNumTasks())
            ThrowException("Simulation ended with unfinished scheduler tasks");
        for (auto& h : hosts) {
            for (const auto& vm : h.vms) VM_Shutdown(vm.second);
            h.vms.clear();
        }
        // Keep the supplied human-readable summary and add a precise machine-
        // readable record so experiment scripts do not depend on debug logging.
        std::cout << std::setprecision(12)
                  << "SLA violation report\nSLA0: " << GetSLAReport(SLA0)
                  << "%\nSLA1: " << GetSLAReport(SLA1)
                  << "%\nSLA2: " << GetSLAReport(SLA2) << "%\n"
                  << "Total Energy " << Machine_GetClusterEnergy() << "KW-Hour\n"
                  << "Simulation run finished in " << double(now) / 1000000.0 << " seconds\n"
                  << "RESULT policy=" << name << " tasks=" << completed
                  << " energy_kwh=" << Machine_GetClusterEnergy()
                  << " simulated_seconds=" << double(now) / 1000000.0
                  << " sla0=" << GetSLAReport(SLA0) << " sla1=" << GetSLAReport(SLA1)
                  << " sla2=" << GetSLAReport(SLA2)
                  << " mean_response_us=" << (completed ? response_sum / completed : 0.0)
                  << " mean_deadline_ratio=" << (normalized_count ? normalized_sum / normalized_count : 0.0)
                  << " sla0_tasks=" << sla_counts[SLA0] << " sla1_tasks=" << sla_counts[SLA1]
                  << " sla2_tasks=" << sla_counts[SLA2] << " sla3_tasks=" << sla_counts[SLA3]
                  << " wakeups=" << wakeups << " dvfs_changes=" << dvfs_changes
                  << " queued=" << queued << " peak_active=" << peak_active
                  << " memory_warnings=" << warnings << " deep_sleeps=" << deep_sleeps << '\n';
    }
};
Controller control;
} // namespace

void Scheduler::Init() { control.init(); }
void Scheduler::NewTask(Time_t now, TaskId_t id) { control.arrival(now, id); }
void Scheduler::TaskComplete(Time_t now, TaskId_t id) { control.completion(now, id); }
void Scheduler::PeriodicCheck(Time_t now) { control.check(now); }
void Scheduler::MigrationComplete(Time_t, VMId_t) {
    // These policies avoid migration overhead; no VM has an in-flight migration.
}
void Scheduler::Shutdown(Time_t now) { control.shutdown(now); }

static Scheduler scheduler;
void InitScheduler() { scheduler.Init(); }
void HandleNewTask(Time_t now, TaskId_t id) { scheduler.NewTask(now, id); }
void HandleTaskCompletion(Time_t now, TaskId_t id) { scheduler.TaskComplete(now, id); }
void SchedulerCheck(Time_t now) { scheduler.PeriodicCheck(now); }
void MigrationDone(Time_t now, VMId_t id) { scheduler.MigrationComplete(now, id); }
void StateChangeComplete(Time_t now, MachineId_t id) { control.state_complete(now, id); }
void SLAWarning(Time_t now, TaskId_t id) { control.warning(now, id); }
void MemoryWarning(Time_t now, MachineId_t id) {
    ++control.warnings;
    SimOutput("Memory warning on machine " + std::to_string(id) + " at " + std::to_string(now), 0);
}
void SimulationComplete(Time_t now) { scheduler.Shutdown(now); }
