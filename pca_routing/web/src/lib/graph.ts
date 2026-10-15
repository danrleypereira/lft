// Brief: the same minimal undirected weighted graph as pca_routing/graph.py, loaded from
// src/data/rnp.json (exported from graph.py::load_rnp_topology by scripts/export_data.py).
import rnp from "../data/rnp.json";

export interface Edge { u: string; v: string; rtt: number; capacity: number }
export interface GeoNode { id: string; lat: number; lon: number }

export class Graph {
  nodes: string[] = [];
  private adj = new Map<string, [string, number][]>();
  private w = new Map<string, number>();

  addEdge(u: string, v: string, weight: number) {
    for (const n of [u, v]) if (!this.adj.has(n)) { this.adj.set(n, []); this.nodes.push(n); }
    this.adj.get(u)!.push([v, weight]);
    this.adj.get(v)!.push([u, weight]);
    this.w.set(edgeKey(u, v), weight);
  }
  neighbors(u: string): [string, number][] { return this.adj.get(u) ?? []; }
  /** each undirected edge once, u < v (same order as Graph.edges() in Python) */
  edges(): [string, string, number][] {
    const out: [string, string, number][] = [];
    for (const [u, nbrs] of this.adj) for (const [v, w] of nbrs) if (u < v) out.push([u, v, w]);
    return out;
  }
  get numNodes() { return this.nodes.length; }
  weight(u: string, v: string) { return this.w.get(edgeKey(u, v))!; }
}

export const edgeKey = (u: string, v: string) => (u < v ? `${u}|${v}` : `${v}|${u}`);

export function pathWeight(g: Graph, path: string[]): number {
  let s = 0;
  for (let i = 0; i + 1 < path.length; i++) s += g.weight(path[i], path[i + 1]);
  return s;
}

/** Mirrors graph.py::load_rnp_topology("rtt"): weight = measured RTT in ms. */
export function loadRnpTopology(): Graph {
  const g = new Graph();
  for (const e of rnp.edges as Edge[]) g.addEdge(e.u, e.v, e.rtt);
  return g;
}

export const geoNodes: GeoNode[] = rnp.nodes;
export const edgeList: Edge[] = rnp.edges as Edge[];
export const capacityOf = new Map(edgeList.map((e) => [edgeKey(e.u, e.v), e.capacity]));
