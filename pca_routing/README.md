# pca_routing

Shortest-path routing algorithms (Dijkstra, Bellman-Ford, BFS) implemented
from scratch for the "Design and Complexity of Algorithms" assignment, run
over this project's own topology data. See [`DESIGN.md`](DESIGN.md) for the
architecture, the Liskov Substitution Principle design, and why Dijkstra vs.
Bellman-Ford (not BFS vs. Dijkstra) is the graded comparison.

## Run it

```bash
# from the repo root, with the project's uv venv active
python3 -m pca_routing.experiment          # diamond + RNP instances, then the scaling experiment
python3 -m unittest discover -s pca_routing/tests -t . -v
```

No third-party library implements any part of the algorithms themselves —
only the stdlib (`heapq` is not even used; see `DESIGN.md`'s complexity
section for why).
