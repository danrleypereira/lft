# Brief: a plain undirected weighted graph, plus loaders that build one from this
# repo's own topology data (diamond_topology, rnp_topology) or at random, for the
# PCA routing-algorithms assignment. No graph library is used anywhere here -
# add_edge/neighbors are the entire "graph API" the three algorithms get.

from __future__ import annotations

import importlib.util
import random
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Graph:
    """Undirected weighted graph as an adjacency list: node id -> [(neighbor, weight), ...].

    Deliberately minimal - the three algorithms only ever call add_edge() while
    building a Graph and neighbors()/nodes while searching it. That narrow surface
    is what makes it easy to swap in a bigger/different Graph later without
    touching the algorithms.
    """

    nodes: set[str] = field(default_factory=set)
    _adj: dict[str, list[tuple[str, float]]] = field(default_factory=dict)

    def add_node(self, node: str) -> None:
        self.nodes.add(node)
        self._adj.setdefault(node, [])

    def add_edge(self, u: str, v: str, weight: float = 1.0) -> None:
        self.add_node(u)
        self.add_node(v)
        self._adj[u].append((v, weight))
        self._adj[v].append((u, weight))

    def neighbors(self, u: str) -> list[tuple[str, float]]:
        return self._adj.get(u, [])

    def edges(self) -> list[tuple[str, str, float]]:
        """Each undirected edge once (u < v lexicographically)."""
        seen = []
        for u, nbrs in self._adj.items():
            for v, w in nbrs:
                if u < v:
                    seen.append((u, v, w))
        return seen

    @property
    def num_nodes(self) -> int:
        return len(self.nodes)

    @property
    def num_edges(self) -> int:
        return len(self.edges())


def _load_constants(relative_path: str):
    """Import a constants.py by file path (same trick cli.py's _load_config uses),
    instead of `import onos_topologies...` - keeps this package decoupled from
    the rest of the LFT/profissa_lft import chain (docker, paramiko, ...), since
    all we actually want out of those files is a couple of plain tuples."""
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_diamond_topology() -> Graph:
    """The 4-PoP diamond (ES, MG, RJ, SP), with the REAL per-link delays this
    project actually applies - not diamond_topology/constants.py's CONFIG
    (which is a single uniform 10ms/35mbit for every link, applied before any
    experiment-specific tc rules run), but the four distinct values
    onos_topologies/iperf_experiment/diamond_topology/main.py's own
    `prio_links` list sets per snapshot, which is where the real heterogeneity
    in this topology actually lives:
        ES<->MG : 10ms, 35mbit   (normal)
        ES<->RJ : 30ms, 5mbit    (the static bottleneck: cfg_delay+20, 5mbit)
        MG<->SP : 10ms, 35mbit
        RJ<->SP : 10ms, 35mbit
    Edge weight here is delay in ms - a genuine measured/configured quantity,
    not a proxy.
    """
    g = Graph()
    g.add_edge("ES", "MG", 10.0)
    g.add_edge("ES", "RJ", 30.0)
    g.add_edge("MG", "SP", 10.0)
    g.add_edge("RJ", "SP", 10.0)
    return g


def load_rnp_topology(cost: str = "inverse_capacity") -> Graph:
    """The real 30-node RNP backbone from
    onos_topologies/iperf_experiment/rnp_topology/constants.py.

    `cost`:
      - "inverse_capacity" (default): weight = 1 / capacity_gbit. Favors fat
        pipes. This is a COST, not a latency - rnp_topology ships no per-link
        delay matrix, only capacity, so never call this "latency" in the report.
      - "capacity": weight = capacity_gbit directly (useful only for display;
        meaningless to minimize, since a bigger number here is a FASTER link).
      - "hops": weight = 1.0 for every edge (same graph BFS already walks).
    """
    mod = _load_constants("onos_topologies/iperf_experiment/rnp_topology/constants.py")
    names = [p[0].replace("PoP-", "") for p in mod.POPS]
    n = len(names)
    g = Graph()
    for i in range(n):
        for j in range(i + 1, n):
            if not mod.ADJACENCY_MATRIX[i][j]:
                continue
            raw = mod.THROUGHPUT_MATRIX[i][j] or mod.THROUGHPUT_MATRIX[j][i] or "1gbit"
            gbit = float(raw.replace("gbit", ""))
            if cost == "capacity":
                w = gbit
            elif cost == "hops":
                w = 1.0
            else:
                w = 1.0 / gbit
            g.add_edge(names[i], names[j], w)
    return g


def random_graph(n: int, avg_degree: float = 3.0, weight_range: tuple[float, float] = (1.0, 50.0),
                  seed: int | None = None) -> Graph:
    """A random connected graph for the growing-|V| execution-time experiment.
    Built as a random spanning tree (guarantees connectivity) plus extra random
    edges until the average degree target is met - deliberately simple, not a
    textbook random-graph model, since all this needs to do is give the three
    algorithms graphs of controlled, increasing size.
    """
    rng = random.Random(seed)
    g = Graph()
    ids = [f"n{i}" for i in range(n)]
    for node in ids:
        g.add_node(node)

    # random spanning tree: connect each new node to a random earlier one
    for i in range(1, n):
        j = rng.randrange(i)
        g.add_edge(ids[i], ids[j], round(rng.uniform(*weight_range), 2))

    target_edges = int(n * avg_degree / 2)
    attempts = 0
    while g.num_edges < target_edges and attempts < target_edges * 20:
        u, v = rng.choice(ids), rng.choice(ids)
        attempts += 1
        if u == v or any(v == nb for nb, _ in g.neighbors(u)):
            continue
        g.add_edge(u, v, round(rng.uniform(*weight_range), 2))
    return g


def path_weight(graph: Graph, path: list[str]) -> float:
    """Sum of edge weights along `path`. Used by every algorithm, including BFS,
    so that PathResult.cost always means the same thing regardless of which
    algorithm produced the path (see algorithms/base.py)."""
    if len(path) < 2:
        return 0.0
    lookup = {}
    for u, v, w in graph.edges():
        lookup[(u, v)] = w
        lookup[(v, u)] = w
    return sum(lookup[(path[i], path[i + 1])] for i in range(len(path) - 1))


def reconstruct_path(prev: dict[str, str | None], source: str, target: str) -> list[str]:
    if target not in prev:
        return []
    path = []
    node = target
    while node is not None:
        path.append(node)
        node = prev[node]
    path.reverse()
    return path if path and path[0] == source else []
