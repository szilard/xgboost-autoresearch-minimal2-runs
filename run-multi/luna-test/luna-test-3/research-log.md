# Research log — sep29

## Baseline — c294417

- Hypothesis: establish the untouched starter performance before changing anything.
- Result: Eval AUC 0.7203; status `keep`.
- Configuration: six native categorical columns, `CRSDepTime` and `Distance`, 30 trees, depth 6, learning rate 0.1, categorical XGBoost enabled.
- Observation: the harness completed successfully; evaluation dominates runtime (~30.8s versus ~1.1s training).

## Experiment 1 — boosting capacity — 0116998

- Classification: exploration.
- Hypothesis: the 30-tree baseline may be underfit. Following the XGBoost parameter-tuning guidance that a lower `eta` should be paired with more boosting rounds, 100 trees at learning rate 0.05 may improve ranking while keeping the same depth and features.
- Source: [XGBoost parameter-tuning notes](https://xgboost.readthedocs.io/en/release_1.7.0/tutorials/param_tuning.html).
- Result: Eval AUC 0.7264; status `keep` (+0.0061 versus baseline).
- Observation: the larger model remained well within the 60-second training and 5-minute evaluation limits.

## Experiment 2 — slower, longer boosting (pending)

- Classification: follow-up to the promising Experiment 1.
- Hypothesis: if 100 trees at 0.05 is still improving underfit, 200 trees at 0.025 may continue the smoother optimization and improve ranking further. This changes the number of rounds and step size together while keeping the same total feature/model family.
- Result: Eval AUC 0.7263; status `discard` (-0.0001 versus Experiment 1).
- Observation: extending the smoother schedule past 100 trees did not help, so the next tests should target representation or tree structure rather than simply adding rounds.

## Experiment 3 — categorical partitioning (pending)

- Classification: exploration.
- Hypothesis: forcing optimal partitioning for all native categorical features may let the model group similar months, weekdays, or carriers instead of making one-hot-style splits. This is a representation/split-strategy change, while retaining the best boosting schedule.
- Source: [XGBoost categorical-data documentation](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html).
- Result: Eval AUC 0.7264; status `discard` (equal to the best).
- Observation: the extra split-strategy parameter did not improve ranking, so the simpler native-categorical default remains preferable.

## Experiment 4 — route interaction (pending)

- Classification: exploration.
- Hypothesis: origin and destination are currently available only as separate features. A native categorical directed `Origin-Dest` route can expose route-specific delay behavior directly; the training data has 4,290 routes and a median of 32 examples per route, so this should not be dominated by singleton categories.
- Source: [Flight Delay Prediction using Airport Situational Awareness Map](https://arxiv.org/abs/1911.01605), which motivates spatial/airport context and historical flight information as useful predictors of departure delay.
- Result: Eval AUC 0.7097; status `discard` (-0.0167 versus the best).
- Observation: direct high-cardinality route categoricals overfit or interact poorly with native categorical splits here, and increased evaluation time from ~31s to ~48s. Keep route interactions out unless represented more compactly.

## Experiment 5 — true scheduled-departure minutes (pending)

- Classification: exploration.
- Hypothesis: `CRSDepTime` is encoded as HHMM, so its numeric gaps are not proportional to elapsed time around each hour. Adding minutes since midnight may give tree splits a cleaner time-of-day representation without removing the original feature.
- Source: [Flight Delay Prediction using Airport Situational Awareness Map](https://arxiv.org/abs/1911.01605), which identifies scheduled timing and temporal context as part of departure-delay prediction, and [flight-delay feature-engineering research](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches), which includes hour/time-block features.
- Result: Eval AUC 0.7264; status `discard` (equal to the best).
- Observation: the corrected time scale did not improve ranking and increased evaluation time, so the raw schedule feature is sufficient for now.

## Experiment 6 — shallower trees (pending)

- Classification: ablation/simplification.
- Hypothesis: depth 6 may be fitting noisy interactions among the categorical fields. A depth-4 model could generalize better and also be simpler/faster, while retaining the schedule that improved the baseline.
- Source: [XGBoost parameter-tuning notes](https://xgboost.readthedocs.io/en/release_1.7.0/tutorials/param_tuning.html), which identify `max_depth` as a primary complexity/overfitting control.
- Result: Eval AUC 0.7190; status `discard` (-0.0074 versus the best).
- Observation: the shallower trees lost useful interactions, so depth 6 remains the working point.

## Experiment 7 — deeper trees (pending)

- Classification: follow-up to the depth ablation.
- Hypothesis: since depth 4 underfit, depth 8 may capture useful carrier/airport/time interactions that depth 6 misses; the main risk is overfitting.
- Result: Eval AUC 0.7290; status `keep` (+0.0026 versus the prior best).
- Observation: depth 8 captures useful higher-order interactions and remains comfortably within the harness limits.

## Experiment 8 — row/feature subsampling regularization (pending)

- Classification: follow-up to a promising result.
- Hypothesis: deeper trees improve the signal but may also fit noise. XGBoost’s documented `subsample` and `colsample_bytree` controls can inject diversity and reduce overfitting; testing both at 0.8 may retain the depth-8 gain while improving generalization.
- Source: [XGBoost parameter-tuning notes](https://xgboost.readthedocs.io/en/release_1.7.0/tutorials/param_tuning.html).
- Result: Eval AUC 0.7349; status `keep` (+0.0059 versus the prior best).
- Observation: adding stochastic row and feature sampling substantially improved the depth-8 model.

## Experiment 9 — row-subsampling ablation (pending)

- Classification: ablation of a promising result.
- Hypothesis: with only eight base predictors, dropping features may be unnecessarily noisy; retaining `subsample=0.8` but using all features per tree may match or exceed the combined regularization result.
- Result: Eval AUC 0.7273; status `discard` (-0.0076 versus the combined subsampling model).
- Observation: feature subsampling is the essential component of the regularization gain; keep both `subsample=0.8` and `colsample_bytree=0.8`.

## Synthesis after 10 runs

- Best result: Eval AUC 0.7349 at `b864405` (depth 8, 100 trees, learning rate 0.05, row and feature subsampling 0.8).
- What helped: moving from 30 to 100 trees at a smaller learning rate (+0.0061), increasing depth from 6 to 8 (+0.0026), and adding both row and feature subsampling (+0.0059).
- What did not help: 200 very-small-step trees, forcing categorical partitioning, minutes-since-midnight, and a direct high-cardinality route category. Depth 4 underfit; row subsampling without feature subsampling was much worse.
- Current theory: this dataset has useful nonlinear interactions among the existing eight predictors, but native high-cardinality categorical interactions are risky. Model regularization through feature diversity is currently more valuable than adding raw route/time columns.
- Next direction: investigate compact, train-fitted group statistics or lower-dimensional time/airport encodings, and test remaining XGBoost structural controls deliberately rather than adding another high-cardinality categorical.

## Experiment 11 — smoothed category delay rates (pending)

- Classification: exploration.
- Hypothesis: compact numeric priors for carrier, origin, and destination may expose the ordering of category-level delay risk more directly than native categorical splits. Each lookup is smoothed toward the global training rate and fitted once from `train`; `prepare(df)` only maps the current row’s category, so it remains valid under row-wise evaluation.
- Leakage caution: target encoding can overfit when the same labels are used to encode training rows. The smoothing strength (20 observations) should reduce this risk; the result will be judged only by the harness’s unseen `eval.csv` score.
- Sources: [CatBoost’s ordered categorical-feature paper](https://arxiv.org/abs/1706.09516) and [scikit-learn’s target-encoder cross-fitting example](https://sklearn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html).
- Result: Eval AUC 0.7330; status `discard` (-0.0019 versus the best).
- Observation: these full-training target lookups likely introduced prediction-shift/overfit despite smoothing; do not keep this encoding in the final model.

## Experiment 12 — longer schedule on the regularized deep model (pending)

- Classification: follow-up to a promising result.
- Hypothesis: the earlier 200-tree/0.025 test used depth 6 with no subsampling, so its neutral result does not rule out a smoother schedule for the current depth-8, subsampled model. Doubling rounds while halving the step size may improve ranking under the stronger regularization.
- Result: Eval AUC 0.7366; status `keep` (+0.0017 versus the previous best).
- Observation: the regularized deeper model benefits from additional low-rate boosting rounds.

## Experiment 13 — minimum child weight (pending)

- Classification: follow-up to a promising result.
- Hypothesis: `min_child_weight=5` may prevent depth-8 trees from making low-support splits that do not generalize, while preserving the useful higher-order structure. XGBoost documents this parameter as a direct tree-complexity control.
- Source: [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html).
- Result: Eval AUC 0.7361; status `discard` (-0.0005 versus the best).
- Observation: modest child-weight regularization was slightly harmful; retain the default of 1.

## Experiment 14 — finer histogram bins (pending)

- Classification: exploration.
- Hypothesis: the default 256 histogram bins may coarsen useful thresholds in scheduled departure time and distance. Doubling to 512 should give the depth-8 model more precise continuous splits, with little risk of categorical-route overfitting because no new categorical features are added.
- Source: [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html), which states that increasing `max_bin` improves split optimality at increased computation cost.
- Result: Eval AUC 0.7359; status `discard` (-0.0007 versus the best).
- Observation: the default histogram resolution is adequate; additional bins added cost without generalization benefit.

## Experiment 15 — categorical departure hour (pending)

- Classification: exploration.
- Hypothesis: the raw HHMM schedule may obscure hour-specific delay regimes. Adding a 24-level categorical `DepHour` gives native XGBoost a direct time-block feature while remaining compact and row-local; this is distinct from the previously neutral continuous minutes feature.
- Source: [flight-delay feature-engineering research](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches), which identifies hour/time-block features as useful temporal inputs.
- Result: Eval AUC 0.7335; status `discard` (-0.0031 versus the best).
- Observation: the native model already extracts the useful schedule signal from HHMM; the extra categorical representation is harmful here.

## Experiment 16 — stronger feature subsampling (pending)

- Classification: follow-up to a promising result.
- Hypothesis: the 0.8 feature fraction was beneficial; lowering it modestly to 0.7 may further decorrelate deep trees and improve the ensemble, while retaining the 0.8 row fraction and all other settings.
- Result: Eval AUC 0.7376; status `keep` (+0.0010 versus the prior best).
- Observation: the feature-subsampling optimum is not yet saturated; stronger column diversity helped again.

## Experiment 17 — still stronger feature subsampling (pending)

- Classification: follow-up to a promising result.
- Hypothesis: lowering `colsample_bytree` to 0.6 may further reduce correlated deep-tree errors; the risk is losing too many of the eight predictors in each tree.
- Result: Eval AUC 0.7391; status `keep` (+0.0015 versus the prior best).
- Observation: stronger feature diversity continued to help; a lower bound test can identify where signal loss begins.

## Experiment 18 — half-feature subsampling (pending)

- Classification: follow-up to a promising result.
- Hypothesis: with eight predictors and deep trees, sampling half the columns per tree may further reduce correlated errors. This is the next point after two consecutive gains at 0.8 and 0.7/0.6.
- Result: Eval AUC 0.7391; status `discard` (equal to the best).
- Observation: further column reduction did not improve ranking; retain 0.6 as the simplest best-performing point in this sweep.

## Experiment 19 — stronger row subsampling (pending)

- Classification: follow-up to a promising result.
- Hypothesis: with `colsample_bytree=0.6` now supplying strong feature diversity, reducing `subsample` from 0.8 to 0.7 may further decorrelate the 200 deep trees and improve AUC.
- Result: Eval AUC 0.7376; status `discard` (-0.0015 versus the best).
- Observation: the 0.8 row fraction is better when paired with 0.6 column sampling; keep row subsampling at 0.8.

## Experiment 20 — deeper trees with stronger feature sampling (pending)

- Classification: follow-up to a promising result.
- Hypothesis: the earlier depth-8 improvement may reflect useful interactions that become clearer with depth 10, now that column sampling at 0.6 is reducing overfit. The main risk is excessive tree complexity.
- Result: Eval AUC 0.7461; status `keep` (+0.0070 versus the prior best).
- Observation: depth 10 unlocks a large gain when paired with feature sampling; previous depth-8 results understated the useful interaction order.

## Synthesis after 20 runs

- Best result: Eval AUC 0.7461 at `bea6014` (200 trees, learning rate 0.025, depth 10, `subsample=0.8`, `colsample_bytree=0.6`).
- What helped: deeper trees (6→8→10), longer low-rate boosting on the regularized model, and feature subsampling. Column sampling improved monotonically from 0.8 to 0.6; 0.5 tied rather than improved. Row sampling below 0.8 hurt.
- What did not help: high-cardinality route categories, categorical hour/minutes features, target-rate lookups, higher histogram resolution, `min_child_weight=5`, and depth 4. Categorical representation is best left to the starter columns.
- Current theory: the signal is in high-order interactions among the existing fields, with stochastic column sampling acting as the main anti-overfit mechanism. The next likely gains are deeper/longer model capacity or carefully chosen regularization, not broad feature expansion.
- Next direction: test depth 12 and/or schedule refinement, then investigate gamma/L1/L2 or compact interactions only if the deeper model plateaus.

## Experiment 21 — depth twelve (pending)

- Classification: follow-up to a promising result.
- Hypothesis: depth 10 produced the largest gain so far; depth 12 may capture still richer airport/carrier/time interactions, with `colsample_bytree=0.6` providing regularization against the added complexity.
- Result: Eval AUC 0.7497; status `keep` (+0.0036 versus the prior best).
- Observation: the depth trend is still positive, although model size rose to ~90 MB.

## Experiment 22 — depth fourteen (pending)

- Classification: follow-up to a promising result.
- Hypothesis: depth 12 is still improving, so depth 14 may capture additional high-order interactions. The explicit 0.6 column sampling should limit the effective complexity; watch the 60-second training and 5-minute evaluation limits.
- Result: Eval AUC 0.7497; status `discard` (tied the best).
- Observation: depth 14 added substantial model size and time without improving AUC; depth 12 is the complexity frontier so far.

## Experiment 23 — finer 300-tree schedule (pending)

- Classification: follow-up to a promising result.
- Hypothesis: 200 trees at 0.025 is strong at depth 12, but 300 smaller updates at 0.0167 may fit the same total boosting strength more smoothly and improve ranking. The extra model size is acceptable if AUC improves within the harness limits.
- Result: Eval AUC 0.7493; status `discard` (-0.0004 versus the best).
- Observation: more, smaller updates did not help and substantially increased artifact size; retain 200 trees at 0.025.

## Experiment 24 — small split-loss regularization (pending)

- Classification: exploration of tree regularization.
- Hypothesis: depth 12 may contain weak late splits even though `min_child_weight=5` was harmful. A small `gamma=0.1` requires a positive loss reduction for each split and could prune only the noisiest additions.
- Source: [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html), which defines `gamma`/`min_split_loss` as the minimum loss reduction required for another partition.
- Result: Eval AUC 0.7498; status `keep` (+0.0001 versus the prior best).
- Observation: a small split-loss threshold gave a marginal but positive improvement with lower model size.

## Experiment 25 — stronger split-loss regularization (pending)

- Classification: follow-up to a promising result.
- Hypothesis: increasing `gamma` from 0.1 to 0.5 may prune more weak deep splits and improve generalization; the risk is removing useful rare interactions.
- Result: Eval AUC 0.7493; status `discard` (-0.0005 versus the best).
- Observation: the marginal benefit is specific to a very small threshold; use gamma 0.1 if retaining this direction.

## Experiment 26 — stronger L2 leaf regularization (pending)

- Classification: exploration of tree regularization.
- Hypothesis: `reg_lambda=5` may make the deep model’s leaf scores more conservative and improve out-of-sample ranking while preserving the useful depth-12 interactions.
- Source: [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html), which describes `reg_lambda` as L2 regularization that makes the model more conservative.
- Result: Eval AUC 0.7510; status `keep` (+0.0012 versus the prior best).
- Observation: deeper trees benefit from stronger L2 shrinkage; this is the second useful regularization change after gamma 0.1.

## Experiment 27 — stronger L2 regularization (pending)

- Classification: follow-up to a promising result.
- Hypothesis: increasing `reg_lambda` from 5 to 10 may further stabilize the depth-12 leaf estimates; the risk is suppressing useful rare interactions.
- Result: Eval AUC 0.7505; status `discard` (-0.0005 versus the best).
- Observation: L2=5 is near the useful optimum; doubling it over-regularizes slightly.

## Experiment 28 — small L1 regularization (pending)

- Classification: exploration of complementary regularization.
- Hypothesis: `reg_alpha=0.1` may remove weak leaf weights that L2 does not sparsify, improving the depth-12 model while retaining `reg_lambda=5` and `gamma=0.1`.
- Source: [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html), which defines `reg_alpha` as L1 regularization and `reg_lambda` as L2 regularization.
- Result: Eval AUC 0.7511; status `keep` (+0.0001 versus the prior best).
- Observation: a small L1 complement is marginally helpful; test one stronger value before settling.

## Experiment 29 — stronger L1 regularization (pending)

- Classification: follow-up to a promising result.
- Hypothesis: `reg_alpha=0.5` may improve sparsity further, but could remove rare useful interactions in the deep trees.
- Result: Eval AUC 0.7519; status `keep` (+0.0008 versus the prior best).
- Observation: moderate L1 plus L2 and a small gamma is the strongest regularization combination so far.

## Synthesis after 30 runs

- Best result: Eval AUC 0.7519 at `ab271ef` (200 trees, learning rate 0.025, depth 12, `subsample=0.8`, `colsample_bytree=0.6`, `gamma=0.1`, `reg_lambda=5`, `reg_alpha=0.5`).
- What helped: increasing depth to 12, lowering the learning rate with 200 trees, feature subsampling, and then moderate L2/L1/split-loss regularization. The depth gains were especially large (0.7290 at depth 8, 0.7461 at depth 10, 0.7497 at depth 12).
- What did not help: depth 14, 300 finer trees, stronger gamma, lambda 10, categorical/route/time feature additions, target rates, and stronger row sampling. Depth 14 tied but was much larger.
- Current theory: model capacity plus carefully balanced regularization is extracting interactions among the original features; the held-out score is now mostly sensitive to tree shape and leaf shrinkage, not extra representations.
- Next direction: tune the remaining schedule/regularization neighborhood (learning rate/rounds, subsample, or interaction constraints only if well motivated) and avoid high-cardinality feature additions.

## Experiment 31 — loss-guided tree growth (pending)

- Classification: exploration of tree structure.
- Hypothesis: depth-wise trees spend capacity at every level, while XGBoost’s `lossguide` policy grows the leaf with the largest loss change. With `max_leaves=512`, this may focus capacity on the most valuable interactions and outperform the depth-12 depth-wise trees while avoiding an unbounded model.
- Source: [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html), which documents `grow_policy` and `max_leaves` for `hist`/`approx` tree methods.
- Result: Eval AUC 0.7489; status `discard` (-0.0030 versus the best).
- Observation: depth-wise growth is materially better for this feature set; the leaf-wise alternative is not worth pursuing further.

## Experiment 32 — lighter row subsampling (pending)

- Classification: follow-up to the sampling sweep.
- Hypothesis: `subsample=0.9` may keep the useful variance reduction from row sampling while avoiding the loss seen at 0.7; feature sampling remains fixed at the strong 0.6 value.
- Result: Eval AUC 0.7522; status `keep` (+0.0003 versus the prior best).
- Observation: with gamma/L1/L2 active, retaining more rows per tree is slightly better.

## Experiment 33 — near-full row sampling (pending)

- Classification: follow-up to a promising result.
- Hypothesis: `subsample=0.95` may improve further by reducing row-sampling noise while retaining a small amount of ensemble diversity; compare directly to 0.9.
- Result: Eval AUC 0.7523; status `keep` (+0.0001 versus the prior best).
- Observation: the score continues to rise toward full row usage; feature sampling and leaf regularization appear to be doing most of the useful regularization.

## Experiment 34 — full row sampling (pending)

- Classification: follow-up to a promising result.
- Hypothesis: with `colsample_bytree=0.6`, gamma, L1, and L2 all active, `subsample=1.0` may remove unnecessary row noise and improve the final model slightly.
- Result: Eval AUC 0.7506; status `discard` (-0.0017 versus the best).
- Observation: retaining a small amount of row stochasticity matters; keep `subsample=0.95`.

## Experiment 35 — fine column-sampling adjustment (pending)

- Classification: follow-up to the sampling sweep.
- Hypothesis: the best unregularized point was 0.6 and 0.5 tied it; with the current leaf regularization, an intermediate `colsample_bytree=0.55` may balance feature diversity and retaining signal slightly better.
- Result: Eval AUC 0.7523; status `discard` (equal to the best).
- Observation: 0.6 remains the simplest selected column fraction; the local optimum is broad but does not reward the extra tuning.

## Experiment 36 — larger categorical partition budget (pending)

- Classification: exploration of native categorical handling.
- Hypothesis: `Origin` and `Dest` have 283 levels, while XGBoost’s partition split search can cap the categories considered per split. Raising `max_cat_threshold` to 256 may recover useful airport groupings that the default cap misses, with the current sampling and leaf regularization guarding against overfit.
- Source: [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html), which describes `max_cat_threshold` as the maximum categories considered for partition-based splits to control overfitting.
- Result: Eval AUC 0.7525; status `keep` (+0.0002 versus the prior best).
- Observation: more complete airport-category partition search gives a marginal gain.

## Experiment 37 — effectively unrestricted categorical threshold (pending)

- Classification: follow-up to a promising result.
- Hypothesis: with 283 origin/destination levels, `max_cat_threshold=512` should consider all categories in each partition search and may improve slightly beyond 256; the risk is category overfit and slower training.
- Result: Eval AUC 0.7523; status `discard` (-0.0002 versus the best).
- Observation: considering every airport category is slightly too flexible; retain the 256 threshold.

## Experiment 38 — carrier-by-hour interaction (pending)

- Classification: exploration of compact feature interactions.
- Hypothesis: carrier delay patterns may vary by scheduled hour. A `UniqueCarrier × hour` categorical has only 401 observed levels (median 360 rows per level), much denser than the failed 4,290-level route feature, and may expose a useful interaction directly.
- Source: [flight-delay feature-engineering research](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches), which identifies carrier and departure-time features as complementary predictors.
- First attempt: status `crash` at `29f8d93`; the category-level lookup accidentally used the full Series rather than `.unique()`, so `pandas.Categorical` rejected duplicate categories before training. The implementation is corrected in the rerun commit.
- Rerun result: Eval AUC 0.7437; status `discard` (-0.0088 versus the best). The interaction expanded the artifact to 159 MB and evaluation to ~40s, so it is not worth retaining.

## Experiment 39 — moderate finer schedule (pending)

- Classification: follow-up to the current best.
- Hypothesis: 250 trees at 0.02 is a less extreme refinement than the failed 300×0.0167 schedule, preserving the same approximate cumulative step size while possibly improving the depth-12 model’s ranking under its current regularization.
- Result: Eval AUC 0.7526; status `keep` (+0.0001 versus the prior best).
- Observation: the moderate finer schedule is marginally better than 200×0.025, but the gain is small relative to its larger artifact.

## Experiment 40 — stronger L1 with the refined schedule (pending)

- Classification: follow-up to a promising result.
- Hypothesis: L1 improved from 0.1 to 0.5; testing `reg_alpha=1.0` with the new 250-tree schedule may improve sparsity further, or reveal that 0.5 is the useful boundary.
- Result: Eval AUC 0.7532; status `keep` (+0.0006 versus the prior best).
- Observation: L1 regularization continues to help at this schedule; the model is now moderately sparse and strongly L2-regularized.

## Synthesis after 40 runs

- Best result: Eval AUC 0.7532 at `0ee2bc7` (250 trees, learning rate 0.02, depth 12, `subsample=0.95`, `colsample_bytree=0.6`, `max_cat_threshold=256`, `gamma=0.1`, `reg_lambda=5`, `reg_alpha=1`).
- What helped since the last synthesis: near-full row sampling (0.9→0.95), a 250-tree/0.02 schedule, and increasing L1 to 1. The categorical partition budget of 256 gave a small gain; full 512 was slightly worse.
- What did not help: loss-guided growth, carrier-hour interactions, full row sampling, 0.55 column sampling, and unrestricted categorical partitions. The carrier-hour retry also exposed a fixed category-list bug, which was corrected before judging the model.
- Current theory: a deep depth-wise ensemble with almost-full rows, moderate feature subsampling, and strong leaf regularization is the best bias/variance balance. Gains are now incremental; the remaining promising axes are L1/L2/gamma and schedule refinement around 250×0.02.
- Next direction: test nearby L1/L2/gamma combinations and perhaps `max_cat_threshold` below 256; keep changes compact and stop favoring larger artifacts without clear AUC gains.

## Experiment 41 — stronger L1 sweep (pending)

- Classification: follow-up to a promising result.
- Hypothesis: the observed L1 gains from 0.1 to 0.5 to 1.0 may continue at `reg_alpha=2.0`; the risk is oversparsifying useful deep-tree leaves.
- Result: Eval AUC 0.7535; status `keep` (+0.0003 versus the prior best).
- Observation: L1 gains continue, though with diminishing returns.

## Experiment 42 — L1 boundary test (pending)

- Classification: follow-up to a promising result.
- Hypothesis: `reg_alpha=3.0` may give another small improvement before L1 becomes too conservative; all other parameters remain at the current best.
- Result: Eval AUC 0.7529; status `discard` (-0.0006 versus the best).
- Observation: stronger L1 starts removing useful structure; retain `reg_alpha=2.0`.

## Experiment 43 — lighter L2 with tuned L1 (pending)

- Classification: follow-up to a promising result.
- Hypothesis: with L1 now doing more sparsification, reducing `reg_lambda` from 5 to 3 may restore useful leaf magnitude while keeping the successful gamma and sampling controls.
- Result: Eval AUC 0.7538; status `keep` (+0.0003 versus the prior best).
- Observation: the stronger L1 permits a lighter L2 penalty; continue cautiously toward the default.

## Experiment 44 — still lighter L2 (pending)

- Classification: follow-up to a promising result.
- Hypothesis: `reg_lambda=2.0` may recover a little more useful signal while L1=2 and gamma=0.1 still control weak leaves.
- Result: Eval AUC 0.7542; status `keep` (+0.0004 versus the prior best).
- Observation: reducing L2 continues to help with L1=2; test the default boundary next.

## Experiment 45 — default L2 boundary (pending)

- Classification: follow-up to a promising result.
- Hypothesis: `reg_lambda=1.0` may maximize useful leaf flexibility while L1=2, gamma=0.1, and sampling still regularize the model.
- Result: Eval AUC 0.7542; status `discard` (tied the best).
- Observation: lambda 2 is the simpler selected point because it is more conservative at the same measured AUC.

## Experiment 46 — softer split-loss threshold (pending)

- Classification: follow-up to the regularization sweep.
- Hypothesis: `gamma=0.05` may retain a few useful splits that gamma 0.1 prunes, while still removing zero/near-zero improvements; the previous gamma 0.5 result suggests the threshold needs to stay small.
- Result: Eval AUC 0.7540; status `discard` (-0.0002 versus the best).
- Observation: gamma 0.1 is the better small threshold; softer pruning slightly hurts.

## Experiment 47 — smaller categorical partition budget (pending)

- Classification: follow-up to categorical-threshold tuning.
- Hypothesis: `max_cat_threshold=128` may regularize origin/destination partitions better than 256 after the 512 test overfit slightly, while still allowing more category candidates than the implicit default.
- Result: Eval AUC 0.7542; status `discard` (tied the best).
- Observation: the lower threshold does not improve the tuned model; retain 256.

## Experiment 48 — per-node feature sampling (pending)

- Classification: exploration of sampling granularity.
- Hypothesis: `colsample_bynode=0.8` on top of `colsample_bytree=0.6` may decorrelate splits within each deep tree, improving generalization; the cumulative sampling is deliberately moderate to avoid the strong loss seen from excessive feature removal.
- Source: [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html), which describes the cumulative `colsample_by*` family and per-node sampling.
- Result: Eval AUC 0.7487; status `discard` (-0.0055 versus the best).
- Observation: per-node sampling is too destructive when combined with tree-level sampling for this small feature set.

## Experiment 49 — depth fourteen with tuned regularization (pending)

- Classification: follow-up to a promising result.
- Hypothesis: depth 14 previously tied depth 12 before L1/L2 and categorical-threshold tuning. The current stronger regularization may make the extra depth useful without the earlier size/overfit cost; compare directly under the final tuned settings.
- Research note: DART was considered after reading the [DART paper](https://arxiv.org/abs/1505.01866) and XGBoost docs, but the docs warn that DART predictions can apply dropouts unless a finite iteration range is supplied. Because the fixed harness calls `predict_proba` directly, depth refinement is safer here.
- Result: Eval AUC 0.7554; status `keep` (+0.0012 versus the prior best).
- Observation: the stronger regularization makes depth 14 useful; artifact size remains below 150 MB and timing is within limits.

## Experiment 50 — depth sixteen (pending)

- Classification: follow-up to a promising result.
- Hypothesis: depth 16 may capture still richer interactions now that L1/L2/gamma and sampling control overfit. This is the last planned depth expansion before reassessing; reject it if artifact or timing grows disproportionately without a clear AUC gain.
- Result: Eval AUC 0.7556; status `keep` (+0.0002 versus the prior best).
- Observation: depth 16 gives a marginal gain at ~188 MB, still under the artifact/evaluation constraints but with increasing cost.

## Synthesis after 50 runs

- Best result: Eval AUC 0.7556 at `5cb8aef` (250 trees, learning rate 0.02, depth 16, `subsample=0.95`, `colsample_bytree=0.6`, `max_cat_threshold=256`, `gamma=0.1`, `reg_lambda=2`, `reg_alpha=2`).
- What helped: after tuning regularization, depth 14 and 16 continued to improve; the best L1/L2 neighborhood is alpha 2 / lambda 2, with gamma 0.1. Near-full row sampling and 0.6 feature sampling remain important.
- What did not help: DART was not attempted because the fixed harness’s direct `predict_proba` path can apply inference-time dropout; per-node sampling, loss-guided growth, high-cardinality interactions, and unrestricted category partitions failed.
- Current theory: the data rewards very high-order depth-wise interactions among the original fields, but only with strong leaf/split regularization and feature diversity. Improvements are now small and model size is approaching 200 MB.
- Next direction: favor high-value regularization/schedule refinements or a compact model-size ablation; avoid deeper trees unless a clear mechanism justifies the cost.

## Experiment 51 — fewer trees at depth 16 (pending)

- Classification: ablation/simplification of the current best.
- Hypothesis: with depth 16 providing more capacity per tree, 200 trees at 0.025 may match or exceed 250×0.02 while reducing artifact size and training time.
- Result: Eval AUC 0.7556; status `keep` (equal to the best, with a simpler/smaller model).
- Observation: the extra 50 trees were unnecessary; the 200-tree schedule is now preferred.

## Experiment 52 — 150-tree simplification (pending)

- Classification: ablation/simplification.
- Hypothesis: 150 trees at `0.0333` may preserve the same cumulative boosting strength with an even smaller artifact; keep only if AUC remains about equal.
- Result: Eval AUC 0.7554; status `discard` (-0.0002 versus the best).
- Observation: 200 trees is the smallest tested schedule that reaches the current best score.

## Experiment 53 — depth eighteen (pending)

- Classification: bounded exploration of tree capacity.
- Hypothesis: depth 18 may capture remaining high-order interactions under the strong regularization; reject if the gain is marginal relative to the artifact and timing increase.
- Result: Eval AUC 0.7553; status `discard` (-0.0003 versus the best).
- Observation: depth 16 is the capacity frontier; additional depth adds size without generalization benefit.

## Experiment 54 — one-hot low-cardinality categoricals (pending)

- Classification: follow-up to categorical handling research.
- Hypothesis: low-cardinality fields may benefit from one-hot-style splits, while airports remain partitioned. Setting `max_cat_to_onehot=64` should switch Month, day, weekday, and carrier to one-hot without affecting Origin/Dest; the earlier all-partition test did not answer this direction.
- Source: [XGBoost categorical-data documentation](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html), which describes the one-hot versus optimal-partition split choice.
- Result: Eval AUC 0.7463; status `discard` (-0.0093 versus the best).
- Observation: optimal partitioning is strongly preferable even for the low-cardinality features; retain the native default.

## Experiment 55 — gradient-based row sampling (pending)

- Classification: exploration of sampling method.
- Hypothesis: gradient-based sampling may prioritize difficult rows instead of sampling uniformly, potentially improving the ranking objective while retaining the near-full 0.95 fraction.
- Source: [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html), which describes `sampling_method="gradient_based"` and its support requirements.
- Result: Eval AUC 0.7554; status `discard` (-0.0002 versus the best).
- Observation: uniform sampling is slightly better for this balanced dataset and current near-full fraction.

## Experiment 56 — approximate tree construction (pending)

- Classification: exploration of tree-building algorithm.
- Hypothesis: explicit `tree_method="approx"` may produce different quantile-based split candidates than the current histogram path and improve generalization; categorical support is documented for both approximate and histogram methods.
- Source: [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html), which distinguishes `approx` and `hist` tree construction and their categorical support.
- Result: Eval AUC 0.7503; status `discard` (-0.0053 versus the best).
- Observation: `hist` is both much faster and more accurate for this setup; retain the automatic histogram path.

## Experiment 57 — ordered smoothed category rates (pending)

- Classification: exploration of leakage-safe feature engineering.
- Hypothesis: the earlier full-training carrier/origin/destination target rates hurt because training rows saw statistics containing their own labels. CatBoost’s ordered-statistics idea suggests using only preceding training rows for each training encoding, then applying full train-fitted smoothed rates to evaluation rows. This may expose category risk without prediction shift.
- Source: [CatBoost: unbiased boosting with categorical features](https://arxiv.org/abs/1706.09516), which motivates ordered target statistics to reduce target leakage/prediction shift.
- Result: Eval AUC 0.7501; status `discard` (-0.0055 versus the best).
- Observation: target-rate features are harmful even when ordered and leakage-controlled; the native categorical model already captures this signal more effectively.

## Experiment 58 — small child-weight regularization (pending)

- Classification: follow-up to the tuned tree model.
- Hypothesis: `min_child_weight=2` may remove only the most fragile deep splits while preserving the interactions that made depth 16 useful. The previous `min_child_weight=5` negative result used depth 8 and weaker regularization, so this is a distinct small-step test.
- Result: Eval AUC 0.7558; status `keep` (+0.0002 versus the prior best).
- Observation: a small increase above the default helps at depth 16; test whether 3 continues the gain.

## Experiment 59 — child-weight refinement (pending)

- Classification: follow-up to a promising result.
- Hypothesis: `min_child_weight=3` may prune a few more unstable leaves without reaching the over-regularization seen at 5.
- Result: Eval AUC 0.7559; status `keep` (+0.0001 versus the prior best).
- Observation: modest child-weight regularization continues to help; test 4 before settling.

## Experiment 60 — child-weight boundary (pending)

- Classification: follow-up to a promising result.
- Hypothesis: `min_child_weight=4` may capture the last bit of the observed improvement before the earlier value 5 over-regularized the model.
- Result: Eval AUC 0.7556; status `discard` (-0.0003 versus the best).
- Observation: `min_child_weight=3` is the selected local optimum; higher values begin to remove useful splits.

## Synthesis after 60 runs

- Best result: Eval AUC 0.7559 at `6b5bb3f` (200 trees, learning rate 0.025, depth 16, `min_child_weight=3`, `subsample=0.95`, `colsample_bytree=0.6`, `max_cat_threshold=256`, `gamma=0.1`, `reg_lambda=2`, `reg_alpha=2`).
- What helped: deeper trees through depth 16, a smaller 200-tree schedule that tied the larger model, and fine regularization tuning. `min_child_weight` improved from 1 to 3; 4/5 were worse. Ordered target statistics and alternate sampling/tree methods failed.
- Current theory: the best model is a highly expressive depth-wise native-categorical ensemble with near-full row sampling, moderate tree-level feature sampling, and a narrow regularization balance. The score is now near a plateau; improvements are likely tiny.
- Next direction: try only low-risk local refinements (e.g. small schedule or sampling changes) and preserve the simpler `ef49f0f`-derived lineage. Do not add more target encodings or high-cardinality interactions.

## Experiment 61 — refined schedule with child weight 3 (pending)

- Classification: follow-up to a promising result.
- Hypothesis: `min_child_weight=3` may make the extra 50 smaller boosting updates useful; test 250 trees at 0.02 against the current 200×0.025 best.
- Result: Eval AUC 0.7557; status `discard` (-0.0002 versus the best).
- Observation: 200×0.025 remains the better and smaller schedule even after child-weight tuning.

## Experiment 62 — slightly more feature coverage (pending)

- Classification: follow-up to the sampling/regularization interaction.
- Hypothesis: `colsample_bytree=0.65` may recover signal discarded at 0.6 now that `min_child_weight=3` prunes weak splits; the earlier 0.7/0.8 sweep used weaker regularization and is not definitive for this model.
- Result: Eval AUC 0.7568; status `keep` (+0.0009 versus the prior best).
- Observation: the stronger child-weight regularization shifts the useful feature fraction upward; continue one step to 0.7.

## Experiment 63 — feature coverage at 0.7 (pending)

- Classification: follow-up to a promising result.
- Hypothesis: `colsample_bytree=0.7` may recover still more signal now that child weight 3 suppresses weak splits, while staying below the earlier unregularized 0.7 result.
- Result: Eval AUC 0.7568; status `discard` (tied the best).
- Observation: 0.65 is the selected column fraction; extra feature coverage no longer helps.

## Experiment 64 — row sampling with tuned columns (pending)

- Classification: follow-up to the joint sampling/regularization sweep.
- Hypothesis: `subsample=0.9` may pair better with the newly improved `colsample_bytree=0.65` and `min_child_weight=3`, adding diversity that 0.95 may no longer need.
- Result: Eval AUC 0.7565; status `discard` (-0.0003 versus the best).
- Observation: the near-full 0.95 row fraction remains preferable even after the column/child-weight update.

## Experiment 65 — intermediate L1 with tuned sampling (pending)

- Classification: follow-up to a promising local optimum.
- Hypothesis: `reg_alpha=2.5` may balance the extra feature coverage at colsample 0.65 better than alpha 2, retaining the useful deep interactions while pruning more weak leaves.
- Result: Eval AUC 0.7568; status `keep` (equal to the best with a smaller artifact).
- Observation: alpha 2.5 is a simpler/equal-score choice at the new column fraction; continue tuning L2 from this point.

## Experiment 66 — lighter L2 with alpha 2.5 (pending)

- Classification: follow-up to a promising result.
- Hypothesis: reducing `reg_lambda` from 2 to 1.5 may recover leaf signal after the L1 increase, while preserving the child-weight and sampling gains.
- Result: Eval AUC 0.7567; status `discard` (-0.0001 versus the best).
- Observation: lambda 2 remains the better conservative point with alpha 2.5.

## Experiment 67 — alternate subsampling seed (pending)

- Classification: exploration of stochastic sampling realization.
- Hypothesis: since the selected model uses row and column subsampling, a different fixed seed may produce a better generalizing ensemble even with identical hyperparameters. Use seed 7 as a reproducible alternative to 42.
- Result: Eval AUC 0.7547; status `discard` (-0.0021 versus the best).
- Observation: the original seed 42 is materially better for this train/eval split; do not treat the stochastic seed as a free gain.

## Experiment 68 — log distance transformation (pending)

- Classification: compact feature-engineering exploration.
- Hypothesis: `Distance` has a long right tail; adding `log1p(Distance)` may let histogram splits resolve short/medium routes more finely while retaining the raw distance feature. This is a row-local monotonic transform with negligible lookup/evaluation cost.
- Result: Eval AUC 0.7538; status `discard` (-0.0030 versus the best).
- Observation: the raw distance feature plus native trees is better than this compressed transform; avoid redundant numeric transforms.

## Experiment 69 — cyclic departure-time features (pending)

- Classification: compact feature-engineering exploration.
- Hypothesis: sine/cosine of minutes since midnight can express the daily cycle and make 23:59/00:00 neighbors in feature space, complementing the raw HHMM value. This differs from the previously neutral linear `DepMinutes` feature.
- Source: [flight-delay feature-engineering research](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches), which identifies departure hour/time blocks as useful temporal features.
- Result: Eval AUC 0.7546; status `discard` (-0.0022 versus the best).
- Observation: even periodic time features are redundant or harmful for this deep native model; keep the raw HHMM schedule only.

## Experiment 70 — fine L1 boundary (pending)

- Classification: follow-up to the local regularization optimum.
- Hypothesis: `reg_alpha=2.75` may capture a small amount of additional sparsity before the alpha-3.0 drop, without changing the model’s feature/sampling structure.
- Result: Eval AUC 0.7567; status `discard` (-0.0001 versus the best).
- Observation: alpha 2.5 is the selected L1 point; the local optimum is narrow.

## Synthesis after 70 runs

- Best result: Eval AUC 0.7568 at `c3f4948` (200 trees, learning rate 0.025, depth 16, `min_child_weight=3`, `subsample=0.95`, `colsample_bytree=0.65`, `max_cat_threshold=256`, `gamma=0.1`, `reg_lambda=2`, `reg_alpha=2.5`, seed 42).
- What helped: adding child-weight regularization shifted the best column fraction from 0.6 to 0.65; alpha 2.5 tied the previous score with a smaller artifact. The current model is ~140 MB and remains within all limits.
- What did not help: target-rate encodings, time/distance transforms, alternate seed, gradient-based sampling, per-node sampling, one-hot categoricals, approximate trees, deeper depth 18, and further L1/L2 adjustments. This reinforces that the original eight features and native partitioning are the right representation.
- Current theory: the search is at a broad plateau around 0.7568; remaining variations are likely noise-scale gains. Preserve the compact c3f lineage unless a clear improvement appears.
- Next direction: use the remaining time for a few final low-risk checks (possibly depth/schedule ablations or a reproducible second seed only if justified), then ensure the branch ends at the best kept commit and finish the logs.

## Experiment 71 — intermediate depth simplification (pending)

- Classification: ablation/simplification.
- Hypothesis: depth 15 may retain the useful interactions of depth 16 while reducing artifact size; keep only if Eval AUC is about equal.
- Result: Eval AUC 0.7566; status `discard` (-0.0002 versus the best).
- Observation: the depth-16 boundary is meaningful; depth 15 loses a small amount of ranking quality.

## Experiment 72 — intermediate split-loss pruning (pending)

- Classification: local regularization refinement.
- Hypothesis: `gamma=0.15` may prune a few more unstable deep splits than 0.1 without approaching the harmful 0.5 setting, potentially improving generalization at the current plateau.
- Result: Eval AUC 0.7569; status `keep` (+0.0001 versus the prior best).
- Observation: a slightly stronger split threshold gives another marginal gain; test 0.2.

## Experiment 73 — split-loss refinement (pending)

- Classification: follow-up to a promising result.
- Hypothesis: `gamma=0.2` may continue the small pruning improvement while remaining far below the harmful 0.5 threshold.
- Result: Eval AUC 0.7566; status `discard` (-0.0003 versus the best).
- Observation: gamma 0.15 is the selected split-loss threshold; stronger pruning removes useful structure.

## Experiment 74 — L1/gamma interaction (pending)

- Classification: follow-up to a promising regularization combination.
- Hypothesis: the slightly stronger gamma may make alpha 2.75 viable even though it was marginally worse at gamma 0.1; together they may prune complementary weak structures.
- Result: Eval AUC 0.7563; status `discard` (-0.0006 versus the best).
- Observation: alpha 2.5 remains preferred with gamma 0.15; extra L1 is harmful.

## Experiment 75 — fine column-sampling point (pending)

- Classification: local sampling refinement.
- Hypothesis: `colsample_bytree=0.625` may capture a little more feature signal than 0.6 while retaining more diversity than 0.65; this midpoint has not been tested under the current gamma/child-weight settings.
- Result: Eval AUC 0.7569; status `discard` (tied the best).
- Observation: the 0.65 setting is sufficient; the local sampling plateau is broad.

## Experiment 76 — intermediate categorical threshold (pending)

- Classification: local categorical regularization refinement.
- Hypothesis: `max_cat_threshold=192` may reduce noisy airport partition candidates relative to 256 while retaining more useful grouping than 128, now that child weight and gamma are tuned.
- Result: Eval AUC 0.7568; status `discard` (-0.0001 versus the best).
- Observation: 256 remains the better categorical threshold; the lower budgets are slightly worse after tuning.

## Experiment 77 — intermediate boosting schedule (pending)

- Classification: schedule refinement at the current regularization point.
- Hypothesis: 225 trees at 0.02222 may capture a little more of the fine-update benefit than 200×0.025 without the cost or slight loss seen at 250×0.02.
- Result: Eval AUC 0.7568; status `discard` (-0.0001 versus the best).
- Observation: no schedule between 200×0.025 and 250×0.02 improves the current model; keep the 200-tree schedule.

## Experiment 78 — fractional child-weight midpoint (pending)

- Classification: local regularization refinement.
- Hypothesis: `min_child_weight=3.5` may sit between the improving value 3 and the slightly harmful value 4, yielding a marginal gain without changing the model structure.
- Result: Eval AUC 0.7565; status `discard` (-0.0004 versus the best).
- Observation: retain the discrete min-child weight 3; fractional interpolation is worse.

## Experiment 79 — L2 midpoint (pending)

- Classification: local regularization refinement.
- Hypothesis: `reg_lambda=2.5` may complement alpha 2.5 and gamma 0.15 better than lambda 2, giving slightly stronger leaf shrinkage without reaching the earlier lambda-3 region.
- Result: Eval AUC 0.7563; status `discard` (-0.0006 versus the best).
- Observation: lambda 2 is the selected L2 value; stronger shrinkage is harmful at this gamma/alpha combination.

## Experiment 80 — near-full row sampling midpoint (pending)

- Classification: local sampling refinement.
- Hypothesis: `subsample=0.975` may retain more data than 0.95 while preserving just enough stochasticity to avoid the full-row overfit seen earlier.
- Result: Eval AUC 0.7569; status `discard` (tied the best).
- Observation: 0.95 remains the preferred row fraction; additional rows do not help.

## Synthesis after 80 runs

- Best result: Eval AUC 0.7569 at `4c7b3d0` (200 trees, learning rate 0.025, depth 16, `min_child_weight=3`, `subsample=0.95`, `colsample_bytree=0.65`, `max_cat_threshold=256`, `gamma=0.15`, `reg_lambda=2`, `reg_alpha=2.5`, seed 42).
- Recent checks all plateaued or regressed: ordered target encodings, cyclic/log distance/time features, approximate trees, gradient/per-node sampling, depth 15/18, schedule midpoints, categorical thresholds, and local alpha/lambda/row-sampling midpoints.
- Current theory: the original native-categorical feature set is already well matched to the task. The strongest gains came from deep depth-wise capacity plus carefully tuned stochastic sampling and regularization; additional feature engineering is counterproductive.
- Final direction: run only a small number of explicitly motivated reproducibility or simplification checks, then leave the branch at the best kept commit and complete the final log before the clock expires.

## Experiment 81 — depth seventeen boundary (pending)

- Classification: final bounded capacity check.
- Hypothesis: depth 17 may retain the depth-16 score while capturing a small amount of additional interaction capacity; depth 18 was worse, so this is the last intermediate point worth testing.
- Result: Eval AUC 0.7564; status `discard` (-0.0005 versus the best).
- Observation: the depth-16 optimum is sharp; do not increase depth further.

## Experiment 82 — 190-tree simplification (pending)

- Classification: ablation/simplification.
- Hypothesis: 190 trees at `0.0263158` may preserve the score with a smaller artifact while maintaining roughly the same total boosting step size as 200×0.025.
- Result: Eval AUC 0.7563; status `discard` (-0.0006 versus the best).
- Observation: 200 trees is a real schedule boundary; retain the current model.

## Final summary

- Best Eval AUC: **0.7569**, commit `4c7b3d0`.
- Final kept configuration: 200 trees, learning rate 0.025, depth 16, `min_child_weight=3`, `gamma=0.15`, `reg_lambda=2`, `reg_alpha=2.5`, `subsample=0.95`, `colsample_bytree=0.65`, `max_cat_threshold=256`, native categorical features, seed 42.
- Main wins: deeper depth-wise trees, slower boosting, tree-level feature sampling, near-full row sampling, and a narrow combination of L1/L2/split/child regularization.
- Main losses: direct route and carrier-hour categoricals, target-rate encodings (including ordered leakage-safe rates), time/distance transforms, one-hot categoricals, alternate tree methods, per-node/gradient sampling, larger depths beyond 16, and most schedule/regularization midpoints.
- The branch is left at the best kept commit. Further work should focus on validating this model on the human-only holdout and avoid modifying the evaluation harness or reading prohibited holdout tools/data.
