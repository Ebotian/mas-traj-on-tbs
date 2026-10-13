#!/usr/bin/env python3
"""Fetch DeepSeek's official pricing page and emit a VERIFIABLE rate card.

Verifiability contract:
  1. The raw page bytes are hashed (sha256) and the hash + byte count are stored.
  2. Every parsed number must appear verbatim in the raw HTML (checked).
  3. Internal consistency checks: off_peak == peak/2 for every pair; flash < pro.
  4. `--verify <card>` re-fetches, re-parses, and diffs against a stored card.
Usage:
  python3 fetch_rate_card.py                 # write rate-card-<date>.json here
  python3 fetch_rate_card.py --verify FILE   # re-fetch and compare
"""
import datetime as dt
import hashlib
import html as H
import json
import re
import sys
import urllib.request
import pathlib

URL = "https://api-docs.deepseek.com/quick_start/pricing"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
HERE = pathlib.Path(__file__).resolve().parent


def fetch() -> bytes:
    req = urllib.request.Request(URL, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read()


def flatten(page: bytes) -> str:
    t = page.decode("utf-8", errors="replace")
    t = re.sub(r"<script.*?</script>", " ", t, flags=re.S)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", H.unescape(t))


def parse(txt: str) -> dict:
    def grab(label: str) -> dict:
        m = re.search(
            label + r" OFF-PEAK \$([0-9.]+) \$([0-9.]+) PEAK \$([0-9.]+) \$([0-9.]+)", txt
        )
        assert m, f"rate row not found: {label}"
        off_f, off_p, pk_f, pk_p = map(float, m.groups())
        return {
            "flash": {"off_peak": off_f, "peak": pk_f},
            "v4_pro": {"off_peak": off_p, "peak": pk_p},
        }

    card = {
        "cache_hit_input_usd_per_m": grab(r"1M INPUT TOKENS \(CACHE HIT\)"),
        "cache_miss_input_usd_per_m": grab(r"1M INPUT TOKENS \(CACHE MISS\)"),
        "output_usd_per_m": grab(r"1M OUTPUT TOKENS"),
    }
    m = re.search(r"(Off-peak rates are half of the peak rates\..*?public holidays[^.]*\.)", txt)
    card["peak_rule_verbatim"] = m.group(1) if m else None
    for key, row in card.items():
        if isinstance(row, dict):
            for model, f in row.items():
                assert abs(f["peak"] / 2 - f["off_peak"]) < 1e-9, f"{key}/{model} not half: {f}"
            assert row["flash"]["peak"] < row["v4_pro"]["peak"], key
    assert card["peak_rule_verbatim"] and "01:00 - 04:00" in card["peak_rule_verbatim"] \
        and "06:00 - 10:00" in card["peak_rule_verbatim"] \
        and "Monday through Friday" in card["peak_rule_verbatim"], "peak rule incomplete"
    m = re.search(r"(Use deepseek-flash as the model name\..*?Flash price\.)", txt)
    card["official_name_note_verbatim"] = m.group(1) if m else None
    return card


def verify_numbers_in_raw(card: dict, raw: bytes) -> None:
    for key, row in card.items():
        if isinstance(row, dict):
            for model in row:
                for v in row[model].values():
                    s = ("%g" % v)
                    assert s.encode() in raw, f"value {s} not found verbatim in raw page: {key}/{model}"


def main() -> int:
    page = fetch()
    txt = flatten(page)
    card = parse(txt)
    verify_numbers_in_raw(card, page)
    card["source_url"] = URL
    card["fetched_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    card["page_sha256"] = hashlib.sha256(page).hexdigest()
    card["page_bytes"] = len(page)
    card["parser"] = "fetch_rate_card.py v1"

    if len(sys.argv) >= 3 and sys.argv[1] == "--verify":
        old = json.load(open(sys.argv[2]))
        drift = [k for k in ("cache_hit_input_usd_per_m", "cache_miss_input_usd_per_m", "output_usd_per_m", "peak_rule_verbatim")
                 if old.get(k) != card.get(k)]
        if drift:
            print("RATE DRIFT DETECTED:", drift)
            for k in drift:
                print(f"  {k}: stored={old.get(k)} live={card.get(k)}")
            return 1
        print(f"verify OK: rates identical to {sys.argv[2]} (page sha changed {old.get('page_sha256') != card.get('page_sha256')})")
        return 0

    out = HERE / f"rate-card-{card['fetched_at_utc'][:10]}.json"
    out.write_text(json.dumps(card, indent=2, ensure_ascii=False) + "\n")
    print(f"written: {out}")
    print(json.dumps(card, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
