# traj_stats ckpt-m01
commit: fde97e0ce213c7e7dd455b3c900c7b93bc26f192  (2026-10-12T16:03:25Z)  cut_epoch: 1791821196
availability: tag_commit=1791821005 max_source=1791821196 cut=1791821196 unknown=protocol.dirs.a,protocol.dirs.b

volume[a]: lines<=cut=533 cut_last_line=533 assistant=81 tool_results=97 tokens={"prompt": 8044416, "candidates": 80776, "thoughts": 55400, "cached": 7878272} uncached=166144
pacing[a]: median=0s p90=4s p99=53s max=590s silences>600s=0
volume[b]: lines<=cut=689 cut_last_line=689 assistant=102 tool_results=126 tokens={"prompt": 15734998, "candidates": 147819, "thoughts": 96307, "cached": 15465060} uncached=269938
pacing[b]: median=0s p90=8s p99=71s max=97s silences>600s=0
surface: only_a=85 only_b=142 both=56 untouched_repo_files=1
text_overlap: a->b=89 (cited 0)  b->a=71 (cited 0)  concurrent=0  [events listed=30/160] (文本重合计数,非语义采纳)
ledger[a]: entries=15 kinds={"commit": 1, "file": 10, "row": 1, "run": 3} unresolved=0 source=tag:ckpt-m01
ledger[b]: entries=26 kinds={"commit": 2, "file": 11, "row": 6, "run": 5, "unresolved": 2} unresolved=2 source=tag:ckpt-m01
protocol: forks=10 differing=8/10

note: 程序生成的机械统计(无网络/无 LLM/无任务先验);列表均已截断;明细见同名 .json。
