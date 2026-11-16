#!/bin/bash

make all
python3 tools/gen_inputs.py
python3 tools/run_matrix.py --provided input_files/provided --label after --timeout 900 --out results/runs/after.csv
python3 tools/run_matrix.py --provided input_files/provided --label after_deep --timeout 900 \
    --env SCHED_DWELL_US=1000000 --out results/runs/after_deep.csv
python3 tools/report.py results/runs/after_deep.csv --compare results/runs/before.csv
python3 tools/make_addendum.py --before results/runs/before.csv --after results/runs/after.csv \
    --deep results/runs/after_deep.csv
pdflatex -interaction=nonstopmode -halt-on-error report.tex   # run twice; needs pdfLaTeX
