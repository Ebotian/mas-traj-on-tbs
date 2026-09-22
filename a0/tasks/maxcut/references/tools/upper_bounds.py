#!/usr/bin/env python3
"""Cheap *rigorous* upper bounds on max-cut, for the reference table.

A feasible cut is a lower bound on the optimum; it is never an upper bound.
This module supplies the other side, so that

  * saturation can be detected at all (INTERFACE.md / A1-CONTRACT-AUDIT.md B3),
  * "R_i is optimal" can be *certified* whenever U_i == R_i,
  * U_i is available as the denominator-side sanity check.

Two bounds, both valid for every y in R^n:

  (1) spectral / eigenvalue bound.
      For x in {+-1}^n:   cut(x) = m/2 - (1/4) x^T A x
      so   maxcut = m/2 + (1/4) max_x (-x^T A x) <= m/2 + (n/4) * (-lambda_min(A)).
      (isolated vertices are dropped first: they cannot change maxcut but they do
      inflate n, hence the bound.)

  (2) SDP (Goemans-Williamson) dual bound, Delorme-Poljak form.
      The GW relaxation is   max { m/2 - (1/4)<A,X> : diag(X)=1, X >= 0 }.
      Its LP dual is          max { -1^T y : A + Diag(y) >= 0 },
      hence       maxcut <= m/2 + (1/4) * min_y { 1^T y : A + Diag(y) >= 0 }.
      For ANY y, c := max(0, -lambda_min(A + Diag(y))) makes y + c*1 feasible, so
            phi(y) := 1^T y + n * max(0, -lambda_min(A + Diag(y)))
      is a valid (convex) bound function:  maxcut <= m/2 + phi(y)/4  for all y.
      y = 0 reproduces the spectral bound, so minimising phi over y can only
      improve it.  We minimise with a Polyak subgradient method using the known
      feasible cut as the lower bound on phi*:
            phi* >= 4*R_i - 2*m      (because the SDP value is >= maxcut >= R_i).

Rigour caveat, stated plainly: the argument is exact in real arithmetic.  The
certificate is a numeric eigen-decomposition, so a small safety margin is added
to c and to the final floor.  Validity is checked a posteriori against the
known feasible cut for every graph (U_i >= R_i); a violation is a bug and is
reported rather than hidden.
"""
import numpy as np

MARGIN = 1e-9


def adjacency(graph):
    n = graph["n"]
    A = np.zeros((n, n), dtype=np.float64)
    for u, v in graph["edges"]:
        A[u, v] = 1.0
        A[v, u] = 1.0
    return A


def _phi(A, y):
    """Return (phi, lambda_min, c) for the given diagonal vector y."""
    n = A.shape[0]
    M = A + np.diag(y)
    w = np.linalg.eigvalsh(M)
    lam = float(w[0])
    c = max(0.0, -lam) + MARGIN * (1.0 + abs(lam))
    return float(y.sum() + n * c), lam, c


def drop_isolated(A):
    """Restrict to vertices of positive degree (does not change maxcut)."""
    deg = A.sum(axis=1)
    keep = np.nonzero(deg > 0)[0]
    if len(keep) == len(deg):
        return A
    if len(keep) == 0:
        return np.zeros((0, 0))
    return A[np.ix_(keep, keep)]


def spectral_bound(A):
    m = A.sum() / 2.0
    if A.shape[0] == 0:
        return 0.0, 0.0
    phi, lam, _ = _phi(A, np.zeros(A.shape[0]))
    return m / 2.0 + phi / 4.0, lam


def sdp_dual_bound(A, m, feasible_lower, iters=4000, seed=20260922):
    """Minimise phi(y) by Polyak subgradient.  Every iterate is a valid bound."""
    n = A.shape[0]
    if n == 0:
        return 0.0, {"iters": 0, "best_phi": 0.0, "lambda_min_at_best": 0.0}
    if m <= 0:
        return 0.0, {"iters": 0, "best_phi": 0.0, "lambda_min_at_best": 0.0}
    rng = np.random.default_rng(seed)
    A = np.asarray(A, dtype=np.float64)
    # lower bound on phi* from the known feasible cut (an integer, exact)
    phi_lb = 4.0 * float(feasible_lower) - 2.0 * float(m)

    cands = []                      # every entry is a valid bound
    phi0, lam0, _ = _phi(A, np.zeros(n))
    cands.append((phi0, np.zeros(n), lam0))

    y = rng.normal(scale=1.0, size=n)
    best_phi, best_y, best_lam = float("inf"), None, 0.0
    for t in range(iters):
        w, V = np.linalg.eigh(A + np.diag(y))
        lam = float(w[0])
        c = max(0.0, -lam) + MARGIN * (1.0 + abs(lam))
        phi = float(y.sum() + n * c)
        if phi < best_phi:
            best_phi, best_y, best_lam = phi, y.copy(), lam
        if lam < 0:
            g = 1.0 - n * (V[:, 0] ** 2)
        else:
            g = np.ones(n)
        gap = phi - phi_lb
        nrm2 = float(g @ g)
        if gap <= 1e-9 or nrm2 == 0.0:
            break
        step = 0.5 * gap / nrm2
        y = y - step * g
        # keep the scaled diagonal from drifting into overflow
        if not np.all(np.isfinite(y)) or np.max(np.abs(y)) > 1e6:
            y = rng.normal(scale=1.0, size=n)
    cands.append((best_phi, best_y, best_lam))
    # also the iterate average, which is often better than the last point
    cands.append((_phi(A, y)[0], y, _phi(A, y)[1]))

    cands.sort(key=lambda trip: trip[0])
    phi_star, y_star, lam_star = cands[0]
    bound = m / 2.0 + phi_star / 4.0
    return bound, {
        "iters": iters,
        "best_phi": phi_star,
        "phi_lower_bound": phi_lb,
        "lambda_min_at_best": float(lam_star),
        "diagonal_shift": float(np.max(np.abs(y_star))) if y_star is not None else 0.0,
        "spectral_phi": phi0,
        "improved_over_spectral": bool(phi_star < phi0 - 1e-9),
    }


def bm_dual_bound(A, m, rank=8, iters=4000, seed=20260922, penalty_scale=1e3):
    """Burer-Monteiro on the GW primal, then read the dual certificate off it.

    Minimise g(V) = <A, V V^T> over V in R^{n x r} with unit-norm rows (the GW
    primal in factored form; its optimum is n/2 times... precisely:
    SDP = m/2 - g(V*)/4 at the optimum).  Uncoupled to unit balls by a penalty,
    solved with L-BFGS-B.

    Given ANY V, define X = V V^T and y_i = -(A X)_ii.  Then
        1^T y = -<A, X> = -g(V)
    and y + c*1 is dual feasible for c = max(0, -lambda_min(A + Diag(y))).
    So  m/2 + (1^T y + n*c)/4  is a valid upper bound for every V.  At an exact
    SDP optimum c = 0 and the bound equals the SDP value.
    """
    n = A.shape[0]
    if n == 0 or m <= 0:
        return float("inf"), {"rank": rank, "iters": 0}
    from scipy.optimize import minimize

    rng = np.random.default_rng(seed)
    pen = penalty_scale * max(m, 1.0)

    def unpack(x):
        return x.reshape(n, rank)

    def fg(x):
        V = unpack(x)
        AV = A @ V
        g = float(np.einsum("ij,ij->", V, AV))          # <A, V V^T>
        sq = np.einsum("ij,ij->i", V, V)
        viol = sq - 1.0
        f = g + pen * float(viol @ viol)
        grad = 2.0 * AV + (4.0 * pen * viol)[:, None] * V
        return f, grad.ravel()

    x0 = rng.normal(size=(n, rank))
    x0 /= np.linalg.norm(x0, axis=1, keepdims=True)
    res = minimize(fg, x0.ravel(), jac=True, method="L-BFGS-B",
                   options={"maxiter": iters, "maxfun": iters * 2,
                            "ftol": 1e-14, "gtol": 1e-10})
    V = unpack(res.x)
    V = V / np.maximum(np.linalg.norm(V, axis=1, keepdims=True), 1e-12)
    AX = A @ V @ V.T
    y = -np.diag(AX)
    phi, lam, c = _phi(A, y)
    bound = m / 2.0 + phi / 4.0
    return bound, {
        "rank": rank, "iters": int(res.nit), "penalty": pen,
        "objective": float(res.fun), "lambda_min_at_certificate": lam,
        "shift_c": c, "one_y": float(y.sum()),
        "row_norm_max_deviation": float(np.max(np.abs(np.linalg.norm(V, axis=1) - 1.0))),
    }


def upper_bounds(graph, feasible_lower, iters=4000, bm_rank=8, bm_iters=3000):
    """Return a dict of rigorous upper bounds (floats) plus the driving data."""
    A_full = adjacency(graph)
    A = drop_isolated(A_full)
    m = float(len(graph["edges"]))
    spec, lam0 = spectral_bound(A)
    sdp, info = sdp_dual_bound(A, m, feasible_lower, iters=iters)
    bm, bm_info = bm_dual_bound(A, m, rank=bm_rank, iters=bm_iters)
    out = {
        "edges_total": int(m),
        "n_effective": int(A.shape[0]),
        "lambda_min": lam0,
        "U_spectral": spec,
        "U_sdp_dual": sdp,
        "U_bm_certificate": bm,
        "U_min": min(spec, sdp, bm),
        "sdp_info": info,
        "bm_info": bm_info,
    }
    return out
