# Brief: the Experiment file the assignment asks for - loads a graph, runs the
# three algorithms over it, and reports path/cost/complexity-counters/timing
# for each. This file is the one and only place that knows the concrete
# algorithm classes exist; everything below ALGORITHMS calls them only
# through the PathFinder interface.

from __future__ import annotations

import csv
import sys
from pathlib import Path

from .algorithms.base import PathFinder, PathResult
from .algorithms.bellman_ford import BellmanFordPathFinder
from .algorithms.bfs import BFSPathFinder
from .algorithms.dijkstra import DijkstraPathFinder
from .graph import Graph, load_diamond_topology, load_rnp_topology, random_graph

# ---------------------------------------------------------------------------
# THE ONE SELECTION POINT. To swap which implementation answers for
# "dijkstra"/"bellman_ford"/"bfs" - or add a fourth algorithm - this list is
# the only thing that changes. Nothing below this line ever imports or
# names DijkstraPathFinder/BellmanFordPathFinder/BFSPathFinder again: run_one()
# (line ~40) and run_suite() (line ~55) are written once, against the
# PathFinder type, and that single call `algo.find_path(graph, source, target)`
# is the Liskov substitution in action - swap any entry in ALGORITHMS for any
# other PathFinder subclass and neither function needs to change.
# ---------------------------------------------------------------------------
ALGORITHMS: list[PathFinder] = [
    DijkstraPathFinder(),
    BellmanFordPathFinder(),
    BFSPathFinder(),
]


def run_one(graph: Graph, algo: PathFinder, source: str, target: str) -> PathResult:
    """Run a single algorithm over a single (source, target) pair. `algo` is
    typed as PathFinder here, not as any concrete class - this function would
    be identical if ALGORITHMS held three totally different implementations."""
    return algo.find_path(graph, source, target)


def run_suite(graph: Graph, source: str, target: str) -> dict[str, PathResult]:
    """Run every algorithm in ALGORITHMS over the same (source, target) and
    return {algorithm_name: PathResult}."""
    return {algo.name: run_one(graph, algo, source, target) for algo in ALGORITHMS}


def check_correctness(results: dict[str, PathResult], *, tol: float = 1e-9) -> bool:
    """Dijkstra and Bellman-Ford solve the SAME problem (minimum total weight),
    so on a graph with non-negative weights their costs must agree - this is
    a free correctness oracle, not just a comparison: if they disagree, one
    implementation has a bug. BFS is excluded on purpose: it optimizes hop
    count, so its cost is not expected to match the other two (see bfs.py)."""
    dij, bf = results.get("dijkstra"), results.get("bellman_ford")
    if dij is None or bf is None:
        return True
    if dij.reachable != bf.reachable:
        return False
    if not dij.reachable:
        return True
    return abs(dij.cost - bf.cost) < tol


def print_suite(label: str, graph: Graph, source: str, target: str) -> dict[str, PathResult]:
    results = run_suite(graph, source, target)
    ok = check_correctness(results)
    print(f"\n=== {label}: {source} -> {target}  (|V|={graph.num_nodes}, |E|={graph.num_edges}) ===")
    for name, r in results.items():
        path = " -> ".join(r.path) if r.reachable else "(unreachable)"
        print(f"  {name:<13} hops={r.hops:<3} cost={r.cost:<10.3f} "
              f"comparisons={r.comparisons:<6} relaxations={r.relaxations:<6} "
              f"elapsed_ns={r.elapsed_ns:<9} path={path}")
    print(f"  correctness oracle (dijkstra.cost == bellman_ford.cost): {'OK' if ok else 'MISMATCH'}")
    if not ok:
        raise AssertionError(f"{label}: dijkstra/bellman_ford cost mismatch - check the implementations")
    return results


def scaling_experiment(sizes: list[int], out_csv: Path, seed: int = 42) -> None:
    """The growing-|V| execution-time experiment: for each size, build a random
    connected graph, run all three algorithms once, and log their counters -
    this is where Theta(V^2) (Dijkstra) vs. the early-terminating Theta(VE)
    worst case (Bellman-Ford) vs. Theta(V+E) (BFS) actually shows up in
    practice, since on the 4-node diamond or even the 27-node RNP graph the
    runtime is mostly Python call overhead, not algorithmic work.
    """
    rows = []
    for n in sizes:
        g = random_graph(n, avg_degree=3.0, seed=seed)
        nodes = sorted(g.nodes)
        source, target = nodes[0], nodes[-1]
        results = run_suite(g, source, target)
        for name, r in results.items():
            rows.append({
                "n": n, "edges": g.num_edges, "algorithm": name,
                "hops": r.hops, "cost": r.cost, "comparisons": r.comparisons,
                "relaxations": r.relaxations, "nodes_visited": r.nodes_visited,
                "elapsed_ns": r.elapsed_ns,
            })
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {len(rows)} rows to {out_csv}")


def main() -> int:
    # 1) the diamond: small enough to walk by hand in the report, real
    #    per-link delays (see graph.py's load_diamond_topology docstring)
    diamond = load_diamond_topology()
    print_suite("diamond_topology", diamond, "ES", "SP")

    # 2) the real 27-node RNP backbone, cost = measured RTT (ms)
    rnp = load_rnp_topology(cost="rtt")
    print_suite("rnp_topology", rnp, "ES", "AC")
    print_suite("rnp_topology", rnp, "RJ", "RR")

    # 3) growing random graphs, for the execution-time/complexity section
    scaling_experiment(
        sizes=[10, 20, 30, 50, 100, 200, 500],
        out_csv=Path(__file__).resolve().parent / "results" / "scaling.csv",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
