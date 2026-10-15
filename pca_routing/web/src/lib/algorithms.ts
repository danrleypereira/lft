// Brief: Dijkstra / Bellman-Ford / BFS ported line-for-line from pca_routing/algorithms/*.py,
// including the comparisons/relaxations counters, so the side panel shows the same numbers the
// report does. Same PathFinder contract: never throws for "no path"; cost = sum of edge
// weights along the path for ALL three (BFS included).
import { Graph, pathWeight } from "./graph";

export interface PathResult {
  algorithm: string; path: string[]; reachable: boolean; hops: number; cost: number;
  comparisons: number; relaxations: number; nodesVisited: number;
}
export type PathFinder = (g: Graph, source: string, target: string) => PathResult;

function reconstruct(prev: Map<string, string | null>, source: string, target: string): string[] {
  if (!prev.has(target)) return [];
  const path: string[] = [];
  let n: string | null = target;
  while (n !== null) { path.push(n); n = prev.get(n) ?? null; }
  path.reverse();
  return path[0] === source ? path : [];
}

function result(algorithm: string, g: Graph, path: string[], c: number, r: number, v: number): PathResult {
  return {
    algorithm, path, reachable: path.length > 0, hops: Math.max(path.length - 1, 0),
    cost: path.length ? pathWeight(g, path) : Infinity, comparisons: c, relaxations: r, nodesVisited: v,
  };
}

export const dijkstra: PathFinder = (g, source, target) => {
  const dist = new Map(g.nodes.map((n) => [n, Infinity]));
  const prev = new Map<string, string | null>(g.nodes.map((n) => [n, null]));
  dist.set(source, 0);
  const visited = new Set<string>();
  let comparisons = 0, relaxations = 0, nodesVisited = 0;
  for (let i = 0; i < g.numNodes; i++) {
    let u: string | null = null, best = Infinity;
    for (const n of g.nodes) {
      comparisons++;
      if (!visited.has(n) && dist.get(n)! < best) { u = n; best = dist.get(n)!; }
    }
    if (u === null) break;
    visited.add(u); nodesVisited++;
    if (u === target) break;
    for (const [v, w] of g.neighbors(u)) {
      comparisons++;
      if (visited.has(v)) continue;
      relaxations++;
      if (dist.get(u)! + w < dist.get(v)!) { dist.set(v, dist.get(u)! + w); prev.set(v, u); }
    }
  }
  return result("dijkstra", g, reconstruct(prev, source, target), comparisons, relaxations, nodesVisited);
};

export const bellmanFord: PathFinder = (g, source, target) => {
  const dist = new Map(g.nodes.map((n) => [n, Infinity]));
  const prev = new Map<string, string | null>(g.nodes.map((n) => [n, null]));
  dist.set(source, 0);
  const directed: [string, string, number][] = [];
  for (const [u, v, w] of g.edges()) { directed.push([u, v, w]); directed.push([v, u, w]); }
  let comparisons = 0, relaxations = 0, passes = 0;
  for (let i = 0; i < Math.max(g.numNodes - 1, 0); i++) {
    passes++;
    let updated = false;
    for (const [u, v, w] of directed) {
      comparisons++;
      if (dist.get(u)! + w < dist.get(v)!) { dist.set(v, dist.get(u)! + w); prev.set(v, u); updated = true; relaxations++; }
    }
    if (!updated) break;
  }
  return result("bellman_ford", g, reconstruct(prev, source, target), comparisons, relaxations, passes);
};

export const bfs: PathFinder = (g, source, target) => {
  const prev = new Map<string, string | null>([[source, null]]);
  const queue = [source];
  let comparisons = 0, nodesVisited = 0;
  for (let head = 0; head < queue.length; head++) {
    const u = queue[head];
    nodesVisited++;
    if (u === target) break;
    for (const [v] of g.neighbors(u)) {
      comparisons++;
      if (!prev.has(v)) { prev.set(v, u); queue.push(v); }
    }
  }
  return result("bfs", g, reconstruct(prev, source, target), comparisons, 0, nodesVisited);
};

export const ALGORITHMS: { id: string; label: string; color: string; find: PathFinder }[] = [
  { id: "dijkstra", label: "Dijkstra", color: "#2563eb", find: dijkstra },
  { id: "bellman_ford", label: "Bellman-Ford", color: "#d97706", find: bellmanFord },
  { id: "bfs", label: "BFS (hops)", color: "#16a34a", find: bfs },
];
