# Findings — does this implementation matter beyond the assignment?

Short answer: **yes, more than expected** — not as a replacement for REIN's
real solver wholesale, but as a strong, defensible case that its *inner
loop* is solving plain shortest path with much heavier machinery than it
needs. Full reasoning below, because the honest answer has real caveats.

## The open issue

`UnB-COMNET/lft#10`, "Função de Cálculo do melhor Caminho" ("Best-path
calculation function"), opened 2025-11-23, still open, assigned to
`gustavo978`, zero comments since. Its acceptance criteria, translated:

> As a Researcher, I want to run a `MelhorCaminhoQoE` function using the
> topology matrix and the sets of nodes of interest, so the optimal
> Client→Server path maximizing QoE is determined mathematically.
> - Accepts the subset of hosts defined as "Clients" and the available servers.
> - Returns an ordered list of nodes/links representing the chosen path.
> - Deterministic: same topology + same client-server pair ⇒ same result,
>   unless the research has an explicit stochastic component.

That's almost exactly `pca_routing`'s `PathFinder.find_path()` contract.

## It's already implemented — just not with a graph algorithm

`REIN/deployer/services/cdn_qoe.py::solve_shortest_path_with_constraints()`
already does this, in production, for the `cdn-qoe` intent. It:

- Builds the topology live: scrapes ONOS's Karaf CLI (`link-latencies`,
  `links` over `docker exec -t c1 .../bin/client`) with regex, cross-
  references `docker inspect`/`ovs-vsctl` to map devices to PoPs.
- Formulates the path as a **min-cost flow ILP** (Google OR-Tools, SCIP
  backend): one binary variable per edge, flow-conservation constraints,
  solved once per candidate target server, cheapest wins.
- Depends on `ortools`, `numpy`, `networkx` (the last two barely used),
  `matplotlib` (imported, unused in this file).

## The actual finding: the ILP is solving plain shortest path

Look at the objective:

```python
obj.SetCoefficient(var, aij[i][j])   # a * normalized_RTT[i][j], per edge
obj.SetOffset(-b * ntx[t])           # a single number, per TARGET - not per edge
```

The only per-*edge* term is `a * RTT[i][j]`. The throughput term (`b * tx`)
is a **flat constant for the whole candidate target**, not something that
varies along the path — it never influences *which edges* the solver
picks, only the final comparison between different candidate servers
*after* each one's shortest path is already found. Which means: for a
fixed target, this ILP's own objective reduces to

> minimize Σ RTT(i, j) along the path from source to target

— textbook weighted shortest path. `DijkstraPathFinder.find_path()` solves
the identical problem, for the identical graph, with a provably identical
result (both reach the true optimum; there's nothing to approximate), in
polynomial time, with zero external solver, and in a form that's directly
inspectable (a path, not a solver's internal certificate). The multi-target
loop around it — try each candidate server, keep the best
`a·RTT − b·tx` — doesn't need to change at all; only the per-target inner
solve would swap from "build an ILP, call SCIP, solve" to
`DijkstraPathFinder().find_path(graph, source, target)`.

**Caveat, stated plainly**: this reduction holds for the code *as it
stands today* — one commodity (one client's flow) at a time, no shared
link-capacity constraints across simultaneously-routed clients. If the
real intent is eventually to route several clients at once under a shared
capacity budget per link, that genuinely needs multi-commodity flow /ILP
machinery Dijkstra alone can't give you. Worth asking Arthur or gustavo978
directly whether that's actually planned, rather than assuming either way.

## A second, independent correctness concern in the existing code

```python
# Fractional ms must be accepted: "--- 4.38ms" fails a \d+ match entirely,
# so the link silently keeps 0.0 and the solver treats it as a free hop.
pattern = r"src=(of:[a-f0-9]+)/\d+, dst=(of:[a-f0-9]+)/\d+.*--- (\d+(?:\.\d+)?)ms"
```

That comment is the previous author documenting a bug they found and
patched: a fractional-ms link latency that doesn't match a regex is
silently treated as **zero cost** rather than erroring — the solver would
then happily route traffic across what it thinks is a free, instant link.
The regex shown already has the `(?:\.\d+)?` fix, so this specific case is
handled — but it's a sign this whole path (scraping CLI text output with
regexes to build a cost matrix) is fragile in a way a typed ONOS REST call
wouldn't be, and worth keeping an eye on for other unhandled output shapes.

## Where ONOS's own southbound path service fits (the other half of the question)

Separately, the deployer *also* calls ONOS's own built-in path endpoint
directly — `GET /onos/v1/paths/{src}/{dst}` — for the "middlebox"
service-chaining logic (`onos.py` lines ~244, ~414, ~450), not for
`cdn-qoe`. This is ONOS's own `TopologyService`, which by default computes
shortest paths by **hop count** (unweighted BFS-equivalent) unless a
custom `LinkWeigher` is registered — i.e., exactly the `fwd`-mode behavior
this project's own `BFSPathFinder` models, and exactly why `ospf` mode
(link-state, Dijkstra-based per RFC 2328) is the other point of comparison
in `DESIGN.md`. So all three of this package's algorithms map onto
something real and already running in this stack:

| `pca_routing` algorithm | Maps onto |
|---|---|
| `BFSPathFinder` | ONOS's default hop-count path service, used by the deployer's middlebox chaining and by `fwd` mode |
| `DijkstraPathFinder` | What `ospf` mode already does (RFC 2328), and what `cdn_qoe.py`'s ILP is *provably equivalent to*, per-target |
| `BellmanFordPathFinder` | The required literature comparison for the assignment; not currently used anywhere in REIN itself |

## Honest verdict

Not "just useful for the assignment" and not "a ready-to-merge replacement"
either — it's a genuine, well-evidenced engineering argument: a real, still-open
issue asks for exactly this; the current implementation already meets
the issue's letter but via much heavier machinery than the problem (as
currently scoped) requires; and this package's `DijkstraPathFinder` is a
proven drop-in for that inner loop *if* the single-commodity assumption
holds going forward. Turning that into an actual PR is separate work -
would need: a live ONOS-REST-based topology loader (cleaner than the
Karaf-CLI-scraping approach, not just a port of it), the multi-target
wrapper, and signoff from whoever owns `cdn_qoe.py` on the
single-vs-multi-commodity question above.
