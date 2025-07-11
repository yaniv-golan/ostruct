#!/usr/bin/env python3
"""dag_sort.py – Kahn topological sorter used by agent runner.

Reads a JSON array of steps from stdin. Each step must already contain
`provides` (list[str]) and `requires` (list[str]) fields that indicate
file dependencies.  Output JSON:
    {"error": null|str, "steps": [ ...sorted steps... ]}
If a cycle is detected, `error` is "cycle_detected" and `steps` is empty.
Any unexpected failure sets `error` to the exception string.
"""

import json
import sys
from collections import defaultdict, deque


def kahn_sort(steps):
    graph = defaultdict(list)
    in_deg = defaultdict(int)
    nodes = {}
    for idx, step in enumerate(steps):
        nid = f"step_{idx}"
        nodes[nid] = step
        in_deg[nid] = 0
    # build edges
    for i, step in enumerate(steps):
        provides = step.get("provides", [])
        for j, other in enumerate(steps):
            if i == j:
                continue
            requires = other.get("requires", [])
            if any(p in requires for p in provides):
                graph[f"step_{i}"].append(f"step_{j}")
                in_deg[f"step_{j}"] += 1
    # Kahn
    queue = deque([n for n, deg in in_deg.items() if deg == 0])
    result = []
    while queue:
        cur = queue.popleft()
        result.append(nodes[cur])
        for neigh in graph[cur]:
            in_deg[neigh] -= 1
            if in_deg[neigh] == 0:
                queue.append(neigh)
    has_cycle = len(result) != len(steps)
    return result, has_cycle


def main():
    try:
        steps = json.load(sys.stdin)
        if not steps:
            json.dump({"error": None, "steps": []}, sys.stdout)
            return
        sorted_steps, cycle = kahn_sort(steps)
        if cycle:
            json.dump({"error": "cycle_detected", "steps": []}, sys.stdout)
        else:
            json.dump({"error": None, "steps": sorted_steps}, sys.stdout)
    except json.JSONDecodeError:
        json.dump({"error": "json_decode_error", "steps": []}, sys.stdout)
    except Exception as exc:  # pylint: disable=broad-except
        json.dump({"error": str(exc), "steps": []}, sys.stdout)


if __name__ == "__main__":
    main()
