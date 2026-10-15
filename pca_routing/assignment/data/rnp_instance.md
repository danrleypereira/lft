# Instance: the real RNP backbone (30 nodes)

Source: `onos_topologies/iperf_experiment/rnp_topology/constants.py` — the
real Brazilian academic/research network (RNP) backbone this whole project
is modeled on, not a synthetic benchmark graph.

- **30 nodes** (`POPS`): one per Brazilian state/region PoP, plus
  Araraquara and João Pessoa as their own PoPs (distinct from the SP/PB
  state nodes).
- **50 undirected edges** (`ADJACENCY_MATRIX`).
- **Edge weight**: `1 / capacity_gbit` (`load_rnp_topology(cost="inverse_capacity")`,
  the default) — a genuine engineering cost (favors high-capacity trunks),
  **not latency**: this dataset carries no per-link delay matrix, only
  capacity (1–40 gbit per link, from `THROUGHPUT_MATRIX`), and the report
  must say "cost," never "latency," for this instance. `cost="capacity"`
  and `cost="hops"` are also available on the same loader for comparison
  figures.

## Why this is the scaling instance, not just a visual aid

At 4 nodes (the diamond) every algorithm finishes in microseconds regardless
of its complexity class — there's nothing to measure. At 30 real nodes the
separation between Dijkstra's Θ(V²) and BFS's Θ(V+E) already starts to show
in the `comparisons` counter (`experiment.py`'s `print_suite` output), and
`scaling_experiment` (`random_graph`, sizes 10→500) is what makes it
unambiguous — see `figures/comparisons_vs_n.png`.

## Two queries used in `experiment.main()`

1. **ES → AC** (Espírito Santo to Acre — opposite corners of the country):
   Dijkstra/Bellman-Ford take `ES → RJ → SP → ARARAQUARA → MT → RO → AC`
   (6 hops, cost 1.60); BFS takes `ES → BA → DF → MT → RO → AC` (5 hops,
   cost 3.05). **These disagree** — a real instance of the BFS-vs-weighted
   divergence the whole comparison is about, not just the synthetic
   textbook example in `tests/test_algorithms.py`.
2. **RJ → RR** (Rio de Janeiro to Roraima): same pattern, 6 hops either way
   here, but still a materially different cost (2.10 vs. 4.525) — a second,
   independent real-data confirmation.

Both are reproduced verbatim by running `python3 -m pca_routing.experiment`.
