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

## Advanced scenario — why Dijkstra (and this package, as built) stop being a good fit

The single-commodity reduction above holds only because today's deployer
routes one client's intent at a time, independently, as it arrives via
chat. The moment multiple clients must be routed **together**, under a
**shared** link-capacity budget, the problem changes shape entirely - and
this is worth presenting as its own scenario, not folded into the main
comparison, because the fix is not "turn the ILP back on."

**Why independent per-client Dijkstra breaks.** Dijkstra finds the cheapest
path for one flow; it has no notion of a link's remaining capacity or of a
second flow wanting the same link. Route 10 clients independently and
Dijkstra gives all 10 the *identical* cheapest path if their endpoints are
similar - dumping all their traffic onto one link, saturating it, while
parallel links sit idle. Re-running Dijkstra per client sequentially
("give client 1 its best path, subtract its usage, route client 2 against
what's left...") doesn't fix this either: whichever client is routed first
gets the true optimum and may consume a bottleneck link that a later
client then needs, forcing a detour it wouldn't have needed had the first
client been routed slightly less optimally. The *order* clients happen to
arrive in silently determines the outcome - not something a research
testbed should want to depend on.

**Why this is unsplittable multi-commodity flow, not just "more Dijkstra
calls".** The real problem becomes: given all clients' (source, candidate
servers) pairs at once, and a capacity on every link, choose one path per
client such that no link's total assigned traffic exceeds its capacity,
minimizing total cost. That's the multi-commodity flow problem, and
because the assignment requires *one whole path per client* (no splitting
a client's own traffic across multiple paths), it's the NP-hard
*unsplittable* variant - this is where ILP (or an equivalent combinatorial
heuristic) earns its place, for real, not as over-engineering. (Aside for
rigor: if splitting one client's own traffic across several paths were
ever acceptable, the linear-programming *relaxation* of the same problem,
with no integer constraints, is solvable in polynomial time and already
gives the optimal fractional answer - ILP only re-enters because the
answer must be one undivided path per client.)

**Why this doesn't become a fourth `PathFinder` subclass.** Its signature
isn't `find_path(graph, source, target) -> PathResult` - it needs *every*
active client's (source, candidate-targets) at once, plus per-edge
capacities, and returns a *set* of paths, not one. Forcing it into the
`PathFinder` hierarchy would mean either quietly requiring more than the
interface promises its callers, or quietly changing what it hands back -
exactly the kind of substitutability violation `algorithms/base.py`
already calls out for `supports_negative_weights`. The honest design is a
second, separate interface one level up (a `SequentialDijkstraAllocator`
that just calls `PathFinder` once per client - today's actual, uncoordinated
behavior, made explicit - alongside an `ILPAllocator` that extends
`cdn_qoe.py`'s existing formulation with real `Σ flow(i,j) ≤ capacity(i,j)`
constraints), with the deployer's own policy choosing between them
(e.g. per-client while no contention is detected, joint re-optimization
once concurrent active flows cross some threshold) - a decision for
whoever owns `cdn_qoe.py` to weigh in on, not something to build silently.

## Honest verdict

Not "just useful for the assignment" and not "a ready-to-merge replacement"
either — it's a genuine, well-evidenced engineering argument: a real, still-open
issue asks for exactly this; the current implementation already meets
the issue's letter but via much heavier machinery than the problem (as
currently scoped) requires; and this package's `DijkstraPathFinder` is a
proven drop-in for that inner loop *if* the single-commodity assumption
holds going forward - which, as shown above, is a real assumption with a
real expiration date, not a technicality. Turning the single-client case
into an actual PR is separate work - would need: a live ONOS-REST-based
topology loader (cleaner than the Karaf-CLI-scraping approach, not just a
port of it), the multi-target wrapper, and signoff from whoever owns
`cdn_qoe.py` on the
single-vs-multi-commodity question above.
