#!/usr/bin/env python3
"""Build and freeze `C*(T1)`: the fixed candidate set for the max-cut evaluator.

Every candidate here exists to exercise one row of `INTERFACE.md` §6 (the frozen
decision rules) or one of the five first-principles constraints.  The bytes are
the candidate: `manifest.json` freezes the sha256 of every file in every
candidate directory, and `--check` re-verifies them, so a measurement taken
against this set stays meaningful.

    python3 build_candidates.py --write    # (re)write the tree and the manifest
    python3 build_candidates.py --check     # verify frozen bytes, change nothing

The sources live here as literals rather than as loose files so that "the
candidate" is a reproducible artifact of one command, exactly as the plumbing
workstream's `C_STAR` is.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANDIDATES_DIR = HERE / "candidates"


def canonical_bytes(payload: object) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")


# --------------------------------------------------------------------------- #
# sources
# --------------------------------------------------------------------------- #

PRELUDE = '''"""{doc}"""

import argparse
import json
import sys


def parse_args():
    parser = argparse.ArgumentParser(description={doc!r})
    parser.add_argument("--graph", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, required=True)
    return parser.parse_args()


def load_graph(path):
    with open(path, "r", encoding="utf-8") as handle:
        document = json.load(handle)
    return document["graph_id"], int(document["n"]), [tuple(edge) for edge in document["edges"]]


def emit_partition(path, graph_id, assignment):
    payload = {{"schema": "a0.maxcut.partition/v1", "graph_id": graph_id, "assignment": assignment}}
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\\n"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
'''

SEARCH_HELPERS = '''

MASK64 = (1 << 64) - 1


class Rng:
    """splitmix64: the same bits on every interpreter, so `--seed` alone decides
    the stream (unlike `random`, whose algorithm is a CPython implementation
    detail this candidate must not depend on)."""

    def __init__(self, seed):
        self.state = (int(seed) ^ 0x9E3779B97F4A7C15) & MASK64

    def next_u64(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK64
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK64
        return z ^ (z >> 31)

    def bit(self):
        return self.next_u64() & 1


def adjacency(n, edges):
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    return adj


def cut_size(edges, assignment):
    """The candidate's own search signal.  It is never written to the artifact:
    the harness recomputes the cut from the graph and the partition."""
    return sum(1 for u, v in edges if assignment[u] != assignment[v])


def local_optimum(n, adj, assignment):
    """Steepest-ascent 1-flip descent to a local optimum, in a fixed vertex
    order so the result is a function of the input assignment alone.

    `gain[v]` is the exact change in cut size that flipping v would produce:
    same-side neighbours become cut and cut neighbours stop being cut, so
    `gain[v] = 2*same - degree`.  Positive gain therefore means "flipping
    improves", which is the direction this descent moves.
    """
    gain = [0] * n
    for v in range(n):
        same = sum(1 for w in adj[v] if assignment[w] == assignment[v])
        gain[v] = 2 * same - len(adj[v])
    moved = True
    while moved:
        moved = False
        for v in range(n):
            if gain[v] > 0:
                assignment[v] ^= 1
                moved = True
                gain[v] = -gain[v]
                for w in adj[v]:
                    gain[w] += 2 if assignment[w] == assignment[v] else -2
    return assignment


def best_of_restarts(n, edges, seed, starts, greedy=False):
    adj = adjacency(n, edges)
    rng = Rng(seed)
    best, best_cut = None, -1
    for start in range(starts):
        if greedy and start == 0:
            assignment = [0] * n
        else:
            assignment = [rng.bit() for _ in range(n)]
        local_optimum(n, adj, assignment)
        value = cut_size(edges, assignment)
        if value > best_cut:
            best_cut, best = value, list(assignment)
    return best
'''


def source(doc: str, body: str, *, helpers: str = "") -> str:
    return PRELUDE.format(doc=doc) + helpers + "\n\n" + body


CANDIDATES: list[dict[str, object]] = [
    {
        "dir": "c01_ok_high_pc",
        "kind": "ok",
        "role": "high",
        "purpose": "The high end of §10's 'ok but high score' row: a multi-start local search. "
                   "Its numbers are the reference for the tie pair and for the ordered pair with c02.",
        "expected": {"status": "ok", "failure_kind": None, "rows": ["ok-high"]},
        "source": source(
            "Deterministic multi-start local search for unweighted max-cut (the 'PC' candidate).",
            '''
def main():
    args = parse_args()
    graph_id, n, edges = load_graph(args.graph)
    assignment = best_of_restarts(n, edges, args.seed, starts=8, greedy=True)
    emit_partition(args.out, graph_id, assignment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
            helpers=SEARCH_HELPERS,
        ),
    },
    {
        "dir": "c02_ok_low_baseline",
        "kind": "ok",
        "role": "low",
        "purpose": "§10's 'ok but low score' row: a seeded uniform-random bisection, i.e. the c_0 "
                   "baseline a search must beat. Deterministic given --seed, so it is a legitimate ok.",
        "expected": {"status": "ok", "failure_kind": None, "rows": ["ok-low"]},
        "source": source(
            "Seeded uniform-random bisection: the low-scoring but honest baseline.",
            '''
def main():
    args = parse_args()
    graph_id, n, edges = load_graph(args.graph)
    rng = Rng(args.seed ^ 0xA5A5A5A5A5A5A5A5)
    assignment = [rng.bit() for _ in range(n)]
    emit_partition(args.out, graph_id, assignment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
            helpers=SEARCH_HELPERS,
        ),
    },
    {
        "dir": "c03_ok_zero_all_one_side",
        "kind": "ok",
        "role": "edge",
        "purpose": "A legitimate ok whose objective is exactly 0. It is the control that separates "
                   "'measured zero' from 'not measured': the harness must report cut_edges 0 here and "
                   "null for every invalid/error/timeout candidate.",
        "expected": {"status": "ok", "failure_kind": None, "cut_edges_rule": "exactly 0", "rows": ["ok-zero"]},
        "source": source(
            "All vertices on one side: a legal partition whose cut is genuinely zero.",
            '''
def main():
    args = parse_args()
    graph_id, n, _edges = load_graph(args.graph)
    emit_partition(args.out, graph_id, [0] * n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
        ),
    },
    {
        "dir": "c04_tie_a_pc_optimum",
        "kind": "ok",
        "role": "tie-a",
        "purpose": "§10's byte-different numerical tie pair, first member: the local optimum itself.",
        "expected": {"status": "ok", "failure_kind": None, "rows": ["tie-pair"]},
        "source": source(
            "Tie pair A: the local-search optimum, unmodified.",
            '''
def main():
    args = parse_args()
    graph_id, n, edges = load_graph(args.graph)
    assignment = best_of_restarts(n, edges, args.seed, starts=8, greedy=True)
    emit_partition(args.out, graph_id, assignment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
            helpers=SEARCH_HELPERS,
        ),
    },
    {
        "dir": "c05_tie_b_pc_complement",
        "kind": "ok",
        "role": "tie-b",
        "purpose": "Tie pair B: the exact complement of A. Flipping every vertex leaves every edge "
                   "crossing exactly as before, so cut_edges is identical while partition.json bytes "
                   "differ -- the pair that catches a runtime keying a cache by bytes or by path.",
        "expected": {"status": "ok", "failure_kind": None, "cut_edges_rule": "equal to c04", "rows": ["tie-pair"]},
        "source": source(
            "Tie pair B: the exact complement of the local-search optimum.",
            '''
def main():
    args = parse_args()
    graph_id, n, edges = load_graph(args.graph)
    assignment = best_of_restarts(n, edges, args.seed, starts=8, greedy=True)
    emit_partition(args.out, graph_id, [1 - value for value in assignment])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
            helpers=SEARCH_HELPERS,
        ),
    },
    {
        "dir": "c06_invalid_length",
        "kind": "invalid",
        "role": "malformed",
        "purpose": "§10's 'invalid (wrong length)' row: assignment has one element too many. "
                   "§6 rule 2 -> invalid, and cut_edges must be null rather than a number.",
        "expected": {"status": "invalid", "failure_kind": "malformed_partition", "rows": ["invalid-length"]},
        "source": source(
            "Wrong assignment length: exits 0 and writes a well-formed but wrong-sized partition.",
            '''
def main():
    args = parse_args()
    graph_id, n, _edges = load_graph(args.graph)
    emit_partition(args.out, graph_id, [0] * (n + 1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
        ),
    },
    {
        "dir": "c07_invalid_element",
        "kind": "invalid",
        "role": "malformed",
        "purpose": "§10's 'invalid (element not 0/1)' row: the first element is 2.",
        "expected": {"status": "invalid", "failure_kind": "malformed_partition", "rows": ["invalid-element"]},
        "source": source(
            "Element outside {0, 1}: the first assignment entry is 2.",
            '''
def main():
    args = parse_args()
    graph_id, n, _edges = load_graph(args.graph)
    assignment = [0] * n
    if n:
        assignment[0] = 2
    emit_partition(args.out, graph_id, assignment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
        ),
    },
    {
        "dir": "c08_invalid_json",
        "kind": "invalid",
        "role": "malformed",
        "purpose": "§10's 'invalid (corrupt JSON)' row: the artifact is truncated mid-object, so it is "
                   "a format violation (§6 rule 2), not an execution failure.",
        "expected": {"status": "invalid", "failure_kind": "malformed_partition", "rows": ["invalid-json"]},
        "source": source(
            "Corrupt JSON: a truncated object is written to the artifact path.",
            '''
def main():
    args = parse_args()
    graph_id, _n, _edges = load_graph(args.graph)
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write('{"schema":"a0.maxcut.partition/v1","graph_id":"' + graph_id + '","assignment":[0,1,0')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
        ),
    },
    {
        "dir": "c09_invalid_missing_file",
        "kind": "invalid",
        "role": "malformed",
        "purpose": "§10's 'error (writes no file)' row, resolved the way the frozen rule reads: the "
                   "candidate exits 0 claiming success and writes nothing, and §6 rule 2 makes an "
                   "absent partition.json invalid -- see DEVIATIONS.md D-T1-2. c14 covers the "
                   "non-zero-exit variant of the same behaviour, which is an error.",
        "expected": {"status": "invalid", "failure_kind": "missing_partition", "rows": ["no-file-exit-0"]},
        "source": source(
            "Exits 0 without writing partition.json: the artifact is absent.",
            '''
def main():
    args = parse_args()
    load_graph(args.graph)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
        ),
    },
    {
        "dir": "c10_invalid_json_true",
        "kind": "invalid",
        "role": "malformed",
        "purpose": "JSON `true` where §3 requires the integer 0 or 1. Extra coverage of the 'element "
                   "not 0/1' row: in Python `bool` subclasses `int`, so a harness that tests only "
                   "`value in (0, 1)` accepts it. This is the probe that catches that.",
        "expected": {"status": "invalid", "failure_kind": "malformed_partition", "rows": ["invalid-element"]},
        "source": source(
            "Boolean elements: `true` is not the integer 1 under §3.",
            '''
def main():
    args = parse_args()
    graph_id, n, _edges = load_graph(args.graph)
    assignment = [0] * n
    if n:
        assignment[0] = True
    emit_partition(args.out, graph_id, assignment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
        ),
    },
    {
        "dir": "c11_error_raises",
        "kind": "error",
        "role": "crash",
        "purpose": "§10's 'error (raises)' row: an uncaught exception terminates the interpreter with "
                   "a non-zero code that is none of §4's named codes, so it is `error` with the raw "
                   "code preserved.",
        "expected": {"status": "error", "failure_kind": "candidate_crashed", "rows": ["error-raises"]},
        "source": source(
            "Raises an uncaught exception: the process dies with a foreign exit code.",
            '''
def main():
    args = parse_args()
    graph_id, n, edges = load_graph(args.graph)
    raise RuntimeError("c11_error_raises: deliberate crash after reading " + str((graph_id, n, len(edges))))


if __name__ == "__main__":
    raise SystemExit(main())
''',
        ),
    },
    {
        "dir": "c12_error_exit30",
        "kind": "error",
        "role": "internal-error",
        "purpose": "§4's named code 30 ('candidate internal error'). It pins the exit table: 30 is an "
                   "error, not an invalid, and it is distinguished from the uncaught-exception path "
                   "by its label even though both end as `error`.",
        "expected": {"status": "error", "failure_kind": "candidate_call_raised", "rows": ["error-exit-30"]},
        "source": source(
            "Exits 30: §4's 'candidate internal error' code.",
            '''
def main():
    args = parse_args()
    load_graph(args.graph)
    return 30


if __name__ == "__main__":
    raise SystemExit(main())
''',
        ),
    },
    {
        "dir": "c13_error_non_deterministic",
        "kind": "error",
        "role": "non-deterministic",
        "purpose": "§10's 'error (non-determinism: unseeded randomness)' row, i.e. §6 rule 4. The "
                   "partition is well formed and even decent, so the ONLY thing wrong with it is "
                   "that two runs with identical (candidate bytes, graph bytes, seed) disagree.",
        "expected": {"status": "error", "failure_kind": "non_deterministic", "rows": ["non-deterministic"]},
        "source": source(
            "Ignores --seed and uses process-random bits: two runs must disagree.",
            '''
import random


def main():
    args = parse_args()
    graph_id, n, edges = load_graph(args.graph)
    # Deliberately unseeded: `random` is seeded from os.urandom at import, so the
    # two invocations of §6 rule 4 differ with probability 1 - 2**-n.
    assignment = [random.getrandbits(1) for _ in range(n)]
    emit_partition(args.out, graph_id, assignment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
        ),
    },
    {
        "dir": "c14_error_no_file_nonzero",
        "kind": "error",
        "role": "missing-artifact",
        "purpose": "§10's 'error (writes no file)' row in the shape that is unambiguously an error: "
                   "the candidate exits non-zero (1) and writes nothing, so §4's 'other non-zero -> "
                   "error (raw code preserved)' applies before §6 rule 2 is ever reached.",
        "expected": {"status": "error", "failure_kind": "candidate_crashed", "rows": ["no-file-nonzero"]},
        "source": source(
            "Exits 1 without writing the artifact: no measurement can exist.",
            '''
def main():
    args = parse_args()
    load_graph(args.graph)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
''',
        ),
    },
    {
        "dir": "c15_error_network_attempt",
        "kind": "error",
        "role": "network",
        "purpose": "§10's 'error (attempts to reach the network)' row. Under the closed topology the "
                   "connection cannot be made, so the candidate refuses (exit 40, §4) and the graph "
                   "is recorded as error. In an open topology this same candidate would succeed, "
                   "which is exactly why the closed topology is a precondition of the measurement "
                   "and not a convenience.",
        "expected": {"status": "error", "failure_kind": "candidate_refused", "rows": ["network-attempt"],
                     "topology_dependent": True},
        "source": source(
            "Attempts a real outbound connection and refuses to run without it.",
            '''
import socket


def main():
    args = parse_args()
    graph_id, n, _edges = load_graph(args.graph)
    try:
        connection = socket.create_connection(("api.deepseek.com", 443), timeout=3.0)
        connection.close()
    except OSError as exc:
        # §4: 40 is "the candidate refuses", e.g. refusing to run with no network.
        sys.stderr.write("c15_error_network_attempt: no network: %s\\n" % (exc,))
        return 40
    emit_partition(args.out, graph_id, [index % 2 for index in range(n)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
        ),
    },
    {
        "dir": "c16_error_refused",
        "kind": "error",
        "role": "refused",
        "purpose": "§4's named code 40 taken unconditionally, so the refusal label is covered even "
                   "when the topology happens to be open and c15 would succeed.",
        "expected": {"status": "error", "failure_kind": "candidate_refused", "rows": ["error-exit-40"]},
        "source": source(
            "Exits 40 unconditionally: the candidate refuses to run.",
            '''
def main():
    args = parse_args()
    load_graph(args.graph)
    sys.stderr.write("c16_error_refused: refusing to run\\n")
    return 40


if __name__ == "__main__":
    raise SystemExit(main())
''',
        ),
    },
    {
        "dir": "c17_error_input_tampered",
        "kind": "error",
        "role": "tamper",
        "purpose": "Constraint (ii)/(iv) probe: rewrites graph.json so that a harness which re-read the "
                   "input after the run would compute an inflated cut, then writes the partition that "
                   "is optimal for the doctored graph. The harness must (a) recompute from its own "
                   "frozen copy and (b) report the change rather than ignore it. Run against a private "
                   "copy of the graph, since the candidate deliberately corrupts its input.",
        "expected": {"status": "error", "failure_kind": "input_tampered", "rows": ["input-tampered"],
                     "needs_private_graph_copy": True},
        "source": source(
            "Rewrites the input graph to inflate the cut, then leaves it rewritten.",
            '''
def main():
    args = parse_args()
    graph_id, n, edges = load_graph(args.graph)
    with open(args.graph, "r", encoding="utf-8") as handle:
        raw = handle.read()
    doctored = json.loads(raw)
    # A second copy of every edge whose endpoints this partition separates: a
    # harness that trusts the file it re-reads would see the cut nearly double.
    assignment = [index % 2 for index in range(n)]
    planted = [list(edge) for edge in doctored["edges"] if assignment[edge[0]] != assignment[edge[1]]]
    doctored["edges"] = sorted([list(edge) for edge in doctored["edges"]] + planted)
    with open(args.graph, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(doctored))
    emit_partition(args.out, graph_id, assignment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
        ),
    },
    {
        "dir": "c18_ok_inflation_attempt",
        "kind": "ok",
        "role": "tamper-restored",
        "purpose": "The complement of c17, and the direct proof of constraint (ii): the candidate "
                   "inflates graph.json, writes the partition that is optimal for the inflated graph, "
                   "then restores the original bytes. The input is byte-identical at the end, so "
                   "nothing is reported -- and the measured cut is the TRUE one, because the harness "
                   "recomputes from its own frozen copy. A candidate cannot buy a score by writing "
                   "to its input.",
        "expected": {"status": "ok", "failure_kind": None, "rows": ["inflation-attempt"]},
        "source": source(
            "Transiently rewrites the graph to inflate its own cut, then restores it byte-for-byte.",
            '''
def main():
    args = parse_args()
    graph_id, n, edges = load_graph(args.graph)
    with open(args.graph, "rb") as handle:
        original = handle.read()
    assignment = [index % 2 for index in range(n)]
    doctored = json.loads(original.decode("utf-8"))
    planted = [list(edge) for edge in doctored["edges"] if assignment[edge[0]] != assignment[edge[1]]]
    doctored["edges"] = sorted([list(edge) for edge in doctored["edges"]] + planted)
    with open(args.graph, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(doctored))
    emit_partition(args.out, graph_id, assignment)
    with open(args.graph, "wb") as handle:
        handle.write(original)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
        ),
    },
    {
        "dir": "c19_timeout_process_group",
        "kind": "timeout",
        "role": "timeout",
        "purpose": "§7's timeout row. The candidate ignores SIGTERM and forks a grandchild that beats a "
                   "heartbeat file forever. If the harness SIGKILLed only the direct child, the "
                   "grandchild would survive and the heartbeat would keep growing after tau; because "
                   "§7 kills the process GROUP, the heartbeat stops dead at tau. That is the "
                   "difference between a budget and a suggestion.",
        "expected": {"status": "timeout", "failure_kind": "runtime_budget_exceeded", "rows": ["timeout"],
                     "heartbeat": True},
        "source": source(
            "Ignores SIGTERM, forks a heartbeat grandchild, sleeps forever: only a group SIGKILL stops it.",
            '''
import os
import signal
import time


def main():
    args = parse_args()
    load_graph(args.graph)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    heartbeat = args.out + ".orphan_heartbeat"
    try:
        pid = os.fork()
    except OSError:
        pid = 0
    if pid == 0:
        # The grandchild.  It knows nothing about tau, so it does not try to
        # outlive a deadline; it just proves liveness by counting.  If the
        # harness killed only the direct child, this count keeps rising after
        # the verdict was taken, and the parent's probe sees it move.
        while True:
            with open(heartbeat, "a", encoding="utf-8") as handle:
                handle.write("beat\\n")
                handle.flush()
                os.fsync(handle.fileno())
            time.sleep(0.25)
        os._exit(0)
    while True:
        time.sleep(1.0)


if __name__ == "__main__":
    raise SystemExit(main())
''',
        ),
    },
    {
        "dir": "c21_ok_parity_probe",
        "kind": "ok",
        "role": "arithmetic-probe",
        "purpose": "A trivial deterministic candidate whose achieved cut is a construction parameter of "
                   "the graphs under graphs_tmp/float_tie_{A,B}/: the graphs are built with the exact "
                   "number of cross-parity edges needed to make both sets' exact score equal to 10/21 "
                   "while their naive float means differ. It is the end-to-end half of the "
                   "exact-aggregation proof (#6) -- real graphs, real candidate, real aggregate.",
        "expected": {"status": "ok", "failure_kind": None, "rows": ["exact-aggregation"]},
        "source": source(
            "Assigns every vertex by its index parity: deterministic and trivially checkable.",
            '''
def main():
    args = parse_args()
    graph_id, n, _edges = load_graph(args.graph)
    emit_partition(args.out, graph_id, [index % 2 for index in range(n)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
        ),
    },
    {
        "dir": "c20_env_probe",
        "kind": "ok",
        "role": "probe",
        "purpose": "Proof #5 of the T1 brief: dumps exactly what the child environment contains to a "
                   "file next to --out, then behaves normally. The dump is the evidence that §4's "
                   "environment carries no proxy variable and no credential, read from inside the "
                   "child rather than asserted by the harness.",
        "expected": {"status": "ok", "failure_kind": None, "rows": ["env-probe"]},
        "source": source(
            "Writes its own environment next to the artifact, then produces a valid partition.",
            '''
import os


def main():
    args = parse_args()
    graph_id, n, _edges = load_graph(args.graph)
    dump = args.out + ".env_probe.json"
    with open(dump, "w", encoding="utf-8") as handle:
        handle.write(json.dumps({
            "environ": dict(os.environ),
            "cwd": os.getcwd(),
            "argv": list(sys.argv),
            "executable": sys.executable,
        }, sort_keys=True, indent=2) + "\\n")
    emit_partition(args.out, graph_id, [index % 2 for index in range(n)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
        ),
    },
]


# --------------------------------------------------------------------------- #
# build / check
# --------------------------------------------------------------------------- #

def file_digests(directory: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(directory)
        if any(part == "__pycache__" or part.startswith(".") for part in relative.parts):
            continue
        data = path.read_bytes()
        entries.append({
            "path": relative.as_posix(),
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    return entries


def candidate_source_sha256(entries: list[dict[str, object]]) -> str:
    return hashlib.sha256(canonical_bytes(entries)).hexdigest()


def file_digests_from_payloads(payloads: dict[str, bytes]) -> list[dict[str, object]]:
    """The same digest list `e_star_child.candidate_files` produces for a
    candidate directory: path, byte count, sha256, sorted by path."""
    return [
        {"path": name.split("/", 1)[1], "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        for name, data in sorted(payloads.items())
    ]


def wanted_files() -> dict[str, bytes]:
    """Every byte this builder owns, keyed by path relative to C*(T1)'s root."""
    files: dict[str, bytes] = {}
    manifest_entries = []
    for entry in CANDIDATES:
        directory = str(entry["dir"])
        files[f"{directory}/solution.py"] = str(entry["source"]).encode("utf-8")
        metadata = {
            "schema": "a0.maxcut.candidate/v1",
            "candidate_id": directory,
            "kind": entry["kind"],
            "role": entry["role"],
            "purpose": entry["purpose"],
            "expected": entry["expected"],
            "version": "1.0.0",
        }
        files[f"{directory}/candidate.json"] = canonical_bytes(metadata)
        entries = file_digests_from_payloads({
            f"{directory}/candidate.json": files[f"{directory}/candidate.json"],
            f"{directory}/solution.py": files[f"{directory}/solution.py"],
        })
        manifest_entries.append({
            "candidate_id": directory,
            "dir": directory,
            "source_sha256": candidate_source_sha256(entries),
            "files": entries,
            "kind": entry["kind"],
            "role": entry["role"],
            "purpose": entry["purpose"],
            "expected": entry["expected"],
            "version": "1.0.0",
        })
    manifest = {
        "schema": "a0.candidateset/v1",
        "candidate_set_id": "C*(T1)",
        "candidate_count": len(CANDIDATES),
        "task": "a0/tasks/maxcut",
        "candidates": manifest_entries,
    }
    files["manifest.json"] = canonical_bytes(manifest)
    return files


def cmd_write() -> int:
    files = wanted_files()
    for relative, payload in sorted(files.items()):
        path = CANDIDATES_DIR / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    print(f"wrote {len(CANDIDATES)} candidates and manifest.json under {CANDIDATES_DIR}")
    return 0


def cmd_check() -> int:
    files = wanted_files()
    problems: list[str] = []
    for relative, payload in sorted(files.items()):
        path = CANDIDATES_DIR / relative
        if not path.is_file():
            problems.append(f"missing: {relative}")
        elif path.read_bytes() != payload:
            problems.append(f"bytes differ: {relative}")
    for path in sorted(CANDIDATES_DIR.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(CANDIDATES_DIR).as_posix()
        if any(part == "__pycache__" for part in Path(relative).parts):
            continue
        if relative not in files:
            problems.append(f"unexpected file in the frozen set: {relative}")
    if problems:
        for problem in problems:
            print(f"build_candidates: {problem}", file=sys.stderr)
        return 1
    print(f"build_candidates: {len(CANDIDATES)} candidates verified byte-for-byte against their frozen sources")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="build/verify C*(T1)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    return cmd_write() if args.write else cmd_check()


if __name__ == "__main__":
    raise SystemExit(main())
