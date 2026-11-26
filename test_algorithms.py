"""Comprehensive unit and integration tests for all DAA Capstone components."""

from __future__ import annotations

import unittest
from pathlib import Path

from src.graph import DeliveryGraph, dijkstra, reconstruct_path
from src.io_utils import load_scenario
from src.knapsack import knapsack_1d, knapsack_2d, knapsack_greedy
from src.models import Parcel
from src.planner import run_courier_plan
from src.sorting import insertion_sort, merge_sort, parcel_priority_key, quick_sort
from src.tsp import nearest_neighbor_tsp


class TestSorting(unittest.TestCase):
    def setUp(self) -> None:
        self.parcels = [
            Parcel("P1", "A", weight=5, value=50, deadline_hours=6.0, priority=3),
            Parcel("P2", "B", weight=2, value=40, deadline_hours=2.0, priority=4),
            Parcel("P3", "C", weight=3, value=60, deadline_hours=2.0, priority=5),
            Parcel("P4", "D", weight=4, value=80, deadline_hours=4.0, priority=2),
        ]

    def test_all_sorts_match_expected_order(self) -> None:
        expected_ids = ["P3", "P2", "P4", "P1"]
        for fn in (merge_sort, quick_sort, insertion_sort):
            sorted_ids = [p.parcel_id for p in fn(self.parcels, parcel_priority_key)]
            self.assertEqual(sorted_ids, expected_ids)

    def test_empty_and_single_parcel(self) -> None:
        for fn in (merge_sort, quick_sort, insertion_sort):
            self.assertEqual(fn([], parcel_priority_key), [])
            self.assertEqual(fn([self.parcels[0]], parcel_priority_key), [self.parcels[0]])


class TestKnapsack(unittest.TestCase):
    def test_dp_beats_greedy_on_classic_counterexample(self) -> None:
        # Greedy picks A (w=10, v=60) + B (w=20, v=100) = 160, leaving 20kg (cannot fit C).
        # Optimal 0/1 DP picks B + C (w=20+30=50, v=100+120=220).
        parcels = [
            Parcel("A", "N1", weight=10, value=60, deadline_hours=4.0, priority=3),
            Parcel("B", "N2", weight=20, value=100, deadline_hours=4.0, priority=3),
            Parcel("C", "N3", weight=30, value=120, deadline_hours=4.0, priority=3),
        ]
        res_2d = knapsack_2d(parcels, capacity=50)
        res_1d = knapsack_1d(parcels, capacity=50)
        res_greedy = knapsack_greedy(parcels, capacity=50)

        self.assertEqual(res_2d.total_value, 220)
        self.assertEqual(res_1d.total_value, 220)
        self.assertEqual(res_2d.total_weight, 50)
        self.assertEqual({p.parcel_id for p in res_2d.selected_parcels}, {"B", "C"})
        self.assertLess(res_greedy.total_value, res_2d.total_value)

    def test_zero_capacity_selects_nothing(self) -> None:
        parcels = [Parcel("P1", "A", weight=2, value=20, deadline_hours=2.0, priority=5)]
        res = knapsack_2d(parcels, capacity=0)
        self.assertEqual(res.total_value, 0)
        self.assertEqual(res.selected_parcels, [])


class TestGraphAndTSP(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = DeliveryGraph.from_edge_list(
            nodes=["Depot", "A", "B", "C"],
            edges=[
                ("Depot", "A", 2.0),
                ("A", "B", 2.0),
                ("Depot", "B", 10.0),
                ("B", "C", 3.0),
                ("Depot", "C", 9.0),
            ],
        )

    def test_dijkstra_finds_indirect_shortcut(self) -> None:
        dist, parent = dijkstra(self.graph, "Depot")
        self.assertEqual(dist["B"], 4.0)
        self.assertEqual(reconstruct_path(parent, "Depot", "B"), ["Depot", "A", "B"])
        self.assertEqual(dist["C"], 7.0)
        self.assertEqual(reconstruct_path(parent, "Depot", "C"), ["Depot", "A", "B", "C"])

    def test_nearest_neighbor_tsp_visits_all_stops_and_returns(self) -> None:
        route = nearest_neighbor_tsp(self.graph, depot="Depot", delivery_stops=["C", "A", "B", "A"])
        self.assertEqual(route.stop_sequence[0], "Depot")
        self.assertEqual(route.stop_sequence[-1], "Depot")
        self.assertEqual(set(route.stop_sequence[1:-1]), {"A", "B", "C"})
        self.assertEqual(len(route.stop_sequence), 5)  # Depot, 3 unique stops, Depot
        self.assertGreater(route.total_distance, 0.0)


class TestIntegration(unittest.TestCase):
    def test_small_scenario_end_to_end(self) -> None:
        scenario_path = Path(__file__).resolve().parent.parent / "data" / "sample_small.json"
        name, cap, depot, graph, parcels = load_scenario(scenario_path)
        plan = run_courier_plan(name, cap, depot, graph, parcels)
        self.assertLessEqual(plan.packing.total_weight, cap)
        self.assertGreater(plan.packing.total_value, 0)
        self.assertEqual(plan.route.stop_sequence[0], depot)
        self.assertEqual(plan.route.stop_sequence[-1], depot)
        self.assertGreater(plan.route.total_distance, 0.0)


if __name__ == "__main__":
    unittest.main()
