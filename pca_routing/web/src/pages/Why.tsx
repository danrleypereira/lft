export default function Why() {
  return (
    <main className="prose">
      <h2>Why coordinate flows?</h2>
      <p>
        With <b>one</b> source/target pair, Dijkstra is optimal. With <b>two</b> unsplittable flows that share
        finite-capacity links, routing each one independently can overload a shared link even when alternative paths
        exist. The joint problem is integral multi-commodity flow: Even, Itai and Shamir (1976) proved it is already
        NP-complete with only two commodities.
      </p>
      <p>
        In the <i>Two flows</i> tab, <b>naive</b> runs Dijkstra per pair; <b>coordinated</b> picks one whole path per
        flow minimizing total RTT under every link's capacity. If splitting a flow were acceptable (the LP
        relaxation), the problem would be a linear program, solvable in polynomial time.
      </p>
      <p>
        Same interface, different algorithm: <code>find_path(graph, source, target)</code> swaps <code>PathFinder</code>
        subclasses without changing the caller (LSP); the joint allocator is a separate interface because it takes all
        flows at once. Details: <code>pca_routing/FINDINGS.md</code> and <code>assignment/complexity/why-np-hard.md</code>.
      </p>
    </main>
  );
}
