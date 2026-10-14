# Offline Replay Attribution for Agent Trajectories: A Reproducible Manual-Prior + AutoFE Pipeline

## Executive summary

The right abstraction for this project is **not “train a classifier on agent logs.”** It is:

\[
\boxed{
\text{historically valid replay state}
\rightarrow
\text{predictive state model}
\rightarrow
\text{explicit intervention}
\rightarrow
\text{counterfactual outcome attribution}
}
\]

The distinction matters. ATIF gives a sequential record of agent interactions, tool calls, observations, metrics, and subagent trajectories; OCEL provides a natural representation for the many-to-many graph connecting agents, events, files, commits, artifacts, and evidence; OpenTelemetry gives fine-grained operation timing and trace relationships. They should be retained as complementary source layers rather than collapsed early into one flat trajectory table. Harbor's active ATIF RFC is explicitly designed for complete agent interaction histories and replay-oriented use, while OCEL 2.0 was designed for object-centric event logs with qualified event-object and object-object relationships. citeturn15search0turn16academia48turn20search8

Your earlier Microarch evidence changes one design decision from “recommended” to **mandatory**: every feature used at historical checkpoint \(c\) must be proven to have been knowable at \(c\). OpenTelemetry itself distinguishes source event time from observation time, and its trace specification explicitly permits events with custom timestamps to be recorded out of timestamp order. Therefore sorting by timestamp is not enough to establish historical availability. citeturn20search0turn20search10

I recommend four immutable temporal fields:

\[
(\text{eventTime},\;\text{observedAt},\;\text{availableAt},\;\text{derivedAt})
\]

and the hard eligibility rule

\[
\boxed{
f\text{ is legal at checkpoint }c
\iff
\max_{s\in Dep(f)} availableAt(s)\le cutoff(c)
}
\]

with **zero tolerated violations**.

The feature system should deliberately combine two branches:

\[
X_c =
\underbrace{X_c^{manual}}_{\text{pre-registered scientific priors}}
\oplus
\underbrace{X_c^{auto}}_{\text{nested leakage-safe AutoFE}}
\oplus
\underbrace{X_c^{latent}}_{\text{HMM/HSMM phase state}}
\]

Manual priors encode hypotheses already suggested by your Tumor/Microarch analyses: error and recovery dynamics, evidence integrity, consensus/divergence, Git churn, unresolved obligations, cache efficiency, validation activity, and remaining-time pressure. AutoFE should discover interactions, multi-scale temporal structure, sequence motifs, and OCEL graph patterns that the manual layer missed. tsfresh provides a useful precedent for large-scale automated time-series feature extraction; Featuretools' Deep Feature Synthesis targets relational/temporal data; OpenFE addresses candidate expansion and pruning in large AutoFE spaces. All target-aware selection must occur *inside training folds*, not before splitting. citeturn17search0turn17search13turn16academia49

For prediction, I would make **sparse logistic/linear models the interpretability baseline and GBDT + SHAP the primary nonlinear model**, with LSTM and Transformer models as comparison arms rather than the default. XGBoost is a mature tree-boosting approach for sparse tabular problems, while SHAP provides additive local feature attribution; importantly, SHAP explains the predictor, **not causal effects of features**. citeturn14academia24turn13search1 Sequence models become valuable once the number of genuinely independent trajectories—not merely correlated prefixes—is large enough; LSTM and Transformer are natural comparison architectures for sequential traces. citeturn18search0turn19search0

For causal attribution, the hierarchy should be:

\[
\boxed{
\text{randomized checkpoint fork}
>
\text{DR/AIPW with logged intervention propensities}
>
\text{estimated-propensity observational DR}
>
\text{IPW alone}
}
\]

Doubly robust estimators combine outcome and treatment/behavior models, and sequential DR extends the idea to off-policy sequential evaluation. Cross-fitting and orthogonal scores are especially appropriate once AutoFE/GBDT nuisance models become flexible. citeturn22academia36turn13search0turn18search5

The most important instrumentation change is consequently **not another feature**. It is to introduce a small number of explicit, discrete, policy-level intervention points and log their assignment probabilities. Examples are “search-before-build enabled,” “run an independent validation now,” “ask peer agent,” “retain ensemble vs choose one model,” or “allocate another validation budget block.” Retrospectively estimating the probability that an unrestricted LLM would emit an arbitrary terminal action is a weak causal foundation. A randomized router over predefined meta-actions gives you actual propensities and makes DR/OPE substantially more credible. The original contextual-bandit DR work specifically addresses evaluation from historically logged contexts, actions and rewards when action distributions differ. citeturn22search2turn22academia36

For the confirmatory study I would pre-register the following **engineering success gates**, explicitly as proposed thresholds rather than universal constants:

| Layer | Proposed confirmatory gate |
|---|---:|
| Historical availability | **0** `availableAt > cutoff` dependency violations |
| Raw provenance | **100%** raw inputs SHA-256-addressed |
| Feature reproducibility | identical feature-matrix content hash on independent rerun |
| Binary outcome prediction | Brier skill ≥ **0.15** over task-conditioned null |
| Imbalanced classification | PR skill ≥ **0.20** |
| Calibration | ECE ≤ **0.05**, calibration slope **0.8–1.2** |
| Continuous normalized verifier score | MAE ≤ **0.10** and ≥ **20%** better than null |
| AutoFE incremental value | ≥ **0.03 absolute AUPRC** gain or ≥ **10% relative MAE** reduction over manual-only |
| Cross-task robustness | held-out-task degradation ≤ **20% relative** |
| Synthetic causal-effect recovery | absolute bias ≤ **2 percentage points** |
| Nominal causal CI validation | 95% CI empirical coverage **92–98%** |
| Real attribution precision | 95% CI half-width ≤ **5 percentage points** |
| OPE overlap | effective sample size / \(N\) ≥ **0.30** |
| Attribution stability | same effect sign in ≥ **80%** leave-one-task-family-out resamples |

AUPRC is preferable to ROC-AUC as a primary ranking metric when success/failure becomes imbalanced, and Brier score directly evaluates probabilistic forecasts. citeturn19search2turn19search1

Finally, the power calculation is sobering and should shape the data-collection strategy. At a 50% baseline success rate, detecting a **5 percentage-point** absolute improvement with a conventional independent two-arm design at 80% power requires approximately **1,565 runs per arm**; a **10-point** improvement requires about **388 per arm**. A paired checkpoint-fork design can cut this dramatically: if only 20% of paired outcomes are discordant, approximately **621 checkpoint pairs** are needed for 5 points and **150 pairs** for 10 points. This is why I would spend engineering effort on matched checkpoint forks rather than merely accumulating more unrelated full trajectories.

The conceptual conclusion is therefore:

\[
\boxed{
\text{The unit of scientific progress should become the replayable intervention opportunity,
not the log line and not the prefix row.}
}
\]

That is the architecture most likely to turn your current computational-history idea from retrospective pattern finding into defensible causal attribution.

## Replay data contract and historical semantics

The offline replay pipeline should preserve the raw sources independently and build a canonical event/object layer **above** them. ATIF should remain the authoritative sequential interaction record. Harbor's active RFC defines trajectory steps, timestamps, agent/model metadata, tool calls, observations, step metrics, final metrics, continued trajectories and subagent trajectories; it also explicitly treats session and trajectory identity separately. citeturn15search0

OCEL should then represent the relational structure that ATIF does not naturally flatten: an event can involve several objects, objects can be related independently of individual events, and OCEL 2.0 supports qualified event-object and object-object relations as well as time-varying object attributes. This is exactly the topology of a multi-agent research run: an agent action can simultaneously concern a checkpoint, file, Git commit, artifact, peer message and validation result. citeturn16academia48turn20search5

I would use the following canonical mapping.

| Input | Preserve as raw source | Canonical role | Typical joins |
|---|---|---|---|
| **ATIF** | original JSON/JSONL | semantic action/message sequence | session, trajectory, step, tool-call ID |
| **OCEL** | JSON/SQLite export | object/event relationship graph | event ID, object ID, qualifier |
| **Git** | bundle/repository + refs | workspace state transition | commit, parent, tree/blob |
| **Artifacts** | exact files | evidence/results state | SHA-256, producer event |
| **Verifier** | exact output | final or intermediate outcomes | trial, metric, checkpoint |
| **OTel** | OTLP/JSON/raw exporter data | latency, concurrency, call structure | trace ID, span ID, session |
| **A2A metadata** | task/ask/message structures | collaboration state | source agent, destination agent, artifact |
| **Experiment config** | immutable config | treatment/context | task, model, harness, timeout, policy |

Your current runner already enables Qwen telemetry, writes it to `/logs/agent/otel.json`, disables prompt telemetry and includes session IDs in telemetry. That means the proposed OTel layer is an extension of instrumentation you already have rather than a new dependency. The same script currently selects `deepseek-flash` by alias; for replay manifests, I would additionally record the provider's exact model revision/fingerprint whenever the provider exposes one, because an alias alone is not a reproducibility guarantee. fileciteturn0file0

### The bitemporal rule

Every canonical record should carry at least:

```text
event_id
source_type
source_id
event_type

event_time
observed_at
available_at
ingested_at

run_id
task_id
agent_id
trajectory_id
checkpoint_id

trace_id
span_id
git_commit

payload_hash
source_file_hash
schema_version
```

`event_time` means “when the source says this event happened.” `observed_at` means “when an independent collector observed it,” where such a clock exists. OpenTelemetry explicitly defines a source `Timestamp` and an `ObservedTimestamp` for logs, and its tracing API allows custom event timestamps that can be recorded out of timestamp order. citeturn20search0turn20search10

`available_at` is the new field that matters for historical replay:

> the earliest verified time at which this information could have influenced the policy being reconstructed.

For a terminal observation returned synchronously to the agent, that may be the tool-result delivery time. For an asynchronous artifact, it may be the durable-write time. For a later verifier report, it is not the event's logical timestamp if the agent had not yet received the report.

`derived_at`, stored on derived features, is different again: it is the date the offline analysis system computed the feature. It is audit metadata and should **not** determine historical eligibility.

For every feature \(f\) at checkpoint \(c\),

\[
availableAt(f)
=
\max_{s\in Dep(f)}availableAt(s)
\]

and

\[
I(f,c)
=
\mathbf 1[
availableAt(f)\le cutoff(c)
].
\]

The feature compiler must refuse to materialize a row when \(I(f,c)=0\).

This should be implemented as a database invariant or failing CI test, not a warning.

### Checkpoints must themselves be leakage-safe

A subtle failure mode is defining a checkpoint as “50% of the *eventual* run duration.” At historical time \(t\), eventual duration is future information.

Therefore safe prefix checkpoints should be based on quantities known in advance:

\[
25\%,50\%,75\%
\quad\text{of a fixed configured time budget}
\]

or fixed elapsed times such as 15/30/60 minutes, or fixed event counts such as 32/128/512 historically available events.

Retrospective “fraction of final duration” checkpoints can still be useful for descriptive process mining, but they must be marked `retrospective_only=true` and excluded from online-like prediction and causal replay.

### Deduplication must not destroy provenance

There are two different cases.

An **exact duplicate**, for example the same JSON event written twice by the same exporter, can be collapsed using canonical content hash plus identity fields.

A semantically identical action observed by ATIF, OTel and a terminal log should generally **not** be discarded as a duplicate. Those are independent observations of one latent event. Create:

```text
canonical_event
    ├── observed_by: ATIF row
    ├── observed_by: OTel span
    └── observed_by: terminal log
```

This lets you later detect inconsistencies between clocks or sources rather than silently erasing them.

Every raw input should get SHA-256, while each derived feature receives a reproducibility digest such as

\[
H_f=
SHA256(
extractor\_git\_sha
\Vert params
\Vert sorted(H_{dependencies})
).
\]

Hashes should be **provenance fields, never ordinary model inputs**. A raw artifact hash is nearly a unique run identifier and could let a model memorize outcomes.

### OCEL object model

I would define objects such as:

```text
Trial
Task
AgentSession
ModelCall
ToolCall
Checkpoint
File
GitCommit
Artifact
EvidenceItem
A2AMessage
A2ATask
VerifierResult
```

and events such as:

```text
agent_step
model_request
model_response
tool_start
tool_finish
file_read
file_write
commit
test_run
evidence_verify
gate_block
a2a_send
a2a_receive
consensus_update
checkpoint
```

The OCEL relationships can then carry qualifiers such as `produced`, `consumed`, `modified`, `verified`, `requested_by`, `assigned_to`, `supports`, `contradicts`, or `derived_from`. OCEL 2.0's support for qualified relationships and object-object links is exactly what makes this representation preferable to forcing everything into a single case identifier. citeturn20search8turn16academia48

This leads to a useful principle:

\[
\boxed{\text{ATIF is the sequence; OCEL is the topology.}}
\]

Neither should replace the other.

## Manual priors and automated feature engineering

The manual/AutoFE split should be explicit in both storage and evaluation:

```text
M__...  manually specified prior features
A__...  automatically generated features
L__...  latent-state features
G__...  OCEL graph features
```

This allows four mandatory ablations:

\[
M,\quad A,\quad M+A,\quad M+A+L+G.
\]

That matters because an apparently strong AutoFE model can simply exploit task identity, run-specific artifacts or accidental future information. AutoFE needs to demonstrate **incremental out-of-task value**, not merely higher in-sample fit.

### Feature families

| Family | Manual priors | Automated expansions | Why it matters |
|---|---|---|---|
| **Errors/recovery** | error count, failure rate, retry count, recovery latency | burstiness, rolling slope, inter-error intervals, error n-grams | distinguishes transient failure from deteriorating trajectory |
| **Evidence integrity** | gate block count, hash mismatch, verified-artifact fraction | sequences of block→repair→verify, integrity velocity | operationalizes whether conclusions rest on verified evidence |
| **Consensus/A2A** | disagreement count, unresolved asks, consensus reached, time to consensus | interaction motifs, response-latency trends, peer-adoption paths | tests whether collaboration helps rather than just converges |
| **Git/workspace** | commits, diff size, changed files, revert count | churn acceleration, change entropy, branch-distance trends | measures research/implementation instability |
| **Validation** | tests run, independent validation count, candidate margin | validation sequences, diversity indices, test→revision motifs | distinguishes implementation from actual falsification |
| **Progress/obligations** | unresolved tasks, artifact completeness | obligation burn-down slope, obligations/minute remaining | captures “too much scientific work left for remaining budget” |
| **Cost/cache** | prompt, completion, cached tokens, cost, cache fraction | rolling cache trend, tokens/outcome-progress, cost acceleration | supports cost-performance attribution |
| **Latency/concurrency** | model latency, tool latency, active-agent count, idle fraction | critical-path estimates, queue bursts, overlap ratios | explains wall-clock efficiency |
| **Sequence** | selected manually meaningful transitions | n-grams, subsequences, transition entropy | captures order unavailable to static counts |
| **OCEL graph** | agent/artifact degrees | typed motifs, path counts, component dynamics | captures multi-object coordination structure |
| **Latent research state** | none | HMM/HSMM state occupancy and dwell time | discovers recurring phases without manual labels |

Several priors come directly from hypotheses your previous data have made plausible rather than proven: consensus should be represented separately from evidence quality; remaining time should be normalized by unresolved obligations rather than considered alone; and local validation strength should be separate from final hidden-test success. The purpose of the manual layer is to ensure those hypotheses remain visible even if AutoFE fails to rediscover them.

For cache accounting, ATIF's current RFC defines cached tokens as a subset of prompt tokens and supports per-step and final cost metrics; it also warns that provider-specific cost factors may require extra fields. Therefore I would store provider-reported `cost_usd` as historical ground truth when available and compute a separate `cache_fraction = cached_tokens / prompt_tokens` rather than reconstructing historical dollars from today's pricing. citeturn15search0

### Multi-resolution temporal AutoFE

Do not choose one binning resolution. Agent behavior exists on several timescales.

I would initially materialize:

| View | Proposed windows |
|---|---|
| recent wall clock | 30 s, 2 min, 10 min |
| recent event history | last 8, 32, 128 events |
| since checkpoint/start | cumulative |
| configured-budget position | 5% bins of *known budget* |
| phase-relative | since most recent detected state transition |

For numerical channels \(x(t)\), generate:

\[
\{
count,\ mean,\ std,\ min,\ max,\ q_{10},q_{50},q_{90},
slope,\ EWMA,\Delta slope,
time\_since\_last,\ burstiness
\}.
\]

tsfresh demonstrates the general feasibility of systematically expanding time-series statistics—it combines 63 characterization methods and hundreds of candidate features—although in this application I would use a restricted calculator whitelist rather than its full default feature universe. citeturn17search0

The reason is statistical rather than computational: hundreds of prefixes from ten underlying trials do **not** constitute hundreds of independent experiments.

### Sequence-pattern features

At each cutoff, convert actions to a controlled event alphabet such as:

```text
SEARCH
READ
MODEL_CALL
RUN_CODE
TEST
FAIL
RETRY
EDIT
COMMIT
ASK_PEER
RECEIVE_PEER
VERIFY
GATE_BLOCK
CONSENSUS
```

Then extract:

\[
\text{2--5 grams},
\quad
\text{transition probabilities},
\quad
H(\text{next action}),
\quad
\text{frequent subsequences},
\quad
\text{time-weighted motifs}.
\]

Examples that might prove discriminative are:

```text
TEST → FAIL → EDIT → TEST
ASK_PEER → RECEIVE_PEER → VERIFY
GATE_BLOCK → REPAIR → VERIFY
SEARCH → SEARCH → SEARCH → no execution
EDIT → EDIT → EDIT → timeout
```

All sequence vocabularies and frequency thresholds must be learned on training folds only.

### Relational and graph AutoFE

Featuretools' Deep Feature Synthesis is useful conceptually because it composes aggregation and transformation primitives across relational and temporal tables. citeturn17search13 For this project I would apply the same idea to a **whitelisted relation graph**, for example:

\[
Agent
\rightarrow ToolCall
\rightarrow Artifact
\rightarrow Verifier
\]

or

\[
Agent_A
\rightarrow Message
\rightarrow Agent_B
\rightarrow Commit.
\]

Examples include:

\[
\#Artifacts(agent),
\]

\[
\operatorname{mean}(
verification\_latency(
artifacts(agent)
)),
\]

\[
\frac{
\#\text{peer artifacts independently verified}
}{
\#\text{peer artifacts consumed}
}.
\]

On the OCEL graph, add typed:

\[
degree,\quad
two\text{-}hop\ path\ count,\quad
motif\ count,\quad
component\ size,\quad
bridge\ count,
\]

and their changes over time.

A particularly interesting A2A feature is an **independence ratio**:

\[
I_{\text{evidence}}
=
\frac{
\text{claims supported by independently produced evidence}
}{
\text{claims supported by any evidence}
}.
\]

That is a better candidate than raw agreement count for distinguishing genuine corroboration from correlated consensus.

### OpenFE and candidate pruning

OpenFE's central idea is relevant here: candidate generation creates an enormous feature space, so it uses feature-based candidate evaluation plus coarse-to-fine pruning rather than fitting every possible transformed feature exhaustively. citeturn16academia49

I would constrain it much more tightly:

\[
\text{operator depth}\le 2,
\]

initial candidate budget roughly

\[
2{,}000\text{--}20{,}000,
\]

and final AutoFE set

\[
K\le
\min(200,\lfloor N_{\text{independent train}}/5\rfloor)
\]

for the confirmatory tabular analysis.

The \(N/5\) cap is an engineering regularization heuristic, not a theorem. Its purpose is to stop AutoFE from creating a superficially precise but completely unstable explanation from a small number of independent runs.

Target-dependent OpenFE selection must be rerun inside every inner training fold. The same rule applies to tsfresh relevance selection.

### Latent HMM/HSMM states

Your “computational history” hypothesis predicts a small number of recurring abstract phases beneath raw actions. That is exactly where latent state models become useful.

I would fit a 4–8 state HMM/HSMM on low-dimensional emissions such as:

\[
[
error\_rate,
edit\_rate,
test\_rate,
search\_rate,
a2a\_rate,
evidence\_rate,
commit\_rate,
cost\_rate
].
\]

Candidate states might later *look like* “exploration,” “construction,” “validation,” “recovery,” or “convergence,” but they should initially remain unlabeled.

HSMM is preferable as an experimental arm because unlike an ordinary HMM it can explicitly model non-geometric state durations; explicit-duration semi-Markov models were developed precisely to represent such dwell-time structure. citeturn18search1

Features then become:

\[
P(S_t=k),
\quad
\text{time in state }k,
\quad
\text{number of transitions},
\]

\[
\text{mean dwell time},
\quad
P(S_t\ne S_{t-\Delta}),
\quad
\text{state-transition entropy}.
\]

The entire latent model, including the number and identity of states, must be fit using training trajectories only. Otherwise the state abstraction itself becomes a leakage channel.

### Hard exclusions

The AutoFE engine should never receive unrestricted raw columns.

The following should be tagged `PROVENANCE_ONLY` or `LABEL_ONLY`:

| Field | Reason |
|---|---|
| artifact SHA/hash | nearly unique run identifier |
| Git object hash | potential run memorization |
| UUID/session ID | direct identity leakage |
| final verifier result | target leakage |
| post-cut artifact properties | future leakage |
| total eventual duration | future leakage |
| final consensus/result file | future leakage before creation |
| absolute filesystem paths | possible task/run identity |
| arbitrary timestamps | calendar/task drift memorization |

OpenFE should operate on a **safe typed feature view**, never the raw lake.

That separation is one of the strongest protections against an AutoFE system “discovering” a perfect but meaningless historical predictor.

## Predictive and causal attribution models

Predictive modeling and causal attribution need to be separate products.

A predictive model estimates:

\[
P(Y\mid H_{\le c}).
\]

A causal model asks:

\[
E[Y\mid do(A=a),H_{\le c}]
-
E[Y\mid do(A=a'),H_{\le c}].
\]

Those are not interchangeable.

SHAP can explain why a GBDT assigned a high predicted failure probability, but the SHAP value of `error_count=8` does **not** imply that artificially removing eight error records would improve success. SHAP was introduced as an additive feature-attribution framework for model predictions, not as an estimator of intervention effects. citeturn13search1

### Predictive model ladder

| Model | Role | Advantages | Main risk | Recommendation |
|---|---|---|---|---|
| task-conditioned mean/prevalence | null baseline | impossible to overinterpret | no trajectory information | mandatory |
| sparse logistic/linear | semantic baseline | coefficients, regularization, stable | misses nonlinear interactions | mandatory |
| GBDT/XGBoost + SHAP | **primary predictor** | nonlinear, mixed tabular features, interactions | correlated-feature attribution instability | mandatory |
| HMM/HSMM + sparse outcome model | structured-history model | interpretable abstract phases | state-model sensitivity | mandatory experimental arm |
| LSTM | raw-sequence comparison | temporal recurrence | data hungry | comparison |
| Transformer | raw-sequence comparison | long-range interactions, parallel training | highest capacity/overfit risk | comparison |

XGBoost is a good primary candidate because gradient-boosted trees naturally handle nonlinear tabular interactions and sparse inputs, while retaining a mature interpretation route through SHAP. citeturn14academia24turn13search1 LSTM and Transformer provide qualitatively different sequence-model baselines. citeturn18search0turn19search0

I would not make LSTM/Transformer confirmatory primary models until you have roughly **thousands of independent trajectories**, for example \(\gtrsim5{,}000\), across several task families. That is an engineering guardrail rather than a literature-derived sample-complexity theorem. Fifty thousand prefix rows created from 500 runs still contain only about 500 independent run outcomes.

The outer evaluation split must therefore be grouped at the run/task level.

### Primary predictive targets

The offline model should predict several outcomes separately rather than collapsing everything into one utility:

\[
Y_{\mathrm{success}}\in\{0,1\},
\]

\[
Y_{\mathrm{quality}}\in[0,1],
\]

\[
Y_{\mathrm{time}}=\text{remaining wall-clock time},
\]

\[
Y_{\mathrm{cost}}=\text{remaining dollar/token cost}.
\]

A composite utility can be computed afterward:

\[
U =
Y_{\mathrm{quality}}
-\lambda_tY_{\mathrm{time}}
-\lambda_cY_{\mathrm{cost}},
\]

but accuracy should remain the principal endpoint, consistent with your actual optimization priority. Otherwise a weight choice can conceal a scientifically bad but cheap trajectory.

### Randomized checkpoint-fork attribution

This should be the gold standard.

At checkpoint \(c\), create one immutable replay capsule:

```text
filesystem snapshot
Git commit/tree
artifacts and hashes
agent-visible context
ATIF prefix
A2A state
tool state
network replay cassette
model/harness configuration
randomization block
```

Then randomly assign:

\[
A=0:\text{reference policy}
\]

versus

\[
A=1:\text{specific intervention}.
\]

Examples of useful treatments are narrow, manipulable changes:

```text
search-before-build off vs on
single-model choice vs ensemble retention
ask-peer now vs continue independently
extra validation budget vs no extra budget
evidence gate strict vs reference rule
cache strategy A vs B
```

Each intervention should modify **exactly one declared policy lever**.

The estimand becomes:

\[
ATE_c
=
E[Y_c(1)-Y_c(0)].
\]

For binary success:

\[
\Delta_{\mathrm{success}}
=
P(Y=1\mid do(A=1))
-
P(Y=1\mid do(A=0)).
\]

For wall time and cost, retain natural units.

Because the forks originate from the same checkpoint, task history and much of initial difficulty are automatically controlled. This is the causal equivalent of the historical matching intuition you were developing earlier.

### Replay nondeterminism

To make this meaningful, the future environment after a fork must be controlled.

Live internet responses are especially problematic because the A and B branches may see different external states. For offline replay I recommend a content-addressed network cassette:

```text
request canonical hash
response body hash
response headers
retrieval timestamp
source URL identifier
```

with the fork reading recorded responses unless the intervention explicitly concerns network access.

The same problem applies to mutable package registries, API aliases and model providers. A historical fork whose model implementation can no longer be reproduced is not the exact historical counterfactual. It should be labeled:

```text
replay_equivalence = degraded
```

and interpreted as:

> “effect of this intervention when replaying this historical state under the currently pinned runtime,”

not as the exact alternate history of the original run.

### Doubly robust observational attribution

For binary policy-level treatment \(A\), pre-treatment state \(X\), and outcome \(Y\), estimate:

\[
\hat m_a(X)
=
E[Y\mid X,A=a],
\]

and

\[
\hat e(X)
=
P(A=1\mid X).
\]

Then use the AIPW/DR estimator

\[
\hat\tau
=
\frac1N
\sum_{i=1}^{N}
\left[
\hat m_1(X_i)-\hat m_0(X_i)
+
\frac{A_i(Y_i-\hat m_1(X_i))}{\hat e(X_i)}
-
\frac{(1-A_i)(Y_i-\hat m_0(X_i))}
{1-\hat e(X_i)}
\right].
\]

The foundational doubly robust result combines a reward/outcome model with a behavior-policy model; later work extends DR to sequential off-policy value estimation. citeturn22academia36turn13search0

With flexible GBDT/AutoFE nuisance models, use **cross-fitting** so an observation is not evaluated using nuisance predictions trained on itself. Double/debiased machine learning uses sample splitting/cross-fitting and orthogonal scores specifically to reduce the first-order impact of nuisance-model estimation error. citeturn18search5

Critically, only **pre-treatment** features belong in \(X\).

For:

\[
X\rightarrow A\rightarrow M\rightarrow Y,
\]

a post-action test result \(M\) is a mediator, not an ordinary confounder. Including it indiscriminately in the propensity/outcome adjustment can change the estimand or introduce bias.

The causal DAG itself should therefore be a preregistered artifact.

### Exact propensities are worth instrumenting

For unrestricted historical LLM behavior, one rarely possesses a trustworthy macro-action probability

\[
P(A=\text{“run another validation”}\mid X).
\]

Token log probabilities are not automatically the probability of a semantically aggregated research action.

Therefore the next harness version should insert a small **meta-decision router**:

```text
decision_type = "independent_validation"
available_actions = [continue, validate]
assignment_probability = [0.8, 0.2]
chosen_action = validate
```

or an adaptive randomized policy with a known probability.

Then OPE has an actual logging policy rather than a reconstructed one.

This is much more valuable scientifically than trying to estimate propensities for every unconstrained terminal command.

Open Bandit Pipeline is useful as a reference implementation because it provides reusable interfaces for logged-bandit data, IPW, direct-method and DR OPE experiments. citeturn23search1

### Causal-method comparison

| Method | Best use | Identification requirement | Main weakness | Status in pipeline |
|---|---|---|---|---|
| **Paired checkpoint-fork A/B** | manipulable agent-policy choices | randomized intervention, equivalent replay | expensive | **primary causal evidence** |
| **AIPW / DR** | one policy choice at checkpoint | no unmeasured confounding + overlap, or randomized assignment | hidden confounding | primary observational estimator |
| **Sequential DR OPE** | sequence of predefined decisions | sequential coverage and behavior propensities | variance explodes with poor support | secondary |
| **IPW** | simple OPE diagnostic | correct propensity + support | high variance | sensitivity baseline |
| **Outcome model / g-formula** | well-covered simple setting | correct conditional outcome model | model bias | sensitivity baseline |
| **Synthetic control** | global policy/harness rollout | credible untreated donor series and pre-period fit | poor fit to local decisions | cohort-level only |

Synthetic control is appropriate, for example, if at some date you enable `search-before-build` for a whole task family and have comparable untreated task cohorts with a long pre-intervention history. It was developed for comparative settings in which a treated aggregate unit is compared with a weighted combination of untreated units. citeturn22search1turn22search4

It is **not** the method I would use for “would this agent at checkpoint 57 have benefited from one more test?” That is a checkpoint-fork problem.

DoWhy is useful around these estimators because its workflow makes the causal graph, identification assumptions, estimation, and refutation/sensitivity steps explicit rather than treating causal inference as a model-fitting problem. citeturn21academia24turn23search0

## Validation and numeric success criteria

The most dangerous failure mode is obtaining a very accurate model of the **retrospective archive** that has learned something impossible to know at decision time.

Validation therefore begins with temporal and provenance integrity, not AUPRC.

### Split strategy

Use three nested boundaries.

First, no prefixes from one run may cross train/test boundaries.

Second, the confirmatory outer test should contain entire unseen task families wherever possible—for your data this eventually means splits conceptually like “train without Microarch, test Microarch” and vice versa, not only random run splitting.

Third, reserve a chronological holdout so the system is tested against model/harness/task drift.

A useful structure is:

\[
\text{outer: task family/date}
\]

\[
\text{middle: independent run}
\]

\[
\text{inner: AutoFE/model tuning}.
\]

Every one of these operations belongs inside the training side:

```text
OpenFE candidate selection
tsfresh relevance filtering
sequence vocabulary mining
HMM/HSMM fitting
feature normalization
feature selection
hyperparameter tuning
calibration fitting
```

The final holdout should remain sealed until the entire analysis specification is frozen. Preregistration is specifically intended to separate exploratory hypothesis generation from confirmatory testing, including the possibility of exploring one partition and sealing another for later confirmation. citeturn22search0

### Predictive metrics

For binary success with prevalence \(\pi\), report AUPRC and define a prevalence-adjusted PR skill:

\[
S_{PR}
=
\frac{AUPRC-\pi}{1-\pi}.
\]

A value of zero means no improvement over random/prevalence ranking; one is perfect.

PR-based evaluation is especially informative under class imbalance. citeturn19search2

For probabilistic accuracy:

\[
BS
=
\frac1N\sum_i(p_i-y_i)^2
\]

and

\[
BSS
=
1-\frac{BS}{BS_{\mathrm{null}}}.
\]

Brier's score was introduced specifically for evaluating probability forecasts. citeturn19search1

For normalized continuous final score:

\[
MAE
=
\frac1N\sum_i|\hat y_i-y_i|.
\]

For uncertainty intervals, report empirical coverage, not only mean interval width.

### Proposed confirmatory thresholds

These values should be frozen after a pilot and **before** opening the final holdout.

| Quantity | Pass | Warning/failure interpretation |
|---|---:|---|
| `availableAt` rule violations | **0** | any violation invalidates corresponding feature build |
| raw provenance hash coverage | **100%** | incomplete audit chain |
| feature rerun hash agreement | **100%** | extractor not deterministic/reproducible |
| binary Brier skill | ≥ **0.15** | below: weak probability value |
| PR skill | ≥ **0.20** | below: weak ranking value |
| ECE | ≤ **0.05** | above: probabilities not decision-ready |
| calibration slope | **0.8–1.2** | outside: systematic over/under-confidence |
| normalized verifier MAE | ≤ **0.10** | above: insufficient outcome resolution |
| MAE vs task-only baseline | ≥ **20% reduction** | otherwise trajectory adds little information |
| combined AutoFE AUPRC gain over manual | ≥ **0.03 absolute** | below: AutoFE complexity not justified |
| or AutoFE MAE reduction | ≥ **10% relative** | same decision |
| leave-one-task-family performance loss | ≤ **20% relative** | above: task-specific, not general history model |
| top-feature sign/rank stability | ≥ **80% / Jaccard ≥0.60** | explanation unstable |
| nominal 90% predictive interval | **87–93% coverage** | uncertainty model fails calibration |
| known-effect attribution bias | ≤ **2 pp** | causal pipeline insufficient |
| nominal 95% causal CI coverage | **92–98%** | inference miscalibrated |
| real causal CI half-width | ≤ **5 pp** | too imprecise for 5–10 pp decisions |

These are **project acceptance criteria**, not claims that the literature defines 0.05 ECE or 0.15 Brier skill as universal boundaries.

### Mandatory leakage tests

A reliable replay system should actively try to break itself.

The first test is deterministic:

\[
\max availableAt(dependencies)\le cutoff
\]

must hold on **every** feature row.

Second, inject deliberately forbidden fields:

```text
final_reward
final_artifact_hash
post_cut_error_count
eventual_wall_clock_duration
```

and verify that the feature compiler rejects all of them. Required rejection rate:

\[
\boxed{100\%}.
\]

Third, generate placebo features from random hash suffixes and unrelated IDs. They should not show stable predictive importance across folds.

Fourth, shift a feature stream one checkpoint into the future. A properly enforced availability layer should reject it before training; if it enters the matrix, the pipeline has failed even if predictive performance looks excellent.

### Causal falsification

For causal estimates, run:

\[
\text{placebo treatment}
\]

by permuting intervention assignments within randomization blocks,

\[
\text{placebo outcome}
\]

using an outcome that the intervention cannot plausibly affect,

and

\[
\text{negative-control feature}
\]

that occurs before neither treatment nor outcome in the relevant causal path.

DoWhy explicitly treats placebo, bootstrap and unobserved-confounding sensitivity checks as part of a causal workflow rather than as optional presentation extras. citeturn21academia24

A preregistered placebo gate could require:

\[
0\in CI_{95\%}(\hat\tau_{\mathrm{placebo}})
\]

and, once sample sizes are sufficiently powered,

\[
|\hat\tau_{\mathrm{placebo}}|\le0.02
\]

for binary success.

### OPE overlap diagnostics

For weights \(w_i\), compute:

\[
ESS
=
\frac{(\sum_i w_i)^2}{\sum_iw_i^2}.
\]

I would refuse a primary DR/OPE claim when:

\[
ESS/N < 0.30,
\]

or when the top 1% of observations contributes more than 20% of total weight mass.

For binary treatments, also flag:

\[
\hat e(X)<0.05
\quad\text{or}\quad
\hat e(X)>0.95.
\]

These are intentionally conservative engineering diagnostics rather than mathematical identification thresholds. Poor action support is a central difficulty in off-policy evaluation because a target policy cannot be reliably evaluated in regions scarcely represented by the logged policy. DR reduces some estimator fragility, but it does not magically create missing support. citeturn22academia36turn13search0

When these gates fail, the correct result is:

```text
OPE_STATUS = INSUFFICIENT_SUPPORT
```

not a more sophisticated estimator.

### Counterfactual ground-truth tests

Before trusting attribution of scientifically meaningful actions, create causal tests whose true effects are known.

One simple systems-level test is an injected deterministic delay:

\[
do(delay=+10s).
\]

The wall-clock estimator should recover approximately +10 s.

A semi-synthetic binary test can inject a known

\[
\Delta=+0.10
\]

outcome effect conditional on a recorded treatment and verify that AIPW/DR recovers the effect with low bias and nominal interval coverage.

For the causal engine I would require over repeated semi-synthetic experiments:

\[
|\operatorname{bias}|\le0.02
\]

and

\[
0.92
\le
\operatorname{coverage}_{95\%}
\le
0.98.
\]

Only after that would I treat estimated effects of “search,” “consensus,” “validation,” or “evidence gating” as quantitative evidence.

## Statistical power and required sample sizes

This is where the design strongly favors paired replay.

For independent binary outcomes with baseline \(p_0\), treatment outcome \(p_1\), two-sided type-I error \(\alpha\), and power \(1-\beta\), a standard normal approximation gives:

\[
n_{\text{per arm}}
\approx
\frac{
\left[
z_{1-\alpha/2}
\sqrt{2\bar p(1-\bar p)}
+
z_{1-\beta}
\sqrt{
p_0(1-p_0)+p_1(1-p_1)
}
\right]^2
}{
(p_1-p_0)^2
},
\]

where

\[
\bar p=(p_0+p_1)/2.
\]

Using \(\alpha=0.05\):

| Baseline → treatment | Absolute effect | 80% power | 90% power |
|---|---:|---:|---:|
| 40% → 45% | +5 pp | **1,534/arm** | **2,053/arm** |
| 40% → 50% | +10 pp | **388/arm** | **519/arm** |
| 50% → 55% | +5 pp | **1,565/arm** | **2,095/arm** |
| 50% → 60% | +10 pp | **388/arm** | **519/arm** |
| 70% → 75% | +5 pp | **1,251/arm** | **1,674/arm** |
| 70% → 80% | +10 pp | **294/arm** | **392/arm** |

The \(1/\Delta^2\) scaling is the practical lesson. Halving a detectable effect from 10 pp to 5 pp costs about four times as many observations.

### Paired checkpoint forks

Let each historical checkpoint produce both an A and B fork. Define

\[
D_i=Y_i(B)-Y_i(A)\in\{-1,0,+1\}.
\]

Let \(d\) be the expected fraction of pairs whose outcomes are discordant. Then approximately:

\[
Var(D)
=
d-\Delta^2,
\]

and a planning approximation is:

\[
n_{\mathrm{pairs}}
\approx
\frac{
(z_{1-\alpha/2}+z_{1-\beta})^2
(d-\Delta^2)
}{
\Delta^2
}.
\]

This should eventually be refined with exact McNemar or simulation-based power calculations using your empirically observed discordance, but it is very useful for planning.

At \(\alpha=.05\):

| Discordant-pair rate | Effect | 80% power | 90% power |
|---:|---:|---:|---:|
| 20% | +5 pp | **621 pairs** | **831 pairs** |
| 20% | +10 pp | **150 pairs** | **200 pairs** |
| 30% | +5 pp | **935 pairs** | **1,251 pairs** |
| 30% | +10 pp | **228 pairs** | **305 pairs** |
| 40% | +5 pp | **1,248 pairs** | **1,671 pairs** |
| 40% | +10 pp | **307 pairs** | **410 pairs** |

This quantitatively supports a design decision that follows from your historical-analysis hypothesis:

\[
\boxed{
\text{same-history counterfactual pairs are substantially more valuable than unmatched extra runs}
}
\]

when outcomes from the paired forks are strongly correlated.

### What does not count as extra sample size

Suppose you have 100 runs and extract checkpoints at 10%, 20%, …, 90%.

You have:

\[
900\ \text{prefix rows}
\]

but still approximately:

\[
100\ \text{independent final outcomes}.
\]

Treating 900 prefixes as \(N=900\) would severely understate uncertainty.

The same applies to two agents inside one shared environment: they provide valuable within-run observations, but not two independent task outcomes when their trajectories interact.

Uncertainty should therefore be clustered or bootstrapped by at least:

```text
source trial
checkpoint fork family
task
```

depending on the estimand.

### Multiplicity matters

If four separate interventions are all treated as primary hypotheses and you naïvely Bonferroni-adjust to

\[
\alpha=0.0125,
\]

the independent 50%→60%, 80%-power example rises from approximately:

\[
388
\]

to roughly:

\[
551
\]

runs per arm.

So the confirmatory program should pre-register **one or at most a very small number of primary interventions**, and leave the rest exploratory.

### How I would interpret your present dataset scale

The batches we have been analyzing are currently on the scale of **tens, not hundreds or thousands, of independent full runs**. At that scale, they are already very useful for:

\[
\text{schema discovery},
\quad
\text{leakage detection},
\quad
\text{feature hypothesis generation},
\]

\[
\text{latent-state exploration},
\quad
\text{effect-size variance estimation},
\]

and designing interventions.

They are **not yet large enough** for a stable general claim such as:

> “this trajectory feature increases agent success by 5 percentage points across tasks.”

That is not a failure of the project. It simply tells us what the current data are scientifically good for.

The next data should be collected **to answer predeclared causal questions**, rather than merely increasing raw log volume.

## Implementation protocol and deliverables

The pipeline can be implemented as a deterministic sequence whose output at every stage has an immutable hash.

| Order | Operation | Main implementation | Required deliverable | Hard gate |
|---:|---|---|---|---|
| 1 | freeze research specification | YAML/JSON + Git | `analysis_plan.yaml` | hash frozen before confirmatory outcomes |
| 2 | manifest raw archive | SHA-256 scanner | `raw_manifest.parquet` | 100% file coverage |
| 3 | parse ATIF/OTel/Git/verifier | Pydantic/Polars | source-normalized tables | schema validation |
| 4 | create canonical event layer | DuckDB/Parquet | `events.parquet` | unique IDs + provenance |
| 5 | build OCEL graph | OCEL 2.0/PM4Py-compatible tables | OCEL JSON/SQLite | relation validation |
| 6 | derive `availableAt` | source-specific rules | `availability.parquet` | zero unresolved critical events |
| 7 | construct checkpoint prefixes | deterministic compiler | `checkpoints.parquet` | zero future dependencies |
| 8 | generate manual features | versioned Python | `features_manual.parquet` | deterministic hash |
| 9 | generate AutoFE | tsfresh/Featuretools/OpenFE | `features_auto.parquet` | training-fold-only selection |
| 10 | learn latent states | HMM/HSMM | state posterior/features | training-only fit |
| 11 | fit predictive models | sparse + XGBoost + sequence arms | calibrated models | outer-group evaluation |
| 12 | generate replay interventions | checkpoint fork runner | paired A/B outcomes | assignment log required |
| 13 | estimate causal effects | paired test + DR/OPE | `effects.parquet` | overlap/CI gates |
| 14 | run falsification | placebo/leakage/stability suite | `robustness.json` | all hard tests pass |
| 15 | seal result bundle | content-addressed package | report + manifests + model cards | reproducible from raw hashes |

### Recommended technical stack

The storage layer should be deliberately boring: **Parquet + DuckDB** for immutable analytical tables, with Polars or Pandas for transformation. Raw source files remain untouched.

For ATIF, use Harbor's reference schema/validator rather than maintaining a parallel interpretation; Harbor's active RFC describes a Pydantic reference implementation and trajectory validator. citeturn15search0

For object-centric analysis, use OCEL 2.0-compatible tables and PM4Py where its existing process-mining operations are useful; the formal OCEL specification supports JSON, XML and relational/SQLite representations. citeturn16academia48turn20search5

For AutoFE:

| Need | Recommended tool/style |
|---|---|
| time-series statistics | **tsfresh**, curated calculator subset |
| relational transforms | **Featuretools / DFS** |
| wide tabular interaction search | **OpenFE**, constrained operators |
| graph features | NetworkX/igraph-style typed graph transforms |
| custom sequence motifs | native Python/Rust/Polars extractor |
| latent states | custom HMM/explicit-duration HSMM implementation |

tsfresh, Featuretools and OpenFE represent three complementary AutoFE styles rather than interchangeable packages: statistical time-series characterization, relational feature synthesis and wide tabular candidate generation/pruning, respectively. citeturn17search0turn17search13turn16academia49

For prediction:

```text
scikit-learn sparse logistic/linear
XGBoost
SHAP
PyTorch for LSTM/Transformer comparisons
```

For causal analysis:

```text
DoWhy for DAG / identify / refute workflow
EconML-style DML/AIPW implementations where appropriate
Open Bandit Pipeline as OPE reference/test harness
statsmodels/scipy for paired tests and basic inference
```

DoWhy is explicitly organized around model → identify → estimate → refute, and its current ecosystem interoperates with more specialized treatment-effect estimators; OBP provides concrete implementations of direct, IPW and DR-style OPE workflows. citeturn23search0turn23search1

### Pre-registration artifact

I would make `analysis_plan.yaml` contain at least:

```yaml
estimands:
  primary:
    - intervention: search_before_build
      outcome: verifier_success
      estimand: paired_ATE

checkpoints:
  policy: fixed_budget_fraction
  values: [0.25, 0.50, 0.75]

feature_families:
  manual: frozen
  auto: nested_training_only
  latent_states: [4, 6, 8]

primary_predictor:
  type: xgboost

causal_estimators:
  primary: paired_randomized
  secondary: crossfit_aipw

metrics:
  prediction:
    - auprc
    - brier
    - calibration
  causal:
    - ate
    - ci95
    - ess

failure_gates:
  availability_violations: 0
  provenance_coverage: 1.0
  min_ess_ratio: 0.30
```

Then hash this file before opening the confirmatory holdout. Preregistration is particularly relevant here because AutoFE gives the analyst enormous degrees of freedom; separating exploration from confirmation prevents a post hoc discovered pattern from being presented as if it were prospectively predicted. citeturn22search0

### Feature registry

Every feature should be described by a machine-readable contract:

```text
feature_id
feature_family
description
inputs
window
aggregation
historical_availability_rule
extractor_version
extractor_git_sha
parameters_hash
causal_role
    PRETREATMENT | TREATMENT | MEDIATOR | OUTCOME | PROVENANCE
```

That last field is crucial.

The same variable can be legal for prediction yet illegal for causal adjustment depending on when it occurs relative to treatment.

### Model comparison report

Every experiment should produce the same ablation table:

| Feature/model system | AUPRC | PR skill | Brier | ECE | MAE | held-out-task Δ | feature stability |
|---|---:|---:|---:|---:|---:|---:|---:|
| task-only null | | | | | | | |
| manual + sparse | | | | | | | |
| AutoFE + sparse | | | | | | | |
| manual + GBDT | | | | | | | |
| AutoFE + GBDT | | | | | | | |
| manual + AutoFE + GBDT | | | | | | | |
| + HMM/HSMM | | | | | | | |
| LSTM raw sequence | | | | | | | |
| Transformer raw sequence | | | | | | | |

This makes the central scientific question measurable:

\[
\Delta_{\mathrm{AutoFE}}
=
Score(M+A)-Score(M).
\]

My proposed decision rule is:

\[
\Delta AUPRC\ge0.03
\]

or

\[
\frac{MAE_M-MAE_{M+A}}{MAE_M}\ge0.10
\]

**and** no material cross-task stability deterioration.

Otherwise AutoFE has not earned its complexity.

### Attribution report

Likewise each intervention gets a standard causal table:

| Intervention | N independent pairs | A success | B success | Δ success | 95% CI | Δ time | Δ cost | ESS/N | placebo pass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| search-before-build | | | | | | | | | |
| extra validation | | | | | | | | | |
| peer consultation | | | | | | | | | |
| model ensemble | | | | | | | | | |

SHAP should appear in a separate **predictive attribution** table. It should never be merged into the causal-effect column.

That distinction gives you two complementary answers:

\[
\text{SHAP: “what historical signals made failure predictable?”}
\]

versus

\[
\text{ATE: “what manipulable decision would actually have changed success?”}.
\]

### What I expect the first serious study to show

The first confirmatory study should not aim to discover a universal “agent intelligence score.” It should test narrower propositions.

A realistic first target would be to establish that by the midpoint of a run,

\[
H_{\le0.5T}
\]

contains enough stable structure to predict final scientific success better than task identity alone; determine whether AutoFE adds information beyond your manual priors; and causally test one manipulable action such as an extra validation/search policy.

A good first-stage result would look approximately like:

\[
BSS\ge0.15,
\qquad
S_{PR}\ge0.20,
\]

\[
\Delta AUPRC_{\text{AutoFE}}\ge0.03,
\]

while preserving:

\[
ECE\le0.05
\]

and:

\[
\text{held-out-task loss}\le20\%.
\]

The causal side should first prove itself on known-effect interventions with ≤2 pp bias and approximately nominal CI coverage, then attempt a 10 pp real effect with roughly 150–300 paired checkpoint forks if observed pair discordance is favorable. A 5 pp claim should be treated as a later, substantially larger experiment.

The resulting research program is therefore not:

\[
\text{logs}\rightarrow\text{feature importance}.
\]

It is:

\[
\boxed{
\begin{aligned}
&\text{immutable raw historical record}\\
&\downarrow\\
&\text{bitemporally valid prefix state}\\
&\downarrow\\
&\text{manual priors + leakage-safe AutoFE + latent process state}\\
&\downarrow\\
&\text{calibrated predictive model}\\
&\downarrow\\
&\text{explicit manipulable intervention}\\
&\downarrow\\
&\text{paired replay / DR counterfactual}\\
&\downarrow\\
&\text{effect estimate + CI + robustness evidence}.
\end{aligned}
}
\]

That design fits the empirical lesson from the trajectory work so far particularly well: **process completion, agreement, evidence handling, scientific quality and eventual action value are distinct latent quantities.** An offline replay system should model those distinctions instead of collapsing them into “progress.”

More fundamentally, it operationalizes your computational-history analogy. The archive is not merely a collection of transcripts; it becomes a temporally constrained historical record from which one reconstructs what was knowable, infers abstract states, compares alternative decisions from matched historical moments, and quantifies which interventions survive counterfactual testing. That is a much stronger scientific object than ordinary trajectory analytics.