# pca_routing — design notes

Coursework for "Design and Complexity of Algorithms" (PCA), built on top of
this project's own topology data. Kept fully standalone from `profissa_lft`/
`onos_topologies` on purpose — see "Scope" below.

## The problem

Given `G = (V, E)` with edge cost `w(u, v)`, find the minimum-cost path from
`s` to `t`.

| Role | Algorithm | Literature | Technique |
|---|---|---|---|
| Main algorithm | **Dijkstra** | Dijkstra, 1959 | Greedy / graph algorithm |
| Required comparison | **Bellman-Ford** | Bellman, 1958 | Dynamic programming / repeated relaxation |
| Extra baseline | **BFS / hop count** | Moore, 1959 | Graph traversal |

Full citations: `/home/tupan/Documents/PCA/literature-references.md`.

### Why Dijkstra vs. Bellman-Ford, not BFS vs. Dijkstra

The first instinct (and the user's own original PCA idea) was BFS vs.
Dijkstra. That's a good *networking* experiment but a weaker *algorithms
assignment*, because BFS minimizes hop count and Dijkstra minimizes summed
weight — two different objective functions, not two solutions to the same
problem. A grader can reasonably object: "these solve different problems."
Dijkstra and Bellman-Ford both solve *minimum-weight path*, so they must
agree on cost for every positive-weight instance — that agreement is a
built-in correctness oracle (`experiment.check_correctness`), and if it ever
fails, an implementation has a bug, not "a different answer." BFS is kept as
a third, explicitly-labeled baseline, not the graded comparison — it's the
literature anchor for this project's own `fwd` experiment mode (ONOS's
reactive forwarding computes shortest paths by hop count by default).

## Liskov Substitution Principle, applied directly

`algorithms/base.py` defines one abstract contract, `PathFinder`. All three
algorithms implement it, and nothing outside `algorithms/` ever imports a
concrete class except the single selection list in `experiment.py`:

```
experiment.py:25   ALGORITHMS = [DijkstraPathFinder(), BellmanFordPathFinder(), BFSPathFinder()]
experiment.py:40   return algo.find_path(graph, source, target)   # <- the one polymorphic call site
```

Everything downstream of that call (`run_suite`, `print_suite`,
`scaling_experiment`) is written once, against `PathFinder`, and is
identical no matter which three classes `ALGORITHMS` holds. Concretely, the
contract both directions of substitutability require:

- **Precondition, not strengthened by any subclass**: a `Graph`, a `source`
  and a `target` node id — nothing more. `supports_negative_weights` is
  `False` on the base class and on Dijkstra/BFS, `True` on Bellman-Ford; no
  caller here depends on negative-weight support (every real weight used —
  delay in ms, 1/capacity — is non-negative), so this is documented rather
  than load-bearing, but it's the one place the three honestly differ.
- **Postcondition, guaranteed by every subclass**: always returns a
  `PathResult`, never raises on "no path"; `path` starts at `source` and
  ends at `target` when reachable; **`cost` is always the sum of edge
  weights along `path`**, computed identically for all three
  (`graph.path_weight`) — including BFS, whose own search criterion is hop
  count, not weight. Without that last rule, BFS's `.cost` would silently
  mean something different from the other two, and a caller comparing
  `.cost` across algorithms would be comparing two different quantities
  while believing they were the same one — exactly the kind of postcondition
  violation LSP forbids.

`tests/test_algorithms.py::TestLSPConformance` tests this directly: one test
function, run against all three classes via `subTest`, asserting the shared
postconditions — not "does Dijkstra work" and "does BFS work" as separate
tests, but "does every `PathFinder` honor the contract."

## File layout

```
pca_routing/
├── graph.py                  Graph (adjacency list) + loaders (diamond, rnp, random)
├── algorithms/
│   ├── base.py                PathFinder (ABC) + PathResult — the LSP contract
│   ├── dijkstra.py             array-based, Θ(V²)
│   ├── bellman_ford.py          repeated relaxation + early termination
│   └── bfs.py                   hop-count baseline
├── experiment.py              the ONE selection point (ALGORITHMS, line 25) + the suite runner
├── tests/test_algorithms.py   unit tests, incl. LSP conformance
└── results/scaling.csv        output of the growing-|V| timing experiment
```

Maps directly onto the assignment's required split: `graph.py` +
`algorithms/` = "Algorithm", `experiment.py` = "Experiment".

## The test instances

- **`load_diamond_topology()`** — the 4-PoP diamond (ES, MG, RJ, SP), small
  enough to work through by hand in the report. Edge weights are the **real**
  per-link delays `diamond_topology/main.py`'s own `prio_links` applies
  (ES↔MG 10ms, ES↔RJ 30ms — the static bottleneck, MG↔SP 10ms, RJ↔SP 10ms) —
  not `diamond_topology/constants.py`'s `CONFIG`, which is a single uniform
  10ms/35mbit for every link before any experiment-specific `tc` rules run.
- **`load_rnp_topology()`** — the real 30-node RNP backbone
  (`rnp_topology/constants.py`), weight = `1/capacity_gbit` by default
  (`cost="capacity"` and `cost="hops"` also available). This is a **cost**,
  not a latency — the dataset ships no per-link delay matrix, only capacity,
  and the report must not call it latency.
- **`random_graph(n, ...)`** — random connected graphs of controlled size,
  for `scaling_experiment` (`sizes=[10, 20, 30, 50, 100, 200, 500]` in
  `experiment.main()`), since on the 4- or 30-node real graphs the measured
  runtime is mostly Python call overhead, not algorithmic work.

## Complexity (for the implementation actually here — not a textbook quote)

| Algorithm | Implementation model | Best case | Worst case |
|---|---|---:|---:|
| Dijkstra | array/linear-scan selection (no heap) | Θ(V) (`s == t`: one scan, zero relaxations — not Θ(1), the scan never shrinks) | Θ(V²) |
| Bellman-Ford | edge-list relaxation, early termination | Θ(E) (converges pass 1) | Θ(VE) |
| BFS | adjacency-list traversal | Θ(1) (`s == t`) | Θ(V+E) |

Full best/worst/average-case derivation, including why Dijkstra's floor is
Θ(V) and not Θ(1): `assignment/complexity/complexity-table.md`.

Dijkstra is deliberately **not** heap-based for the base comparison: it gives
a single, unconditional Θ(V²), with no data-structure argument needed, which
is a cleaner story for the report than "O(E log V), unless..." . A
binary-heap version (`O((V+E) log V)`) is a natural "optimization" subsection
to add afterward, not required for the graded comparison.

`PathResult.comparisons` / `.relaxations` / `.nodes_visited` count the actual
operations each run performed — this is the "algorithmic work" evaluation
the report should lead with, since on small graphs wall-clock time
(`.elapsed_ns`) is mostly noise; `scaling_experiment` is what makes the
asymptotic difference show up in real numbers.

## What this is not (yet)

Connecting a computed path to the *live* testbed (install the route, run
real `ping`/`iperf`, check the predicted cost against what was actually
measured) is a separate, later piece of work — see the "Phase 2" note in the
conversation this came out of. It needs `lft-vm` up and ONOS running, and is
deliberately kept out of the graded deliverable: this package never imports
`profissa_lft`, `onos_topologies`, Docker, or ONOS — only the plain topology
*data* in the `constants.py` files, read via `importlib` so no package
import chain (and its `docker`/`paramiko` dependencies) is pulled in just to
read three tuples.

## Scope note

This lives on a local/personal branch (`pca/routing-algorithms`, off
`chore/uv-kvm-migration`) in the shared `lft` repo, since this course's
project is itself under the research group's professor. It is still a
graded, individually-written deliverable — see the assignment's own
independent-work rule in `/home/tupan/Documents/PCA/Trabalho_de_PCA-2.pdf`
§5.
