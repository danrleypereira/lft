# Brief: the common contract all three path-finding algorithms implement. This
# is the Liskov Substitution Principle applied directly: `experiment.py` is
# written once, against PathFinder, and never against DijkstraPathFinder,
# BellmanFordPathFinder or BFSPathFinder by name - any of the three can be
# substituted for any other without the caller changing a single line, because
# every subclass honors the same pre/postconditions below.

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class PathResult:
    """What every PathFinder.find_path() returns - identical shape regardless
    of which algorithm produced it. That uniformity is what makes the three
    substitutable: experiment.py reads result.cost / result.hops / result.path
    the same way no matter which concrete class it called.

    `cost` is always "sum of edge weights along `path`" - computed the same
    way for all three (graph.path_weight), even for BFS, whose own search
    criterion is hop count, not weight. Without that rule, BFS's "cost" would
    quietly mean something different from Dijkstra's and Bellman-Ford's, and
    a caller comparing `.cost` across algorithms would be comparing two
    different quantities while believing they were the same one - exactly the
    kind of silent postcondition violation Liskov substitutability forbids.
    """

    algorithm: str
    path: list[str]
    reachable: bool
    hops: int
    cost: float
    # bookkeeping for the report's complexity/execution-time section
    comparisons: int = 0
    relaxations: int = 0
    nodes_visited: int = 0
    elapsed_ns: int = 0


class PathFinder(ABC):
    """Common interface for Dijkstra, Bellman-Ford and BFS.

    Precondition (what an implementation may assume, and must NOT demand more
    than - strengthening a precondition would break substitutability: a
    caller that only knows it is holding a PathFinder must be able to call it
    exactly like this on ANY subclass):
      - `graph` is a pca_routing.graph.Graph; `source` and `target` are node
        ids that may or may not be in it, may or may not be connected.

    `supports_negative_weights` is deliberately NOT part of the precondition
    every subclass must satisfy - it is false by default (Dijkstra's classic
    proof assumes non-negative weights) and Bellman-Ford overrides it to
    True. Every graph actually used in this project has non-negative weights
    (delay in ms, 1/capacity), so this never matters for the experiments run
    here - but the type is honest about it rather than silently promising a
    guarantee two of the three implementations can't keep.

    Postcondition (what every implementation MUST guarantee - this is the
    part callers actually rely on without knowing the concrete class, i.e.
    the actual substitutability contract):
      - always returns a PathResult; never raises for "no path exists"
        (`reachable=False`, `path=[]` instead)
      - `result.path`, when reachable, starts at `source` and ends at `target`
      - `result.cost` is the sum of edge weights along `result.path`, by the
        same definition for all three algorithms (see PathResult above)
    """

    name: str = "pathfinder"
    supports_negative_weights: bool = False

    @abstractmethod
    def find_path(self, graph, source: str, target: str) -> PathResult:
        raise NotImplementedError
