"""Phase 2: Parcel prioritization sorting algorithms implemented from scratch."""

from __future__ import annotations

from typing import Callable, TypeVar

from src.models import Parcel

T = TypeVar("T")


def parcel_priority_key(parcel: Parcel) -> tuple[float, int, float, str]:
    """Return a deterministic ordering key for courier dispatch prioritization.

    Ordering rules (ascending tuple comparison):
    1. Earlier deadline first (`deadline_hours` ascending).
    2. Higher priority tier first (`-priority` ascending).
    3. Higher value density first (`-(value / weight)` ascending, treating 0 weight as inf).
    4. Stable tie-break by `parcel_id`.
    """
    density = (parcel.value / parcel.weight) if parcel.weight > 0 else float("inf")
    return (parcel.deadline_hours, -parcel.priority, -density, parcel.parcel_id)


def merge_sort(items: list[T], key: Callable[[T], object] | None = None) -> list[T]:
    """Sort `items` stably using top-down Merge Sort.

    Time Complexity: O(n log n) worst, average, and best case.
    Space Complexity: O(n) auxiliary space.
    """
    if len(items) <= 1:
        return list(items)

    key_fn = key or (lambda x: x)
    mid = len(items) // 2
    left = merge_sort(items[:mid], key=key_fn)
    right = merge_sort(items[mid:], key=key_fn)
    return _merge(left, right, key_fn)


def _merge(left: list[T], right: list[T], key_fn: Callable[[T], object]) -> list[T]:
    merged: list[T] = []
    i = 0
    j = 0
    while i < len(left) and j < len(right):
        # <= preserves stability when keys are equal.
        if key_fn(left[i]) <= key_fn(right[j]):  # type: ignore[operator]
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1
    if i < len(left):
        merged.extend(left[i:])
    if j < len(right):
        merged.extend(right[j:])
    return merged


def quick_sort(items: list[T], key: Callable[[T], object] | None = None) -> list[T]:
    """Sort `items` using Quick Sort with median-of-three pivot selection.

    Time Complexity: O(n log n) expected, O(n^2) worst case.
    Space Complexity: O(log n) recursion stack on average (returns a new list).
    """
    arr = list(items)
    if len(arr) <= 1:
        return arr

    key_fn = key or (lambda x: x)
    keys = [key_fn(x) for x in arr]
    _quick_sort_inplace(arr, keys, 0, len(arr) - 1)
    return arr


def _median_of_three(keys: list[object], low: int, high: int) -> int:
    mid = (low + high) // 2
    if keys[low] > keys[mid]:  # type: ignore[operator]
        low, mid = mid, low
    if keys[low] > keys[high]:  # type: ignore[operator]
        low, high = high, low
    if keys[mid] > keys[high]:  # type: ignore[operator]
        mid = high
    return mid


def _quick_sort_inplace(arr: list[T], keys: list[object], low: int, high: int) -> None:
    while low < high:
        pivot_idx = _median_of_three(keys, low, high)
        keys[pivot_idx], keys[high] = keys[high], keys[pivot_idx]
        arr[pivot_idx], arr[high] = arr[high], arr[pivot_idx]

        p = _partition(arr, keys, low, high)
        # Tail-call elimination: recurse on smaller partition first to bound stack depth.
        if p - low < high - p:
            _quick_sort_inplace(arr, keys, low, p - 1)
            low = p + 1
        else:
            _quick_sort_inplace(arr, keys, p + 1, high)
            high = p - 1


def _partition(arr: list[T], keys: list[object], low: int, high: int) -> int:
    pivot = keys[high]
    i = low - 1
    for j in range(low, high):
        if keys[j] <= pivot:  # type: ignore[operator]
            i += 1
            arr[i], arr[j] = arr[j], arr[i]
            keys[i], keys[j] = keys[j], keys[i]
    arr[i + 1], arr[high] = arr[high], arr[i + 1]
    keys[i + 1], keys[high] = keys[high], keys[i + 1]
    return i + 1


def insertion_sort(items: list[T], key: Callable[[T], object] | None = None) -> list[T]:
    """Sort `items` stably using Insertion Sort (baseline for performance comparison).

    Time Complexity: O(n^2) worst/average case, O(n) nearly-sorted best case.
    Space Complexity: O(1) auxiliary beyond output copy.
    """
    arr = list(items)
    key_fn = key or (lambda x: x)
    keys = [key_fn(x) for x in arr]

    for i in range(1, len(arr)):
        current_item = arr[i]
        current_key = keys[i]
        j = i - 1
        while j >= 0 and keys[j] > current_key:  # type: ignore[operator]
            arr[j + 1] = arr[j]
            keys[j + 1] = keys[j]
            j -= 1
        arr[j + 1] = current_item
        keys[j + 1] = current_key
    return arr


SORTING_ALGORITHMS: dict[str, Callable[[list[Parcel], Callable[[Parcel], object]], list[Parcel]]] = {
    "merge_sort": merge_sort,
    "quick_sort": quick_sort,
    "insertion_sort": insertion_sort,
}


def sort_parcels(parcels: list[Parcel], algorithm: str = "merge_sort") -> list[Parcel]:
    """Prioritize parcels using the chosen sorting algorithm."""
    if algorithm not in SORTING_ALGORITHMS:
        raise ValueError(f"Unknown sorting algorithm '{algorithm}'. Choose from {list(SORTING_ALGORITHMS)}")
    return SORTING_ALGORITHMS[algorithm](parcels, parcel_priority_key)
