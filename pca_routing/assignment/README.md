# assignment/

Everything needed to write the report and slides, gathered in one place —
not the report or slides themselves yet ("after we finish everything" per
the plan). Code lives in `pca_routing/`, one level up; this folder is pure
report material.

| Folder | What's in it |
|---|---|
| `data/` | The two worked instances (`diamond_instance.md`, `rnp_instance.md`, hand-traced) + `scaling.csv` (the execution-time experiment's raw output) |
| `complexity/` | `complexity-table.md` — best/worst/average case derived from the actual code, not a textbook quote |
| `figures/` | `make_plots.py` (regenerate anytime: `.venv/bin/python -m pca_routing.assignment.figures.make_plots`) + the 3 PNGs it produces |
| `report/` | `report.tex` (structure only, every section has a TODO + pointer to its source material) + `refs.bib` |
| `slides/` | `outline.md` — slide-by-slide skeleton, same section order as the report |

Regenerate `data/scaling.csv` and the figures together:

```bash
.venv/bin/python -m pca_routing.experiment
.venv/bin/python -m pca_routing.assignment.figures.make_plots
cp pca_routing/results/scaling.csv pca_routing/assignment/data/scaling.csv
```
