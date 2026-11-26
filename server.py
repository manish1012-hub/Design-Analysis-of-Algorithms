"""Lightweight local web server exposing the DAA Courier Planner API and UI."""

from __future__ import annotations

import argparse
import json
import math
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from src.benchmark import run_all_benchmarks
from src.charts import generate_charts
from src.io_utils import load_scenario
from src.planner import run_courier_plan

ROOT_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
RESULTS_DIR = ROOT_DIR / "results"

DATASETS = {
    "small": DATA_DIR / "sample_small.json",
    "medium": DATA_DIR / "sample_medium.json",
    "large": DATA_DIR / "sample_large.json",
}


def _compute_node_positions(nodes: list[str], depot: str, edges: list[tuple[str, str, float]]) -> dict[str, dict[str, float]]:
    """Compute clean deterministic 2D coordinates for SVG graph visualization."""
    positions: dict[str, dict[str, float]] = {depot: {"x": 50.0, "y": 50.0}}
    others = sorted(n for n in nodes if n != depot)
    count = len(others)
    if count == 0:
        return positions

    # Arrange nodes in concentric rings by index, then run a lightweight spring pass.
    for idx, node in enumerate(others):
        ring = 1 if count <= 14 else (1 if idx % 2 == 0 else 2)
        radius = 32.0 if ring == 1 else 42.0
        angle = (2.0 * math.pi * idx) / count - math.pi / 2.0
        positions[node] = {
            "x": round(50.0 + radius * math.cos(angle), 2),
            "y": round(50.0 + radius * math.sin(angle), 2),
        }

    # Light relaxation to separate crowded neighbors slightly while keeping depot centered.
    if count > 8:
        adj_set: set[tuple[str, str]] = {(u, v) for u, v, _ in edges} | {(v, u) for u, v, _ in edges}
        for _ in range(18):
            forces = {n: [0.0, 0.0] for n in others}
            for i, a in enumerate(others):
                for b in others[i + 1 :]:
                    dx = positions[a]["x"] - positions[b]["x"]
                    dy = positions[a]["y"] - positions[b]["y"]
                    dist = math.hypot(dx, dy) or 0.1
                    if dist < 16.0:
                        push = (16.0 - dist) * 0.06
                        forces[a][0] += (dx / dist) * push
                        forces[a][1] += (dy / dist) * push
                        forces[b][0] -= (dx / dist) * push
                        forces[b][1] -= (dy / dist) * push
                    if (a, b) in adj_set and dist > 28.0:
                        pull = (dist - 28.0) * 0.015
                        forces[a][0] -= (dx / dist) * pull
                        forces[a][1] -= (dy / dist) * pull
                        forces[b][0] += (dx / dist) * pull
                        forces[b][1] += (dy / dist) * pull
            for n in others:
                positions[n]["x"] = round(min(92.0, max(8.0, positions[n]["x"] + forces[n][0])), 2)
                positions[n]["y"] = round(min(92.0, max(8.0, positions[n]["y"] + forces[n][1])), 2)

    return positions


def _serialize_plan(dataset_key: str, sort_algo: str, pack_algo: str, apply_two_opt: bool) -> dict[str, object]:
    dataset_path = DATASETS.get(dataset_key)
    if dataset_path is None or not dataset_path.exists():
        raise FileNotFoundError(f"Unknown or missing dataset '{dataset_key}'")

    dataset_name, capacity, depot, graph, parcels = load_scenario(dataset_path)
    plan = run_courier_plan(
        dataset_name=dataset_name,
        vehicle_capacity=capacity,
        depot=depot,
        graph=graph,
        parcels=parcels,
        sort_algo=sort_algo,
        pack_algo=pack_algo,
        apply_two_opt=apply_two_opt,
    )

    seen_edges: set[tuple[str, str]] = set()
    edges: list[tuple[str, str, float]] = []
    for u in sorted(graph.nodes):
        for v, w in graph.adj[u]:
            key = (u, v) if graph.directed else tuple(sorted((u, v)))
            if key not in seen_edges:
                seen_edges.add(key)  # type: ignore[arg-type]
                edges.append((u, v, w))

    positions = _compute_node_positions(sorted(graph.nodes), depot, edges)
    selected_ids = {p.parcel_id for p in plan.packing.selected_parcels}

    dp_preview = None
    if plan.packing.dp_table is not None:
        max_r = min(len(plan.packing.dp_table), 14)
        max_c = min(len(plan.packing.dp_table[0]), 26) if plan.packing.dp_table else 0
        dp_preview = {
            "rows": [
                {
                    "label": "Init (0)" if i == 0 else plan.prioritized_parcels[i - 1].parcel_id,
                    "values": plan.packing.dp_table[i][:max_c],
                    "final_cap_value": plan.packing.dp_table[i][-1],
                }
                for i in range(max_r)
            ],
            "total_rows": len(plan.packing.dp_table),
            "total_cols": len(plan.packing.dp_table[0]) if plan.packing.dp_table else 0,
            "shown_cols": max_c,
        }

    return {
        "dataset_key": dataset_key,
        "dataset_name": plan.dataset_name,
        "depot": depot,
        "capacity": capacity,
        "parcels_total": len(plan.prioritized_parcels),
        "prioritized_parcels": [
            {
                "rank": idx,
                "parcel_id": p.parcel_id,
                "destination": p.destination,
                "weight": p.weight,
                "value": p.value,
                "deadline_hours": p.deadline_hours,
                "priority": p.priority,
                "selected": p.parcel_id in selected_ids,
            }
            for idx, p in enumerate(plan.prioritized_parcels, start=1)
        ],
        "packing": {
            "algorithm": plan.packing.algorithm,
            "selected_count": len(plan.packing.selected_parcels),
            "excluded_count": len(plan.packing.excluded_parcels),
            "total_weight": plan.packing.total_weight,
            "total_value": plan.packing.total_value,
            "capacity": plan.packing.capacity,
            "utilization_pct": round(plan.packing.utilization_pct, 1),
            "dp_preview": dp_preview,
        },
        "graph": {
            "node_count": len(graph.nodes),
            "edge_count": graph.edge_count(),
            "nodes": [
                {
                    "id": n,
                    "x": positions[n]["x"],
                    "y": positions[n]["y"],
                    "is_depot": n == depot,
                }
                for n in sorted(graph.nodes)
            ],
            "edges": [{"u": u, "v": v, "weight": w} for u, v, w in edges],
        },
        "route": {
            "algorithm": plan.route.algorithm,
            "stop_sequence": plan.route.stop_sequence,
            "total_distance": plan.route.total_distance,
            "legs": [
                {
                    "leg_no": idx,
                    "start": leg.start,
                    "end": leg.end,
                    "distance": leg.distance,
                    "path": leg.path,
                }
                for idx, leg in enumerate(plan.route.legs, start=1)
            ],
            "shortest_paths_from_depot": [
                {"stop": stop, "distance": dist, "path": path}
                for stop, (dist, path) in sorted(plan.route.shortest_paths_from_depot.items())
                if stop != depot
            ],
        },
        "timings_ms": plan.timings_ms,
    }


class CourierRequestHandler(BaseHTTPRequestHandler):
    """HTTP handler serving static web assets, JSON APIs, and chart PNGs."""

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return

    def _send_json(self, payload: object, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, file_path: Path) -> None:
        if not file_path.exists() or not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return
        mime_type, _ = mimetypes.guess_type(str(file_path))
        data = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            self._send_file(WEB_DIR / "index.html")
            return

        if path.startswith("/charts/"):
            chart_name = Path(path).name
            self._send_file(RESULTS_DIR / "charts" / chart_name)
            return

        if path == "/api/plan":
            qs = parse_qs(parsed.query)
            dataset = qs.get("dataset", ["small"])[0]
            sort_algo = qs.get("sort_algo", ["merge_sort"])[0]
            pack_algo = qs.get("pack_algo", ["knapsack_2d"])[0]
            two_opt = qs.get("two_opt", ["true"])[0].lower() != "false"
            try:
                result = _serialize_plan(dataset, sort_algo, pack_algo, two_opt)
                self._send_json(result)
            except Exception as exc:  # noqa: BLE001
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        if path == "/api/benchmarks":
            bench_file = RESULTS_DIR / "benchmark_results.json"
            if not bench_file.exists():
                results = run_all_benchmarks(output_dir=RESULTS_DIR)
                generate_charts(results, charts_dir=RESULTS_DIR / "charts")
            self._send_json(json.loads(bench_file.read_text(encoding="utf-8")))
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found")

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/benchmarks/run":
            results = run_all_benchmarks(output_dir=RESULTS_DIR)
            generate_charts(results, charts_dir=RESULTS_DIR / "charts")
            self._send_json(results)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found")


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ReusableThreadingHTTPServer((host, port), CourierRequestHandler)
    print(f"Courier Planner Dashboard running at http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Intelligent Courier Planner Web UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    serve(host=args.host, port=args.port)
