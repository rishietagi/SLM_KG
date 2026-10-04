"""Orphan check: every node must reach the CPGValueChain root (and hence a ValueChainActivity's stage)."""
from __future__ import annotations

from collections import defaultdict, deque

ROOT_CLASS = "CPGValueChain"


def find_orphans(node_classes: dict[str, str], edges: list[tuple[str, str]]) -> list[str]:
    """node_classes: id -> class; edges: (from_id, to_id). Undirected reachability from root nodes."""
    adj: dict[str, set[str]] = defaultdict(set)
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    roots = [n for n, c in node_classes.items() if c == ROOT_CLASS]
    seen = set(roots)
    queue = deque(roots)
    while queue:
        for nb in adj[queue.popleft()]:
            if nb not in seen:
                seen.add(nb)
                queue.append(nb)
    return sorted(n for n in node_classes if n not in seen)
