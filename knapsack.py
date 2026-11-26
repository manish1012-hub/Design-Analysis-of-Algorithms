"""Phase 2: Dynamic Programming (0/1 Knapsack) and greedy baseline for vehicle packing."""

from __future__ import annotations

from src.models import PackingResult, Parcel


def knapsack_2d(parcels: list[Parcel], capacity: int) -> PackingResult:
    """Solve 0/1 Knapsack using full 2D Dynamic Programming table with backtracking.

    Time Complexity: O(n * W), where n = len(parcels) and W = capacity.
    Space Complexity: O(n * W) to store the DP table for reconstruction and inspection.
    """
    if capacity < 0:
        raise ValueError("Vehicle capacity must be non-negative.")

    n = len(parcels)
    dp: list[list[int]] = [[0] * (capacity + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        parcel = parcels[i - 1]
        w_i = parcel.weight
        v_i = parcel.value
        for w in range(capacity + 1):
            if w_i <= w:
                include_val = dp[i - 1][w - w_i] + v_i
                exclude_val = dp[i - 1][w]
                dp[i][w] = include_val if include_val > exclude_val else exclude_val
            else:
                dp[i][w] = dp[i - 1][w]

    # Backtrack through the DP table to recover exact selected parcels.
    selected_indices: set[int] = set()
    w_rem = capacity
    for i in range(n, 0, -1):
        if dp[i][w_rem] != dp[i - 1][w_rem]:
            selected_indices.add(i - 1)
            w_rem -= parcels[i - 1].weight

    selected = [p for idx, p in enumerate(parcels) if idx in selected_indices]
    excluded = [p for idx, p in enumerate(parcels) if idx not in selected_indices]
    total_weight = sum(p.weight for p in selected)
    total_value = dp[n][capacity]

    return PackingResult(
        selected_parcels=selected,
        excluded_parcels=excluded,
        total_weight=total_weight,
        total_value=total_value,
        capacity=capacity,
        algorithm="0/1 Knapsack (2D DP)",
        dp_table=dp,
    )


def knapsack_1d(parcels: list[Parcel], capacity: int) -> PackingResult:
    """Solve 0/1 Knapsack with O(W) space optimization and choice bitmasks/pointers.

    Time Complexity: O(n * W).
    Space Complexity: O(W) for DP value array (plus boolean decision table if reconstructing).
    """
    if capacity < 0:
        raise ValueError("Vehicle capacity must be non-negative.")

    n = len(parcels)
    dp = [0] * (capacity + 1)
    keep = [[False] * (capacity + 1) for _ in range(n)]

    for i, parcel in enumerate(parcels):
        w_i = parcel.weight
        v_i = parcel.value
        for w in range(capacity, w_i - 1, -1):
            candidate = dp[w - w_i] + v_i
            if candidate > dp[w]:
                dp[w] = candidate
                keep[i][w] = True

    selected_indices: set[int] = set()
    w_rem = capacity
    for i in range(n - 1, -1, -1):
        if keep[i][w_rem]:
            selected_indices.add(i)
            w_rem -= parcels[i].weight

    selected = [p for idx, p in enumerate(parcels) if idx in selected_indices]
    excluded = [p for idx, p in enumerate(parcels) if idx not in selected_indices]
    return PackingResult(
        selected_parcels=selected,
        excluded_parcels=excluded,
        total_weight=sum(p.weight for p in selected),
        total_value=dp[capacity],
        capacity=capacity,
        algorithm="0/1 Knapsack (1D Space-Optimized DP)",
        dp_table=None,
    )


def knapsack_greedy(parcels: list[Parcel], capacity: int) -> PackingResult:
    """Greedy 0/1 heuristic sorted by value-to-weight ratio (for optimality comparison).

    Time Complexity: O(n log n).
    Note: Does NOT guarantee optimal total value for 0/1 Knapsack.
    """
    if capacity < 0:
        raise ValueError("Vehicle capacity must be non-negative.")

    ranked = sorted(
        enumerate(parcels),
        key=lambda pair: (
            -(pair[1].value / pair[1].weight) if pair[1].weight > 0 else float("-inf"),
            -pair[1].value,
        ),
    )

    selected_indices: set[int] = set()
    used_weight = 0
    for idx, parcel in ranked:
        if used_weight + parcel.weight <= capacity:
            selected_indices.add(idx)
            used_weight += parcel.weight

    selected = [p for idx, p in enumerate(parcels) if idx in selected_indices]
    excluded = [p for idx, p in enumerate(parcels) if idx not in selected_indices]
    return PackingResult(
        selected_parcels=selected,
        excluded_parcels=excluded,
        total_weight=used_weight,
        total_value=sum(p.value for p in selected),
        capacity=capacity,
        algorithm="Greedy Value/Weight Heuristic",
        dp_table=None,
    )


def format_dp_table_preview(dp: list[list[int]], parcels: list[Parcel], max_rows: int = 12, max_cols: int = 16) -> str:
    """Format a compact ASCII preview of the DP table for demonstration evidence."""
    rows = min(len(dp), max_rows + 1)
    cols = min(len(dp[0]), max_cols + 1) if dp else 0
    header = "Item\\Cap | " + " ".join(f"{c:>4}" for c in range(cols))
    if dp and cols < len(dp[0]):
        header += f" ... {len(dp[0]) - 1:>4}"
    lines = [header, "-" * len(header)]

    for i in range(rows):
        label = "0 (init)" if i == 0 else parcels[i - 1].parcel_id
        row_vals = " ".join(f"{dp[i][c]:>4}" for c in range(cols))
        if cols < len(dp[i]):
            row_vals += f" ... {dp[i][-1]:>4}"
        lines.append(f"{label:<8} | {row_vals}")

    if rows < len(dp):
        lines.append(f"... ({len(dp) - rows} more parcel rows omitted)")
    return "\n".join(lines)
