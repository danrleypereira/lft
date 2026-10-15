# Instance: the real RNP backbone (27 nodes)

Source: `onos_topologies/topologies/configs/rnp.py` — the real Brazilian
academic/research network (RNP) backbone this whole project is modeled on,
not a synthetic benchmark graph. (This replaces the earlier 30-node file at
`onos_topologies/iperf_experiment/rnp_topology/constants.py`, removed when
`origin/dash-experiments` was merged into this branch — the new file is a
genuine upgrade, not just a move: see below.)

- **27 nodes** (`POPS`): one per Brazilian state/region PoP.
- **44 undirected edges** (`ADJACENCY_MATRIX`).
- **Edge weight**: real measured **round-trip time in ms**
  (`load_rnp_topology(cost="rtt")`, the default, reading `RTT_MATRIX`). This
  is a genuine latency now, not a proxy — the version of this file this
  package originally shipped against had no delay matrix at all, only
  capacity, which forced `1/capacity` as a stand-in cost (kept available as
  `cost="inverse_throughput"` purely for comparison against that earlier
  draft). `cost="throughput"` (`THROUGHPUT_MATRIX`, in mbit) and
  `cost="hops"` are also available on the same loader.

## Why this is the scaling instance, not just a visual aid

At 4 nodes (the diamond) every algorithm finishes in microseconds regardless
of its complexity class — there's nothing to measure. At 27 real nodes the
separation between Dijkstra's Θ(V²) and BFS's Θ(V+E) already starts to show
in the `comparisons` counter (`experiment.py`'s `print_suite` output), and
`scaling_experiment` (`random_graph`, sizes 10→500) is what makes it
unambiguous — see `figures/comparisons_vs_n.png`.

## Two queries used in `experiment.main()`

1. **ES → AC** (Espírito Santo to Acre — opposite corners of the country):
   with real RTT weights, Dijkstra, Bellman-Ford **and** BFS all agree here
   — `ES → BA → DF → MT → RO → AC`, 5 hops, 66.42 ms. On this particular
   pair, minimizing hops happens to also minimize latency. Kept as a query
   specifically *because* it doesn't diverge — not every pair should, and a
   report that only shows diverging examples would be cherry-picking.
2. **RJ → RR** (Rio de Janeiro to Roraima): **these disagree**, on real
   measured RTT, not a synthetic example — BFS takes `RJ → SP → CE → RR`
   (3 hops, but **144.01 ms**); Dijkstra/Bellman-Ford take
   `RJ → MG → DF → AM → RR` (4 hops, **98.15 ms**). Fewer hops, worse
   latency, by a wide margin (+47%) — on a real backbone, with real
   measurements, not the textbook `diverging_graph()` example in
   `tests/test_algorithms.py`. This is the instance to lead with in the
   report's results section.

Both are reproduced verbatim by running `python3 -m pca_routing.experiment`.
