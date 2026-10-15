# pca_routing/web — React PoC

Class demo for `pca_routing`: the real 27-PoP RNP backbone on a Brazil map (Vite + React + React Router).

- **Algorithms (1 pair):** Dijkstra / Bellman-Ford / BFS for one source→target, each path in its own color, with
  the `PathResult` numbers (RTT cost, hops, comparisons, relaxations).
- **Two flows:** two concurrent source→target pairs with a demand (Mbit) each. *Naive* = Dijkstra per pair;
  *Coordinated* = one whole path per flow minimizing total RTT under every link's capacity (exact, by path
  enumeration). The two diverge where a shared link overflows (default: AL→SP + DF→SP at 60 Mbit overloads DF–SP, 20 Mbit).

## Run

```bash
cd pca_routing/web
npm install
npm run dev        # http://localhost:5173
npm test           # TS port vs. Python ground truth (all 351 pairs x 3 algorithms) + allocator checks
npm run build
```

## Data

`src/data/rnp.json`, `src/data/brazil.json` and `src/lib/parity.fixture.json` are generated from the Python side
(`graph.py::load_rnp_topology`, the throughput matrix as link capacity, simplified state outlines):

```bash
# from the repo root; the GeoJSON is any Brazil-states file with a `sigla` property (optional: omit to skip the map)
python3 -m pca_routing.web.scripts.export_data brazil-states.geojson
```

The TS algorithms (`src/lib/algorithms.ts`) are line-for-line ports of `pca_routing/algorithms/*.py`; the parity test
checks cost for every pair and Dijkstra's comparison counter. Python iterates a `set`, so on equal-cost ties the
exact path may differ between runs; cost is what is asserted.
