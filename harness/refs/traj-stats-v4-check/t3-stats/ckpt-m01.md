# traj_stats ckpt-m01
commit: e219108326cd0da1d9a0eff83079a2958bc69f5e  (2026-10-13T14:40:31Z)  cut_epoch: 1791902676
availability: tag_commit=1791902431 max_source=1791902676 cut=1791902676 unknown=protocol.dirs.a

volume[a]: lines<=cut=374 cut_last_line=374 assistant=56 tool_results=66 tokens={"prompt": 6566878, "candidates": 134406, "thoughts": 114125, "cached": 6338944} uncached=227934
pacing[a]: median=0s p90=4s p99=52s max=95s silences>600s=0
volume[b]: lines<=cut=354 cut_last_line=354 assistant=54 tool_results=64 tokens={"prompt": 5034185, "candidates": 44689, "thoughts": 16409, "cached": 4880046} uncached=154139
pacing[b]: median=0s p90=7s p99=43s max=65s silences>600s=0
surface: only_a=57 only_b=96 both=41 untouched_repo_files=1
text_overlap: a->b=71 (cited 0)  b->a=47 (cited 0)  concurrent=0  [events listed=30/118] (文本重合计数,非语义采纳)
ledger[a]: entries=16 kinds={"file": 9, "run": 7} unresolved=0 source=tag:ckpt-m01
ledger[b]: entries=12 kinds={"file": 3, "run": 9} unresolved=0 source=tag:ckpt-m01
protocol: forks=10 differing=4/10

note: 程序生成的机械统计(无网络/无 LLM/无任务先验);列表均已截断;明细见同名 .json。
