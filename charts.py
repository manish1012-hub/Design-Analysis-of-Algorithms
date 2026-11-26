"""Phase 4: Generate runtime and optimality comparison charts using Matplotlib."""

from __future__ import annotations

from pathlib import Path


def generate_charts(benchmark_data: dict[str, list[dict[str, object]]], charts_dir: str | Path = "results/charts") -> list[Path]:
    """Render PNG performance charts for sorting, knapsack, routing, and pipeline steps."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir = Path(charts_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")

    created: list[Path] = []

    # 1. Sorting Runtime Comparison
    sort_rows = benchmark_data["sorting"]
    xs = [r["n_parcels"] for r in sort_rows]
    fig, ax = plt.subplots(figsize=(8, 4.8), dpi=150)
    ax.plot(xs, [r["merge_sort_ms"] for r in sort_rows], marker="o", linewidth=2, label="Merge Sort O(n log n)")
    ax.plot(xs, [r["quick_sort_ms"] for r in sort_rows], marker="s", linewidth=2, label="Quick Sort O(n log n)")
    ax.plot(xs, [r["insertion_sort_ms"] for r in sort_rows], marker="^", linewidth=2, label="Insertion Sort O(n^2)")
    ax.set_title("Phase 2A: Parcel Sorting Runtime Comparison")
    ax.set_xlabel("Number of Parcels (n)")
    ax.set_ylabel("Execution Time (ms)")
    ax.legend()
    fig.tight_layout()
    p1 = out_dir / "sorting_runtime.png"
    fig.savefig(p1)
    plt.close(fig)
    created.append(p1)

    # 2. Knapsack Runtime & Value Optimality
    knap_rows = benchmark_data["knapsack"]
    labels = [f"n={r['n_parcels']}\nW={r['capacity']}" for r in knap_rows]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.8), dpi=150)

    ax1.plot(labels, [r["dp_2d_ms"] for r in knap_rows], marker="o", linewidth=2, label="2D DP O(nW)")
    ax1.plot(labels, [r["dp_1d_ms"] for r in knap_rows], marker="s", linewidth=2, label="1D Space-Opt DP O(nW)")
    ax1.plot(labels, [r["greedy_ms"] for r in knap_rows], marker="^", linewidth=2, label="Greedy O(n log n)")
    ax1.set_title("Knapsack Packing Runtime")
    ax1.set_xlabel("Problem Scale (Parcels, Capacity)")
    ax1.set_ylabel("Execution Time (ms)")
    ax1.legend()

    x_idx = range(len(labels))
    width = 0.36
    ax2.bar([i - width / 2 for i in x_idx], [r["dp_optimal_value"] for r in knap_rows], width, label="0/1 DP (Exact Optimal)")
    ax2.bar([i + width / 2 for i in x_idx], [r["greedy_value"] for r in knap_rows], width, label="Greedy Heuristic")
    ax2.set_xticks(list(x_idx))
    ax2.set_xticklabels(labels)
    ax2.set_title("Packing Value: Exact DP vs Greedy")
    ax2.set_xlabel("Problem Scale")
    ax2.set_ylabel("Total Packed Value")
    ax2.legend()

    fig.tight_layout()
    p2 = out_dir / "knapsack_comparison.png"
    fig.savefig(p2)
    plt.close(fig)
    created.append(p2)

    # 3. Routing Runtime & Distance Optimization
    route_rows = benchmark_data["routing"]
    v_vals = [r["n_nodes"] for r in route_rows]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.8), dpi=150)

    ax1.plot(v_vals, [r["nn_tsp_ms"] for r in route_rows], marker="o", linewidth=2, label="Dijkstra + NN TSP")
    ax1.plot(v_vals, [r["nn_two_opt_ms"] for r in route_rows], marker="s", linewidth=2, label="Dijkstra + NN + 2-Opt")
    ax1.set_title("Phase 3: Routing Runtime Scaling")
    ax1.set_xlabel("Customer Graph Nodes (V)")
    ax1.set_ylabel("Execution Time (ms)")
    ax1.legend()

    ax2.plot(v_vals, [r["nn_distance"] for r in route_rows], marker="o", linewidth=2, label="Nearest-Neighbor TSP")
    ax2.plot(v_vals, [r["two_opt_distance"] for r in route_rows], marker="s", linewidth=2, label="NN + 2-Opt Optimized")
    ax2.set_title("Total Route Distance: NN vs 2-Opt")
    ax2.set_xlabel("Customer Graph Nodes (V)")
    ax2.set_ylabel("Tour Distance (km)")
    ax2.legend()

    fig.tight_layout()
    p3 = out_dir / "routing_optimization.png"
    fig.savefig(p3)
    plt.close(fig)
    created.append(p3)

    # 4. End-to-End Pipeline Breakdown
    pipe_rows = benchmark_data["pipeline"]
    scen_labels = [str(r["scenario"]).replace(" (", "\n(") for r in pipe_rows]
    sort_ms = [float(r["sorting_ms"]) for r in pipe_rows]
    knap_ms = [float(r["knapsack_ms"]) for r in pipe_rows]
    route_ms = [float(r["routing_ms"]) for r in pipe_rows]

    fig, ax = plt.subplots(figsize=(8.2, 4.8), dpi=150)
    ax.bar(scen_labels, sort_ms, label="Phase 2A: Sorting")
    ax.bar(scen_labels, knap_ms, bottom=sort_ms, label="Phase 2B: 0/1 Knapsack DP")
    bottoms = [s + k for s, k in zip(sort_ms, knap_ms)]
    ax.bar(scen_labels, route_ms, bottom=bottoms, label="Phase 3: Dijkstra + TSP")
    ax.set_title("End-to-End Courier Pipeline Runtime Breakdown")
    ax.set_ylabel("Execution Time (ms)")
    ax.legend()
    fig.tight_layout()
    p4 = out_dir / "pipeline_breakdown.png"
    fig.savefig(p4)
    plt.close(fig)
    created.append(p4)

    return created
