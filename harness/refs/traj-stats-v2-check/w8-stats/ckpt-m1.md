# traj_stats ckpt-m1
commit: ecf8bda1a12bc5461c0c7677b72590b3b4858b45  (2026-10-12T10:35:49Z)  cut_epoch: 1791801349

volume[a]: lines<=cut=343/673 assistant=44 tool_results=76 tokens={"prompt": 10049686, "candidates": 227253, "thoughts": 206515, "cached": 9707776} uncached=341910
pacing[a]: median=0s p90=8s p99=69s max=245s silences>600s=0
volume[b]: lines<=cut=387/631 assistant=59 tool_results=70 tokens={"prompt": 4891168, "candidates": 60366, "thoughts": 34187, "cached": 4745554} uncached=145614
pacing[b]: median=0s p90=12s p99=59s max=278s silences>600s=0
surface: only_a=80 only_b=39 both=47 untouched_repo_files=0
adoption: a->b=155 (cited 0)  b->a=91 (cited 0)  concurrent=0  [events listed=30/246]
ledger[a]: entries=8 kinds={"commit": 4, "file": 2, "run": 2} unresolved=0 source=tag:ckpt-m1
ledger[b]: entries=20 kinds={"commit": 5, "file": 4, "row": 4, "run": 3, "traj": 1, "unresolved": 3} unresolved=3 source=tag:ckpt-m1
protocol: forks=5 differing=3/5

note: 程序生成的机械统计(无网络/无 LLM/无任务先验);列表均已截断;明细见同名 .json。
