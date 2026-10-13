# Early-stop audit over collected dual-agent runs (2026-10-12)

runs=20  side-transcripts=40  pool(sides>=12 steps)=40

## Inventory by family
- microarch  runs= 2 sides= 4 steps=  814 out_tok=    1.79M unc_tok=  1.15M cache_tok=   236.3M
- rehearsal  runs=16 sides=32 steps= 2400 out_tok=    4.95M unc_tok=  4.34M cache_tok=   215.5M
- tumor      runs= 2 sides= 4 steps=  821 out_tok=    2.03M unc_tok=  2.01M cache_tok=   264.1M
- totals     runs=20 sides=40 steps= 4035 out=8.77M unc=7.50M cache=715.9M
- pool cost: A=$6.513(USD) B=40.9(CNY) total~CNY 86.5 ; tail75 of cost: A=$1.447 B=14.5

## Perfect-halt saving upper bound (median over pool, cut at k%% of steps)
- cut 50% : saved out=49.9%  unc=37.6%  cache=67.6%  wall-residue=52.8%
- cut 75% : saved out=20.4%  unc=16.4%  cache=38.3%  wall-residue=20.2%
- cut 90% : saved out=8.1%  unc=6.5%  cache=16.6%  wall-residue=7.0%

## Context growth (median prompt tokens at deciles of the run)
- decile 10% : median prompt    38084 tok
- decile 20% : median prompt    55788 tok
- decile 30% : median prompt    63508 tok
- decile 40% : median prompt    78034 tok
- decile 50% : median prompt    88005 tok
- decile 60% : median prompt   108796 tok
- decile 70% : median prompt   117455 tok
- decile 80% : median prompt   126627 tok
- decile 90% : median prompt   133764 tok
- decile 100% : median prompt   143112 tok

## Existing stop/abort signals vs verdicts
- runs with abort files: 3 ; of them abnormal: 3
    microarch-1 abort-a @ 2026-10-11T18:18:00Z | abort a 2026-10-11T18:18:00Z reason: peer-b ended its session at 2026-10-11T18:12:02Z (wrote stop-b; pid-b dead) before performing its M2 me
    microarch-2 abort-b @ None | abort-b: wait_pos a 8 rc=2 x2 windows -- "wait_pos: peer-a silent for ~900 s (no transcript activity)"; peer stalled after writing /root/mod
    walkthrough-7 abort-b @ 2026-10-12T08:14:30Z | abort b 2026-10-12T08:14:30Z reason (verbatim from `bash /root/wt/wait_peer.sh a 3`, exit code 2): wait_peer: peer-a dead, round < 3 detail:
- normal runs: 17 ; runs with any abort among them: 0
- runs with recover.json: walkthrough-7[wakes=2], walkthrough-8[wakes=1]
- abnormal runs and mechanism:
    microarch-1 : b early-stop (skipped M2 duty) -> a abort
    microarch-2 : b abort on perceived a-stall (~900s x2); a stop later (race)
    walkthrough-7 : peer-dead(a, 402) -> b abort -> recovery closeout

## Side A (deepseek) vs side B (qwen) descriptive
- side a : n=20  gap med=3.7s p90=27.3s max=203.1s  out/step=2777 tok  steps med=75
- side b : n=20  gap med=7.5s p90=26.9s max=98.3s  out/step=946 tok  steps med=91

## Per-run table
- bump-0251-flow     rehearsal normal=True  rc=[0, 0] stop=[True, True] abort=[False, False] mech=
- microarch-1        microarch normal=False rc=[0, 0] stop=[False, True] abort=[True, False] mech=b early-stop (skipped M2 duty) -> a abort
- microarch-2        microarch normal=False rc=[0, 0] stop=[True, False] abort=[False, True] mech=b abort on perceived a-stall (~900s x2); a stop later (race)
- tumor-1            tumor    normal=True  rc=[0, 0] stop=[True, True] abort=[False, False] mech=
- tumor-2            tumor    normal=True  rc=[0, 0] stop=[True, True] abort=[False, False] mech=
- w6n-pilot          rehearsal normal=True  rc=[0, 0] stop=[True, True] abort=[False, False] mech=
- w6n1               rehearsal normal=True  rc=[0, 0] stop=[True, True] abort=[False, False] mech=
- w6n2               rehearsal normal=True  rc=[0, 0] stop=[True, True] abort=[False, False] mech=
- w6n3               rehearsal normal=True  rc=[0, 0] stop=[True, True] abort=[False, False] mech=
- w6n4               rehearsal normal=True  rc=[0, 0] stop=[True, True] abort=[False, False] mech=
- w6r-pilot          rehearsal normal=True  rc=[0, 0] stop=[True, True] abort=[False, False] mech=
- w6r1               rehearsal normal=True  rc=[0, 0] stop=[True, True] abort=[False, False] mech=
- w6r2               rehearsal normal=True  rc=[0, 0] stop=[True, True] abort=[False, False] mech=
- w6r3               rehearsal normal=True  rc=[0, 0] stop=[True, True] abort=[False, False] mech=
- w6r4               rehearsal normal=True  rc=[0, 0] stop=[True, True] abort=[False, False] mech=
- walkthrough-4      rehearsal normal=True  rc=[0, 0] stop=[True, True] abort=[False, False] mech=
- walkthrough-5      rehearsal normal=True  rc=[0, 0] stop=[True, True] abort=[False, False] mech=
- walkthrough-6      rehearsal normal=True  rc=[0, 0] stop=[True, True] abort=[False, False] mech=
- walkthrough-7      rehearsal normal=False rc=[1, 0] stop=[True, False] abort=[False, True] mech=peer-dead(a, 402) -> b abort -> recovery closeout
- walkthrough-8      rehearsal normal=True  rc=[0, 0] stop=[True, True] abort=[False, False] mech=

## Per-side table (pool only)
- bump-0251-flow     a steps= 71 out=  0.20M unc= 0.18M cache=    6.9M wall=1507s gapmax=454s saved_out75=23.0% saved_unc75=19.2%
- bump-0251-flow     b steps= 73 out=  0.13M unc= 0.14M cache=    5.0M wall=1527s gapmax=83s saved_out75=31.1% saved_unc75=23.5%
- microarch-1        a steps=204 out=  0.49M unc= 0.17M cache=   53.8M wall=3787s gapmax=124s saved_out75=23.1% saved_unc75=22.4%
- microarch-1        b steps=110 out=  0.31M unc= 0.37M cache=   26.3M wall=3530s gapmax=205s saved_out75=11.6% saved_unc75=14.4%
- microarch-2        a steps=295 out=  0.70M unc= 0.24M cache=  115.9M wall=4822s gapmax=608s saved_out75=11.9% saved_unc75=17.1%
- microarch-2        b steps=205 out=  0.29M unc= 0.37M cache=   40.3M wall=4721s gapmax=286s saved_out75=23.9% saved_unc75=22.5%
- tumor-1            a steps=158 out=  0.46M unc= 0.22M cache=   45.5M wall=7022s gapmax=609s saved_out75=16.4% saved_unc75=14.3%
- tumor-1            b steps=264 out=  0.63M unc= 0.68M cache=   97.0M wall=7048s gapmax=261s saved_out75=24.3% saved_unc75=20.8%
- tumor-2            a steps=228 out=  0.53M unc= 0.65M cache=   74.9M wall=4746s gapmax=623s saved_out75=14.7% saved_unc75=66.8%
- tumor-2            b steps=171 out=  0.40M unc= 0.46M cache=   46.7M wall=4829s gapmax=204s saved_out75=16.3% saved_unc75=14.5%
- w6n-pilot          a steps= 81 out=  0.17M unc= 0.06M cache=    7.4M wall=1122s gapmax=177s saved_out75=18.8% saved_unc75=10.0%
- w6n-pilot          b steps=101 out=  0.09M unc= 0.11M cache=    6.5M wall=1248s gapmax=89s saved_out75=25.6% saved_unc75=18.7%
- w6n1               a steps= 82 out=  0.12M unc= 0.05M cache=    5.3M wall=955s gapmax=137s saved_out75=31.0% saved_unc75=18.6%
- w6n1               b steps= 81 out=  0.08M unc= 0.19M cache=    4.8M wall=1504s gapmax=605s saved_out75=20.9% saved_unc75=55.9%
- w6n2               a steps= 75 out=  0.19M unc= 0.05M cache=    6.1M wall=904s gapmax=123s saved_out75=17.1% saved_unc75=12.8%
- w6n2               b steps= 83 out=  0.07M unc= 0.10M cache=    4.8M wall=1002s gapmax=47s saved_out75=23.8% saved_unc75=16.5%
- w6n3               a steps= 73 out=  0.23M unc= 0.09M cache=   10.5M wall=1044s gapmax=206s saved_out75=12.1% saved_unc75=8.6%
- w6n3               b steps= 95 out=  0.09M unc= 0.12M cache=    6.8M wall=1128s gapmax=68s saved_out75=25.6% saved_unc75=16.4%
- w6n4               a steps= 82 out=  0.22M unc= 0.07M cache=   10.5M wall=1124s gapmax=159s saved_out75=11.5% saved_unc75=12.1%
- w6n4               b steps= 96 out=  0.07M unc= 0.09M cache=    5.3M wall=1223s gapmax=125s saved_out75=20.6% saved_unc75=17.6%
- w6r-pilot          a steps= 64 out=  0.18M unc= 0.06M cache=    6.4M wall=948s gapmax=201s saved_out75=21.9% saved_unc75=9.2%
- w6r-pilot          b steps= 87 out=  0.08M unc= 0.10M cache=    5.1M wall=1025s gapmax=59s saved_out75=20.1% saved_unc75=14.7%
- w6r1               a steps= 75 out=  0.18M unc= 0.04M cache=    6.3M wall=1264s gapmax=456s saved_out75=13.5% saved_unc75=11.7%
- w6r1               b steps=107 out=  0.09M unc= 0.12M cache=    7.5M wall=1364s gapmax=105s saved_out75=30.6% saved_unc75=21.0%
- w6r2               a steps= 75 out=  0.13M unc= 0.05M cache=    5.3M wall=1219s gapmax=350s saved_out75=18.8% saved_unc75=8.8%
- w6r2               b steps= 95 out=  0.11M unc= 0.13M cache=    6.8M wall=1374s gapmax=125s saved_out75=26.6% saved_unc75=25.0%
- w6r3               a steps= 76 out=  0.18M unc= 0.06M cache=    7.9M wall=746s gapmax=75s saved_out75=11.0% saved_unc75=8.5%
- w6r3               b steps= 74 out=  0.07M unc= 0.09M cache=    4.2M wall=789s gapmax=64s saved_out75=33.3% saved_unc75=17.4%
- w6r4               a steps= 66 out=  0.19M unc= 0.07M cache=    7.5M wall=897s gapmax=249s saved_out75=13.8% saved_unc75=10.8%
- w6r4               b steps= 86 out=  0.08M unc= 0.11M cache=    5.0M wall=1022s gapmax=58s saved_out75=34.3% saved_unc75=27.3%
- walkthrough-4      a steps= 34 out=  0.16M unc= 0.03M cache=    2.9M wall=670s gapmax=64s saved_out75=10.5% saved_unc75=8.6%
- walkthrough-4      b steps= 59 out=  0.04M unc= 0.06M cache=    2.4M wall=722s gapmax=76s saved_out75=17.9% saved_unc75=13.4%
- walkthrough-5      a steps= 38 out=  0.17M unc= 0.03M cache=    3.9M wall=675s gapmax=67s saved_out75=4.4% saved_unc75=8.4%
- walkthrough-5      b steps= 50 out=  0.03M unc= 0.06M cache=    1.9M wall=694s gapmax=92s saved_out75=25.4% saved_unc75=11.4%
- walkthrough-6      a steps= 75 out=  0.24M unc= 0.07M cache=    9.6M wall=846s gapmax=80s saved_out75=14.9% saved_unc75=12.7%
- walkthrough-6      b steps= 69 out=  0.08M unc= 0.11M cache=    4.5M wall=1022s gapmax=47s saved_out75=30.8% saved_unc75=18.1%
- walkthrough-7      a steps= 31 out=  0.36M unc= 0.44M cache=    4.5M wall=2353s gapmax=1159s saved_out75=13.5% saved_unc75=12.3%
- walkthrough-7      b steps= 57 out=  0.11M unc= 0.32M cache=    4.4M wall=1849s gapmax=540s saved_out75=36.2% saved_unc75=46.2%
- walkthrough-8      a steps= 91 out=  0.63M unc= 0.94M cache=   28.3M wall=2445s gapmax=245s saved_out75=12.4% saved_unc75=54.2%
- walkthrough-8      b steps= 98 out=  0.16M unc= 0.21M cache=   11.0M wall=2315s gapmax=292s saved_out75=29.4% saved_unc75=19.4%
