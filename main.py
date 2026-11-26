"""CLI entry point for the Intelligent Courier Planning System (DAA Capstone)."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.benchmark import run_all_benchmarks
from src.charts import generate_charts
from src.io_utils import generate_synthetic_scenario, load_scenario, save_scenario
from src.planner import format_plan_report, run_courier_plan
from web.server import serve


def cmd_plan(args: argparse.Namespace) -> None:
    dataset_name, capacity, depot, graph, parcels = load_scenario(args.dataset)
    plan = run_courier_plan(
        dataset_name=dataset_name,
        vehicle_capacity=capacity,
        depot=depot,
        graph=graph,
        parcels=parcels,
        sort_algo=args.sort_algo,
        pack_algo=args.pack_algo,
        apply_two_opt=not args.no_two_opt,
    )
    report = format_plan_report(plan, graph, show_dp_table=not args.hide_dp_table)
    print(report)

    if args.save_trace:
        trace_path = Path(args.save_trace)
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        trace_path.write_text(report + "\n", encoding="utf-8")
        print(f"\nSaved output trace to: {trace_path}")


def cmd_benchmark(args: argparse.Namespace) -> None:
    print("Running Phase 4 performance benchmarks across sorting, knapsack, and routing...")
    results = run_all_benchmarks(output_dir=args.output_dir)
    chart_paths = generate_charts(results, charts_dir=Path(args.output_dir) / "charts")
    print(f"Benchmark JSON/CSV saved to: {args.output_dir}")
    for cp in chart_paths:
        print(f"Generated chart: {cp}")


def cmd_generate_datasets(args: argparse.Namespace) -> None:
    out_dir = Path(args.output_dir)
    specs = [
        ("sample_medium.json", "Medium City Courier Network (80 Parcels, 25 Stops)", 80, 25, 120, 42),
        ("sample_large.json", "Large Metro Courier Network (250 Parcels, 60 Stops)", 250, 60, 250, 99),
    ]
    for filename, title, n_p, n_v, cap, seed in specs:
        name, cap_val, depot, graph, parcels = generate_synthetic_scenario(
            num_parcels=n_p, num_nodes=n_v, vehicle_capacity=cap, seed=seed, dataset_name=title
        )
        target = out_dir / filename
        save_scenario(target, name, cap_val, depot, graph, parcels)
        print(f"Generated dataset: {target} ({len(parcels)} parcels, {len(graph.nodes)} nodes)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="courier-planner",
        description="Intelligent Courier Planning System — DAA Capstone Prototype",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    plan_p = sub.add_parser("plan", help="Run end-to-end courier prioritization, packing, and routing")
    plan_p.add_argument("--dataset", default="data/sample_small.json", help="Path to JSON scenario file")
    plan_p.add_argument(
        "--sort-algo",
        choices=["merge_sort", "quick_sort", "insertion_sort"],
        default="merge_sort",
        help="Sorting algorithm for parcel prioritization",
    )
    plan_p.add_argument(
        "--pack-algo",
        choices=["knapsack_2d", "knapsack_1d", "knapsack_greedy"],
        default="knapsack_2d",
        help="Packing algorithm for vehicle box filling",
    )
    plan_p.add_argument("--no-two-opt", action="store_true", help="Disable 2-opt tour improvement")
    plan_p.add_argument("--hide-dp-table", action="store_true", help="Omit ASCII DP table preview")
    plan_p.add_argument("--save-trace", default="", help="Optional path to save output trace text")
    plan_p.set_defaults(func=cmd_plan)

    bench_p = sub.add_parser("benchmark", help="Run Phase 4 scaling benchmarks and generate Matplotlib charts")
    bench_p.add_argument("--output-dir", default="results", help="Directory for benchmark files and charts")
    bench_p.set_defaults(func=cmd_benchmark)

    gen_p = sub.add_parser("generate-datasets", help="Generate medium and large sample JSON datasets")
    gen_p.add_argument("--output-dir", default="data", help="Output directory for JSON datasets")
    gen_p.set_defaults(func=cmd_generate_datasets)

    web_p = sub.add_parser("web", help="Launch the interactive browser dashboard")
    web_p.add_argument("--host", default="127.0.0.1", help="Host interface to bind")
    web_p.add_argument("--port", type=int, default=8765, help="Port to listen on")
    web_p.set_defaults(func=lambda a: serve(host=a.host, port=a.port))

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
