# Brief: one-shot exporter for the React PoC. Writes src/data/rnp.json (the 27-PoP
# RNP topology straight from graph.py::load_rnp_topology + the throughput matrix as
# per-link capacity + capital coordinates) and src/data/brazil.json (state outlines,
# Douglas-Peucker-simplified so the bundle stays small). Run from the repo root:
#   python3 -m pca_routing.web.scripts.export_data  <brazil-states.geojson>
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from pca_routing.graph import _load_constants, _parse_mbit, load_rnp_topology

OUT = Path(__file__).resolve().parent.parent / "src" / "data"

# (lat, lon) of each state's capital - the PoP's real location.
COORDS = {
    "AC": (-9.97, -67.81), "AL": (-9.67, -35.74), "AM": (-3.12, -60.02), "AP": (0.03, -51.07),
    "BA": (-12.97, -38.51), "CE": (-3.73, -38.52), "DF": (-15.79, -47.88), "ES": (-20.32, -40.34),
    "GO": (-16.68, -49.25), "MA": (-2.53, -44.30), "MG": (-19.92, -43.94), "MS": (-20.47, -54.62),
    "MT": (-15.60, -56.10), "PA": (-1.46, -48.50), "PB": (-7.12, -34.86), "PE": (-8.05, -34.88),
    "PI": (-5.09, -42.80), "PR": (-25.43, -49.27), "RJ": (-22.91, -43.17), "RN": (-5.79, -35.21),
    "RO": (-8.76, -63.90), "RR": (2.82, -60.67), "RS": (-30.03, -51.23), "SC": (-27.59, -48.55),
    "SE": (-10.91, -37.07), "SP": (-23.55, -46.63), "TO": (-10.18, -48.33),
}


def _dp(points, eps):
    """Douglas-Peucker on a list of (x, y)."""
    if len(points) < 3:
        return points
    (x1, y1), (x2, y2) = points[0], points[-1]
    dx, dy = x2 - x1, y2 - y1
    norm = math.hypot(dx, dy) or 1e-12
    idx, dmax = 0, 0.0
    for i in range(1, len(points) - 1):
        d = abs(dy * points[i][0] - dx * points[i][1] + x2 * y1 - y2 * x1) / norm
        if d > dmax:
            idx, dmax = i, d
    if dmax > eps:
        return _dp(points[: idx + 1], eps)[:-1] + _dp(points[idx:], eps)
    return [points[0], points[-1]]


def export_topology():
    g = load_rnp_topology("rtt")
    mod = _load_constants("onos_topologies/topologies/configs/rnp.py")
    names = [p[0].replace("PoP-", "") for p in mod.POPS]
    idx = {n: i for i, n in enumerate(names)}
    edges = []
    for u, v, rtt in sorted(g.edges()):
        i, j = idx[u], idx[v]
        raw = mod.THROUGHPUT_MATRIX[i][j] or mod.THROUGHPUT_MATRIX[j][i]
        edges.append({"u": u, "v": v, "rtt": rtt, "capacity": _parse_mbit(raw)})
    nodes = [{"id": n, "lat": COORDS[n][0], "lon": COORDS[n][1]} for n in names]
    (OUT / "rnp.json").write_text(json.dumps({"nodes": nodes, "edges": edges}, indent=1))
    print(f"rnp.json: {len(nodes)} nodes, {len(edges)} edges")


def export_map(src):
    gj = json.loads(Path(src).read_text())
    states = []
    for f in gj["features"]:
        geom = f["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        rings = []
        for poly in polys:
            ring = [(x, y) for x, y in poly[0]]
            # a closed ring has first == last, which degenerates DP's chord; split it
            # at the point farthest from the start and simplify each half.
            far = max(range(len(ring)), key=lambda i: math.hypot(ring[i][0] - ring[0][0], ring[i][1] - ring[0][1]))
            ring = _dp(ring[: far + 1], 0.04)[:-1] + _dp(ring[far:], 0.04)
            if len(ring) >= 4:
                rings.append([[round(x, 2), round(y, 2)] for x, y in ring])
        states.append({"sigla": f["properties"]["sigla"], "rings": rings})
    (OUT / "brazil.json").write_text(json.dumps(states, separators=(",", ":")))
    print(f"brazil.json: {sum(len(s['rings']) for s in states)} rings, {(OUT/'brazil.json').stat().st_size} bytes")


def export_parity():
    """Ground truth for the TS port: every unordered pair, all three Python algorithms."""
    from pca_routing.algorithms.bellman_ford import BellmanFordPathFinder
    from pca_routing.algorithms.bfs import BFSPathFinder
    from pca_routing.algorithms.dijkstra import DijkstraPathFinder

    g = load_rnp_topology("rtt")
    ids = sorted(g.nodes)
    rows = []
    for i, s in enumerate(ids):
        for t in ids[i + 1:]:
            for f in (DijkstraPathFinder(), BellmanFordPathFinder(), BFSPathFinder()):
                r = f.find_path(g, s, t)
                rows.append({"s": s, "t": t, "alg": r.algorithm, "path": r.path, "cost": round(r.cost, 6),
                             "comparisons": r.comparisons, "relaxations": r.relaxations, "visited": r.nodes_visited})
    (OUT.parent / "lib" / "parity.fixture.json").write_text(json.dumps(rows, separators=(",", ":")))
    print(f"parity.fixture.json: {len(rows)} rows")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    export_topology()
    export_parity()
    if len(sys.argv) > 1:
        export_map(sys.argv[1])
