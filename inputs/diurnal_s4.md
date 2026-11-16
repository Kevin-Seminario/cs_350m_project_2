machine class:
{
        Number of machines: 16
        CPU type: X86
        Number of cores: 8
        Memory: 16384
        S-States: [120, 100, 100, 80, 40, 10, 0]
        P-States: [12, 8, 6, 4]
        C-States: [12, 3, 1, 0]
        MIPS: [1000, 800, 600, 400]
        GPUs: yes
}
machine class:
{
        Number of machines: 24
        CPU type: ARM
        Number of cores: 16
        Memory: 16384
        S-States: [120, 100, 100, 80, 40, 10, 0]
        P-States: [12, 8, 6, 4]
        C-States: [12, 3, 1, 0]
        MIPS: [1000, 800, 600, 400]
        GPUs: yes
}
task class:
{
        Start time: 60000
        End time: 10000000
        Inter arrival: 400000
        Expected runtime: 2000000
        Memory: 8
        VM type: LINUX
        GPU enabled: no
        SLA type: SLA1
        CPU type: X86
        Task type: WEB
        Seed: 4001
}
task class:
{
        Start time: 10060000
        End time: 20000000
        Inter arrival: 150000
        Expected runtime: 2000000
        Memory: 8
        VM type: LINUX
        GPU enabled: no
        SLA type: SLA1
        CPU type: X86
        Task type: WEB
        Seed: 4008
}
task class:
{
        Start time: 20060000
        End time: 30000000
        Inter arrival: 40000
        Expected runtime: 2000000
        Memory: 8
        VM type: LINUX
        GPU enabled: no
        SLA type: SLA1
        CPU type: X86
        Task type: WEB
        Seed: 4015
}
task class:
{
        Start time: 30060000
        End time: 40000000
        Inter arrival: 150000
        Expected runtime: 2000000
        Memory: 8
        VM type: LINUX
        GPU enabled: no
        SLA type: SLA1
        CPU type: X86
        Task type: WEB
        Seed: 4022
}
task class:
{
        Start time: 40060000
        End time: 50000000
        Inter arrival: 400000
        Expected runtime: 2000000
        Memory: 8
        VM type: LINUX
        GPU enabled: no
        SLA type: SLA1
        CPU type: X86
        Task type: WEB
        Seed: 4029
}
