# pca_routing — open items

## Postponed

- **React PoC for the PCA graph visualization.** Was going to be a small
  Vite + React Router app visualizing `graph.py`'s diamond/RNP topologies
  and the BFS/Dijkstra/Bellman-Ford comparison (the "RNP Backbone Atlas"
  artifact already prototypes the visual/interaction side of this in plain
  JS+D3 — https://claude.ai/artifact/ECnXExrjP8j6B3enD3pPpA — porting that to
  React+Router was the plan). Doubled as the stack-validation step for
  `REIN/console/MIGRATION-PLAN.md`'s Phase 0.
  **Postponed 2026-10-15** — not urgent for the graded deliverable itself
  (the assignment doesn't require a UI), picked back up whenever the console
  migration actually starts.

## Not yet done (tracked in `DESIGN.md` already, repeated here for visibility)

- Phase 2: wire a computed `PathResult` into the *live* `lft-vm` testbed —
  install the path, run real `ping`/`iperf`, compare predicted vs. measured.
  Needs `lft-vm` up and ONOS running; deliberately kept separate from the
  graded code (`pca_routing/` imports nothing from `profissa_lft`/
  `onos_topologies` on purpose).
- Writing the actual report (`assignment/report/report.tex`) and slides
  (`assignment/slides/outline.md`) content — currently structure/pointers
  only, see each file's own TODOs.
- Optional: a binary-heap Dijkstra (`O((V+E) log V)`) as a documented
  "optimization" subsection, once the base Θ(V²) comparison is written up.
