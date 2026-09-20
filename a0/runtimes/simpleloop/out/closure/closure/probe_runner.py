"""Run one SimpleLoop iteration batch inside whatever isolation it is launched in."""
import sys
from pathlib import Path

adapter_dir, run_dir, work_root, unused = sys.argv[1:5]
sys.path.insert(0, adapter_dir)

from a0_adapter.candidates import load_candidate_set          # noqa: E402
from a0_adapter.eidmap import load_eid                        # noqa: E402
from a0_adapter.loop import Budget                            # noqa: E402
from a0_adapter.policy import load_policy                     # noqa: E402
from a0_adapter.runner import Settings, parse_theta, run_once  # noqa: E402

work_root = Path(work_root)
adapter_dir = Path(adapter_dir)
script = Path(run_dir).parent / "scripts" / "closure_probe.json"
settings = Settings(
    work_root=work_root,
    adapter_dir=adapter_dir,
    e_star_python=work_root / "a0/tasks/circle-packing/.venv/bin/python",
    e_star_script=work_root / "a0/tasks/circle-packing/e_star.py",
    candidate_set=load_candidate_set(work_root / "a0/tasks/circle-packing/C_STAR/manifest.json"),
    eid=load_eid(
        work_root / "a0/tasks/circle-packing/plumbing.EID.proposed.json",
        spec_path=work_root / "a0/tasks/circle-packing/plumbing.contract.proposed.json",
        evalcontract_py=work_root / "a0/contract/evalcontract.py",
        python=Path(sys.executable),
        work_root=work_root,
    ),
    policy=load_policy(),
    theta=parse_theta("seed=1337,fidelity=full,fraction=1.0"),
    run_dir=Path(run_dir),
    run_id="closure-isolation",
    task="circle-packing",
    runtime="simpleloop",
    budget=Budget(),
    epsilon=1e-9,
    solver_kind="injected",
    solver_script=script,
    max_iterations=4,
)
outcome, _ev, _loop = run_once(settings, run_dir=Path(run_dir), run_id="closure-isolation",
                               max_iterations=4)
print("ISOLATION_RUN champion", outcome.champion_id, outcome.champion_scalar)
