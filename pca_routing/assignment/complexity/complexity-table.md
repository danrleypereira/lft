# Complexity analysis (report-ready)

Analysis of the actual implementations in `pca_routing/algorithms/`, not a
textbook quote — the assignment specifically grades "complexity calculated
correctly" against *this* code, and the complexity of Dijkstra in particular
depends entirely on which data structure selects the next node.

## Dijkstra (`algorithms/dijkstra.py`) — array/linear-scan selection

```
for _ in range(|V|):            # V iterations
    scan all nodes for min dist  # Θ(V) per iteration
    relax its neighbors          # Θ(deg(u)) per iteration, sums to Θ(E) overall
```

- **Best case**: Θ(V), not Θ(1). Reached only when `source == target`: the
  first scan always picks `source` (it's the only node with finite distance
  before any relaxation happens), and the implementation breaks immediately
  after marking it visited, *before* relaxing its neighbors (`dijkstra.py`:
  the `if u == target: break` comes before the relaxation loop). So the
  absolute floor is exactly one full Θ(V) scan and zero relaxations —
  confirmed empirically: on a 2-node graph, `find_path(g, "A", "A")` reports
  `comparisons=2, relaxations=0`. The scan never shrinks based on what's
  already settled, so even the cheapest possible query still costs Θ(V),
  not Θ(1).
- **Worst case**: Θ(V²). Reached when `target` is the last node settled
  (the farthest reachable node, or `target` unreachable so the outer loop
  runs until no unvisited node has finite distance): all V iterations run,
  each paying its Θ(V) scan. Since E ≤ V(V−1)/2 = O(V²) for *any* simple
  graph, the total relaxation work never exceeds the scan cost — Θ(V²) is
  the bound regardless of how sparse the graph actually is, not just "once
  E is large."
- **Average case**: Θ(V²) as well. If `target`'s position in the
  visitation order is uniformly distributed between 1 and V, the expected
  number of iterations is Θ(V) — and Θ(V) iterations × Θ(V) scan cost each
  is still Θ(V²); only the constant improves versus the worst case, not the
  asymptotic class.
- **Space**: Θ(V) for `dist`/`prev`/`visited`.

## Bellman-Ford (`algorithms/bellman_ford.py`) — edge relaxation + early termination

```
for pass in range(|V|-1):        # up to V-1 passes
    for (u, v, w) in edges:       # Θ(E) per pass (E counted both directions)
        relax
    if nothing changed: break      # early termination
```

- **Best case**: Θ(E). If the graph's true shortest-path tree has depth 1
  from `source` (every node directly reachable), the first pass finds all
  final distances and the second pass changes nothing, so the loop exits
  after 2 passes regardless of `|V|`.
- **Worst case**: Θ(VE). A graph whose shortest-path tree is a straight
  chain of length V−1 forces every one of the V−1 passes to make progress,
  each pass doing Θ(E) work.
- **Average case**: between the two, Θ(kE) where k is the shortest-path
  tree's actual depth for the given source — early termination is exactly
  what makes this better than the textbook Θ(VE) bound in practice (see
  `relaxations` counts in `experiment.py`'s output: Bellman-Ford's
  relaxation count is close to Dijkstra's on every instance actually run,
  despite the coarser Θ(VE) worst-case bound).
- **Space**: Θ(V) for `dist`/`prev`, Θ(E) for the directed edge list built
  once per call.

## BFS (`algorithms/bfs.py`)

- **Best case**: Θ(1) when `source == target` (not a case either other
  algorithm special-cases either, for consistency — all three still touch
  `source`'s bookkeeping once).
- **Worst case**: Θ(V+E) — every node enqueued once, every edge examined
  once from each endpoint.
- **Average case**: Θ(V+E) as well; BFS has no input-dependent early exit
  beyond "target found," which only changes the constant, not the bound.
- **Space**: Θ(V) for `prev` and the queue.

## Summary table

| Algorithm | Best | Worst | Average | Space |
|---|---:|---:|---:|---:|
| Dijkstra (array) | Θ(V) | Θ(V²) | Θ(V²) | Θ(V) |
| Bellman-Ford (+ early term.) | Θ(E) | Θ(VE) | Θ(kE), k = tree depth | Θ(V+E) |
| BFS | Θ(1) | Θ(V+E) | Θ(V+E) | Θ(V) |

## What the measured data in `figures/comparisons_vs_n.png` confirms

Across `n ∈ {10, 20, 30, 50, 100, 200, 500}` random connected graphs
(`random_graph`, avg degree 3), Dijkstra's `comparisons` counter grows
visibly faster than Bellman-Ford's or BFS's, consistent with Θ(V²) pulling
away from the other two — see `assignment/data/scaling.csv` for the raw
counts behind that plot.
