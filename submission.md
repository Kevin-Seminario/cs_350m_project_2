# Cloud Management for Energy and Performance — submission

Repository: [Kevin-Seminario/cs_350m_project_2](https://github.com/Kevin-Seminario/cs_350m_project_2)

| Branch to grade | Algorithm |
|---|---|
| [algorithm-round-robin](https://github.com/Kevin-Seminario/cs_350m_project_2/tree/algorithm-round-robin) | Capacity-aware round robin |
| [algorithm-best-fit](https://github.com/Kevin-Seminario/cs_350m_project_2/tree/algorithm-best-fit) | Best-fit consolidation |
| [algorithm-min-power](https://github.com/Kevin-Seminario/cs_350m_project_2/tree/algorithm-min-power) | Online minimum incremental power, adapted from MBFD |
| [algorithm-deadline-energy](https://github.com/Kevin-Seminario/cs_350m_project_2/tree/algorithm-deadline-energy) | Deadline-aware execution-energy placement and DVFS |

For each branch:

```sh
make all
./simulator input_files/custom/03_surge
```

Each grading branch selects its algorithm automatically; no environment variable
is required. `ALGORITHM.md` identifies the algorithm and `make test` verifies it.
The comparison report is `report_updated.pdf`, with its editable source in
`report_updated.tex`. Deep sleep is an optional experiment and is disabled for the
four graded configurations.

Grade the four branches listed above. `main`, `attempt-one`, and `update_latex`
contain repository history and comparative development work.
