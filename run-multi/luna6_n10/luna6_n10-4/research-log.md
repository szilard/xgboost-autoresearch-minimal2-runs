# Research log — sep30

## Setup

- Created branch `sep30` from the existing `main` HEAD.
- Confirmed `data/train.csv` and `data/eval.csv` are present.
- No training changes were made for the baseline.

## Baseline — `92e43e6`

- Ran the untouched `train.py` through the harness.
- Eval AUC: **0.7203**. This is the reference score for subsequent experiments.

## Research before experiment 1

- The [XGBoost parameter-tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) describe `eta` as shrinkage and say to increase boosting rounds when reducing it. The [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) explains that shrinkage makes updates more conservative.
- A flight-delay prediction study reports that prior work commonly uses day-of-week and month alongside flight information, and finds airport traffic context valuable for departure-delay prediction ([Shao et al., 2019](https://arxiv.org/abs/1911.01605)). The available training features already include month, weekday, carrier, airports, scheduled time, and distance; the extra traffic/weather sources are unavailable here.

## Experiment 1 — `2a91ba4`

- **Category:** exploration of boosting-round count.
- **Hypothesis:** 30 trees may stop before the additive model has used the available signal. Increasing to 120 while holding depth, learning rate, and all other settings fixed should improve ranking if the baseline is underfit; the harness Eval AUC decides.
- **Change:** `n_estimators` 30 → 120.
- **Result:** Eval AUC **0.7317** (+0.0114 vs baseline), status **keep**. This supports testing whether more rounds add useful signal before saturation.

## Experiment 2 — `8ca3375`

- **Category:** follow-up to `2a91ba4`.
- **Hypothesis:** the large gain from 30 to 120 trees suggests useful signal remains; doubling to 240 with the same learning rate and depth should reveal whether additional rounds improve ranking or start to overfit.
- **Change:** `n_estimators` 120 → 240; all other settings fixed.
- **Result:** Eval AUC **0.7345** (+0.0028 vs 120 trees), status **keep**. The improvement supports one more larger-count check.

## Experiment 3 — `47e578c`

- **Category:** follow-up to `8ca3375`.
- **Hypothesis:** the score still rose at 240 trees, so 480 may capture further additive signal; if it falls, the current round count may be near the generalization optimum.
- **Change:** `n_estimators` 240 → 480; all other settings fixed.
- **Result:** Eval AUC **0.7316** (−0.0029 vs 240 trees), status **discard**. Reset to the 240-tree model; this count appears beyond the current sweet spot.

## Research before experiment 4

- A recent flight-delay feature-engineering study derives scheduled departure hour and minute from `CRS_DEP_TIME` in `HHMM` form and also tests time-of-day bins ([Electronics, 2024](https://www.mdpi.com/2079-9292/13/24/4910)). This motivates exposing hour and minute separately while retaining the original field.
- These are per-row transformations of an existing field, so they preserve the `prepare(df)` row-independence requirement and need no fitted lookup.

## Experiment 4 — `742f9c7`

- **Category:** exploration / first feature-engineering change.
- **Hypothesis:** the raw `HHMM` integer combines hour and minute in a way that makes splits within the same hour less direct. Adding separate scheduled hour and minute columns may let trees capture coarse daily patterns and within-hour effects with fewer splits.
- **Change:** add row-wise `CRSDepHour` and `CRSDepMinute` in `prepare(df)`, retaining the original `CRSDepTime`; keep the 240-tree model and other settings fixed.
- **Result:** Eval AUC **0.7342** (−0.0003 vs 240-tree reference), status **discard**. The pair did not improve the reference model.

## Experiment 5 — `4c19728`

- **Category:** ablation of experiment 4.
- **Hypothesis:** the `CRSDepMinute` feature may add noise or redundancy; keeping only the hour may preserve broad time-of-day signal with less complexity.
- **Change:** add only row-wise `CRSDepHour` in `prepare(df)`; keep the 240-tree model and all other settings fixed.
- **Result:** Eval AUC **0.7351** (+0.0006 vs reference), status **keep**. The hour component alone helps slightly while the minute component was not useful in the combined test.

## Experiment 6 — `d8b3bde`

- **Category:** follow-up to `4c19728`.
- **Hypothesis:** six-level trees may be unnecessarily complex after adding 240 rounds; depth 5 may reduce variance while retaining useful interactions. XGBoost's [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) notes that greater `max_depth` increases complexity and overfitting risk.
- **Change:** `max_depth` 6 → 5; keep 240 trees, the hour feature, and other settings fixed.
- **Result:** Eval AUC **0.7357** (+0.0006), status **keep**. The small improvement supports testing one further step of regularization.

## Experiment 7 — `a979090`

- **Category:** follow-up to `d8b3bde`.
- **Hypothesis:** the depth-5 improvement suggests slightly smaller trees may further reduce overfitting; test depth 4 while keeping the boosted-round count and features unchanged.
- **Change:** `max_depth` 5 → 4; all other settings fixed.
- **Result:** Eval AUC **0.7332** (−0.0025 vs depth 5), status **discard**. Depth 5 is preferable; reset to `d8b3bde`.

## Experiment 8 — `7c1caac`

- **Category:** exploration of stochastic regularization.
- **Hypothesis:** subsampling 80% of rows per tree may reduce variance in the 240-tree, depth-5 model while preserving most training signal. XGBoost's [tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommend `subsample` as a way to add randomness and improve robustness to noise.
- **Change:** set `subsample=0.8`; keep other parameters and features fixed.
- **Result:** Eval AUC **0.7249** (−0.0108 vs best), status **discard**. Row subsampling at 0.8 hurt substantially; reset to `d8b3bde`.

## Experiment 9 — `56fefc4`

- **Category:** exploration of feature subsampling, distinct from experiment 8's row subsampling.
- **Hypothesis:** randomizing the available predictors per tree may reduce tree correlation without discarding 20% of the training rows. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `colsample_bytree` as the feature fraction sampled per tree.
- **Change:** set `colsample_bytree=0.8`; keep all other settings fixed.
- **Result:** Eval AUC **0.7356** (−0.0001 vs best), status **discard**. Feature subsampling did not improve the current model, so reset to `d8b3bde`.

## Synthesis after 10 runs (including the baseline)

- Best result is Eval AUC **0.7357** at `d8b3bde` (240 trees, depth 5, scheduled departure hour feature).
- More trees helped strongly from 30 to 120 (+0.0114) and again from 120 to 240 (+0.0028), but 480 fell by 0.0029. The useful range appears centered near 240 at learning rate 0.1.
- The scheduled hour alone added a small gain; adding minute with it did not. Depth 5 beat both depths 6 and 4 by small but consistent margins against their respective comparisons.
- Row subsampling at 0.8 hurt substantially; column subsampling at 0.8 was effectively neutral and slightly lower. Keep both at defaults for now.
- **Current theory:** moderate tree count and depth are helping generalization; useful gains may come from making airport-pair interactions explicit while preserving native categorical handling.

## Research before experiment 10

- The [XGBoost categorical-data tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains that native categorical features can split by category membership or one-hot-style equality tests. The current pipeline already uses pandas categories and `enable_categorical=True`.
- A flight-delay study describes origin–destination pairs and route-based delay propagation as part of its spatial-temporal inputs ([FlightNet-ST, 2025](https://link.springer.com/article/10.1007/s44196-025-00932-2)). This does not directly test a simple route category on our data, but it motivates exposing the directional airport pair as one additional feature.

## Experiment 10 — `7fd9c17`

- **Category:** exploration of a route interaction feature.
- **Hypothesis:** a directional `Origin`→`Dest` category may let depth-5 trees learn route-specific risk without first combining two separate airport splits. It is a row-wise feature, and its category levels will be fit from `train.csv` only.
- **Change:** add a native categorical `Route` feature while retaining `Origin` and `Dest`; keep model parameters fixed at the current best.
- **Result:** Eval AUC **0.7077** (−0.0280 vs best), status **discard**. The high-cardinality route feature hurt severely; reset to `d8b3bde`.

## Research before experiment 11

- The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) states that `max_cat_threshold` limits the categories considered by partition-based splits and is intended to prevent overfitting. The [categorical-data tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) describes these splits as grouping categories with similar output values.
- Since the route feature caused a large regression and has many possible airport pairs, test whether limiting category split candidates to 32 rescues it. This is a targeted follow-up, not a new baseline change.

## Experiment 11 — `5a215ef`

- **Category:** follow-up to `7fd9c17`, testing categorical regularization.
- **Hypothesis:** the route feature may be useful but overfit when its many category values are freely partitioned. Adding `max_cat_threshold=32` may reduce that overfit.
- **Change:** re-add the train-fitted directional `Route` category and set `max_cat_threshold=32`; keep the rest of the `d8b3bde` model fixed.
- **Result:** Eval AUC **0.7153** (−0.0204 vs best). This is higher than the unbounded route trial but still far below the best, so status **discard** and reset to `d8b3bde`.

## Experiment 12 — `01ce3e0`

- **Category:** exploration of native categorical split regularization.
- **Hypothesis:** even without the route feature, limiting category candidates may reduce overfit in the existing airport/carrier categories. XGBoost documents `max_cat_threshold` specifically as a regularizer for partition-based categorical splits.
- **Change:** set `max_cat_threshold=32` on the current best model, with no route feature and all other settings unchanged.
- **Result:** Eval AUC **0.7355** (−0.0002), status **discard**. The threshold did not improve the existing categorical features; reset to `d8b3bde`.

## Experiment 13 — `125f16b`

- **Category:** exploration of categorical split strategy.
- **Hypothesis:** one-hot splits for low-cardinality Month and DayOfWeek may capture category-specific effects better than partition splits. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says features below `max_cat_to_onehot` use one-hot splits.
- **Change:** set `max_cat_to_onehot=13`; retain the current features and all other settings.
- **Result:** Eval AUC **0.7336** (−0.0021), status **discard**. Forcing one-hot splits on low-cardinality features hurt; reset to `d8b3bde`.

## Experiment 14 — `e8296c8`

- **Category:** exploration of leaf-size regularization.
- **Hypothesis:** increasing `min_child_weight` may prevent marginal splits in the depth-5, 240-tree model. XGBoost's [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says larger values make the model more conservative.
- **Change:** set `min_child_weight=5`; leave the best features and all other parameters unchanged.
- **Result:** Eval AUC **0.7351** (−0.0006), status **discard**. The higher child-weight constraint did not help; reset to `d8b3bde`.

## Experiment 15 — `994c2da`

- **Category:** exploration of split-gain regularization.
- **Hypothesis:** a small positive minimum split loss may suppress weak, noisy splits while retaining useful ones. XGBoost defines `gamma` as the minimum loss reduction required to split a leaf.
- **Change:** set `gamma=0.1`; keep the best features and other parameters fixed.
- **Result:** Eval AUC **0.7349** (−0.0008), status **discard**. This penalty did not help; reset to `d8b3bde`.

## Experiment 16 — `e9c2235`

- **Category:** follow-up to `994c2da`.
- **Hypothesis:** `gamma=0.1` may have blocked too many useful splits; a tenfold smaller value tests whether light split regularization retains signal while still removing marginal splits.
- **Change:** set `gamma=0.01`; keep every other setting fixed.
- **Result:** Eval AUC **0.7357** (equal at displayed precision), status **discard**. It did not beat the best and adds complexity; reset to `d8b3bde`.

## Experiment 17 — `9964eea`

- **Category:** exploration of L2 leaf-weight regularization.
- **Hypothesis:** stronger L2 shrinkage may reduce variance in leaf scores without the split suppression caused by `gamma` or `min_child_weight`. XGBoost's [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says increasing `reg_lambda` makes the model more conservative.
- **Change:** set `reg_lambda=5`; keep all other settings fixed.
- **Result:** Eval AUC **0.7360** (+0.0003), status **keep**. This is a new best; test a stronger L2 value next before leaving this parameter path.

## Experiment 18 — `0030eea`

- **Category:** follow-up to `9964eea`.
- **Hypothesis:** if L2 shrinkage reduced noisy leaf scores at 5, increasing to 10 may improve further; if it is too strong, AUC will fall.
- **Change:** `reg_lambda` 5 → 10; all other settings fixed.
- **Result:** Eval AUC **0.7346** (−0.0014 vs `reg_lambda=5`), status **discard**. Stronger shrinkage hurt; restore `9964eea`.

## Experiment 19 — `d714902`

- **Category:** follow-up to `9964eea`.
- **Hypothesis:** `reg_lambda=10` was too strong, while 5 slightly improved over the default. Testing 3 checks an intermediate level that may retain the gain with less shrinkage.
- **Change:** `reg_lambda` 5 → 3; all other settings fixed.
- **Result:** Eval AUC **0.7350** (−0.0010 vs 5), status **discard**. Reset to `9964eea`; the tested L2 values favor 5.

## Synthesis after 20 runs (including the baseline)

- Best result is Eval AUC **0.7360** at `9964eea`: 240 trees, depth 5, learning rate 0.1, the scheduled departure hour feature, and `reg_lambda=5`.
- Tree count still favors 240: 30→120 and 120→240 improved AUC, while 480 regressed. Depth 5 beat depths 4 and 6. Departure hour gave a small gain, and L2=5 added another small gain.
- Row sampling, the route category, one-hot category splits, higher child weight, gamma, and stronger/weaker L2 values did not beat the current best. Column sampling and gamma=0.01 tied or nearly tied but added complexity.
- **Current theory:** moderate model complexity is working. Feature gains are small, so the next experiments should add structured signal with simple, row-independent transformations rather than sparse route categories or aggressive regularization.

## Research before experiment 21

- In a flight-delay study, time variables are represented with sine/cosine pairs to preserve periodicity; trigonometric time features were selected more often than their non-encoded versions ([Probabilistic Flight Delay Predictions, 2021](https://www.mdpi.com/2226-4301/8/6/152)).
- A separate flight-delay study explains that 23:00 and 00:00 are adjacent on the daily cycle and uses circular sine/cosine encodings for hour, weekday, and month ([Prediction of Flight Delays at Beijing Capital International Airport](https://www.mdpi.com/2076-3417/12/20/10621)).
- These studies support testing a scheduled-departure-time cycle on this feature set. I’ll add only the daily sine/cosine pair first, preserving the original time and hour features so the experiment measures the added representation.

## Experiment 21 — `6dc2e7c`

- **Category:** exploration of cyclical time feature engineering.
- **Hypothesis:** cyclic sine/cosine columns may help the trees recognize the midnight boundary, where late-night and just-after-midnight flights are close in time, while the raw HHMM and hour features preserve useful threshold splits.
- **Change:** parse scheduled HHMM into minutes since midnight and add daily sine/cosine features in `prepare(df)`; keep current model parameters and existing features unchanged.
- **Result:** Eval AUC **0.7345** (−0.0015), status **discard**. Daily cyclic columns did not help alongside the original time and hour features; reset to `9964eea`.

## Experiment 22 — pending commit

- **Category:** follow-up feature engineering for the weekly calendar cycle.
- **Hypothesis:** unlike scheduled time, `DayOfWeek` is already categorical; adding a cyclic representation may expose adjacency between Saturday and Sunday while preserving the categorical column. A flight-delay study selected trigonometric weekday features among its predictors ([2021 study](https://www.mdpi.com/2226-4301/8/6/152)).
- **Change:** add row-wise `DayOfWeekSin` and `DayOfWeekCos`; retain the original feature and keep model parameters fixed.
- **First attempt (`b849b25`):** crashed because `DayOfWeek` was loaded as strings and could not be multiplied by a float. The fix coerces numeric strings and maps weekday names before calculating the cycle.
- **Rerun (`b6b526d`):** Eval AUC **0.7360**, tied at displayed precision with the best. Status **discard** because it adds two features without a score gain; reset to `9964eea`.

## Experiment 23 — pending commit

- **Category:** exploration of an annual calendar cycle.
- **Hypothesis:** monthly delay patterns may vary smoothly across the year, with December and January adjacent; a sine/cosine pair may expose that periodic structure while preserving native Month categories.
- **Research basis:** a 2021 flight-delay study uses Month sine/cosine features alongside the original Month field ([paper](https://www.mdpi.com/2226-4301/8/6/152)).
- **Change:** add row-wise `MonthSin` and `MonthCos`; keep the current model parameters and other features fixed.
- **Result:** Eval AUC **0.7360**, tied with the best at displayed precision. Status **discard** because the added transformations did not improve AUC; reset to `9964eea`.

## Experiment 24 — `bb71b53`

- **Category:** follow-up on the learning-rate / boosting-round relationship.
- **Hypothesis:** 480 trees at learning rate 0.1 overfit, but halving the learning rate while doubling the rounds may yield a smoother ensemble and better ranking. XGBoost's [tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) explicitly recommend increasing rounds when reducing `eta`.
- **Change:** `learning_rate` 0.1 → 0.05 and `n_estimators` 240 → 480; keep depth 5, `reg_lambda=5`, hour feature, and other settings fixed.
- **Result:** Eval AUC **0.7356** (−0.0004), status **discard**. The lower-rate, higher-round model did not beat the 240-tree reference; reset to `9964eea`.

## Research before experiment 25

- A flight-delay analysis reports that delays worsen late in the day and that the change differs by carrier, suggesting a carrier-by-hour interaction ([UC Berkeley project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches)). It is a different dataset and metric, so this motivates a test rather than predicting an outcome here.

## Experiment 25 — pending commit

- **Category:** exploration of a carrier/time interaction.
- **Hypothesis:** a native categorical `CarrierHour` feature may expose carrier-specific hourly patterns directly, while its cardinality stays below the failed origin–destination interaction.
- **Change:** fit `CarrierHour` levels on train from `UniqueCarrier` and scheduled departure hour; map the rowwise feature in `prepare(df)`, retaining both source features and keeping model settings fixed.
- **Result:** Eval AUC **0.7267** (−0.0093), status **discard**. This interaction also overfit; reset to `9964eea`.

## Experiment 26 — `050c1e3`

- **Category:** exploration of histogram split resolution.
- **Hypothesis:** finer numeric bins may improve split thresholds for scheduled time and distance. XGBoost's [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says increasing `max_bin` can improve split optimality at added computation cost.
- **Change:** set `max_bin=512`; keep all features and other model settings fixed.
- **Result:** Eval AUC **0.7358** (−0.0002), status **discard**. Finer bins at 512 did not improve the current model; reset to `9964eea`.

## Experiment 27 — `96bc96f`

- **Category:** follow-up to `050c1e3`.
- **Hypothesis:** 512 bins was nearly tied with the best; testing 1024 checks whether finer candidate thresholds provide a small gain that 512 did not capture.
- **Change:** set `max_bin=1024`; keep all other settings fixed.
- **Result:** Eval AUC **0.7349** (−0.0011), status **discard**. Further bin resolution hurt; reset to `9964eea`.

## Research before experiment 28

- XGBoost's [DART tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) describes dropping prior trees during training as a way to address overfitting. It uses the same tree parameters as `gbtree` and controls dropout with `rate_drop`; the docs note that training can be slower.

## Experiment 28 — `7695983`

- **Category:** exploration of a different booster strategy.
- **Hypothesis:** dropout may reduce dependence on early trees and improve generalization beyond the current `gbtree` model.
- **Change:** use `booster="dart"` with `rate_drop=0.1`; keep 240 trees, depth 5, learning rate 0.1, `reg_lambda=5`, and features fixed.
- **Result:** Eval AUC **0.7186** (−0.0174), status **discard**. The dropout booster was much slower and performed poorly; reset to `9964eea`.

## Experiment 29 — `4097483`

- **Category:** exploration of L1 leaf-weight regularization.
- **Hypothesis:** a small L1 penalty may suppress weak leaf weights while retaining the benefit from `reg_lambda=5`. XGBoost's [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `reg_alpha` as L1 regularization and says larger values make the model more conservative.
- **Change:** set `reg_alpha=0.1`; keep all other settings fixed.
- **Result:** Eval AUC **0.7345** (−0.0015), status **discard**. L1 at 0.1 hurt; reset to `9964eea`.

## Experiment 30 — `34a55d7`

- **Category:** follow-up to `4097483`.
- **Hypothesis:** the 0.1 L1 penalty may have been too strong; 0.01 tests whether a lighter threshold preserves the useful leaf weights while reducing only tiny ones.
- **Change:** set `reg_alpha=0.01`; all other settings fixed.
- **Result:** Eval AUC **0.7349** (−0.0011), status **discard**. The lighter L1 penalty also hurt; reset to `9964eea`.

## Synthesis after 30 runs (including the baseline)

- The best remains Eval AUC **0.7360** at `9964eea`. The core combination of 240 trees, depth 5, numeric scheduled hour, and `reg_lambda=5` remains the only clear winner.
- Experiments 21–24 found that cyclic daily/weekly/monthly representations tied or underperformed; a slower learning rate with more trees also fell short. Experiments 25–27 show that a carrier-hour category hurt substantially and finer histograms did not help. DART and both tested L1 penalties were worse.
- **Current theory:** the gain comes from a modest amount of model capacity plus the simple numeric hour feature and L2 shrinkage. Sparse interactions and more elaborate representations have not added signal. Continue with low-complexity operational features and small, isolated parameter checks.

## Experiment 31 — `227e766`

- **Category:** exploration of tree growth policy.
- **Hypothesis:** with a similar leaf budget, best-first growth may spend capacity on the strongest splits instead of expanding every branch level by level. XGBoost's [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `lossguide` as splitting the leaf with the highest loss change and supports it with histogram trees.
- **Change:** set `grow_policy="lossguide"`, `max_leaves=31`, and `max_depth=0`; retain the current features, 240 rounds, learning rate, and `reg_lambda=5`.
- **Result:** Eval AUC **0.7334** (−0.0026), status **discard**. Loss-guided growth under this leaf budget hurt; reset to `9964eea`.

## Experiment 32 — `6d5bd94`

- **Category:** exploration of split construction algorithm.
- **Hypothesis:** the approximate quantile-sketch method may produce useful split candidates different from the default histogram method, potentially improving ranking on scheduled time and distance.
- **Research basis:** the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) distinguishes `approx` (quantile sketch and gradient histogram) from `hist` (histogram-optimized approximate greedy splits).
- **Change:** set `tree_method="approx"`; keep model parameters and features fixed.
- **Result:** Eval AUC **0.7355** (−0.0005), status **discard**. Approximate split finding did not improve the histogram baseline; reset to `9964eea`.

## Research before experiment 33

- XGBoost's [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says a positive `max_delta_step` makes each leaf update more conservative and can help logistic regression under strong class imbalance. The [parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) suggest trying 1. Flight delay labels are binary and likely imbalanced, so test the suggested value without changing class weights or the objective.

## Experiment 33 — `3df773f`

- **Category:** exploration of leaf update constraints.
- **Hypothesis:** limiting each leaf's update with `max_delta_step=1` may improve generalization on the binary delay ranking task.
- **Change:** set `max_delta_step=1`; keep model parameters and features fixed.
- **Result:** Eval AUC **0.7355** (−0.0005), status **discard**. Constrained leaf updates did not improve the score; reset to `9964eea`.

## Research before experiment 34

- XGBoost's [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says `scale_pos_weight` changes positive-class weight in logistic objectives and gives the negative-to-positive count ratio as a typical starting point for imbalanced labels. Test a restrained value of 2 as a single step toward positive reweighting, without reading the dataset outside the training program.

## Experiment 34 — `c0be676`

- **Category:** exploration of positive-class weighting.
- **Hypothesis:** moderately increasing the positive-class weight may help trees focus on rare delayed flights and improve AUC.
- **Change:** set `scale_pos_weight=2`; keep model parameters and features fixed.
- **Result:** Eval AUC **0.7333** (−0.0027), status **discard**. This degree of positive-class weighting hurt ranking; reset to `9964eea`.

## Research before experiment 35

- A recent [flight-delay feature engineering study](https://www.mdpi.com/2079-9292/13/24/4910) defines a night-flight indicator for scheduled departures from 9 p.m. to 4 a.m. XGBoost's [categorical data guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) confirms categorical and partitioned splits can express group membership. Test the study's compact night-time indicator alongside the existing numeric hour feature.

## Experiment 35 — `11f684d`

- **Category:** exploration of a coarse scheduled-time feature.
- **Hypothesis:** a night-flight flag may expose a useful operational regime with one split, complementing the ordered hour feature.
- **Change:** add `IsNightFlight`, true for scheduled hours 21–23 and 0–3; leave all existing features and model parameters fixed.
- **Result:** Eval AUC **0.7360** (tie at reported precision), status **discard**. The extra feature tied the best without improving the displayed score; reset to the simpler `9964eea`.

## Research before experiment 36

- The [Berkeley flight-delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) identifies hour of day as a departure-delay predictor. XGBoost's [categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) supports categorical group splits. Test whether letting trees group individual scheduled hours performs better than treating the derived hour as ordered numeric input.

## Experiment 36 — `395f1fb`

- **Category:** representation change for scheduled departure hour.
- **Hypothesis:** delay risk can vary nonmonotonically across the day, so categorical hour splits may rank flights better than numeric thresholds.
- **Change:** represent `CRSDepHour` as a category with levels 0–23; keep all other features and model settings fixed.
- **Result:** Eval AUC **0.7356** (−0.0004), status **discard**. Treating each hour as a category did not beat ordered hour; reset to `9964eea`.

## Research before experiment 37

- The flight-delay study in [Electronics](https://www.mdpi.com/2079-9292/13/24/4910) also groups HHMM scheduled departure times into 12 two-hour intervals to represent time-of-day patterns. The 24-level categorical-hour variant just tested was slightly worse, so compare the coarser 12-level block while retaining the original numeric hour.

## Experiment 37 — `e936bc5`

- **Category:** exploration of a coarser scheduled-time feature.
- **Hypothesis:** two-hour categories may capture broad operational periods with less sparsity than a separate category for every hour.
- **Change:** add categorical `CRSDepTimeBlock` levels 0–11 from the scheduled hour divided by two; leave other features and settings fixed.
- **Result:** Eval AUC **0.7356** (−0.0004), status **discard**. The coarser block also failed to improve the numeric-hour baseline; reset to `9964eea`.

## Research before experiment 38

- XGBoost's [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `max_depth` as a direct control on tree complexity. Depth 5 beat depth 4 earlier in the run; now test depth 6 with the stronger `reg_lambda=5` setting to see whether shrinkage makes a slightly more expressive tree useful.

## Experiment 38 — `b3479be`

- **Category:** follow-up tuning of tree capacity.
- **Hypothesis:** stronger L2 regularization may permit depth-6 trees to model useful feature interactions without the overfit seen at the original depth-6 setup.
- **Change:** set `max_depth=6`; keep current feature set and all other model parameters fixed.
- **Result:** Eval AUC **0.7359** (−0.0001), status **discard**. Depth 6 nearly tied but did not improve over depth 5; reset to `9964eea`.

## Research before experiment 39

- A flight-delay feature study in [Electronics](https://www.mdpi.com/2079-9292/13/24/4910) defines `Is Weekend` as a Saturday/Sunday flag to summarize weekend-specific traffic and operations. `DayOfWeek` is already present categorically, but an explicit binary grouping gives trees a direct weekday/weekend split. Derive it from weekday names or the common 1–7 Monday–Sunday encoding without inspecting the data separately.

## Experiment 39 — `36c128f`

- **Category:** exploration of a weekday/weekend grouping.
- **Hypothesis:** a weekend flag may capture a shared Saturday/Sunday effect more directly than learning it from seven separate weekday levels.
- **Change:** add `IsWeekend` from `DayOfWeek`; preserve the existing weekday feature and all model settings.
- **Result:** Eval AUC **0.7360** (tie at reported precision), status **discard**. The added grouping tied the best but did not improve the reported score; reset to `9964eea`.

## Experiment 40 — pending commit

- **Category:** follow-up tuning of boosting rounds.
- **Hypothesis:** 240 rounds beat both 120 and 480 in earlier trials; testing 300 probes a modest increase near the current optimum while preserving the learning rate.
- **Change:** set `n_estimators=300`; keep depth, features, learning rate, and regularization fixed.
- **Result:** Eval AUC **0.7364** (+0.0004), status **keep**. Retain `2e3ccba` as the new best; 300 rounds improved the current model.

## Synthesis after 40 runs (including the baseline)

- The best is now Eval AUC **0.7364** at `2e3ccba`: 300 trees, depth 5, learning rate 0.1, numeric scheduled hour, and `reg_lambda=5`.
- Experiments 31–39 found no gain from alternate split/growth methods, leaf constraints or class weighting; the night, categorical-hour, two-hour-block, and weekend features tied or underperformed. Depth 6 was effectively tied but did not beat the simpler depth-5 model.
- **Current theory:** the structured signal in the basic schedule and airport/carrier categories is already captured reasonably well. A small increase from 240 to 300 rounds helped, so probe nearby capacity and a training-only schedule-density feature before stopping.

## Research before experiment 41

- Airport traffic-prediction research represents scheduled demand as the number of departures at each airport in a time interval ([Nationwide Airport Throughput Prediction](https://pmc.ncbi.nlm.nih.gov/articles/PMC9234322/)). This is an available-at-scheduling-time congestion proxy. Test a training-derived count of flights at the same origin on the same calendar day and two-hour window, using schedule columns only and no labels.

## Experiment 41 — `6193e0f`

- **Category:** exploration of an airport schedule-density feature.
- **Hypothesis:** more scheduled departures from the same origin around the flight's scheduled time may indicate congestion and improve delayed-flight ranking.
- **Change:** add `OriginPeriodCount`, the training-set count for `(Month, DayofMonth, Origin, two-hour departure block)`; keep all existing features and model parameters fixed.
- **Result:** Eval AUC **0.7369** (+0.0005), status **keep**. The schedule count helped; retain `6193e0f` as the new best.

## Research before experiment 42

- Airport throughput research represents scheduled demand at each airport in 15-minute intervals ([study](https://pmc.ncbi.nlm.nih.gov/articles/PMC9234322/)). The two-hour origin count helped in experiment 41; test a finer one-hour bin as a closer fit to short-term airport demand while keeping the same date/origin aggregation.

## Experiment 42 — `4df1261`

- **Category:** follow-up on schedule-density resolution.
- **Hypothesis:** a one-hour origin count may expose departure peaks that are diluted in two-hour blocks.
- **Change:** replace `OriginPeriodCount` with `OriginHourCount`, grouped by `(Month, DayofMonth, Origin, departure hour)`; hold all other features and model settings fixed.
- **Result:** Eval AUC **0.7349** (−0.0020 vs. the two-hour feature), status **discard**. One-hour counts were too specific; restore `6193e0f` with two-hour bins.

## Experiment 43 — `90b6fec`

- **Category:** follow-up tuning of boosting rounds with schedule density.
- **Hypothesis:** the origin count adds a useful split dimension, so 240 rounds may generalize better than the 300-round setting that won before the feature was added.
- **Change:** set `n_estimators=240`; keep `OriginPeriodCount` and every other feature/model parameter fixed.
- **Result:** Eval AUC **0.7363** (−0.0006), status **discard**. The lower round count came close but did not beat the 300-round schedule-density model; reset to `6193e0f`.

## Experiment 44 — `422d699`

- **Category:** continued local tuning of boosting rounds with schedule density.
- **Hypothesis:** 240 rounds trailed 300 by 0.0006; a modest increase to 360 tests whether the density feature benefits from continued boosting before the previously tested 480-round regime.
- **Change:** set `n_estimators=360`; keep `OriginPeriodCount` and all other features and parameters fixed.
- **Result:** Eval AUC **0.7368** (−0.0001), status **discard**. 360 rounds nearly tied but did not improve the best 300-round model; reset to `6193e0f`.

## Experiment 45 — `a8e2885`

- **Category:** alternate aggregation for origin schedule density.
- **Hypothesis:** an origin-by-two-hour count pooled across all dates may provide a more stable airport capacity/time-of-day interaction than the date-specific count.
- **Change:** replace `OriginPeriodCount` with `OriginTimeBlockCount`, the training-set frequency of `(Origin, two-hour departure block)` across dates; keep all other features and model settings fixed.
- **Result:** Eval AUC **0.7354** (−0.0015), status **discard**. Pooling across all dates lost useful variation; restore the date-specific two-hour count at `6193e0f`.

## Experiment 46 — `dcef069`

- **Category:** alternate temporal grouping for origin schedule density.
- **Hypothesis:** grouping by day of week instead of exact calendar date may retain recurring weekly schedule patterns while providing denser counts than date-specific groups.
- **Change:** replace `OriginPeriodCount` with the training-set frequency for `(DayOfWeek, Origin, two-hour departure block)`; preserve all other features and model settings.
- **Result:** Eval AUC **0.7341** (−0.0028), status **discard**. Weekday grouping was less useful than the date-specific count; restore `6193e0f`.

## Experiment 47 — `44a2211`

- **Category:** local refinement of boosting rounds with schedule density.
- **Hypothesis:** the 300-round count model beat both 240 and 360; 330 tests a closer midpoint in case slightly fewer trees preserve the gain while limiting overfit.
- **Change:** set `n_estimators=330`; keep `OriginPeriodCount` and all other features and parameters fixed.
- **Result:** Eval AUC **0.7369** (tie at reported precision), status **discard**. 330 rounds tied the best but adds no score gain; keep the simpler 300-round `6193e0f`.

## Experiment 48 — `26540ff`

- **Category:** follow-up regularization for schedule-density splits.
- **Hypothesis:** the date-specific count can create small groups; a modest `min_child_weight=2` may suppress weak splits while retaining useful congestion patterns. A stronger value of 5 hurt before the count feature was added.
- **Change:** set `min_child_weight=2`; keep all features and other model settings fixed.
- **Result:** Eval AUC **0.7374** (+0.0005), status **keep**. Light child-weight regularization improved the schedule-density model; retain `26540ff` as the new best.

## Experiment 49 — `1eff58b`

- **Category:** follow-up tuning of child-weight regularization.
- **Hypothesis:** `min_child_weight=2` improved AUC; testing 3 checks whether slightly stronger suppression of small leaves provides an additional gain.
- **Change:** set `min_child_weight=3`; keep the schedule-density feature and every other setting fixed.
- **Result:** Eval AUC **0.7366** (−0.0008), status **discard**. The lighter value 2 was better; reset to `26540ff`.

## Experiment 50 — `f72ab1e`

- **Category:** follow-up split regularization with schedule density.
- **Hypothesis:** `min_child_weight=2` improved the model; a very small `gamma=0.01` may complement it by removing only marginal splits.
- **Change:** set `gamma=0.01`; keep all other features and settings fixed.
- **Result:** Eval AUC **0.7374** (tie at reported precision), status **discard**. The split penalty added no gain over `26540ff`.

## Synthesis after 50 runs (including the baseline)

- Best is Eval AUC **0.7374** at `26540ff`: 300 trees, depth 5, learning rate 0.1, `min_child_weight=2`, `reg_lambda=5`, numeric scheduled hour, and a training-derived origin/date/two-hour departure count.
- The clearest feature gain came from origin schedule density (+0.0005 over the previous 300-round model); one-hour, weekday-only, and date-pooled alternatives underperformed. Light child-weight regularization added another +0.0005. 240/330/360 rounds and `gamma=0.01` tied or fell short.
- Earlier experiments found little benefit from cyclic or categorical time alternatives, route/carrier-hour combinations, class weighting, alternate boosters/tree methods, and higher histogram resolution.
- **Current theory:** same-origin schedule load for a specific date and time window captures congestion that the raw airport and time features miss; overly specific bins lose signal, while a small amount of leaf regularization helps. Next, test whether an airline's own scheduled activity adds a complementary operational signal.

## Research before experiment 51

- The Berkeley flight-delay project reports carrier-specific differences across departure hours and describes delays propagating through airline aircraft rotations ([project study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches)). As a schedule-only proxy for airline workload, test the number of same-carrier flights scheduled on the same date within the same two-hour block, using no target values.

## Experiment 51 — `ced2abf`

- **Category:** exploration of carrier schedule density.
- **Hypothesis:** carrier workload in a date/time window may complement origin congestion and explain operational strain shared across that airline's flights.
- **Change:** add training-derived `CarrierPeriodCount` for `(Month, DayofMonth, UniqueCarrier, two-hour departure block)`; preserve `OriginPeriodCount` and all other settings.
- **Result:** Eval AUC **0.7359** (−0.0015), status **discard**. Carrier activity did not add useful signal beyond origin density; reset to `26540ff`.

## Experiment 52 — `cc71ca4`

- **Category:** follow-up on temporal resolution for origin schedule density.
- **Hypothesis:** two-hour bins beat one-hour bins; a three-hour window may retain local schedule pressure while smoothing sparse airport/date groups.
- **Change:** replace `OriginPeriodCount` with `OriginThreeHourCount`, using `(Month, DayofMonth, Origin, three-hour departure block)`; hold all other settings fixed.
- **Result:** Eval AUC **0.7376** (+0.0002), status **keep**. Three-hour bins modestly improved the best; retain `cc71ca4`.

## Experiment 53 — `ea6b548`

- **Category:** follow-up on temporal resolution for origin schedule density.
- **Hypothesis:** three-hour bins improved over two-hour bins; test a broader four-hour window to see if further smoothing helps rare origin/date groups.
- **Change:** replace `OriginThreeHourCount` with an origin/date/four-hour count; keep all other features and model settings fixed.
- **Result:** Eval AUC **0.7376** (tie at reported precision), status **discard**. Four-hour bins tied the three-hour result without improving the score; restore `cc71ca4`.

## Experiment 54 — `f0729c1`

- **Category:** follow-up tuning of tree depth with schedule-density features.
- **Hypothesis:** the three-hour count and `min_child_weight=2` may support additional interactions; test depth 6 with the new feature set, which was not available in the earlier depth-6 trial.
- **Change:** set `max_depth=6`; keep the three-hour origin count and every other setting fixed.
- **Result:** Eval AUC **0.7372** (−0.0004), status **discard**. Depth 6 did not improve over depth 5; reset to `cc71ca4`.

## Experiment 55 — `d4c38bb`

- **Category:** follow-up child-weight tuning with three-hour density.
- **Hypothesis:** the three-hour count changed group frequency; test the default `min_child_weight=1` against the winning value 2 to check whether the finer density representation needs less regularization.
- **Change:** remove the explicit `min_child_weight=2` setting; keep all other features and settings fixed.
- **Result:** Eval AUC **0.7380** (+0.0004), status **keep**. The three-hour count performed best with default child weight; retain `d4c38bb`.

## Experiment 56 — `31ee1bc`

- **Category:** local boosting-round tuning with the new best features.
- **Hypothesis:** 330 rounds tied 300 when `min_child_weight=2`; check whether the default child weight now benefits from a small increase in rounds.
- **Change:** set `n_estimators=330`; keep all features, including the three-hour origin count, and other parameters fixed.
- **Result:** Eval AUC **0.7382** (+0.0002), status **keep**. Retain `31ee1bc` as the final best.

## Final summary

- Best Eval AUC: **0.7382**, commit `31ee1bc`.
- Best setup: XGBoost with 330 trees, depth 5, learning rate 0.1, L2 regularization 5, numeric scheduled hour, and a training-derived count of same-origin flights on the same date within a three-hour scheduled departure block. Default `min_child_weight` performed better than 2 with this representation.
- The strongest gains came from moderate tree capacity, scheduled hour, L2 regularization, origin schedule density, and tuning count resolution/leaf weight. The other tested time transforms, class weights, sparse interactions, alternate split/booster methods, and pooled/weekday/hourly counts did not beat the best.
- Further work could test leakage-safe historical delay rates or richer airport/aircraft rotation and weather data if available; those signals were not part of this feature set.
