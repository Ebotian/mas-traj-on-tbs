# traj_stats ckpt-m01
commit: 0314d6ee8e004ecb9e415ccf12c85786a9022951  (2026-10-13T14:45:42Z)  cut_epoch: 1791903539
availability: tag_commit=1791902742 max_source=1791903539 cut=1791903539 unknown=-

volume[a]: lines<=cut=588 cut_last_line=588 assistant=77 tool_results=128 tokens={"prompt": 11037558, "candidates": 153793, "thoughts": 118106, "cached": 10760448} uncached=277110
pacing[a]: median=0s p90=5s p99=62s max=240s silences>600s=0
volume[b]: lines<=cut=466 cut_last_line=466 assistant=67 tool_results=89 tokens={"prompt": 6841377, "candidates": 89687, "thoughts": 56456, "cached": 6652719} uncached=188658
pacing[b]: median=0s p90=8s p99=72s max=196s silences>600s=0
surface: only_a=138 only_b=118 both=57 untouched_repo_files=0
text_overlap: a->b=75 (cited 0)  b->a=41 (cited 0)  concurrent=0  [events listed=30/116] (文本重合计数,非语义采纳)
ledger[a]: entries=14 kinds={"file": 7, "row": 3, "run": 3, "unresolved": 1} unresolved=1 source=tag:ckpt-m01
ledger[b]: entries=17 kinds={"file": 7, "row": 8, "run": 1, "unresolved": 1} unresolved=1 source=tag:ckpt-m01
protocol: forks=11 differing=3/11

note: 程序生成的机械统计(无网络/无 LLM/无任务先验);列表均已截断;明细见同名 .json。
