// Behavior tests against a strict mock of the public simulator interface.
// Codex assisted. No supplied simulator/header implementation is replaced.
#include "../Scheduler.cpp"
#include <cassert>
#include <functional>

namespace fake {
std::vector<MachineInfo_t> machines;
std::map<TaskId_t, TaskInfo_t> tasks;
std::map<VMId_t, VMInfo_t> vms;
std::map<MachineId_t, MachineState_t> transitions;
std::map<TaskId_t, VMId_t> placements;
Time_t sim_time = 0;
VMId_t next_vm = 0;
bool synchronous = false;

MachineInfo_t machine(CPUType_t cpu = X86, unsigned cores = 1, unsigned memory = 128) {
    MachineInfo_t m{};
    m.cpu = cpu; m.num_cpus = cores; m.memory_size = memory;
    m.performance = {3000, 2400, 1800, 1000};
    m.p_states = {24, 14, 8, 4}; m.c_states = {24, 3, 1, 0};
    m.s_states = {100 * cores, 75 * cores, 40 * cores, 20 * cores, 8 * cores, 2 * cores, 0};
    m.s_state = S0; m.p_state = P0;
    return m;
}
void reset(std::vector<MachineInfo_t> configuration, const char* policy = "deadline_energy") {
    machines = std::move(configuration);
    for (unsigned i = 0; i < machines.size(); ++i) machines[i].machine_id = i;
    tasks.clear(); vms.clear(); transitions.clear(); placements.clear();
    next_vm = 0; sim_time = 0; synchronous = false;
    setenv("SCHEDULER_POLICY", policy, 1);
    InitScheduler();
}
TaskId_t task(unsigned memory = 32, CPUType_t cpu = X86, VMType_t vm = LINUX,
              Time_t deadline = 5000000, SLAType_t sla = SLA1) {
    TaskInfo_t t{};
    t.task_id = unsigned(tasks.size()); t.required_memory = memory;
    t.required_cpu = cpu; t.required_vm = vm; t.required_sla = sla;
    t.total_instructions = t.remaining_instructions = 300000000;
    t.arrival = sim_time; t.target_completion = deadline;
    tasks[t.task_id] = t;
    return t.task_id;
}
void arrive(TaskId_t id) { HandleNewTask(sim_time, id); }
void transition(MachineId_t id) {
    machines.at(id).s_state = transitions.at(id);
    transitions.erase(id);
    StateChangeComplete(sim_time, id);
}
void finish(TaskId_t id) {
    auto& t = tasks.at(id);
    auto& v = vms.at(placements.at(id));
    auto& m = machines.at(v.machine_id);
    t.completed = true; t.remaining_instructions = 0; t.completion = sim_time;
    v.active_tasks.erase(std::remove(v.active_tasks.begin(), v.active_tasks.end(), id), v.active_tasks.end());
    m.memory_used -= t.required_memory; --m.active_tasks;
    placements.erase(id);
    HandleTaskCompletion(sim_time, id);
}
void rejects(const std::function<void()>& operation) {
    bool rejected = false;
    try { operation(); } catch (const std::invalid_argument&) { rejected = true; }
    assert(rejected);
}
} // namespace fake

unsigned Machine_GetTotal() { return unsigned(fake::machines.size()); }
MachineInfo_t Machine_GetInfo(MachineId_t id) { return fake::machines.at(id); }
void Machine_SetState(MachineId_t id, MachineState_t state) {
    assert(fake::transitions.count(id) == 0);
    assert(fake::machines.at(id).active_tasks == 0);
    if (fake::machines.at(id).s_state == state) { StateChangeComplete(fake::sim_time, id); return; }
    fake::transitions[id] = state;
    if (fake::synchronous) fake::transition(id);
}
void Machine_SetCorePerformance(MachineId_t id, unsigned, CPUPerformance_t p) {
    assert(!fake::transitions.count(id));
    fake::machines.at(id).p_state = p;
}
VMId_t VM_Create(VMType_t type, CPUType_t cpu) {
    VMInfo_t v{}; v.vm_id = fake::next_vm++; v.vm_type = type; v.cpu = cpu;
    fake::vms[v.vm_id] = v;
    return v.vm_id;
}
void VM_Attach(VMId_t id, MachineId_t machine) {
    auto& v = fake::vms.at(id); auto& m = fake::machines.at(machine);
    assert(m.s_state == S0 && !fake::transitions.count(machine));
    assert(v.cpu == m.cpu);
    assert(uint64_t(m.memory_used) + VM_MEMORY_OVERHEAD <= m.memory_size);
    m.memory_used += VM_MEMORY_OVERHEAD; ++m.active_vms;
    v.machine_id = machine;
}
void VM_AddTask(VMId_t id, TaskId_t task, Priority_t priority) {
    auto& v = fake::vms.at(id); auto& t = fake::tasks.at(task);
    auto& m = fake::machines.at(v.machine_id);
    assert(m.s_state == S0 && !fake::transitions.count(v.machine_id));
    assert(t.required_cpu == v.cpu && t.required_vm == v.vm_type);
    assert(!fake::placements.count(task));
    assert(uint64_t(m.memory_used) + t.required_memory <= m.memory_size);
    assert(m.active_tasks < m.num_cpus);
    m.memory_used += t.required_memory; ++m.active_tasks;
    t.priority = priority;
    v.active_tasks.push_back(task); fake::placements[task] = id;
}
VMInfo_t VM_GetInfo(VMId_t id) { return fake::vms.at(id); }
void VM_Shutdown(VMId_t id) {
    const auto& v = fake::vms.at(id);
    assert(v.active_tasks.empty());
    auto& m = fake::machines.at(v.machine_id);
    m.memory_used -= VM_MEMORY_OVERHEAD; --m.active_vms;
    fake::vms.erase(id);
}
TaskInfo_t GetTaskInfo(TaskId_t id) { return fake::tasks.at(id); }
void SetTaskPriority(TaskId_t id, Priority_t p) { fake::tasks.at(id).priority = p; }
unsigned GetNumTasks() { return unsigned(fake::tasks.size()); }
double GetSLAReport(SLAType_t) { return 0.0; }
double Machine_GetClusterEnergy() { return 0.0; }
void SimOutput(std::string, unsigned) {}
void ThrowException(std::string message) { throw std::invalid_argument(message); }

int main() {
    using namespace fake;
    // Machine counts, CPU families and operating systems are discovered dynamically.
    reset({machine(RISCV)});
    auto a = task(32, RISCV, LINUX_RT); arrive(a);
    assert(placements.count(a)); finish(a); SchedulerCheck(sim_time);
    assert(vms.empty()); SimulationComplete(sim_time);

    reset({machine(ARM), machine(POWER), machine(X86), machine(RISCV)});
    for (const auto& pair : std::vector<std::pair<CPUType_t, VMType_t>>{
             {ARM, WIN}, {POWER, AIX}, {X86, LINUX_RT}, {RISCV, LINUX}}) {
        const auto id = task(32, pair.first, pair.second); arrive(id);
        assert(machines.at(vms.at(placements.at(id)).machine_id).cpu == pair.first);
    }

    // Count each OS image's VM overhead; memory, rather than cores, limits admission.
    reset({machine(X86, 4)});
    a = task(58); auto b = task(58, X86, WIN); arrive(a); arrive(b);
    assert(placements.count(a) && !placements.count(b));
    sim_time = 100000; finish(a); assert(placements.count(b));
    finish(b); SchedulerCheck(sim_time); assert(vms.empty());

    // Reservations consume memory before asynchronous wake-up finishes.
    reset({machine(), machine(X86, 4)}, "best_fit");
    a = task(90); b = task(90); auto c = task(90);
    arrive(a); arrive(b); arrive(c);
    assert(placements.size() == 1 && transitions.at(1) == S1);
    transition(1); assert(transitions.at(1) == S0 && placements.size() == 1);
    transition(1); assert(placements.size() == 2 && !placements.count(c));
    finish(b); assert(placements.count(c));
    SchedulerCheck(sim_time); assert(!transitions.count(1)); // Never sleep a busy host.

    // Two pending tasks of the same OS share one reserved VM overhead.
    reset({machine(), machine(X86, 2)}, "best_fit");
    arrive(task(32)); b = task(60); c = task(60); arrive(b); arrive(c);
    transition(1); transition(1);
    assert(placements.count(b) && placements.count(c));
    assert(machines[1].memory_used == 128);

    // EDF admission selects the tighter deadline after a slot becomes available.
    reset({machine()});
    a = task(); b = task(32, X86, LINUX, 4000000);
    c = task(32, X86, LINUX, 1000000);
    arrive(a); arrive(b); arrive(c); finish(a);
    assert(placements.count(c) && !placements.count(b));

    // Aging also advances best-effort jobs in the admission queue itself.
    reset({machine()}); a = task();
    b = task(32, X86, LINUX, std::numeric_limits<Time_t>::max(), SLA3);
    c = task(32, X86, LINUX, 5000000, SLA1);
    arrive(a); arrive(b); arrive(c); sim_time = 1000000; finish(a);
    assert(placements.count(b) && !placements.count(c));

    // DVFS must protect every admitted deadline, including a new tight arrival.
    auto m = machine(X86, 2); m.p_states = {80, 24, 10, 4};
    m.s_states = {30, 25, 15, 10, 5, 1, 0};
    reset({m}); a = task(32, X86, LINUX, 5000000, SLA3); arrive(a);
    assert(machines[0].p_state != P0);
    b = task(32, X86, LINUX, 250000, SLA0); arrive(b);
    assert(machines[0].p_state == P0 && tasks[b].priority == HIGH_PRIORITY);

    // An aged best-effort task is promoted, even without a meaningful deadline.
    tasks[a].target_completion = 0; sim_time = 1000; SchedulerCheck(sim_time);
    assert(tasks[a].priority == LOW_PRIORITY);
    sim_time = 1000000; SchedulerCheck(sim_time); assert(tasks[a].priority == HIGH_PRIORITY);

    // Impossible requests and policy typos fail explicitly, without creating a VM.
    reset({machine()}); a = task(121);
    rejects([&] { arrive(a); }); assert(vms.empty());
    b = task(32, ARM); rejects([&] { arrive(b); });
    c = task(32, X86, AIX); rejects([&] { arrive(c); });
    rejects([&] { reset({machine()}, "typo"); });
    reset({}); a = task(); rejects([&] { arrive(a); });

    // Immediate callbacks and an empty simulation both remain valid.
    reset({machine(), machine()}, "best_fit");
    transition(1); synchronous = true;
    arrive(task()); b = task(); arrive(b); assert(placements.count(b));
    reset({machine()}); SimulationComplete(0);
    std::cout << "Scheduler behavior tests passed\n";
}
