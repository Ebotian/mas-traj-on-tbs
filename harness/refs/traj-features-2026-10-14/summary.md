# traj-features-2026-10-14 — 轨迹特征数值实验 v1(摘要)

确定性、零模型调用:所有数值均为所收集工件的纯函数(定义见 README.md)。

## 语料
| family | runs | sides | calls | masked | normal |
|---|---:|---:|---:|---:|---:|
| microarch | 5 | 10 | 2998 | 105 | 3/5 |
| tess | 1 | 2 | 655 | 8 | 1/1 |
| tumor | 3 | 6 | 1438 | 49 | 2/3 |
| walkthrough | 19 | 36 | 3371 | 1 | 14/19 |

## arms(单 agent ATIF)
- arms=8 calls=728 masked=26
  - agent-flash-1: ATIF-v1.7 calls=73 masked=1
  - agent-flash-1-restricted: ATIF-v1.8 calls=96 masked=0
  - agent-flash-1-sbb: ATIF-v1.8 calls=86 masked=1
  - agent-flash-1-sbb-eo: ATIF-v1.8 calls=94 masked=3
  - agent-flash-1-sbb-gateway: ATIF-v1.8 calls=82 masked=7
  - agent-flash-1-sbb-restricted: ATIF-v1.8 calls=93 masked=0
  - agent-qwen38flash-1-sbb-gateway: ATIF-v1.8 calls=68 masked=4
  - agent-qwen38max-1-sbb-restricted: ATIF-v1.8 calls=136 masked=10

## 不变式(独立复算)
- arms calls_total == 728 → 728 (OK)
- arms masked == 26 → 26 (OK)
- tumor-1 calls_total == 430(机制归因复核口径)→ 430 (OK)

## 双跑特征表(每跑)
| job | family | calls | masked | span_s(a/b) | cache_ratio(a/b) | rounds(a/b) | normal |
|---|---|---:|---:|---:|---:|---:|---:|
| bump-0251-flow | walkthrough | 165 | 0 | 1507.197/1527.19 | 0.994579/0.994545 | 7/7 | True |
| microarch-1 | microarch | 330 | 19 | 3786.802/3529.853 | 0.999635/0.992102 | 4/4 | False |
| microarch-2 | microarch | 514 | 18 | 4821.551/4721.271 | 0.999704/0.996284 | 8/8 | False |
| microarch-3 | microarch | 814 | 29 | 11086.668/10847.16 | 0.970505/0.999058 | 7/7 | True |
| microarch-4 | microarch | 656 | 14 | 11624.627/11270.175 | 0.979255/0.999301 | 5/5 | True |
| microarch-5 | microarch | 684 | 25 | 9844.04/9566.946 | 0.98885/0.998739 | 6/6 | True |
| tess-1 | tess | 655 | 8 | 9519.697/9360.698 | 0.997994/0.999195 | 5/5 | True |
| tumor-1 | tumor | 430 | 17 | 7021.717/7047.593 | 0.999511/0.998526 | 6/7 | None |
| tumor-2 | tumor | 403 | 5 | 4746.075/4829.286 | 0.99934/0.999062 | 6/6 | True |
| tumor-3 | tumor | 605 | 27 | 9407.447/9135.902 | 0.995306/0.997267 | 6/6 | True |
| w6n-pilot | walkthrough | 203 | 0 | 1122.212/1247.915 | 0.998322/0.99668 | 7/7 | True |
| w6n1 | walkthrough | 192 | 0 | 954.574/1504.273 | 0.998006/0.996424 | 7/7 | True |
| w6n2 | walkthrough | 199 | 0 | 904.485/1002.367 | 0.99839/0.985415 | 7/7 | True |
| w6n3 | walkthrough | 221 | 0 | 1044.453/1128.176 | 0.998333/0.99794 | 7/7 | True |
| w6n4 | walkthrough | 206 | 0 | 1124.425/1222.53 | 0.998591/0.992302 | 7/7 | True |
| w6r-pilot | walkthrough | 180 | 0 | 948.378/1024.654 | 0.998467/0.993504 | 7/7 | True |
| w6r1 | walkthrough | 211 | 1 | 1264.037/1363.763 | 0.998835/0.998586 | 7/7 | True |
| w6r2 | walkthrough | 201 | 0 | 1219.149/1374.138 | 0.998129/0.994945 | 7/7 | True |
| w6r3 | walkthrough | 168 | 0 | 746.48/788.605 | 0.996436/0.990624 | 7/7 | True |
| w6r4 | walkthrough | 180 | 0 | 896.569/1021.619 | 0.999181/0.995994 | 7/7 | True |
| walkthrough-10 | walkthrough | 252 | 0 | 2510.779/2273.848 | 0.99532/0.993767 | 7/7 | True |
| walkthrough-3 | walkthrough | 0 | 0 | None/None | None/None | 0/0 | None |
| walkthrough-4 | walkthrough | 114 | 0 | 670.492/721.59 | 0.998258/0.997481 | 7/7 | None |
| walkthrough-5 | walkthrough | 108 | 0 | 674.974/693.642 | 0.997931/0.996827 | 7/7 | None |
| walkthrough-6 | walkthrough | 163 | 0 | 845.918/1021.967 | 0.999069/0.99392 | 7/7 | None |
| walkthrough-7 | walkthrough | 123 | 0 | 2353.165/1848.617 | 0.99067/0.991538 | 1/3 | False |
| walkthrough-8 | walkthrough | 242 | 0 | 2444.832/2315.394 | 0.997293/0.995635 | 7/7 | True |
| walkthrough-9 | walkthrough | 243 | 0 | 2109.901/1762.569 | 0.992611/0.989078 | 7/7 | True |

## 备注
- 定义与口径:见 README.md;masked = 工具结果 exitCode==0 且 output 含 Traceback(启发式下界)。
- 转录记录 schema:Qwen chat JSONL(assistant functionCall / tool_result.toolCallResult.resultDisplay)。
- 本表不含语义推断类特征(S 类),只收机械可算量;语义特征需单独的证据根映射。
- 熵:kind_entropy=类别边际熵(非首调用,−Σp·log₂p,bit);transition_entropy=条件转移熵(§4.2,α=1,π̂=经验边际,nat)。
