"""Phase 4: Performance benchmarking across sorting, DP packing, and graph routing."""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from statistics import mean

from src.io_utils import generate_synthetic_scenario
from src.knapsack import knapsack_1d, knapsack_2d, knapsack_greedy
from src.planner import run_courier_plan
from src.sorting import insertion_sort, merge_sort, parcel_priority_key, quick_sort
from src.tsp import nearest_neighbor_tsp


def _measure_ms(fn, repeats: int = 3) -> float:
    samples: list[float] = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000.0)
    return round(mean(samples), 4)


def run_all_benchmarks(output_dir: str | Path = "results") -> dict[str, object]:
    """Execute sorting, knapsack, routing, and end-to-end scaling benchmarks."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # 1. Sorting scaling benchmark
    sorting_sizes = [25, 50, 100, 250, 500, 1000, 2000]
    sorting_results: list[dict[str, object]] = []
    for n in sorting_sizes:
        _, _, _, _, parcels = generate_synthetic_scenario(
            num_parcels=n, num_nodes=max(10, n // 10), vehicle_capacity=100, seed=100 + n
        )
        t_merge = _measure_ms(lambda: merge_sort(parcels, parcel_priority_key), repeats=3)
        t_quick = _measure_ms(lambda: quick_sort(parcels, parcel_priority_key), repeats=3)
        t_insert = _measure_ms(lambda: insertion_sort(parcels, parcel_priority_key), repeats=3 if n <= 1000 else 1)
        sorting_results.append(
            {
                "n_parcels": n,
                "merge_sort_ms": t_merge,
                "quick_sort_ms": t_quick,
                "insertion_sort_ms": t_insert,
            }
        )

    # 2. Knapsack DP vs 1D DP vs Greedy benchmark
    knapsack_configs = [
        (10, 30),
        (25, 60),
        (50, 120),
        (100, 200),
        (200, 350),
        (300, 500),
    ]
    knapsack_results: list[dict[str, object]] = []
    for n, cap in knapsack_configs:
        _, _, _, _, parcels = generate_synthetic_scenario(
            num_parcels=n, num_nodes=max(8, n // 4), vehicle_capacity=cap, seed=200 + n
        )
        t_2d = _measure_ms(lambda: knapsack_2d(parcels, cap), repeats=3)
        t_1d = _measure_ms(lambda: knapsack_1d(parcels, cap), repeats=3)
        t_greedy = _measure_ms(lambda: knapsack_greedy(parcels, cap), repeats=3)
        res_2d = knapsack_2d(parcels, cap)
        res_greedy = knapsack_greedy(parcels, cap)
        gap_pct = (
            ((res_2d.total_value - res_greedy.total_value) / res_2d.total_value) * 100.0
            if res_2d.total_value > 0
            else 0.0
        )
        knapsack_results.append(
            {
                "n_parcels": n,
                "capacity": cap,
                "dp_2d_ms": t_2d,
                "dp_1d_ms": t_1d,
                "greedy_ms": t_greedy,
                "dp_optimal_value": res_2d.total_value,
                "greedy_value": res_greedy.total_value,
                "greedy_optimality_gap_pct": round(gap_pct, 2),
            }
        )

    # 3. Graph Dijkstra + Nearest-Neighbor TSP vs 2-Opt benchmark
    graph_sizes = [8, 15, 25, 45, 70, 100]
    routing_results: list[dict[str, object]] = []
    for v in graph_sizes:
        _, _, depot, graph, _ = generate_synthetic_scenario(
            num_parcels=v * 2, num_nodes=v, vehicle_capacity=100, seed=300 + v
        )
        stops = [node for node in sorted(graph.nodes) if node != depot]
        t_nn = _measure_ms(lambda: nearest_neighbor_tsp(graph, depot, stops, apply_two_opt=False), repeats=3)
        t_opt = _measure_ms(lambda: nearest_neighbor_tsp(graph, depot, stops, apply_two_opt=True), repeats=3)
        res_nn = nearest_neighbor_tsp(graph, depot, stops, apply_two_opt=False)
        res_opt = nearest_neighbor_tsp(graph, depot, stops, apply_two_opt=True)
        improvement_pct = (
            ((res_nn.total_distance - res_opt.total_distance) / res_nn.total_distance) * 100.0
            if res_nn.total_distance > 0
            else 0.0
        )
        routing_results.append(
            {
                "n_nodes": v,
                "n_edges": graph.edge_count(),
                "nn_tsp_ms": t_nn,
                "nn_two_opt_ms": t_opt,
                "nn_distance": res_nn.total_distance,
                "two_opt_distance": res_opt.total_distance,
                "distance_improvement_pct": round(improvement_pct, 2),
            }
        )

    # 4. End-to-End pipeline scaling across Small, Medium, Large scenarios
    pipeline_specs = [
        ("Small (12 parcels, 8 nodes)", 12, 8, 30),
        ("Medium (80 parcels, 25 nodes)", 80, 25, 120),
        ("Large (250 parcels, 60 nodes)", 250, 60, 250),
    ]
    pipeline_results: list[dict[str, object]] = []
    for label, n_p, n_v, cap in pipeline_specs:
        name, cap_val, depot, graph, parcels = generate_synthetic_scenario(
            num_parcels=n_p, num_nodes=n_v, vehicle_capacity=cap, seed=400 + n_p, dataset_name=label
        )
        plan = run_courier_plan(name, cap_val, depot, graph, parcels)
        pipeline_results.append(
            {
                "scenario": label,
                "n_parcels": n_p,
                "n_nodes": n_v,
                "capacity": cap_val,
                "selected_count": len(plan.packing.selected_parcels),
                "total_value": plan.packing.total_value,
                "route_distance": plan.route.total_distance,
                **plan.timings_ms,
            }
        )

    summary = {
        "sorting": sorting_results,
        "knapsack": knapsack_results,
        "routing": routing_results,
        "pipeline": pipeline_results,
    }

    (out_path / "benchmark_results.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    # Also write a clean flat CSV summary for spreadsheet inspection.
    csv_path = out_path / "benchmark_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Category", "Scale", "Metric_A", "Value_A", "Metric_B", "Value_B", "Metric_C", "Value_C"])
        for row in sorting_results:
            writer.writerow([
                "Sorting",
                f"n={row['n_parcels']}",
                "merge_sort_ms",
                row["merge_sort_ms"],
                "quick_sort_ms",
                row["quick_sort_ms"],
                "insertion_sort_ms",
                row["insertion_sort_ms"],
            ])
        for row in knapsack_results:
            writer.writerow([
                "Knapsack",
                f"n={row['n_parcels']},W={row['capacity']}",
                "dp_2d_ms",
                row["dp_2d_ms"],
                "dp_1d_ms",
                row["dp_1d_ms"],
                "greedy_gap_pct",
                row["greedy_optimality_gap_pct"],
            ])
        for row in routing_results:
            writer.writerow([
                "Routing",
                f"V={row['n_nodes']},E={row['n_edges']}",
                "nn_tsp_ms",
                row["nn_tsp_ms"],
                "nn_two_opt_ms",
                row["nn_two_opt_ms"],
                "dist_improvement_pct",
                row["distance_improvement_pct"],
            ])
        for row in pipeline_results:
            writer.writerow([
                "Pipeline",
                row["scenario"],
                "sorting_ms",
                row["sorting_ms"],
                "knapsack_ms",
                row["knapsack_ms"],
                "routing_ms",
                row["routing_ms"],
            ])

    return summary
