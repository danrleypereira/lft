# Brief: unit tests for pca_routing. Run with: python3 -m unittest discover pca_routing/tests -v
# (stdlib unittest only - no pytest dependency, consistent with the
# assignment's "no external library does the algorithm for you" spirit; a
# test runner isn't the algorithm, but there's no reason to need one here).

from __future__ import annotations

import unittest

from ..algorithms.base import PathFinder, PathResult
from ..algorithms.bellman_ford import BellmanFordPathFinder
from ..algorithms.bfs import BFSPathFinder
from ..algorithms.dijkstra import DijkstraPathFinder
from ..graph import (
    Graph,
    load_diamond_topology,
    load_from_console_api,
    load_rnp_topology,
    path_weight,
    random_graph,
)

ALGORITHMS: list[PathFinder] = [DijkstraPathFinder(), BellmanFordPathFinder(), BFSPathFinder()]


def diverging_graph() -> Graph:
    """The textbook case where hop-count and weighted-shortest-path disagree:
    A-B-D is 2 hops at 140, A-C-X-D is 3 hops at 15. BFS must return the
    former, Dijkstra/Bellman-Ford the latter - the exact example from the
    ChatGPT analysis this design is built around.
    """
    g = Graph()
    g.add_edge("A", "B", 70)
    g.add_edge("B", "D", 70)
    g.add_edge("A", "C", 5)
    g.add_edge("C", "X", 5)
    g.add_edge("X", "D", 5)
    return g


class TestGraph(unittest.TestCase):
    def test_add_edge_is_undirected(self):
        g = Graph()
        g.add_edge("A", "B", 3.0)
        self.assertIn(("B", 3.0), g.neighbors("A"))
        self.assertIn(("A", 3.0), g.neighbors("B"))

    def test_counts(self):
        g = diverging_graph()
        self.assertEqual(g.num_nodes, 5)
        self.assertEqual(g.num_edges, 5)

    def test_path_weight(self):
        g = diverging_graph()
        self.assertEqual(path_weight(g, ["A", "B", "D"]), 140)
        self.assertEqual(path_weight(g, ["A", "C", "X", "D"]), 15)
        self.assertEqual(path_weight(g, ["A"]), 0.0)
        self.assertEqual(path_weight(g, []), 0.0)


class TestLSPConformance(unittest.TestCase):
    """One test function, run against every PathFinder subclass via
    subTest - this is the Liskov Substitution Principle made directly
    testable: every algorithm must satisfy the same postconditions from
    algorithms/base.py, or the test fails regardless of which one it is."""

    def test_every_algorithm_honors_the_shared_contract(self):
        g = diverging_graph()
        for algo in ALGORITHMS:
            with self.subTest(algorithm=algo.name):
                result = algo.find_path(g, "A", "D")
                self.assertIsInstance(result, PathResult)
                self.assertTrue(result.reachable)
                self.assertEqual(result.path[0], "A")
                self.assertEqual(result.path[-1], "D")
                self.assertEqual(result.hops, len(result.path) - 1)
                # the shared postcondition: cost always = sum of weights along
                # the path actually returned, independent of what the
                # algorithm itself searched on.
                self.assertAlmostEqual(result.cost, path_weight(g, result.path))

    def test_every_algorithm_reports_unreachable_without_raising(self):
        g = Graph()
        g.add_edge("A", "B", 1)
        g.add_node("Z")  # disconnected
        for algo in ALGORITHMS:
            with self.subTest(algorithm=algo.name):
                result = algo.find_path(g, "A", "Z")
                self.assertFalse(result.reachable)
                self.assertEqual(result.path, [])


class TestDivergingCase(unittest.TestCase):
    """The actual behavior the three algorithms are being compared for."""

    def test_bfs_prefers_fewer_hops(self):
        g = diverging_graph()
        r = BFSPathFinder().find_path(g, "A", "D")
        self.assertEqual(r.path, ["A", "B", "D"])
        self.assertEqual(r.hops, 2)
        self.assertEqual(r.cost, 140)

    def test_dijkstra_and_bellman_ford_prefer_lower_cost(self):
        g = diverging_graph()
        for algo in (DijkstraPathFinder(), BellmanFordPathFinder()):
            with self.subTest(algorithm=algo.name):
                r = algo.find_path(g, "A", "D")
                self.assertEqual(r.path, ["A", "C", "X", "D"])
                self.assertEqual(r.hops, 3)
                self.assertEqual(r.cost, 15)


class TestDijkstraBellmanFordAgree(unittest.TestCase):
    """The correctness oracle: on positive-weight graphs these two MUST
    agree on cost, because they solve the same problem by construction.
    Checked here on the real topologies and a batch of random ones."""

    def test_on_diamond_topology(self):
        g = load_diamond_topology()
        for s in g.nodes:
            for t in g.nodes:
                if s == t:
                    continue
                dij = DijkstraPathFinder().find_path(g, s, t)
                bf = BellmanFordPathFinder().find_path(g, s, t)
                self.assertAlmostEqual(dij.cost, bf.cost, msg=f"{s}->{t}")

    def test_on_rnp_topology(self):
        g = load_rnp_topology(cost="rtt")
        pairs = [("ES", "AC"), ("RJ", "RR"), ("SP", "TO"), ("BA", "RS")]
        for s, t in pairs:
            dij = DijkstraPathFinder().find_path(g, s, t)
            bf = BellmanFordPathFinder().find_path(g, s, t)
            self.assertAlmostEqual(dij.cost, bf.cost, msg=f"{s}->{t}")

    def test_on_random_graphs(self):
        for n in (10, 25, 60):
            g = random_graph(n, avg_degree=3.0, seed=n)
            nodes = sorted(g.nodes)
            dij = DijkstraPathFinder().find_path(g, nodes[0], nodes[-1])
            bf = BellmanFordPathFinder().find_path(g, nodes[0], nodes[-1])
            self.assertEqual(dij.reachable, bf.reachable)
            if dij.reachable:
                self.assertAlmostEqual(dij.cost, bf.cost, msg=f"n={n}")


class TestTopologyLoaders(unittest.TestCase):
    def test_diamond_shape(self):
        g = load_diamond_topology()
        self.assertEqual(g.num_nodes, 4)
        self.assertEqual(g.num_edges, 4)
        self.assertEqual(set(g.nodes), {"ES", "MG", "RJ", "SP"})

    def test_rnp_shape(self):
        g = load_rnp_topology()
        self.assertEqual(g.num_nodes, 27)
        self.assertEqual(g.num_edges, 44)

    def test_rnp_cost_modes_differ(self):
        rtt = load_rnp_topology(cost="rtt")
        inv = load_rnp_topology(cost="inverse_throughput")
        tp = load_rnp_topology(cost="throughput")
        # AL<->PE: real values are 100mbit (both directions) and ~3.3ms RTT -
        # three different weights for the same edge depending on cost mode,
        # none of which should coincide (a 1mbit edge would trivially give
        # 1/1 == 1 under both throughput modes, which is what tripped this
        # test up the first time, before RTT_MATRIX existed, against AL-PE's
        # old 40gbit value).
        w_rtt = next(w for a, b, w in rtt.edges() if {a, b} == {"AL", "PE"})
        w_inv = next(w for a, b, w in inv.edges() if {a, b} == {"AL", "PE"})
        w_tp = next(w for a, b, w in tp.edges() if {a, b} == {"AL", "PE"})
        self.assertAlmostEqual(w_tp, 100.0)
        self.assertAlmostEqual(w_inv, 1 / 100)
        self.assertAlmostEqual(w_rtt, 3.36)
        self.assertNotEqual(w_rtt, w_inv)
        self.assertNotEqual(w_inv, w_tp)


class TestLiveApiLoader(unittest.TestCase):
    """A small hand-built fixture matching REIN console's GET /api/testbed
    shape - exercises load_from_console_api() deterministically, without
    needing a live lft-vm/ONOS/console stack up just to run the test suite.
    The real validation against an actually-running testbed is in
    FINDINGS.md's "Live-data validation" section.
    """

    def fixture(self) -> dict:
        return {
            "nodes": [
                {"id": "s0", "kind": "switch", "desc": "AC"},
                {"id": "s1", "kind": "switch", "desc": "RO"},
                {"id": "s2", "kind": "switch", "desc": "AM"},
                {"id": "cl0", "kind": "host", "ip": "192.168.0.5", "sw": "s0"},
            ],
            "links": [
                {"a": "s0", "b": "s1", "now": {"delay": 3.51, "rate": 100.0, "loss": 0, "down": False}},
                {"a": "s1", "b": "s2", "now": {"delay": 5.0, "rate": 50.0, "loss": 0, "down": False}},
                # a down link must be skipped entirely, not just zero-weighted
                {"a": "s0", "b": "s2", "now": {"delay": 1.0, "rate": 10.0, "loss": 0, "down": True}},
                # a host-facing link (cl0 isn't a switch) must also be skipped
                {"a": "s0", "b": "cl0", "now": {"delay": 0.5, "rate": 1000.0, "loss": 0, "down": False}},
            ],
        }

    def test_builds_switch_only_graph_with_desc_names(self):
        g = load_from_console_api(self.fixture(), cost="delay")
        self.assertEqual(g.nodes, {"AC", "RO", "AM"})
        self.assertEqual(g.num_edges, 2)  # the down link and the host link are both excluded

    def test_cost_modes(self):
        delay = load_from_console_api(self.fixture(), cost="delay")
        rate = load_from_console_api(self.fixture(), cost="rate")
        w_delay = next(w for a, b, w in delay.edges() if {a, b} == {"AC", "RO"})
        w_rate = next(w for a, b, w in rate.edges() if {a, b} == {"AC", "RO"})
        self.assertAlmostEqual(w_delay, 3.51)
        self.assertAlmostEqual(w_rate, 100.0)

    def test_algorithms_run_unchanged_against_it(self):
        g = load_from_console_api(self.fixture(), cost="delay")
        for algo in ALGORITHMS:
            with self.subTest(algorithm=algo.name):
                r = algo.find_path(g, "AC", "AM")
                self.assertTrue(r.reachable)
                self.assertEqual(r.path, ["AC", "RO", "AM"])  # the only path left once AC-AM is down


class TestRandomGraph(unittest.TestCase):
    def test_connected_and_sized(self):
        g = random_graph(30, avg_degree=3.0, seed=1)
        self.assertEqual(g.num_nodes, 30)
        # connectivity: BFS from an arbitrary node reaches every other node
        bfs = BFSPathFinder()
        nodes = sorted(g.nodes)
        for target in nodes[1:]:
            r = bfs.find_path(g, nodes[0], target)
            self.assertTrue(r.reachable, f"{nodes[0]}->{target} should be reachable")


if __name__ == "__main__":
    unittest.main()
