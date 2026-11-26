"""Scenario loading and deterministic synthetic dataset generation."""

from __future__ import annotations

import json
import random
from pathlib import Path

from src.graph import DeliveryGraph
from src.models import Parcel


def load_scenario(path: str | Path) -> tuple[str, int, str, DeliveryGraph, list[Parcel]]:
    """Load a courier planning scenario from a JSON file."""
    file_path = Path(path)
    raw = json.loads(file_path.read_text(encoding="utf-8"))

    dataset_name = str(raw.get("dataset_name", file_path.stem))
    vehicle_capacity = int(raw["vehicle_capacity"])
    depot = str(raw["depot"])
    directed = bool(raw.get("directed", False))

    nodes = [str(n) for n in raw["nodes"]]
    edges = [(str(e["u"]), str(e["v"]), float(e["weight"])) for e in raw["edges"]]
    graph = DeliveryGraph.from_edge_list(nodes=nodes, edges=edges, directed=directed)

    parcels = [
        Parcel(
            parcel_id=str(p["parcel_id"]),
            destination=str(p["destination"]),
            weight=int(p["weight"]),
            value=int(p["value"]),
            deadline_hours=float(p["deadline_hours"]),
            priority=int(p["priority"]),
        )
        for p in raw["parcels"]
    ]
    return dataset_name, vehicle_capacity, depot, graph, parcels


def save_scenario(
    path: str | Path,
    dataset_name: str,
    vehicle_capacity: int,
    depot: str,
    graph: DeliveryGraph,
    parcels: list[Parcel],
) -> None:
    """Serialize a courier scenario to JSON."""
    seen_edges: set[tuple[str, str]] = set()
    edge_list: list[dict[str, object]] = []
    for u in sorted(graph.nodes):
        for v, w in graph.adj[u]:
            key = (u, v) if graph.directed else tuple(sorted((u, v)))
            if key in seen_edges:
                continue
            seen_edges.add(key)  # type: ignore[arg-type]
            edge_list.append({"u": u, "v": v, "weight": w})

    payload = {
        "dataset_name": dataset_name,
        "vehicle_capacity": vehicle_capacity,
        "depot": depot,
        "directed": graph.directed,
        "nodes": sorted(graph.nodes),
        "edges": edge_list,
        "parcels": [
            {
                "parcel_id": p.parcel_id,
                "destination": p.destination,
                "weight": p.weight,
                "value": p.value,
                "deadline_hours": p.deadline_hours,
                "priority": p.priority,
            }
            for p in parcels
        ],
    }
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def generate_synthetic_scenario(
    num_parcels: int,
    num_nodes: int,
    vehicle_capacity: int,
    seed: int = 42,
    dataset_name: str = "Synthetic Scenario",
) -> tuple[str, int, str, DeliveryGraph, list[Parcel]]:
    """Create a connected customer graph and random parcel set deterministically."""
    rng = random.Random(seed)
    depot = "Depot"
    customer_nodes = [f"Stop_{i:02d}" for i in range(1, num_nodes)]
    all_nodes = [depot] + customer_nodes

    graph = DeliveryGraph(directed=False)
    for node in all_nodes:
        graph.add_node(node)

    # Assign 2D coordinates so edge weights obey realistic road geometry.
    coords: dict[str, tuple[float, float]] = {depot: (50.0, 50.0)}
    for node in customer_nodes:
        coords[node] = (rng.uniform(0.0, 100.0), rng.uniform(0.0, 100.0))

    def euclid(a: str, b: str) -> float:
        ax, ay = coords[a]
        bx, by = coords[b]
        return round(((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5 * rng.uniform(1.0, 1.25), 1)

    # Guarantee connectivity via a spanning tree first.
    shuffled = list(all_nodes)
    rng.shuffle(shuffled)
    for idx in range(1, len(shuffled)):
        u = shuffled[idx]
        v = shuffled[rng.randrange(0, idx)]
        graph.add_edge(u, v, max(1.0, euclid(u, v)))

    # Add extra cross-roads (~1.5x edges) for realistic alternative shortest paths.
    existing = {tuple(sorted((u, v))) for u in graph.nodes for v, _ in graph.adj[u]}
    extra_edges = max(1, num_nodes)
    attempts = 0
    added = 0
    while added < extra_edges and attempts < extra_edges * 10:
        attempts += 1
        u, v = rng.sample(all_nodes, 2)
        pair = tuple(sorted((u, v)))
        if pair not in existing:
            existing.add(pair)
            graph.add_edge(u, v, max(1.0, euclid(u, v)))
            added += 1

    max_item_weight = max(2, min(18, vehicle_capacity // 3))
    parcels: list[Parcel] = []
    for i in range(1, num_parcels + 1):
        weight = rng.randint(1, max_item_weight)
        priority = rng.randint(1, 5)
        deadline = round(rng.choice([2.0, 4.0, 6.0, 8.0, 12.0, 18.0, 24.0]), 1)
        value = weight * rng.randint(12, 35) + priority * rng.randint(8, 25)
        parcels.append(
            Parcel(
                parcel_id=f"P{i:03d}",
                destination=rng.choice(customer_nodes),
                weight=weight,
                value=value,
                deadline_hours=deadline,
                priority=priority,
            )
        )

    return dataset_name, vehicle_capacity, depot, graph, parcels
