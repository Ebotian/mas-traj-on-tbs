"""Canonical form for a0.maxcut graph/partition artifacts.

Authority: a0/tasks/maxcut/INTERFACE.md section 2 (graph.json) and section 3
(partition.json).  The canonical byte string is

    json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    + a single trailing newline

and the *identity* of a graph is the sha256 of that byte string.
"""
import hashlib
import json
import os
from fractions import Fraction


def canonical_bytes(obj) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True) + "\n").encode("ascii")


def canonical_sha256(obj) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def file_sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_canonical(path, obj) -> str:
    data = canonical_bytes(obj)
    tmp = "%s.tmp.%d" % (path, os.getpid())
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, path)
    return hashlib.sha256(data).hexdigest()


def load_graph(path):
    with open(path, "rb") as fh:
        return json.loads(fh.read().decode("ascii"))


def validate_graph(g):
    """Return (ok, reason).  Mirrors INTERFACE.md section 2."""
    if g.get("schema") != "a0.maxcut.graph/v1":
        return False, "schema"
    n = g.get("n")
    if not isinstance(n, int) or n <= 0:
        return False, "n"
    edges = g.get("edges")
    if not isinstance(edges, list):
        return False, "edges"
    prev = None
    for e in edges:
        if not isinstance(e, list) or len(e) != 2:
            return False, "edge_shape"
        u, v = e
        if not isinstance(u, int) or not isinstance(v, int):
            return False, "edge_type"
        if not (0 <= u < n and 0 <= v < n):
            return False, "edge_range"
        if u >= v:
            return False, "edge_order_or_self_loop"
        if prev is not None and (u, v) <= prev:
            return False, "edge_not_strictly_sorted_or_duplicate"
        prev = (u, v)
    if "weight" in g or any("weight" in e for e in edges if isinstance(e, dict)):
        return False, "weight_present"
    return True, "ok"


def cut_edges_exact(graph, assignment):
    """Harness-owned recomputation.  INTEGER arithmetic only.

    Returns the number of edges whose endpoints fall in different parts.
    Raises ValueError when the assignment does not match section 3.
    """
    n = graph["n"]
    if not isinstance(assignment, list) or len(assignment) != n:
        raise ValueError("assignment length")
    for a in assignment:
        if a not in (0, 1) or isinstance(a, bool):
            raise ValueError("assignment element not in {0,1}")
    cut = 0
    for u, v in graph["edges"]:
        if assignment[u] != assignment[v]:
            cut += 1
    return cut


def cut_fraction_display(cut, edges_total, digits=19):
    """Display-only decimal, per INTERFACE.md section 5.  Never used in a verdict."""
    if cut is None:
        return None
    return format(Fraction(cut, edges_total), "." + str(digits) + "f")


def write_partition(path, graph_id, assignment):
    return write_canonical(path, {
        "schema": "a0.maxcut.partition/v1",
        "graph_id": graph_id,
        "assignment": [int(a) for a in assignment],
    })
