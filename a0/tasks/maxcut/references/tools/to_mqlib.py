#!/usr/bin/env python3
"""Convert a canonical a0.maxcut graph.json into MQLib's Max-Cut input format.

MQLib's MaxCutInstance parser (include/problem/max_cut_instance.h) reads:

    n m
    a b w          (1-indexed endpoints, a < b, one line per edge)

with '#' comment lines allowed.  Weights here are all 1 (INTERFACE.md section 2
fixes weight 1 and forbids a weight field), so every edge is written with w=1.

Node k of graph.json (0-indexed) becomes node k+1 in the MQLib file.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canonical import load_graph  # noqa: E402


def write_mqlib_input(graph, path):
    lines = ["# converted from canonical a0.maxcut.graph/v1 (unit weights)",
             "%d %d" % (graph["n"], len(graph["edges"]))]
    for u, v in graph["edges"]:
        lines.append("%d %d 1" % (u + 1, v + 1))
    data = "\n".join(lines) + "\n"
    # several worker processes may convert the same graph at once; a
    # pid-unique temp name keeps the rename atomic and race-free
    tmp = "%s.tmp.%d" % (path, os.getpid())
    with open(tmp, "w") as fh:
        fh.write(data)
    os.replace(tmp, path)
    return data


def main():
    src, dst = sys.argv[1], sys.argv[2]
    g = load_graph(src)
    write_mqlib_input(g, dst)
    print("%s -> %s (%d nodes, %d edges)" % (src, dst, g["n"], len(g["edges"])))


if __name__ == "__main__":
    main()
