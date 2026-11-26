"""Data models for the Intelligent Courier Planning System."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Parcel:
    """Represents a single courier parcel awaiting dispatch.

    Attributes:
        parcel_id: Unique parcel identifier (e.g., "P001").
        destination: Delivery node name in the customer graph.
        weight: Integer weight in kg (required for 0/1 Knapsack DP table).
        value: Monetary value or delivery reward score.
        deadline_hours: Delivery SLA deadline in hours (smaller = more urgent).
        priority: Priority tier from 1 (lowest) to 5 (highest).
    """

    parcel_id: str
    destination: str
    weight: int
    value: int
    deadline_hours: float
    priority: int

    def __post_init__(self) -> None:
        if self.weight < 0:
            raise ValueError(f"Parcel {self.parcel_id} weight must be non-negative.")
        if self.value < 0:
            raise ValueError(f"Parcel {self.parcel_id} value must be non-negative.")
        if self.deadline_hours <= 0:
            raise ValueError(f"Parcel {self.parcel_id} deadline_hours must be positive.")
        if not (1 <= self.priority <= 5):
            raise ValueError(f"Parcel {self.parcel_id} priority must be in [1, 5].")


@dataclass
class PackingResult:
    """Output from the Phase 2 package selection algorithm."""

    selected_parcels: list[Parcel]
    excluded_parcels: list[Parcel]
    total_weight: int
    total_value: int
    capacity: int
    algorithm: str
    dp_table: list[list[int]] | None = None

    @property
    def utilization_pct(self) -> float:
        if self.capacity <= 0:
            return 0.0
        return (self.total_weight / self.capacity) * 100.0


@dataclass
class RouteLeg:
    """Single hop between two consecutive delivery stops along shortest road path."""

    start: str
    end: str
    distance: float
    path: list[str]


@dataclass
class RouteResult:
    """Output from the Phase 3 route optimization pipeline."""

    depot: str
    stop_sequence: list[str]
    legs: list[RouteLeg]
    total_distance: float
    algorithm: str
    shortest_paths_from_depot: dict[str, tuple[float, list[str]]] = field(default_factory=dict)


@dataclass
class CourierPlan:
    """Complete end-to-end execution result and per-phase timings."""

    dataset_name: str
    prioritized_parcels: list[Parcel]
    packing: PackingResult
    route: RouteResult
    timings_ms: dict[str, float]
