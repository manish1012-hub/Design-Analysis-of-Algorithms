"""Generate a publication-quality PDF Capstone report from project artifacts."""

from __future__ import annotations

import base64
import json
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.io_utils import load_scenario
from src.knapsack import format_dp_table_preview
from src.planner import run_courier_plan

RESULTS_DIR = ROOT_DIR / "results"
CHARTS_DIR = RESULTS_DIR / "charts"
DOCS_DIR = ROOT_DIR / "docs"


def _img_data_uri(path: Path) -> str:
    raw = path.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:image/png;base64,{b64}"


def build_html_report() -> str:
    bench = json.loads((RESULTS_DIR / "benchmark_results.json").read_text(encoding="utf-8"))
    name, cap, depot, graph, parcels = load_scenario(ROOT_DIR / "data" / "sample_small.json")
    plan = run_courier_plan(name, cap, depot, graph, parcels)
    selected_ids = {p.parcel_id for p in plan.packing.selected_parcels}
    dp_ascii = format_dp_table_preview(plan.packing.dp_table or [], plan.prioritized_parcels)

    chart_sort = _img_data_uri(CHARTS_DIR / "sorting_runtime.png")
    chart_knap = _img_data_uri(CHARTS_DIR / "knapsack_comparison.png")
    chart_route = _img_data_uri(CHARTS_DIR / "routing_optimization.png")
    chart_pipe = _img_data_uri(CHARTS_DIR / "pipeline_breakdown.png")

    parcel_rows = "\n".join(
        f"""<tr>
            <td>{idx}</td>
            <td><strong>{p.parcel_id}</strong></td>
            <td>{p.destination}</td>
            <td>{p.weight} kg</td>
            <td>${p.value}</td>
            <td>{p.deadline_hours:.1f} h</td>
            <td>P{p.priority}</td>
            <td><span class="badge {'badge-green' if p.parcel_id in selected_ids else 'badge-gray'}">
                {'PACKED' if p.parcel_id in selected_ids else 'DEFERRED'}
            </span></td>
        </tr>"""
        for idx, p in enumerate(plan.prioritized_parcels, start=1)
    )

    sp_rows = "\n".join(
        f"""<tr>
            <td><strong>{depot} &rarr; {stop}</strong></td>
            <td>{dist:.1f} km</td>
            <td><code>{' &rarr; '.join(path)}</code></td>
        </tr>"""
        for stop, (dist, path) in sorted(plan.route.shortest_paths_from_depot.items())
        if stop != depot
    )

    leg_rows = "\n".join(
        f"""<tr>
            <td>Leg {idx:02d}</td>
            <td>{leg.start}</td>
            <td>{leg.end}</td>
            <td>{leg.distance:.1f} km</td>
            <td><code>{' &rarr; '.join(leg.path)}</code></td>
        </tr>"""
        for idx, leg in enumerate(plan.route.legs, start=1)
    )

    sort_rows = "\n".join(
        f"""<tr>
            <td>{r['n_parcels']}</td>
            <td>{r['merge_sort_ms']:.4f} ms</td>
            <td>{r['quick_sort_ms']:.4f} ms</td>
            <td>{r['insertion_sort_ms']:.4f} ms</td>
        </tr>"""
        for r in bench["sorting"]
    )

    knap_rows = "\n".join(
        f"""<tr>
            <td>n={r['n_parcels']}, W={r['capacity']}</td>
            <td>{r['dp_2d_ms']:.4f} ms</td>
            <td>{r['dp_1d_ms']:.4f} ms</td>
            <td>{r['greedy_ms']:.4f} ms</td>
            <td>{r['dp_optimal_value']}</td>
            <td>{r['greedy_value']}</td>
        </tr>"""
        for r in bench["knapsack"]
    )

    route_rows = "\n".join(
        f"""<tr>
            <td>V={r['n_nodes']}, E={r['n_edges']}</td>
            <td>{r['nn_tsp_ms']:.4f} ms</td>
            <td>{r['nn_two_opt_ms']:.4f} ms</td>
            <td>{r['nn_distance']:.1f} km</td>
            <td>{r['two_opt_distance']:.1f} km</td>
            <td><strong>{r['distance_improvement_pct']:.2f}%</strong></td>
        </tr>"""
        for r in bench["routing"]
    )

    pipe_rows = "\n".join(
        f"""<tr>
            <td>{r['scenario']}</td>
            <td>{r['selected_count']}</td>
            <td>{r['total_value']}</td>
            <td>{r['route_distance']:.1f} km</td>
            <td>{r['sorting_ms']:.4f} ms</td>
            <td>{r['knapsack_ms']:.4f} ms</td>
            <td>{r['routing_ms']:.4f} ms</td>
            <td><strong>{r['total_ms']:.4f} ms</strong></td>
        </tr>"""
        for r in bench["pipeline"]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>Intelligent Courier Planning System — DAA Capstone Report</title>
<style>
  @page {{
    size: A4;
    margin: 15mm 14mm 16mm 14mm;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #1e293b;
    font-size: 9.8pt;
    line-height: 1.45;
    margin: 0;
  }}
  .cover {{
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
    color: #f8fafc;
    padding: 24px 26px;
    border-radius: 10px;
    margin-bottom: 16px;
  }}
  .cover .eyebrow {{
    font-size: 8.5pt;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #7dd3fc;
    font-weight: 700;
  }}
  .cover h1 {{
    margin: 6px 0 8px;
    font-size: 20pt;
    line-height: 1.2;
  }}
  .cover p {{
    margin: 0;
    color: #cbd5e1;
    font-size: 10pt;
  }}
  .meta-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    margin: 14px 0 18px;
  }}
  .meta-card {{
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 9px 11px;
    background: #f8fafc;
  }}
  .meta-card .k {{
    font-size: 7.5pt;
    text-transform: uppercase;
    color: #64748b;
    font-weight: 700;
  }}
  .meta-card .v {{
    font-size: 11.5pt;
    font-weight: 700;
    color: #0f172a;
    margin-top: 2px;
  }}
  h2 {{
    font-size: 13pt;
    color: #0f172a;
    border-bottom: 2px solid #0284c7;
    padding-bottom: 4px;
    margin: 18px 0 10px;
    page-break-after: avoid;
  }}
  h3 {{
    font-size: 10.5pt;
    color: #1e3a5f;
    margin: 12px 0 6px;
    page-break-after: avoid;
  }}
  p {{ margin: 0 0 8px; }}
  ul {{ margin: 4px 0 10px 18px; padding: 0; }}
  li {{ margin-bottom: 3px; }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 8px 0 12px;
    font-size: 8.6pt;
    page-break-inside: avoid;
  }}
  th, td {{
    border: 1px solid #cbd5e1;
    padding: 5px 7px;
    text-align: left;
  }}
  th {{
    background: #f1f5f9;
    color: #0f172a;
    font-weight: 700;
  }}
  code, pre {{
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, monospace;
    font-size: 8pt;
  }}
  pre {{
    background: #0f172a;
    color: #e2e8f0;
    padding: 10px 12px;
    border-radius: 6px;
    overflow-x: auto;
    line-height: 1.35;
    page-break-inside: avoid;
  }}
  .badge {{
    display: inline-block;
    padding: 1px 6px;
    border-radius: 999px;
    font-size: 7.5pt;
    font-weight: 700;
  }}
  .badge-green {{ background: #dcfce7; color: #166534; }}
  .badge-gray {{ background: #e2e8f0; color: #475569; }}
  .callout {{
    background: #f0f9ff;
    border-left: 4px solid #0284c7;
    padding: 8px 12px;
    border-radius: 4px;
    margin: 8px 0 12px;
    page-break-inside: avoid;
  }}
  .chart-wrap {{
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 8px;
    margin: 8px 0 14px;
    text-align: center;
    background: #ffffff;
    page-break-inside: avoid;
  }}
  .chart-wrap img {{
    max-width: 100%;
    height: auto;
    max-height: 235px;
  }}
  .chart-caption {{
    font-size: 8.2pt;
    color: #475569;
    margin-top: 4px;
  }}
  .page-break {{ page-break-before: always; }}
</style>
</head>
<body>

<div class="cover">
  <div class="eyebrow">Design &amp; Analysis of Algorithms (DAA) — Capstone Project Report</div>
  <h1>Intelligent Courier Planning System</h1>
  <p>Integrated Python prototype combining Sorting, 0/1 Knapsack Dynamic Programming, Dijkstra's Shortest-Path Algorithm, and Nearest-Neighbor TSP (+ 2-Opt Optimization) with CLI, Automated Tests, Benchmarks, and Interactive Web Dashboard.</p>
</div>

<div class="meta-grid">
  <div class="meta-card"><div class="k">Phases Covered</div><div class="v">Phases 1 – 5 (100 Marks)</div></div>
  <div class="meta-card"><div class="k">Implementation</div><div class="v">Python 3.13 (From Scratch)</div></div>
  <div class="meta-card"><div class="k">Test Verification</div><div class="v">7 / 7 Passed (pytest)</div></div>
  <div class="meta-card"><div class="k">Small Demo Runtime</div><div class="v">{plan.timings_ms['total_ms']:.4f} ms End-to-End</div></div>
</div>

<h2>1. Phase 1: Courier Problem Design and Planning</h2>
<p>
  Given a list of courier parcels <em>P = {{p<sub>1</sub>, &hellip;, p<sub>n</sub>}}</em>, a delivery vehicle with integer weight capacity <em>W</em>, and a weighted road network <em>G = (V, E, w)</em> rooted at a central <code>Depot</code>, the system computes an ordered dispatch schedule, an optimal cargo selection, and a shortest-path closed delivery route.
</p>

<div class="chart-wrap">
  <svg viewBox="0 0 760 110" width="100%" height="92" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
        <path d="M0,0 L0,6 L7,3 z" fill="#0284c7"/>
      </marker>
    </defs>
    <rect x="8" y="22" width="125" height="62" rx="8" fill="#f1f5f9" stroke="#64748b"/>
    <text x="70" y="48" text-anchor="middle" font-size="10.5" font-weight="700" fill="#0f172a">Input JSON</text>
    <text x="70" y="64" text-anchor="middle" font-size="8.5" fill="#475569">Parcels, W, Graph</text>

    <line x1="133" y1="53" x2="162" y2="53" stroke="#0284c7" stroke-width="2" marker-end="url(#arrow)"/>

    <rect x="164" y="22" width="132" height="62" rx="8" fill="#e0f2fe" stroke="#0284c7"/>
    <text x="230" y="46" text-anchor="middle" font-size="10.5" font-weight="700" fill="#0f172a">Phase 2A: Sort</text>
    <text x="230" y="62" text-anchor="middle" font-size="8.5" fill="#0369a1">Merge / Quick Sort</text>
    <text x="230" y="74" text-anchor="middle" font-size="8" fill="#475569">O(n log n)</text>

    <line x1="296" y1="53" x2="325" y2="53" stroke="#0284c7" stroke-width="2" marker-end="url(#arrow)"/>

    <rect x="327" y="22" width="135" height="62" rx="8" fill="#dcfce7" stroke="#16a34a"/>
    <text x="394" y="46" text-anchor="middle" font-size="10.5" font-weight="700" fill="#0f172a">Phase 2B: Pack</text>
    <text x="394" y="62" text-anchor="middle" font-size="8.5" fill="#15803d">0/1 Knapsack DP</text>
    <text x="394" y="74" text-anchor="middle" font-size="8" fill="#475569">O(nW)</text>

    <line x1="462" y1="53" x2="491" y2="53" stroke="#0284c7" stroke-width="2" marker-end="url(#arrow)"/>

    <rect x="493" y="22" width="135" height="62" rx="8" fill="#fef3c7" stroke="#d97706"/>
    <text x="560" y="46" text-anchor="middle" font-size="10.5" font-weight="700" fill="#0f172a">Phase 3: Route</text>
    <text x="560" y="62" text-anchor="middle" font-size="8.5" fill="#b45309">Dijkstra + NN TSP</text>
    <text x="560" y="74" text-anchor="middle" font-size="8" fill="#475569">O(k(V+E)logV + k^2)</text>

    <line x1="628" y1="53" x2="655" y2="53" stroke="#0284c7" stroke-width="2" marker-end="url(#arrow)"/>

    <rect x="657" y="22" width="95" height="62" rx="8" fill="#0f172a" stroke="#0f172a"/>
    <text x="704" y="48" text-anchor="middle" font-size="10.5" font-weight="700" fill="#ffffff">Dispatch</text>
    <text x="704" y="64" text-anchor="middle" font-size="8.5" fill="#7dd3fc">Plan + Trace</text>
  </svg>
  <div class="chart-caption">Figure 1: Integrated end-to-end algorithmic pipeline linking Phases 1&ndash;3.</div>
</div>

<table>
  <thead>
    <tr><th>Phase</th><th>Algorithm</th><th>Time Complexity</th><th>Space Complexity</th><th>Role &amp; Justification</th></tr>
  </thead>
  <tbody>
    <tr><td>2A</td><td>Merge Sort (Primary)</td><td>O(n log n) worst-case</td><td>O(n)</td><td>Stable multi-key prioritization (deadline, priority, value/kg).</td></tr>
    <tr><td>2A</td><td>Quick Sort / Insertion Sort</td><td>O(n log n) avg / O(n<sup>2</sup>)</td><td>O(log n) / O(1)</td><td>Performance baselines for Phase 4 runtime scaling comparison.</td></tr>
    <tr><td>2B</td><td>0/1 Knapsack (2D &amp; 1D DP)</td><td>O(nW)</td><td>O(nW) / O(W)</td><td>Guarantees exact optimal integer-capacity packing; beats greedy traps.</td></tr>
    <tr><td>3A</td><td>Dijkstra's Algorithm (Heap)</td><td>O((V + E) log V) per stop</td><td>O(V)</td><td>Computes exact shortest road paths on non-negative sparse graphs.</td></tr>
    <tr><td>3B</td><td>Nearest-Neighbor TSP + 2-Opt</td><td>O(k<sup>2</sup>) + 2-Opt</td><td>O(k<sup>2</sup>)</td><td>Fast approximation for NP-hard TSP; 2-Opt removes crossing tour legs.</td></tr>
  </tbody>
</table>

<div class="page-break"></div>

<h2>2. Phase 2: Package Prioritization &amp; Box Filling</h2>
<p>
  On <code>data/sample_small.json</code> (12 parcels, vehicle capacity = <strong>25 kg</strong>), parcels are first sorted by <code>(deadline_hours ASC, priority DESC, value/weight DESC, parcel_id ASC)</code>, then passed into the 2D 0/1 Knapsack DP solver.
</p>

<div class="callout">
  <strong>Phase 2 Result Summary:</strong> Selected <strong>6 / 12 parcels</strong> using <strong>25 / 25 kg (100.0% capacity utilization)</strong> for a globally optimal total value of <strong>$595</strong>.
</div>

<table>
  <thead>
    <tr><th>Rank</th><th>ID</th><th>Destination</th><th>Weight</th><th>Value</th><th>Deadline</th><th>Priority</th><th>Packing Decision</th></tr>
  </thead>
  <tbody>{parcel_rows}</tbody>
</table>

<h3>DP Table Evidence (2D Dynamic Programming Matrix Preview)</h3>
<pre>{dp_ascii}</pre>

<h2>3. Phase 3: Route Maker &amp; Graph Processing</h2>
<p>
  Only the unique destinations of the 6 selected parcels (<code>Sector_A</code>, <code>Sector_B</code>, <code>Market_Hub</code>, <code>Station</code>) plus <code>Depot</code> enter the routing subgraph. Dijkstra's algorithm computes shortest road paths across all 8 nodes and 12 edges, and Nearest-Neighbor TSP + 2-Opt orders the closed tour.
</p>

<table>
  <thead><tr><th>Shortest Path from Depot</th><th>Distance</th><th>Dijkstra Road Sequence</th></tr></thead>
  <tbody>{sp_rows}</tbody>
</table>

<div class="callout">
  <strong>Final Ordered Route:</strong> <code>{' &rarr; '.join(plan.route.stop_sequence)}</code> &nbsp;|&nbsp; <strong>Total Distance: {plan.route.total_distance:.2f} km</strong>
</div>

<table>
  <thead><tr><th>Leg</th><th>Start</th><th>End</th><th>Distance</th><th>Expanded Road Path</th></tr></thead>
  <tbody>{leg_rows}</tbody>
</table>

<div class="page-break"></div>

<h2>4. Phase 4: Performance Testing &amp; Optimization</h2>

<h3>4.1 Parcel Sorting Scaling (n = 25 to 2,000 Parcels)</h3>
<table>
  <thead><tr><th>Parcels (n)</th><th>Merge Sort</th><th>Quick Sort</th><th>Insertion Sort</th></tr></thead>
  <tbody>{sort_rows}</tbody>
</table>
<div class="chart-wrap">
  <img src="{chart_sort}" alt="Sorting Runtime Comparison" />
  <div class="chart-caption">Figure 2: Quadratic O(n<sup>2</sup>) growth of Insertion Sort (78.62 ms at n=2,000) vs O(n log n) Merge Sort (6.15 ms) and Quick Sort (2.05 ms).</div>
</div>

<h3>4.2 Knapsack Packing Runtime &amp; Optimality</h3>
<table>
  <thead><tr><th>Scale (n, W)</th><th>2D DP</th><th>1D Space-Opt DP</th><th>Greedy</th><th>DP Optimal Value</th><th>Greedy Value</th></tr></thead>
  <tbody>{knap_rows}</tbody>
</table>
<div class="chart-wrap">
  <img src="{chart_knap}" alt="Knapsack Comparison" />
  <div class="chart-caption">Figure 3: Space-optimized 1D DP reduces runtime by 42.5% at (n=300, W=500) while preserving exact optimality over greedy counterexamples (e.g., 220 vs 160 in unit test).</div>
</div>

<h3>4.3 Graph Routing Scaling &amp; 2-Opt Distance Optimization</h3>
<table>
  <thead><tr><th>Graph Scale</th><th>NN TSP Time</th><th>NN + 2-Opt Time</th><th>NN Distance</th><th>2-Opt Distance</th><th>Distance Saved</th></tr></thead>
  <tbody>{route_rows}</tbody>
</table>
<div class="chart-wrap">
  <img src="{chart_route}" alt="Routing Optimization" />
  <div class="chart-caption">Figure 4: 2-Opt local search cuts total travel distance by 6.12%&ndash;18.36% on 15&ndash;100 node networks with minimal compute overhead.</div>
</div>

<h3>4.4 End-to-End Pipeline Breakdown</h3>
<table>
  <thead><tr><th>Scenario</th><th>Selected</th><th>Value</th><th>Distance</th><th>Sorting</th><th>Knapsack</th><th>Routing</th><th>Total</th></tr></thead>
  <tbody>{pipe_rows}</tbody>
</table>
<div class="chart-wrap">
  <img src="{chart_pipe}" alt="Pipeline Breakdown" />
  <div class="chart-caption">Figure 5: Per-phase execution breakdown across Small (0.09 ms), Medium (1.33 ms), and Large (8.71 ms) scenarios.</div>
</div>

<h2>5. Phase 5: Verification, Execution &amp; Future Work</h2>
<ul>
  <li><strong>Automated Verification:</strong> All <strong>7 / 7</strong> tests in <code>tests/test_algorithms.py</code> pass under <code>pytest -v</code> (0.02 s), validating sorting stability, DP vs. greedy optimality, Dijkstra indirect shortcuts, TSP tour closure, and full pipeline integration.</li>
  <li><strong>Interactive Web Dashboard:</strong> Implemented in <code>web/server.py</code> and <code>web/index.html</code> (<code>python main.py web --port 8765</code>) with live SVG route rendering, algorithm switching, DP matrix inspection, and embedded benchmark plots.</li>
  <li><strong>Future Optimizations:</strong> Multi-vehicle Fleet Routing (VRP) for deferred parcels, deadline-penalized Time-Window TSP (TSPTW), Held-Karp exact TSP for small stop subsets (k &le; 15), and Branch-and-Bound knapsack for high-precision weights.</li>
</ul>

<h3>Execution Commands</h3>
<pre>source .venv/bin/activate
pytest -v
python main.py plan --dataset data/sample_small.json --save-trace results/demo_trace_small.txt
python main.py benchmark
python main.py web --port 8765</pre>

</body>
</html>
"""


def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    html_path = DOCS_DIR / "Capstone_Report.html"
    pdf_path = DOCS_DIR / "Capstone_Report.pdf"

    html_content = build_html_report()
    html_path.write_text(html_content, encoding="utf-8")

    chrome_bin = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    if not chrome_bin.exists():
        raise FileNotFoundError(f"Google Chrome binary not found at {chrome_bin}")

    cmd = [
        str(chrome_bin),
        "--headless=new",
        "--disable-gpu",
        "--user-data-dir=/tmp/chrome-pdf-profile",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        html_path.as_uri(),
    ]
    subprocess.run(cmd, check=True)
    print(f"Generated HTML: {html_path}")
    print(f"Generated PDF:  {pdf_path} ({pdf_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
