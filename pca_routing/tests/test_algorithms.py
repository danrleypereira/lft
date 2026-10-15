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
from ..graph import Graph, load_diamond_topology, load_rnp_topology, path_weight, random_graph

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
        g = load_rnp_topology(cost="inverse_capacity")
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
        self.assertEqual(g.num_nodes, 30)
        self.assertEqual(g.num_edges, 50)

    def test_rnp_cost_modes_differ(self):
        inv = load_rnp_topology(cost="inverse_capacity")
        cap = load_rnp_topology(cost="capacity")
        # AL<->PE is a real 40gbit link: 1/40 under inverse_capacity vs. 40
        # under capacity - these must differ (a 1gbit edge would trivially
        # give 1/1 == 1 under both modes, which is what tripped this test up
        # the first time).
        w_inv = next(w for a, b, w in inv.edges() if {a, b} == {"AL", "PE"})
        w_cap = next(w for a, b, w in cap.edges() if {a, b} == {"AL", "PE"})
        self.assertAlmostEqual(w_inv, 1 / 40)
        self.assertAlmostEqual(w_cap, 40.0)
        self.assertNotEqual(w_inv, w_cap)


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
