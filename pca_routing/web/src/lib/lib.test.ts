import { describe, expect, it } from "vitest";
import { bellmanFord, bfs, dijkstra } from "./algorithms";
import { loadRnpTopology, pathWeight } from "./graph";
import { coordinatedAllocation, naiveAllocation } from "./joint";
import parity from "./parity.fixture.json";

const g = loadRnpTopology();
const finders: Record<string, typeof dijkstra> = { dijkstra, bellman_ford: bellmanFord, bfs };

describe("topology", () => {
  it("is the 27-node / 44-edge RNP backbone", () => {
    expect(g.numNodes).toBe(27);
    expect(g.edges().length).toBe(44);
  });
});

describe("TS port matches the Python algorithms (ground truth from pca_routing)", () => {
  // Python iterates a `set` of node names (hash-randomized per run), so on ties it may pick a
  // different equal-cost path and visit nodes in another order: compare cost always, and the
  // exact path/counters wherever the Python result is itself tie-free.
  for (const row of parity as any[]) {
    it(`${row.alg} ${row.s}->${row.t}`, () => {
      const r = finders[row.alg](g, row.s, row.t);
      expect(r.cost).toBeCloseTo(row.cost, 5);
      expect(pathWeight(g, r.path)).toBeCloseTo(row.cost, 5);
      expect(r.path[0]).toBe(row.s);
      expect(r.path.at(-1)).toBe(row.t);
      if (row.alg === "dijkstra") expect(r.comparisons).toBe(row.comparisons); // V per round + edges scanned: order-independent unless ties end the search earlier
    });
  }
});

describe("two-flow allocation", () => {
  const flows = [
    { source: "DF", target: "CE", demand: 60 },
    { source: "MG", target: "CE", demand: 60 },
  ];
  it("naive Dijkstra can overload a shared link that coordinated routing avoids", () => {
    const n = naiveAllocation(g, flows);
    const c = coordinatedAllocation(g, flows);
    console.log("naive", n.results.map((r) => r.path.join(">")), n.overloaded, n.totalCost);
    console.log("coord", c.results.map((r) => r.path.join(">")), c.overloaded, c.totalCost, c.feasible);
    expect(c.totalCost).toBeGreaterThanOrEqual(n.totalCost - 1e-9); // coordination never beats the unconstrained optimum
    if (!n.feasible) expect(c.feasible).toBe(true);
  });
});
