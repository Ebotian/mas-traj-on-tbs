# traj_stats ckpt-m00
commit: f57ecfa9a19faa7f5f745ae505a6ae21b93901be  (2026-10-12T10:22:42Z)  cut_epoch: 1791800562

volume[a]: lines<=cut=145/673 assistant=15 tool_results=40 tokens={"prompt": 1669461, "candidates": 104259, "thoughts": 96044, "cached": 1498752} uncached=170709
pacing[a]: median=0s p90=1s p99=62s max=245s silences>600s=0
volume[b]: lines<=cut=168/631 assistant=24 tool_results=33 tokens={"prompt": 1311126, "candidates": 26483, "thoughts": 15784, "cached": 1224476} uncached=86650
pacing[b]: median=0s p90=9s p99=61s max=278s silences>600s=0
surface: only_a=51 only_b=29 both=31 untouched_repo_files=1
adoption: a->b=52 (cited 0)  b->a=59 (cited 0)  concurrent=0  [events listed=30/111]
ledger[a]: entries=15 kinds={"commit": 4, "file": 3, "run": 2, "traj": 3, "unresolved": 3} unresolved=3 source=file:/tmp/stats-v2-check/w8/repo/refs-a.jsonl
ledger[b]: entries=6 kinds={"commit": 2, "file": 2, "run": 1, "unresolved": 1} unresolved=1 source=tag:ckpt-m00
protocol: forks=5 differing=3/5

note: 程序生成的机械统计(无网络/无 LLM/无任务先验);列表均已截断;明细见同名 .json。
