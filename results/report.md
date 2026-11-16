# Benchmark results

108 runs; 9 scenarios; 3 seeds per scenario; baseline: `round_robin`.

SLA limits (max share of tasks missing their deadline): SLA0 5%, SLA1 10%, SLA2 20%. A cell passes only if every seed passes. Savings are paired by scenario and seed.

## Energy saved vs `round_robin`

| Policy | diurnal | hetero_gpu | long_idle | low | mem_pressure | power_aix | sample | slack_mix | surge | Mean |
|---|---|---|---|---|---|---|---|---|---|---|
| best_fit | +25.6% | +13.7% | +27.4% | +22.6% | +18.4% | +17.5% | +16.1% | +14.0% | +15.6% | +19.0% |
| min_power | +25.7% | +13.7% | +27.4% | +22.6% | +18.4% | +17.5% | +16.1% | +14.0% | +15.6% | +19.0% |
| deadline_energy | +25.7% | +13.8% | +27.4% | +22.6% | +18.4% | +17.5% | +16.1% | +14.0% | +15.6% | +19.0% |

`*` = saved energy but violated an SLA.

## Detail

| Scenario | Policy | Energy kWh mean [min-max] | Saved vs base | Sim s | Slower | SLA0/1/2 worst % | SLA | Wake | Queued |
|---|---|---|---|---|---|---|---|---|---|
| diurnal | round_robin | 0.09443 [0.09316-0.09591] | +0.0% | 52.5 | +0.0% | 0.0/0.0/0.0 | pass | 0 | 0 |
| diurnal | best_fit | 0.07028 [0.06932-0.07143] | +25.6% | 52.5 | +0.0% | 0.0/0.0/0.0 | pass | 11 | 0 |
| diurnal | min_power | 0.07013 [0.06918-0.07124] | +25.7% | 52.5 | +0.0% | 0.0/0.0/0.0 | pass | 14 | 0 |
| diurnal | deadline_energy | 0.07021 [0.06927-0.07132] | +25.7% | 52.5 | +0.0% | 0.0/0.0/0.0 | pass | 13 | 0 |
| hetero_gpu | round_robin | 0.00953 [0.00948-0.00958] | +0.0% | 4.8 | +0.0% | 0.0/0.0/0.0 | pass | 0 | 0 |
| hetero_gpu | best_fit | 0.00822 [0.00818-0.00827] | +13.7% | 5.0 | +5.0% | 0.0/0.0/0.0 | pass | 19 | 0 |
| hetero_gpu | min_power | 0.00822 [0.00818-0.00827] | +13.7% | 5.0 | +5.0% | 0.0/0.0/0.0 | pass | 19 | 0 |
| hetero_gpu | deadline_energy | 0.00821 [0.00818-0.00826] | +13.8% | 5.0 | +5.0% | 0.0/0.0/0.0 | pass | 19 | 0 |
| long_idle | round_robin | 0.22223 [0.22050-0.22412] | +0.0% | 126.1 | +0.0% | 0.0/0.0/0.0 | pass | 0 | 0 |
| long_idle | best_fit | 0.16143 [0.16017-0.16281] | +27.4% | 126.1 | +0.0% | 0.0/0.0/0.0 | pass | 0 | 0 |
| long_idle | min_power | 0.16143 [0.16017-0.16281] | +27.4% | 126.1 | +0.0% | 0.0/0.0/0.0 | pass | 0 | 0 |
| long_idle | deadline_energy | 0.16143 [0.16017-0.16281] | +27.4% | 126.1 | +0.0% | 0.0/0.0/0.0 | pass | 0 | 0 |
| low | round_robin | 0.00566 [0.00555-0.00576] | +0.0% | 3.2 | +0.0% | 0.0/0.0/0.0 | pass | 0 | 0 |
| low | best_fit | 0.00438 [0.00425-0.00456] | +22.6% | 3.3 | +5.0% | 0.0/0.0/0.0 | pass | 1 | 0 |
| low | min_power | 0.00438 [0.00425-0.00456] | +22.6% | 3.3 | +5.0% | 0.0/0.0/0.0 | pass | 1 | 0 |
| low | deadline_energy | 0.00438 [0.00425-0.00456] | +22.6% | 3.3 | +5.0% | 0.0/0.0/0.0 | pass | 1 | 0 |
| mem_pressure | round_robin | 0.00745 [0.00723-0.00757] | +0.0% | 4.0 | +0.0% | 0.0/0.0/0.0 | pass | 0 | 0 |
| mem_pressure | best_fit | 0.00608 [0.00595-0.00620] | +18.4% | 4.2 | +5.5% | 0.0/0.0/0.0 | pass | 10 | 0 |
| mem_pressure | min_power | 0.00608 [0.00595-0.00620] | +18.4% | 4.2 | +5.5% | 0.0/0.0/0.0 | pass | 10 | 0 |
| mem_pressure | deadline_energy | 0.00608 [0.00595-0.00620] | +18.4% | 4.2 | +5.5% | 0.0/0.0/0.0 | pass | 10 | 0 |
| power_aix | round_robin | 0.00741 [0.00724-0.00752] | +0.0% | 3.4 | +0.0% | 0.0/0.0/0.0 | pass | 0 | 0 |
| power_aix | best_fit | 0.00611 [0.00600-0.00617] | +17.5% | 3.7 | +8.1% | 0.0/0.0/0.0 | pass | 5 | 0 |
| power_aix | min_power | 0.00611 [0.00600-0.00617] | +17.5% | 3.7 | +8.1% | 0.0/0.0/0.0 | pass | 5 | 0 |
| power_aix | deadline_energy | 0.00611 [0.00600-0.00617] | +17.5% | 3.7 | +8.1% | 0.0/0.0/0.0 | pass | 5 | 0 |
| sample | round_robin | 0.00723 [0.00663-0.00795] | +0.0% | 3.7 | +0.0% | 0.0/0.0/0.0 | pass | 0 | 2 |
| sample | best_fit | 0.00605 [0.00576-0.00661] | +16.1% | 3.9 | +4.4% | 0.0/0.0/0.0 | pass | 15 | 2 |
| sample | min_power | 0.00605 [0.00576-0.00661] | +16.1% | 3.9 | +4.4% | 0.0/0.0/0.0 | pass | 15 | 2 |
| sample | deadline_energy | 0.00605 [0.00576-0.00661] | +16.1% | 3.9 | +4.4% | 0.0/0.0/0.0 | pass | 15 | 2 |
| slack_mix | round_robin | 0.01022 [0.00971-0.01086] | +0.0% | 5.3 | +0.0% | 0.0/0.0/0.0 | pass | 0 | 14 |
| slack_mix | best_fit | 0.00878 [0.00820-0.00913] | +14.0% | 5.7 | +7.5% | 0.0/0.0/0.0 | pass | 15 | 18 |
| slack_mix | min_power | 0.00878 [0.00820-0.00913] | +14.0% | 5.7 | +7.5% | 0.0/0.0/0.0 | pass | 15 | 18 |
| slack_mix | deadline_energy | 0.00878 [0.00820-0.00913] | +14.0% | 5.7 | +7.5% | 0.0/0.0/0.0 | pass | 15 | 18 |
| surge | round_robin | 0.01006 [0.00999-0.01010] | +0.0% | 5.2 | +0.0% | 0.0/0.0/0.0 | pass | 0 | 52 |
| surge | best_fit | 0.00849 [0.00845-0.00853] | +15.6% | 5.4 | +4.6% | 0.0/0.0/0.0 | pass | 15 | 52 |
| surge | min_power | 0.00849 [0.00845-0.00853] | +15.6% | 5.4 | +4.6% | 0.0/0.0/0.0 | pass | 15 | 52 |
| surge | deadline_energy | 0.00849 [0.00845-0.00853] | +15.6% | 5.4 | +4.6% | 0.0/0.0/0.0 | pass | 15 | 52 |

## Caveats

- 'best_fit' and 'min_power' are identical on 24/27 runs.
- No SLA violations anywhere: scenarios may be too easy to test SLA compliance.
- DVFS never fired in any run (dvfs_changes = 0 everywhere).
- No memory warnings in any run; memory pressure is not being exercised.
