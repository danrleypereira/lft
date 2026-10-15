# Brief: Bellman-Ford - repeated relaxation of every edge, up to |V|-1 passes
# (Bellman's own 1958 paper: successive approximation, converging in at most
# N-1 steps). Dynamic-programming technique: pass k holds the best distance
# using at most k edges, built from pass k-1. Early termination (stop as soon
# as a full pass relaxes nothing) is the only deliberate optimization kept -
# everything else is the textbook algorithm.

from __future__ import annotations

import math
import time

from ..graph import path_weight, reconstruct_path
from .base import PathFinder, PathResult


class BellmanFordPathFinder(PathFinder):
    name = "bellman_ford"
    supports_negative_weights = True  # the one place this class differs from Dijkstra's contract

    def find_path(self, graph, source: str, target: str) -> PathResult:
        t0 = time.perf_counter_ns()

        dist: dict[str, float] = {n: math.inf for n in graph.nodes}
        prev: dict[str, str | None] = {n: None for n in graph.nodes}
        dist[source] = 0.0

        # each undirected edge relaxed in both directions, once per pass
        directed_edges = []
        for u, v, w in graph.edges():
            directed_edges.append((u, v, w))
            directed_edges.append((v, u, w))

        comparisons = relaxations = 0
        passes_run = 0
        for _ in range(max(graph.num_nodes - 1, 0)):
            passes_run += 1
            updated = False
            for u, v, w in directed_edges:
                comparisons += 1
                if dist[u] + w < dist[v]:
                    dist[v] = dist[u] + w
                    prev[v] = u
                    updated = True
                    relaxations += 1
            if not updated:
                break  # converged - no edge relaxed this pass, so none will on later passes either

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
            nodes_visited=passes_run,  # reused here as "passes over the edge list"
            elapsed_ns=elapsed,
        )
