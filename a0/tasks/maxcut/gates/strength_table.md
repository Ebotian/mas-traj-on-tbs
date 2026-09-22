| positive control | k | set | Δ mean (≥0.03) | Δ families (≥3/4) | Δ gate | ρ median (≥0.30) | ρ families (≥3/4) | ρ gate | task |
|---|---|---|---|---|---|---|---|---|---|
| `pc` | ∞ (to local opt.) | dev | 0.247943 | 4/4 | PASS | 0.158820 | 0/4 | FAIL | NOT_ADMISSIBLE |
| `pc` | ∞ (to local opt.) | eval | 0.238448 | 4/4 | PASS | 0.178716 | 0/4 | FAIL | NOT_ADMISSIBLE |
| `pc_exchange_k01` | 1 | dev | 0.018221 | 1/4 | FAIL | 0.940123 | 4/4 | PASS | NOT_ADMISSIBLE |
| `pc_exchange_k01` | 1 | eval | 0.017983 | 1/4 | FAIL | 0.942883 | 4/4 | PASS | NOT_ADMISSIBLE |
| `pc_exchange_k02` | 2 | dev | 0.032882 | 4/4 | PASS | 0.895644 | 4/4 | PASS | ADMISSIBLE |
| `pc_exchange_k02` | 2 | eval | 0.033074 | 4/4 | PASS | 0.894196 | 4/4 | PASS | ADMISSIBLE |
| `pc_exchange_k05` | 5 | dev | 0.069658 | 4/4 | PASS | 0.775149 | 4/4 | PASS | ADMISSIBLE |
| `pc_exchange_k05` | 5 | eval | 0.070200 | 4/4 | PASS | 0.762308 | 4/4 | PASS | ADMISSIBLE |
| `pc_exchange_k10` | 10 | dev | 0.116585 | 4/4 | PASS | 0.615639 | 4/4 | PASS | ADMISSIBLE |
| `pc_exchange_k10` | 10 | eval | 0.116427 | 4/4 | PASS | 0.600847 | 4/4 | PASS | ADMISSIBLE |
| `pc_exchange_k25` | 25 | dev | 0.204898 | 4/4 | PASS | 0.325903 | 3/4 | PASS | ADMISSIBLE |
| `pc_exchange_k25` | 25 | eval | 0.202023 | 4/4 | PASS | 0.301163 | 2/4 | FAIL | NOT_ADMISSIBLE |

| positive control | set | ER | RR | BA | Planted |
|---|---|---|---|---|---|
| `pc` | dev | 0.2243 / 0.2051 | 0.3043 / 0.1436 | 0.2429 / 0.1518 | 0.2203 / 0.1526 |
| `pc` | eval | 0.2177 / 0.1781 | 0.2889 / 0.1948 | 0.2414 / 0.1692 | 0.2058 / 0.1806 |
| `pc_exchange_k01` | dev | 0.0164 / 0.9401 | 0.0156 / 0.9580 | 0.0261 / 0.9124 | 0.0147 / 0.9432 |
| `pc_exchange_k01` | eval | 0.0166 / 0.9416 | 0.0156 / 0.9551 | 0.0243 / 0.9143 | 0.0154 / 0.9431 |
| `pc_exchange_k02` | dev | 0.0289 / 0.8956 | 0.0312 / 0.9160 | 0.0446 / 0.8574 | 0.0267 / 0.8951 |
| `pc_exchange_k02` | eval | 0.0304 / 0.8954 | 0.0312 / 0.9101 | 0.0427 / 0.8622 | 0.0280 / 0.8907 |
| `pc_exchange_k05` | dev | 0.0616 / 0.7807 | 0.0755 / 0.8060 | 0.0813 / 0.7417 | 0.0603 / 0.7687 |
| `pc_exchange_k05` | eval | 0.0642 / 0.7631 | 0.0768 / 0.7817 | 0.0800 / 0.7287 | 0.0598 / 0.7635 |
| `pc_exchange_k10` | dev | 0.1068 / 0.6219 | 0.1313 / 0.6345 | 0.1263 / 0.5704 | 0.1020 / 0.6051 |
| `pc_exchange_k10` | eval | 0.1113 / 0.5839 | 0.1297 / 0.6280 | 0.1250 / 0.5589 | 0.0997 / 0.6060 |
| `pc_exchange_k25` | dev | 0.1904 / 0.3275 | 0.2441 / 0.3476 | 0.2085 / 0.2631 | 0.1765 / 0.3224 |
| `pc_exchange_k25` | eval | 0.1941 / 0.2821 | 0.2332 / 0.3481 | 0.2082 / 0.2866 | 0.1725 / 0.3228 |

(per family: mean Δ / median ρ)
