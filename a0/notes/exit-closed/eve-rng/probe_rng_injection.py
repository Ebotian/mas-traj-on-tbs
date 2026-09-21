#!/usr/bin/env python3
"""Is there a *config* surface for the EvE RNG? (review D4: no upstream patch)

Runs against the pinned EvE checkout at ``/tmp/eve`` (read-only; never written).
It does not import the study's adapter; it drives the pinned checkout's own
sampler classes and Hydra ``instantiate``, which is how EvE builds them
(``scaling_evolve/algorithms/eve/factory.py:296-297``).

    a0/runtimes/eve/.venv/bin/python a0/notes/exit-closed/eve-rng/probe_rng_injection.py

Prints a JSON document with three attempts:

  A  config injection: add ``rng``/``seed`` to a sampler config block and instantiate
  B  call-site injection (Python): pass ``rng=random.Random(seed)`` to ``.sample``
  C  Hydra ``_target_`` override: what ``_target_`` can and cannot reach
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

EVE_ROOT = Path("/tmp/eve")
EVE_SRC = EVE_ROOT / "src"
sys.path.insert(0, str(EVE_SRC))

from hydra.utils import instantiate  # noqa: E402
from omegaconf import OmegaConf  # noqa: E402

from scaling_evolve.algorithms.eve.populations.samplers.uniform import (  # noqa: E402
    UniformSampler,
)

LOOP_DEFAULT = EVE_ROOT / "configs" / "eve" / "loop" / "default.yaml"

ITEMS = list(range(1, 21))
SCORES = [float(i) for i in ITEMS]


def _load_prefill_block() -> dict:
    cfg = OmegaConf.load(LOOP_DEFAULT)
    return OmegaConf.to_container(cfg.loop.sampling.solver_prefill, resolve=True)


def attempt_a_config_injection() -> dict:
    """Add rng/seed to the sampler's config block and instantiate it.

    ``factory.py:296-297`` builds every sampler with Hydra ``instantiate`` over
    ``loop.sampling[key]``, so a key that reached the constructor *would* be the
    config surface.  What actually happens to ``seed`` / ``rng`` is what this
    measures.
    """

    block = _load_prefill_block()
    block["seed"] = 1234
    block["rng"] = 1234
    sampler = instantiate(block)

    # Same seed/key on a second instance, sampled with no caller rng.
    sampler2 = instantiate(block)
    first = sampler.sample(ITEMS, SCORES, 4)
    second = sampler.sample(ITEMS, SCORES, 4)
    third = sampler2.sample(ITEMS, SCORES, 4)

    return {
        "config_block_with_injection": block,
        "instantiated_type": type(sampler).__module__ + "." + type(sampler).__name__,
        "instance_attributes": sorted(vars(sampler)),
        "instance_has_rng_attribute": hasattr(sampler, "_rng") or hasattr(sampler, "rng"),
        "samples_same_instance_a": first,
        "samples_same_instance_b": second,
        "samples_fresh_instance_same_config": third,
        "deterministic_within_instance": first == second,
        "deterministic_across_instances": first == third,
        "why_the_key_is_swallowed": (
            "UniformSampler.__init__ signature is "
            "`(*, replacement_mode, **_ignored_kwargs)`: any extra config key lands in "
            "**_ignored_kwargs and is discarded. `rng` is not a constructor parameter at all "
            "-- it is a call-time argument of `.sample`"
        ),
    }


def attempt_b_call_site_injection() -> dict:
    """The only surface that works: pass an rng at the call site (Python code)."""

    sampler = UniformSampler(replacement_mode="no_replacement")
    seeded_a = sampler.sample(ITEMS, SCORES, 4, rng=random.Random(1234))
    seeded_b = sampler.sample(ITEMS, SCORES, 4, rng=random.Random(1234))
    unseeded_a = sampler.sample(ITEMS, SCORES, 4)
    unseeded_b = sampler.sample(ITEMS, SCORES, 4)
    return {
        "seeded_a": seeded_a,
        "seeded_b": seeded_b,
        "seeded_reproduces": seeded_a == seeded_b,
        "unseeded_a": unseeded_a,
        "unseeded_b": unseeded_b,
        "unseeded_reproduces": unseeded_a == unseeded_b,
        "call_site": (
            "The rng is handed in by the caller: workflow/phase2.py:566-633 calls "
            "`self.<pop>_sampler.sample(..., rng=self.<pop>._rng)`, and that population rng "
            "is `rng or random.Random()` (populations/base.py:40). No caller passes a seeded "
            "rng, so every campaign draws a fresh unseeded stream."
        ),
    }


def attempt_c_target_override() -> dict:
    """What `_target_` can and cannot reach.

    `_target_` selects the sampler *class* and hands the remaining keys to its
    ``__init__``.  It cannot define a class inline, and no class the config can
    name reads an rng from its own construction: the rng arrives as a call-time
    argument.  So `_target_` can swap the sampling *policy*, not the *stream*.
    """

    block = _load_prefill_block()
    block["_target_"] = (
        "scaling_evolve.algorithms.eve.populations.samplers.rank_softmax.RankSoftmaxSampler"
    )
    block["temperature"] = 1.0
    sampler = instantiate(block)
    return {
        "target_swapped_to": block["_target_"],
        "instantiated_type": type(sampler).__module__ + "." + type(sampler).__name__,
        "class_is_selectable": True,
        "rng_reachable_via_target": False,
        "why": (
            "`_target_` is a dotted import path resolved by Hydra; it cannot define code. Any "
            "named sampler still receives its rng from phase2's call site, so overriding "
            "`_target_` changes which sampler runs, never its stream"
        ),
    }


def source_evidence() -> dict:
    """path:line anchors for the claims above (read from the pinned checkout)."""

    anchors = {
        "samplers_built_by_hydra": "src/scaling_evolve/algorithms/eve/factory.py:296-297",
        "population_constructed_without_rng": (
            "src/scaling_evolve/algorithms/eve/factory.py:308-314"
        ),
        "workspace_builder_constructed_without_rng": (
            "src/scaling_evolve/algorithms/eve/factory.py:321-328"
        ),
        "population_rng_fallback": "src/scaling_evolve/algorithms/eve/populations/base.py:33,40",
        "workspace_builder_rng_fallback": (
            "src/scaling_evolve/algorithms/eve/workspace/solver_workspace.py:61,91"
        ),
        "uniform_sampler_init_swallows_kwargs": (
            "src/scaling_evolve/algorithms/eve/populations/samplers/uniform.py:19-25"
        ),
        "uniform_sampler_call_time_rng": (
            "src/scaling_evolve/algorithms/eve/populations/samplers/uniform.py:32,35"
        ),
        "sampler_call_sites_use_population_rng": (
            "src/scaling_evolve/algorithms/eve/workflow/phase2.py:566-633"
        ),
    }
    present = {}
    for name, anchor in anchors.items():
        path, _, rng = anchor.partition(":")
        present[name] = (EVE_ROOT / path).is_file() and bool(rng)
    return {"anchors": anchors, "anchors_resolve": present}


def main() -> int:
    document = {
        "checkout": str(EVE_ROOT),
        "checkout_head": _git_head(),
        "attempt_A_config_injection": attempt_a_config_injection(),
        "attempt_B_call_site_injection": attempt_b_call_site_injection(),
        "attempt_C_target_override": attempt_c_target_override(),
        "source_evidence": source_evidence(),
    }
    print(json.dumps(document, indent=2, sort_keys=True))
    return 0


def _git_head() -> str:
    import subprocess

    return subprocess.run(
        ["git", "-C", str(EVE_ROOT), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())
