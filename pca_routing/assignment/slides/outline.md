# Slide outline (skeleton — content TODO, structure fixed)

Matches the report's own section order so the deck and the report never
disagree on the story. One slide per bullet below unless noted; source
material pointers are what to pull onto each slide, not what to say.

1. **Cover** — problem name, group members. Same title as `report.tex`.
2. **The problem** — one line: minimum-cost path on a weighted graph.
   `DESIGN.md` → "The problem".
3. **Why these three algorithms** — the BFS-vs-Dijkstra → Dijkstra-vs-Bellman-Ford
   pivot, in one slide: BFS optimizes hop count, Dijkstra/Bellman-Ford optimize
   summed weight → not the same problem → the graded comparison needs two
   solutions to the *same* problem. `DESIGN.md` → "Why Dijkstra vs.
   Bellman-Ford, not BFS vs. Dijkstra".
4. **The literature** — three citations, three one-line summaries
   (Bellman 1958, Dijkstra 1959, Moore 1959). `literature-references.md`.
5. **Design technique** — greedy (Dijkstra) vs. dynamic programming
   (Bellman-Ford), side by side.
6. **Liskov Substitution in this code** — the actual payoff slide: show
   `experiment.py:25` (`ALGORITHMS = [...]`) and `experiment.py:40`
   (`algo.find_path(...)`) side by side, one slide, make the point that
   swapping an algorithm is a one-line change.
7. **Worked instance (diamond)** — the 4-node graph diagram + Dijkstra's
   `dist[]` table, pass by pass. `data/diamond_instance.md` has the full
   trace already written out; this slide is a visual compression of it.
8. **Real instance (RNP, 27 nodes)** — the RJ→RR query, real measured RTT:
   BFS's 3-hop path is 47% *slower* than Dijkstra/Bellman-Ford's 4-hop one
   (144ms vs. 98ms) — disagreement on a REAL topology, not a toy example.
   `data/rnp_instance.md`.
9. **Complexity** — the summary table (`complexity/complexity-table.md`),
   plus the one genuinely interesting finding: Dijkstra's best case is
   Θ(V), not Θ(1) — worth a slide of its own since it was wrong in an
   earlier draft and only caught by checking the actual code.
10. **Results** — `figures/comparisons_vs_n.png` (or `time_vs_n.png`),
    one chart, the Θ(V²) vs. the other two visibly separating.
11. **Correctness oracle** — Dijkstra.cost == Bellman-Ford.cost holds on
    every instance tested (`tests/test_algorithms.py`); frame this as a
    *result*, not a testing footnote — it's evidence the two
    implementations are correct relative to each other.
11a. **Validated live, not just on paper** — pulled the real running
    topology straight from REIN's console API (`GET /api/testbed`) while an
    actual `rnp` experiment was up in the isolated VM - ONOS, 27 switches,
    deployer and supervisor all live - and ran all three algorithms against
    it with *zero code changes*, only a new loader. Found an even subtler
    divergence than the static example: BA→RJ ties at 2 hops either way,
    but BFS's tied pick costs 2.4× more (35ms vs. 14.43ms) — hop count alone
    can't even break its own ties well. `FINDINGS.md` → "Live-data
    validation".
12. **Real-world application** — this isn't a toy problem: REIN (the real
    IBN research project this data comes from) has an open issue asking for
    exactly this function, and its current solver turns out to be
    *mathematically equivalent*, per-client, to what `DijkstraPathFinder`
    already computes — just via a much heavier ILP solver. `FINDINGS.md` →
    "The actual finding".
13. **Advanced scenario — where Dijkstra stops being a good fit** — the
    honest limit, presented as a feature of understanding the problem, not
    a weakness of the work: route ONE client at a time and Dijkstra is
    provably right; route MANY clients sharing the same links and
    independent Dijkstra calls can saturate one link while others sit idle
    (show the "10 clients, same best path" case from `FINDINGS.md`'s
    advanced-scenario section). This is unsplittable multi-commodity flow —
    NP-hard, genuinely needs ILP (or a heuristic), not a shortcoming of this
    implementation. Also the LSP payoff, stated explicitly: this new
    problem does NOT become a fourth `PathFinder` subclass (different
    signature, different return shape) — it's a separate interface one
    level up, exactly the discipline `algorithms/base.py` already argues
    for.
13a. **Why this is provably hard, not just "harder"** — the precise CS
    result, not a hand-wave: Even, Itai & Shamir (1976) proved the
    *integral* two-commodity flow problem is NP-complete with as few as
    TWO commodities; the *splittable* (fractional) version of the exact
    same problem is a linear program — solvable in polynomial time. One
    requirement (a client's traffic must be ONE undivided path) is the
    entire reason the problem leaves P. Tie this to why Dijkstra
    specifically can't be patched: its greedy-choice proof needs every
    edge weight fixed and decision-independent before it starts; a second
    commodity's choice makes an edge's effective availability depend on a
    decision made *during* the same solve — exactly the assumption the
    proof relies on. Full writeup: `assignment/complexity/why-np-hard.md`
    (also delivered as a standalone PDF). Close with the general lesson:
    sharing one resource across otherwise-independent subproblems is what
    moves a problem between complexity classes — not problem size, not a
    messier cost function.
14. **Conclusion** — what was learned, what was hard. Last slide.

## Format

Not decided yet — Beamer (pairs with `report.tex`'s LaTeX) or a plain
Markdown deck are both reasonable; pick once the report's own visual style
is settled, so the two don't diverge.
