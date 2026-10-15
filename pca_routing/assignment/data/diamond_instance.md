# Worked instance: the diamond topology (ES → SP)

Small enough to trace by hand — this is the "instance of the problem, along
with its solution using the algorithm" the report needs to show step by
step. Source `graph.py`'s `load_diamond_topology()`: real per-link delays
from `onos_topologies/iperf_experiment/diamond_topology/main.py`'s
`prio_links`, not the topology's own uniform `constants.py` default.

## The graph

```
        ES
       /    \
    10ms    30ms   (ES<->RJ is the static bottleneck: +20ms over the baseline)
     /        \
   MG          RJ
     \        /
    10ms    10ms
       \    /
        SP
```

4 nodes, 4 edges: ES–MG (10), ES–RJ (30), MG–SP (10), RJ–SP (10).

## Dijkstra, traced by hand (source = ES, target = SP)

Array-based selection (no heap) — the version actually implemented in
`algorithms/dijkstra.py`.

| Step | Visited | dist[ES] | dist[MG] | dist[RJ] | dist[SP] | pick next |
|---|---|---:|---:|---:|---:|---|
| 0 (init) | {} | 0 | ∞ | ∞ | ∞ | ES (smallest unvisited) |
| 1 | {ES} | 0 | 10 | 30 | ∞ | relax ES's neighbors (MG=10, RJ=30); pick MG (smallest unvisited) |
| 2 | {ES,MG} | 0 | 10 | 30 | 20 | relax MG's neighbors (SP: 10+10=20 < ∞); pick SP (20 < 30) |
| 3 | {ES,MG,SP} | 0 | 10 | 30 | 20 | target reached, stop |

Result: `ES -> MG -> SP`, cost **20**, 2 hops.
(RJ is never improved below 30, and the search stops once SP is popped —
RJ's own distance is irrelevant to this query.)

## Bellman-Ford, traced by hand (same instance)

Relax every directed edge (8 directed edges from the 4 undirected ones), up
to |V|-1 = 3 passes, stopping early if a pass changes nothing.

- **Pass 1**: dist[ES]=0 → relax ES→MG (10), ES→RJ (30); then MG→SP
  (10+10=20); RJ→SP would give 30+10=40, not better than 20 already set in
  the same pass if MG→SP is relaxed first — order-dependent within a pass,
  but the *result* after the pass is the same: dist = {ES:0, MG:10, RJ:30, SP:20}.
- **Pass 2**: no edge improves any distance further → **updated = False** →
  early termination, stop after 2 passes instead of running the full 3.

Result: same path, same cost (**20**) — required, since both solve the
identical minimum-weight-path problem; see `check_correctness` /
`TestDijkstraBellmanFordAgree` in the tests.

## BFS, same instance

Ignores weights entirely, explores by hop count: ES → {MG, RJ} (both 1 hop)
→ SP reached from MG or RJ (2 hops either way — picks whichever was
enqueued first, `MG` here since it's visited before `RJ` in insertion order).

Result: `ES -> MG -> SP` — **same path** as Dijkstra/Bellman-Ford here,
because this particular instance's shortest-hop path happens to also be its
lowest-cost path. That coincidence is exactly why the report should also
show a case where they diverge — see `tests/test_algorithms.py::diverging_graph()`
(A–B–D at 140 in 2 hops vs. A–C–X–D at 15 in 3 hops), reused directly from
the ChatGPT analysis's own example, and
`load_rnp_topology()`'s `ES -> AC` query in `experiment.py`, where BFS's
5-hop path (cost 3.05) and Dijkstra/Bellman-Ford's 6-hop path (cost 1.60)
genuinely disagree on a real instance.
