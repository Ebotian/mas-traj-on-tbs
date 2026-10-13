# traj_stats ckpt-m2
commit: cd48d656685c80c3997d4fce0f00b7cf54dc7bea  (2026-10-12T08:01:25Z)  cut_epoch: 1791792085

volume[a]: lines<=cut=187/282 assistant=21 tool_results=46 tokens={"prompt": 2544159, "candidates": 129892, "thoughts": 122822, "cached": 2361216} uncached=182943
pacing[a]: median=0s p90=2s p99=79s max=174s silences>600s=0
volume[b]: lines<=cut=186/370 assistant=28 tool_results=34 tokens={"prompt": 1596902, "candidates": 30752, "thoughts": 16876, "cached": 1448035} uncached=148867
pacing[b]: median=0s p90=7s p99=35s max=530s silences>600s=0
surface: only_a=25 only_b=41 both=22 untouched_repo_files=0
adoption: a->b=41 (cited 0)  b->a=60 (cited 0)  concurrent=0  [events listed=30/101]
ledger[a]: entries=0 kinds={} unresolved=0 source=missing
ledger[b]: entries=3 kinds={"file": 1, "traj": 1, "unresolved": 1} unresolved=1 source=file:/tmp/stats-v2-check/w7/repo/refs-b.jsonl
protocol: forks=8 differing=0/8

note: 程序生成的机械统计(无网络/无 LLM/无任务先验);列表均已截断;明细见同名 .json。
