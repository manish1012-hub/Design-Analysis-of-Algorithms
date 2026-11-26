"""Phase 3: Nearest-Neighbor TSP approximation and 2-opt local optimization."""

from __future__ import annotations

from src.graph import DeliveryGraph, compute_shortest_path_matrix
from src.models import RouteLeg, RouteResult


def nearest_neighbor_tsp(
    graph: DeliveryGraph,
    depot: str,
    delivery_stops: list[str],
    apply_two_opt: bool = False,
) -> RouteResult:
    """Build an approximate shortest closed delivery tour starting and ending at `depot`.

    Step 1: Compute exact pairwise shortest paths among `{depot} U delivery_stops` via Dijkstra.
    Step 2: Greedily visit the nearest unvisited delivery stop (Nearest-Neighbor TSP, O(k^2)).
    Step 3: Optionally refine tour order using 2-opt local search (Phase 4 optimization).
    """
    unique_targets = [s for s in dict.fromkeys(delivery_stops) if s != depot]
    all_stops = [depot] + unique_targets
    sp_matrix = compute_shortest_path_matrix(graph, all_stops)

    if not unique_targets:
        return RouteResult(
            depot=depot,
            stop_sequence=[depot, depot],
            legs=[],
            total_distance=0.0,
            algorithm="Nearest-Neighbor TSP (No Stops)",
            shortest_paths_from_depot=sp_matrix[depot],
        )

    # Verify reachability from depot before running TSP.
    for stop in unique_targets:
        dist_from_depot, _ = sp_matrix[depot][stop]
        if dist_from_depot == float("inf"):
            raise ValueError(f"Delivery point '{stop}' is unreachable from depot '{depot}'.")

    unvisited = set(unique_targets)
    tour = [depot]
    current = depot

    while unvisited:
        # Deterministic tie-break by stop name when distances are equal.
        next_stop = min(
            unvisited,
            key=lambda candidate: (sp_matrix[current][candidate][0], candidate),
        )
        if sp_matrix[current][next_stop][0] == float("inf"):
            raise ValueError(f"Stop '{next_stop}' is unreachable from '{current}'.")
        tour.append(next_stop)
        unvisited.remove(next_stop)
        current = next_stop

    tour.append(depot)
    algo_name = "Nearest-Neighbor TSP Approximation"

    if apply_two_opt and len(tour) > 4:
        tour = two_opt_improve(tour, sp_matrix)
        algo_name = "Nearest-Neighbor TSP + 2-Opt Optimization"

    legs: list[RouteLeg] = []
    total_distance = 0.0
    for i in range(len(tour) - 1):
        u, v = tour[i], tour[i + 1]
        leg_dist, leg_path = sp_matrix[u][v]
        if leg_dist == float("inf"):
            raise ValueError(f"Return path from '{u}' to '{v}' is disconnected.")
        legs.append(RouteLeg(start=u, end=v, distance=leg_dist, path=leg_path))
        total_distance += leg_dist

    return RouteResult(
        depot=depot,
        stop_sequence=tour,
        legs=legs,
        total_distance=round(total_distance, 4),
        algorithm=algo_name,
        shortest_paths_from_depot=sp_matrix[depot],
    )


def two_opt_improve(
    tour: list[str],
    sp_matrix: dict[str, dict[str, tuple[float, list[str]]]],
) -> list[str]:
    """Improve an existing closed TSP tour via 2-opt edge swaps until local optimum."""
    best = list(tour)
    improved = True
    n = len(best)

    while improved:
        improved = False
        for i in range(1, n - 2):
            for j in range(i + 1, n - 1):
                if j - i == 1:
                    continue
                a, b = best[i - 1], best[i]
                c, d = best[j], best[j + 1]
                current_cost = sp_matrix[a][b][0] + sp_matrix[c][d][0]
                swapped_cost = sp_matrix[a][c][0] + sp_matrix[b][d][0]
                if swapped_cost + 1e-9 < current_cost:
                    best[i : j + 1] = reversed(best[i : j + 1])
                    improved = True
    return best
