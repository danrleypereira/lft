# Brief: breadth-first search, hop count only - no edge weight enters the
# search itself, only the traversal order. This is the literature anchor for
# this project's `fwd` experiment mode (ONOS's reactive forwarding, which
# ONOS's own TopologyService computes shortest paths for in terms of hop
# count by default). Kept as a baseline, not the graded comparison: BFS and
# Dijkstra/Bellman-Ford optimize different quantities (hop count vs. summed
# weight), so they are not interchangeable solutions to the same problem -
# see DESIGN.md for why that disqualifies "BFS vs Dijkstra" as the main
# comparison but keeps it as a legitimate third baseline.

from __future__ import annotations

import time
from collections import deque

from ..graph import path_weight, reconstruct_path
from .base import PathFinder, PathResult


class BFSPathFinder(PathFinder):
    name = "bfs"
    supports_negative_weights = False  # moot: weights are never read

    def find_path(self, graph, source: str, target: str) -> PathResult:
        t0 = time.perf_counter_ns()

        prev: dict[str, str | None] = {source: None}
        queue = deque([source])
        comparisons = nodes_visited = 0

        while queue:
            u = queue.popleft()
            nodes_visited += 1
            if u == target:
                break
            for v, _w in graph.neighbors(u):
                comparisons += 1
                if v not in prev:
                    prev[v] = u
                    queue.append(v)

        path = reconstruct_path(prev, source, target)
        elapsed = time.perf_counter_ns() - t0
        return PathResult(
            algorithm=self.name,
            path=path,
            reachable=bool(path),
            hops=max(len(path) - 1, 0),
            # cost is computed post-hoc from the path BFS found, same definition
            # as the other two (see PathResult) - NOT what BFS searched on.
            cost=path_weight(graph, path) if path else float("inf"),
            comparisons=comparisons,
            relaxations=0,  # BFS never relaxes a weighted distance
            nodes_visited=nodes_visited,
            elapsed_ns=elapsed,
        )
