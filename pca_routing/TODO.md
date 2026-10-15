# pca_routing — open items

## Done

- **React PoC for the PCA graph visualization, scoped as the class
  presentation demo.** Done 2026-10-15, branch `pca/react-poc` @ `15cf019`
  (fork only, no PR/issue). `pca_routing/web/`: Vite + React Router, TS ports
  of Dijkstra/Bellman-Ford/BFS verified against the Python originals over all
  351 RNP pairs (`src/lib/lib.test.ts`, 1055 vitest cases — `tsc --noEmit` and
  `vite build` both clean, independently re-run and confirmed, not just taken
  on the builder's word). Two tabs: **Algorithms** (one pair, all three
  algorithms side by side with cost/hops/comparisons/relaxations, each path
  its own color) and **Two flows** (two concurrent demand-bearing pairs,
  naive-Dijkstra-per-pair vs. an exact coordinated joint allocator —
  `src/lib/joint.ts` enumerates simple paths and picks the capacity-respecting
  pair minimizing total cost, the true unsplittable-two-commodity optimum for
  graphs this size, not an LP relaxation). Default demo (AL→SP + DF→SP,
  60 Mbit each): naive overloads link DF–SP (capacity 20); coordinated
  reroutes flow B via MG–RJ, +10.5 ms, feasible. Run: `cd pca_routing/web &&
  npm i && npm run dev`.
  Open: per-member contribution note aside, this closes the "prove the
  framework to the class" goal from `FINDINGS.md`/`why-np-hard.md` — the
  naive/coordinated divergence is the live version of the NP-hardness
  argument, not just a prettier path-finder.

  Doubled as the stack-validation step for `REIN/console/MIGRATION-PLAN.md`'s
  Phase 0 (the "RNP Backbone Atlas" artifact —
  https://claude.ai/artifact/ECnXExrjP8j6B3enD3pPpA — prototyped the
  map/interaction side in plain JS+D3 first; this is the React+Router port).

## Not yet done (tracked in `DESIGN.md` already, repeated here for visibility)

- Phase 2: wire a computed `PathResult` into the *live* `lft-vm` testbed —
  install the path, run real `ping`/`iperf`, compare predicted vs. measured.
  Needs `lft-vm` up and ONOS running; deliberately kept separate from the
  graded code (`pca_routing/` imports nothing from `profissa_lft`/
  `onos_topologies` on purpose).
- `assignment/report/report.tex` + `report.pdf`: done (branch `pca/report`,
  full content, group authorship) — one open item inside it,
  `% TODO(group)` for the per-member contribution breakdown, needs the
  group's own input, not a guess.
- Slides (`assignment/slides/outline.md`) content — still structure/pointers
  only, deliberately left for after the report/HTML/demo are reviewed.
- Optional: a binary-heap Dijkstra (`O((V+E) log V)`) as a documented
  "optimization" subsection, once the base Θ(V²) comparison is written up.
