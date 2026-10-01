# Research log — sep30

## Experiment 1 — baseline (`92e43e6`)

**Hypothesis:** Establish the starter's reference Eval AUC without changing `train.py`.

**Change:** None. Used the existing categorical columns and starter XGBoost configuration (`n_estimators=30`, `max_depth=6`, `learning_rate=0.1`).

**Result:** Eval AUC 0.7203; run completed successfully. This is the reference for later experiments.

## Experiment 2 — increase boosting rounds (planned)

**Class:** Follow-up to the baseline.

**Hypothesis:** The starter uses only 30 rounds. Increasing to 200 while leaving depth and learning rate unchanged may reduce underfitting and improve AUC; the baseline's very short fit leaves room under the 60-second training limit. This is a controlled test of tree count, guided by XGBoost's discussion of model complexity and bias/variance.

**Research:** [XGBoost Notes on Parameter Tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) explains the complexity trade-off and says lower learning rates should be paired with more rounds. [Flight Delay Prediction using Airport Situational Awareness Map](https://arxiv.org/abs/1911.01605) finds airport traffic and weather features influential, but those measurements are unavailable in this dataset; they motivate considering train-fitted schedule/airport proxies later.

**Change:** Set `n_estimators` from 30 to 200 only. Result pending.

**Outcome:** Eval AUC 0.7345 (`e478dae`), a +0.0142 improvement over baseline; training took 1.2s. Kept this commit.

## Experiment 3 — extend the round count (planned)

**Class:** Follow-up to a promising result.

**Hypothesis:** The 30-to-200 round increase produced a sizable gain with ample training-time headroom. Test 500 rounds, holding all other settings fixed, to see whether the model is still benefiting from additional boosting or has reached its useful complexity.

**Change:** Set `n_estimators` from 200 to 500 only. Result pending.

**Outcome:** Eval AUC 0.7312 (`29c88bd`), down 0.0033 from 200 rounds. Discarded and reset to `e478dae`; 500 rounds appears to add overfit or otherwise reduce ranking quality on this split.

## Experiment 4 — row subsampling (planned)

**Class:** Follow-up to the overfitting signal at 500 rounds.

**Hypothesis:** The 200-round result is better than 500, suggesting additional regularization may help the ranking generalize. XGBoost's parameter guide says `subsample` adds row-level randomness and can prevent overfitting. Test 0.8 with the 200-round model, keeping all other settings fixed.

**Research:** [XGBoost Parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) documents `subsample` as the fraction of instances sampled per boosting iteration and notes that sampling can prevent overfitting.

**Change:** Add `subsample=0.8`. Result pending.

**Outcome:** Eval AUC 0.7275 (`eefcad4`), down 0.0070 from the kept 200-round result. Discarded and reset to `e478dae`; row subsampling did not help at this setting.

## Experiment 5 — scheduled departure hour (planned)

**Class:** Exploration into per-row temporal feature engineering.

**Hypothesis:** `CRSDepTime` is encoded as HHMM. A categorical hour feature can group all minutes within an hour and let trees learn hour-specific delay behavior directly. Prior flight-delay feature engineering extracts the hour component from scheduled HHMM time and also tests time blocks. I checked the allowed training split only: all `CRSDepTime` values are valid HHMM and there are no missing values.

**Research:** The [2014 spatio-temporal feature engineering study](https://www.mdpi.com/2079-9292/13/24/4910) extracts scheduled departure hour and time categories from `CRS_DEP_TIME` (HHMM). The [UC Berkeley air travel delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) also uses hour-of-departure and hourly time blocks.

**Change:** Add `DepHour = CRSDepTime // 100`, with hour categories fitted on `train` and derived inside `prepare(df)`. Result pending.

**Outcome:** Eval AUC 0.7349 (`402b9f7`), +0.0004 over the 200-round model without `DepHour`. Kept the small, row-stable feature.

## Experiment 6 — smaller steps with more rounds (planned)

**Class:** Follow-up to the useful 200-round model and the worse 500-round result.

**Hypothesis:** A smaller learning rate may improve generalization if paired with enough boosting rounds. Following the XGBoost tuning guide, test `learning_rate=0.05` with `n_estimators=400`, keeping the kept hour feature and other settings unchanged.

**Change:** Set learning rate to 0.05 and rounds to 400 as a paired boosting schedule. Result pending.

**Outcome:** Eval AUC 0.7354 (`0c053d9`), +0.0005 over the prior best. Kept the paired lower-rate, higher-round schedule.

## Experiment 7 — extend the lower-rate schedule (planned)

**Class:** Follow-up to a promising result.

**Hypothesis:** The 0.05/400 schedule modestly improved AUC. Test 600 rounds at the same rate to check whether this slower update regime benefits from additional stages; this differs from the rejected 500-round run at rate 0.1.

**Change:** Set `n_estimators` from 400 to 600 only. Result pending.

**Outcome:** Eval AUC 0.7356 (`e29680d`), +0.0002 over 400 rounds at learning rate 0.05. Kept this incremental improvement.

## Experiment 8 — origin–destination route category (planned)

**Class:** Exploration into a categorical interaction.

**Hypothesis:** The model currently sees Origin and Dest separately. A train-fitted route category may expose pair-specific effects that require several tree splits to express otherwise. Prior flight-delay work lists Origin–Destination pairs among predictor factors. XGBoost's categorical tutorial describes partitioning categories into groups for splits, which suits this joint feature.

**Research:** [Categorical Data in XGBoost](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) documents native categorical partition splits. The [flight-delay generation and prediction review](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057) lists Origin–Destination pairs as inputs in prior prediction models.

**Change:** Add `Route = Origin + '-' + Dest`, derive it per row in `prepare(df)`, and fit its valid category levels using `train` only. Unseen routes will become missing categorical values. Result pending.

**Outcome:** Eval AUC 0.7063 (`89cfd63`), down 0.0293 from the kept model. Training took 5.8s, evaluation 53.6s, and the artifact grew to 88.8 MB. Discarded and reset to `e29680d`; the high-cardinality route feature appears to overfit and adds substantial artifact/evaluation cost.

## Experiment 9 — shallower trees (planned)

**Class:** Ablation/simplification of the current best model.

**Hypothesis:** Reducing `max_depth` from 6 to 5 may constrain brittle interactions and improve generalization, particularly after the high-cardinality route trial overfit badly. The XGBoost tuning guide identifies depth as a direct model-complexity control. If AUC stays effectively level, the simpler trees are preferable.

**Change:** Set `max_depth=5` only; retain the 600-round, 0.05-rate model and `DepHour`. Result pending.

**Outcome:** Eval AUC 0.7364 (`b5f1f9f`), +0.0008 over depth 6, with a smaller artifact (7.9 MB). Kept the shallower model.

## Experiment 10 — depth 4 (planned)

**Class:** Follow-up to a promising simplification.

**Hypothesis:** Depth 5 improved over depth 6. Test depth 4 to check whether additional regularization further helps or begins to underfit. This completes a short, directed downward depth sweep rather than changing several regularizers at once.

**Change:** Set `max_depth=4` only. Result pending.

**Outcome:** Eval AUC 0.7352 (`e39e995`), down 0.0012 from depth 5. Discarded and reset to `b5f1f9f`; depth 4 appears too shallow for this model.

## Synthesis after 10 experiments

- Increasing the starter from 30 to 200 trees produced the largest initial gain (+0.0142). At learning rate 0.1, 500 trees was worse; pairing a lower 0.05 rate with 400 and then 600 rounds improved incrementally.
- The train-fitted scheduled departure hour added a small gain (+0.0004), consistent with time-of-day being useful.
- Reducing depth from 6 to 5 improved AUC by 0.0008 and reduced artifact size; depth 4 gave back 0.0012.
- Row subsampling at 0.8 hurt. The high-cardinality Origin–Destination category overfit severely (AUC 0.7063) and increased evaluation time and artifact size.
- Current best: `b5f1f9f`, Eval AUC 0.7364, with 600 rounds, learning rate 0.05, depth 5, and `DepHour`.

**Current theory:** The compact schedule/time features generalize, while excessive tree count at the larger step size and sparse high-cardinality categories do not. The next research pass should focus on regularization controls that act within trees or on robust transformations of the existing schedule/airport inputs.

## Experiment 11 — minimum child weight (planned)

**Class:** Follow-up regularization experiment after the depth sweep.

**Hypothesis:** The depth-5 model improved, while a sparse route interaction overfit badly. Raising the minimum child weight modestly may suppress weak, low-support splits without changing the useful depth, rounds, learning rate, or hour feature.

**Research:** The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says larger `min_child_weight` values make the model more conservative by requiring more summed instance weight before a child split is allowed. The [parameter tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) lists it among direct controls for model complexity.

**Change:** Set `min_child_weight=2` (from the default 1). Result pending.

**Outcome:** Eval AUC 0.7370 (`3ee2216`), +0.0006 over depth 5 alone. Kept `min_child_weight=2`.

## Experiment 12 — minimum split gain (planned)

**Class:** Follow-up regularization experiment using a different mechanism.

**Hypothesis:** Requiring more data support improved AUC. A small `gamma=0.1` may also remove marginal splits by imposing a minimum loss reduction, while leaving child support at 2 and all other settings fixed.

**Research:** The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `gamma` as the minimum loss reduction needed for another partition and says larger values make the model more conservative.

**Change:** Add `gamma=0.1`. Result pending.

**Outcome:** Eval AUC 0.7369 (`fb7f9f4`), 0.0001 below the kept model. Discarded and reset to `3ee2216`.

## Experiment 13 — cyclic scheduled time (planned)

**Class:** Exploration into a different temporal representation.

**Hypothesis:** Raw HHMM values put the end and start of the day far apart numerically. Two periodic features from scheduled minutes on a 24-hour circle may let shallow trees recognize that late-night and early-morning departures are adjacent. This is complementary to the hour category and keeps each feature row-local.

**Research:** An airline disruption-management study describes transforming scheduled departure time into sine/cosine vectors using a 24-hour clock period ([source](https://www.sciencedirect.com/science/article/pii/S2666827021000517)).

**Change:** Add sine and cosine of scheduled departure minutes to `prepare(df)`. Result pending.

**Outcome:** Eval AUC 0.7357 (`96c228e`), down 0.0013 from the kept `min_child_weight=2` model; evaluation increased to 41.0s. Discarded and reset to `3ee2216`.

## Experiment 14 — cyclic time instead of hour category (planned)

**Class:** Ablation of the current temporal representation.

**Hypothesis:** The sine/cosine pair lowered AUC when stacked with `DepHour`, possibly because both encode the same schedule information. Test the pair as a replacement for `DepHour` to see whether the cyclic representation works better on its own.

**Change:** Keep the row-wise sine/cosine features, remove the fitted `DepHour` category, and leave all model settings unchanged. Result pending.

**Outcome:** Eval AUC 0.7359 (`ea27121`), down 0.0011 from the kept model. Discarded and reset to `3ee2216`; cyclic time alone did not beat the hour category.

## Experiment 15 — carrier-specific departure hour (planned)

**Class:** Exploration into a low-cardinality feature interaction after the route category overfit.

**Hypothesis:** Flight-delay analyses report different time-of-day behavior by carrier, including stronger late-night delays. The current model has carrier and hour separately; an explicit `UniqueCarrier × DepHour` category may expose this interaction while remaining far less sparse than full Origin–Destination routes. It uses only row fields and a category vocabulary fitted on `train`; no row counts or target aggregates are used.

**Research:** The [UC Berkeley flight-delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) reports that delay patterns by hour differ across carriers and worsen late at night. XGBoost's [categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) describes category-partition splits. Its [interaction-constraints guide](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html) explains that tree paths represent feature interactions and that unconstrained trees can fit spurious combinations, motivating a compact, domain-informed interaction.

**Change:** Add train-fitted `CarrierHour = UniqueCarrier + '_' + DepHour`, derived per row inside `prepare(df)`. Result pending.

**Outcome:** Eval AUC 0.7281 (`a7d4ed6`), down 0.0089 from the kept model. Evaluation rose to 44.6s and the artifact to 10.7 MB. Discarded and reset to `3ee2216`; even the lower-cardinality carrier-hour interaction did not generalize.

## Experiment 16 — stronger child support (planned)

**Class:** Follow-up to the positive `min_child_weight=2` result.

**Hypothesis:** Requiring child weight 2 improved AUC by 0.0006. Test 4 to check whether a stronger restriction suppresses additional weak splits or begins to underfit; keep the feature set and all other settings fixed.

**Change:** Set `min_child_weight=4`. Result pending.

**Outcome:** Eval AUC 0.7362 (`c0bdca2`), down 0.0008 from `min_child_weight=2`. Discarded and reset to `3ee2216`.

## Experiment 17 — intermediate child weight (planned)

**Class:** Follow-up to the child-weight sweep.

**Hypothesis:** Weight 2 improved AUC while 4 reduced it. Test 3 to locate whether the local optimum lies between those settings, changing only this parameter.

**Change:** Set `min_child_weight=3`. Result pending.

**Outcome:** Eval AUC 0.7365 (`ca4924b`), below `min_child_weight=2` by 0.0005. Discarded and reset to `3ee2216`; 2 remains the best tested child weight.

## Experiment 18 — remove raw scheduled time (planned)

**Class:** Ablation/simplification of the successful `DepHour` feature.

**Hypothesis:** Adding `DepHour` improved AUC while raw `CRSDepTime` remained. Removing the raw HHMM input tests whether its within-hour detail helps beyond hour-of-day. If performance stays about equal, the smaller feature set is preferable.

**Research:** The prior flight-delay feature-engineering study [extracts hour and time blocks from scheduled HHMM](https://www.mdpi.com/2079-9292/13/24/4910), supporting the coarse-hour representation.

**Change:** Remove `CRSDepTime` from model inputs while retaining it to compute `DepHour` inside `prepare(df)`. Result pending.

**Outcome:** Eval AUC 0.7363 (`1f98b04`), 0.0007 below the highest score, with one fewer model input. Kept this simpler representation as about equal under the simplicity criterion; raw scheduled time remains available only to derive `DepHour`.

## Experiment 19 — night-flight indicator (planned)

**Class:** Exploration into a coarse, domain-motivated temporal feature.

**Hypothesis:** The learned hour categories may not expose a broad late-night regime efficiently. Test a row-level binary indicator for scheduled departures from 21:00 through 03:59, keeping the simplified input set and all model settings unchanged.

**Research:** The [spatio-temporal flight feature-engineering study](https://www.mdpi.com/2079-9292/13/24/4910) explicitly constructs `IsNightFlight` from HHMM scheduled time using the 21:00–04:00 window.

**Change:** Add `IsNightFlight = (CRSDepTime >= 2100) or (CRSDepTime < 400)`. Result pending.

**Outcome:** Eval AUC 0.7363 (`6f8090d`), unchanged at four decimal places versus the simpler model, with one extra feature and slightly longer evaluation. Discarded and reset to `1f98b04`.

## Experiment 20 — L2 leaf regularization (planned)

**Class:** Exploration into a distinct model regularization parameter.

**Hypothesis:** Tree depth and child support have helped, while gamma and row subsampling did not. Raising `reg_lambda` from 1 to 2 may further shrink noisy leaf scores without changing the learned feature structure or data preparation.

**Research:** The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `reg_lambda` as L2 regularization on leaf weights and says increasing it makes the model more conservative.

**Change:** Set `reg_lambda=2`. Result pending.

**Outcome:** Eval AUC 0.7375 (`7c792fe`), +0.0012 over the simpler `1f98b04` and +0.0005 over the prior highest score. Kept the L2-regularized model.

## Synthesis after 20 experiments

- The largest gain remains increasing tree count from 30 to 200 (+0.0142). A 0.05 learning rate paired with 600 rounds and depth 5 gave further small gains.
- `DepHour` helped slightly. Removing raw `CRSDepTime` cost 0.0007 but reduced one model input, so that simpler variant was kept; adding `IsNightFlight` did not change AUC.
- Regularization has mattered: `min_child_weight=2` improved the depth-5 model; values 3 and 4 and `gamma=0.1` were worse. Increasing `reg_lambda` to 2 then set a new best at 0.7375.
- Row subsampling hurt. Full route and carrier-hour categories both overfit; cyclic time features and a night flag did not improve on the hour category.
- Current best commit: `7c792fe`, Eval AUC 0.7375, with 600 rounds, learning rate 0.05, depth 5, `min_child_weight=2`, `reg_lambda=2`, `DepHour`, and no raw `CRSDepTime` model input.

**Current theory:** Gains come from enough low-rate boosting with moderate tree/leaf regularization and a compact hour-of-day signal. Sparse categorical crosses overfit on this split. The next research pass will look for ways to control categorical split complexity and alternatives to depth-wise tree growth without adding unsupported row aggregates.

## Experiment 21 — cap categorical partition size (planned)

**Class:** Follow-up to the category-overfit results.

**Hypothesis:** Both route and carrier-hour crosses overfit badly, while the compact native categories remain useful. Restricting categorical split candidates to 32 categories may regularize the existing airport/carrier partitions without adding a new feature. The route cross stays out of this test.

**Research:** XGBoost 3.4.1's [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) and [Python API](https://xgboost.readthedocs.io/en/stable/python/python_api.html) describe `max_cat_threshold` as the maximum categories considered for a partition split, intended to prevent overfitting.

**Change:** Add `max_cat_threshold=32`. Result pending.

**Outcome:** Eval AUC 0.7378 (`1d264b6`), +0.0003 over the prior best; artifact size fell from 8.0 MB to 7.1 MB. Kept the more constrained categorical splits.

## Experiment 22 — tighter categorical cap (planned)

**Class:** Follow-up to a promising result.

**Hypothesis:** A cap of 32 improved AUC. Test 16 to see whether tighter partition regularization helps further or removes useful airport/category groupings.

**Change:** Set `max_cat_threshold=16` only. Result pending.

**Outcome:** Eval AUC 0.7391 (`6085ae3`), +0.0013 over the cap of 32; artifact size fell to 6.4 MB. Kept the tighter categorical partition limit.

## Experiment 23 — categorical cap of 8 (planned)

**Class:** Follow-up to a strong categorical-regularization result.

**Hypothesis:** Lowering the cap from 32 to 16 improved AUC. Test 8 to see whether restricting each category partition further improves generalization or begins to remove useful groupings.

**Change:** Set `max_cat_threshold=8` only. Result pending.

**Outcome:** Eval AUC 0.7392 (`42f9590`), +0.0001 over the cap of 16; artifact size fell to 5.2 MB. Kept the slightly stronger, smaller model.

## Experiment 24 — one-hot low-cardinality categories (planned)

**Class:** Exploration of a different native categorical split strategy.

**Hypothesis:** The cap of 8 improved AUC by constraining partition splits. Switching low-cardinality features (calendar fields, carrier, and departure hour) to one-hot splits may let the trees isolate useful categories directly, while larger airport categories remain partitioned.

**Research:** The [XGBoost categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) says `max_cat_to_onehot` selects one-hot splits below a category-count threshold and partition splits above it.

**Change:** Add `max_cat_to_onehot=32`; retain `max_cat_threshold=8`. Result pending.

**Outcome:** Eval AUC 0.7256 (`68cb2ed`), down 0.0136 from the kept model. Discarded and reset to `42f9590`; one-hot splits at this broad threshold substantially hurt.

## Experiment 25 — narrower one-hot threshold (planned)

**Class:** Follow-up to the failed categorical split-strategy change.

**Hypothesis:** Threshold 32 moved too many medium-cardinality features to one-hot splits. Test 16 so the smallest calendar/carrier categories can use one-hot splits while day-of-month and departure hour remain partitioned.

**Change:** Set `max_cat_to_onehot=16` only; retain `max_cat_threshold=8`. Result pending.

**Outcome:** Eval AUC 0.7395 (`8861a27`), +0.0003 over the best partition-only setting. Kept one-hot splits for categories below 16 levels.

## Experiment 26 — one-hot threshold 8 (planned)

**Class:** Follow-up to a promising categorical strategy.

**Hypothesis:** Threshold 16 improved AUC, while 32 was too broad. Test 8 to determine whether one-hot splits should be limited to only the smallest categories (such as day of week), leaving month, carrier, and hour partitioned.

**Change:** Set `max_cat_to_onehot=8` only; retain `max_cat_threshold=8`. Result pending.

**Outcome:** Eval AUC 0.7400 (`0e7d4af`), +0.0005 over the threshold of 16. Kept one-hot splits for categories below 8 levels.

## Experiment 27 — categorical partition cap of 4 (planned)

**Class:** Follow-up to a sequence of improving partition caps.

**Hypothesis:** Reducing `max_cat_threshold` from 32 to 16 to 8 improved AUC. Test 4 to determine whether tighter partition regularization still helps when the one-hot cutoff is already 8.

**Research:** The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says `max_cat_threshold` caps the categories considered in partition splits to help prevent overfitting.

**Change:** Set `max_cat_threshold=4` only. Result pending.

**Outcome:** Eval AUC 0.7325 (`baa1c65`), down 0.0075 from the cap of 8. Discarded and reset to `0e7d4af`; a cap of 4 over-regularized categorical partitions.

## Experiment 28 — intermediate partition cap (planned)

**Class:** Follow-up to the categorical-cap sweep.

**Hypothesis:** Cap 8 improved AUC, while cap 4 sharply reduced it. Test 6 as an intermediate point to see whether it preserves useful categorical groupings while retaining some of the regularization benefit.

**Change:** Set `max_cat_threshold=6` only; retain `max_cat_to_onehot=8`. Result pending.

**Outcome:** Eval AUC 0.7381 (`0ddfb34`), down 0.0019 from the cap of 8. Discarded and reset to `0e7d4af`; cap 8 remains preferable.

## Experiment 29 — one-hot threshold 12 (planned)

**Class:** Follow-up to the low-cardinality split-strategy sweep.

**Hypothesis:** One-hot threshold 8 reached 0.7400 and threshold 16 reached 0.7395. Test 12 to see whether the intermediate set of categories produces a better balance.

**Change:** Set `max_cat_to_onehot=12` only; retain `max_cat_threshold=8`. Result pending.

**Outcome:** Eval AUC 0.7400 (`5e1180a`), tied with the threshold of 8 at four decimal places and did not reduce artifact size. Discarded and reset to `0e7d4af`.

## Experiment 30 — loss-guided tree growth (planned)

**Class:** Exploration into an alternate tree-growth policy.

**Hypothesis:** The current depth-wise policy expands shallow nodes first. Loss-guided growth prioritizes the available split with the largest loss change and may allocate the same depth-5 capacity more effectively. Test it with the existing depth cap and all current feature/regularization settings unchanged.

**Research:** XGBoost's [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) documents `grow_policy='lossguide'` as splitting nodes with the highest loss change; it is supported with histogram or approximate tree methods. XGBoost 3.4.1 resolves `tree_method='auto'` to the histogram method.

**Change:** Set `grow_policy='lossguide'` only. Result pending.

**Outcome:** Eval AUC 0.7400 (`c75f274`), tied with the depth-wise model at four decimal places and no reduction in artifact size. Discarded and reset to `0e7d4af`.

## Synthesis after 30 experiments

- Best score is `0.7400` at `0e7d4af`, up 0.0197 from the untouched baseline. The largest lift came from 200 trees; the lower learning rate with 600 trees and depth 5 added smaller gains.
- `min_child_weight=2` and `reg_lambda=2` helped, while stronger child support and `gamma=0.1` did not.
- The clearest recent gains came from native categorical regularization: `max_cat_threshold=32`, 16, and 8 improved stepwise; 4 and 6 were too restrictive. `max_cat_to_onehot=8` was strongest; 16 was slightly lower, 32 much worse, and 12 tied.
- `DepHour` added a small gain; removing raw `CRSDepTime` cost only 0.0007 and reduced the model input set. Cyclic time and the night flag did not help. Route and carrier-hour category crosses overfit. Loss-guided growth tied the depth-wise model without a simplicity benefit.
- Current best model: 600 rounds, learning rate 0.05, depth 5, min child weight 2, L2 lambda 2, categorical partition cap 8, one-hot threshold 8, and a train-fitted `DepHour` with no raw scheduled-time model input.

**Current theory:** The dataset benefits from moderate boosting and leaf regularization, plus a compact set of flight features. Better handling of existing categorical fields has mattered more than explicit crosses. Next research should consider robust, low-cardinality domain features (such as weekend timing) and alternate regularization/boosting approaches.

## Experiment 31 — weekend indicator (planned)

**Class:** Exploration into a compact, row-derived calendar feature.

**Hypothesis:** Individual day-of-week categories may not give a shallow tree a direct weekday-versus-weekend split. A binary Saturday/Sunday feature could expose that broad difference while retaining the individual weekday categories.

**Research:** The [flight-delay feature-engineering study](https://www.mdpi.com/2079-2089/13/24/4910) constructs a weekend binary feature. The [BTS on-time reporting directive](https://www.bts.gov/topics/airlines-and-airports/number-17-technical-directive-time-reporting-effective-oct-1-2008) defines Monday as 1 and Sunday as 7, so Saturday and Sunday are values 6 and 7.

**Change:** Add `IsWeekend = DayOfWeek in {6, 7}` inside `prepare(df)`. Result pending.

**Outcome:** Eval AUC 0.7400 (`22fba05`), tied with the kept model at four decimal places but with an extra feature and 2.5s more evaluation time. Discarded and reset to `0e7d4af`.

## Experiment 32 — weekend flag instead of weekday categories (planned)

**Class:** Ablation/simplification of the weekly representation.

**Hypothesis:** The weekend flag did not improve AUC when added alongside `DayOfWeek`. Test it as a replacement to learn whether the broad weekday/weekend distinction retains performance with one fewer categorical input.

**Change:** Remove `DayOfWeek` from model inputs while retaining the row-wise `IsWeekend` flag. Result pending.

**Outcome:** Eval AUC 0.7350 (`d73b0c3`), down 0.0050 from the retained weekday categories. Discarded and reset to `0e7d4af`.

## Experiment 33 — DART dropout booster (planned)

**Class:** Exploration into an alternate boosting method.

**Hypothesis:** The current model uses 600 small-step trees. DART drops earlier trees during training to reduce overfitting and may keep later trees from making only trivial corrections. Test a modest dropout rate with the best feature set and tree regularization unchanged.

**Research:** XGBoost's [DART tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) describes tree dropout as an overfitting control and uses `rate_drop=0.1`, `skip_drop=0.5` in its example. It cautions that DART can train more slowly than `gbtree`.

**Change:** Set `booster='dart'`, `rate_drop=0.1`, and `skip_drop=0.5`. Result pending.

**Outcome:** `f3f289b` timed out during training after 60s, before evaluation; recorded as a crash and discarded. XGBoost also warned that `booster='dart'` is deprecated in this version, and the dropout configuration was far slower than the regular tree booster.

## Experiment 34 — finer numeric histogram (planned)

**Class:** Exploration into split resolution for the remaining numeric feature.

**Hypothesis:** The current feature set has one numeric model input (`Distance`). Doubling histogram resolution may offer more candidate thresholds for this feature and improve ranking, with a small expected training cost relative to the 60s limit.

**Research:** The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says `max_bin` controls the number of bins for histogram-based tree methods and that increasing it can improve split optimality at higher computation cost.

**Change:** Set `max_bin=512`. Result pending.

**Outcome:** Eval AUC 0.7392 (`2999c3f`), down 0.0008 from the cap-8 best. Discarded and reset to `0e7d4af`.

## Experiment 35 — coarser numeric histogram (planned)

**Class:** Follow-up to the numeric-bin resolution test.

**Hypothesis:** Raising `max_bin` to 512 did not help. A lower value of 128 may act as a mild regularizer for distance thresholds by removing fine split candidates; test it while holding other settings fixed.

**Change:** Set `max_bin=128`. Result pending.

**Outcome:** Eval AUC 0.7403 (`8d13074`), +0.0003 over the default bin count. Kept the coarser numeric histogram.

## Experiment 36 — histogram bins at 64 (planned)

**Class:** Follow-up to a promising bin-resolution result.

**Hypothesis:** `max_bin=128` improved AUC while 512 did not. Test 64 to see whether still coarser distance thresholds further regularize the remaining numeric feature.

**Change:** Set `max_bin=64` only. Result pending.

**Outcome:** Eval AUC 0.7395 (`3adfeff`), down 0.0008 from 128 bins. Discarded and reset to `8d13074`.

## Experiment 37 — histogram at 192 bins (planned)

**Class:** Follow-up to the numeric-resolution sweep.

**Hypothesis:** 128 bins improved over the default 256, while 64 lost 0.0008. Test 192 to see whether an intermediate resolution can retain more distance detail without the default's higher resolution.

**Change:** Set `max_bin=192` only. Result pending.

**Outcome:** Eval AUC 0.7400 (`041f634`), tied with the default 256-bin model and below 128. Discarded and reset to `8d13074`.

## Experiment 38 — histogram at 96 bins (planned)

**Class:** Follow-up to the promising 128-bin result.

**Hypothesis:** 128 bins scored 0.7403; 64 scored 0.7395. Test 96 as an intermediate resolution to see if it improves on both.

**Change:** Set `max_bin=96` only. Result pending.

**Outcome:** Eval AUC 0.7404 (`23ca622`), +0.0001 over 128 bins. Kept the new best numeric resolution.

## Experiment 39 — histogram at 112 bins (planned)

**Class:** Follow-up to a small improvement in the bin sweep.

**Hypothesis:** 96 bins narrowly beat 128. Test 112 to see whether a nearby intermediate resolution improves further.

**Change:** Set `max_bin=112` only. Result pending.

**Outcome:** Eval AUC 0.7400 (`358a137`), below 96 bins by 0.0004. Discarded and reset to `23ca622`.

## Experiment 40 — L1 leaf regularization (planned)

**Class:** Exploration into a distinct leaf-weight regularizer.

**Hypothesis:** L2 regularization at 2 improved AUC. A small L1 penalty may shrink weak leaf weights differently and further reduce noise without changing feature splits or categorical settings.

**Research:** The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `reg_alpha` as L1 regularization on leaf weights and says larger values make the model more conservative.

**Change:** Set `reg_alpha=0.1`. Result pending.

**Outcome:** Eval AUC 0.7405 (`986daea`), +0.0001 over the 96-bin model. Kept the new best with both L1 and L2 regularization.

## Synthesis after 40 experiments

- Current best is `986daea`, Eval AUC 0.7405 (+0.0202 from baseline). It uses 600 rounds at learning rate 0.05, depth 5, child weight 2, `reg_lambda=2`, `reg_alpha=0.1`, categorical thresholds of 8, `max_bin=96`, and the train-fitted `DepHour` feature.
- Native categorical tuning delivered the biggest later gains: category partition cap 8 and one-hot threshold 8 outperformed defaults; caps 4/6 were too tight and broad one-hot thresholds hurt.
- A 96-bin histogram slightly beat 128 and the default. Very high or low bin counts were worse.
- Weekend engineering did not improve the model; replacing individual weekday categories with a weekend flag lost 0.005. Loss-guided growth tied the existing model. DART exceeded the training limit and was discarded.
- Compact, train-fitted features and moderate regularization continue to generalize best. Explicit categorical crosses and extra time flags have not helped.

**Current theory:** The signal is mostly captured by the base airport/carrier/calendar fields plus departure hour. Careful categorical split control, leaf penalties, and split resolution produce small additive gains. The next research pass should consider feature subsampling or further regularization around the new best, while avoiding expensive booster changes.

## Research pass after experiment 40

The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says `colsample_bytree` samples a fraction of columns independently for each tree. The [parameter tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) identifies column subsampling as a way to add randomness to improve robustness against overfitting. Earlier row subsampling (`subsample=0.8`) reduced AUC, but it samples rows and does not test this distinct source of variation. With eight model inputs, a mild 0.9 tree-level feature sample may reduce reliance on a brittle split while retaining most predictors. Test that as the next isolated change.

## Experiment 41 — mild tree-level feature subsampling (planned)

**Class:** Exploration into a regularization mechanism distinct from row subsampling.

**Hypothesis:** At `colsample_bytree=0.9`, each tree should retain most of the eight available predictors while introducing modest feature randomness. This may help the ensemble generalize beyond the current all-feature trees.

**Research:** The official [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines tree-level column sampling; the [tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) describes it as an overfitting control.

**Change:** Set `colsample_bytree=0.9` only. Result pending.

**Outcome:** Eval AUC 0.7400 (`9aeaf0c`), below the current best by 0.0005. Discarded; returned to `986daea`. Mild feature sampling did not help on this compact eight-feature input set.

## Experiment 42 — stronger L1 leaf penalty (planned)

**Class:** Follow-up to the small improvement at `reg_alpha=0.1`.

**Hypothesis:** A moderate increase to 0.2 may shrink weak leaf weights and reduce noise further while leaving tree structure unchanged. The prior 0.1 value narrowly improved AUC; this tests whether the regularization trend continues.

**Research:** The official [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `reg_alpha` as L1 regularization on leaf weights and says larger values make the model more conservative.

**Change:** Set `reg_alpha=0.2` only. Result pending.

**Outcome:** Eval AUC 0.7406 (`f69ee6c`), +0.0001 over the prior best. Kept as the current best; the improvement is small but numeric.

## Experiment 43 — weekday and departure-hour interaction (planned)

**Class:** Exploration into a low-cardinality schedule interaction.

**Hypothesis:** Departure delay patterns can vary jointly by weekday and hour. An explicit `DayOfWeek × DepHour` categorical feature may let trees represent these patterns directly, with at most 168 combinations. Earlier route and carrier-hour crosses performed poorly; this cross is smaller and is based on calendar scheduling rather than an operational identifier.

**Research:** A peer-reviewed study of flight departure delays organizes observations by both [day of week and hour of day](https://onlinelibrary.wiley.com/doi/10.1155/2019/3525912), motivating this specific interaction.

**Change:** Add `DayHour` as a string category whose allowed levels are fitted only on `train`; compute each row's value from its own weekday and scheduled departure hour.

**Outcome:** The first run (`82e6b82`) crashed before fitting because `DayOfWeek` contains string labels (for example, `c-2`), and the implementation cast them to integers. Logged as a crash. Correcting the unnecessary cast and rerunning the same experiment.

## Experiment 44 — rerun weekday and departure-hour interaction (planned)

**Class:** Corrected rerun of experiment 43 after a data-type error.

**Hypothesis:** Same as experiment 43: explicitly combining weekday and scheduled departure hour may expose stable schedule patterns to the trees.

**Change:** Preserve the source weekday labels as strings when constructing the train-fitted `DayHour` category. Result pending.

**Outcome:** Eval AUC 0.7391 (`6cb55f5`), 0.0015 below the current best. Discarded and returned to `f69ee6c`. The explicit weekday-hour cross added complexity without helping.

## Experiment 45 — continue L1 regularization tuning (planned)

**Class:** Follow-up to the successive small gains at `reg_alpha=0.1` and `0.2`.

**Hypothesis:** A modest increase to 0.3 may continue to suppress weak leaf weights. This tests the local trend with one parameter change.

**Research:** The XGBoost [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `reg_alpha` as L1 regularization on leaf weights, with larger values making the model more conservative.

**Change:** Set `reg_alpha=0.3` only. Result pending.

**Outcome:** Eval AUC 0.7416 (`be99240`), +0.0010 over the previous best. Kept as the new best; this is the largest recent regularization gain.

## Experiment 46 — stronger L1 leaf penalty (planned)

**Class:** Follow-up to the clear improvement at `reg_alpha=0.3`.

**Hypothesis:** Increasing L1 to 0.5 may further suppress noisy leaf weights; the previous settings 0.1, 0.2, and 0.3 each improved the best score, with the largest step at 0.3.

**Research:** The official [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says `reg_alpha` controls L1 regularization on leaf weights and larger values make the model more conservative.

**Change:** Set `reg_alpha=0.5` only. Result pending.

**Outcome:** Eval AUC 0.7420 (`46e7cda`), +0.0004. Kept as the new best.

## Experiment 47 — continue L1 leaf penalty tuning (planned)

**Class:** Follow-up to the steady gains from `reg_alpha=0.1` through `0.5`.

**Hypothesis:** Raising L1 to 0.8 may continue to regularize weak leaf outputs and improve generalization; the larger step will also reveal whether the recent gains are flattening.

**Research:** The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) documents the conservative effect of increasing `reg_alpha`.

**Change:** Set `reg_alpha=0.8` only. Result pending.

**Outcome:** Eval AUC 0.7431 (`780791e`), +0.0011. Kept as the new best; L1 regularization continues to improve the score.

## Experiment 48 — L1 regularization bracket (planned)

**Class:** Follow-up to experiment 47's substantial improvement.

**Hypothesis:** Test a higher L1 penalty of 1.2 to see whether stronger leaf shrinkage continues to help or begins to underfit.

**Research:** The official [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) specifies that increasing `reg_alpha` makes the model more conservative.

**Change:** Set `reg_alpha=1.2` only. Result pending.

**Outcome:** Eval AUC 0.7438 (`3c046b1`), +0.0007. Kept as the new best.

## Experiment 49 — stronger L1 regularization (planned)

**Class:** Follow-up to the consistent gains through `reg_alpha=1.2`.

**Hypothesis:** A larger `reg_alpha=2.0` may continue to reduce noisy leaf weights; because each step so far has helped, this tests whether the trend holds at a materially stronger penalty.

**Research:** XGBoost's [parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) identifies `reg_alpha` as leaf-weight L1 regularization and notes that larger values produce more conservative models.

**Change:** Set `reg_alpha=2.0` only. Result pending.

**Outcome:** Eval AUC 0.7447 (`34f4c37`), +0.0009. Kept as the new best; stronger L1 has improved at every tested level.

## Experiment 50 — extend L1 regularization range (planned)

**Class:** Follow-up to the monotonic gains up through `reg_alpha=2.0`.

**Hypothesis:** A larger `reg_alpha=3.5` may continue reducing overfit; this wider step checks whether the improvement survives a stronger leaf penalty.

**Research:** The XGBoost [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes the effect of increasing `reg_alpha` on leaf weights.

**Change:** Set `reg_alpha=3.5` only. Result pending.

**Outcome:** Eval AUC 0.7455 (`41b15de`), +0.0008. Kept as the new best.

## Synthesis after 50 experiments

- Current best is `41b15de` at Eval AUC 0.7455 (+0.0252 over the 0.7203 baseline). Its `reg_alpha=3.5` is paired with `reg_lambda=2`, 600 rounds at learning rate 0.05, depth 5, child weight 2, categorical thresholds 8, and 96 histogram bins.
- The regularization trend is the strongest recent signal: increasing L1 from 0.1 through 0.2, 0.3, 0.5, 0.8, 1.2, 2.0, and 3.5 improved every time, adding 0.0050 AUC after the 0.1 checkpoint. This suggests leaf weights were under-regularized even after the original L2 improvement.
- Mild tree-level feature sampling (0.9) reduced AUC; the explicit weekday-hour category also lost 0.0015 and increased artifact/evaluation cost. Existing tests still favor the compact base predictors plus `DepHour`.
- The weekday-hour attempt first crashed on a needless integer cast of string labels; the corrected train-fitted categorical implementation ran successfully and was discarded based on score.

**Current theory:** The current feature set is strong, while carefully increasing leaf-weight shrinkage substantially improves ranking. Next, test a distinct tree-complexity control or feature ablation under the new L1 setting, then continue the alpha range only if results support it.

## Research pass after experiment 50

The official [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says increasing `max_depth` makes trees more complex and more prone to overfitting. The [parameter-tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) frame depth as a structural complexity control. Since depth 5 is the current setting and strong L1 regularization has materially improved the model, test one deeper level to see whether leaf shrinkage now supports useful extra interactions.

## Experiment 51 — depth 6 under stronger L1 (planned)

**Class:** Follow-up to the new best, testing a distinct structural capacity control.

**Hypothesis:** `max_depth=6` may capture additional feature interactions. Earlier depth-6 performance came from a much less regularized/shorter-round configuration, so this re-tests it alongside the current `reg_alpha=3.5` and `reg_lambda=2` penalties.

**Research:** Official [XGBoost docs](https://xgboost.readthedocs.io/en/stable/parameter.html) warn that deeper trees are more complex and more likely to overfit; the [tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) classify depth among direct complexity controls.

**Change:** Set `max_depth=6` only. Result pending.

**Outcome:** Eval AUC 0.7509 (`a8eeed4`), +0.0054. Kept as the new best. Deeper trees work substantially better with the current L1 penalty than in earlier configurations.

## Experiment 52 — depth 7 with L1 regularization (planned)

**Class:** Follow-up to the large depth-6 improvement.

**Hypothesis:** A further depth increase may capture higher-order interactions now that the stronger L1 penalty controls leaf outputs. Depth 7 tests whether the depth-6 gain continues or reaches an overfitting boundary.

**Research:** The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) cautions that deeper trees increase complexity and overfitting risk.

**Change:** Set `max_depth=7` only, retaining `reg_alpha=3.5`. Result pending.

**Outcome:** Eval AUC 0.7534 (`e0a4e0a`), +0.0025. Kept as the new best; depth 7 outperformed depth 6 under the current regularization.

## Experiment 53 — depth 8 with stronger L1 (planned)

**Class:** Follow-up to the two successive depth increases that improved AUC.

**Hypothesis:** Try depth 8 to check whether still deeper interactions help under `reg_alpha=3.5`, or whether generalization now peaks at depth 7.

**Research:** The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) warns that increased depth adds complexity and overfitting risk; the recent depth-6 and depth-7 results motivate this bounded next step.

**Change:** Set `max_depth=8` only. Result pending.

**Outcome:** Eval AUC 0.7547 (`b08cbea`), +0.0013. Kept as the new best.

## Experiment 54 — depth 9 with strong L1 (planned)

**Class:** Follow-up to three consecutive depth improvements under `reg_alpha=3.5`.

**Hypothesis:** A depth-9 tree may capture higher-order interactions in carrier, airport, calendar, and departure hour. Continue cautiously because the official docs warn that deeper trees can overfit.

**Research:** XGBoost's [parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) states that increasing `max_depth` increases complexity and overfitting risk.

**Change:** Set `max_depth=9` only. Result pending.

**Outcome:** Eval AUC 0.7569 (`d19750e`), +0.0022. Kept as the new best.

## Experiment 55 — depth 10 with strong L1 (planned)

**Class:** Follow-up to four successive depth improvements under `reg_alpha=3.5`.

**Hypothesis:** Test depth 10 to see if the monotonic depth trend continues. Strong leaf penalties may control some of the added complexity, but this is increasingly likely to reach the overfit boundary.

**Research:** The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) warns that deeper trees are more complex and prone to overfitting.

**Change:** Set `max_depth=10` only. Result pending.

**Outcome:** Eval AUC 0.7572 (`49788cd`), +0.0003. Kept as the new best, though the gain is smaller than the previous depth increases.

## Experiment 56 — depth 11 with strong L1 (planned)

**Class:** Follow-up to the small continued gain at depth 10.

**Hypothesis:** A further increase to depth 11 may continue capturing interactions, while `reg_alpha=3.5` still shrinks leaf weights. The smaller depth-10 gain suggests the optimum may be near.

**Research:** The official [XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) describe the increasing overfit risk from deeper trees.

**Change:** Set `max_depth=11` only. Result pending.

**Outcome:** Eval AUC 0.7576 (`cf8436e`), +0.0004. Kept as the new best; the depth trend is still positive but has largely tapered.

## Experiment 57 — depth 12 with strong L1 (planned)

**Class:** Follow-up to depth 11's small gain.

**Hypothesis:** Test depth 12 as the next point in the depth sweep. The score is still increasing, but model size and training cost are rising, and the marginal gains have shrunk.

**Research:** The official [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) cautions that deep trees are more likely to overfit and consume more memory.

**Change:** Set `max_depth=12` only. Result pending.

**Outcome:** Eval AUC 0.7582 (`8b95c23`), +0.0006. Kept as the new best.

## Experiment 58 — stronger L1 at depth 12 (planned)

**Class:** Follow-up testing the interaction between the best tree depth and leaf regularization.

**Hypothesis:** Deeper trees may benefit from more leaf-weight shrinkage. Raise `reg_alpha` from 3.5 to 5.0 while holding depth 12 fixed.

**Research:** The official [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `reg_alpha` as L1 regularization on leaf weights, while the tuning notes explain that depth adds model capacity and overfitting risk.

**Change:** Set `reg_alpha=5.0` only. Result pending.

**Outcome:** Eval AUC 0.7604 (`a2bf721`), +0.0022. Kept as the new best; stronger L1 substantially improved the depth-12 model.

## Experiment 59 — larger L1 at depth 12 (planned)

**Class:** Follow-up to the strong depth-12 gain at `reg_alpha=5.0`.

**Hypothesis:** Further increase L1 to 7.5 to check whether depth 12 still benefits from more leaf shrinkage or is nearing underfit.

**Research:** XGBoost's [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes increasing `reg_alpha` as making the model more conservative.

**Change:** Set `reg_alpha=7.5` only. Result pending.

**Outcome:** Eval AUC 0.7618 (`9497c87`), +0.0014. Kept as the new best.

## Experiment 60 — depth 13 with strong L1 (planned)

**Class:** Follow-up testing depth under the now-higher `reg_alpha=7.5` setting.

**Hypothesis:** A depth increase to 13 may continue improving interactions; the recent L1 gains suggest extra capacity benefits from stronger leaf shrinkage.

**Research:** The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes the complexity and overfitting risk of increasing depth.

**Change:** Set `max_depth=13` only, keeping `reg_alpha=7.5`. Result pending.

**Outcome:** Eval AUC 0.7605 (`fd7dd9c`), 0.0013 below the current best. Discarded and returned to `9497c87`; depth 13 appears past the current optimum.

## Synthesis after 60 experiments

- Current best is `9497c87` at Eval AUC 0.7618 (+0.0415 over baseline). It uses depth 12 with `reg_alpha=7.5`, `reg_lambda=2`, 600 rounds at learning rate 0.05, `min_child_weight=2`, category thresholds 8, and `max_bin=96`.
- Stronger L1 improved every tested value from 0.1 through 3.5 under depth 5, then 5.0 and 7.5 improved further under depth 12. Deeper trees and larger L1 work together: depth 6 through 12 repeatedly helped under stronger penalties.
- Depth 13 fell back by 0.0013, so depth 12 is the current best. Earlier tree depths 4 and 5 were weaker, and depth growth under high L1 provided the largest gains of the run.
- Mild column sampling and explicit weekday-hour categories did not help. The original compact feature set remains intact, with train-fitted `DepHour` as the only added predictor.

**Current theory:** This dataset benefits from high-capacity trees when their leaf outputs are strongly regularized. The current depth/L1 pair is near a useful boundary. Next, research and test another split-complexity control such as `min_child_weight` or `gamma` specifically under this deeper model, rather than adding more calendar crosses.

## Research pass after experiment 60

The official [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `min_child_weight` as the minimum child Hessian sum required for a split and says larger values make the model more conservative. The [parameter-tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) list it among direct tree-complexity controls. With depth 12 now winning, increasing this threshold may prune weak, low-support branches. Values 3 and 4 lost in an earlier depth-5 configuration; this test checks whether the result changes alongside depth 12 and `reg_alpha=7.5`.

## Experiment 61 — stronger child support threshold (planned)

**Class:** Follow-up testing split regularization under the deeper, heavily L1-regularized model.

**Hypothesis:** Setting `min_child_weight=4` may prevent unreliable low-Hessian leaves in depth-12 trees. The same value hurt under a shallower earlier model, so this isolates whether the current depth/L1 regime changes the outcome.

**Research:** Official [XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) explain the child Hessian threshold; [tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) identify `min_child_weight` as a tree-complexity control.

**Change:** Set `min_child_weight=4` only. Result pending.

**Outcome:** Eval AUC 0.7617 (`7d13a98`), 0.0001 below best. Discarded and returned to `9497c87`; the stronger child threshold was effectively tied with 2.

## Experiment 62 — allow smaller child nodes at depth 12 (planned)

**Class:** Follow-up to experiment 61, testing the opposite side of the child-weight threshold.

**Hypothesis:** A lower threshold of 1 may allow useful small leaves in the deeper trees; strong L1 at 7.5 can limit their output weights. This checks whether the model needs more split freedom or more child support.

**Research:** The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) explains that smaller `min_child_weight` permits partitions with less Hessian mass.

**Change:** Set `min_child_weight=1` only. Result pending.

**Outcome:** Eval AUC 0.7613 (`0d8e593`), 0.0005 below best. Discarded and returned to `9497c87`; a lower child threshold also did not help.

## Experiment 63 — minimum split loss with deep trees (planned)

**Class:** Follow-up testing a separate split regularizer under the new best model.

**Hypothesis:** A small `gamma=0.1` may prune marginal partitions from depth-12 trees while preserving strong splits. It was nearly neutral in an earlier shallower model; the deeper current model may have more weak branches to remove.

**Research:** The official [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `gamma` as the minimum loss reduction required for a split and says higher values make trees more conservative.

**Change:** Set `gamma=0.1` only. Result pending.

**Outcome:** Eval AUC 0.7608 (`4e2ca87`), 0.0010 below best. Discarded and returned to `9497c87`; a small minimum split loss did not improve the deeper model.

## Plateau research pass after experiment 63

The official [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says `max_bin` controls how continuous features are bucketed for histogram trees, and increasing it can improve split optimality at extra compute cost. Only `Distance` is numeric in this model, but the depth-12 trees now make many more potential splits than the earlier depth-5 configuration where 96 bins narrowly beat 128. Retest 128 bins in the new high-capacity model before abandoning histogram resolution.

## Experiment 64 — revisit histogram resolution at depth 12 (planned)

**Class:** Exploration after split-regularization tests plateaued.

**Hypothesis:** The best histogram resolution may change with tree depth. `max_bin=128` can offer more distance thresholds to the deeper trees, potentially improving split choices compared with 96.

**Research:** Official [XGBoost documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `max_bin` as the number of bins for continuous features and notes that more bins can improve split optimality at higher compute cost.

**Change:** Set `max_bin=128` only. Result pending.

**Outcome:** Eval AUC 0.7606 (`368d3f2`), 0.0012 below the current best. Discarded and returned to `9497c87`; higher histogram resolution did not help at depth 12.

## Experiment 65 — stronger L1 at depth 12 (planned)

**Class:** Follow-up to the continued gains from `reg_alpha=5.0` to `7.5` under depth 12.

**Hypothesis:** Increase `reg_alpha` to 10.0 to test whether the deep model continues to benefit from suppressing weak leaf weights.

**Research:** The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines L1 regularization on leaf weights and says larger values make the model more conservative.

**Change:** Set `reg_alpha=10.0` only. Result pending.

**Outcome:** Eval AUC 0.7611 (`66a7ad4`), 0.0007 below best. Discarded and returned to `9497c87`; the stronger penalty appears to over-regularize.

## Experiment 66 — bracket L1 near 7.5 (planned)

**Class:** Follow-up bracketing the best depth-12 L1 value.

**Hypothesis:** `reg_alpha=9.0` may improve on 7.5 while staying below the over-regularizing 10.0 setting.

**Research:** The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes the conservative effect of stronger L1 penalties; the 7.5/10 results motivate this local bracket.

**Change:** Set `reg_alpha=9.0` only. Result pending.

**Outcome:** Eval AUC 0.7611 (`4cd87c5`), tied with `reg_alpha=10.0` and 0.0007 below best. Discarded and returned to `9497c87`; 7.5 remains the better tested value.

## Experiment 67 — stronger L2 at depth 12 (planned)

**Class:** Follow-up testing the interaction of L2 with the now-high-capacity model.

**Hypothesis:** `reg_lambda=4` may further stabilize deep leaf scores. `reg_lambda=2` improved on 1 in an earlier shallower model; the depth-12/alpha-7.5 configuration may favor a stronger L2 penalty.

**Research:** The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) identifies `reg_lambda` as L2 regularization on leaf weights and says larger values make the model more conservative.

**Change:** Set `reg_lambda=4` only. Result pending.

**Outcome:** Eval AUC 0.7620 (`72bf32c`), +0.0002. Kept as the new best; the stronger L2 penalty helped slightly.

## Experiment 68 — continue L2 tuning at depth 12 (planned)

**Class:** Follow-up to the small gain at `reg_lambda=4`.

**Hypothesis:** Increasing L2 to 6 may further shrink extreme leaf weights in the deep trees, complementing `reg_alpha=7.5`.

**Research:** The official [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says larger `reg_lambda` makes the model more conservative.

**Change:** Set `reg_lambda=6` only. Result pending.

**Outcome:** Eval AUC 0.7617 (`ada4c8d`), 0.0003 below best. Discarded and returned to `72bf32c`; the L2 optimum appears near 4.

## Experiment 69 — bracket L2 near 4 (planned)

**Class:** Follow-up bracketing the best L2 value for depth 12 and `reg_alpha=7.5`.

**Hypothesis:** `reg_lambda=3` may improve on 2 while avoiding the lower score at 6.

**Research:** The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `reg_lambda` as L2 leaf-weight regularization; values 2, 4, and 6 motivate this local bracket.

**Change:** Set `reg_lambda=3` only. Result pending.

**Outcome:** Eval AUC 0.7616 (`09386ac`), 0.0004 below best. Discarded and returned to `72bf32c`; 4 remains the stronger L2 value.

## Experiment 70 — L1/L2 balance at depth 12 (planned)

**Class:** Follow-up to the new best `reg_lambda=4`, checking its interaction with L1.

**Hypothesis:** `reg_alpha=6.5` paired with L2 4 may reduce over-shrinkage compared with 7.5 while retaining strong regularization.

**Research:** The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) documents both L1 and L2 as leaf-weight penalties that make the model more conservative as they increase.

**Change:** Set `reg_alpha=6.5` only, holding `reg_lambda=4`. Result pending.

**Outcome:** Eval AUC 0.7601 (`4d38072`), 0.0019 below best. Discarded and returned to `72bf32c`; the tested L1/L2 balance is worse than 7.5/4.

## Experiment 71 — more boosting rounds with deep trees (planned)

**Class:** Follow-up to the new best high-capacity, strongly regularized model.

**Hypothesis:** Raising `n_estimators` from 600 to 800 may let the lower learning rate and strong leaf penalties build a stronger ensemble incrementally.

**Research:** XGBoost's [parameter-tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) explain that reducing step size generally requires increasing the number of rounds.

**Change:** Set `n_estimators=800` only. Result pending.

**Outcome:** Eval AUC 0.7612 (`2486b3b`), 0.0008 below best. Discarded and returned to `72bf32c`; 600 rounds remains better than 800.

## Experiment 72 — fewer boosting rounds at depth 12 (planned)

**Class:** Follow-up bracketing the 600-round best after 800 rounds lost AUC.

**Hypothesis:** Reducing rounds to 500 may stop before fitting residual noise in the high-capacity trees, improving generalization.

**Research:** The XGBoost [parameter-tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) discuss the tradeoff between learning rate and number of boosting steps.

**Change:** Set `n_estimators=500` only.

**Outcome:** Eval AUC 0.7619 (`875b660`), 0.0001 below the numeric best. Kept as a simplicity/efficiency win: it removes 100 trees, reduces training time from about 9.3s to 8.0s, and reduces artifact size from 47.9 MB to 41.6 MB.

## Experiment 73 — bracket boosting rounds at 550 (planned)

**Class:** Follow-up between the 500-round and 600-round results.

**Hypothesis:** `n_estimators=550` may preserve the smaller model while recovering or exceeding the 0.7620 AUC of the 600-round model.

**Research:** XGBoost's [parameter-tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) discuss the relationship between learning rate and number of rounds.

**Change:** Set `n_estimators=550` only.

**Outcome:** Eval AUC 0.7621 (`adccf54`), +0.0001 over the 600-round numeric best. Kept as the new best.

## Experiment 74 — refine the round count (planned)

**Class:** Follow-up to the 550-round improvement.

**Hypothesis:** Test 575 rounds between the 550-round best and the earlier 600-round setting to refine the ensemble size.

**Research:** XGBoost's [tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) describe the learning-rate/round-count tradeoff.

**Change:** Set `n_estimators=575` only. Result pending.

**Outcome:** Eval AUC 0.7620 (`10d3c9e`), 0.0001 below the 550-round best with 25 extra trees. Discarded and returned to `adccf54`.

## Experiment 75 — refine round count at 525 (planned)

**Class:** Follow-up between 500 and 550 rounds.

**Hypothesis:** Test 525 rounds to see if it retains the 500-round model's smaller size while approaching the better 550-round score.

**Research:** XGBoost's [parameter-tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) discuss number of rounds alongside learning rate.

**Change:** Set `n_estimators=525` only. Result pending.

**Outcome:** Eval AUC 0.7620 (`9192ac1`), 0.0001 below 550. Kept as a simplicity/efficiency win: 25 fewer trees with about 1.6 MB less artifact size and slightly shorter training.

## Experiment 76 — test 540 rounds (planned)

**Class:** Follow-up between the 525-round and 550-round results.

**Hypothesis:** `n_estimators=540` may match or exceed the 550-round best while retaining a modestly smaller model.

**Research:** The [XGBoost parameter-tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) discuss the relationship between learning rate and boosting rounds.

**Change:** Set `n_estimators=540` only. Result pending.

**Outcome:** Eval AUC 0.7620 (`7e3d57d`), tied with 525 rounds but with a larger model. Discarded and returned to `9192ac1`.

## Experiment 77 — lower learning rate with more rounds (planned)

**Class:** Exploration of the learning-rate/round-count tradeoff on the depth-12 model.

**Hypothesis:** A learning rate of 0.04 with 650 rounds may make smaller updates while maintaining a similar total boosting budget, potentially improving generalization.

**Research:** XGBoost's [parameter-tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) say that when reducing the step size, the number of rounds should increase.

**Change:** Set `learning_rate=0.04` and `n_estimators=650` as a paired schedule change. Result pending.

**Outcome:** Eval AUC 0.7620 (`6f48f7e`), tied with simpler 525/550-round models but requiring more rounds. Discarded.

## Experiment 78 — fine L1 adjustment at the best round count (planned)

**Class:** Follow-up to the `reg_alpha=7.5` best.

**Hypothesis:** A small increase to 8.0 may improve leaf shrinkage in the deep model while staying short of the weaker 9.0 and 10.0 settings.

**Research:** The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes increasing `reg_alpha` as increasing conservatism; prior tests bracket the promising region around 7.5.

**Change:** Set `reg_alpha=8.0` only. Result pending.

**Outcome:** Eval AUC 0.7614 (`5255492`), 0.0007 below the 550-round best. Discarded and returned to `adccf54`.

## Experiment 79 — lower L1 bracket at 7.0 (planned)

**Class:** Follow-up bracketing the best `reg_alpha=7.5` value.

**Hypothesis:** Test 7.0 to see whether a slightly weaker penalty retains the score after 6.5 performed poorly and 8.0 fell below the best.

**Research:** The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) explains how L1 strength affects leaf-weight shrinkage; prior tests motivate a narrow bracket around 7.5.

**Change:** Set `reg_alpha=7.0` only. Result pending.

**Outcome:** Eval AUC 0.7617 (`2f30550`), 0.0004 below the best. Discarded and returned to `adccf54`; `reg_alpha=7.5` remains best.

## Experiment 80 — L2 midpoint at 4.5 (planned)

**Class:** Follow-up between the winning `reg_lambda=4` and weaker `reg_lambda=6` settings.

**Hypothesis:** `reg_lambda=4.5` may preserve the small benefit of stronger L2 while avoiding the drop at 6.

**Research:** The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) documents `reg_lambda` as L2 leaf-weight regularization.

**Change:** Set `reg_lambda=4.5` only. Result pending.

**Outcome:** Eval AUC 0.7621 (`b40b823`), tied with the best but no simpler. Discarded and returned to `adccf54`.

## Experiment 81 — final L2 bracket at 3.5 (planned)

**Class:** Follow-up between `reg_lambda=3` and the 4/4.5 results.

**Hypothesis:** `reg_lambda=3.5` may capture the benefit of moderate L2 while staying close to the 4.0 peak.

**Research:** The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes L2 leaf-weight regularization; earlier scores place the likely optimum between 3 and 4.5.

**Change:** Set `reg_lambda=3.5` only. Result pending.

**Outcome:** Eval AUC 0.7615 (`61f15e9`), 0.0006 below best. Discarded and returned to `adccf54`.

## Final summary

- Best numeric result: Eval AUC **0.7621**, commit `adccf54` (550 rounds, depth 12, `reg_alpha=7.5`, `reg_lambda=4`, `min_child_weight=2`, `max_bin=96`, categorical thresholds 8, and train-fitted `DepHour`). This is +0.0418 over the 0.7203 baseline.
- The largest gains came from increasing L1 regularization and then increasing tree depth under that regularization. Depth 6 through 12 improved steadily with `reg_alpha=3.5`; at depth 12, L1 values 5 and 7.5 improved further.
- L2=4 gave a small gain at depth 12; 3, 3.5, 4.5, and 6 were weaker or tied. The 550-round model narrowly beat 500, 575, and 600. A 525-round version (`9192ac1`, 0.7620) was kept as a smaller near-equal model.
- Column sampling, weekday-hour crosses, stronger child thresholds, `gamma=0.1`, higher histogram resolution, L1 above 7.5, and depth 13 did not improve the best.
- Next, test a small learning-rate/round-count grid around 0.04–0.05 and 500–650 rounds under the current depth-12/L1/L2 configuration, or test nearby `min_child_weight` values only after a larger change to regularization.
