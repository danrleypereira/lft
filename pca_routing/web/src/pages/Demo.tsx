// Brief: the class demo. Two modes on the same RNP map:
//   1. "Algoritmos": one (source,target) pair, Dijkstra / Bellman-Ford / BFS side by side, each path in
//      its own color with the PathResult counters (cost, hops, comparisons, relaxations).
//   2. "Two flows": two concurrent pairs with a per-flow demand; naive (Dijkstra per pair) vs
//      coordinated (joint, capacity-aware) so the paths visibly diverge where a shared link overflows.
import { useMemo, useState } from "react";
import { fmt, MapView, NodeSelect, Overlay } from "../components";
import { ALGORITHMS } from "../lib/algorithms";
import { loadRnpTopology } from "../lib/graph";
import { coordinatedAllocation, naiveAllocation } from "../lib/joint";

const g = loadRnpTopology();
const FLOW_COLORS = ["#7c3aed", "#e11d48"];

export default function Demo() {
  const [mode, setMode] = useState<"algos" | "flows">("flows");
  const [a, setA] = useState({ s: "AL", t: "SP", d: 60 });
  const [b, setB] = useState({ s: "DF", t: "SP", d: 60 });
  const [alloc, setAlloc] = useState<"naive" | "coordinated">("naive");

  const flows = useMemo(() => [
    { source: a.s, target: a.t, demand: a.d },
    { source: b.s, target: b.t, demand: b.d },
  ], [a, b]);
  const algoResults = useMemo(() => ALGORITHMS.map((x) => ({ ...x, r: x.find(g, a.s, a.t) })), [a.s, a.t]);
  const naive = useMemo(() => naiveAllocation(g, flows), [flows]);
  const coord = useMemo(() => coordinatedAllocation(g, flows), [flows]);
  const shown = alloc === "naive" ? naive : coord;

  const overlays: Overlay[] = mode === "algos"
    ? algoResults.map((x, i) => ({ path: x.r.path, color: x.color, width: 4, offset: (i - 1) * 3 }))
    : shown.results.map((r, i) => ({ path: r.path, color: FLOW_COLORS[i], width: 5, offset: (i - 0.5) * 4 }));
  const endpoints = mode === "algos"
    ? [{ id: a.s, color: "#111", tag: "S" }, { id: a.t, color: "#111", tag: "T" }]
    : [{ id: a.s, color: FLOW_COLORS[0], tag: "A" }, { id: a.t, color: FLOW_COLORS[0], tag: "A" }, { id: b.s, color: FLOW_COLORS[1], tag: "B" }, { id: b.t, color: FLOW_COLORS[1], tag: "B" }];

  return (
    <main className="layout">
      <section>
        <MapView overlays={overlays} endpoints={endpoints} overloaded={mode === "flows" ? shown.overloaded : []} loads={mode === "flows" ? shown.loads : undefined} />
      </section>
      <aside>
        <div className="tabs">
          <button className={mode === "algos" ? "on" : ""} onClick={() => setMode("algos")}>Algorithms (1 pair)</button>
          <button className={mode === "flows" ? "on" : ""} onClick={() => setMode("flows")}>Two flows</button>
        </div>

        <fieldset style={{ borderColor: FLOW_COLORS[0] }}>
          <legend>{mode === "flows" ? "Flow A" : "Source → target"}</legend>
          <NodeSelect label="source" value={a.s} onChange={(s) => setA({ ...a, s })} />
          <NodeSelect label="target" value={a.t} onChange={(t) => setA({ ...a, t })} />
          {mode === "flows" && <Demand v={a.d} on={(d) => setA({ ...a, d })} />}
        </fieldset>

        {mode === "flows" && (
          <fieldset style={{ borderColor: FLOW_COLORS[1] }}>
            <legend>Flow B</legend>
            <NodeSelect label="source" value={b.s} onChange={(s) => setB({ ...b, s })} />
            <NodeSelect label="target" value={b.t} onChange={(t) => setB({ ...b, t })} />
            <Demand v={b.d} on={(d) => setB({ ...b, d })} />
          </fieldset>
        )}

        {mode === "algos" ? (
          <table>
            <thead><tr><th>algorithm</th><th>RTT (ms)</th><th>hops</th><th>comparisons</th><th>relaxations</th></tr></thead>
            <tbody>
              {algoResults.map((x) => (
                <tr key={x.id}>
                  <td><i style={{ background: x.color }} />{x.label}</td>
                  <td>{fmt(x.r.cost)}</td><td>{x.r.hops}</td><td>{x.r.comparisons}</td><td>{x.r.relaxations}</td>
                  <td className="path">{x.r.reachable ? x.r.path.join(" → ") : "no path"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <>
            <div className="toggle">
              <button className={alloc === "naive" ? "on" : ""} onClick={() => setAlloc("naive")}>Naive: Dijkstra per pair</button>
              <button className={alloc === "coordinated" ? "on" : ""} onClick={() => setAlloc("coordinated")}>Coordinated: exact, joint</button>
            </div>
            <Summary title="Naive (Dijkstra per pair)" al={naive} active={alloc === "naive"} />
            <Summary title="Coordinated (joint, one whole path per flow)" al={coord} active={alloc === "coordinated"} />
            <p className="note">
              Link labels: <b>load/capacity</b> in Mbit. Red links exceed their capacity.
              “Coordinated” picks one whole path per flow minimizing total RTT under the link capacities — the unsplittable
              multi-commodity flow problem (NP-complete even with 2 flows); with 27 nodes the enumeration is exact.
            </p>
          </>
        )}
      </aside>
    </main>
  );
}

const Demand = ({ v, on }: { v: number; on: (n: number) => void }) => (
  <label>demand: {v} Mbit
    <input type="range" min={5} max={150} step={5} value={v} onChange={(e) => on(+e.target.value)} />
  </label>
);

function Summary({ title, al, active }: { title: string; al: ReturnType<typeof naiveAllocation>; active: boolean }) {
  return (
    <div className={`card ${active ? "active" : ""}`}>
      <h4>{title}</h4>
      <p className={al.feasible ? "ok" : "bad"}>
        {al.feasible ? "✓ respects every capacity" : `✗ ${al.overloaded.length ? "overloads: " + al.overloaded.join(", ") : "no feasible solution"}`}
        {" · "}total RTT {fmt(al.totalCost)} ms{al.mode === "coordinated" && al.exact === false ? " (path enumeration truncated)" : ""}
      </p>
      {al.results.map((r, i) => (
        <p key={i} className="path"><i style={{ background: FLOW_COLORS[i] }} />{r.path.join(" → ")} <span>({fmt(r.cost)} ms, {r.hops} hops)</span></p>
      ))}
    </div>
  );
}
