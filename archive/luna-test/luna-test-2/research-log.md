# Experiment log — sep29

## Baseline — `c294417`

- Class: baseline
- Hypothesis: The untouched starter establishes the reference AUC and runtime.
- Result: Eval AUC `0.7203`; status `ok`; total runtime `31.6s` (`1.1s` training, `30.5s` evaluation).
- Observation: The baseline uses native categorical XGBoost with six categorical columns, two numeric columns, 30 trees, depth 6, and learning rate 0.1.

## Research checkpoint before experiment 1

The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes native categorical splitting, column/row subsampling, and the regularization knobs to explore. The [categorical-data tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) confirms that pandas categorical columns can be passed directly with `enable_categorical=True`. A flight-delay study using this dataset family identifies temporal, airline, origin, and destination variables as relevant predictors ([Springer study](https://link.springer.com/article/10.1007/s44196-025-00932-2)).

## Experiment 1 plan — explicit route category

- Class: exploration
- Hypothesis: An `Origin-Dest` categorical feature will let the trees learn route-specific delay propensity directly, instead of requiring repeated interactions between separate origin and destination splits. The route levels will be fitted once from `train` and only looked up in `prepare`, so the feature remains valid under row-by-row evaluation.

## Experiment 1 — `51cbf12`

- Result: Eval AUC `0.7071`; status `discard`; runtime `49.1s` (`1.3s` training, `47.8s` evaluation).
- Observation: The route feature increased the serialized artifact from `0.8 MB` to `6.9 MB` and sharply reduced AUC. The many route categories likely made the shallow 30-tree model brittle and also made row-wise preparation slower. Reverted to the baseline.

## Experiment 2 plan — scheduled departure hour

- Class: exploration
- Hypothesis: Adding `DepHour = CRSDepTime // 100` will expose the time-of-day effect with a clean numeric boundary, avoiding the uneven numeric spacing in HHMM values (for example, 09:59 to 10:00). This is a row-local transformation and therefore safe for row-by-row evaluation. The feature is motivated by the XGBoost parameter guidance on tree splits and flight-delay research identifying scheduled departure time as predictive.

## Experiment 2 — `8b59af5`

- Result: Eval AUC `0.7201`; status `discard`; runtime `34.1s` (`1.1s` training, `33.0s` evaluation).
- Observation: The explicit hour did not improve the baseline and slightly slowed row-wise evaluation. Keep the simpler raw HHMM representation for now.

## Experiment 3 plan — more boosting rounds

- Class: follow-up
- Hypothesis: The 30-tree baseline may be underfit. Increasing `n_estimators` to 100 at the same learning rate and depth should provide additional boosting corrections while leaving the feature representation unchanged. The XGBoost parameter reference describes learning-rate shrinkage as controlling each update, so tree count is the natural capacity counterpart to test.

## Experiment 3 — `c2e7ec8`

- Result: Eval AUC `0.7306`; status `keep`; runtime `31.9s` (`1.4s` training, `30.5s` evaluation).
- Observation: Extra boosting rounds improved AUC by `0.0103` with negligible wall-clock cost. The starter was materially underfit at 30 trees, so tree count is now the leading tuning direction.

## Experiment 4 plan — 200 boosting rounds

- Class: follow-up
- Hypothesis: If 100 rounds are still on the improving part of the boosting curve, 200 rounds at the same depth and learning rate may add useful ranking corrections. I will keep all other settings fixed to distinguish continued capacity from a new regularization regime.

## Experiment 4 — `71326e1`

- Result: Eval AUC `0.7345`; status `keep`; runtime `32.9s` (`2.0s` training, `30.9s` evaluation).
- Observation: A further `0.0039` AUC gain confirms that 100 trees had not saturated. Artifact size increased linearly but remains practical.

## Experiment 5 plan — 400 boosting rounds

- Class: follow-up
- Hypothesis: Continue the successful capacity sweep to 400 trees. This should reveal whether the current depth-6/learning-rate-0.1 configuration continues improving or begins to overfit on the held-out evaluation split.

## Experiment 5 — `916d5a3`

- Result: Eval AUC `0.7325`; status `discard`; runtime `34.0s` (`3.1s` training, `30.9s` evaluation).
- Observation: 400 trees overfit relative to the 200-tree keeper. The current best is 200 trees, depth 6, learning rate 0.1.

## Experiment 6 plan — shallower trees

- Class: follow-up
- Hypothesis: At the 200-tree sweet spot, reducing `max_depth` from 6 to 4 may reduce variance and improve generalization while retaining enough boosting rounds to model the categorical/time structure. All other settings remain at the current best.

## Experiment 6 — `597d027`

- Result: Eval AUC `0.7317`; status `discard`; runtime `32.2s` (`1.6s` training, `30.7s` evaluation).
- Observation: Depth 4 underfit relative to depth 6. The current best remains `n_estimators=200`, `max_depth=6`, `learning_rate=0.1`.

## Experiment 7 plan — deeper trees

- Class: follow-up
- Hypothesis: Test `max_depth=8` at the 200-tree budget to see whether the depth-6 keeper is capacity-limited in feature interactions. The 400-tree overfit result makes this a bounded test of interaction complexity rather than a general move toward larger models.

## Experiment 7 — `f09b5a8`

- Result: Eval AUC `0.7323`; status `discard`; runtime `33.6s` (`2.8s` training, `30.8s` evaluation).
- Observation: Depth 8 also lost to depth 6 and produced a much larger artifact. The useful complexity point is narrowly centered at depth 6 so far.

## Experiment 8 plan — lower learning rate with more rounds

- Class: follow-up
- Hypothesis: Use `learning_rate=0.05` and `n_estimators=400`. This keeps the approximate cumulative step size near the current 200×0.1 model but gives boosting twice as many smaller updates, which may improve ranking generalization. XGBoost documents learning rate as update shrinkage, so the two parameters should be evaluated together rather than interpreted independently.

## Experiment 8 — `c102f10`

- Result: Eval AUC `0.7354`; status `keep`; runtime `34.1s` (`3.1s` training, `31.0s` evaluation).
- Observation: The smaller-step, 400-round schedule improved the incumbent by `0.0009`. The best configuration now has depth 6, learning rate 0.05, and 400 trees.

## Experiment 9 plan — row subsampling

- Class: follow-up
- Hypothesis: Set `subsample=0.8` to decorrelate successive trees and reduce variance while preserving the current 400×0.05 boosting schedule. This is a single regularization change motivated by the XGBoost parameter documentation.

## Experiment 9 — `68be42c`

- Result: Eval AUC `0.7285`; status `discard`; runtime `33.7s` (`3.2s` training, `30.6s` evaluation).
- Observation: Row subsampling caused a large loss, so retain `subsample=1.0` (the default). The strong negative suggests the balanced training sample and available categorical signal benefit from every row.

## Experiment 10 plan — feature subsampling

- Class: exploration
- Hypothesis: Test `colsample_bytree=0.8` independently of row subsampling. With six categorical and two numeric inputs, modest feature subsampling may regularize redundant splits without discarding training rows. This completes the first 10-experiment block; after the run I will pause for a synthesis and new research before continuing.

## Experiment 10 — `1700ce8`

- Result: Eval AUC `0.7386`; status `keep`; runtime `34.1s` (`3.0s` training, `31.1s` evaluation).
- Observation: Feature subsampling improved the prior best by `0.0032`, while row subsampling had been strongly harmful. The current best is depth 6, 400 trees, learning rate 0.05, and `colsample_bytree=0.8`.

## Synthesis after 10 non-baseline experiments

- Feature additions were not useful in their first simple forms: an explicit high-cardinality route category fell to `0.7071`, and a derived departure hour was effectively neutral at `0.7201`. The raw starter representation is therefore retained.
- Capacity was the largest early lever: 30 → 100 → 200 trees moved AUC from `0.7203` to `0.7306` to `0.7345`; 400 trees at learning rate 0.1 overfit (`0.7325`). A slower 400×0.05 schedule recovered and slightly exceeded the 200×0.1 result (`0.7354`).
- Depth 6 was better than both depth 4 (`0.7317`) and depth 8 (`0.7323`) at the tested 200-tree setting. Row subsampling was harmful (`0.7285`), but column subsampling at 0.8 was beneficial (`0.7386`).
- Current theory: the dataset has strong signal in the original categorical fields, and the best gains come from carefully controlled boosting capacity and feature-level regularization rather than high-cardinality interactions or broad row randomization.
- Next direction: investigate native categorical split controls and leakage-safe train-fitted group statistics. These can add category structure while respecting the row-wise `prepare` contract, but need careful handling because counts and per-evaluation-frame aggregates are forbidden.

## Research checkpoint before experiment 11

The current XGBoost documentation says `max_cat_threshold` caps the number of categories considered in a partition split and is intended to prevent over-fitting; its categorical tutorial explains that optimal partitioning groups categories by their gradient-based leaf values ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html), [categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html)). The training data has 283 origin and destination levels, making this control relevant. Research on target encodings also emphasizes leakage and overfitting when target statistics are computed naïvely ([Springer discussion](https://link.springer.com/article/10.1007/s10618-024-01019-w)); I will not use a plain in-sample target mean.

## Experiment 11 plan — categorical partition cap

- Class: exploration
- Hypothesis: `max_cat_threshold=32` will regularize high-cardinality airport partitions while leaving the smaller calendar and carrier categories mostly unconstrained. This is a model-only change on top of the current `0.7386` keeper.

## Experiment 11 — `73a6d4c`

- Result: Eval AUC `0.7392`; status `keep`; runtime `33.5s` (`2.9s` training, `30.6s` evaluation).
- Observation: Limiting categorical partition candidates improved AUC by `0.0006` and reduced the artifact from `9.1 MB` to `8.2 MB`. This supports the hypothesis that unrestricted airport partitions were adding variance.

## Experiment 12 plan — tighter categorical cap

- Class: follow-up
- Hypothesis: Reduce `max_cat_threshold` from 32 to 16. If the gain is from suppressing noisy airport partitions, a tighter cap should help; if useful structure is being removed from 20-level carriers or 31-level day-of-month, AUC should retreat.

## Experiment 12 — `d897a2a`

- Result: Eval AUC `0.7407`; status `keep`; runtime `34.3s` (`3.7s` training, `30.6s` evaluation).
- Observation: The tighter cap added another `0.0015` AUC and reduced the artifact to `7.4 MB`. Continue cautiously with the same categorical-control axis.

## Experiment 13 plan — very tight categorical cap

- Class: follow-up
- Hypothesis: Test `max_cat_threshold=8`. This may further suppress high-cardinality airport noise, but it is a more aggressive change because even the 12-level month and 20-level carrier fields exceed the cap.

## Experiment 13 — `0c59717`

- Result: Eval AUC `0.7405`; status `discard`; runtime `33.0s` (`2.6s` training, `30.4s` evaluation).
- Observation: Threshold 8 was essentially tied but slightly below 16, so the current categorical sweet spot remains 16.

## Experiment 14 plan — intermediate categorical cap

- Class: follow-up
- Hypothesis: Test `max_cat_threshold=12` as an intermediate point between the best 16 and near-best 8. This is a focused refinement of the demonstrated categorical regularization effect.

## Experiment 14 — `56084b5`

- Result: Eval AUC `0.7407`; status `discard`; runtime `33.4s` (`2.7s` training, `30.7s` evaluation).
- Observation: Threshold 12 tied threshold 16 but added no simplicity or performance benefit, so retain the earlier threshold-16 commit.

## Experiment 15 plan — leaf minimum weight

- Class: exploration
- Hypothesis: Set `min_child_weight=5` to discourage low-support leaf splits that can overfit airport/category combinations. This applies regularization at the leaf level while holding the successful boosting schedule, feature subsampling, and categorical cap fixed.

## Experiment 15 — `72e1950`

- Result: Eval AUC `0.7405`; status `discard`; runtime `33.5s` (`2.8s` training, `30.7s` evaluation).
- Observation: Increasing the minimum child weight to 5 was slightly harmful. The default value 1 remains the current best leaf setting.

## Experiment 16 plan — mild leaf regularization

- Class: follow-up
- Hypothesis: Test `min_child_weight=2`, a smaller move from the default than 5. It may remove only the weakest splits while retaining the useful airport/category structure.

## Experiment 16 — `4754cf0`

- Result: Eval AUC `0.7411`; status `keep`; runtime `33.8s` (`2.8s` training, `31.0s` evaluation).
- Observation: Mild leaf regularization improved the incumbent by `0.0004`; stronger value 5 had been harmful. The current best uses `min_child_weight=2`.

## Experiment 17 plan — intermediate leaf constraint

- Class: follow-up
- Hypothesis: Test `min_child_weight=3` to see whether the small improvement continues smoothly or peaks at 2.

## Experiment 17 — `8ac7db0`

- Result: Eval AUC `0.7399`; status `discard`; runtime `33.7s` (`2.8s` training, `31.0s` evaluation).
- Observation: The gain did not extend to 3; keep `min_child_weight=2`.

## Experiment 18 plan — split-loss regularization

- Class: exploration
- Hypothesis: Add `gamma=0.1` so a split must provide a small minimum loss reduction. This complements, rather than duplicates, `min_child_weight`: it filters weak split gains even when a child has enough aggregate weight.

## Experiment 18 — `19181b1`

- Result: Eval AUC `0.7404`; status `discard`; runtime `34.2s` (`2.8s` training, `31.4s` evaluation).
- Observation: A small split-loss threshold was slightly harmful; retain the default `gamma=0`.

## Experiment 19 plan — L2 regularization

- Class: exploration
- Hypothesis: Increase `reg_lambda` from its default 1 to 2. This applies smooth weight shrinkage rather than suppressing splits, and may complement the successful `min_child_weight=2` without the categorical-cap regressions seen with stronger structural constraints.

## Experiment 19 — `e3f12ac`

- Result: Eval AUC `0.7413`; status `keep`; runtime `34.1s` (`3.3s` training, `30.9s` evaluation).
- Observation: Mild L2 shrinkage added `0.0002` over the prior best. The current best combines column subsampling, a categorical partition cap, mild leaf regularization, and modest L2 regularization.

## Synthesis after 20 total experiments

- Best so far: AUC `0.7413` at `e3f12ac`.
- The reliable improvements have come from model controls: more gradual boosting (400 trees at learning rate 0.05), `colsample_bytree=0.8`, `max_cat_threshold=16`, `min_child_weight=2`, and `reg_lambda=2`.
- The failed changes cluster around uncontrolled complexity or broad randomness: explicit route categories, extra hour feature, depth 4/8, 400 trees at learning rate 0.1, row subsampling, gamma, and strong leaf regularization. Threshold sweeps showed a useful but narrow categorical regularization effect: 32 → 16 helped, 8 regressed, and 12 tied.
- Current theory: native categorical airport splits contain signal but need constrained search; the model prefers full row coverage, moderate per-tree feature randomness, and gentle shrinkage. Further gains are more likely from leakage-safe group summaries or carefully tuned boosting schedules than from arbitrary new interactions.
- Next research direction: examine train-fitted group summaries that do not use row counts as features, and consider whether an early-stopping/validation strategy can select the boosting horizon without violating the harness’s final evaluation contract.

## Research checkpoint before experiment 20

The XGBoost callback documentation confirms that early stopping requires an explicit `eval_set` and that the estimator does not create a validation split automatically ([callbacks](https://xgboost.readthedocs.io/en/stable/python/callbacks.html), [scikit-learn interface](https://xgboost.readthedocs.io/en/release_2.0.0/python/sklearn_estimator.html)). The CatBoost paper explains why naïve target statistics leak the current label and motivates ordered statistics ([NeurIPS paper](https://papers.neurips.cc/paper/7898-catboost-unbiased-boosting-with-categorical-features.pdf)); this makes a careful target-encoding implementation a later, separate project. For the immediate run, I will stay with the validated XGBoost parameter family: the parameter reference describes `colsample_bytree` as per-tree feature sampling ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)).

## Experiment 20 plan — stronger feature subsampling

- Class: follow-up
- Hypothesis: Lower `colsample_bytree` from the successful 0.8 to 0.6. Since 0.8 improved the full-feature model by `0.0032`, a little more decorrelation may further reduce variance; if the signal is spread across the eight baseline columns, this will expose underfitting.

## Experiment 20 — `3539535`

- Result: Eval AUC `0.7413`; status `discard`; runtime `33.5s` (`2.7s` training, `30.7s` evaluation).
- Observation: Stronger feature subsampling tied the incumbent but brought no code simplification or score gain. Retain `colsample_bytree=0.8`.

## Experiment 21 plan — lighter feature subsampling

- Class: follow-up
- Hypothesis: Test `colsample_bytree=0.9` to see whether the 0.8 result is a broad plateau or a specific regularization sweet spot. This is the final bracket point before moving away from column sampling.

## Experiment 21 — `5274f5e`

- Result: Eval AUC `0.7398`; status `discard`; runtime `34.2s` (`3.7s` training, `30.5s` evaluation).
- Observation: Sampling only 10% of columns was too weakly regularized and lost `0.0015`. Keep `colsample_bytree=0.8`.

## Experiment 22 plan — slower boosting schedule

- Class: follow-up
- Hypothesis: Replace 400 trees at learning rate 0.05 with 600 trees at learning rate `0.033333`. The approximate cumulative step size stays near 20, but the smaller updates may refine ranking more smoothly under the current regularization.

## Experiment 22 — `11396e4`

- Result: Eval AUC `0.7413`; status `discard`; runtime `34.6s` (`3.7s` training, `30.9s` evaluation).
- Observation: The slower schedule tied the 400×0.05 keeper but increased model size and complexity, so retain the simpler 400-tree schedule.

## Experiment 23 plan — circular departure time

- Class: exploration
- Hypothesis: Add `sin(2π·minutes/1440)` and `cos(2π·minutes/1440)` from `CRSDepTime`. These row-local features encode smooth time-of-day periodicity and make 23:59 and 00:00 adjacent in feature space, unlike raw HHMM. The earlier plain hour feature was a different, non-circular representation.

## Experiment 23 — `0868296`

- Result: Eval AUC `0.7405`; status `discard`; runtime `39.0s` (`2.9s` training, `36.2s` evaluation).
- Observation: Circular time features did not help and made row-wise preparation slower. Retain the compact original feature set.

## Experiment 24 plan — finer numeric histograms

- Class: exploration
- Hypothesis: Set `max_bin=512` so XGBoost can consider finer thresholds for `CRSDepTime` and `Distance`. The current model has only two numeric columns, so the extra histogram resolution should be affordable and may recover useful splits lost at the default 256 bins.

## Experiment 24 — `4b9379c`

- Result: Eval AUC `0.7408`; status `discard`; runtime `33.3s` (`2.7s` training, `30.6s` evaluation).
- Observation: Finer numeric bins lost `0.0005`; the default 256-bin resolution remains preferable.

## Experiment 25 plan — coarser numeric histograms

- Class: follow-up
- Hypothesis: Test `max_bin=128` as the opposite regularization direction. If the numeric fields contain noisy fine-grained thresholds, coarser bins may improve generalization; otherwise the default should win.

## Experiment 25 — `5d41ea3`

- Result: Eval AUC `0.7404`; status `discard`; runtime `34.0s` (`3.6s` training, `30.4s` evaluation).
- Observation: Coarser histograms were also harmful. Retain XGBoost's default `max_bin=256`.

## Experiment 26 plan — L1 regularization

- Class: exploration
- Hypothesis: Add `reg_alpha=0.1` as a small L1 penalty on leaf weights. This may remove weak categorical effects that survive the current L2 and child-weight controls; all successful settings remain fixed.
- Research basis: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `reg_alpha` as L1 regularization on weights and notes that increasing it makes the model more conservative.

## Experiment 26 — `d80d03d`

- Result: Eval AUC `0.7410`; status `discard`; runtime `33.9s` (`2.8s` training, `31.1s` evaluation).
- Observation: L1 regularization at 0.1 slightly hurt, so the useful regularization remains predominantly L2/structural.

## Experiment 27 plan — very mild L1 regularization

- Class: follow-up
- Hypothesis: Test `reg_alpha=0.01` to distinguish an overly large L1 penalty from a generally unhelpful one. Keep `reg_lambda=2` and all other incumbent settings fixed.

## Experiment 27 — `c81053d`

- Result: Eval AUC `0.7403`; status `discard`; runtime `33.6s` (`2.7s` training, `30.9s` evaluation).
- Observation: Even very mild L1 regularization was negative. Keep the default `reg_alpha=0`.

## Experiment 28 plan — DART dropout booster

- Class: exploration
- Hypothesis: Try `booster="dart"` with `rate_drop=0.1` while preserving 400 trees, learning rate 0.05, and the current categorical/regularization settings. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes DART's tree-dropout controls; this may regularize successive corrections differently from row or column sampling.

## Experiment 28 — `623f4be`

- Result: Eval AUC `0.0000`; status `crash` (training timeout); runtime `60.0s` before the harness killed training.
- Observation: DART was far slower than the gbtree incumbent and exceeded the one-minute training limit. The run produced no evaluation score and was discarded.

## Experiment 29 plan — lossguide tree growth

- Class: exploration
- Hypothesis: Use `grow_policy="lossguide"`, `max_depth=0`, and `max_leaves=31` to grow the highest-loss-change nodes first rather than expanding depthwise. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) documents lossguide for `hist`; the leaf cap keeps this alternate topology within a comparable complexity budget.

## Experiment 29 — `a6f9f1f`

- Result: Eval AUC `0.7396`; status `discard`; runtime `34.2s` (`2.9s` training, `31.3s` evaluation).
- Observation: Loss-guided growth with 31 leaves underperformed depthwise growth by `0.0017`; its smaller artifact did not offset the score loss.

## Experiment 30 plan — larger lossguide budget

- Class: follow-up
- Hypothesis: Keep lossguide but raise `max_leaves` from 31 to 63, approximately matching the maximum leaves of a depth-6 depthwise tree. This tests whether the prior loss came from the growth policy or merely from under-capacity.

## Experiment 30 — `3589f1d`

- Result: Eval AUC `0.7435`; status `keep`; runtime `34.8s` (`3.9s` training, `30.9s` evaluation).
- Observation: Lossguide was capacity-sensitive: 31 leaves scored `0.7396`, while 63 leaves reached a new best `0.7435`. The alternate growth policy is now the leading direction. The current best uses explicit `tree_method="hist"`, `grow_policy="lossguide"`, `max_leaves=63`, 400 trees, learning rate 0.05, `colsample_bytree=0.8`, `max_cat_threshold=16`, `min_child_weight=2`, and `reg_lambda=2`.

## Synthesis after 30 non-baseline experiments

- The original depthwise model improved from `0.7203` to `0.7413` through 400×0.05 boosting, column subsampling, categorical partition caps, mild child-weight regularization, and L2 shrinkage. The new lossguide/63-leaf result adds another `0.0022`.
- Feature engineering remains difficult: route, hour, cyclic time, and route-like categorical additions did not help; the compact original eight-column input is still best.
- Regularization has a narrow optimum. `colsample_bytree=0.8`, `max_cat_threshold=16`, `min_child_weight=2`, and `reg_lambda=2` helped. Row subsampling, L1, gamma, extreme depth, extreme histogram bins, and DART either hurt or timed out.
- Growth topology now appears important: lossguide with too few leaves underfit, but a 63-leaf budget beat depthwise depth 6. The next tests should tune leaf capacity and the learning-rate/tree-count schedule around this model rather than return to discarded feature families.

## Research checkpoint before experiment 31

The XGBoost documentation defines `lossguide` as favoring the node with the highest loss change and exposes `max_leaves` as its complexity control ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)). The LightGBM tuning guide, which discusses the same leaf-wise strategy, warns that leaf-wise growth can overfit and recommends tuning the leaf count rather than assuming the depth-equivalent value is optimal ([leaf-wise tuning guide](https://github.com/lightgbm-org/LightGBM/blob/main/docs/Parameters-Tuning.rst)). This supports a local sweep around the successful 63 leaves.

## Experiment 31 plan — intermediate leaf budget

- Class: follow-up
- Hypothesis: Raise `max_leaves` from 63 to 95. The 31-leaf result underfit, so a moderate increase may capture additional high-loss interactions while avoiding the overfitting risk of an unrestricted leaf-wise tree.

## Experiment 31 — `efd27b2`

- Result: Eval AUC `0.7454`; status `keep`; runtime `35.8s` (`4.8s` training, `31.0s` evaluation).
- Observation: Increasing leaf capacity from 63 to 95 added `0.0019` AUC, so lossguide is still improving in this range. Artifact size rose to `15.9 MB` but remains within the harness limits.

## Experiment 32 plan — larger leaf budget

- Class: follow-up
- Hypothesis: Test `max_leaves=127`. If the 95-leaf gain reflects useful high-loss interactions rather than noise, another controlled increase should help; if not, the score should peak or regress.

## Experiment 32 — `caf5735`

- Result: Eval AUC `0.7457`; status `keep`; runtime `37.0s` (`5.9s` training, `31.1s` evaluation).
- Observation: 127 leaves added a smaller `0.0003` gain. The artifact grew to `21.3 MB`, but training remains well below the timeout.

## Experiment 33 plan — high leaf budget

- Class: follow-up
- Hypothesis: Test `max_leaves=191` once. This checks whether the shallow continuing trend persists; the result will determine whether further leaf growth is worth its increasing model size.

## Experiment 33 — `e6c3d09`

- Result: Eval AUC `0.7462`; status `keep`; runtime `38.1s` (`7.3s` training, `30.8s` evaluation).
- Observation: 191 leaves added `0.0005` and increased the artifact to `31.3 MB`. The leaf-cap curve is still rising, though gains are diminishing.

## Experiment 34 plan — 255 leaves

- Class: follow-up
- Hypothesis: Test `max_leaves=255` as the next power-of-two-scale budget. This is a final capacity probe before considering a lower learning rate or early-stopping-style selection; stop increasing if AUC turns down or training approaches the timeout.

## Experiment 34 — `2a2f11b`

- Result: Eval AUC `0.7471`; status `keep`; runtime `40.4s` (`9.2s` training, `31.2s` evaluation).
- Observation: 255 leaves added `0.0009`; the artifact is now `40.9 MB`, still practical. Capacity remains the strongest active direction.

## Experiment 35 plan — 511 leaves

- Class: follow-up
- Hypothesis: Test `max_leaves=511` to see whether the leaf-wise model can keep exploiting high-loss structure. The run remains under the one-minute training limit at the current observed scaling, but the larger artifact is a deliberate complexity tradeoff.

## Experiment 35 — `b972746`

- Result: Eval AUC `0.7465`; status `discard`; runtime `45.7s` (`14.1s` training, `31.6s` evaluation).
- Observation: 511 leaves overfit relative to 255 and expanded the artifact to `75.6 MB`. The useful leaf budget currently peaks at 255.

## Experiment 36 plan — regularize the 255-leaf model

- Class: follow-up
- Hypothesis: Increase `min_child_weight` from 2 to 3 while keeping 255 leaves. The prior depthwise test of 3 was negative, but the much more flexible lossguide trees may benefit from a slightly higher minimum child weight.

## Experiment 36 — `9a533a2`

- Result: Eval AUC `0.7469`; status `discard`; runtime `41.1s` (`9.9s` training, `31.2s` evaluation).
- Observation: Raising the child weight to 3 slightly reduced the 255-leaf score; keep 2.

## Experiment 37 plan — remove extra child regularization

- Class: follow-up
- Hypothesis: Test `min_child_weight=1` with 255 leaves. If the high-capacity model still benefits from smaller leaves, this may recover the lost `0.0002`; otherwise the current value 2 is the safer optimum.

## Experiment 37 — `06eccee`

- Result: Eval AUC `0.7474`; status `keep`; runtime `40.1s` (`8.8s` training, `31.3s` evaluation).
- Observation: Removing the extra child-weight constraint improved AUC by `0.0003`; the 255-leaf model now prefers the default minimum child weight 1.

## Experiment 38 plan — stronger L2 for high-capacity trees

- Class: follow-up
- Hypothesis: Raise `reg_lambda` from 2 to 3 while keeping `min_child_weight=1`. The 255-leaf model has more leaf weights to shrink, so a modestly stronger L2 penalty may improve generalization even though it was not yet tested in this topology.

## Experiment 38 — `2b37301`

- Result: Eval AUC `0.7478`; status `keep`; runtime `40.4s` (`9.2s` training, `31.2s` evaluation).
- Observation: L2 regularization continued to help after increasing leaf capacity, adding `0.0004`.

## Experiment 39 plan — continue L2 sweep

- Class: follow-up
- Hypothesis: Test `reg_lambda=4` with the same 255-leaf configuration. This is a final nearby point before the 40-experiment synthesis; a retreat will establish 3 as the local optimum.

## Experiment 39 — `e421b3c`

- Result: Eval AUC `0.7483`; status `keep`; runtime `40.4s` (`9.1s` training, `31.3s` evaluation).
- Observation: The L2 sweep continued upward: lambda 2 → 3 → 4 gave `0.7474` → `0.7478` → `0.7483` on the 255-leaf model.

## Synthesis after 40 total experiments

- Best so far: AUC `0.7483` at `e421b3c`, with 255-leaf lossguide trees, 400 rounds, learning rate 0.05, `colsample_bytree=0.8`, `max_cat_threshold=16`, `min_child_weight=1`, and `reg_lambda=4`.
- The largest gains came from switching growth topology and then increasing leaf capacity: depthwise best was `0.7413`; lossguide rose from `0.7396` at 31 leaves to `0.7483` at 255 leaves. The 511-leaf model overfit (`0.7465`), so capacity has a clear peak region.
- The high-capacity model prefers less child-weight regularization (1) but more L2 shrinkage (4), unlike the earlier depthwise configuration. This is consistent with many flexible leaf weights needing smooth shrinkage rather than hard split suppression.
- Feature engineering and target encodings remain unproven; simple route/time/cyclic additions were negative, and target statistics were intentionally deferred due leakage concerns. Future feature work should be justified by an ordered or otherwise valid construction.
- Next directions: refine the 255-leaf model’s L2/tree schedule, then consider leakage-safe group features or a carefully controlled train-only validation split for early stopping. Keep the training and evaluation time limits in view as artifacts grow.

## Research checkpoint before experiment 40

The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `reg_lambda` as L2 regularization on leaf weights, with larger values making the model more conservative. The official [Python introduction](https://xgboost.readthedocs.io/en/stable/python/python_intro.html) confirms that early stopping requires a validation set and should select the best iteration explicitly; I will defer that more invasive change while the direct L2 sweep is still improving.

## Experiment 40 plan — continue L2 sweep

- Class: follow-up
- Hypothesis: Increase `reg_lambda` from 4 to 5 with 255 lossguide leaves. The observed 2 → 3 → 4 improvement suggests the high-capacity model is still benefiting from smoother leaf weights.

## Experiment 40 — `6a744e6`

- Result: Eval AUC `0.7475`; status `discard`; runtime `40.3s` (`9.1s` training, `31.2s` evaluation).
- Observation: Lambda 5 over-regularized relative to the lambda-4 keeper. The L2 optimum is currently 4.

## Experiment 41 plan — slower high-capacity schedule

- Class: exploration
- Hypothesis: Use 500 trees at learning rate 0.04 instead of 400×0.05, keeping the approximate total step size near 20. The earlier slower schedule was neutral in depthwise trees, but the 255-leaf lossguide model has a different capacity/regularization balance.

## Experiment 41 — `05054a0`

- Result: Eval AUC `0.7485`; status `keep`; runtime `42.5s` (`11.1s` training, `31.3s` evaluation).
- Observation: The slower schedule improved the current best by `0.0002`; artifact size rose to `50.6 MB` but remains practical.

## Experiment 42 plan — still smaller updates

- Class: follow-up
- Hypothesis: Use 600 trees at learning rate `0.033333` with the same 255-leaf topology and lambda 4. This keeps the cumulative step size near 20 and tests whether the small gain from 500×0.04 continues.

## Experiment 42 — `21f2cad`

- Result: Eval AUC `0.7489`; status `keep`; runtime `44.4s` (`12.8s` training, `31.6s` evaluation).
- Observation: The slower schedule improved by another `0.0004`; artifact size is `59.8 MB`, still within practical limits.

## Experiment 43 plan — continue smaller updates

- Class: follow-up
- Hypothesis: Use 700 trees at learning rate `0.028571`, preserving the approximate cumulative step size near 20. This is the next point on the improving schedule; stop the sweep if the score turns down or training approaches the timeout.

## Experiment 43 — `ec9480a`

- Result: Eval AUC `0.7489`; status `discard`; runtime `47.1s` (`15.3s` training, `31.8s` evaluation).
- Observation: 700×0.028571 tied 600×0.033333 but enlarged the artifact to `69.8 MB`; retain the simpler 600-tree schedule.

## Experiment 44 plan — leakage-safe carrier target rate

- Class: exploration
- Hypothesis: Add a smoothed `UniqueCarrier` delay-rate feature. At training time, use leave-one-out target statistics so a row cannot see its own label; at evaluation time, use the train-fitted smoothed carrier rate. The [CatBoost paper](https://papers.neurips.cc/paper/7898-catboost-unbiased-boosting-with-categorical-features.pdf) identifies naïve target statistics as leakage and motivates this construction. Use a fixed smoothing prior (`alpha=20`) and do not expose group counts as features.

## Experiment 44 — `28f638e`

- Result: Eval AUC `0.6391`; status `discard`; runtime `40.0s` (`6.8s` training, `33.1s` evaluation).
- Observation: Even the leave-one-out/smoothed carrier rate badly damaged generalization. The model likely exploited a train/evaluation distribution mismatch in the target-derived feature, so target encoding is abandoned for this run.

## Experiment 45 plan — tighter cap with lossguide

- Class: follow-up
- Hypothesis: Set `max_cat_threshold=8` on the 255-leaf lossguide keeper. Threshold 8 was only slightly below 16 in the earlier depthwise sweep; with more flexible leafwise trees, the stronger airport regularization may now be beneficial.

## Experiment 45 — `8686d0b`

- Result: Eval AUC `0.7541`; status `keep`; runtime `44.4s` (`12.7s` training, `31.7s` evaluation).
- Observation: Tightening the categorical cap from 16 to 8 transformed the lossguide model, adding `0.0052` AUC. This is a strong interaction between categorical regularization and leaf-wise growth; the artifact is `65.5 MB` but still scores within the timeout.

## Experiment 46 plan — cap at 4

- Class: follow-up
- Hypothesis: Test `max_cat_threshold=4`, the smallest meaningful threshold above one-hot defaults. This may further suppress noisy airport partitions, though it also constrains all six categorical fields to at most four candidates per split.

## Experiment 46 — `2767866`

- Result: Eval AUC `0.7574`; status `keep`; runtime `45.0s` (`13.2s` training, `31.8s` evaluation).
- Observation: Threshold 4 improved another `0.0033`, confirming that the previous categorical partitions were highly overfit in the large lossguide model. Artifact size is `63.1 MB`.

## Experiment 47 plan — stricter categorical cap

- Class: follow-up
- Hypothesis: Test `max_cat_threshold=2` to see whether restricting each partition to only two candidate categories further improves generalization or begins to underfit. This is the last step in the cap sweep before tuning the now-promising model’s other parameters.

## Experiment 47 — `f64de56`

- Result: Eval AUC `0.7516`; status `discard`; runtime `43.3s` (`12.0s` training, `31.4s` evaluation).
- Observation: Threshold 2 underfit badly relative to threshold 4. Keep `max_cat_threshold=4`.

## Experiment 48 plan — more leaves under cap 4

- Class: follow-up
- Hypothesis: Raise `max_leaves` from 255 to 319 while retaining the successful cap-4 categorical regularization. The stricter cap may make extra leaf capacity safer by removing the noisiest category partitions.

## Experiment 48 — `ec35dd0`

- Result: Eval AUC `0.7578`; status `keep`; runtime `47.1s` (`15.1s` training, `32.0s` evaluation).
- Observation: 319 leaves added `0.0004`; artifact size is now `78.1 MB`, still completing within the evaluation limit.

## Experiment 49 plan — lower L2 under cap 4

- Class: follow-up
- Hypothesis: Reduce `reg_lambda` from 4 to 3 with the cap-4/319-leaf model. The stricter categorical cap may have removed enough variance that slightly less weight shrinkage can recover useful signal.

## Experiment 49 — `713ec40`

- Result: Eval AUC `0.7573`; status `discard`; runtime `47.4s` (`15.6s` training, `31.7s` evaluation).
- Observation: Lowering lambda under cap 4 lost `0.0005`; retain `reg_lambda=4`.

## Synthesis after 50 total experiments

- Best so far: AUC `0.7578` at `ec35dd0`, with 319 lossguide leaves, 600 trees, learning rate 0.033333, `colsample_bytree=0.8`, `max_cat_threshold=4`, `min_child_weight=1`, and `reg_lambda=4`.
- The major breakthrough was the interaction between leaf-wise growth and categorical partition regularization: cap 16/255 leaves scored `0.7489`, cap 8 scored `0.7541`, cap 4 scored `0.7574`, and adding leaves to 319 reached `0.7578`. Cap 2 underfit (`0.7516`).
- L2 remains important at high capacity: lambda 3 under cap 4/319 leaves fell to `0.7573`; lambda 4 is currently preferred. The leaf budget is still mildly improving from 255 to 319, but artifact size is now `78.1 MB` and training is `15.1s`, so future growth should be selective.
- Target-derived features were rejected after a carefully attempted leave-one-out/smoothed carrier rate collapsed to `0.6391`; the original categorical variables plus constrained partitions generalize much better.
- Next directions: tune the cap-4/319 model’s learning schedule and possibly test a small, safe input transformation only if it does not undermine the discovered categorical structure. Early stopping remains unattractive without a carefully chosen internal validation protocol and a full-data final model.

## Research checkpoint before experiment 50

The current XGBoost documentation describes `colsample_bylevel` as sampling columns for each tree level and states that `colsample_by*` controls multiply cumulatively ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)). Since `colsample_bytree=0.8` is already a keeper and the model now has many leaf-wise splits, per-level sampling is a focused, untested regularization direction.

## Experiment 50 plan — per-level feature sampling

- Class: exploration
- Hypothesis: Add `colsample_bylevel=0.8`, yielding moderate additional feature randomness after the successful per-tree 0.8 sampling. This may reduce repeated high-capacity interactions; if the eight original features are too sparse for the compounded sampling, AUC will fall.

## Experiment 50 — `b324f9b`

- Result: Eval AUC `0.7580`; status `keep`; runtime `45.8s` (`14.1s` training, `31.7s` evaluation).
- Observation: Per-level sampling added `0.0002`; artifact size is `77.3 MB`. The improvement is small but consistent with the high-capacity model benefiting from additional feature regularization.

## Experiment 51 plan — per-node feature sampling

- Class: follow-up
- Hypothesis: Add `colsample_bynode=0.8` on top of the 0.8 tree- and level-level controls. This compounds to roughly half the original feature set at each split; it may further suppress spurious interactions, but likely risks underfitting.

## Experiment 51 — `a7de024`

- Result: Eval AUC `0.7578`; status `discard`; runtime `45.3s` (`13.9s` training, `31.5s` evaluation).
- Observation: Per-node sampling at 0.8 over-regularized the model. Keep the tree+level sampling combination without node sampling.

## Experiment 52 plan — milder per-node sampling

- Class: follow-up
- Hypothesis: Test `colsample_bynode=0.9` with the current tree- and level-sampling values at 0.8. This retains most features per split and may recover the small loss from the 0.8 node setting.

## Experiment 52 — `2c4e950`

- Result: Eval AUC `0.7578`; status `discard`; runtime `46.6s` (`14.9s` training, `31.7s` evaluation).
- Observation: Even milder per-node sampling did not recover the score. Omit `colsample_bynode` entirely.

## Experiment 53 plan — milder per-level sampling

- Class: follow-up
- Hypothesis: Change `colsample_bylevel` from 0.8 to 0.9 while keeping `colsample_bytree=0.8`. If the 0.8 gain is robust, 0.9 may tie or improve with less compounded randomness.

## Experiment 53 — `3583f87`

- Result: Eval AUC `0.7583`; status `keep`; runtime `45.9s` (`14.0s` training, `31.9s` evaluation).
- Observation: Per-level sampling at 0.9 improved by `0.0003` over 0.8 and by `0.0005` over no per-level sampling. The artifact is `78.8 MB`.

## Experiment 54 plan — intermediate per-level sampling

- Class: follow-up
- Hypothesis: Test `colsample_bylevel=0.85` to refine the apparent 0.8–0.9 optimum without changing any other control.

## Experiment 54 — `5ccb4e8`

- Result: Eval AUC `0.7583`; status `discard`; runtime `45.7s` (`13.9s` training, `31.9s` evaluation).
- Observation: 0.85 tied 0.9 but did not simplify the model; retain the 0.9 keeper.

## Experiment 55 plan — near-full per-level sampling

- Class: follow-up
- Hypothesis: Test `colsample_bylevel=0.95`. This checks whether the optimum is broad near 0.9 or whether 0.9 is a narrow variance-control point.

## Experiment 55 — `4dc182b`

- Result: Eval AUC `0.7583`; status `discard`; runtime `46.3s` (`14.4s` training, `31.9s` evaluation).
- Observation: 0.95 tied 0.9, confirming a broad plateau; retain 0.9 as the simpler tested point.

## Experiment 56 plan — more features per tree

- Class: exploration
- Hypothesis: Raise `colsample_bytree` from 0.8 to 0.9 while retaining `colsample_bylevel=0.9`. This tests whether the per-level sampling already supplies enough regularization to recover signal from a broader per-tree feature set.

## Experiment 56 — `b0c0bbe`

- Result: Eval AUC `0.7581`; status `discard`; runtime `46.9s` (`15.3s` training, `31.6s` evaluation).
- Observation: More features per tree slightly reduced AUC; retain `colsample_bytree=0.8`.

## Experiment 57 plan — stronger per-tree sampling

- Class: follow-up
- Hypothesis: Lower `colsample_bytree` to 0.7 while retaining the successful `colsample_bylevel=0.9`. This may provide a little more variance control than 0.8 without the stronger underfitting seen at the earlier 0.6 baseline sweep.

## Experiment 57 — `1af7a1e`

- Result: Eval AUC `0.7569`; status `discard`; runtime `45.2s` (`13.5s` training, `31.7s` evaluation).
- Observation: More aggressive per-tree sampling was harmful; retain `colsample_bytree=0.8` with per-level 0.9.

## Experiment 58 plan — larger cap-4 leaf budget

- Class: follow-up
- Hypothesis: Raise `max_leaves` from 319 to 383 under the current cap-4/per-level-0.9 model. The earlier 255 → 319 gain suggests a little more leaf capacity may still help after categorical regularization.

## Experiment 58 — `d5271c4`

- Result: Eval AUC `0.7584`; status `keep`; runtime `48.4s` (`16.6s` training, `31.8s` evaluation).
- Observation: 383 leaves added `0.0001`; artifact size reached `94.0 MB`, still comfortably under the evaluation timeout.

## Experiment 59 plan — final capacity probe before synthesis

- Class: follow-up
- Hypothesis: Raise `max_leaves` to 447. The marginal 319 → 383 gain suggests a possible continuing curve, but this is the last larger-artifact test before the 60-run synthesis.

## Experiment 59 — `56e44b7`

- Result: Eval AUC `0.7588`; status `keep`; runtime `49.8s` (`17.8s` training, `32.0s` evaluation).
- Observation: 447 leaves added `0.0004`; artifact size is `109.6 MB`, and the run remains comfortably below both harness limits.

## Synthesis after 60 total experiments

- Best so far: AUC `0.7588` at `56e44b7`: 447 lossguide leaves, 600 trees, learning rate 0.033333, `colsample_bytree=0.8`, `colsample_bylevel=0.9`, `max_cat_threshold=4`, `min_child_weight=1`, and `reg_lambda=4`.
- The strongest generalization gains came from constraining categorical partitions in the leaf-wise model: cap 16 → 8 → 4 rose from `0.7489` to `0.7541` to `0.7574`, and leaf capacity then rose steadily to `0.7588` at 447 leaves. Cap 2 underfit.
- Additional per-level column sampling at 0.9 added another `0.0005` over the cap-4/319 base. Per-node sampling was harmful or neutral; per-tree 0.7 and 0.9 were worse than 0.8.
- The model is now large but still operational: 109.6 MB artifact, 17.8s training, about 32s evaluation. Further improvements should be small and must be weighed against size/complexity.
- Failed avenues remain clear: naïve/leave-one-out target rate features, explicit route/time/cyclic features, row subsampling, DART, depthwise growth, and aggressive L1/gamma controls. The safest next work is a narrow schedule or leaf-cap refinement, not more target-derived features.

## Research checkpoint before experiment 60

The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says `max_cat_threshold` is used in partition-based splits to prevent over-fitting. The official [interaction-constraints tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html) notes that constraints can improve generalization by excluding spurious interactions, but hand-specifying groups would be a larger assumption than the current evidence supports. I will first test the untried intermediate categorical cap of 3.

## Experiment 60 plan — intermediate cap

- Class: follow-up
- Hypothesis: Change `max_cat_threshold` from 4 to 3 on the 447-leaf/per-level-0.9 keeper. Threshold 2 underfit sharply, so 3 may preserve more than 2 while still improving over 4 if the cap curve is smooth.

## Experiment 60 — `6046cbb`

- Result: Eval AUC `0.7589`; status `keep`; runtime `49.7s` (`17.2s` training, `32.5s` evaluation).
- Observation: Cap 3 narrowly improved cap 4 by `0.0001`; artifact size fell to `96.7 MB`. The best categorical cap is currently 3.

## Experiment 61 plan — larger cap-3 leaf budget

- Class: follow-up
- Hypothesis: Raise `max_leaves` from 447 to 511 under cap 3. The stronger categorical regularization may support additional leaf capacity without repeating the cap-16 overfit seen at 511.

## Experiment 61 — `6e075bd`

- Result: Eval AUC `0.7590`; status `keep`; runtime `52.1s` (`20.2s` training, `31.9s` evaluation).
- Observation: Cap-3 leaf growth remained positive at 511 leaves, adding `0.0001`; artifact size is `110.9 MB`.

## Experiment 62 plan — final leaf-cap extension

- Class: follow-up
- Hypothesis: Test `max_leaves=575` under cap 3. This is a modest extension beyond 511; stop the capacity sweep if the score turns down or the artifact/training cost becomes disproportionate.

## Experiment 62 — `12bf0d9`

- Result: Eval AUC `0.7598`; status `keep`; runtime `52.6s` (`20.5s` training, `32.0s` evaluation).
- Observation: 575 leaves added `0.0008`; artifact size is `122.7 MB`. The cap-3 capacity curve remains worthwhile.

## Experiment 63 plan — next cap-3 leaf budget

- Class: follow-up
- Hypothesis: Test `max_leaves=639` as the next moderate extension. Continue only while AUC improves without approaching the harness limits.

## Experiment 63 — `ad275e9`

- Result: Eval AUC `0.7588`; status `discard`; runtime `54.5s` (`22.5s` training, `32.0s` evaluation).
- Observation: 639 leaves overfit relative to 575 and increased the artifact to `135.2 MB`. Keep 575 as the leaf-cap peak.

## Experiment 64 plan — slower 575-leaf schedule

- Class: exploration
- Hypothesis: Change 600 trees at learning rate 0.033333 to 700 trees at 0.028571 while keeping 575 cap-3 leaves. The earlier 700-tree schedule tied at lower capacity, but the stronger cap and larger leaves may benefit from smaller updates.

## Experiment 64 — `5e9808b`

- Result: Eval AUC `0.7599`; status `keep`; runtime `57.8s` (`25.4s` training, `32.4s` evaluation).
- Observation: The slower schedule added `0.0001`; artifact size is `143.0 MB`. It remains just inside the per-run limits.

## Experiment 65 plan — final schedule extension

- Class: follow-up
- Hypothesis: Test 800 trees at learning rate `0.025`, preserving the approximate cumulative step size near 20. This is the last schedule extension unless it gives a clear gain; the model is nearing the practical size/runtime boundary.

## Experiment 65 — `ee0ba64`

- Result: Eval AUC `0.7596`; status `discard`; runtime `60.6s` (`27.5s` training, `33.1s` evaluation).
- Observation: The 800-tree schedule overfit relative to 700 and grew the artifact to `165.6 MB`. Keep the 700×0.028571 schedule.

## Experiment 66 plan — stronger L2 at high capacity

- Class: exploration
- Hypothesis: Increase `reg_lambda` from 4 to 5 on the 575-leaf/cap-3/700-tree model. The larger model may need additional smooth shrinkage even though lambda 5 was negative at lower capacity.

## Experiment 66 — `f75773b`

- Result: Eval AUC `0.7598`; status `discard`; runtime `57.2s` (`24.5s` training, `32.7s` evaluation).
- Observation: Lambda 5 was slightly worse than 4 at the current capacity; restore lambda 4.

## Experiment 67 plan — weighted feature sampling

- Class: exploration
- Hypothesis: Pass `feature_weights=[0.5, 0.5, 1, 1, 1, 1, 1, 1]` to `XGBClassifier.fit`, making the six categorical columns twice as likely as each numeric column to survive the existing column subsampling. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) documents feature weights for column sampling; this tests whether the discovered categorical signal benefits from explicit sampling priority.

## Experiment 67 — `a01d410`

- Result: Eval AUC `0.7607`; status `keep`; runtime `58.3s` (`25.5s` training, `32.8s` evaluation).
- Observation: Giving categorical features twice the sampling weight improved the best score by `0.0008`. The artifact is `153.9 MB`; the run remains within the limits, though the training margin is narrowing.

## Experiment 68 plan — stronger categorical sampling priority

- Class: follow-up
- Hypothesis: Change numeric feature weights from 0.5 to 0.25, making categorical features four times as likely to be sampled. If the improvement comes from preserving categorical signal under column sampling, this may add another small gain; otherwise it will over-focus on categories.

## Experiment 68 — `044cc63`

- Result: Eval AUC `0.7614`; status `keep`; runtime `60.0s` (`26.9s` training, `33.1s` evaluation).
- Observation: Four-times categorical sampling priority added `0.0007`, continuing the monotone feature-weight trend. Artifact size is `165.4 MB`; this is near the practical runtime boundary.

## Experiment 69 plan — strongest categorical sampling priority

- Class: follow-up
- Hypothesis: Set numeric feature weights to 0.125 (8:1 categorical priority). This is the final sampling-weight probe; stop if it fails to improve because the current model is already at the one-minute run boundary.

## Experiment 69 — `ce8a2b6`

- Result: Eval AUC `0.7605`; status `discard`; runtime `60.8s` (`28.0s` training, `32.8s` evaluation).
- Observation: 8:1 categorical priority over-focused on categorical columns and lost `0.0009`; retain the 4:1 setting.

## Experiment 70 plan — intermediate feature weights

- Class: follow-up
- Hypothesis: Test numeric feature weights of 0.2 (5:1 categorical priority), between the successful 4:1 and failed 8:1 settings. This is the last narrow sampling-weight refinement before wrap-up.

## Experiment 70 — `d134084`

- Result: Eval AUC `0.7610`; status `discard`; runtime `60.6s` (`28.2s` training, `32.3s` evaluation).
- Observation: The 5:1 ratio was below the 4:1 keeper; retain numeric weight 0.25.

## Experiment 71 plan — local interpolation

- Class: follow-up
- Hypothesis: Test numeric weight 0.3 (about 3.3:1 categorical priority), interpolating between the successful 0.25 and neutral 0.5 settings. This is the final experiment in this feature-weight sweep.

## Experiment 71 — `8de1be6`

- Result: Eval AUC `0.7614`; status `discard`; runtime `59.7s` (`27.1s` training, `32.5s` evaluation).
- Observation: The 3.33:1 ratio tied the 4:1 keeper without simplifying the model. Retain numeric feature weight 0.25.

## Final summary

- Best result: Eval AUC `0.7614`, retained at commit `044cc63`.
- Final model: categorical histogram XGBoost with lossguide growth, `575` leaves, `700` trees at learning rate `0.028571`, `max_cat_threshold=3`, `min_child_weight=1`, `reg_lambda=4`, `colsample_bytree=0.8`, and `colsample_bylevel=0.9`.
- The strongest improvement came from progressively tuning categorical handling and tree capacity. Giving categorical columns four times the feature-sampling weight of the numeric columns produced the final gain; stronger weighting and nearby interpolation did not improve it.
- Discarded directions included route/time feature additions, leakage-prone target-rate encoding, DART, depthwise alternatives, overly large categorical thresholds, and more aggressive categorical weighting. The DART trial timed out and was recorded as a crash.
- The branch is left at the best keeper. `results.tsv`, this research log, run output, and timing data remain available as the experiment record.
