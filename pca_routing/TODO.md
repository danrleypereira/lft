# pca_routing — open items

## Postponed

- **React PoC for the PCA graph visualization — now scoped as the class
  presentation demo, not a REIN console stepping stone.** Vite + React
  Router app, real RNP topology (reuse `graph.py::load_rnp_topology`, same
  27 nodes/44 edges, plotted on a Brazil map background rather than a
  force-directed layout), with:
  - a picker for a **source and target node**,
  - a side-by-side result panel showing each algorithm's path, cost, hops,
    and `comparisons`/`relaxations` counters (straight from `PathResult`) —
    for Dijkstra, Bellman-Ford, and BFS,
  - the chosen path for each algorithm overlaid on the map in its own color.

  **Refinement to build in from the start, not bolt on later:** a
  single (source, target) pair makes ILP and Dijkstra draw the *identical*
  path (per `FINDINGS.md`, ILP's per-target objective reduces to plain
  shortest path with only one flow) — so showing "5 algorithms" on one pair
  would visually undersell the whole point. Instead let the UI hold **two
  concurrent (source, target) pairs** on the same topology, with a toggle:
  "naive" (Dijkstra solved independently per pair — can overload a shared
  link) vs. "coordinated" (LP/ILP solved jointly over both). The two modes
  visibly diverge exactly where the pairs' paths would share a
  capacity-limited link — this is the live, visual version of
  `assignment/complexity/why-np-hard.md`'s argument, not just a prettier
  path-finder. Worth the extra scope: it's what actually proves the
  framework (LSP: same `find_path` call site, swap `PathFinder` subclass)
  *and* sells the advanced-scenario content to the class in one artifact.

  Doubled as the stack-validation step for `REIN/console/MIGRATION-PLAN.md`'s
  Phase 0 (the "RNP Backbone Atlas" artifact —
  https://claude.ai/artifact/ECnXExrjP8j6B3enD3pPpA — already prototypes the
  map/interaction side in plain JS+D3; porting it to React+Router was that
  plan, still true, just no longer the primary reason to build this).
  **Postponed 2026-10-15** — not urgent for the graded deliverable itself
  (the assignment doesn't require a UI); picked up next once the report/
  slides text itself is written.

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
