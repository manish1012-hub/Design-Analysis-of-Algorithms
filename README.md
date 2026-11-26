# Intelligent Courier Planning System (DAA Capstone)

An integrated Python application combining **Sorting**, **Dynamic Programming (0/1 Knapsack)**, **Dijkstra's Shortest-Path Algorithm**, and **Nearest-Neighbor TSP (+ 2-Opt Optimization)** to simulate an intelligent courier dispatch and route-planning engine.

---

## Project Structure

```text
DAA (Capstone)/
├── main.py                      # CLI entrypoint (plan, benchmark, generate-datasets)
├── pyproject.toml               # Pytest path configuration
├── requirements.txt             # matplotlib, pytest
├── data/
│   ├── sample_small.json        # 12 parcels, 8 nodes (handcrafted demo)
│   ├── sample_medium.json       # 80 parcels, 25 nodes
│   └── sample_large.json        # 250 parcels, 60 nodes
├── src/
│   ├── models.py                # Parcel, PackingResult, RouteLeg, RouteResult, CourierPlan
│   ├── sorting.py               # Merge Sort, Quick Sort, Insertion Sort (from scratch)
│   ├── knapsack.py              # 0/1 Knapsack (2D DP, 1D Space-Opt DP, Greedy baseline)
│   ├── graph.py                 # Adjacency-list DeliveryGraph + Dijkstra + path reconstruction
│   ├── tsp.py                   # Nearest-Neighbor TSP + 2-Opt local search
│   ├── io_utils.py              # JSON scenario loader/saver + synthetic generator
│   ├── planner.py               # End-to-end pipeline & formatted trace generator
│   ├── benchmark.py             # Phase 4 scaling benchmarks (JSON + CSV)
│   └── charts.py                # Matplotlib PNG runtime & optimality chart generator
├── tests/
│   └── test_algorithms.py       # Unit & integration tests (pytest / unittest)
├── docs/
│   ├── DESIGN.md                # Phase 1: Problem design, schemas, and algorithm selection
│   └── REPORT.md                # Phase 4 & 5: Benchmark analysis, charts, and recommendations
└── results/
    ├── benchmark_results.json   # Raw benchmark measurements
    ├── benchmark_summary.csv    # Tabular summary of benchmark runs
    ├── demo_trace_small.txt     # Saved execution trace for sample_small.json
    ├── demo_trace_medium.txt    # Saved execution trace for sample_medium.json
    └── charts/                  # Generated Matplotlib PNG plots
        ├── sorting_runtime.png
        ├── knapsack_comparison.png
        ├── routing_optimization.png
        └── pipeline_breakdown.png
```

---

## Setup & Execution Steps

### 1. Environment Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Unit & Integration Tests
```bash
pytest -v
```

### 3. Run the Courier Planner CLI
Run on the small demo dataset (includes DP table preview, Dijkstra paths, and turn-by-turn route):
```bash
python main.py plan --dataset data/sample_small.json
```

Compare different algorithms (e.g., Quick Sort + 1D Space-Optimized DP without 2-Opt):
```bash
python main.py plan --dataset data/sample_medium.json --sort-algo quick_sort --pack-algo knapsack_1d --no-two-opt
```

Save an execution trace to disk:
```bash
python main.py plan --dataset data/sample_small.json --save-trace results/demo_trace_small.txt
```

### 4. Run Phase 4 Benchmarks & Regenerate Charts
```bash
python main.py benchmark
```
Outputs `results/benchmark_results.json`, `results/benchmark_summary.csv`, and 4 PNG charts in `results/charts/`.

### 5. Regenerate Medium & Large Sample Datasets
```bash
python main.py generate-datasets
```

---

## Capstone Phase Mapping

| Phase | Title | Artifacts & Modules |
|---|---|---|
| **Phase 1** | Courier Problem Design and Planning | [DESIGN.md](docs/DESIGN.md), [models.py](src/models.py) |
| **Phase 2** | Package Prioritization and Box Filling | [sorting.py](src/sorting.py), [knapsack.py](src/knapsack.py), [demo_trace_small.txt](results/demo_trace_small.txt) |
| **Phase 3** | Route Maker and Graph Processing | [graph.py](src/graph.py), [tsp.py](src/tsp.py) |
| **Phase 4** | Performance Testing and Optimization | [benchmark.py](src/benchmark.py), [charts.py](src/charts.py), `results/charts/*.png` |
| **Phase 5** | Final Report and Demonstration | [REPORT.md](docs/REPORT.md), [README.md](README.md), [test_algorithms.py](tests/test_algorithms.py) |
