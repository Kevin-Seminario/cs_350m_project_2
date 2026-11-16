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
        End time: 800000
        Inter arrival: 12000
        Expected runtime: 2000000
        Memory: 8
        VM type: LINUX
        GPU enabled: no
        SLA type: SLA0
        CPU type: X86
        Task type: WEB
        Seed: 4001
}
task class:
{
        Start time: 60000
        End time: 800000
        Inter arrival: 8000
        Expected runtime: 3000000
        Memory: 8
        VM type: LINUX
        GPU enabled: no
        SLA type: SLA2
        CPU type: ARM
        Task type: WEB
        Seed: 4008
}
task class:
{
        Start time: 60000
        End time: 800000
        Inter arrival: 20000
        Expected runtime: 1000000
        Memory: 8
        VM type: LINUX
        GPU enabled: no
        SLA type: SLA3
        CPU type: X86
        Task type: WEB
        Seed: 4015
}
task class:
{
        Start time: 60000
        End time: 800000
        Inter arrival: 15000
        Expected runtime: 4000000
        Memory: 8
        VM type: LINUX
        GPU enabled: yes
        SLA type: SLA1
        CPU type: X86
        Task type: AI
        Seed: 4022
}
