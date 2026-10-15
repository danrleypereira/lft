// Brief: the two-flow allocators behind the "naive vs coordinated" toggle.
//  - naive:       Dijkstra solved independently per (source,target) pair (what the deployer does today)
//  - coordinated: pick ONE whole path per pair minimizing total RTT subject to
//                 sum(demand of flows on a link) <= capacity(link) - the unsplittable two-commodity
//                 problem (NP-complete in general, Even-Itai-Shamir 1976). Solved exactly here by
//                 enumerating simple paths and branch-and-bound over the pair of choices; with 27 nodes
//                 / 44 links the path sets are small, so this is the exact optimum an ILP would return.
//                 (The LP relaxation - splittable flow - is a different, polynomial problem: not shown.)
import { Graph, capacityOf, edgeKey, pathWeight } from "./graph";
import { dijkstra, PathResult } from "./algorithms";

export interface Flow { source: string; target: string; demand: number }
export interface Allocation {
  mode: "naive" | "coordinated";
  results: PathResult[];
  loads: Map<string, number>;       // edge key -> Mbit assigned
  overloaded: string[];             // edge keys with load > capacity
  totalCost: number;
  feasible: boolean;
  exact?: boolean;                  // coordinated only: false if the path enumeration hit its cap
  pathsConsidered?: number[];
}

const MAX_HOPS = 14;
const MAX_PATHS = 4000;

export function edgesOf(path: string[]): string[] {
  const out: string[] = [];
  for (let i = 0; i + 1 < path.length; i++) out.push(edgeKey(path[i], path[i + 1]));
  return out;
}

export function computeLoads(paths: string[][], flows: Flow[]) {
  const loads = new Map<string, number>();
  paths.forEach((p, i) => edgesOf(p).forEach((e) => loads.set(e, (loads.get(e) ?? 0) + flows[i].demand)));
  const overloaded = [...loads].filter(([e, l]) => l > (capacityOf.get(e) ?? Infinity)).map(([e]) => e);
  return { loads, overloaded };
}

function shell(mode: Allocation["mode"], g: Graph, paths: string[][], flows: Flow[], extra: Partial<Allocation> = {}): Allocation {
  const { loads, overloaded } = computeLoads(paths, flows);
  const results: PathResult[] = paths.map((p, i) => ({
    algorithm: mode, path: p, reachable: p.length > 0, hops: Math.max(p.length - 1, 0),
    cost: p.length ? pathWeight(g, p) : Infinity, comparisons: 0, relaxations: 0, nodesVisited: 0,
    ...(mode === "naive" ? dijkstraCounters(g, flows[i]) : {}),
  }));
  return { mode, results, loads, overloaded, totalCost: results.reduce((s, r) => s + r.cost, 0), feasible: overloaded.length === 0, ...extra };
}

function dijkstraCounters(g: Graph, f: Flow) {
  const r = dijkstra(g, f.source, f.target);
  return { comparisons: r.comparisons, relaxations: r.relaxations, nodesVisited: r.nodesVisited };
}

export function naiveAllocation(g: Graph, flows: Flow[]): Allocation {
  return shell("naive", g, flows.map((f) => dijkstra(g, f.source, f.target).path), flows);
}

/** all simple source->target paths with their cost, cheapest first (capped). */
function enumeratePaths(g: Graph, source: string, target: string, demand: number) {
  const out: { path: string[]; cost: number; edges: string[] }[] = [];
  let capped = false;
  const seen = new Set([source]);
  const stack = [source];
  const dfs = (u: string, cost: number) => {
    if (out.length >= MAX_PATHS) { capped = true; return; }
    if (u === target) { out.push({ path: [...stack], cost, edges: edgesOf(stack) }); return; }
    if (stack.length > MAX_HOPS) return;
    for (const [v, w] of g.neighbors(u)) {
      if (seen.has(v)) continue;
      if (demand > (capacityOf.get(edgeKey(u, v)) ?? Infinity)) continue; // a link too thin for this flow alone
      seen.add(v); stack.push(v);
      dfs(v, cost + w);
      stack.pop(); seen.delete(v);
    }
  };
  if (source === target) return { paths: [{ path: [source], cost: 0, edges: [] as string[] }], capped };
  dfs(source, 0);
  return { paths: out.sort((a, b) => a.cost - b.cost), capped };
}

export function coordinatedAllocation(g: Graph, flows: Flow[]): Allocation {
  const enums = flows.map((f) => enumeratePaths(g, f.source, f.target, f.demand));
  const [A, B] = [enums[0].paths, enums[1].paths];
  let best: { a: number; b: number; cost: number } | null = null;
  const cap = (e: string) => capacityOf.get(e) ?? Infinity;
  for (let i = 0; i < A.length; i++) {
    if (best && A[i].cost + (B[0]?.cost ?? 0) >= best.cost) break; // sorted: nothing later can win
    for (let j = 0; j < B.length; j++) {
      const total = A[i].cost + B[j].cost;
      if (best && total >= best.cost) break;
      const shared = A[i].edges.filter((e) => B[j].edges.includes(e));
      if (shared.every((e) => flows[0].demand + flows[1].demand <= cap(e))) { best = { a: i, b: j, cost: total }; break; }
    }
  }
  const exact = !enums[0].capped && !enums[1].capped;
  if (!best) { // no jointly feasible pair of whole paths: fall back to the naive paths, flagged infeasible
    const n = naiveAllocation(g, flows);
    return { ...n, mode: "coordinated", exact, pathsConsidered: [A.length, B.length] };
  }
  return shell("coordinated", g, [A[best.a].path, B[best.b].path], flows, { exact, pathsConsidered: [A.length, B.length] });
}
