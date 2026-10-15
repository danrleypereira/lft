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


def _parse_ms(raw: str) -> float:
    return float(raw.replace("ms", ""))


def _parse_mbit(raw: str) -> float:
    return float(raw.replace("mbit", ""))


def load_rnp_topology(cost: str = "rtt") -> Graph:
    """The real 27-node RNP backbone from
    onos_topologies/topologies/configs/rnp.py (moved there by the
    chore/reorganize-onos-topologies work merged into dash-experiments -
    the old onos_topologies/iperf_experiment/rnp_topology/constants.py this
    used to read no longer exists). That reorganization is also a genuine
    upgrade for this assignment: the old file only had a capacity matrix
    (no per-link delay at all); this one adds a real RTT_MATRIX measured on
    the actual RNP backbone, so "rtt" below is now an honest latency cost,
    not the inverse-capacity proxy the first version of this loader had to
    use instead.

    `cost`:
      - "rtt" (default): weight = measured round-trip time in ms
        (RTT_MATRIX). A genuine latency - minimize this for "lowest-latency
        path," the textbook framing of the problem.
      - "throughput": weight = capacity in mbit directly (useful for
        display; meaningless to minimize, since a bigger number here is a
        FASTER link, not a worse one).
      - "inverse_throughput": weight = 1 / capacity_mbit. Favors fat pipes -
        kept for comparison against the first version of this loader/report
        draft, which used this before RTT_MATRIX existed.
      - "hops": weight = 1.0 for every edge (same graph BFS already walks).
    """
    mod = _load_constants("onos_topologies/topologies/configs/rnp.py")
    names = [p[0].replace("PoP-", "") for p in mod.POPS]
    n = len(names)
    g = Graph()
    for i in range(n):
        for j in range(i + 1, n):
            if not mod.ADJACENCY_MATRIX[i][j]:
                continue
            if cost == "hops":
                w = 1.0
            elif cost in ("throughput", "inverse_throughput"):
                raw = mod.THROUGHPUT_MATRIX[i][j] or mod.THROUGHPUT_MATRIX[j][i]
                mbit = _parse_mbit(raw)
                w = mbit if cost == "throughput" else 1.0 / mbit
            else:
                raw = mod.RTT_MATRIX[i][j] or mod.RTT_MATRIX[j][i]
                w = _parse_ms(raw)
            g.add_edge(names[i], names[j], w)
    return g


def load_from_console_api(testbed: dict, cost: str = "delay") -> Graph:
    """Builds a Graph from REIN console's own `GET /api/testbed` response - the
    LIVE running topology, not a static constants.py file. Proves the same
    algorithms work unchanged against a completely different data source,
    through nothing but Graph.add_edge(): this loader is the only thing that
    knows the console's JSON shape, the three algorithms don't.

    Node ids are each switch's `desc` (its PoP, e.g. "AC") rather than its
    console id ("s0"), so results line up with load_rnp_topology()'s naming.

    `cost`: "delay" (default) - the link's CURRENT one-way delay in ms, from
    `link["now"]["delay"]`. This is NOT the same quantity as
    load_rnp_topology()'s RTT_MATRIX: the console halves a link's measured
    round-trip time to get the per-direction `tc netem delay` each way
    actually uses (confirmed empirically: AC<->RO is "7.02ms" round-trip in
    topologies/configs/rnp.py, 3.51ms one-way live - exactly half). Still a
    genuine, independently-sourced latency, just a different unit; don't
    compare its numbers directly against `load_rnp_topology()`'s without
    doubling them first.
    Also available: "rate" (current throughput in mbit, `now.rate`) and
    "loss" (current packet loss, `now.loss`) for the same live link.
    A link currently marked `now.down == True` is skipped entirely - this
    loader reflects whatever the testbed's real state is *right now*,
    degradations included, not its original baseline (`link["base"]`).
    """
    desc_by_id = {n["id"]: n.get("desc", n["id"]) for n in testbed["nodes"] if n["kind"] == "switch"}
    g = Graph()
    for node_id in desc_by_id.values():
        g.add_node(node_id)
    for link in testbed["links"]:
        a, b = link["a"], link["b"]
        if a not in desc_by_id or b not in desc_by_id:
            continue  # a host-facing link, not a switch-to-switch one
        now = link["now"]
        if now.get("down"):
            continue
        w = {"delay": now["delay"], "rate": now["rate"], "loss": now["loss"]}[cost]
        g.add_edge(desc_by_id[a], desc_by_id[b], float(w))
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
