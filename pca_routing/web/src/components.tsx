// Brief: SVG map of the RNP backbone over simplified Brazilian state outlines. Pure presentation:
// the pages decide which paths to draw (and in which color); this only projects lon/lat and draws.
import brazil from "./data/brazil.json";
import { capacityOf, edgeKey, edgeList, geoNodes } from "./lib/graph";
import { edgesOf } from "./lib/joint";

const W = 640, H = 640, LON0 = -74.5, LON1 = -33.5, LAT0 = 6, LAT1 = -34.5;
const proj = (lon: number, lat: number): [number, number] => [((lon - LON0) / (LON1 - LON0)) * W, ((lat - LAT0) / (LAT1 - LAT0)) * H];
const pos = new Map(geoNodes.map((n) => [n.id, proj(n.lon, n.lat)]));

export interface Overlay { path: string[]; color: string; width?: number; dash?: string; offset?: number; label?: string }

export function MapView({ overlays, overloaded = [], endpoints = [], loads }: {
  overlays: Overlay[]; overloaded?: string[]; endpoints?: { id: string; color: string; tag: string }[]; loads?: Map<string, number>;
}) {
  const ends = new Map(endpoints.map((e) => [e.id, e]));
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="map" role="img" aria-label="Map of Brazil with the RNP topology">
      {(brazil as { sigla: string; rings: number[][][] }[]).flatMap((s) =>
        s.rings.map((r, i) => (
          <polygon key={`${s.sigla}${i}`} points={r.map(([x, y]) => proj(x, y).join(",")).join(" ")} className="state" />
        )),
      )}
      {edgeList.map((e) => {
        const [x1, y1] = pos.get(e.u)!, [x2, y2] = pos.get(e.v)!;
        const k = edgeKey(e.u, e.v), bad = overloaded.includes(k);
        return (
          <g key={k}>
            <line x1={x1} y1={y1} x2={x2} y2={y2} className={bad ? "link bad" : "link"} strokeWidth={bad ? 4 : 1 + Math.log10(e.capacity)} />
            {loads?.has(k) && (
              <text x={(x1 + x2) / 2} y={(y1 + y2) / 2 - 3} className={bad ? "load bad" : "load"}>{loads.get(k)}/{capacityOf.get(k)}</text>
            )}
          </g>
        );
      })}
      {overlays.map((o, oi) =>
        edgesOf(o.path).map((_, i) => {
          const [x1, y1] = pos.get(o.path[i])!, [x2, y2] = pos.get(o.path[i + 1])!;
          const len = Math.hypot(x2 - x1, y2 - y1) || 1, off = o.offset ?? 0;
          const nx = (-(y2 - y1) / len) * off, ny = ((x2 - x1) / len) * off;
          return <line key={`${oi}-${i}`} x1={x1 + nx} y1={y1 + ny} x2={x2 + nx} y2={y2 + ny} stroke={o.color} strokeWidth={o.width ?? 4} strokeDasharray={o.dash} strokeLinecap="round" opacity={0.9} />;
        }),
      )}
      {geoNodes.map((n) => {
        const [x, y] = pos.get(n.id)!, e = ends.get(n.id);
        return (
          <g key={n.id}>
            <circle cx={x} cy={y} r={e ? 9 : 5} className="node" style={e ? { fill: e.color } : undefined} />
            <text x={x} y={y + (e ? 3.5 : -8)} className={e ? "tag" : "name"}>{e ? e.tag : n.id}</text>
          </g>
        );
      })}
    </svg>
  );
}

export const NodeSelect = ({ value, onChange, label }: { value: string; onChange: (v: string) => void; label: string }) => (
  <label>{label}
    <select value={value} onChange={(e) => onChange(e.target.value)}>
      {geoNodes.map((n) => <option key={n.id}>{n.id}</option>)}
    </select>
  </label>
);

export const fmt = (n: number) => (Number.isFinite(n) ? n.toFixed(1) : "∞");
