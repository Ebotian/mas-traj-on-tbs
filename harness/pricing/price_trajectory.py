#!/usr/bin/env python3
"""Price a measured token stream with DeepSeek's time-of-use rate card.

Design (2026-10-10, per the user's efficiency note): an agent execution is a
CONTIGUOUS interval. If that interval contains no TOU boundary, ONE period
prices the whole interval -> O(1) per run ("fast path"). Endpoint-same-period
alone is NOT sufficient (00:30->10:30 both off-peak still encloses the
06:00-10:00 peak), so the fast path checks for boundaries strictly inside
(t0, t1). Fallback: per-step classification. Cross-check: when per-step data
exists, both paths MUST agree exactly; the report records the agreement.

Inputs:
  --card    rate card json (from fetch_rate_card.py)
  --traj    trajectory.json (per-step timestamp + metrics)
  or
  --start/--end ISO8601 (e.g. 2026-10-09T09:04:00Z) --in --cached --out
Model mapping: deepseek-flash / deepseek-v4-flash / deepseek-v4-flash-vision-exp -> flash;
deepseek-v4-pro -> v4_pro.

Scope note: Chinese-public-holiday exclusion is NOT modeled (no holiday table);
runs inside CN holidays are rare and would shift peak->off_peak. Reported anyway.
"""
import argparse
import datetime as dt
import json
import pathlib
import sys

BOUNDARY_HOURS = (1, 4, 6, 10)  # UTC segment edges: 01-04 peak, 04-06 off, 06-10 peak, 10-01 off
MODEL_ALIASES = {
    "deepseek-flash": "flash",
    "deepseek-v4-flash": "flash",
    "deepseek-v4-flash-vision-exp": "flash",
    "deepseek-v4-pro": "v4_pro",
}


def period_of(t: dt.datetime) -> str:
    if t.weekday() <= 4 and ((1 <= t.hour < 4) or (6 <= t.hour < 10)):
        return "peak"
    return "off_peak"


def boundaries_between(t0: dt.datetime, t1: dt.datetime) -> list:
    hits, d = [], t0.date() - dt.timedelta(days=1)
    while d <= t1.date() + dt.timedelta(days=1):
        for h in BOUNDARY_HOURS:
            b = dt.datetime(d.year, d.month, d.day, h, tzinfo=dt.timezone.utc)
            if t0 < b < t1:
                hits.append(b)
        d += dt.timedelta(days=1)
    return hits


def price(period: str, buckets: dict, card: dict, model: str) -> float:
    return (
        buckets["miss_in"] / 1e6 * card["cache_miss_input_usd_per_m"][model][period]
        + buckets["hit_in"] / 1e6 * card["cache_hit_input_usd_per_m"][model][period]
        + buckets["out"] / 1e6 * card["output_usd_per_m"][model][period]
    )


def parse_ts(s: str) -> dt.datetime:
    t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    return t.astimezone(dt.timezone.utc)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--card", required=True)
    ap.add_argument("--traj")
    ap.add_argument("--start"); ap.add_argument("--end")
    ap.add_argument("--in", dest="tin", type=int); ap.add_argument("--cached", type=int, default=0)
    ap.add_argument("--out", dest="tout", type=int)
    ap.add_argument("--model", default=None)
    ap.add_argument("--report", default=None, help="write JSON report to this path")
    a = ap.parse_args()
    card = json.load(open(a.card))

    steps, model_name = [], None
    if a.traj:
        d = json.load(open(a.traj))
        model_name = (d.get("agent") or {}).get("model_name")
        tot = d.get("final_metrics") or {}
        for s in d["steps"]:
            m = s.get("metrics") or {}
            if not m or not s.get("timestamp"):
                continue
            steps.append({
                "ts": parse_ts(s["timestamp"]),
                "prompt": int(m.get("prompt_tokens") or 0),
                "cached": int(m.get("cached_tokens") or 0),
                "out": int(m.get("completion_tokens") or 0),
            })
        assert steps, "no priced steps in trajectory"
        t0, t1 = steps[0]["ts"], steps[-1]["ts"]
        assert all(steps[i]["ts"] <= steps[i + 1]["ts"] for i in range(len(steps) - 1)), "timestamps not monotonic"
        agg = {
            "in": sum(s["prompt"] for s in steps),
            "cached": sum(s["cached"] for s in steps),
            "out": sum(s["out"] for s in steps),
        }
        # 与 final_metrics 对账(若存在)
        fm = {k: tot.get(k) for k in ("total_prompt_tokens", "total_cached_tokens", "total_completion_tokens")}
        if fm["total_prompt_tokens"]:
            print(f"对账: 逐步合计 in={agg['in']} vs final={fm['total_prompt_tokens']} | "
                  f"cached {agg['cached']} vs {fm['total_cached_tokens']} | out {agg['out']} vs {fm['total_completion_tokens']}")
    else:
        t0, t1 = parse_ts(a.start), parse_ts(a.end)
        agg = {"in": a.tin, "cached": a.cached, "out": a.tout}

    model = MODEL_ALIASES.get((a.model or model_name or "").strip(), None)
    assert model, f"unknown model name {a.model or model_name!r}; known: {list(MODEL_ALIASES)}"
    buckets_all = {"miss_in": agg["in"] - agg["cached"], "hit_in": agg["cached"], "out": agg["out"]}

    # 快路径:区间内无 TOU 边界 -> 整段一价
    bs = boundaries_between(t0, t1)
    fast_period = period_of(t0) if not bs else None
    fast_cost = price(fast_period, buckets_all, card, model) if fast_period else None

    # 回退/核验路径:逐步
    per_step_cost, per_step_periods = None, None
    if a.traj:
        per_step_cost = 0.0
        per_step_periods = {"peak": 0.0, "off_peak": 0.0}
        for s in steps:
            p = period_of(s["ts"])
            c = price(p, {"miss_in": s["prompt"] - s["cached"], "hit_in": s["cached"], "out": s["out"]}, card, model)
            per_step_cost += c
            per_step_periods[p] += c

    report = {
        "card_fetched_at_utc": card["fetched_at_utc"],
        "model": model,
        "interval_utc": [t0.isoformat(), t1.isoformat()],
        "duration_min": round((t1 - t0).total_seconds() / 60, 2),
        "buckets": buckets_all,
        "boundaries_inside": [b.isoformat() for b in bs],
        "fast_path": {"uniform": fast_period is not None, "period": fast_period, "cost_usd": fast_cost},
        "per_step": None if per_step_cost is None else {"cost_usd": round(per_step_cost, 6), "by_period": {k: round(v, 6) for k, v in per_step_periods.items()}},
        "cross_check": None if per_step_cost is None or fast_cost is None
                       else ("AGREE" if abs(per_step_cost - fast_cost) < 1e-9 else "DISAGREE"),
        "counterfactual_all_peak_usd": round(price("peak", buckets_all, card, model), 6),
        "counterfactual_all_off_peak_usd": round(price("off_peak", buckets_all, card, model), 6),
        "holiday_exclusion": "NOT modeled",
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if a.report:
        pathlib.Path(a.report).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.report).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        print(f"written: {a.report}")
    if report["cross_check"] == "DISAGREE":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
