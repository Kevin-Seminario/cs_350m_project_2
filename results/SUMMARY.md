# Measured results

Main study: three seed offsets (0, 101, 202). Energies are mean ± sample standard deviation in Wh. Wall times are machine-dependent.

| Workload | Policy | Energy (Wh) | Mean response (s) | Makespan (s) | Wall (s) |
|---|---|---:|---:|---:|---:|
| Low intensity | round_robin | 3.348744 ± 0.152572 | 0.104031 | 13.420000 | 0.002547 |
| Low intensity | best_fit | 1.582255 ± 0.073118 | 0.104031 | 13.420000 | 0.003705 |
| Low intensity | min_power | 1.582255 ± 0.073118 | 0.104031 | 13.420000 | 0.003685 |
| Low intensity | deadline_energy | 1.582255 ± 0.073118 | 0.104031 | 13.420000 | 0.004049 |
| Surge | round_robin | 5.989009 ± 0.117773 | 0.730479 | 12.560000 | 0.015511 |
| Surge | best_fit | 4.491497 ± 0.194606 | 0.908638 | 12.560000 | 0.016856 |
| Surge | min_power | 4.486586 ± 0.194704 | 0.908404 | 12.560000 | 0.015784 |
| Surge | deadline_energy | 4.483684 ± 0.188447 | 0.908963 | 12.560000 | 0.028209 |
| Heterogeneous | round_robin | 5.318512 ± 0.073945 | 0.225288 | 12.640000 | 0.013407 |
| Heterogeneous | best_fit | 3.676579 ± 0.051513 | 0.246177 | 12.680000 | 0.013842 |
| Heterogeneous | min_power | 3.634157 ± 0.048239 | 0.255376 | 12.680000 | 0.014454 |
| Heterogeneous | deadline_energy | 3.685793 ± 0.015514 | 0.247350 | 12.720000 | 0.027346 |
| Memory pressure | round_robin | 0.806290 ± 0.032708 | 0.809842 | 7.340000 | 0.004064 |
| Memory pressure | best_fit | 0.800068 ± 0.027715 | 0.940236 | 7.500000 | 0.004511 |
| Memory pressure | min_power | 0.800068 ± 0.027715 | 0.940236 | 7.500000 | 0.004493 |
| Memory pressure | deadline_energy | 0.800068 ± 0.027715 | 0.940236 | 7.500000 | 0.006798 |
| DVFS slack | round_robin | 2.252262 ± 0.041802 | 0.396501 | 15.640000 | 0.007833 |
| DVFS slack | best_fit | 1.861490 ± 0.048188 | 0.402711 | 15.640000 | 0.007544 |
| DVFS slack | min_power | 1.858906 ± 0.043880 | 0.402711 | 15.640000 | 0.007364 |
| DVFS slack | deadline_energy | 0.832018 ± 0.011852 | 0.669315 | 15.820000 | 0.015042 |
| NiceAndSmooth | round_robin | 11.923227 ± 0.155635 | 0.434830 | 16.080000 | 0.006692 |
| NiceAndSmooth | best_fit | 8.533711 ± 0.233877 | 0.332062 | 15.820000 | 0.012232 |
| NiceAndSmooth | min_power | 8.533711 ± 0.233877 | 0.332062 | 15.820000 | 0.012357 |
| NiceAndSmooth | deadline_energy | 8.964555 ± 0.292324 | 0.736252 | 16.400000 | 0.020202 |
| SpikeyNefarious | round_robin | 11.350285 ± 0.228445 | 0.652796 | 15.820000 | 0.030175 |
| SpikeyNefarious | best_fit | 9.723085 ± 0.158370 | 0.757503 | 15.820000 | 0.032334 |
| SpikeyNefarious | min_power | 9.714485 ± 0.149509 | 0.757494 | 15.820000 | 0.032219 |
| SpikeyNefarious | deadline_energy | 9.710285 ± 0.142592 | 0.756423 | 15.820000 | 0.068088 |

All 84 main-study runs report zero SLA misses and memory warnings. Per-class population counts and normalized response/deadline ratios are in the CSV.

Extended study: supplied seeds unchanged; see `extended.csv` and `day.csv`. TallShort exceeds the SLA0 allowance for every policy. No result was removed.
