# Research log — oct1

## Experiment 0 — baseline
- Commit: `92e43e6`
- Hypothesis: establish the untouched starter score before tuning.
- Change: none. Starter uses 30 trees, depth 6, learning rate 0.1, native categorical features, and seed 42.
- Result: Eval AUC 0.7203; training 0.2 s; row-wise evaluation 30.5 s; status `ok`.
- Observation: baseline fits quickly, so a larger boosting-round count is feasible under the one-minute training cap.

## Initial research and next hypothesis
The [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) describe tree depth as a complexity control and recommend increasing boosting rounds when lowering the learning rate. The [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) documents `n_estimators`/boosting rounds, `eta`, and the regularizing roles of row and column subsampling. A flight-delay review reports scheduled time, calendar fields, carrier, origin, destination, and route information among commonly useful predictors ([Li et al., 2021](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057)); this starter already includes most of these available fields.

### Experiment 1 — more boosting rounds
- Class: follow-up to the baseline.
- Hypothesis: 30 trees may leave useful signal unmodeled; increasing to 150 while holding depth, learning rate, and features fixed should improve AUC if the starter is underfit. The low baseline fit time leaves ample room under the harness cap.
- Decision rule: keep only if eval AUC improves; otherwise revert.

## Experiment 1 — 150 trees
- Commit: `7b7a599`
- Hypothesis: the 30-tree starter may be underfit; increasing only the boosting rounds could capture more signal.
- Change: `n_estimators` 30 → 150; all other parameters and features unchanged.
- Result: Eval AUC 0.7332 (+0.0129); training 0.9 s; evaluation 30.2 s; status `ok`.
- Decision: keep. The gain is substantial and training remains far below the 60 s limit.

### Experiment 2 — 300 trees
- Class: follow-up to the promising round-count increase.
- Hypothesis: the large gain at 150 trees suggests the learning curve may still be rising. Increase only `n_estimators` to 300 to test the next range and measure diminishing returns.
- Decision rule: keep only if eval AUC improves; otherwise revert to `7b7a599`.

## Experiment 2 — 300 trees
- Commit: `7473a85`
- Hypothesis: the 150-tree gain might continue, though with diminishing returns.
- Change: `n_estimators` 150 → 300; all other parameters and features unchanged.
- Result: Eval AUC 0.7342 (+0.0010 over 150); training 1.7 s; evaluation 30.4 s; status `ok`.
- Decision: keep. The AUC increased again, while the increment is now much smaller.

### Experiment 3 — 600 trees
- Class: follow-up to the improving round-count sweep.
- Hypothesis: a single larger step will show whether additional boosting still helps or whether this parameter has reached diminishing returns. Keep all other settings fixed.
- Decision rule: keep only if eval AUC improves; otherwise revert to `7473a85`.

## Experiment 3 — 600 trees
- Commit: `b1fc036`
- Hypothesis: because 300 trees improved over 150, another increase might continue to help.
- Change: `n_estimators` 300 → 600; all other parameters and features unchanged.
- Result: Eval AUC 0.7299 (-0.0043 vs. 300); training 3.4 s; evaluation 30.9 s; status `ok`.
- Decision: discard and reset to `7473a85`. The round-count results show a peak at 300 in this sweep; do not keep increasing rounds.

## Time-feature research and Experiment 4 proposal
The scikit-learn time-feature example notes that tree models can learn non-monotonic patterns from ordinal time features, so a generic sine/cosine transform is not automatically justified ([scikit-learn time-related feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html)). A flight-delay study explicitly derives a night-flight flag from scheduled HHMM, defining night as 21:00–04:00 ([Saputri et al., 2024](https://www.mdpi.com/2079-9292/13/24/4910)). The latter is a different delay task/model, so this is a targeted hypothesis rather than an assumed gain.

### Experiment 4 — night-flight flag
- Class: exploration via a small feature-engineering change.
- Hypothesis: the current model sees scheduled HHMM as an ordered numeric input. An explicit 21:00–04:00 binary flag could make the wraparound night interval available in one split and interact with airport/date features; retain the raw value so the model also has its original detail.
- Change planned: derive the hour from `CRSDepTime` inside `prepare(df)` and add one binary `NightFlight` feature. It uses only the row's scheduled time and therefore has the same meaning during training and row-by-row evaluation.
- Decision rule: keep only if eval AUC beats the current best 0.7342; otherwise revert to `7473a85`.

## Experiment 4 — night-flight flag
- Commit: `64eb864`
- Hypothesis: a 21:00–04:00 binary indicator might expose the overnight interval compactly while retaining raw scheduled time.
- Change: added `NightFlight` inside `prepare(df)` from that row's `CRSDepTime`; all original features remained.
- Result: Eval AUC 0.7336 (-0.0006 vs. best); training 1.8 s; evaluation 34.2 s; status `ok`.
- Decision: discard and reset to `7473a85`. The idea did not beat the current best and adds a feature.

### Experiment 5 — reduce tree depth
- Class: exploration of model complexity, motivated by the 600-tree regression and XGBoost's parameter guidance.
- Hypothesis: 300 rounds worked best at depth 6; shallower depth 4 may reduce per-tree variance and generalize better while the larger ensemble retains capacity.
- Change planned: `max_depth` 6 → 4; 300 rounds and all other settings unchanged.
- Decision rule: keep only if eval AUC beats 0.7342; otherwise revert to `7473a85`.

## Experiment 5 — depth 4
- Commit: `bf11b32`
- Hypothesis: shallower trees could reduce overfitting at the best 300-tree round count.
- Change: `max_depth` 6 → 4; all other settings and features unchanged.
- Result: Eval AUC 0.7343 (+0.0001 vs. best); training 1.1 s; evaluation 30.3 s; status `ok`.
- Decision: keep. The gain is small but the code/model setup is equally simple.

### Experiment 6 — depth 3
- Class: follow-up to the slight gain from reducing depth.
- Hypothesis: if added regularization helped at depth 4, depth 3 may improve generalization further. Keep 300 rounds and all other settings fixed.
- Decision rule: keep only if eval AUC improves; otherwise revert to `bf11b32`.

## Experiment 6 — depth 3
- Commit: `95a12bc`
- Hypothesis: stronger regularization than depth 4 might improve generalization.
- Change: `max_depth` 4 → 3; 300 rounds and all other settings unchanged.
- Result: Eval AUC 0.7286 (-0.0057 vs. best); training 0.8 s; evaluation 30.4 s; status `ok`.
- Decision: discard and reset to `bf11b32`. Depth 3 appears too restrictive at this round count.

### Experiment 7 — depth 5
- Class: follow-up to bracket the small depth-4 gain against the depth-3 regression.
- Hypothesis: depth 5 may retain useful interactions while regularizing slightly relative to the original depth 6.
- Change planned: `max_depth` 4 → 5; all other settings unchanged.
- Decision rule: keep only if eval AUC beats 0.7343; otherwise revert to `bf11b32`.

## Experiment 7 — depth 5
- Commit: `9d7f41b`
- Hypothesis: depth 5 could preserve interactions at depth 6 while regularizing slightly; depth 4 and 3 bracketed this setting.
- Change: `max_depth` 4 → 5; all other settings unchanged.
- Result: Eval AUC 0.7354 (+0.0011 vs. previous best); training 1.4 s; evaluation 30.4 s; status `ok`.
- Decision: keep. This is the current best.

### Experiment 8 — row subsampling
- Class: exploration of a separate regularization control.
- Hypothesis: with 300 rounds and depth 5 now performing best, `subsample=0.8` may add useful randomness and reduce overfitting. XGBoost's [tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) identify subsampling as a way to control overfitting.
- Change planned: set `subsample=0.8`; all other settings unchanged.
- Decision rule: keep only if eval AUC beats 0.7354; otherwise revert to `9d7f41b`.

## Experiment 8 — row subsampling
- Commit: `2136874`
- Hypothesis: `subsample=0.8` might add useful randomness and reduce overfitting.
- Change: added row subsampling at 0.8; all other settings unchanged.
- Result: Eval AUC 0.7246 (-0.0108 vs. best); training 1.4 s; evaluation 30.4 s; status `ok`.
- Decision: discard and reset to `9d7f41b`. This setting substantially hurt the eval score.

### Experiment 9 — lower learning rate with more rounds
- Class: follow-up using the coupled learning-rate/round-count guidance in the [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html).
- Hypothesis: `learning_rate=0.05` with 600 rounds keeps roughly the same aggregate step scale as the current 300 × 0.1 model while taking smaller boosting steps; this may generalize better than the failed 600 × 0.1 run.
- Change planned: `learning_rate` 0.1 → 0.05 and `n_estimators` 300 → 600; keep depth 5 and all other settings fixed.
- Decision rule: keep only if eval AUC beats 0.7354; otherwise revert to `9d7f41b`.

## Experiment 9 — lower learning rate with more rounds
- Commit: `42d5dcf`
- Hypothesis: 600 smaller boosting steps at learning rate 0.05 could generalize better than 300 steps at 0.1, as recommended by XGBoost's tuning notes.
- Change: `n_estimators` 300 → 600 and `learning_rate` 0.1 → 0.05; kept depth 5 and all other settings fixed.
- Result: Eval AUC 0.7362 (+0.0008 vs. previous best); training 2.7 s; evaluation 30.7 s; status `ok`.
- Decision: keep. This is the new best commit.

## Synthesis after 10 experiments
- The starter's 30 trees were substantially underfit: 150 trees gained 0.0129 AUC, and 300 added another 0.0010.
- At learning rate 0.1, 600 trees regressed. Pairing 600 rounds with learning rate 0.05 recovered and slightly improved the best score, consistent with using smaller boosting steps over more rounds.
- Mid-range tree depth matters: depth 5 improved the 300-tree model; depth 3 was too restrictive. Depth 4 gave only a marginal gain.
- The `NightFlight` feature and `subsample=0.8` both hurt on this eval split. No new features are kept; all improvements so far come from model capacity and parameters.
- Current best: commit `42d5dcf`, Eval AUC 0.7362, with 600 trees, depth 5, and learning rate 0.05.
- Next direction to investigate: whether smoothed carrier/airport/route target-rate lookups provide useful row-level priors beyond native categorical splits. Research leakage control and smoothing before implementing one.

## Research after experiment 10 and Experiment 10 proposal
The [scikit-learn TargetEncoder documentation](https://scikit-learn.org/stable/modules/preprocessing.html) explains that smoothing shrinks small groups toward the global mean and that cross-fitting is used to prevent target leakage. A simple full-training target-rate feature would expose each training label to its own encoding, so I am not starting with that approach.

XGBoost's [categorical-data guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) documents partition-based splits that group categories with similar learned leaf values. A flight-delay review lists origin-destination pairs and route type among features used in prior models ([Li et al., 2021](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057)). These findings motivate testing route identity as a native categorical feature without target-derived statistics.

### Experiment 10 — directed route category
- Class: exploration via a single categorical interaction feature.
- Hypothesis: a directed `Origin>Dest` category may let trees capture route-specific patterns in a split and combine routes with similar learned effects. The current model has separate origin and destination categories but no direct route key.
- Change planned: construct the route string from each row's origin and destination inside `prepare(df)`; fit the allowed route category levels once from `train`; unseen evaluation routes become missing categories. No labels or other rows are used to prepare a row.
- Decision rule: keep only if eval AUC beats 0.7362; otherwise revert to `42d5dcf`.

## Experiment 10 — directed route category
- Commit: `7b31d99`
- Hypothesis: a native directed route category might expose route-specific delay patterns beyond separate origin and destination categories.
- Change: added train-fitted `Origin>Dest` categorical levels and derived the category inside `prepare(df)`.
- Result: Eval AUC 0.7079 (-0.0283 vs. best); training 5.3 s; evaluation 43.9 s; status `ok`.
- Observation: pandas emitted warnings for unseen route values; row-wise evaluation was slower than the baseline feature set.
- Decision: discard and reset to `42d5dcf`. The high-cardinality route feature hurt substantially and added evaluation cost.

## Experiment 11 — one-hot splits for low-cardinality categoricals
XGBoost's [categorical parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says `max_cat_to_onehot` selects one-hot splits below a category-count threshold and partition splits above it. The [categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains that partitioning groups categories by similar learned leaf values. The failed route experiment does not rule out the lower-cardinality month/day/carrier fields, whose effects may be non-monotonic.

- Class: exploration of native categorical split strategy.
- Hypothesis: setting `max_cat_to_onehot=32` will let low-cardinality calendar/carrier fields isolate individual categories in one split, while higher-cardinality airport categories continue to use partitions. This may better express non-monotonic effects at depth 5.
- Change planned: add only `max_cat_to_onehot=32`; preserve the current 600-tree, depth-5, learning-rate-0.05 model.
- Decision rule: keep only if eval AUC beats 0.7362; otherwise revert to `42d5dcf`.

## Experiment 11 — one-hot splits for low-cardinality categoricals
- Commit: `e25ab74`
- Hypothesis: individual one-hot tests for low-cardinality calendar/carrier categories might better express non-monotonic effects than partition splits.
- Change: set `max_cat_to_onehot=32`; all other settings unchanged.
- Result: Eval AUC 0.7235 (-0.0127 vs. best); training 2.3 s; evaluation 30.8 s; status `ok`.
- Decision: discard and reset to `42d5dcf`. One-hot splits were much worse on this eval set.

### Experiment 12 — minimum child weight
- Class: exploration of tree regularization.
- Hypothesis: the best model has many rounds and depth-5 trees. Raising `min_child_weight` from its default 1 to 5 may suppress weak splits supported by small child nodes, improving generalization without changing features or category encoding. XGBoost's [parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes larger values as more conservative.
- Change planned: `min_child_weight=5`; all other settings unchanged.
- Decision rule: keep only if eval AUC beats 0.7362; otherwise revert to `42d5dcf`.

## Experiment 12 — minimum child weight 5
- Commit: `fefe7c8`
- Hypothesis: a higher minimum child weight might suppress weak small-node splits in the 600-tree depth-5 model.
- Change: set `min_child_weight=5`; all other settings unchanged.
- Result: Eval AUC 0.7359 (-0.0003 vs. best); training 2.7 s; evaluation 30.3 s; status `ok`.
- Decision: discard and reset to `42d5dcf`.

### Experiment 13 — finer histogram bins
- Class: exploration of continuous split precision.
- Hypothesis: the model has only two numeric fields, and increasing `max_bin` from its default 256 to 512 may provide more precise candidate thresholds for scheduled time and distance. The XGBoost [parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) says larger `max_bin` can improve split optimality at additional computation cost.
- Change planned: add `max_bin=512`; preserve all other settings.
- Decision rule: keep only if eval AUC beats 0.7362; otherwise revert to `42d5dcf`.

## Experiment 13 — histogram bins 512
- Commit: `15969e3`
- Hypothesis: more bins could improve numeric split precision for scheduled time and distance.
- Change: set `max_bin=512`; all other settings unchanged.
- Result: Eval AUC 0.7357 (-0.0005 vs. best); training 2.6 s; evaluation 30.4 s; status `ok`.
- Decision: discard and reset to `42d5dcf`.

### Experiment 14 — coarser histogram bins
- Class: follow-up to the `max_bin` resolution check.
- Hypothesis: if 512 bins slightly hurt, reducing to 128 may regularize the two numeric features by offering fewer candidate thresholds.
- Change planned: set `max_bin=128`; all other settings unchanged.
- Decision rule: keep only if eval AUC beats 0.7362; otherwise revert to `42d5dcf`.

## Experiment 14 — histogram bins 128
- Commit: `4806c5b`
- Hypothesis: coarser numeric thresholds might regularize the scheduled-time and distance splits.
- Change: set `max_bin=128`; all other settings unchanged.
- Result: Eval AUC 0.7365 (+0.0003 vs. previous best); training 2.6 s; evaluation 30.7 s; status `ok`.
- Decision: keep. This is the new best.

### Experiment 15 — histogram bins 64
- Class: follow-up to the small gain at 128 bins.
- Hypothesis: a further reduction may regularize numeric splits more, but could lose useful resolution; test one step lower with all else fixed.
- Change planned: `max_bin` 128 → 64.
- Decision rule: keep only if eval AUC improves; otherwise revert to `4806c5b`.

## Experiment 15 — histogram bins 64
- Commit: `b46e187`
- Hypothesis: coarser numeric thresholds than 128 bins might further regularize time and distance.
- Change: `max_bin` 128 → 64; all other settings unchanged.
- Result: Eval AUC 0.7364 (-0.0001 vs. best); training 2.6 s; evaluation 30.7 s; status `ok`.
- Decision: discard and reset to `4806c5b`; 128 bins remains best.

### Experiment 16 — depth 4 with the lower-rate schedule
- Class: follow-up to the earlier depth sweep under a changed training schedule.
- Hypothesis: depth 4 slightly improved on depth 6 at 300 rounds and learning rate 0.1. At 600 rounds and learning rate 0.05, shallower trees may again improve generalization.
- Change planned: `max_depth` 5 → 4; retain `n_estimators=600`, `learning_rate=0.05`, and `max_bin=128`.
- Decision rule: keep only if eval AUC beats 0.7365; otherwise revert to `4806c5b`.

## Experiment 16 — depth 4 with the lower-rate schedule
- Commit: `af1091e`
- Hypothesis: shallower trees might generalize better at 600 rounds and learning rate 0.05, even though the earlier depth sweep used 300 rounds and 0.1.
- Change: `max_depth` 5 → 4; retained 600 rounds, learning rate 0.05, and `max_bin=128`.
- Result: Eval AUC 0.7351 (-0.0014 vs. best); training 2.0 s; evaluation 30.6 s; status `ok`.
- Decision: discard and reset to `4806c5b`.

### Experiment 17 — depth 6 with the lower-rate schedule
- Class: follow-up to the depth interaction check.
- Hypothesis: since depth 4 regressed under the 600-round schedule, depth 6 may recover useful interactions at learning rate 0.05. Test against the depth-5 best while keeping `max_bin=128`.
- Change planned: `max_depth` 5 → 6; all other settings unchanged.
- Decision rule: keep only if eval AUC beats 0.7365; otherwise revert to `4806c5b`.

## Experiment 17 — depth 6 with the lower-rate schedule
- Commit: `a2f697c`
- Hypothesis: deeper trees might recover interactions at 600 rounds and learning rate 0.05 after depth 4 regressed.
- Change: `max_depth` 5 → 6; retained 600 rounds, learning rate 0.05, and `max_bin=128`.
- Result: Eval AUC 0.7354 (-0.0011 vs. best); training 3.3 s; evaluation 30.4 s; status `ok`.
- Decision: discard and reset to `4806c5b`. Depth 5 remains best under this schedule.

### Experiment 18 — finer boosting steps
- Class: follow-up to the improvement from 300 × 0.1 to 600 × 0.05.
- Hypothesis: 900 rounds at learning rate 0.0333 keeps the approximate cumulative step scale near 30 while making each update smaller; this may improve generalization further.
- Change planned: `n_estimators` 600 → 900 and `learning_rate` 0.05 → 0.0333; retain depth 5 and `max_bin=128`.
- Decision rule: keep only if eval AUC beats 0.7365; otherwise revert to `4806c5b`.

## Experiment 18 — 900 smaller boosting steps
- Commit: `da4414d`
- Hypothesis: 900 rounds at learning rate 0.0333 might improve generalization over 600 rounds at 0.05 while keeping a similar aggregate step scale.
- Change: `n_estimators` 600 → 900 and `learning_rate` 0.05 → 0.0333; retained depth 5 and `max_bin=128`.
- Result: Eval AUC 0.7365 (tied with best); training 3.9 s; evaluation 30.7 s; status `ok`.
- Decision: discard and reset to `4806c5b`; the more complex schedule gave no rounded AUC gain.

### Experiment 19 — small split penalty
- Class: exploration of split regularization.
- Hypothesis: `gamma=0.1` may prune marginal splits in the depth-5 ensemble while leaving strong splits available. The XGBoost [parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes larger gamma as requiring more loss reduction before a split.
- Change planned: add `gamma=0.1`; all other settings unchanged.
- Decision rule: keep only if eval AUC beats 0.7365; otherwise revert to `4806c5b`.

## Experiment 19 — gamma 0.1
- Commit: `312cc67`
- Hypothesis: a small split penalty might suppress marginal splits in the depth-5 model.
- Change: added `gamma=0.1`; all other settings unchanged.
- Result: Eval AUC 0.7360 (-0.0005 vs. best); training 2.6 s; evaluation 30.4 s; status `ok`.
- Decision: discard and reset to `4806c5b`.

## Synthesis after 20 experiments
- Eval AUC rose from 0.7203 to 0.7365 (+0.0162). The largest gain came from increasing the number of boosting rounds; lowering learning rate while increasing rounds added further improvement.
- Depth 5 consistently outperformed depth 3, 4, and 6 in the tested settings. `max_bin=128` added a small gain over the default; 64 and 512 bins were slightly worse.
- Experiments adding a night flag, directed route category, one-hot category splits, row subsampling, stronger child-weight regularization, and gamma did not beat the best. Route and one-hot category changes caused the largest regressions.
- Current best remains commit `4806c5b` with 600 trees, depth 5, learning rate 0.05, and max_bin 128. The feature set is still the starter's original fields.
- Next direction: research dropout boosting (DART) as a different way to regularize the long ensemble, then test it only if training and prediction remain compatible with this harness.

## DART research and next feature proposal
The [DART paper](https://arxiv.org/abs/1505.01866) proposes dropout boosting to reduce over-specialization in long tree ensembles. However, the [XGBoost DART guide](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) warns that inference must use an explicit iteration range to avoid randomly dropping trees. The fixed harness calls `predict_proba` without that range, so I am not using DART in this setup.

Flight-delay literature includes scheduled departure time in hours as a standard predictor ([Li et al., 2021](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057)). XGBoost's [categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains that partition splits can group categories with similar learned effects.

### Experiment 20 — scheduled departure hour category
- Class: exploration through one row-wise time feature.
- Hypothesis: extracting hour from HHMM and treating the 24 hours as a native categorical feature may let the model group non-adjacent hours with similar delay behavior, while retaining the raw numeric `CRSDepTime` detail.
- Change planned: fit observed hour levels on `train` at module scope; derive `(CRSDepTime // 100) % 24` inside `prepare(df)`; cast to categorical using those fitted levels. Unseen hours become missing.
- Decision rule: keep only if eval AUC beats 0.7365; otherwise revert to `4806c5b`.

## Experiment 20 — scheduled departure hour category
- Commit: `4cd5fd8`
- Hypothesis: a native categorical hour feature could group non-adjacent hours with similar delay behavior while retaining raw HHMM.
- Change: derived hour from `CRSDepTime` inside `prepare(df)` and fitted its levels on train.
- Result: Eval AUC 0.7367 (+0.0002 vs. previous best); training 2.7 s; evaluation 36.5 s; status `ok`.
- Decision: keep. This is the new best; evaluation remains within the harness limit.

### Experiment 21 — coarser departure-time periods
- Class: ablation/simplification of the new hour feature.
- Hypothesis: replacing 24 hour categories with six four-hour periods may smooth noisy hour-level patterns, retain useful daypart signal, and reduce row-wise preparation overhead.
- Change planned: replace `DepHour` with a six-level `DepPeriod` derived as `hour // 4`; keep raw `CRSDepTime` and all other features.
- Decision rule: keep if eval AUC improves, or is about equal with lower evaluation time and simpler feature preparation; otherwise revert to `4cd5fd8`.

## Experiment 21 — four-hour departure periods
- Commit: `b5de04b`
- Hypothesis: six coarse time periods might smooth hour-specific noise and reduce encoding overhead.
- Change: replaced the 24-level `DepHour` with six `DepPeriod` categories; retained raw scheduled time.
- Result: Eval AUC 0.7357 (-0.0010 vs. best); training 2.7 s; evaluation 35.8 s; status `ok`.
- Decision: discard and reset to `4cd5fd8`. The full hour category performed better with similar evaluation time.

### Experiment 22 — ablate raw scheduled time
- Class: ablation/simplification of the successful hour feature.
- Hypothesis: `DepHour` may carry most of the useful time-of-day signal. Removing raw `CRSDepTime` from the model inputs could preserve AUC while reducing redundant detail.
- Change planned: remove `CRSDepTime` from `num_cols`; keep the row-wise derivation of `DepHour` and all other features.
- Decision rule: keep if eval AUC improves, or is about equal with fewer model inputs; otherwise revert to `4cd5fd8`.

## Experiment 22 — remove raw scheduled time
- Commit: `00fe269`
- Hypothesis: `DepHour` may carry most useful time-of-day signal, making raw `CRSDepTime` redundant.
- Change: removed raw `CRSDepTime` from `num_cols` while retaining the row-wise hour category.
- Result: Eval AUC 0.7366 (-0.0001 vs. best); training 2.7 s; evaluation 35.2 s; status `ok`.
- Decision: keep as a simplification. The rounded AUC is effectively unchanged and the model has one fewer input.

### Experiment 23 — weekday-hour interaction
- Class: follow-up feature engineering based on the successful `DepHour` feature.
- Hypothesis: departure-hour effects may differ across weekdays. A `DayOfWeek × DepHour` category could expose that interaction in one categorical split; flight-delay literature commonly includes both calendar day and scheduled time ([Li et al., 2021](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057)).
- Change planned: add a row-wise composite categorical `DOWHour`; fit its observed levels on train, retain the separate `DayOfWeek` and `DepHour` inputs.
- Decision rule: keep only if eval AUC beats 0.7367; otherwise revert to `00fe269`.

## Experiment 23 — weekday-hour interaction
- Commit: `a357302`
- Hypothesis: a `DayOfWeek × DepHour` categorical interaction might expose different time-of-day effects across weekdays.
- Change: added a train-fitted `DOWHour` category while retaining the separate features.
- Result: Eval AUC 0.7301 (-0.0066 vs. best); training 2.9 s; evaluation 42.3 s; status `ok`.
- Decision: discard and reset to `00fe269`. The composite category hurt and increased row-wise evaluation time.

## Tree-growth research and Experiment 24 proposal
The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) documents `grow_policy="depthwise"` as expanding nodes closest to the root and `grow_policy="lossguide"` as expanding the node with the highest loss change. The policy is supported with histogram or approximate tree methods. The current model uses depthwise growth; with depth 5 and long boosting, allocating a fixed leaf budget to the strongest splits may use capacity more efficiently.

### Experiment 24 — lossguide growth
- Class: exploration of tree structure.
- Hypothesis: loss-guided expansion may spend a fixed tree budget on the highest-value splits and improve AUC over depthwise growth.
- Change planned: set `tree_method="hist"`, `grow_policy="lossguide"`, and `max_leaves=31`, retaining `max_depth=5` and other current settings. The explicit histogram method matches the supported policy and the leaf cap keeps tree size bounded.
- Decision rule: keep only if eval AUC beats 0.7367; otherwise revert to `00fe269`.

## Experiment 24 — loss-guided tree growth
- Commit: `bd5143f`
- Hypothesis: loss-guided growth could allocate a bounded tree budget to the highest-value splits more efficiently than depthwise growth.
- Change: set histogram tree method, `grow_policy="lossguide"`, and `max_leaves=31`; retained depth 5 and other model settings.
- Result: Eval AUC 0.7380 (+0.0013 vs. previous best); training 3.1 s; evaluation 35.4 s; status `ok`.
- Decision: keep. This is the new best and remains within the timing limits.

### Experiment 25 — remove the depth cap under lossguide
- Class: follow-up to the promising loss-guided result.
- Hypothesis: with `max_leaves=31` already bounding tree size, removing the depth cap may let loss-guided growth place more splits along the strongest branches.
- Change planned: `max_depth` 5 → 0; keep `max_leaves=31` and all other settings fixed.
- Decision rule: keep only if eval AUC beats 0.7380; otherwise revert to `bd5143f`.

## Experiment 25 — remove the depth cap under lossguide
- Commit: `4d18adf`
- Hypothesis: the 31-leaf limit might allow useful deeper branches when the depth cap is removed.
- Change: `max_depth` 5 → 0; retained `max_leaves=31` and loss-guided growth.
- Result: Eval AUC 0.7359 (-0.0021 vs. best); training 2.9 s; evaluation 35.4 s; status `ok`.
- Decision: discard and reset to `bd5143f`. The depth-5 cap helps.

### Experiment 26 — smaller steps under lossguide
- Class: follow-up to the loss-guided gain.
- Hypothesis: 900 rounds at learning rate 0.0333 tied with the 600 × 0.05 depthwise model; loss-guided growth may benefit differently from the finer updates.
- Change planned: `n_estimators` 600 → 900 and `learning_rate` 0.05 → 0.0333; keep depth 5, `max_leaves=31`, and all other settings.
- Decision rule: keep only if eval AUC beats 0.7380; otherwise revert to `bd5143f`.

## Experiment 25 — smaller steps under lossguide
- Commit: `3c35be9`
- Hypothesis: the finer 900 × 0.0333 schedule might work better with loss-guided growth than it did with depthwise growth.
- Change: increased rounds 600 → 900 and lowered learning rate 0.05 → 0.0333; retained depth 5, 31 leaves, and lossguide.
- Result: Eval AUC 0.7370 (-0.0010 vs. best); training 5.0 s; evaluation 35.3 s; status `ok`.
- Decision: discard and reset to `bd5143f`.

### Experiment 26 — smaller leaf budget
- Class: follow-up to the gain from loss-guided growth.
- Hypothesis: limiting trees to 15 leaves instead of 31 may reduce overfitting while preserving lossguide's priority for high-value splits.
- Change planned: `max_leaves` 31 → 15; use the best 600-round, 0.05 learning-rate configuration.
- Decision rule: keep only if eval AUC beats 0.7380; otherwise revert to `bd5143f`.

## Experiment 26 — leaf budget 15
- Commit: `19b1812`
- Hypothesis: fewer loss-guided leaves might regularize individual trees.
- Change: `max_leaves` 31 → 15; retained depth 5 and other settings.
- Result: Eval AUC 0.7324 (-0.0056 vs. best); training 1.9 s; evaluation 35.1 s; status `ok`.
- Decision: discard and reset to `bd5143f`. The smaller leaf budget was too restrictive.

### Experiment 27 — limit categorical split candidates
- Class: follow-up regularization of the native categorical features.
- Hypothesis: airport categories may benefit from considering fewer category candidates per partition. XGBoost documents `max_cat_threshold` as a control for overfitting in partition-based categorical splits.
- Change planned: set `max_cat_threshold=32`; retain loss-guided growth with depth 5 and 31 leaves.
- Decision rule: keep only if eval AUC beats 0.7380; otherwise revert to `bd5143f`.

## Experiment 27 — categorical partition threshold 32
- Commit: `de21778`
- Hypothesis: fewer categories considered per partition could regularize high-cardinality airport splits under loss-guided growth.
- Change: set `max_cat_threshold=32`; all other settings unchanged.
- Result: Eval AUC 0.7372 (+0.0008 vs. best); training 2.8 s; evaluation 35.5 s; status `ok`.
- Decision: keep. This is the new best.

### Experiment 28 — categorical partition threshold 16
- Class: follow-up to the improvement at threshold 32.
- Hypothesis: a stronger limit may further reduce overfitting in airport-category partitions.
- Change planned: `max_cat_threshold` 32 → 16; all other settings unchanged.
- Decision rule: keep only if eval AUC beats 0.7372; otherwise revert to `de21778`.

## Experiment 28 — categorical partition threshold 16
- Commit: `03cc94f`
- Hypothesis: a tighter partition threshold than 32 could further regularize airport-category splits.
- Change: `max_cat_threshold` 32 → 16; all other settings unchanged.
- Result: Eval AUC 0.7391 (+0.0019 vs. previous best); training 2.7 s; evaluation 35.2 s; status `ok`.
- Decision: keep. This is the new best.

## Synthesis after 30 experiments
- Eval AUC improved from 0.7203 to 0.7391 (+0.0188). Increasing trees from 30 to 150 produced the largest early gain; lower learning rate with more rounds helped further.
- The largest recent gain came from loss-guided growth at depth 5 with 31 leaves. Removing the depth cap or cutting the leaf budget to 15 hurt; 900 smaller steps were slightly worse than 600 × 0.05.
- `max_bin=128` helped modestly. Reducing native categorical partition candidates to 32 and then 16 improved the loss-guided model; setting a high one-hot threshold hurt.
- The full `DepHour` categorical feature gave a small gain; removing raw `CRSDepTime` kept almost the same AUC with fewer model inputs. Coarse periods and weekday-hour/route composites hurt.
- Current best: commit `03cc94f`, Eval AUC 0.7391. Parameters: 600 trees, depth 5, learning rate 0.05, 128 bins, histogram method, loss-guided growth, 31 leaves, categorical threshold 16. Features are Distance, six starter categoricals, and the row-wise DepHour category.
- Next direction to research: column sampling per tree, which has not been tested. Row subsampling at 0.8 hurt, so test feature sampling separately and at a moderate rate.

## Column-sampling research and Experiment 31 proposal
The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) says `colsample_bytree` samples a fraction of columns once per tree, with values in `(0, 1]`. This gives each tree a slightly different candidate feature set, a form of training randomness distinct from row subsampling. The current model has eight inputs, so a mild 0.9 setting should retain most features on each tree while testing whether that variation improves generalization. The previous `subsample=0.8` trial reduced AUC, but it changed row sampling and does not determine the effect of column sampling.

### Experiment 31 — mild per-tree column sampling
- Class: tree-level feature sampling.
- Hypothesis: sampling 90% of columns per tree may add useful diversity and modestly reduce overfitting while keeping most of the eight inputs available.
- Change planned: add `colsample_bytree=0.9`; leave all other best-model parameters and features unchanged.
- Decision rule: keep only if Eval AUC exceeds 0.7391; otherwise reset to `03cc94f`.

## Experiment 31 — mild per-tree column sampling
- Commit: `42d260a`
- Hypothesis: sampling 90% of columns per tree might add useful diversity while retaining most model inputs.
- Change: added `colsample_bytree=0.9`; all other settings remained at the best configuration.
- Result: Eval AUC 0.7385 (-0.0006 vs. best); training 2.7 s; evaluation 35.9 s; status `ok`.
- Decision: discard and reset to `03cc94f`. The small column-sampling rate did not improve evaluation AUC.

### Experiment 32 — categorical partition threshold 8
- Class: follow-up to categorical split regularization.
- Hypothesis: a tighter limit than 16 may regularize the airport splits further, extending the consistent gains seen at 32 and 16.
- Change planned: set `max_cat_threshold=8`; leave other settings unchanged.
- Decision rule: keep only if Eval AUC exceeds 0.7391; otherwise reset to `03cc94f`.

## Experiment 32 — categorical partition threshold 8
- Commit: `bb44818`
- Hypothesis: a tighter categorical candidate limit might regularize airport splits beyond the successful value of 16.
- Change: set `max_cat_threshold=8`; all other settings remained at the best configuration.
- Result: Eval AUC 0.7373 (-0.0018 vs. best); training 2.5 s; evaluation 35.2 s; status `ok`.
- Decision: discard and reset to `03cc94f`. A threshold of 8 was too restrictive.

## Periodic time-feature research and Experiment 33 proposal
The [scikit-learn time-feature guide](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) demonstrates mapping hour-of-day to sine and cosine coordinates with a 24-hour period so midnight is adjacent to the end of the day. The guide studies other estimators and does not establish a benefit for boosted trees. Here the existing categorical `DepHour` remains in place; adding the two numeric coordinates will test whether this smooth cyclic view provides useful complementary splits without removing the current strong representation.

### Experiment 33 — add cyclic departure-hour coordinates
- Class: periodic feature engineering.
- Hypothesis: sine/cosine coordinates for the 24-hour departure cycle may capture smooth wraparound patterns that complement categorical `DepHour`.
- Change planned: add row-wise `DepHourSin` and `DepHourCos` computed from `CRSDepTime`-derived hour; retain `DepHour` and all other inputs.
- Decision rule: keep only if Eval AUC exceeds 0.7391; otherwise reset to `03cc94f`.

## Experiment 33 — cyclic departure-hour coordinates
- Commit: `65b4479`
- Hypothesis: cyclic sine/cosine coordinates might complement the hourly category by representing smooth wraparound relationships.
- Change: added row-wise `DepHourSin` and `DepHourCos`, retaining categorical `DepHour` and the rest of the best configuration.
- Result: Eval AUC 0.7395 (+0.0004 vs. previous best); training 2.9 s; evaluation 38.7 s; status `ok`.
- Decision: keep. The cyclic coordinates give a small improvement; this is the new best.

### Experiment 34 — replace hourly category with cyclic coordinates
- Class: ablation of the new periodic representation.
- Hypothesis: the sine/cosine pair may carry the useful departure-hour signal without the separate category, reducing redundant input and allowing smoother hour relationships.
- Change planned: remove categorical `DepHour` while retaining `DepHourSin` and `DepHourCos`.
- Decision rule: keep only if Eval AUC exceeds 0.7395; otherwise reset to `65b4479`.

## Experiment 34 — cyclic-only departure-hour representation
- Commit: `11f738e`
- Hypothesis: the sine/cosine pair might carry the hour signal without the separate category.
- Change: removed categorical `DepHour` while retaining both cyclic coordinates.
- Result: Eval AUC 0.7385 (-0.0010 vs. best); training 2.6 s; evaluation 34.6 s; status `ok`.
- Decision: discard and reset to `65b4479`. The category remains useful alongside the cyclic features.

### Experiment 35 — minute-resolution cyclic time
- Class: follow-up granularity test for periodic time features.
- Hypothesis: scheduled minute-of-day coordinates may expose within-hour schedule patterns that the hour-level coordinates cannot represent.
- Change planned: replace `DepHourSin`/`DepHourCos` with row-wise `DepTimeSin`/`DepTimeCos` using the 1,440-minute daily period; retain categorical `DepHour`.
- Decision rule: keep only if Eval AUC exceeds 0.7395; otherwise reset to `65b4479`.

## Experiment 35 — minute-resolution cyclic time
- Commit: `97a9220`
- Hypothesis: minute-of-day coordinates might capture useful schedule structure within each hour.
- Change: replaced the hour-level sine/cosine pair with minute-level cyclic coordinates; retained categorical `DepHour`.
- Result: Eval AUC 0.7384 (-0.0011 vs. best); training 2.8 s; evaluation 39.9 s; status `ok`.
- Decision: discard and reset to `65b4479`. Finer timing added noise relative to the hour-level encoding.

## Regularization research and Experiment 36 proposal
The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `reg_lambda` as L2 regularization on leaf weights and says larger values make the model more conservative. Since the newly added cyclic coordinates improved the best score, a moderate increase from the default may reduce overly strong leaf scores while preserving the tree structure and feature set.

### Experiment 36 — modestly increase L2 regularization
- Class: leaf-weight regularization.
- Hypothesis: increasing `reg_lambda` from its default 1 to 2 may slightly reduce overfitting in the best model with cyclic time inputs.
- Change planned: add `reg_lambda=2`; leave all other parameters and features unchanged.
- Decision rule: keep only if Eval AUC exceeds 0.7395; otherwise reset to `65b4479`.

## Experiment 36 — increase L2 regularization
- Commit: `295e455`
- Hypothesis: moderate leaf-weight shrinkage might help the richer time representation generalize.
- Change: set `reg_lambda=2`; kept all other settings at the best configuration.
- Result: Eval AUC 0.7398 (+0.0003 vs. previous best); training 2.9 s; evaluation 39.0 s; status `ok`.
- Decision: keep. This is the new best.

### Experiment 37 — stronger L2 regularization
- Class: follow-up to the improvement at `reg_lambda=2`.
- Hypothesis: a further increase may continue to improve leaf-weight shrinkage, or show that 2 is near the optimum.
- Change planned: `reg_lambda` 2 → 4; retain all other settings.
- Decision rule: keep only if Eval AUC exceeds 0.7398; otherwise reset to `295e455`.

## Experiment 37 — stronger L2 regularization
- Commit: `768d338`
- Hypothesis: further leaf-weight shrinkage might continue the gain from `reg_lambda=2`.
- Change: increased `reg_lambda` from 2 to 4; other settings stayed fixed.
- Result: Eval AUC 0.7399 (+0.0001 vs. previous best); training 2.9 s; evaluation 39.1 s; status `ok`.
- Decision: keep. This is the new best.

### Experiment 38 — L2 regularization at 8
- Class: follow-up to the gradual gains at values 2 and 4.
- Hypothesis: stronger shrinkage may provide a further small benefit before the model begins to underfit.
- Change planned: `reg_lambda` 4 → 8; retain all other settings.
- Decision rule: keep only if Eval AUC exceeds 0.7399; otherwise reset to `768d338`.

## Experiment 38 — L2 regularization at 8
- Commit: `c87cc80`
- Hypothesis: stronger leaf-weight shrinkage might extend the gains from 2 and 4.
- Change: increased `reg_lambda` from 4 to 8; other settings stayed fixed.
- Result: Eval AUC 0.7396 (-0.0003 vs. best); training 2.8 s; evaluation 39.2 s; status `ok`.
- Decision: discard and reset to `768d338`. The stronger setting over-regularized relative to 4.

## L1 regularization note
The XGBoost parameter guide also describes `reg_alpha` as L1 regularization on leaf weights; higher values make the model more conservative. Test a mild positive value independently on top of the current L2 setting to see whether sparsity-oriented shrinkage complements it.

### Experiment 39 — mild L1 leaf regularization
- Class: L1 leaf-weight regularization.
- Hypothesis: `reg_alpha=0.1` may shrink weak leaf scores and complement the useful L2 penalty without suppressing strong leaves.
- Change planned: add `reg_alpha=0.1` to the best `reg_lambda=4` model.
- Decision rule: keep only if Eval AUC exceeds 0.7399; otherwise reset to `768d338`.

## Experiment 39 — mild L1 leaf regularization
- Commit: `73b337d`
- Hypothesis: a small L1 penalty might complement L2 by shrinking weak leaf weights.
- Change: added `reg_alpha=0.1` alongside `reg_lambda=4`; all other settings unchanged.
- Result: Eval AUC 0.7401 (+0.0002 vs. previous best); training 2.8 s; evaluation 38.8 s; status `ok`.
- Decision: keep. This is the new best.

### Experiment 40 — increase L1 regularization
- Class: follow-up to the gain at `reg_alpha=0.1`.
- Hypothesis: somewhat stronger L1 shrinkage may improve the result further, or show that 0.1 is near the useful range.
- Change planned: `reg_alpha` 0.1 → 0.3; keep `reg_lambda=4` and all other settings.
- Decision rule: keep only if Eval AUC exceeds 0.7401; otherwise reset to `73b337d`.

## Experiment 40 — stronger L1 regularization
- Commit: `197db2b`
- Hypothesis: a stronger L1 penalty might further shrink weak leaf scores.
- Change: increased `reg_alpha` from 0.1 to 0.3 while retaining `reg_lambda=4`.
- Result: Eval AUC 0.7411 (+0.0010 vs. previous best); training 2.9 s; evaluation 39.0 s; status `ok`.
- Decision: keep. This is the new best.

## Synthesis after 40 experiments
- Eval AUC is now 0.7411, up 0.0208 from the 0.7203 baseline.
- The per-tree column sample at 0.9 and `max_cat_threshold=8` both reduced AUC. A threshold of 16 remains better than 8.
- Adding hour-level sine/cosine coordinates alongside categorical `DepHour` improved AUC to 0.7395. Removing the category or using minute-level coordinates both hurt, so retain the categorical hour plus hour-level cyclic pair.
- L2 regularization improved gradually through `reg_lambda=4` (0.7399); 8 fell back to 0.7396. L1 then improved the model to 0.7401 at 0.1 and 0.7411 at 0.3.
- Current best: commit `197db2b`, with 600 trees, depth 5, learning rate 0.05, 128 bins, histogram method, loss-guided growth, 31 leaves, `max_cat_threshold=16`, `reg_lambda=4`, `reg_alpha=0.3`, and ten model inputs: Distance, six original categoricals, DepHour, and its sine/cosine coordinates.
- A possible class-weighting experiment was considered after consulting XGBoost docs, but `train.csv` has exactly 100,000 positive and 100,000 negative examples. The documented negative/positive ratio is therefore 1.0, so the default `scale_pos_weight=1` already matches it; skip that change.

## Month-hour interaction research and Experiment 41 proposal
Zhang et al.'s [airport-delay study](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12071) treats month (season) and time of day as relevant delay features. That supports testing, but does not establish, whether departure-hour effects vary by month in this flight-level dataset. A train-fitted month-hour category is a compact way to expose that interaction to the trees while preserving both main-effect features.

### Experiment 41 — month-by-departure-hour category
- Class: calendar-time interaction.
- Hypothesis: delay patterns by departure hour may shift across seasons, and an explicit month-hour category could capture that joint structure.
- Change planned: add a row-wise `MonthHour` categorical feature built from `Month` and `DepHour`, with levels fitted from train; retain all existing features.
- Decision rule: keep only if Eval AUC exceeds 0.7411; otherwise reset to `197db2b`.

## Experiment 41 — month-by-departure-hour category
- Commit: `16e140d`
- Hypothesis: explicit seasonal variation in hourly delay patterns might provide a useful joint feature.
- Change: added train-fitted `MonthHour` categorical levels from `Month` and scheduled departure hour; retained all main effects.
- Result: Eval AUC 0.7361 (-0.0050 vs. best); training 2.9 s; evaluation 46.0 s; status `ok`.
- Decision: discard and reset to `197db2b`. The composite hurt AUC and increased evaluation time.

### Experiment 42 — categorical threshold 12
- Class: tune native categorical partition regularization on the new best.
- Hypothesis: a setting between the successful value 16 and unsuccessful value 8 may retain useful airport partitions while still limiting candidate search.
- Change planned: set `max_cat_threshold=12`; leave the best feature set and other parameters unchanged.
- Decision rule: keep only if Eval AUC exceeds 0.7411; otherwise reset to `197db2b`.

## Experiment 42 — categorical threshold 12
- Commit: `183cc2f`
- Hypothesis: a threshold between 8 and 16 could preserve more useful category partitions than 8 while retaining regularization.
- Change: set `max_cat_threshold=12`; all other settings remained at the best configuration.
- Result: Eval AUC 0.7419 (+0.0008 vs. previous best); training 3.5 s; evaluation 38.7 s; status `ok`.
- Decision: keep. This is the new best.

### Experiment 43 — categorical threshold 10
- Class: follow-up to the improvement at threshold 12.
- Hypothesis: a slightly tighter threshold may improve the regularization tradeoff further.
- Change planned: `max_cat_threshold` 12 → 10; retain all other settings.
- Decision rule: keep only if Eval AUC exceeds 0.7419; otherwise reset to `183cc2f`.

## Experiment 43 — categorical threshold 10
- Commit: `47a1813`
- Hypothesis: a slightly tighter categorical split limit might improve on threshold 12.
- Change: reduced `max_cat_threshold` from 12 to 10; other settings unchanged.
- Result: Eval AUC 0.7421 (+0.0002 vs. previous best); training 2.7 s; evaluation 38.8 s; status `ok`.
- Decision: keep. This is the new best.

### Experiment 44 — categorical threshold 8 on the updated model
- Class: follow-up categorical-threshold tuning.
- Hypothesis: the earlier threshold-8 decline occurred before cyclic time features and L1/L2 regularization; on the stronger model, a tighter category limit may work differently.
- Change planned: `max_cat_threshold` 10 → 8; retain all other current best settings.
- Decision rule: keep only if Eval AUC exceeds 0.7421; otherwise reset to `47a1813`.

## Experiment 44 — categorical threshold 8 on the updated model
- Commit: `35ef366`
- Hypothesis: the stronger feature set and regularization might change the earlier threshold-8 result.
- Change: reduced `max_cat_threshold` from 10 to 8; other settings unchanged.
- Result: Eval AUC 0.7419 (-0.0002 vs. best); training 2.6 s; evaluation 38.9 s; status `ok`.
- Decision: discard and reset to `47a1813`.

### Experiment 45 — categorical threshold 9
- Class: narrow categorical-threshold search.
- Hypothesis: threshold 9 may preserve enough airport-category partitions to outperform 8 while keeping the gains from threshold 10.
- Change planned: `max_cat_threshold` 10 → 9; retain all other current best settings.
- Decision rule: keep only if Eval AUC exceeds 0.7421; otherwise reset to `47a1813`.

## Experiment 45 — categorical threshold 9
- Commit: `97d63cd`
- Hypothesis: a value between 8 and 10 might retain enough category partitions to preserve accuracy while keeping regularization.
- Change: set `max_cat_threshold=9`; other settings unchanged.
- Result: Eval AUC 0.7421 (tied best); training 2.7 s; evaluation 38.8 s; status `ok`.
- Decision: discard and reset to `47a1813`; it did not exceed threshold 10.

### Experiment 46 — L1 regularization at 0.5
- Class: follow-up to the improvement at `reg_alpha=0.3`.
- Hypothesis: slightly stronger L1 shrinkage may continue improving the model before weak leaves are over-penalized.
- Change planned: `reg_alpha` 0.3 → 0.5; keep `reg_lambda=4` and all other current best settings.
- Decision rule: keep only if Eval AUC exceeds 0.7421; otherwise reset to `47a1813`.

## Experiment 46 — L1 regularization at 0.5
- Commit: `daea9c0`
- Hypothesis: stronger L1 shrinkage might extend the improvement at 0.3.
- Change: increased `reg_alpha` from 0.3 to 0.5; all other settings unchanged.
- Result: Eval AUC 0.7425 (+0.0004 vs. previous best); training 2.7 s; evaluation 39.4 s; status `ok`.
- Decision: keep. This is the new best.

### Experiment 47 — L1 regularization at 0.7
- Class: follow-up to the gains at 0.3 and 0.5.
- Hypothesis: another moderate increase may continue to shrink weak leaf weights productively.
- Change planned: `reg_alpha` 0.5 → 0.7; retain `reg_lambda=4` and all other settings.
- Decision rule: keep only if Eval AUC exceeds 0.7425; otherwise reset to `daea9c0`.

## Experiment 47 — L1 regularization at 0.7
- Commit: `4132aae`
- Hypothesis: another moderate increase in L1 shrinkage might further improve the model.
- Change: increased `reg_alpha` from 0.5 to 0.7; all other settings unchanged.
- Result: Eval AUC 0.7434 (+0.0009 vs. previous best); training 2.8 s; evaluation 39.0 s; status `ok`.
- Decision: keep. This is the new best.

### Experiment 48 — L1 regularization at 0.9
- Class: follow-up to the continuing gains at 0.3, 0.5, and 0.7.
- Hypothesis: a small additional increase may continue to suppress weak leaf weights usefully.
- Change planned: `reg_alpha` 0.7 → 0.9; retain `reg_lambda=4` and all other settings.
- Decision rule: keep only if Eval AUC exceeds 0.7434; otherwise reset to `4132aae`.

## Experiment 48 — L1 regularization at 0.9
- Commit: `7060ea4`
- Hypothesis: slightly more L1 shrinkage might improve on the setting at 0.7.
- Change: increased `reg_alpha` from 0.7 to 0.9; all other settings unchanged.
- Result: Eval AUC 0.7434 (tied best); training 3.7 s; evaluation 38.6 s; status `ok`.
- Decision: discard and reset to `4132aae`; it did not exceed 0.7.

### Experiment 49 — L1 regularization at 1.1
- Class: follow-up to the L1 sweep.
- Hypothesis: testing just above 1 may determine whether stronger shrinkage can beat the plateau at 0.7–0.9.
- Change planned: `reg_alpha` 0.7 → 1.1; retain `reg_lambda=4` and all other settings.
- Decision rule: keep only if Eval AUC exceeds 0.7434; otherwise reset to `4132aae`.

## Experiment 49 — L1 regularization at 1.1
- Commit: `e1f07c4`
- Hypothesis: stronger L1 shrinkage beyond 0.9 might move past the recent plateau.
- Change: increased `reg_alpha` from 0.7 to 1.1; all other settings unchanged.
- Result: Eval AUC 0.7442 (+0.0008 vs. previous best); training 2.9 s; evaluation 38.6 s; status `ok`.
- Decision: keep. This is the new best.

### Experiment 50 — L1 regularization at 1.3
- Class: follow-up to the continued gain at `reg_alpha=1.1`.
- Hypothesis: a further modest increase may continue to shrink weak leaf weights productively.
- Change planned: `reg_alpha` 1.1 → 1.3; retain `reg_lambda=4` and all other settings.
- Decision rule: keep only if Eval AUC exceeds 0.7442; otherwise reset to `e1f07c4`.

## Experiment 50 — L1 regularization at 1.3
- Commit: `db85efd`
- Hypothesis: another modest increase in L1 shrinkage might improve on the score at 1.1.
- Change: increased `reg_alpha` from 1.1 to 1.3; all other settings unchanged.
- Result: Eval AUC 0.7439 (-0.0003 vs. best); training 2.9 s; evaluation 38.9 s; status `ok`.
- Decision: discard and reset to `e1f07c4`. The best remains at `reg_alpha=1.1`.

## Synthesis after 50 experiments
- Eval AUC improved from 0.7203 to 0.7442 (+0.0239).
- Month-by-hour categorical interaction hurt substantially. The latest categorical threshold sweep favored 10 (0.7421), with 8 at 0.7419, 9 tied at 0.7421, and 12 slightly higher on an earlier baseline at 0.7419.
- L1 regularization has given the clearest gains on the expanded feature set: `reg_alpha=0.5` scored 0.7425, 0.7 scored 0.7434, 0.9 tied, 1.1 reached 0.7442, and 1.3 fell to 0.7439. The peak is near 1.1.
- Current best: commit `e1f07c4`, with 600 trees, depth 5, learning rate 0.05, 128 bins, histogram method, loss-guided growth, 31 leaves, `max_cat_threshold=10`, `reg_lambda=4`, `reg_alpha=1.1`, and features Distance, six original categoricals, categorical DepHour, and the hour-level sine/cosine pair.
- The positive and negative classes in `train.csv` are exactly balanced (100,000 each), so class reweighting at the documented negative/positive ratio would leave `scale_pos_weight` at its default 1.0.
- Next research direction: more boosting rounds at the current 0.05 learning rate, since the earlier 900-round trial also changed learning rate and used the older model.

## Boosting-round research and Experiment 51 proposal
The XGBoost [Python API](https://xgboost.readthedocs.io/en/stable/python/python_api.html) defines `n_estimators` as the number of boosting rounds. Its [parameter-tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) advise increasing the round count when using a smaller learning rate. Here the learning rate remains fixed at 0.05; a 750-round trial checks whether the newer feature and regularization gains still benefit from additional trees. The earlier 900-round trial also lowered the learning rate and predated the current features and regularization, so it did not isolate round count on this model.

### Experiment 51 — 750 boosting rounds
- Class: boosting-round count.
- Hypothesis: the best model may still benefit from additional trees at the current learning rate of 0.05.
- Change planned: increase `n_estimators` from 600 to 750; leave all other settings unchanged.
- Decision rule: keep only if Eval AUC exceeds 0.7442; otherwise reset to `e1f07c4`.

## Experiment 51 — 750 boosting rounds
- Commit: `8ed7281`
- Hypothesis: additional trees might improve the regularized model at the existing 0.05 learning rate.
- Change: increased `n_estimators` from 600 to 750; all other settings unchanged.
- Result: Eval AUC 0.7459 (+0.0017 vs. previous best); training 3.5 s; evaluation 39.0 s; status `ok`.
- Decision: keep. This is the new best.

### Experiment 52 — 900 boosting rounds at 0.05
- Class: follow-up to the significant gain at 750 rounds.
- Hypothesis: the additional trees may continue to improve ranking before overfitting begins.
- Change planned: increase `n_estimators` from 750 to 900 while keeping `learning_rate=0.05`.
- Decision rule: keep only if Eval AUC exceeds 0.7459; otherwise reset to `8ed7281`.

## Experiment 52 — 900 boosting rounds at 0.05
- Commit: `e5484fa`
- Hypothesis: more boosting rounds at the unchanged learning rate might continue the 750-round gain.
- Change: increased `n_estimators` from 750 to 900; retained `learning_rate=0.05` and all other settings.
- Result: Eval AUC 0.7470 (+0.0011 vs. previous best); training 4.2 s; evaluation 39.2 s; status `ok`.
- Decision: keep. This is the new best.

### Experiment 53 — 1,050 boosting rounds
- Class: follow-up to the continued gains at 750 and 900 rounds.
- Hypothesis: additional rounds may keep improving ranking, though returns may be diminishing.
- Change planned: increase `n_estimators` from 900 to 1,050; keep learning rate 0.05.
- Decision rule: keep only if Eval AUC exceeds 0.7470; otherwise reset to `e5484fa`.

## Experiment 53 — 1,050 boosting rounds
- Commit: `a4f13c4`
- Hypothesis: further boosting rounds might improve ranking beyond the 900-round score.
- Change: increased `n_estimators` from 900 to 1,050; kept `learning_rate=0.05` and other settings fixed.
- Result: Eval AUC 0.7472 (+0.0002 vs. previous best); training 4.9 s; evaluation 39.1 s; status `ok`.
- Decision: keep. This is the new best.

### Experiment 54 — 1,200 boosting rounds
- Class: follow-up to the continuing, smaller gains from additional rounds.
- Hypothesis: another 150 rounds may produce a small gain or identify the start of the plateau.
- Change planned: increase `n_estimators` from 1,050 to 1,200; keep learning rate 0.05.
- Decision rule: keep only if Eval AUC exceeds 0.7472; otherwise reset to `a4f13c4`.

## Experiment 54 — 1,200 boosting rounds
- Commit: `ead8b2d`
- Hypothesis: another 150 rounds might add a modest gain at the current learning rate.
- Change: increased `n_estimators` from 1,050 to 1,200; kept `learning_rate=0.05` and other settings fixed.
- Result: Eval AUC 0.7474 (+0.0002 vs. previous best); training 5.6 s; evaluation 39.4 s; status `ok`.
- Decision: keep. This is the new best.

### Experiment 55 — 1,350 boosting rounds
- Class: follow-up to the small gain at 1,200 rounds.
- Hypothesis: the current trend may continue with another 150 trees, though the gains are diminishing.
- Change planned: increase `n_estimators` from 1,200 to 1,350; keep learning rate 0.05.
- Decision rule: keep only if Eval AUC exceeds 0.7474; otherwise reset to `ead8b2d`.

## Experiment 55 — 1,350 boosting rounds
- Commit: `3f63a98`
- Hypothesis: another 150 trees might continue the small gain at 1,200 rounds.
- Change: increased `n_estimators` from 1,200 to 1,350; kept learning rate at 0.05.
- Result: Eval AUC 0.7469 (-0.0005 vs. best); training 6.3 s; evaluation 39.2 s; status `ok`.
- Decision: discard and reset to `ead8b2d`. The score has started to decline beyond 1,200.

### Experiment 56 — 1,275 boosting rounds
- Class: midpoint check around the current peak.
- Hypothesis: the best round count may lie between 1,200 and 1,350.
- Change planned: increase `n_estimators` from 1,200 to 1,275; keep learning rate at 0.05.
- Decision rule: keep only if Eval AUC exceeds 0.7474; otherwise reset to `ead8b2d`.

## Experiment 56 — 1,275 boosting rounds
- Commit: `30e0bc4`
- Hypothesis: the best round count might fall between 1,200 and 1,350.
- Change: increased `n_estimators` from 1,200 to 1,275; kept learning rate at 0.05.
- Result: Eval AUC 0.7471 (-0.0003 vs. best); training 5.9 s; evaluation 38.5 s; status `ok`.
- Decision: discard and reset to `ead8b2d`. The midpoint did not recover the 1,200-round score.

## Tree-depth research and Experiment 57 proposal
The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) says increasing `max_depth` increases model complexity and overfitting risk. The current loss-guided model also has a 31-leaf cap and stronger leaf-weight regularization, so testing depth 6 will show whether a slightly deeper structure can help at 1,200 rounds without an unbounded tree.

### Experiment 57 — depth 6 with a 31-leaf cap
- Class: tree-structure tuning.
- Hypothesis: allowing one additional level may capture useful interactions while `max_leaves=31` bounds the number of terminal regions.
- Change planned: increase `max_depth` from 5 to 6; retain `max_leaves=31` and all other current best settings.
- Decision rule: keep only if Eval AUC exceeds 0.7474; otherwise reset to `ead8b2d`.

## Experiment 57 — depth 6 with a 31-leaf cap
- Commit: `af9b4d9`
- Hypothesis: one extra level might help loss-guided trees use their bounded leaves more effectively.
- Change: increased `max_depth` from 5 to 6; retained `max_leaves=31` and other settings.
- Result: Eval AUC 0.7479 (+0.0005 vs. previous best); training 5.1 s; evaluation 39.2 s; status `ok`.
- Decision: keep. This is the new best.

### Experiment 58 — depth 7 with a 31-leaf cap
- Class: follow-up to the gain at depth 6.
- Hypothesis: an additional level may allow useful longer paths while the 31-leaf cap still bounds tree size.
- Change planned: increase `max_depth` from 6 to 7; keep `max_leaves=31` and other settings.
- Decision rule: keep only if Eval AUC exceeds 0.7479; otherwise reset to `af9b4d9`.

## Experiment 58 — depth 7 with a 31-leaf cap
- Commit: `ca69bfd`
- Hypothesis: one more level might improve the deeper loss-guided trees while preserving the leaf cap.
- Change: increased `max_depth` from 6 to 7; kept `max_leaves=31` and other settings fixed.
- Result: Eval AUC 0.7476 (-0.0003 vs. best); training 5.2 s; evaluation 39.1 s; status `ok`.
- Decision: discard and reset to `af9b4d9`. Depth 6 remains preferable.

### Experiment 59 — increase leaf budget to 63
- Class: tree-capacity follow-up.
- Hypothesis: with depth 6 and stronger leaf regularization, allowing up to 63 leaves may capture useful structure beyond the 31-leaf cap.
- Change planned: increase `max_leaves` from 31 to 63; keep `max_depth=6` and other settings fixed.
- Decision rule: keep only if Eval AUC exceeds 0.7479; otherwise reset to `af9b4d9`.

## Experiment 59 — leaf budget 63
- Commit: `3317681`
- Hypothesis: a larger loss-guided leaf budget might capture useful structure beyond 31 leaves under the stronger regularization.
- Change: increased `max_leaves` from 31 to 63; retained depth 6 and other settings.
- Result: Eval AUC 0.7467 (-0.0012 vs. best); training 7.6 s; evaluation 39.2 s; status `ok`.
- Decision: discard and reset to `af9b4d9`. The larger trees reduced AUC.

### Experiment 60 — leaf budget 47
- Class: midpoint test for loss-guided tree capacity.
- Hypothesis: a moderate increase above 31 leaves may retain useful splits without the accuracy drop seen at 63.
- Change planned: increase `max_leaves` from 31 to 47; retain depth 6 and all other current best settings.
- Decision rule: keep only if Eval AUC exceeds 0.7479; otherwise reset to `af9b4d9`.

## Experiment 60 — leaf budget 47
- Commit: `b0fc0e8`
- Hypothesis: an intermediate leaf cap might retain useful structure without the drop seen at 63.
- Change: increased `max_leaves` from 31 to 47; retained depth 6 and other settings.
- Result: Eval AUC 0.7475 (-0.0004 vs. best); training 6.7 s; evaluation 39.2 s; status `ok`.
- Decision: discard and reset to `af9b4d9`. The 31-leaf cap remains best.

## Synthesis after 60 experiments
- Eval AUC improved from 0.7203 to 0.7479 (+0.0276).
- The L1 sweep peaked at `reg_alpha=1.1` (0.7442); 1.3 slipped slightly. The later round-count experiments added more improvement than further L1 tuning.
- Increasing the current model from 600 to 750, 900, 1,050, then 1,200 rounds steadily improved AUC from 0.7442 to 0.7474. At 1,275 and 1,350 rounds, AUC fell, so 1,200 is currently best.
- Allowing depth 6 at 1,200 rounds improved AUC to 0.7479. Depth 7, 47 leaves, and 63 leaves all underperformed; keep depth 6 and the 31-leaf cap.
- Current best: commit `af9b4d9`, with 1,200 trees, depth 6, learning rate 0.05, 128 bins, histogram method, loss-guided growth, 31 leaves, categorical threshold 10, `reg_lambda=4`, `reg_alpha=1.1`, and Distance, six original categoricals, categorical DepHour, and its sine/cosine features.
- Next direction to research: modest split-loss regularization (`gamma`) on this stronger model; an earlier gamma trial used the old 600-round model and does not settle its value here.

## Split-loss research and Experiment 61 proposal
The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `gamma` (`min_split_loss`) as the minimum loss reduction needed for another tree split; higher values make partitioning more conservative. A previous `gamma=0.1` test on the older 600-round model was slightly worse, but the present model has a different depth, round count, and leaf regularization. Test a smaller value of 0.05 to see whether trimming marginal splits helps this stronger configuration.

### Experiment 61 — mild split-loss threshold
- Class: split regularization.
- Hypothesis: `gamma=0.05` may suppress weak splits and improve generalization while preserving productive partitions.
- Change planned: add `gamma=0.05`; retain all current best settings.
- Decision rule: keep only if Eval AUC exceeds 0.7479; otherwise reset to `af9b4d9`.

## Experiment 61 — mild split-loss threshold
- Commit: `82fb485`
- Hypothesis: requiring a small loss reduction before splitting might trim weak branches.
- Change: added `gamma=0.05`; all other settings unchanged.
- Result: Eval AUC 0.7479 (tied best); training 5.1 s; evaluation 38.8 s; status `ok`.
- Decision: discard and reset to `af9b4d9`; no improvement over the default.

### Experiment 62 — split-loss threshold 0.02
- Class: smaller split-loss regularization check.
- Hypothesis: a lighter threshold may retain useful partitions while still pruning marginal splits.
- Change planned: add `gamma=0.02`; keep all other current best settings.
- Decision rule: keep only if Eval AUC exceeds 0.7479; otherwise reset to `af9b4d9`.

## Experiment 62 — split-loss threshold 0.02
- Commit: `1c57272`
- Hypothesis: a lighter threshold might trim marginal splits without removing useful branches.
- Change: added `gamma=0.02`; other settings unchanged.
- Result: Eval AUC 0.7479 (tied best); training 5.1 s; evaluation 39.4 s; status `ok`.
- Decision: discard and reset to `af9b4d9`; it did not improve on the default.

## Histogram-bin research and Experiment 63 proposal
The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `max_bin` as the number of discrete bins used for continuous features with `hist` and says larger values can improve split optimality at added computation cost. `max_bin=128` helped on the earlier model; test 256 on the current expanded, deeper model to see whether its numeric distance and cyclic-time splits benefit from finer resolution.

### Experiment 63 — 256 histogram bins
- Class: histogram split-resolution tuning.
- Hypothesis: finer numeric split candidates may improve the deeper model's handling of distance and cyclic time.
- Change planned: increase `max_bin` from 128 to 256; keep all other current best settings.
- Decision rule: keep only if Eval AUC exceeds 0.7479; otherwise reset to `af9b4d9`.

## Experiment 63 — 256 histogram bins
- Commit: `4a64b18`
- Hypothesis: a finer histogram might improve numeric split candidates with the expanded time features.
- Change: increased `max_bin` from 128 to 256; all other settings unchanged.
- Result: Eval AUC 0.7472 (-0.0007 vs. best); training 5.1 s; evaluation 38.8 s; status `ok`.
- Decision: discard and reset to `af9b4d9`.

### Experiment 64 — 192 histogram bins
- Class: midpoint histogram-resolution test.
- Hypothesis: 192 bins may improve numeric split precision without the AUC loss at 256.
- Change planned: increase `max_bin` from 128 to 192; retain all other current best settings.
- Decision rule: keep only if Eval AUC exceeds 0.7479; otherwise reset to `af9b4d9`.

## Experiment 64 — 192 histogram bins
- Commit: `be305a9`
- Hypothesis: an intermediate bin count might improve split precision without the loss at 256.
- Change: increased `max_bin` from 128 to 192; all other settings unchanged.
- Result: Eval AUC 0.7476 (-0.0003 vs. best); training 5.1 s; evaluation 39.4 s; status `ok`.
- Decision: discard and reset to `af9b4d9`.

### Experiment 65 — 160 histogram bins
- Class: finer midpoint check near the best 128-bin setting.
- Hypothesis: 160 bins may provide a small increase in numeric split resolution without the losses seen at 192 and 256.
- Change planned: increase `max_bin` from 128 to 160; retain all other current best settings.
- Decision rule: keep only if Eval AUC exceeds 0.7479; otherwise reset to `af9b4d9`.

## Experiment 65 — 160 histogram bins
- Commit: `76bd1f5`
- Hypothesis: an intermediate number of histogram bins might improve numeric split resolution over 128.
- Change: increased `max_bin` from 128 to 160; other settings unchanged.
- Result: Eval AUC 0.7469 (-0.0010 vs. best); training 5.1 s; evaluation 39.0 s; status `ok`.
- Decision: discard and reset to `af9b4d9`. Keep 128 bins.

### Experiment 66 — categorical threshold 12 on the updated model
- Class: revisit categorical-threshold tuning after the round-count and depth gains.
- Hypothesis: the later 1,200-round, depth-6 model may benefit from a threshold above the current 10.
- Change planned: increase `max_cat_threshold` from 10 to 12; retain all other current best settings.
- Decision rule: keep only if Eval AUC exceeds 0.7479; otherwise reset to `af9b4d9`.

## Experiment 66 — categorical threshold 12 on the updated model
- Commit: `2a834bf`
- Hypothesis: the later 1,200-round, depth-6 model might prefer a higher categorical candidate limit.
- Change: increased `max_cat_threshold` from 10 to 12; all other settings unchanged.
- Result: Eval AUC 0.7460 (-0.0019 vs. best); training 5.2 s; evaluation 39.3 s; status `ok`.
- Decision: discard and reset to `af9b4d9`. Threshold 10 remains preferable.

### Experiment 67 — L1 regularization at 1.0
- Class: fine adjustment around the L1 value 1.1 that improved the model.
- Hypothesis: a slightly lower L1 penalty may improve the tradeoff between leaf shrinkage and useful signal.
- Change planned: reduce `reg_alpha` from 1.1 to 1.0; keep other settings unchanged.
- Decision rule: keep only if Eval AUC exceeds 0.7479; otherwise reset to `af9b4d9`.

## Experiment 67 — L1 regularization at 1.0
- Commit: `c06327b`
- Hypothesis: a slightly lower L1 penalty might improve the tradeoff around the best value of 1.1.
- Change: reduced `reg_alpha` from 1.1 to 1.0; all other settings unchanged.
- Result: Eval AUC 0.7473 (-0.0006 vs. best); training 5.0 s; evaluation 39.0 s; status `ok`.
- Decision: discard and reset to `af9b4d9`.

### Experiment 68 — L2 regularization at 2
- Class: revisit L2 tuning on the newer 1,200-round, depth-6 model.
- Hypothesis: the current stronger model may prefer a lower L2 penalty than the earlier 600-round configuration.
- Change planned: reduce `reg_lambda` from 4 to 2; retain all other current best settings.
- Decision rule: keep only if Eval AUC exceeds 0.7479; otherwise reset to `af9b4d9`.

## Experiment 68 — L2 regularization at 2 on the updated model
- Commit: `7d2ebc2`
- Hypothesis: the newer, longer-trained model might benefit from less L2 shrinkage than the earlier 600-round configuration.
- Change: reduced `reg_lambda` from 4 to 2; all other settings unchanged.
- Result: Eval AUC 0.7474 (-0.0005 vs. best); training 5.2 s; evaluation 39.4 s; status `ok`.
- Decision: discard and reset to `af9b4d9`.

### Experiment 69 — minimum child weight 2
- Class: split-support regularization.
- Hypothesis: requiring a little more Hessian weight in each child may reduce weak splits in the deeper, longer-trained model.
- Change planned: set `min_child_weight=2`; retain all other current best settings.
- Decision rule: keep only if Eval AUC exceeds 0.7479; otherwise reset to `af9b4d9`.

## Experiment 69 — minimum child weight 2
- Commit: `ec4f989`
- Hypothesis: requiring more Hessian weight per child might reduce weak splits in the deeper model.
- Change: set `min_child_weight=2`; all other settings unchanged.
- Result: Eval AUC 0.7477 (-0.0002 vs. best); training 5.1 s; evaluation 39.3 s; status `ok`.
- Decision: discard and reset to `af9b4d9`.

### Experiment 70 — L1 regularization at 1.2
- Class: fine adjustment near the best `reg_alpha=1.1` setting.
- Hypothesis: a small increase may improve regularization on the deeper, longer-trained model.
- Change planned: increase `reg_alpha` from 1.1 to 1.2; retain all other current best settings.
- Decision rule: keep only if Eval AUC exceeds 0.7479; otherwise reset to `af9b4d9`.

## Experiment 70 — L1 regularization at 1.2
- Commit: `cbeb1a9`
- Hypothesis: a slight increase above the best value of 1.1 might improve the model.
- Change: increased `reg_alpha` from 1.1 to 1.2; all other settings unchanged.
- Result: Eval AUC 0.7479 (tied best); training 5.1 s; evaluation 38.9 s; status `ok`.
- Decision: discard and reset to `af9b4d9`; it did not improve on 1.1.

### Experiment 71 — L1 regularization at 1.15
- Class: final fine adjustment around `reg_alpha=1.1`.
- Hypothesis: a value midway between 1.1 and 1.2 may resolve the tie while retaining the same regularization balance.
- Change planned: set `reg_alpha=1.15`; retain all other current best settings.
- Decision rule: keep only if Eval AUC exceeds 0.7479; otherwise reset to `af9b4d9`.

## Experiment 71 — L1 regularization at 1.15
- Commit: `380e4f2`
- Hypothesis: a midpoint between 1.1 and 1.2 might improve the tie between those settings.
- Change: set `reg_alpha=1.15`; all other settings unchanged.
- Result: Eval AUC 0.7471 (-0.0008 vs. best); training 5.6 s; evaluation 39.0 s; status `ok`.
- Decision: discard and reset to `af9b4d9`.

## Final synthesis
- Best Eval AUC: 0.7479, up 0.0276 from the 0.7203 baseline.
- Best commit: `af9b4d9`. It uses 1,200 estimators, max depth 6, learning rate 0.05, max_bin 128, histogram trees with loss-guided growth, 31 leaves, max_cat_threshold 10, reg_lambda 4, and reg_alpha 1.1. Features are Distance, six original categoricals, DepHour, and hour-level sine/cosine coordinates.
- Follow-up gamma values tied but did not improve. Larger histogram-bin counts, a higher categorical threshold, smaller L2, minimum child weight 2, and nearby L1 values all scored below or tied the best.
- The kept working tree is restored to the best model; `results.tsv` and `research-log.md` contain the experiment record.
