# traj_stats ckpt-m01
commit: 985402289aa252c595ff361675521f1a3ea98da8  (2026-10-12T16:21:03Z)  cut_epoch: 1791822737
availability: tag_commit=1791822063 max_source=1791822737 cut=1791822737 unknown=protocol.dirs.a,protocol.dirs.b

volume[a]: lines<=cut=670 cut_last_line=670 assistant=95 tool_results=133 tokens={"prompt": 16645284, "candidates": 358866, "thoughts": 322899, "cached": 16177664} uncached=467620
pacing[a]: median=0s p90=6s p99=87s max=600s silences>600s=0
volume[b]: lines<=cut=689 cut_last_line=689 assistant=100 tool_results=129 tokens={"prompt": 19195714, "candidates": 201675, "thoughts": 127802, "cached": 18788043} uncached=407671
pacing[b]: median=0s p90=10s p99=92s max=590s silences>600s=0
surface: only_a=113 only_b=155 both=65 untouched_repo_files=0
text_overlap: a->b=351 (cited 0)  b->a=296 (cited 0)  concurrent=0  [events listed=30/647] (文本重合计数,非语义采纳)
ledger[a]: entries=27 kinds={"commit": 4, "file": 12, "row": 3, "run": 8} unresolved=0 source=tag:ckpt-m01
ledger[b]: entries=15 kinds={"file": 6, "row": 2, "run": 5, "unresolved": 2} unresolved=2 source=tag:ckpt-m01
protocol: forks=12 differing=7/12

note: 程序生成的机械统计(无网络/无 LLM/无任务先验);列表均已截断;明细见同名 .json。
