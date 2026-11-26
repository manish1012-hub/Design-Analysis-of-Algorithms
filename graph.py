"""Phase 3: Customer delivery network graph and Dijkstra's shortest-path algorithm."""

from __future__ import annotations

import heapq
from collections import defaultdict


class DeliveryGraph:
    """Weighted graph representing road intersections and customer delivery points."""

    def __init__(self, directed: bool = False) -> None:
        self.directed = directed
        self.adj: dict[str, list[tuple[str, float]]] = defaultdict(list)
        self.nodes: set[str] = set()

    def add_node(self, node: str) -> None:
        self.nodes.add(node)
        self.adj.setdefault(node, [])

    def add_edge(self, u: str, v: str, weight: float) -> None:
        if weight < 0:
            raise ValueError(f"Edge ({u}, {v}) has negative weight {weight}; Dijkstra requires non-negative weights.")
        self.add_node(u)
        self.add_node(v)
        self.adj[u].append((v, float(weight)))
        if not self.directed:
            self.adj[v].append((u, float(weight)))

    @classmethod
    def from_edge_list(cls, nodes: list[str], edges: list[tuple[str, str, float]], directed: bool = False) -> DeliveryGraph:
        graph = cls(directed=directed)
        for node in nodes:
            graph.add_node(node)
        for u, v, w in edges:
            graph.add_edge(u, v, w)
        return graph

    def edge_count(self) -> int:
        total = sum(len(neighbors) for neighbors in self.adj.values())
        return total if self.directed else total // 2


def dijkstra(graph: DeliveryGraph, source: str) -> tuple[dict[str, float], dict[str, str | None]]:
    """Compute shortest paths from `source` to all reachable nodes via Dijkstra's algorithm.

    Time Complexity: O((V + E) log V) using a binary min-heap.
    Space Complexity: O(V) for distance and predecessor maps.
    """
    if source not in graph.nodes:
        raise ValueError(f"Source node '{source}' is not in the delivery graph.")

    dist: dict[str, float] = {node: float("inf") for node in graph.nodes}
    parent: dict[str, str | None] = {node: None for node in graph.nodes}
    dist[source] = 0.0

    min_heap: list[tuple[float, str]] = [(0.0, source)]
    visited: set[str] = set()

    while min_heap:
        current_dist, u = heapq.heappop(min_heap)
        if u in visited:
            continue
        visited.add(u)

        if current_dist > dist[u]:
            continue

        for v, weight in graph.adj[u]:
            if v in visited:
                continue
            new_dist = current_dist + weight
            if new_dist < dist[v]:
                dist[v] = new_dist
                parent[v] = u
                heapq.heappush(min_heap, (new_dist, v))

    return dist, parent


def reconstruct_path(parent: dict[str, str | None], source: str, target: str) -> list[str]:
    """Reconstruct shortest node sequence from `source` to `target` using predecessor map."""
    if source == target:
        return [source]
    if parent.get(target) is None:
        return []

    path: list[str] = []
    curr: str | None = target
    while curr is not None:
        path.append(curr)
        if curr == source:
            break
        curr = parent.get(curr)

    if not path or path[-1] != source:
        return []
    path.reverse()
    return path


def compute_shortest_path_matrix(
    graph: DeliveryGraph,
    required_stops: list[str],
) -> dict[str, dict[str, tuple[float, list[str]]]]:
    """Run Dijkstra from each stop in `required_stops` to build pairwise shortest paths.

    Returns:
        matrix[u][v] = (shortest_distance, road_node_path)
    """
    unique_stops = list(dict.fromkeys(required_stops))
    matrix: dict[str, dict[str, tuple[float, list[str]]]] = {}
    for src in unique_stops:
        dist, parent = dijkstra(graph, src)
        matrix[src] = {}
        for dst in unique_stops:
            d = dist[dst]
            path = reconstruct_path(parent, src, dst) if d < float("inf") else []
            matrix[src][dst] = (d, path)
    return matrix
