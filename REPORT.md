# Phase 4 & 5 Report: Performance Testing, Optimization, and Demonstration

## 1. Executive Summary
This report documents the empirical performance evaluation, optimization analysis, and demonstration traces of the **Intelligent Courier Planning System** across all five Capstone phases. All algorithms were implemented from scratch in Python 3.13 (`src/sorting.py`, `src/knapsack.py`, `src/graph.py`, `src/tsp.py`) and verified with `pytest` (`7/7` tests passing).

---

## 2. Demonstration Trace Summary (`data/sample_small.json`)
- **Dataset**: 12 parcels, 8 road nodes, 12 edges, vehicle capacity = `25 kg`, depot = `Depot`.
- **Phase 2A (Merge Sort Prioritization)**: Ordered `P007` (2.0h, P5) $\rightarrow$ `P001` (2.0h, P5) $\rightarrow$ `P005` (2.5h, P4) $\rightarrow \dots \rightarrow$ `P009` (10.0h, P2).
- **Phase 2B (0/1 Knapsack 2D DP)**: Selected 6 parcels (`P007`, `P001`, `P005`, `P003`, `P012`, `P010`) using `25/25 kg` (**100.0%** utilization) for an optimal total value of **595**.
- **Phase 3 (Dijkstra + Nearest-Neighbor TSP + 2-Opt)**:
  - Visited all 4 unique destination stops of the selected parcels (`Sector_A`, `Market_Hub`, `Station`, `Sector_B`).
  - Ordered route: `Depot -> Sector_A -> Market_Hub -> Station -> Sector_B -> Depot`.
  - Total distance: **26.00 km** (computed end-to-end in **0.1210 ms**).
- Full trace files are saved in [demo_trace_small.txt](../results/demo_trace_small.txt) and [demo_trace_medium.txt](../results/demo_trace_medium.txt).

---

## 3. Phase 4: Performance Benchmarks & Observations

Raw data is stored in [benchmark_results.json](../results/benchmark_results.json) and [benchmark_summary.csv](../results/benchmark_summary.csv).

### 3.1 Phase 2A — Sorting Scaling ($n = 25 \dots 2000$ parcels)
| Parcels ($n$) | Merge Sort (ms) | Quick Sort (ms) | Insertion Sort (ms) |
|---:|---:|---:|---:|
| 25 | 0.0490 | 0.0212 | 0.0200 |
| 100 | 0.1895 | 0.0675 | 0.1740 |
| 500 | 1.2699 | 0.4531 | 4.3342 |
| 1000 | 2.7963 | 0.9367 | 19.5303 |
| 2000 | 6.1543 | 2.0510 | 78.6160 |

**Analysis**:
- At $n = 25$, Insertion Sort (`0.0200 ms`) is competitive due to minimal overhead.
- By $n = 2000$, Insertion Sort degrades quadratically ($O(n^2)$) to **78.6160 ms**, whereas Quick Sort (`2.0510 ms`) is **38.3x faster** and Merge Sort (`6.1543 ms`) is **12.8x faster** while preserving strict $O(n \log n)$ worst-case stability.

![Sorting Runtime Comparison](../results/charts/sorting_runtime.png)

---

### 3.2 Phase 2B — Packing Runtime & Optimality ($O(nW)$ vs $O(n \log n)$)
| Scale $(n, W)$ | 2D DP (ms) | 1D Space-Opt DP (ms) | Greedy (ms) | DP Optimal Value |
|---|---:|---:|---:|---:|
| $n=10, W=30$ | 0.0374 | 0.0195 | 0.0057 | 1410 |
| $n=50, W=120$ | 0.4868 | 0.3025 | 0.0150 | 4729 |
| $n=100, W=200$ | 1.6109 | 0.9555 | 0.0300 | 8086 |
| $n=300, W=500$ | 13.6256 | 7.8339 | 0.1030 | 21446 |

**Analysis**:
- **Space & cache optimization**: Switching from the full `dp[n+1][W+1]` 2D table to `knapsack_1d` reduced runtime by **42.5%** at $(300, 500)$ (`13.6256 ms` $\rightarrow$ `7.8339 ms`) and memory from $O(nW)$ integers to $O(W)$ integers + boolean backtracking flags.
- **Optimality vs. Greedy**: On tight integer-capacity edge cases (verified in `tests/test_algorithms.py :: test_dp_beats_greedy_on_classic_counterexample`), Greedy achieved `160` while 0/1 DP achieved `220` (+37.5% value). Thus 0/1 DP is essential whenever parcel weights do not divide capacity evenly.

![Knapsack Comparison](../results/charts/knapsack_comparison.png)

---

### 3.3 Phase 3 — Graph Shortest Paths & TSP Tour Optimization
| Nodes ($V$) | Edges ($E$) | NN TSP (ms) | NN + 2-Opt (ms) | NN Distance (km) | 2-Opt Distance (km) | Distance Saved |
|---:|---:|---:|---:|---:|---:|---:|
| 8 | 15 | 0.0841 | 0.0697 | 429.9 | 429.9 | 0.00% |
| 15 | 29 | 0.2273 | 0.2845 | 799.5 | 652.7 | **18.36%** |
| 25 | 49 | 0.6742 | 0.8416 | 1420.3 | 1267.1 | **10.79%** |
| 45 | 89 | 2.3213 | 2.6874 | 3172.2 | 2978.1 | **6.12%** |
| 70 | 139 | 5.6926 | 7.2390 | 5000.5 | 4437.3 | **11.26%** |
| 100 | 199 | 12.2267 | 15.5716 | 7171.8 | 6308.0 | **12.04%** |

**Analysis**:
- Applying **2-Opt local search** on top of Nearest-Neighbor TSP reduced total travel distance by **6.12%–18.36%** on graphs with $15 \dots 100$ nodes, adding only ~`0.06–3.34 ms` of compute time.

![Routing Optimization](../results/charts/routing_optimization.png)

---

### 3.4 End-to-End Pipeline Breakdown
| Scenario | Parcels | Nodes | Cap (kg) | Sorting (ms) | Knapsack (ms) | Routing (ms) | Total (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Small | 12 | 8 | 30 | 0.0185 | 0.0368 | 0.0356 | **0.0909** |
| Medium | 80 | 25 | 120 | 0.1493 | 0.7853 | 0.3903 | **1.3250** |
| Large | 250 | 60 | 250 | 0.5615 | 5.0082 | 3.1396 | **8.7093** |

![Pipeline Runtime Breakdown](../results/charts/pipeline_breakdown.png)

---

## 4. Suggested Improvements for Future Iterations
1. **Multi-Vehicle Capacitated Routing (VRP)**: Extend single-vehicle 0/1 Knapsack + TSP into multi-trip / fleet assignment for deferred parcels.
2. **Time-Window Constrained TSP (TSPTW)**: Incorporate parcel `deadline_hours` directly as hard edge/arrival penalties inside the 2-opt cost function rather than only at sorting time.
3. **Christofides / Held-Karp Hybrid**: For small active stop counts ($k \le 15$), use Held-Karp DP ($O(k^2 2^k)$) for exact TSP optimality; for larger $k$, use Christofides' 1.5-approximation or Lin-Kernighan heuristics.
4. **Meet-in-the-Middle / Branch-and-Bound Knapsack**: When parcel weights have high precision (large $W$), branch-and-bound or capacity scaling avoids pseudo-polynomial table blowup.
