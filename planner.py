"""End-to-end Intelligent Courier Planning pipeline orchestrating Phases 1-3."""

from __future__ import annotations

import time

from src.graph import DeliveryGraph
from src.knapsack import format_dp_table_preview, knapsack_1d, knapsack_2d, knapsack_greedy
from src.models import CourierPlan, PackingResult, Parcel
from src.sorting import sort_parcels
from src.tsp import nearest_neighbor_tsp


def run_courier_plan(
    dataset_name: str,
    vehicle_capacity: int,
    depot: str,
    graph: DeliveryGraph,
    parcels: list[Parcel],
    sort_algo: str = "merge_sort",
    pack_algo: str = "knapsack_2d",
    apply_two_opt: bool = True,
) -> CourierPlan:
    """Execute sorting, knapsack DP, Dijkstra shortest paths, and TSP route planning."""
    t0 = time.perf_counter()
    prioritized = sort_parcels(parcels, algorithm=sort_algo)
    t_sort = (time.perf_counter() - t0) * 1000.0

    t1 = time.perf_counter()
    if pack_algo == "knapsack_2d":
        packing: PackingResult = knapsack_2d(prioritized, vehicle_capacity)
    elif pack_algo == "knapsack_1d":
        packing = knapsack_1d(prioritized, vehicle_capacity)
    elif pack_algo == "knapsack_greedy":
        packing = knapsack_greedy(prioritized, vehicle_capacity)
    else:
        raise ValueError(f"Unknown packing algorithm '{pack_algo}'.")
    t_pack = (time.perf_counter() - t1) * 1000.0

    selected_stops = [p.destination for p in packing.selected_parcels]
    t2 = time.perf_counter()
    route = nearest_neighbor_tsp(graph, depot=depot, delivery_stops=selected_stops, apply_two_opt=apply_two_opt)
    t_route = (time.perf_counter() - t2) * 1000.0

    timings_ms = {
        "sorting_ms": round(t_sort, 4),
        "knapsack_ms": round(t_pack, 4),
        "routing_ms": round(t_route, 4),
        "total_ms": round(t_sort + t_pack + t_route, 4),
    }

    return CourierPlan(
        dataset_name=dataset_name,
        prioritized_parcels=prioritized,
        packing=packing,
        route=route,
        timings_ms=timings_ms,
    )


def format_plan_report(plan: CourierPlan, graph: DeliveryGraph, show_dp_table: bool = True) -> str:
    """Render a structured text report of the courier plan for CLI output and traces."""
    lines: list[str] = []
    sep = "=" * 78
    lines.append(sep)
    lines.append(f"INTELLIGENT COURIER PLANNING SYSTEM — {plan.dataset_name}")
    lines.append(sep)

    # Phase 2A: Prioritized Parcels
    lines.append("\n[PHASE 2A] PARCEL PRIORITIZATION (Sorted by Deadline ASC, Priority DESC, Value/Kg DESC)")
    lines.append(f"Total Input Parcels: {len(plan.prioritized_parcels)}")
    lines.append(f"{'Rank':<5} {'ID':<6} {'Dest':<12} {'Wt(kg)':>7} {'Value':>7} {'Deadline':>9} {'Priority':>8}")
    lines.append("-" * 62)
    preview_limit = 20
    for rank, p in enumerate(plan.prioritized_parcels[:preview_limit], start=1):
        lines.append(
            f"{rank:<5} {p.parcel_id:<6} {p.destination:<12} {p.weight:>7} {p.value:>7} {p.deadline_hours:>7.1f}h {p.priority:>8}"
        )
    if len(plan.prioritized_parcels) > preview_limit:
        lines.append(f"... ({len(plan.prioritized_parcels) - preview_limit} additional parcels omitted from preview)")

    # Phase 2B: Knapsack Packing
    lines.append(f"\n[PHASE 2B] BOX FILLING & PACKAGE SELECTION ({plan.packing.algorithm})")
    lines.append(
        f"Capacity: {plan.packing.capacity} kg | Used: {plan.packing.total_weight} kg "
        f"({plan.packing.utilization_pct:.1f}%) | Optimal Total Value: {plan.packing.total_value}"
    )
    lines.append(
        "Selected Parcels ("
        + str(len(plan.packing.selected_parcels))
        + "): "
        + ", ".join(f"{p.parcel_id}->{p.destination}({p.weight}kg/${p.value})" for p in plan.packing.selected_parcels)
    )
    if plan.packing.excluded_parcels:
        excluded_ids = ", ".join(p.parcel_id for p in plan.packing.excluded_parcels[:15])
        suffix = " ..." if len(plan.packing.excluded_parcels) > 15 else ""
        lines.append(f"Deferred Parcels ({len(plan.packing.excluded_parcels)}): {excluded_ids}{suffix}")

    if show_dp_table and plan.packing.dp_table is not None:
        lines.append("\n[DP TABLE PREVIEW]")
        lines.append(format_dp_table_preview(plan.packing.dp_table, plan.prioritized_parcels))

    # Phase 3: Graph, Dijkstra & TSP Route
    lines.append(f"\n[PHASE 3] GRAPH PROCESSING & ROUTE OPTIMIZATION ({plan.route.algorithm})")
    lines.append(f"Customer Network: {len(graph.nodes)} nodes, {graph.edge_count()} roads | Depot: {plan.route.depot}")
    lines.append("Shortest Paths from Depot (Dijkstra):")
    for stop, (dist, path) in sorted(plan.route.shortest_paths_from_depot.items()):
        if stop == plan.route.depot:
            continue
        lines.append(f"  {plan.route.depot} -> {stop:<10} : {dist:>6.1f} km | Path: {' -> '.join(path)}")

    lines.append("\nOrdered Delivery Route Sequence:")
    lines.append("  " + " -> ".join(plan.route.stop_sequence))
    lines.append("\nTurn-by-Turn Road Segments:")
    for idx, leg in enumerate(plan.route.legs, start=1):
        lines.append(
            f"  Leg {idx:02d}: {leg.start} -> {leg.end} ({leg.distance:.1f} km) via [{' -> '.join(leg.path)}]"
        )
    lines.append(f"Total Route Distance: {plan.route.total_distance:.2f} km")

    # Phase 4: Timings
    lines.append("\n[PHASE 4] EXECUTION TIMINGS")
    lines.append(
        f"  Sorting: {plan.timings_ms['sorting_ms']:.4f} ms | "
        f"Knapsack DP: {plan.timings_ms['knapsack_ms']:.4f} ms | "
        f"Dijkstra + TSP: {plan.timings_ms['routing_ms']:.4f} ms | "
        f"Total: {plan.timings_ms['total_ms']:.4f} ms"
    )
    lines.append(sep)
    return "\n".join(lines)
