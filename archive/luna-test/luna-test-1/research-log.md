# Research log — sep28

## Setup and baseline

- Branch: `sep28`
- Baseline commit: `c294417`
- Baseline Eval AUC: `0.7203`
- Baseline model: XGBoost with the starter's six categorical features, two numeric features, 30 trees, depth 6, learning rate 0.1, and native categorical handling.
- Observation: the baseline completed successfully; evaluation dominates runtime (about 30 seconds), leaving ample room for many short experiments.
- Next requirement: research XGBoost binary-classification tuning and airline-delay/tabular feature engineering before the first non-baseline experiment.

## Pre-experiment research (2026-09-28)

Sources:

- [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html): depth increases complexity, while `min_child_weight`, `gamma`, subsampling, column subsampling, and regularization make learning more conservative.
- [XGBoost categorical data](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html): native categorical columns use category-aware splits; optimal partitioning is supported, and categorical columns should be passed with `enable_categorical=True`.
- [Empirical Study on Airline Delay Analysis and Prediction](https://arxiv.org/abs/2002.10254): delay patterns are associated with calendar, airline, and weather/context attributes; this supports testing schedule and carrier/airport representations available in this restricted schema.

The first experiment tests a route interaction because the starter exposes origin and destination separately. The route is fitted only from training categories and computed row-wise inside `prepare`, so it respects the artifact evaluation contract.

## Experiment 1 — discard

- Commit: `1a73a22`
- Hypothesis: a native categorical `Origin-Dest` route feature would capture route-specific delay risk that separate origin and destination columns miss.
- Result: Eval AUC `0.7071`; status `discard`.
- Observation: this was `0.0132` below baseline and increased the serialized artifact from `0.8 MB` to `6.9 MB`. The high-cardinality route feature is not useful with the starter configuration, so it was reverted.

## Experiment 2 — discard

- Commit: `0c4faca`
- Hypothesis: exposing `CRSDepTime // 100` as a separate numeric scheduled-hour feature would make the strong hour-of-day pattern easier to learn than the raw `HHMM` representation.
- Result: Eval AUC `0.7201`; status `discard`.
- Observation: the result was `0.0002` below baseline. Because the numeric feature preserves essentially the same threshold ordering as `CRSDepTime`, it adds little new information and was reverted.

## Experiment 3 — discard

- Commit: `ecd9236`
- Hypothesis: making scheduled departure hour categorical would let native categorical partitioning learn arbitrary groups of hours, beyond the threshold splits already available from `CRSDepTime`.
- Result: Eval AUC `0.7198`; status `discard`.
- Observation: the categorical representation was `0.0005` below baseline and added no useful signal at the starter tree budget. It was reverted.

## Experiment 4 — keep

- Commit: `34f7971`
- Hypothesis: lowering the learning rate from `0.1` to `0.05` and increasing trees from `30` to `100` would produce a smoother, better fit, as recommended by the XGBoost tuning guidance.
- Result: Eval AUC `0.7264`; status `keep`; artifact size `2.6 MB`.
- Observation: this is a `+0.0061` improvement over baseline. The branch now retains the slower, longer boosting schedule as the current best.

## Experiment 5 — keep

- Commit: `57cd9c0`
- Hypothesis: the 100-tree model was still underfit, so doubling the number of rounds at the proven `0.05` learning rate should add useful fit.
- Result: Eval AUC `0.7325`; status `keep`; artifact size `5.1 MB`.
- Observation: this adds another `+0.0061` over experiment 4 and `+0.0122` over baseline. More rounds remain promising.

## Experiment 6 — keep

- Commit: `ad84906`
- Hypothesis: continue increasing the number of rounds at the successful `0.05` learning rate because 100 and 200 trees both improved the score.
- Result: Eval AUC `0.7354`; status `keep`; artifact size `10.0 MB`.
- Observation: another positive step (`+0.0029`) confirms the model is not yet saturated at 200 trees. Training remains well below the one-minute limit.

## Experiment 7 — discard

- Commit: `ca9ecaf`
- Hypothesis: doubling the successful 400-tree schedule to 800 trees might continue the gradual improvement.
- Result: Eval AUC `0.7348`; status `discard`; artifact size `20.0 MB`.
- Observation: the score fell `0.0006` below the 400-tree model, indicating mild overfitting or diminishing returns. Reverted to `ad84906`.

## Experiment 8 — keep

- Commit: `e74507d`
- Hypothesis: the best round count was between 400 and 800, so test the targeted midpoint at 600 trees.
- Result: Eval AUC `0.7359`; status `keep`; artifact size `15.1 MB`.
- Observation: this improves the 400-tree model by `0.0005` and the baseline by `0.0156`; 600 trees is the current best round count.

## Experiment 9 — discard

- Commit: `77b49c4`
- Hypothesis: reducing depth from 6 to 4 could regularize the model while 600 rounds provide sufficient capacity.
- Result: Eval AUC `0.7350`; status `discard`; artifact size `3.9 MB`.
- Observation: the shallower model was `0.0009` below the current best, so the baseline depth 6 remains preferable despite the smaller artifact.

## Experiment 10 — discard

- Commit: `90afb01`
- Hypothesis: depth 8 might capture richer feature interactions than depth 6 at the longer boosting schedule.
- Result: Eval AUC `0.7321`; status `discard`; artifact size `49.8 MB`.
- Observation: deeper trees substantially worsened the score and inflated the artifact, confirming that depth 6 is a better complexity point here.

## Synthesis after 10 non-baseline experiments

- The strongest result so far is `0.7359` at commit `e74507d`: depth 6, learning rate `0.05`, and 600 trees.
- The clearest gain came from slower boosting with more rounds: `30 @ 0.1` scored `0.7203`, `100 @ 0.05` scored `0.7264`, `200 @ 0.05` scored `0.7325`, and `400 @ 0.05` scored `0.7354`.
- Increasing to 800 rounds slightly overfit; 600 was the local peak. Depth 4 and depth 8 both lost to depth 6.
- Simple schedule-hour encodings were redundant or slightly harmful. A high-cardinality route category was strongly harmful, so future feature engineering should prefer compact, train-fitted statistics or low-cardinality transformations rather than raw route categories.
- Next direction: research and test regularization, sampling, and compact target/statistical encodings around the 600-tree depth-6 model.

## Fresh research after 10 experiments (2026-09-28)

Sources:

- [XGBoost notes on parameter tuning](https://xgboost.readthedocs.io/en/release_2.0.0/tutorials/param_tuning.html): recommends `subsample` and `colsample_bytree` as randomness-based overfitting controls, alongside depth, child weight, and split loss.
- [scikit-learn TargetEncoder documentation](https://scikit-learn.org/dev/modules/generated/sklearn.preprocessing.TargetEncoder.html): shrinks category target means toward the global mean and uses cross-fitting for training transforms to prevent leakage and downstream overfitting.
- [Regularized target encoding benchmark](https://epub.ub.uni-muenchen.de/106778/1/s00180-022-01207-6.pdf): simple target means overfit rare levels; smoothing and cross-validation are important for high-cardinality features.
- [Air travel delay feature engineering study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches): emphasizes carrier, route, distance, scheduled timing, and cascading operational context; actual post-departure fields would be leakage here, so only pre-departure variables remain in scope.

The next test starts with `subsample`, which directly addresses the mild overfit seen at 800 trees without adding a fragile feature lookup. Target encodings remain a later option, but should be smoothed and interpreted cautiously because `prepare(train)` cannot safely use per-row target values at evaluation time.

## Experiment 11 — discard

- Commit: `bedbdfe`
- Hypothesis: `subsample=0.8` would decorrelate trees and reduce overfitting at the 600-tree setting.
- Result: Eval AUC `0.7280`; status `discard`.
- Observation: this was `0.0079` below the full-row model, so strong row subsampling is not suitable here. Reverted to `e74507d`.

## Experiment 12 — discard

- Commit: `0ca362d`
- Hypothesis: a route positive-rate lookup smoothed toward the global rate would retain route signal without the overfitting of a native 4,290-level route category.
- Result: Eval AUC `0.7327`; status `discard`.
- Observation: the statistic was `0.0032` below the current best. Even with smoothing 50, route-level target variation was not useful in this model and was reverted.

## Experiment 13 — discard

- Commit: `51ccd92`
- Hypothesis: smoothed airport-level delay rates would retain robust origin/destination effects without the variance of route-level rates.
- Result: Eval AUC `0.7350`; status `discard`.
- Observation: the pair was `0.0009` below the current best, so explicit target-rate lookups are not helping enough to justify their complexity. Reverted to `e74507d`.

## Experiment 14 — discard

- Commit: `fbcd811`
- Hypothesis: a compact native `UniqueCarrier × departure-hour` categorical interaction would capture carrier-specific timing patterns without route-level sparsity.
- Result: Eval AUC `0.7257`; status `discard`; artifact size `21.3 MB`.
- Observation: this was strongly below the current best (`-0.0102`), so native categorical interactions are not promising with this configuration. Reverted to `e74507d`.

## Experiment 15 — discard

- Commit: `c09c3fc`
- Hypothesis: increasing `min_child_weight` from 1 to 5 would prevent weak, low-support leaf splits and improve generalization.
- Result: Eval AUC `0.7345`; status `discard`.
- Observation: the stronger leaf constraint reduced AUC by `0.0014`; reverted to `e74507d`.

## Experiment 16 — keep

- Commit: `3d97dd5`
- Hypothesis: a light `gamma=0.1` split-loss threshold would remove marginal splits without the stronger leaf-size constraint.
- Result: Eval AUC `0.7360`; status `keep`.
- Observation: this is a small `+0.0001` over the previous best. The improvement is modest but comes from a simple, well-motivated one-parameter change.

## Experiment 17 — discard

- Commit: `ff4da35`
- Hypothesis: a stronger `gamma=0.5` threshold might further remove marginal splits.
- Result: Eval AUC `0.7349`; status `discard`.
- Observation: the score fell `0.0011` below `gamma=0.1`; stronger split regularization is too aggressive here. Reverted to `3d97dd5`.

## Experiment 18 — keep

- Commit: `869e434`
- Hypothesis: test a near-default `gamma=0.01` to see whether a tiny split threshold is better than `0.1`.
- Result: Eval AUC `0.7363`; status `keep`.
- Observation: this improved the prior best by `0.0003`, making the light threshold the preferred gamma setting so far.

## Experiment 19 — keep

- Commit: `ede7b44`
- Hypothesis: column subsampling at `0.8` would add useful tree diversity while preserving all rows, unlike the rejected `subsample=0.8` experiment.
- Result: Eval AUC `0.7405`; status `keep`; artifact size `13.6 MB`.
- Observation: a strong `+0.0042` over the previous best confirms column sampling is a promising regularization axis for this feature set.

## Experiment 20 — keep

- Commit: `2ff4ce2`
- Hypothesis: reducing column sampling from `0.8` to `0.7` would add more tree diversity while retaining enough of the eight predictors.
- Result: Eval AUC `0.7418`; status `keep`; artifact size `12.7 MB`.
- Observation: this improves the previous best by `0.0013`; `0.7` is now the preferred column fraction.

## Synthesis after 20 non-baseline experiments

- Current best: commit `2ff4ce2`, Eval AUC `0.7418`, with 600 trees, depth 6, learning rate `0.05`, `gamma=0.01`, and `colsample_bytree=0.7`.
- The dominant gains came from boosting schedule and column sampling. Slower boosting with more rounds improved AUC steadily through 600 trees; 800 began to overfit. Column sampling improved the 600-tree model from `0.7363` at full columns to `0.7405` at `0.8` and `0.7418` at `0.7`.
- Row subsampling was harmful (`0.7280`), as were route and carrier-hour categorical interactions, smoothed route/airport target rates, and depth changes. These failures suggest the native categorical model already extracts the useful low-cardinality effects, and noisy interaction/statistical encodings distract it.
- `gamma` has a shallow optimum near zero: `0.01` beat `0.1`, while `0.5` was harmful. The next search should continue around column sampling and then test other low-risk model parameters such as `max_bin`, `reg_lambda`, or a modest learning-rate/round-count adjustment.

## Fresh research after 20 experiments (2026-09-28)

Sources:

- [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html): `max_bin` controls histogram resolution and increasing it can improve split optimality for continuous features; `reg_lambda` and `reg_alpha` provide L2 and L1 weight regularization.
- [XGBoost DART tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html): dropout can reduce overfitting in long boosted ensembles, though it introduces randomness and can slow training.
- [XGBoost categorical-data tutorial](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html): categorical partitioning and one-hot modes are distinct; the route and carrier-hour failures suggest testing categorical split controls only after simpler numeric parameters.

The next experiment targets `max_bin=512`: the two continuous predictors have roughly 1,200 distinct values each, so the default 256-bin histogram may be coarsening useful schedule/distance thresholds. This is a single, deterministic model change before considering the more stochastic DART booster.

## Experiment 21 — discard

- Commit: `9184b10`
- Hypothesis: increasing histogram resolution from the default 256 bins to 512 would improve continuous split thresholds.
- Result: Eval AUC `0.7416`; status `discard`.
- Observation: the change was `0.0002` below the current best, so the default histogram resolution is sufficient. Reverted to `2ff4ce2`.

## Experiment 22 — keep

- Commit: `9ceeb8b`
- Hypothesis: a modest increase of L2 leaf-weight regularization from 1 to 2 would stabilize the column-subsampled ensemble.
- Result: Eval AUC `0.7425`; status `keep`; artifact size `12.6 MB`.
- Observation: this improved the current best by `0.0007`, supporting light L2 regularization.

## Experiment 23 — keep

- Commit: `3cea599`
- Hypothesis: increasing L2 from 2 to 5 might continue stabilizing the 600-tree, column-subsampled ensemble.
- Result: Eval AUC `0.7429`; status `keep`; artifact size `12.3 MB`.
- Observation: another `+0.0004` improvement supports continuing the L2 sweep.

## Experiment 24 — keep

- Commit: `360b126`
- Hypothesis: increasing L2 regularization from 5 to 10 would continue controlling leaf weights in the high-capacity ensemble.
- Result: Eval AUC `0.7443`; status `keep`; artifact size `12.0 MB`.
- Observation: the gain accelerated to `+0.0014`; stronger L2 remains promising.

## Experiment 25 — keep

- Commit: `8365a8b`
- Hypothesis: continue the increasing L2 trend with `reg_lambda=20`.
- Result: Eval AUC `0.7445`; status `keep`; artifact size `11.7 MB`.
- Observation: a smaller but positive `+0.0002` gain; the L2 curve may be approaching a plateau.

## Experiment 26 — keep

- Commit: `9a4cc36`
- Hypothesis: test a stronger L2 value of 50 after the positive 2 → 5 → 10 → 20 trend.
- Result: Eval AUC `0.7451`; status `keep`; artifact size `11.5 MB`.
- Observation: AUC improved another `+0.0006`; stronger L2 is still helping.

## Experiment 27 — keep

- Commit: `b11e222`
- Hypothesis: continue the positive L2 trend with `reg_lambda=100`.
- Result: Eval AUC `0.7452`; status `keep`; artifact size `11.5 MB`.
- Observation: the gain was only `+0.0001`, indicating the curve is flattening but has not yet reversed.

## Experiment 28 — discard

- Commit: `44c99b6`
- Hypothesis: test `reg_lambda=200` as the next coarse L2 point.
- Result: Eval AUC `0.7449`; status `discard`.
- Observation: the score fell `0.0003` from 100, locating the practical L2 peak near `100`. Reverted to `b11e222`.

## Experiment 29 — keep

- Commit: `1142b89`
- Hypothesis: a small L1 penalty (`reg_alpha=0.1`) could remove weak leaf weights while preserving the successful `reg_lambda=100` shrinkage.
- Result: Eval AUC `0.7457`; status `keep`; artifact size `12.6 MB`.
- Observation: the added L1 term improved AUC by `0.0005`; test a stronger L1 value next.

## Experiment 30 — keep

- Commit: `ea235cd`
- Hypothesis: a stronger L1 penalty (`reg_alpha=1`) might continue the improvement from `reg_alpha=0.1`.
- Result: Eval AUC `0.7463`; status `keep`; artifact size `12.4 MB`.
- Observation: AUC improved another `+0.0006`; the best model now uses both strong L2 (`100`) and moderate L1 (`1`).

## Synthesis after 30 non-baseline experiments

- Current best: commit `ea235cd`, Eval AUC `0.7463`, with 600 trees, depth 6, learning rate `0.05`, `gamma=0.01`, `colsample_bytree=0.7`, `reg_lambda=100`, and `reg_alpha=1`.
- The largest gains came from a slower/longer boosting schedule, column subsampling, and then regularization. Full-column 600-tree AUC was `0.7363`; column sampling at `0.7` raised it to `0.7418`; L2 100 and L1 1 raised it to `0.7463`.
- The L2 sweep rose across 2, 5, 10, 20, 50, and 100, then declined at 200. L1 also improved from 0 to 0.1 to 1. The current model is therefore substantially regularized despite using 600 trees.
- Failed directions include route/airport target encodings, native route and carrier-hour interactions, row subsampling, extra depth, and finer histograms. Compact feature additions have not beaten the tuned model; future work should favor model-level changes or very simple deterministic features.
- Next direction: research whether DART, tree growth policy, categorical split thresholds, or a refined learning-rate/round-count pairing can improve this regularized ensemble.

## Fresh research after 30 experiments (2026-09-28)

Sources:

- [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html): `grow_policy=lossguide` prioritizes nodes with the highest loss change, while `depthwise` grows nodes closest to the root; `max_leaves` controls the leaf budget for histogram/approximate trees.
- [XGBoost DART tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html): dropout is designed to reduce overfitting in long boosted ensembles, with `rate_drop`, normalization, and skip-drop controls; it adds randomness and can slow training.
- [XGBoost categorical-data tutorial](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html): `max_cat_to_onehot=1` forces partitioning, while larger thresholds allow one-hot splits for low-cardinality features. This is a distinct, testable choice from the already rejected interaction features.

The next experiment will test `grow_policy=lossguide` with a leaf budget comparable to depth 6, keeping the strong regularization fixed. This changes how limited tree capacity is allocated and may focus splits on the highest-loss regions without increasing depth.

## Experiment 31 — keep

- Commit: `b60164c`
- Hypothesis: lossguide with `max_leaves=64` would allocate comparable tree capacity to the highest-loss nodes more effectively than depthwise growth.
- Result: Eval AUC `0.7490`; status `keep`; artifact size `14.3 MB`.
- Observation: a strong `+0.0027` over the previous best validates the new growth policy. The next sweep will vary the leaf budget around 64.

## Experiment 32 — discard

- Commit: `d0f88be`
- Hypothesis: reducing lossguide to 32 leaves might preserve its selective-growth benefit with stronger regularization.
- Result: Eval AUC `0.7456`; status `discard`; artifact size `7.6 MB`.
- Observation: the model lost `0.0034` versus 64 leaves, so the extra leaf capacity is important. Reverted to `b60164c`.

## Experiment 33 — keep

- Commit: `6b1203a`
- Hypothesis: increasing lossguide capacity to 128 leaves would improve selective growth after 32 leaves underfit and 64 leaves won.
- Result: Eval AUC `0.7523`; status `keep`; artifact size `27.2 MB`.
- Observation: a strong `+0.0033` over 64 leaves confirms that more selectively allocated capacity is useful.

## Experiment 34 — keep

- Commit: `d767118`
- Hypothesis: doubling lossguide capacity to 256 leaves would continue the positive 32 → 64 → 128 trend.
- Result: Eval AUC `0.7543`; status `keep`; artifact size `50.9 MB`.
- Observation: AUC improved `+0.0020`; training remained under the one-minute limit at about 15 seconds, though artifact size is now a material tradeoff.

## Experiment 35 — keep

- Commit: `ee1f62b`
- Hypothesis: test 512 lossguide leaves as the next capacity point.
- Result: Eval AUC `0.7550`; status `keep`; artifact size `91.8 MB`; training time about 25 seconds.
- Observation: AUC improved `+0.0007`, but the artifact and runtime costs are now significant. An intermediate leaf count will determine whether this is still worth retaining.

## Experiment 36 — discard

- Commit: `4d77d02`
- Hypothesis: 768 lossguide leaves might continue the positive capacity curve beyond 512.
- Result: Eval AUC `0.7548`; status `discard`; artifact size `129.2 MB`; training time about 31 seconds.
- Observation: AUC fell `0.0002` despite the much larger artifact and runtime. The current capacity peak is 512 leaves; reverted to `ee1f62b`.

## Experiment 37 — discard

- Commit: `002ab96`
- Hypothesis: one-hot splits for low-cardinality calendar/carrier categories might complement partitioned airport splits.
- Result: Eval AUC `0.7497`; status `discard`; artifact size `76.0 MB`.
- Observation: the setting lost `0.0053` versus the best and increased training cost, so the existing categorical split behavior is preferable. Reverted to `ee1f62b`.

## Experiment 38 — crash

- Commit: `e2845ff`
- Hypothesis: DART dropout at `rate_drop=0.1` might reduce overfitting in the 512-leaf ensemble.
- Result: Eval AUC unavailable (`0.0000`); status `crash`.
- Observation: training exceeded the harness's 60-second limit and was killed before evaluation. XGBoost also reports that the legacy `booster=dart` path is deprecated. Reverted to `ee1f62b` and will not retry this oversized DART configuration.

## Experiment 39 — keep

- Commit: `e9522d3`
- Hypothesis: capping categorical partition candidates at 32 would reduce noisy airport-category splits.
- Result: Eval AUC `0.7557`; status `keep`; artifact size `92.1 MB`.
- Observation: this improved the 512-leaf best by `0.0007`, validating the categorical regularization direction.

## Experiment 40 — keep

- Commit: `01c9d34`
- Hypothesis: tightening the categorical partition cap from 32 to 16 would further regularize high-cardinality airport splits.
- Result: Eval AUC `0.7566`; status `keep`; artifact size `93.4 MB`.
- Observation: another `+0.0009` gain; the tighter categorical cap is currently best.

## Synthesis after 40 non-baseline experiments

- Current best: commit `01c9d34`, Eval AUC `0.7566`, using 600 trees, lossguide growth, 512 leaves, learning rate `0.05`, `gamma=0.01`, `colsample_bytree=0.7`, `reg_lambda=100`, `reg_alpha=1`, and `max_cat_threshold=16`.
- The largest recent gain came from changing depthwise growth to lossguide and increasing leaves: depthwise best `0.7463`, lossguide 64 `0.7490`, 128 `0.7523`, 256 `0.7543`, and 512 `0.7550`. 768 turned over slightly.
- Categorical partition regularization added another lift: threshold 32 reached `0.7557`, threshold 16 reached `0.7566`. One-hot-for-small-categories hurt, and DART timed out at the 512-leaf capacity.
- The model is now complex and expensive (about 93 MB artifact, 23 seconds training plus 32 seconds evaluation), so future experiments should be high-information and avoid gratuitous capacity increases.
- Next direction: research whether a smaller learning rate with a proportionally larger number of lossguide trees, `max_leaves` refinement, or a modest categorical threshold change can improve AUC within the remaining clock.

## Fresh research after 40 experiments (2026-09-28)

Sources:

- [XGBoost learning-rate/estimator tradeoff](https://www.xgboost.org/concept/xgboost-learning-rate-tuning/): `learning_rate` and `n_estimators` are tightly coupled; smaller steps generally require more trees and can generalize better until a practical floor.
- [XGBoost additive training](https://www.xgboost.org/concept/xgboost-additive-training/): the learning rate scales each tree’s contribution, and early stopping is the standard way to locate the useful round count when a validation set is available.
- [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html): lossguide prioritizes the highest-loss nodes and `max_leaves` caps tree size; categorical thresholds affect partition-based splits.

The earlier learning-rate sweep was done only with depthwise trees. The current lossguide model has a different capacity allocation, so the next test will revisit the coupled schedule with `learning_rate=0.025` and `n_estimators=1200`, keeping the effective step budget near the current 600 × 0.05 configuration.

## Experiment 41 — keep

- Commit: `6a9855c`
- Hypothesis: retuning the lossguide model to 1200 trees at learning rate `0.025` would improve the current 600 × `0.05` schedule.
- Result: Eval AUC `0.7571`; status `keep`; artifact size `188.6 MB`; training time about 47 seconds.
- Observation: AUC improved `+0.0005`. The gain is real but comes with a major artifact/runtime cost, so later experiments should clear a meaningful improvement threshold.

## Experiment 42 — keep

- Commit: `c95874a`
- Hypothesis: reducing `max_cat_threshold` from 16 to 8 would further regularize categorical partitions under the slower schedule.
- Result: Eval AUC `0.7589`; status `keep`; artifact size `205.0 MB`; training time about 49 seconds.
- Observation: A strong `+0.0018` gain confirms the threshold is still an important lever, but the run is close to the training timeout.

## Experiment 43 — keep

- Commit: `c17aff8`
- Hypothesis: reducing `max_cat_threshold` from 8 to 4 would continue the categorical regularization trend.
- Result: Eval AUC `0.7607`; status `keep`; artifact size `247.3 MB`; training time about 50 seconds.
- Observation: another `+0.0018` gain; threshold 4 became the current best, though resource cost is high.

## Experiment 44 — discard

- Commit: `ada6182`
- Hypothesis: test the smallest practical categorical threshold, 2.
- Result: Eval AUC `0.7552`; status `discard`; artifact size `207.0 MB`.
- Observation: the score fell `0.0055` below threshold 4, so further tightening is harmful. Reverted to `c17aff8`.

## Experiment 45 — discard

- Commit: `0e7b78d`
- Hypothesis: threshold 3 might sit between the strong threshold-4 result and the failed threshold-2 result.
- Result: Eval AUC `0.7596`; status `discard`; artifact size `238.3 MB`.
- Observation: threshold 3 was `0.0011` below threshold 4; the best tested categorical cap remains 4. Reverted to `c17aff8`.

## Experiment 46 — discard

- Commit: `967cf14`
- Hypothesis: 576 leaves might suit the slower 1200-tree schedule better than the 512-leaf setting.
- Result: Eval AUC `0.7601`; status `discard`; artifact size `277.2 MB`; training time about 57 seconds.
- Observation: the model lost `0.0006` and approached the timeout, so 512 leaves remains preferable. Reverted to `c17aff8`.

## Experiment 47 — discard

- Commit: `6dc3555`
- Hypothesis: the slower 1200-tree schedule might need stronger L2 than the 600-tree optimum, so test `reg_lambda=200`.
- Result: Eval AUC `0.7600`; status `discard`; artifact size `262.4 MB`.
- Observation: the score fell `0.0007` below `reg_lambda=100`; the previous L2 setting remains best. Reverted to `c17aff8`.

## Experiment 48 — keep

- Commit: `1f97489`
- Hypothesis: increasing L1 from 1 to 2 might continue the earlier positive L1 trend on the slower schedule.
- Result: Eval AUC `0.7616`; status `keep`; artifact size `194.0 MB`.
- Observation: another `+0.0009` gain supports a stronger L1 setting.

## Experiment 49 — discard

- Commit: `a84815b`
- Hypothesis: increasing L1 from 2 to 5 might continue the slower-schedule improvement.
- Result: Eval AUC `0.7615`; status `discard`; artifact size `117.2 MB`.
- Observation: the score was `0.0001` below L1=2, so the local L1 peak is near 2. Reverted to `1f97489`.

## Experiment 50 — discard

- Commit: `9ba100f`
- Hypothesis: reducing column sampling from 0.7 to 0.6 might add useful diversity to the slower 1200-tree model.
- Result: Eval AUC `0.7590`; status `discard`; artifact size `181.8 MB`.
- Observation: the score fell `0.0026`; retain `colsample_bytree=0.7`. Reverted to `1f97489`.

## Synthesis after 50 non-baseline experiments

- Current best: commit `1f97489`, Eval AUC `0.7616`, with 1200 trees, learning rate `0.025`, lossguide growth, 512 leaves, `gamma=0.01`, `colsample_bytree=0.7`, `reg_lambda=100`, `reg_alpha=2`, and `max_cat_threshold=4`.
- The slower lossguide schedule improved the 600-tree winner (`0.7566` → `0.7571` before categorical tuning). Categorical threshold tuning was especially effective: 16 → 8 → 4 raised the score to `0.7607`; 3 and 2 were worse.
- The slow-model L1 retune moved 1 → 2 up to `0.7616`, while 5 dipped. L2=200 and colsample=0.6 both lost, so the current regularization settings are locally selected.
- Capacity beyond 512 leaves was not useful: 576 fell and was close to timeout. DART timed out, and one-hot categorical splits hurt. The current artifact is large (~194 MB) and each run takes about 85 seconds, so remaining tests must target likely gains.
- Next direction: research compact schedule/categorical feature representations or a validation-safe early-stopping-style round selection; avoid more brute-force capacity sweeps unless the hypothesis is strong.

## Fresh research after 50 experiments (2026-09-28)

Sources:

- [Stanford CS229 Airline Departure Delay Prediction](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf): lists day of week, month of year, day of year, airline, origin, destination, scheduled departure time, and distance as relevant pre-departure predictors.
- [Flight delay prediction: evaluating machine-learning algorithms](https://journals.plos.org/plosone/article/file?id=10.1371%2Fjournal.pone.0335141&type=printable): reports engineered temporal features including departure-hour bins and day of year.
- [XGBoost feature interaction constraints](https://xgboost.readthedocs.io/en/release_2.0.0/tutorials/feature_interaction_constraint.html): explains that unconstrained deep trees can capture spurious interactions, motivating compact domain features instead of indiscriminately increasing interaction capacity.

The next experiment will add numeric day-of-year from the existing month/day columns. It is deterministic, row-local, and low-dimensional; unlike the failed route/hour interaction categories, it may let lossguide represent broad seasonal intervals across month boundaries.

## Experiment 51 — keep

- Commit: `165c839`
- Hypothesis: an ordered numeric day-of-year feature would expose seasonal continuity across month boundaries without adding a high-cardinality category.
- Result: Eval AUC `0.7653`; status `keep`; artifact size `188.1 MB`.
- Observation: a strong `+0.0037` gain confirms seasonal ordering is valuable. The feature is deterministic and row-local, so it remains valid under row-by-row evaluation.

## Experiment 52 — keep

- Commit: `3488ee6`
- Hypothesis: adding sine/cosine coordinates for the 365-day cycle would complement numeric day-of-year by representing circular seasonality.
- Result: Eval AUC `0.7662`; status `keep`; artifact size `172.4 MB`.
- Observation: the cyclic pair added `+0.0009`; seasonal features remain useful and compact.

## Experiment 53 — discard

- Commit: `61e028f`
- Hypothesis: cyclic scheduled-time coordinates would add useful midnight-aware geometry beyond raw `HHMM`.
- Result: Eval AUC `0.7653`; status `discard`; artifact size `172.0 MB`.
- Observation: the time pair erased the `+0.0009` seasonal-cyclic gain, so raw scheduled time is already sufficient for this model. Reverted to `3488ee6`.

## Experiment 54 — discard

- Commit: `0bea429`
- Hypothesis: an explicit weekend bit would make the Saturday/Sunday grouping available despite the categorical partition cap.
- Result: Eval AUC `0.7661`; status `discard`; artifact size `178.9 MB`.
- Observation: the result was `0.0001` below the cyclic-seasonal model, so the extra bit adds no useful signal. Reverted to `3488ee6`.

## Experiment 55 — discard

- Commit: `5571f1a`
- Hypothesis: an 84-level month-by-weekday category would capture seasonal weekday effects with adequate support.
- Result: Eval AUC `0.7656`; status `discard`; artifact size `184.4 MB`.
- Observation: the interaction was `0.0006` below the cyclic-seasonal model, so the existing calendar features are preferable. Reverted to `3488ee6`.

## Experiment 56 — discard

- Commit: `e1ad213`
- Hypothesis: raw `DayofMonth` might be redundant after adding numeric and cyclic day-of-year features, so removing it could reduce noise.
- Result: Eval AUC `0.7629`; status `discard`; artifact size `183.8 MB`.
- Observation: the ablation lost `0.0033`; raw day-of-month remains useful. Reverted to `3488ee6`.

## Experiment 57 — discard

- Commit: `9dc4923`
- Hypothesis: raw month might be redundant after adding numeric and cyclic day-of-year features.
- Result: Eval AUC `0.7656`; status `discard`; artifact size `183.9 MB`.
- Observation: removing month cost `0.0006`; retain both raw month and derived seasonal features. Reverted to `3488ee6`.

## Experiment 58 — discard

- Commit: `2709dce`
- Hypothesis: cosine might be redundant given numeric day-of-year and sine.
- Result: Eval AUC `0.7657`; status `discard`; artifact size `187.1 MB`.
- Observation: removing cosine cost `0.0005`, so retain both cyclic coordinates. Reverted to `3488ee6`.

## Experiment 59 — discard

- Commit: `4d4d69b`
- Hypothesis: sine might be redundant given numeric day-of-year and cosine.
- Result: Eval AUC `0.7659`; status `discard`; artifact size `188.2 MB`.
- Observation: removing sine cost `0.0003`; retain both cyclic coordinates. Reverted to `3488ee6`.

## Experiment 60 — keep

- Commit: `7e80331`
- Hypothesis: increasing L1 from 2 to 3 could improve the seasonal-feature model after adding day-of-year and cyclic coordinates.
- Result: Eval AUC `0.7667`; status `keep`; artifact size `138.1 MB`.
- Observation: AUC improved `+0.0005`; the best current model uses `reg_alpha=3`.

## Synthesis after 60 non-baseline experiments

- Current best: commit `7e80331`, Eval AUC `0.7667`, with numeric and cyclic day-of-year features, 1200 lossguide trees at learning rate `0.025`, 512 leaves, `gamma=0.01`, `colsample_bytree=0.7`, `reg_lambda=100`, `reg_alpha=3`, and `max_cat_threshold=4`.
- The strongest feature gain was numeric day-of-year (`0.7616` → `0.7653`), followed by its sine/cosine pair (`0.7662`). Both cyclic coordinates matter: removing cosine scored `0.7657`, removing sine `0.7659`.
- Raw month and day-of-month remain complementary; both ablations lost. Weekend and month-weekday interaction features did not help. L1 retuning from 2 to 3 added another `+0.0005`.
- The model remains resource-heavy but current runs stay under the 60-second training limit. The remaining search should favor small, well-motivated calendar/schedule features or a final regularization check, then finish with the best kept commit.

## Fresh research after 60 experiments (2026-09-29)

Sources:

- [scikit-learn time-related feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html): sine/cosine transformations preserve periodic continuity, and complementary cyclic coordinates are useful when the first and last values should be adjacent.
- [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html): feature weights can alter the probability that a feature is selected under column sampling; this is separate from changing `colsample_bytree` itself.
- [XGBoost feature-weight example](https://xgboost.readthedocs.io/en/release_1.7.0/python/examples/feature_weights.html): demonstrates supplying feature weights to the XGBoost data interface for column sampling.

The current model has a proven seasonal feature block but samples only 70% of columns per tree. The next test will give the three seasonal features a modestly higher selection weight, allowing the model to see them more often without increasing the total feature fraction or adding new data-derived statistics.

## Experiment 61 — discard

- Commit: `f797bce`
- Hypothesis: feature weights of 2 for the seasonal block would make the proven features appear more often under column sampling.
- Result: Eval AUC `0.7665`; status `discard`; artifact size `134.6 MB`.
- Observation: the weighted model was `0.0002` below the unweighted best, and XGBoost deprecated fit-time feature weights in this environment. Reverted to `7e80331`.

## Experiment 62 — discard

- Commit: `f57a6e4`
- Hypothesis: threshold 5 might improve on the current threshold-4 setting after adding seasonal features.
- Result: Eval AUC `0.7666`; status `discard`.
- Observation: the score was `0.0001` below the best, so threshold 4 remains selected. Reverted to `7e80331`.

## Experiment 63 — discard

- Commit: `463f470`
- Hypothesis: increasing L1 from 3 to 4 might continue the seasonal-model improvement.
- Result: Eval AUC `0.7665`; status `discard`.
- Observation: the score fell `0.0002`; retain `reg_alpha=3`. Reverted to `7e80331`.

## Experiment 64 — discard

- Commit: `94c185b`
- Hypothesis: a midpoint `colsample_bytree=0.75` might improve the seasonal model over 0.7.
- Result: Eval AUC `0.7666`; status `discard`.
- Observation: the score was `0.0001` below the best; retain 0.7. Reverted to `7e80331`.

## Experiment 65 — discard

- Commit: `0e901bb`
- Hypothesis: a four-level quarter category would provide a direct coarse season grouping under the categorical threshold cap.
- Result: Eval AUC `0.7666`; status `discard`; artifact size `142.7 MB`.
- Observation: the result was `0.0001` below the best and added no signal beyond the day-of-year block. Reverted to `7e80331`.

## Final summary

- The two-hour search window completed with 65 non-baseline experiments.
- Baseline: commit `c294417`, Eval AUC `0.7203`.
- Best final commit: `7e80331`, Eval AUC `0.7667`, an absolute improvement of `0.0464`.
- The final model uses native categorical features plus numeric and cyclic day-of-year features, with 1200 lossguide trees, 512 leaves, learning rate `0.025`, `gamma=0.01`, `colsample_bytree=0.7`, `reg_lambda=100`, `reg_alpha=3`, and `max_cat_threshold=4`.
- The largest improvement came from adding day-of-year and its sine/cosine representation. Slower boosting, lossguide growth, categorical-threshold tuning, column sampling, and regularization also contributed. Route/target encodings, schedule interactions, row subsampling, DART, feature weighting, and quarter grouping did not improve the score.
- The branch remains on the best kept commit `7e80331`. `results.tsv` and this research log are intentionally uncommitted per the experiment protocol.
