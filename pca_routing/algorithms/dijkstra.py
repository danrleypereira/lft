# Brief: Dijkstra's algorithm - greedy choice of the unvisited node with the
# smallest known distance, relax its neighbors, repeat. Array/linear-scan
# selection on purpose (not a heap): it gives an exceptionally simple
# complexity story for the report - Theta(V^2) every time, best case and
# worst case, with no data-structure subtlety to argue about. A binary-heap
# version (O((V+E) log V)) is a natural "optimization" section to add later,
# not needed for the base comparison against Bellman-Ford.

from __future__ import annotations

import math
import time

from ..graph import path_weight, reconstruct_path
from .base import PathFinder, PathResult


class DijkstraPathFinder(PathFinder):
    name = "dijkstra"
    supports_negative_weights = False  # classic proof assumes w(u,v) >= 0; never violated here

    def find_path(self, graph, source: str, target: str) -> PathResult:
        t0 = time.perf_counter_ns()

        dist: dict[str, float] = {n: math.inf for n in graph.nodes}
        prev: dict[str, str | None] = {n: None for n in graph.nodes}
        dist[source] = 0.0
        visited: set[str] = set()

        comparisons = relaxations = nodes_visited = 0

        # V iterations, each a linear scan over V nodes to pick the next
        # closest unvisited one -> Theta(V^2) regardless of the graph's shape
        # or density (that's the whole point of this version).
        for _ in range(graph.num_nodes):
            u, best = None, math.inf
            for n in graph.nodes:
                comparisons += 1
                if n not in visited and dist[n] < best:
                    u, best = n, dist[n]
            if u is None:
                break  # remaining nodes are unreachable
            visited.add(u)
            nodes_visited += 1
            if u == target:
                break
            for v, w in graph.neighbors(u):
                comparisons += 1
                if v in visited:
                    continue
                relaxations += 1
                if dist[u] + w < dist[v]:
                    dist[v] = dist[u] + w
                    prev[v] = u

        path = reconstruct_path(prev, source, target)
        elapsed = time.perf_counter_ns() - t0
        return PathResult(
            algorithm=self.name,
            path=path,
            reachable=bool(path),
            hops=max(len(path) - 1, 0),
            cost=path_weight(graph, path) if path else math.inf,
            comparisons=comparisons,
            relaxations=relaxations,
            nodes_visited=nodes_visited,
            elapsed_ns=elapsed,
        )
