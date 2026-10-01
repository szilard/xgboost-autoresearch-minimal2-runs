# Research log

## Baseline — `92e43e6`

- **Hypothesis:** Establish the starter model's Eval AUC before changing any training or feature code.
- **Change:** None. Ran the existing `train.py` as the required baseline (`XGBClassifier`, 30 trees, depth 6, learning rate 0.1; categorical features enabled).
- **Result:** Eval AUC `0.7203`; run completed successfully in 31.4 seconds (1.1 seconds training, 30.4 seconds evaluation).
- **Decision:** Keep as the reference point for subsequent experiments.
## Experiment 1 — scheduled departure time encoding (`e25ad0c`)

- **Class:** Exploration.
- **Hypothesis:** The raw `CRSDepTime` integer uses HHMM notation, whose numeric gaps do not match elapsed minutes and whose midnight boundary is discontinuous. Adding minutes since midnight and sine/cosine encodings may expose smoother daily delay patterns while retaining the original value.
- **Research:** A flight-delay study examines scheduled departure time alongside airline and airport ([arXiv:2408.02802](https://arxiv.org/abs/2408.02802)). XGBoost's tuning notes recommend letting task knowledge guide preprocessing ([parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- **Change:** Added minutes since midnight and sine/cosine time-of-day columns in `prepare`, retaining the original `CRSDepTime` feature.
- **Result:** Eval AUC `0.7195` (35.1 seconds; status `ok`), a decrease of `0.0008` from baseline.
- **Decision:** Discard and return to baseline; the extra time encodings did not help this model.
## Experiment 2 — origin-destination category (`74791e4`)

- **Class:** Exploration.
- **Hypothesis:** Delay patterns may differ for specific directional airport pairs. A combined route category can expose an origin-destination interaction directly, instead of asking shallow trees to reconstruct it from separate airport categories.
- **Research:** A 2025 flight-delay study includes origin-destination pairs in its input data ([Springer article](https://link.springer.com/article/10.1007/s44196-025-00932-2)). XGBoost documents native categorical splits using one-hot or partition-based splitting ([categorical data guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html)).
- **Change:** Added a categorical route key using `Origin` and `Dest`, with category levels fit once from training data.
- **Result:** Eval AUC `0.7071` (49.2 seconds; status `ok`), down `0.0132` from baseline. Artifact size rose from 0.8 MB to 6.9 MB.
- **Decision:** Discard. The high-cardinality route representation hurt AUC and increased artifact size substantially.
## Experiment 3 — more boosting rounds (`e6cf329`)

- **Class:** Follow-up to the baseline.
- **Hypothesis:** Thirty boosting rounds may underfit 200K training examples. Raising only `n_estimators` to 100 may improve ranking by fitting more residual structure while keeping feature representation, depth, and learning rate fixed.
- **Research:** XGBoost's parameter-tuning notes describe the bias-variance tradeoff behind model complexity and boosting settings ([parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- **Change:** Increased `n_estimators` from 30 to 100, holding other model settings and features fixed.
- **Result:** Eval AUC `0.7306` (32.1 seconds; status `ok`), up `0.0103` from baseline.
- **Decision:** Keep; this is the current best.
## Experiment 4 — extend boosting to 200 rounds (`edd60ad`)

- **Class:** Follow-up to the promising 100-tree result.
- **Hypothesis:** The gain from 30 to 100 trees suggests more rounds may capture useful residual structure. Doubling to 200 tests whether that trend continues or eval performance starts to decline.
- **Research:** This continues the XGBoost model-complexity tuning direction motivated by the [official parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html).
- **Change:** Increased `n_estimators` from 100 to 200, holding all other settings fixed.
- **Result:** Eval AUC `0.7345` (32.6 seconds; status `ok`), up `0.0039` from the 100-tree run and `0.0142` from baseline.
- **Decision:** Keep; AUC continued to improve with more rounds.
## Experiment 5 — extend boosting to 400 rounds (`40794f6`)

- **Class:** Follow-up to the improving 100- and 200-tree results.
- **Hypothesis:** The 100-to-200 increase still improved AUC, so 400 trees may add further useful residual fits, though the gain may be smaller as performance approaches a plateau.
- **Research:** This continues the model-complexity tuning direction guided by the [XGBoost parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html).
- **Change:** Increased `n_estimators` from 200 to 400, holding all other settings fixed.
- **Result:** Eval AUC `0.7325` (33.7 seconds; status `ok`), down `0.0020` from the 200-tree best. Training remained fast at 3.1 seconds.
- **Decision:** Discard; restore the 200-tree model as current best.
## Experiment 6 — smaller steps with 400 rounds (`56b0e18`)

- **Class:** Follow-up to the 200-tree best and the weaker 400-tree result.
- **Hypothesis:** Four hundred rounds at learning rate `0.1` reduced Eval AUC. Pairing 400 rounds with a smaller `0.05` learning rate may make the longer sequence of updates more gradual and improve generalization.
- **Research:** XGBoost's [parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) specifically recommend increasing boosting rounds when reducing `eta`.
- **Change:** Set `n_estimators=400` and reduced `learning_rate` from `0.1` to `0.05`.
- **Result:** Eval AUC `0.7354` (33.6 seconds; status `ok`), up `0.0009` from the previous best.
- **Decision:** Keep as the new best.
## Experiment 7 — finer steps with 800 rounds (`b93416e`)

- **Class:** Follow-up to the 400-tree, `0.05` result.
- **Hypothesis:** Halving the learning rate again to `0.025` while doubling to 800 rounds may produce a smoother fit and improve on the current best; the previous 400-tree run improved slightly over 200 trees.
- **Research:** This follows the guidance in the [XGBoost parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) to pair smaller learning rates with more boosting rounds.
- **Change:** Set `n_estimators=800` and reduced `learning_rate` from `0.05` to `0.025`.
- **Result:** Eval AUC `0.7349` (36.3 seconds; status `ok`), down `0.0005` from the 400-tree/`0.05` best. Artifact size doubled to 20.1 MB.
- **Decision:** Discard; the added trees and artifact size did not improve AUC.
## Experiment 8 — shallower trees (`35f9b34`)

- **Class:** Follow-up to the 400-tree, `0.05` best.
- **Hypothesis:** With 400 boosting rounds, depth-6 trees may be more complex than needed. Reducing only `max_depth` to 4 may regularize the ensemble and improve Eval AUC.
- **Research:** XGBoost's [parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) identify `max_depth` as a direct model-complexity control.
- **Change:** Reduced `max_depth` from 6 to 4 with 400 trees and learning rate `0.05`.
- **Result:** Eval AUC `0.7326` (32.8 seconds; status `ok`), down `0.0028` from the current best.
- **Decision:** Discard; keep depth 6.
## Experiment 9 — row subsampling (`4533c8e`)

- **Class:** Follow-up to the 400-tree, `0.05` best.
- **Hypothesis:** The depth-4 model lost AUC, but row subsampling can add training randomness without reducing tree depth. Setting `subsample=0.8` may improve generalization while retaining the useful depth-6 interactions.
- **Research:** XGBoost's [parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) describe `subsample` as a way to add randomness and improve robustness.
- **Change:** Set `subsample=0.8` with the 400-tree/`0.05` configuration.
- **Result:** Eval AUC `0.7285` (33.9 seconds; status `ok`), down `0.0069` from the current best.
- **Decision:** Discard; retain the full-data fit.
## Synthesis after 10 experiments

- **Best so far:** Commit `56b0e18`, Eval AUC `0.7354` (`n_estimators=400`, `learning_rate=0.05`, depth 6), up `0.0151` over the baseline.
- **What helped:** Increasing rounds from 30 to 100 and then 200 raised AUC substantially. Pairing 400 rounds with a smaller `0.05` learning rate added a smaller gain.
- **What did not help:** Raw-time cyclic/minute features were slightly worse. The high-cardinality route category sharply reduced AUC and enlarged the artifact. At the current best settings, 400 trees at `0.1`, 800 at `0.025`, depth 4, and row subsampling all scored below the best.
- **Current theory / next direction:** The starter features are useful, but 30 trees underfit. A 400-round, moderately smaller learning rate improves AUC; much smaller steps and extra rounds add cost without gain. Keep the baseline feature representation and explore regularization controls such as `min_child_weight` or `colsample_bytree` to improve the current ensemble.
## Experiment 11 — minimum child weight (`e9148ab`)

- **Class:** Follow-up to the depth-6, 400-tree best.
- **Hypothesis:** Reducing depth to 4 hurt AUC, so keep depth 6 but prevent low-support child splits. Setting `min_child_weight=5` may regularize less bluntly than reducing depth.
- **Research:** The [official XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) define `min_child_weight` as the minimum instance-weight sum required in a child; larger values make the model more conservative.
- **Change:** Set `min_child_weight=5` with the 400-tree/`0.05` best configuration.
- **Result:** Eval AUC `0.7346` (33.9 seconds; status `ok`), down `0.0008` from the current best.
- **Decision:** Discard; retain the default value of 1.
## Experiment 12 — mild child-weight increase (`ad5be21`)

- **Class:** Follow-up to the child-weight-5 result.
- **Hypothesis:** The value 5 reduced AUC slightly. A smaller increase to `min_child_weight=2` may preserve useful splits while suppressing only the weakest children.
- **Research:** This narrows the regularization setting using the [official XGBoost definition](https://xgboost.readthedocs.io/en/stable/parameter.html) of the child-weight threshold.
- **Change:** Set `min_child_weight=2` with the 400-tree/`0.05` configuration.
- **Result:** Eval AUC `0.7354` (34.1 seconds; status `ok`), equal to the current best at the reported precision.
- **Decision:** Discard under the keep rule because it added a parameter without improving or simplifying the model.
## Experiment 13 — per-tree feature sampling (`1d7cf8f`)

- **Class:** Follow-up to the best full-data fit.
- **Hypothesis:** Row subsampling hurt, but feature sampling may still add useful tree diversity. With eight starter columns, `colsample_bytree=0.8` should leave each tree access to most of the available predictors while varying the subset.
- **Research:** The [official XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) define `colsample_bytree` as the fraction of columns sampled for each tree.
- **Change:** Set `colsample_bytree=0.8` with 400 trees at learning rate `0.05`.
- **Result:** Eval AUC `0.7386` (34.0 seconds; status `ok`), up `0.0032` from the previous best. Artifact size decreased from 10.0 MB to 9.1 MB.
- **Decision:** Keep as the new best; feature sampling improved AUC and reduced artifact size.
## Experiment 14 — stronger per-tree feature sampling (`e02eab6`)

- **Class:** Follow-up to the `colsample_bytree=0.8` gain.
- **Hypothesis:** Sampling 60% of columns per tree may add more useful diversity than 80% while still retaining several predictors per tree. It could also omit important inputs too often, so compare directly against the 0.8 result.
- **Research:** The [official XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) define per-tree column sampling as a feature fraction in `(0, 1]`.
- **Change:** Reduced `colsample_bytree` from 0.8 to 0.6.
- **Result:** Eval AUC `0.7423` (33.8 seconds; status `ok`), up `0.0037` from the 0.8 result. Artifact size decreased from 9.1 MB to 8.1 MB.
- **Decision:** Keep as the new best.
## Experiment 15 — stronger per-tree feature sampling (`e326d39`)

- **Class:** Follow-up to the `colsample_bytree=0.6` gain.
- **Hypothesis:** Reducing the fraction to 0.4 will make trees more diverse, but may leave too few of the eight predictors available. Test whether the gains continue or reverse.
- **Research:** This continues the focused comparison of the per-tree sampling fraction described in the [official XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html).
- **Change:** Reduced `colsample_bytree` from 0.6 to 0.4.
- **Result:** Eval AUC `0.7424` (33.7 seconds; status `ok`), a `0.0001` increase over the 0.6 result. Artifact size fell from 8.1 MB to 7.2 MB.
- **Decision:** Keep as a small improvement and the new best.
## Experiment 16 — test a 0.3 column fraction (`f3ca7c3`)

- **Class:** Follow-up to the `colsample_bytree=0.4` result.
- **Hypothesis:** A 0.3 fraction may add further diversity, but with only eight features it can limit a tree's ability to learn interactions. Compare against the 0.4 best.
- **Research:** This continues the per-tree feature-fraction comparison from the [official parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html).
- **Change:** Reduced `colsample_bytree` from 0.4 to 0.3.
- **Result:** Eval AUC `0.7334` (33.5 seconds; status `ok`), down `0.0090` from the 0.4 best.
- **Decision:** Discard; 0.3 sampled too few features for the model.
## Experiment 17 — midpoint column fraction (`dea6053`)

- **Class:** Follow-up to the 0.4 and 0.6 column-sampling results.
- **Hypothesis:** Those settings were nearly tied, while 0.3 dropped sharply. Testing `colsample_bytree=0.5` brackets the narrow region around the current best.
- **Research:** This continues the parameter sweep for the per-tree column fraction defined in the [official XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html).
- **Change:** Set `colsample_bytree=0.5`.
- **Result:** Eval AUC `0.7423` (33.8 seconds; status `ok`), `0.0001` below the 0.4 best and equal to the 0.6 result at the reported precision.
- **Decision:** Discard; retain 0.4.
## Experiment 18 — depth 5 with feature sampling (`4eb11a2`)

- **Class:** Follow-up to the best `colsample_bytree=0.4` model.
- **Hypothesis:** Depth 4 hurt when all features were available, but depth 5 may be a less severe complexity reduction when each tree already sees only 40% of features. Test whether this combination preserves interactions and improves generalization.
- **Research:** XGBoost's [parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) frame `max_depth` as a direct bias-variance control.
- **Change:** Reduced `max_depth` from 6 to 5, retaining `colsample_bytree=0.4`.
- **Result:** Eval AUC `0.7374` (33.5 seconds; status `ok`), down `0.0050` from the current best. Artifact size decreased, but the AUC loss was material.
- **Decision:** Discard; retain depth 6.
## Experiment 19 — minimum split-loss threshold (`2f64036`)

- **Class:** Follow-up to the best `colsample_bytree=0.4` model.
- **Hypothesis:** Depth and child-weight regularization both reduced AUC. A small `gamma=0.1` may selectively block low-benefit splits without limiting useful depth-6 interactions.
- **Research:** The [official XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) define `gamma` as the minimum loss reduction required for a split.
- **Change:** Set `gamma=0.1` with 400 trees, learning rate `0.05`, depth 6, and column fraction 0.4.
- **Result:** Eval AUC `0.7425` (33.8 seconds; status `ok`), up `0.0001` from the previous best.
- **Decision:** Keep as the new best at the reported precision.
## Experiment 20 — stronger split-loss threshold (`1c76f62`)

- **Class:** Follow-up to the `gamma=0.1` gain.
- **Hypothesis:** A higher `gamma=0.5` may remove more low-value splits, but could also suppress useful interactions. Compare against the small positive change at 0.1.
- **Research:** This adjusts the minimum loss-reduction threshold described in the [official XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html).
- **Change:** Increased `gamma` from 0.1 to 0.5.
- **Result:** Eval AUC `0.7411` (33.7 seconds; status `ok`), down `0.0014` from the gamma-0.1 best.
- **Decision:** Discard; restore `gamma=0.1`.
## Synthesis after 20 experiments

- **Best so far:** Commit `2f64036`, Eval AUC `0.7425` (`n_estimators=400`, `learning_rate=0.05`, depth 6, `colsample_bytree=0.4`, `gamma=0.1`), up `0.0222` over baseline.
- **What helped:** Boosting from 30 to 200 rounds gave the largest gains. A smaller learning rate at 400 rounds improved further. Per-tree feature sampling was the strongest later change: 0.8, 0.6, and 0.4 improved in sequence; 0.3 lost sharply. A small `gamma=0.1` added a marginal gain.
- **What did not help:** The departure-time encodings and high-cardinality route category hurt. Row subsampling, stronger child-weight regularization, shallower trees, 800 very small steps, and `gamma=0.5` did not beat the best.
- **Current theory / next direction:** Random feature subsets help more than row sampling on these eight predictors, and depth-6 interactions remain useful. Keep `colsample_bytree=0.4` and mild split pruning while exploring a distinct representation of time or a different per-node feature-sampling strategy.
## Experiment 21 — categorical departure hour (`003959b`)

- **Class:** Exploration.
- **Hypothesis:** The earlier cyclic minute features did not help, but an hour category makes a different assumption: departure risk may vary sharply and non-monotonically across daily operating periods. Keep raw HHMM and add hour-of-day as a separate category.
- **Research:** A recent departure-delay study includes departure hour among its traditional predictor features ([arXiv:2512.08197](https://arxiv.org/abs/2512.08197)).
- **Change:** Added departure hour as a categorical feature, with levels derived once from the training data.
- **Result:** Eval AUC `0.7406` (39.5 seconds; status `ok`), down `0.0019` from the best. Row-by-row evaluation rose from 30.8 to 36.1 seconds.
- **Decision:** Discard; keep the raw HHMM representation.
## Experiment 22 — sample columns per split (`96a3a26`)

- **Class:** Exploration.
- **Hypothesis:** Per-tree sampling improved the model, but it fixes a smaller feature pool for every split in a tree. Replacing it with `colsample_bynode=0.4` may let separate nodes choose different features while keeping the same fraction available at each split.
- **Research:** The [official XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) distinguish `colsample_bytree` (once per tree) from `colsample_bynode` (once per split).
- **Change:** Replaced `colsample_bytree=0.4` with `colsample_bytree=1.0` and `colsample_bynode=0.4`.
- **Result:** Eval AUC `0.7411` (34.2 seconds; status `ok`), down `0.0014` from the current best.
- **Decision:** Discard; keep per-tree sampling.
## Experiment 23 — limit categorical split candidates (`023952f`)

- **Class:** Follow-up to the high-cardinality route overfit and the current native-categorical model.
- **Hypothesis:** Capping categories considered in partition-based splits may regularize airport and carrier splits while retaining their useful effects. Start with `max_cat_threshold=32`.
- **Research:** The [official XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) describe `max_cat_threshold` as the maximum categories considered per split and a control for categorical overfitting.
- **Change:** Set `max_cat_threshold=32` with the current best model.
- **Result:** Eval AUC `0.7420` (33.3 seconds; status `ok`), down `0.0005` from the best. Artifact size decreased to 6.5 MB.
- **Decision:** Discard because Eval AUC fell.

## Experiment 24 — intermediate learning rate and rounds (`1e9b05a`)

- **Class:** Follow-up to the current best with per-tree feature sampling.
- **Hypothesis:** The 400-tree/`0.05` setting is best, while 800/`0.025` was slightly worse before feature sampling. Testing 500 rounds at `0.04` checks an intermediate step size with a correspondingly higher tree count.
- **Research:** XGBoost's [parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommend increasing boosting rounds when reducing the learning rate.
- **Change:** Set `n_estimators=500` and `learning_rate=0.04`, retaining `colsample_bytree=0.4` and `gamma=0.1`.
- **Result:** Eval AUC `0.7421` (35.0 seconds; status `ok`), down `0.0004` from the current best.
- **Decision:** Discard; restore the 400-tree/`0.05` model.

## Experiment 25 — increase L2 leaf regularization (`1341b07`)

- **Class:** Follow-up to the current best.
- **Hypothesis:** The feature-sampled model benefits from mild split pruning. Increasing `reg_lambda` from 1 to 2 may further regularize leaf weights without restricting tree structure.
- **Research:** The [official XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) state that larger `reg_lambda` values make the model more conservative.
- **Change:** Set `reg_lambda=2` instead of the default value of 1.
- **Result:** Eval AUC `0.7422` (33.7 seconds; status `ok`), down `0.0003` from the current best.
- **Decision:** Discard; retain the default L2 penalty.

## Experiment 26 — DART dropout booster (`18fbae2`)

- **Class:** Exploration.
- **Hypothesis:** The current ensemble may still over-specialize across 400 boosting rounds. DART drops existing trees while fitting new ones, which may improve generalization relative to `gbtree`.
- **Research:** The original DART paper reports reduced over-specialization and better results across classification tasks ([PMLR paper](https://proceedings.mlr.press/v38/korlakaivinayak15.html)); XGBoost's [DART guide](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) describes dropout as an overfitting control. The [Python API](https://xgboost.readthedocs.io/en/release_3.0.0/python/python_api.html) supports `iteration_range` in `predict_proba`, which will be set to the full fitted tree range for scoring.
- **Change:** Switched to `booster="dart"` with `rate_drop=0.1`; added a classifier override to evaluate the full fitted tree range deterministically.
- **Result:** Training exceeded the harness's 60-second timeout; no Eval AUC was produced (`timeout-training`).
- **Decision:** Log as `crash` and discard; DART is too slow under this run limit.

## Experiment 27 — two trees per boosting round (`035f389`)

- **Class:** Exploration.
- **Hypothesis:** The current model benefits from feature sampling. Fitting two parallel trees per update may average over more feature subsets while preserving 400 total trees and the same depth, learning rate, and regularization.
- **Research:** The [official XGBoost random-forest guide](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) describes using `num_parallel_tree` with multiple boosting rounds as a boosted random-forest strategy.
- **Change:** Set `n_estimators=200` and `num_parallel_tree=2`, retaining the 400-tree total and other best settings.
- **Result:** Eval AUC `0.7353` (34.5 seconds; status `ok`), down `0.0072` from the single-tree best.
- **Decision:** Discard; return to one tree per boosting round.

## Experiment 28 — mild L1 leaf regularization (`73e6681`)

- **Class:** Follow-up to the current best.
- **Hypothesis:** Increasing L2 regularization did not help, but a small L1 penalty may suppress weak leaf weights more selectively. Test `reg_alpha=0.1` while retaining the default L2 setting.
- **Research:** The [official XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) define `reg_alpha` as the L1 regularization term on leaf weights.
- **Change:** Set `reg_alpha=0.1` with the current best configuration.
- **Result:** Eval AUC `0.7420` (33.5 seconds; status `ok`), down `0.0005` from the best.
- **Decision:** Discard; retain the default L1 penalty.

## Experiment 29 — depth 7 with feature sampling (`2c4edeb`)

- **Class:** Follow-up to the depth-6 best.
- **Hypothesis:** Depths 4 and 5 hurt, but the current model's feature sampling and mild split penalty may support one additional interaction level. Test `max_depth=7` while holding all else fixed.
- **Research:** XGBoost's [parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) describe `max_depth` as a key bias-variance control.
- **Change:** Increased `max_depth` from 6 to 7, retaining `colsample_bytree=0.4` and `gamma=0.1`.
- **Result:** Eval AUC `0.7458` (34.5 seconds; status `ok`), up `0.0033` from the previous best.
- **Decision:** Keep as the new best.

## Experiment 30 — depth 8 with feature sampling (`3b0d806`)

- **Class:** Follow-up to the depth-7 gain.
- **Hypothesis:** Increasing depth from 6 to 7 improved AUC. One more level may capture useful higher-order interactions, though it could overfit; keep all other settings fixed.
- **Research:** This continues the `max_depth` search guided by the [XGBoost parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html).
- **Change:** Increased `max_depth` from 7 to 8, retaining `colsample_bytree=0.4` and `gamma=0.1`.
- **Result:** Eval AUC `0.7472` (35.3 seconds; status `ok`), up `0.0014` from depth 7. Artifact size rose from 12.8 MB to 22.2 MB.
- **Decision:** Keep as the new best; depth 8 gives a meaningful AUC gain despite a larger artifact.

## Synthesis after 30 experiments

- **Best so far:** Commit `3b0d806`, Eval AUC `0.7472` (`n_estimators=400`, `learning_rate=0.05`, depth 8, `colsample_bytree=0.4`, `gamma=0.1`), up `0.0269` over baseline.
- **What helped:** More boosting rounds helped through 200, and 400 at a smaller learning rate was better. Per-tree feature sampling at 0.4 and `gamma=0.1` improved the model. With feature sampling in place, increasing depth from 6 to 7 and 8 added more gains.
- **What did not help:** Time features, route/hour categories, row sampling, child-weight/L1/L2 regularization, lower learning rates beyond 0.05, stronger gamma, by-node sampling, and parallel trees did not improve. DART exceeded the 60-second training limit.
- **Current theory / next direction:** The current eight-feature model benefits from high-depth interactions when column-sampled, despite shallower trees losing AUC. Depth 8 is promising but doubled artifact size from depth 7. Research whether deeper boosted trees with subsampling or categorical interaction handling remain useful, then compare depth 9 and tune complexity around the new high-depth best.

## Experiment 31 — loss-guided tree growth (`97e3fcb`)

- **Class:** Exploration.
- **Hypothesis:** At depth 8, depth-wise growth may spend splits near the root before focusing on the strongest branches. Loss-guided growth may allocate a bounded 256-leaf budget to the largest loss reductions and improve AUC.
- **Research:** The [official XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) support `lossguide` with `hist` or `approx` and define it as splitting nodes with the highest loss change; `max_leaves` provides a cap.
- **Change:** Set `grow_policy="lossguide"`, `max_leaves=256`, and `tree_method="hist"` with max depth 8.
- **Result:** Eval AUC `0.7472` (37.6 seconds; status `ok`), equal to the current best at reported precision; training took 6.4 seconds versus 3.5 for the depth-wise run.
- **Decision:** Discard; the more complex growth policy tied the score and trained more slowly.

## Experiment 32 — depth 9 with feature sampling (`6816613`)

- **Class:** Follow-up to the depth-8 gain.
- **Hypothesis:** Depth 8 improved over depth 7, so depth 9 may capture further useful interactions. Keep feature sampling and split pruning fixed to control complexity; monitor the artifact-size cost.
- **Research:** This continues the high-depth comparison guided by the [XGBoost parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html).
- **Change:** Increased `max_depth` from 8 to 9, retaining the 400-tree, `0.05` learning-rate, column-sampled model.
- **Result:** Eval AUC `0.7470` (36.1 seconds; status `ok`), down `0.0002` from depth 8. Artifact size rose from 22.2 MB to 36.8 MB.
- **Decision:** Discard; the extra depth and artifact size did not improve AUC.

## Experiment 33 — reduce depth-8 model to 300 rounds (`b348a08`)

- **Class:** Simplification of the depth-8 best.
- **Hypothesis:** Deeper trees may make the last 100 rounds redundant. Reducing `n_estimators` from 400 to 300 could preserve AUC while shrinking the artifact and training time.
- **Research:** This ablates boosting rounds around the current best; earlier results showed that rounds matter, so compare directly at depth 8.
- **Change:** Reduced `n_estimators` from 400 to 300, keeping depth 8, learning rate `0.05`, column sampling, and `gamma=0.1` fixed.
- **Result:** Eval AUC `0.7466` (34.6 seconds; status `ok`), down `0.0006` from 400 rounds. Artifact size fell from 22.2 MB to 16.5 MB, and training time from 3.3 to 2.5 seconds.
- **Decision:** Keep as a simplification win; the small AUC reduction buys a 25% smaller artifact and lower training time.

## Experiment 34 — midpoint at 350 rounds (`20de88c`)

- **Class:** Follow-up to the 300-round simplification.
- **Hypothesis:** The 300-tree model lost only `0.0006` AUC versus 400 rounds. Trying 350 may recover some ranking performance while keeping an artifact smaller than the 400-tree model.
- **Research:** This brackets boosting rounds around the current compact depth-8 model, motivated by the measured 300-versus-400 results.
- **Change:** Increased `n_estimators` from 300 to 350, keeping the depth-8 configuration fixed.
- **Result:** Eval AUC `0.7472` (34.6 seconds; status `ok`), recovering `0.0006` versus 300 rounds and matching the 400-round score at reported precision. Artifact size was 19.3 MB, 13% below the 400-round model; training took 2.9 seconds.
- **Decision:** Keep; the 350-round model recovers the measured AUC while remaining smaller than the 400-round model.

## Experiment 35 — smaller learning rate at depth 8 (`659a243`)

- **Class:** Follow-up to the depth-8 gain.
- **Hypothesis:** A smaller learning rate may make finer corrections across boosting rounds. Try `learning_rate=0.04` with 450 rounds, approximately preserving the current `0.05 × 350` total step size while testing it with the stronger depth-8 configuration. The earlier 0.04 trial used a shallower model.
- **Research:** The [XGBoost parameter tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends tuning learning rate together with the number of boosting rounds; the current depth-8 result motivates retesting that pair.
- **Change:** Set `learning_rate=0.04` and `n_estimators=450`, keeping the depth-8 tree configuration fixed.
- **Result:** Eval AUC `0.7475` (35.6 seconds; status `ok`), up `0.0003` from the 350-round model. Artifact size was 24.7 MB; training took 3.7 seconds.
- **Decision:** Keep; this is a small but measurable AUC improvement over the prior best.

## Experiment 36 — one-hot splits for small categories (`0d8452c`)

- **Class:** Exploration of categorical split strategy.
- **Hypothesis:** Direct one-hot splits may let the model isolate individual month and weekday effects, while higher-cardinality categories retain partition-based splits. Set the category threshold to 13, keeping the current depth-8 model fixed.
- **Research:** [XGBoost's categorical parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) describe `max_cat_to_onehot` as the threshold between one-hot and partition-based splits.
- **Change:** Set `max_cat_to_onehot=13`, retaining the current depth-8 model and training schedule.
- **Result:** Eval AUC `0.7453` (35.0 seconds; status `ok`), down `0.0022` from the current best. Artifact size was 23.2 MB; training took 3.5 seconds.
- **Decision:** Discard; the one-hot threshold did not improve AUC.

## Experiment 37 — modest positive-class weighting (`67392a8`)

- **Class:** Exploration of objective weighting.
- **Hypothesis:** Give delayed flights twice the training weight to encourage splits that identify the positive class, which may improve ranking under class imbalance. Keep all features and the current tree settings fixed.
- **Research:** The [XGBoost parameter tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends considering `scale_pos_weight` when AUC is the target; the parameter docs describe it as balancing positive and negative weights.
- **Change:** Set `scale_pos_weight=2.0`, retaining the current feature and tree configuration.
- **Result:** Eval AUC `0.7469` (35.6 seconds; status `ok`), down `0.0006` from the current best. Artifact size was 24.4 MB; training took 3.7 seconds.
- **Decision:** Discard; the positive-class weighting did not improve ranking.

## Experiment 38 — finer histogram bins (`e163052`)

- **Class:** Exploration of numeric split resolution.
- **Hypothesis:** Increasing the histogram from 256 to 512 bins may let the deep trees choose more precise thresholds for `CRSDepTime` and `Distance`, at some extra training cost.
- **Research:** The [XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) state that `max_bin` controls continuous-feature bins for histogram trees and that more bins can improve split optimality at higher computation cost.
- **Change:** Set `tree_method="hist"` and increased `max_bin` from its default to 512.
- **Result:** Eval AUC `0.7474` (35.4 seconds; status `ok`), `0.0001` below the current best. Artifact size was 24.4 MB; training took 3.7 seconds.
- **Decision:** Discard; the slight score loss and extra split resolution did not justify changing the model.

## Experiment 39 — cross-fitted route delay-rate encoding (`460b1f1`)

- **Class:** Exploration of leakage-safe target encoding.
- **Hypothesis:** The raw origin-destination categorical feature hurt substantially, likely because many routes are rare. A smoothed route delay-rate feature could keep signal on frequent routes while shrinking rare routes toward the global rate. Use five-fold out-of-fold values for training so each flight's target is excluded from its own encoding; evaluation rows use a lookup fit on all training rows.
- **Research:** The [scikit-learn cross-fitting example](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html) explains that target means should be cross-fitted to prevent overfitting; the [TargetEncoder docs](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html) describe smoothing category rates toward the global target mean.
- **Change:** Added one smoothed origin-destination target-rate feature (`20`-flight prior strength), using deterministic five-fold out-of-fold rates for training and a full-train smoothed lookup for evaluation.
- **Result:** Eval AUC `0.7440` (43.6 seconds; status `ok`), down `0.0035` from the current best. Artifact size was 23.2 MB; training took 3.6 seconds, while row-by-row evaluation rose to 38.7 seconds.
- **Decision:** Discard; the safer encoding substantially beat the raw route feature but did not match the current model and slowed evaluation.

## Experiment 40 — cross-fitted origin delay rate (`f710efb`)

- **Class:** Exploration of a less sparse airport-level signal.
- **Hypothesis:** Origin airports have local operating conditions associated with departure delays. A smoothed airport-level rate uses many more flights per category than an origin-destination route, so it may be more stable and useful than the route encoding from Experiment 39. Train with five-fold out-of-fold rates and evaluate with a full-training lookup.
- **Research:** Li et al. analyze local and network delay effects at individual airports and report that airport-level factors carry predictive information in [their flight-delay study](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057).
- **Change:** Added one origin-airport target-rate feature with a 50-flight prior, using five-fold out-of-fold rates for training and a full-training lookup for evaluation.
- **Result:** Eval AUC `0.7453` (38.8 seconds; status `ok`), down `0.0022` from the current best. Artifact size was 22.6 MB; training took 3.5 seconds and evaluation 34.0 seconds.
- **Decision:** Discard; airport-level rate encoding also failed to beat the native categorical model.

## Synthesis after 40 experiments

- **Best:** Commit `659a243`, Eval AUC `0.7475`: depth 8, 450 rounds, learning rate `0.04`, `colsample_bytree=0.4`, `gamma=0.1`. It improved by `0.0272` over baseline.
- **What helped:** Deeper trees through depth 8, modest per-tree feature sampling, and retuning the learning-rate/rounds pair at depth 8. The 350-round model also matched the former best with a smaller artifact.
- **What did not:** Depth 9 and loss-guided growth, a one-hot categorical threshold, positive-class weighting, higher histogram resolution, and smoothed cross-fitted route or origin rates. Native categorical handling currently beats these added encodings and keeps row-by-row evaluation faster.
- **Current theory:** Useful high-order interactions among the original categorical and numeric features drive the gain; the depth-8 model benefits from sampling a subset of features per tree. Recent domain-derived aggregates did not improve generalization on this split.
- **Next direction:** Research ways to make feature sampling more informative or tune its rate in the deeper model; retain the original compact feature set unless evidence supports adding features.

## Experiment 41 — favor numeric features during sampling (`6d3691a`)

- **Class:** Follow-up to the feature-sampling gain.
- **Hypothesis:** With `colsample_bytree=0.4`, some trees may omit both numeric fields. Weight `CRSDepTime` and `Distance` twice as strongly as the categorical features so schedule and route-length information is sampled more often while retaining the same column fraction.
- **Research:** The [XGBoost Python API docs](https://xgboost.readthedocs.io/en/stable/python/python_api.html) define `feature_weights` as weights for column sampling. The flight-delay study by [Li et al.](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057) includes scheduled departure time and distance among commonly used prediction factors.
- **Change:** Passed feature weights of `2.0` for `CRSDepTime` and `Distance` and `1.0` for each categorical feature to `fit`.
- **Result:** Eval AUC `0.7434` (35.7 seconds; status `ok`), down `0.0041` from the current best. Artifact size was 22.1 MB; training took 3.5 seconds. XGBoost accepted the weights and warned that the `fit` argument is deprecated in favor of constructor or `set_params` configuration.
- **Decision:** Discard; weighted feature sampling reduced AUC substantially.

## Experiment 42 — retune column fraction at depth 8 (`be6fb10`)

- **Class:** Follow-up to the depth-8 feature-sampling gain.
- **Hypothesis:** The earlier `colsample_bytree=0.5` trial was at depth 6. With depth 8 and the improved `0.04` learning-rate schedule, allowing half the features per tree may expose useful combinations that the 0.4 fraction misses.
- **Research:** The current best and the depth-6 column-fraction sweep motivate retesting this value after the depth increase; the [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) defines the per-tree column sampling ratio.
- **Change:** Increased `colsample_bytree` from 0.4 to 0.5, retaining depth 8, 450 rounds, and learning rate 0.04.
- **Result:** Eval AUC `0.7486` (35.5 seconds; status `ok`), up `0.0011` from the prior best. Artifact size was 29.0 MB; training took 3.9 seconds.
- **Decision:** Keep; the deeper model benefits from sampling more features per tree.

## Experiment 43 — test a 0.6 tree feature fraction (`3298742`)

- **Class:** Follow-up to the `0.5` feature-sampling gain.
- **Hypothesis:** Raising the tree fraction from 0.5 to 0.6 may expose more useful feature combinations in depth-8 trees. The earlier 0.6 result was at depth 6, so this tests it in the new stronger configuration.
- **Research:** The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `colsample_bytree` as the fraction of columns sampled for each tree; Experiment 42 shows the best depth-8 value may differ from the earlier depth-6 sweep.
- **Change:** Increased `colsample_bytree` from 0.5 to 0.6, retaining depth 8, 450 rounds, and learning rate 0.04.
- **Result:** Eval AUC `0.7486` (35.7 seconds; status `ok`), tied with the current best at reported precision. Artifact size remained 29.0 MB; training took 3.9 seconds.
- **Decision:** Discard; it tied the 0.5 model without reducing model size or runtime.

## Experiment 44 — midpoint at 0.55 tree feature fraction (`d7c7b84`)

- **Class:** Follow-up to the `0.5` gain and `0.6` tie.
- **Hypothesis:** The best feature fraction may lie between 0.5 and 0.6. Test 0.55 to refine the local maximum for the depth-8, 0.04/450 model.
- **Research:** The recent 0.5, 0.6, and prior depth-6 0.4 results motivate a narrow, measured bracket around the current peak; the [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) defines this parameter's per-tree column fraction.
- **Change:** Set `colsample_bytree=0.55`, retaining the depth-8, 0.04/450 model.
- **Result:** Eval AUC `0.7486` (35.8 seconds; status `ok`), tied with the current best. Artifact size remained 29.0 MB; training took 3.9 seconds.
- **Decision:** Discard; 0.55 tied but did not improve on the smaller 0.5 tree fraction.

## Experiment 45 — depth 9 with stronger feature sampling (`fc5e4ac`)

- **Class:** Follow-up to the depth-8 and feature-sampling gains.
- **Hypothesis:** Depth 9 previously scored slightly worse using `colsample_bytree=0.4`, learning rate 0.05, and 400 rounds. Test depth 9 with the now-better 0.5 feature fraction and 0.04/450 schedule to see whether deeper interactions improve further.
- **Research:** The prior depth-9 result and current depth-8 best motivate a controlled retest; the [XGBoost parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) advise tuning interacting tree parameters together.
- **Change:** Increased `max_depth` from 8 to 9, keeping `colsample_bytree=0.5`, learning rate 0.04, and 450 rounds fixed.
- **Result:** Eval AUC `0.7491` (37.7 seconds; status `ok`), up `0.0005` from the depth-8 model. Artifact size rose from 29.0 MB to 49.2 MB; training took 5.6 seconds.
- **Decision:** Keep; the AUC improved with a one-parameter configuration change, and the larger artifact and added training time remain within the harness budget.

## Experiment 46 — regularize deep leaves (`b328d4d`)

- **Class:** Follow-up to the depth-9 gain.
- **Hypothesis:** The larger depth-9 model may include small leaves that overfit. Set `min_child_weight=2` to require more Hessian mass per child; it may preserve AUC while reducing the model's leaf complexity. The value was neutral in a shallower model, but has not been tested with depth 9.
- **Research:** The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `min_child_weight` as the minimum sum of instance-weight Hessians needed in a child; the deeper model motivates retesting this regularizer.
- **Change:** Set `min_child_weight=2` with the depth-9, 0.5 feature-fraction, 0.04/450 model.
- **Result:** Eval AUC `0.7500` (37.1 seconds; status `ok`), up `0.0009` from the prior best. Artifact size fell from 49.2 MB to 48.5 MB; training took 4.9 seconds.
- **Decision:** Keep; the regularizer improved AUC while slightly reducing artifact size and training time.

## Experiment 47 — slightly stronger leaf regularization (`f888d1d`)

- **Class:** Follow-up to the `min_child_weight=2` gain.
- **Hypothesis:** Raising `min_child_weight` to 3 may remove more weak leaves from depth-9 trees and improve generalization, continuing the regularization gain seen at 2.
- **Research:** The [XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) describe the child Hessian threshold; Experiment 46 provides direct evidence that the deeper trees benefit from moving above the default.
- **Change:** Raised `min_child_weight` from 2 to 3 in the depth-9 model.
- **Result:** Eval AUC `0.7494` (37.1 seconds; status `ok`), down `0.0006` from the weight-2 model. Artifact size fell slightly to 47.9 MB; training took 4.9 seconds.
- **Decision:** Discard; the small artifact reduction did not compensate for the AUC loss.

## Experiment 48 — depth 10 with leaf regularization (`28e19b7`)

- **Class:** Follow-up to the depth-9 gain.
- **Hypothesis:** Depth 9 improved over depth 8, and `min_child_weight=2` improved the deeper model. Test depth 10 with that regularizer to see whether one more interaction level helps without unrestricted tiny leaves.
- **Research:** The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends tuning depth and leaf constraints together; the recent depth-9 and child-weight results motivate this controlled extension.
- **Change:** Increased `max_depth` from 9 to 10, retaining `min_child_weight=2`, `colsample_bytree=0.5`, and the 0.04/450 schedule.
- **Result:** Eval AUC `0.7493` (38.2 seconds; status `ok`), down `0.0007` from the depth-9 best. Artifact size rose to 77.2 MB; training took 6.2 seconds.
- **Decision:** Discard; the extra depth reduced AUC and substantially increased artifact size.

## Experiment 49 — reduce depth-9 rounds to 400 (`d81ccec`)

- **Class:** Simplification of the depth-9 best.
- **Hypothesis:** The depth-8 model retained its best score at 350 instead of 400 rounds. Reducing the depth-9 model from 450 to 400 rounds may preserve its AUC while shrinking the model.
- **Research:** The depth-8 round ablation motivates testing this at depth 9, where deeper leaves and `min_child_weight=2` may change how many rounds are needed.
- **Change:** Reduced `n_estimators` from 450 to 400, retaining depth 9 and `min_child_weight=2`.
- **Result:** Eval AUC `0.7500` (36.6 seconds; status `ok`), tied with the 450-round best at reported precision. Artifact size fell from 48.5 MB to 43.5 MB; training took 4.4 seconds.
- **Decision:** Keep as a simplification win; it preserves AUC with a 10% smaller artifact and lower training time.

## Experiment 50 — reduce depth-9 rounds to 350 (`74c0a1f`)

- **Class:** Further simplification of the depth-9 best.
- **Hypothesis:** The depth-8 model retained its score at 350 rounds, and the depth-9 model matched 450 rounds at 400. Try 350 rounds to see whether additional trees can be removed without a meaningful AUC loss.
- **Research:** This continues the direct rounds ablation motivated by Experiments 33, 34, and 49.
- **Change:** Reduced `n_estimators` from 400 to 350, retaining depth 9 and `min_child_weight=2`.
- **Result:** Eval AUC `0.7500` (35.8 seconds; status `ok`), tied with the 400-round model at reported precision. Artifact size fell from 43.5 MB to 38.1 MB; training took 3.9 seconds.
- **Decision:** Keep as a simplification win; it preserves AUC with a 12% smaller artifact and lower training time.

## Synthesis after 50 experiments

- **Best:** Commit `74c0a1f`, Eval AUC `0.7500`: depth 9, 350 rounds, learning rate `0.04`, `colsample_bytree=0.5`, `min_child_weight=2`, and `gamma=0.1`. This is `0.0297` above baseline.
- **What helped:** Moving the tree feature fraction from 0.4 to 0.5 at depth 8; retesting depth 9 under that stronger configuration; `min_child_weight=2` at depth 9. Reducing rounds from 450 to 350 preserved the best score and cut the artifact to 38.1 MB.
- **What did not:** Feature sampling weights favoring numeric fields, depth 10, `min_child_weight=3`, and feature fractions 0.55/0.6 did not improve the best. Route and airport target-rate features also underperformed native categories.
- **Current theory:** The best model uses depth 9 with moderate feature sampling and a small child-weight floor to exploit interactions while avoiding weak leaves. Much of the 450-round ensemble was redundant; 350 rounds now gives the same score.
- **Next direction:** Research leaf-output and logistic-objective regularization for deep trees, then test one controlled change at a time.

## Experiment 51 — cap leaf output changes (`e8a966d`)

- **Class:** Exploration of leaf-output regularization.
- **Hypothesis:** Limiting each leaf's output step may make the depth-9 model more conservative and reduce overfit without changing its tree structure or training schedule.
- **Research:** The [XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) define `max_delta_step` as a maximum leaf-output step; positive values make updates more conservative. Test the guide's suggested value of 1 with the current best.
- **Change:** Set `max_delta_step=1`, retaining the depth-9, 350-round model with `min_child_weight=2`.
- **Result:** Eval AUC `0.7496` (35.7 seconds; status `ok`), down `0.0004` from the current best. Artifact size was 37.9 MB; training took 3.9 seconds.
- **Decision:** Discard; the leaf-output cap reduced AUC and barely changed model size.

## Experiment 52 — same step budget with fewer rounds (`5d55e95`)

- **Class:** Simplification of the depth-9 best.
- **Hypothesis:** Try `learning_rate=0.05` with 280 rounds, approximately preserving the current `0.04 × 350` total step budget while reducing the tree count by 20%. This may maintain AUC with a smaller artifact and faster training.
- **Research:** Experiments 35 and 50 show that learning-rate/rounds tradeoffs shift with tree depth; this tests a matched step budget on the current depth-9 configuration.
- **Change:** Set `learning_rate=0.05` and `n_estimators=280`, retaining depth 9 and `min_child_weight=2`.
- **Result:** Eval AUC `0.7496` (35.0 seconds; status `ok`), down `0.0004` from the best. Artifact size fell from 38.1 MB to 30.1 MB; training took 3.2 seconds.
- **Decision:** Keep as a simplification win; the small AUC reduction buys a 21% smaller artifact and lower training time.

## Experiment 53 — intermediate learning-rate schedule (`7026164`)

- **Class:** Follow-up to the rounds simplification.
- **Hypothesis:** Interpolate between `0.04 × 350` (best AUC) and `0.05 × 280` (smaller artifact): use `learning_rate=0.045` with 310 rounds, keeping the approximate total step budget while potentially recovering AUC with fewer trees than the best model.
- **Research:** Experiments 50 and 52 bracket the tree-count/step-size tradeoff for the depth-9 regularized model.
- **Change:** Set `learning_rate=0.045` and `n_estimators=310`, retaining depth 9 and `min_child_weight=2`.
- **Result:** Eval AUC `0.7494` (35.2 seconds; status `ok`), down `0.0002` from the compact `0.05/280` model. Artifact size was 33.9 MB; training took 3.4 seconds.
- **Decision:** Discard; the intermediate schedule scored lower and produced a larger artifact than the compact `0.05/280` model.

## Experiment 54 — add rounds to compact depth-9 model (`0d4f090`)

- **Class:** Follow-up to the compact `0.05/280` result.
- **Hypothesis:** The 280-round model scored `0.7496`, slightly below the `0.04/350` best. Raising it to 320 rounds at learning rate 0.05 may recover AUC while keeping a smaller artifact than the 350-round model.
- **Research:** Experiments 50, 52, and 53 bracket the rounds/learning-rate schedule for the depth-9 model; this tests whether a moderate round increase improves the compact candidate.
- **Change:** Increased the compact model from 280 to 320 rounds at learning rate 0.05.
- **Result:** Eval AUC `0.7492` (35.3 seconds; status `ok`), down `0.0004` from the 280-round compact model. Artifact size rose from 30.1 MB to 34.3 MB; training took 3.5 seconds.
- **Decision:** Discard; more rounds reduced AUC and increased artifact size.

## Experiment 55 — modest L2 regularization increase (`cec373c`)

- **Class:** Follow-up to the depth-9 regularization gains.
- **Hypothesis:** A small increase in `reg_lambda` from 1 to 2 may further stabilize the depth-9 leaves while retaining the gains from `min_child_weight=2`. The earlier lambda trial was at depth 6.
- **Research:** The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `reg_lambda` as L2 regularization on leaf weights; retest it with the deeper tree structure that has now proved beneficial.
- **Change:** Set `reg_lambda=2` with depth 9, 350 rounds, `colsample_bytree=0.5`, and `min_child_weight=2`.
- **Result:** Eval AUC `0.7510` (35.9 seconds; status `ok`), up `0.0010` from the prior best. Artifact size fell slightly to 37.2 MB; training took 3.9 seconds.
- **Decision:** Keep; stronger L2 regularization improved AUC while slightly shrinking the model.

## Experiment 56 — increase L2 regularization to 3 (`f3cfbdd`)

- **Class:** Follow-up to the `reg_lambda=2` gain.
- **Hypothesis:** A further increase to 3 may continue to stabilize the deeper leaves, or indicate that the gain peaks near 2.
- **Research:** The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `reg_lambda` as L2 regularization; Experiment 55 provides a direct gain at depth 9 and motivates a modest follow-up.
- **Change:** Raised `reg_lambda` from 2 to 3, retaining depth 9, 350 rounds, and `min_child_weight=2`.
- **Result:** Eval AUC `0.7511` (35.8 seconds; status `ok`), up `0.0001` from the prior best. Artifact size fell to 36.3 MB; training took 3.9 seconds.
- **Decision:** Keep; the score edged higher and the artifact shrank.

## Experiment 57 — increase L2 regularization to 4 (`a996d58`)

- **Class:** Follow-up to the small gain at `reg_lambda=3`.
- **Hypothesis:** Test whether L2 regularization continues to help at 4 or whether the improvement peaks around 3.
- **Research:** The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) defines the leaf-weight penalty; the measured depth-9 gains at values 2 and 3 motivate one more step.
- **Change:** Raised `reg_lambda` from 3 to 4, retaining the depth-9 regularized model.
- **Result:** Eval AUC `0.7508` (35.9 seconds; status `ok`), down `0.0003` from the current best. Artifact size fell slightly to 35.8 MB; training took 3.9 seconds.
- **Decision:** Discard; the small size change does not offset the score loss.

## Experiment 58 — refine L2 regularization near 3 (`1a90f10`)

- **Class:** Follow-up to the `reg_lambda` sweep.
- **Hypothesis:** Values 2 and 3 scored 0.7510 and 0.7511, while 4 fell to 0.7508. Test 2.5 to check whether a slightly smaller penalty can improve on the local peak.
- **Research:** The recent local sweep and the [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) motivate checking an intermediate L2 value with all other settings fixed.
- **Change:** Set `reg_lambda=2.5`, retaining depth 9 and the other current best settings.
- **Result:** Eval AUC `0.7504` (35.8 seconds; status `ok`), down `0.0007` from `reg_lambda=3`. Artifact size was 37.0 MB; training took 3.9 seconds.
- **Decision:** Discard; the local regularization peak remains at 3.

## Experiment 59 — relax split-loss threshold slightly (`0e31508`)

- **Class:** Follow-up to the regularized depth-9 gain.
- **Hypothesis:** With `reg_lambda=3` and `min_child_weight=2` controlling leaf complexity, lowering `gamma` from 0.1 to 0.05 may admit a few useful splits and improve AUC.
- **Research:** The [XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) define `gamma` as the minimum loss reduction required for a split; test a small decrease while keeping the other regularizers fixed.
- **Change:** Lowered `gamma` from 0.1 to 0.05, retaining `reg_lambda=3` and `min_child_weight=2`.
- **Result:** Eval AUC `0.7505` (36.6 seconds; status `ok`), down `0.0006` from the current best. Artifact size was 36.7 MB; training took 4.9 seconds.
- **Decision:** Discard; admitting more splits lowered AUC and increased training time.

## Experiment 60 — mild L1 regularization with depth 9 (`59dfad7`)

- **Class:** Exploration of L1/L2 regularization interaction.
- **Hypothesis:** The depth-9 model improved with `reg_lambda=3`. Add mild `reg_alpha=0.1` to see whether sparse leaf weights complement that L2 penalty; the earlier L1 trial used a shallower model.
- **Research:** The [XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) define `reg_alpha` as L1 regularization on leaf weights and note that larger values make the model more conservative.
- **Change:** Added `reg_alpha=0.1` to the depth-9 model with `reg_lambda=3`.
- **Result:** Eval AUC `0.7515` (36.2 seconds; status `ok`), up `0.0004` from the prior best. Artifact size was 38.7 MB; training took 3.9 seconds.
- **Decision:** Keep; mild L1 regularization improved the current best.

## Synthesis after 60 experiments

- **Best:** Commit `59dfad7`, Eval AUC `0.7515`: depth 9, 350 rounds, learning rate `0.04`, `colsample_bytree=0.5`, `min_child_weight=2`, `gamma=0.1`, `reg_lambda=3`, and `reg_alpha=0.1`. This is `0.0312` above baseline.
- **What helped:** The 0.5 tree feature fraction, depth 9 with `min_child_weight=2`, L2 around 3, and adding mild L1 on top of L2. Round reductions to 350 retained the best score and limited artifact size.
- **What did not:** Depth 10, leaf-output capping, a higher child-weight threshold, more L2 (4) or an intermediate 2.5, lower gamma, and most alternate round schedules did not beat the best. The 0.05/280 model remains a useful smaller near-best option.
- **Current theory:** High-order interactions in depth-9 trees generalize best when the feature fraction is moderate and leaf weights are regularized with L2=3 plus mild L1. More depth or less split pruning did not help.
- **Next direction:** Research nearby regularization settings or a compact alternate ensemble, then continue controlled tests while preserving the 0.7515 checkpoint.

## Experiment 61 — increase L1 regularization to 0.2 (`118a7a6`)

- **Class:** Follow-up to the `reg_alpha=0.1` gain.
- **Hypothesis:** A slightly stronger L1 penalty may continue to suppress weak leaf weights after the gain from 0.1; keep all other settings fixed.
- **Research:** The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) frames regularization as a bias-variance control; the parameter docs say higher `reg_alpha` makes the model more conservative. Test a small step from the measured 0.1 result.
- **Change:** Increased `reg_alpha` from 0.1 to 0.2, retaining the depth-9 model with `reg_lambda=3`.
- **Result:** Eval AUC `0.7518` (35.9 seconds; status `ok`), up `0.0003` from the prior best. Artifact size was 39.7 MB; training took 3.9 seconds.
- **Decision:** Keep; the mild L1 increase improved AUC.

## Experiment 62 — increase L1 regularization to 0.3 (`ace666b`)

- **Class:** Follow-up to the `reg_alpha=0.2` gain.
- **Hypothesis:** A further small increase may continue to suppress weak leaf weights; test 0.3 with the rest of the best configuration fixed.
- **Research:** The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes increasing `reg_alpha` as more conservative; Experiment 61 motivates checking whether the gain continues.
- **Change:** Increased `reg_alpha` from 0.2 to 0.3, retaining the depth-9 model with `reg_lambda=3`.
- **Result:** Eval AUC `0.7515` (35.9 seconds; status `ok`), down `0.0003` from the 0.2 model. Artifact size rose to 40.3 MB; training took 3.9 seconds.
- **Decision:** Discard; the score and artifact cost both moved in the wrong direction.

## Experiment 63 — refine L1 regularization near 0.2 (`a0656d9`)

- **Class:** Follow-up to the L1 regularization sweep.
- **Hypothesis:** The scores at 0.1 and 0.3 were both below the 0.2 result. Test 0.25 to refine the local peak.
- **Research:** The observed local sweep motivates this intermediate value; the [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) confirms `reg_alpha` controls conservative L1 shrinkage.
- **Change:** Set `reg_alpha=0.25`, retaining the current depth-9 model with `reg_lambda=3`.
- **Result:** Eval AUC `0.7510` (35.8 seconds; status `ok`), down `0.0008` from the 0.2 model. Artifact size was 40.2 MB; training took 4.0 seconds.
- **Decision:** Discard; the midpoint did not improve the local peak and increased artifact size.

## Experiment 64 — reduce regularized depth-9 model to 325 rounds (`e1cf167`)

- **Class:** Simplification of the current best.
- **Hypothesis:** The 350-round model with `reg_lambda=3` and `reg_alpha=0.2` scores 0.7518. Reducing it to 325 rounds may preserve nearly all AUC while shrinking the artifact.
- **Research:** Earlier rounds ablations showed substantial redundancy at depth 9; test a small reduction after adding L1 regularization.
- **Change:** Reduced `n_estimators` from 350 to 325, retaining depth 9, `reg_lambda=3`, and `reg_alpha=0.2`.
- **Result:** Eval AUC `0.7514` (35.6 seconds; status `ok`), down `0.0004` from the best. Artifact size fell from 39.7 MB to 36.9 MB; training took 3.6 seconds.
- **Decision:** Keep as a compact near-best; the small score loss buys a 7% smaller artifact and slightly lower training time.

## Experiment 65 — reduce regularized depth-9 model to 300 rounds (`d9fcb69`)

- **Class:** Further simplification of the L1/L2 model.
- **Hypothesis:** Reducing 25 more rounds may shrink the artifact further; retain 300 rounds only if the AUC stays close to 0.7514.
- **Research:** The recent 350-to-325 reduction motivates one more direct ablation at 300 rounds.
- **Change:** Reduced `n_estimators` from 325 to 300, retaining depth 9 and both regularizers.
- **Result:** Eval AUC `0.7514` (35.1 seconds; status `ok`), tied with the 325-round model at reported precision. Artifact size fell from 36.9 MB to 34.2 MB; training took 3.4 seconds.
- **Decision:** Keep as a further simplification; the same score comes with a 7% smaller artifact and lower training time.

## Experiment 66 — reduce regularized depth-9 model to 275 rounds (`79a9d20`)

- **Class:** Further simplification of the current near-best.
- **Hypothesis:** Removing 25 more rounds may reduce the artifact without changing reported AUC; compare directly with the 300-round model.
- **Research:** Experiments 64 and 65 both preserved AUC while reducing rounds, motivating one final reduction if time permits.
- **Change:** Reduced `n_estimators` from 300 to 275, retaining depth 9 and both regularizers.
- **Result:** Eval AUC `0.7510` (36.6 seconds; status `ok`), down `0.0004` from the 300-round model. Artifact size fell from 34.2 MB to 31.6 MB; training took 4.5 seconds.
- **Decision:** Keep as a further compact near-best; the score loss remains small with a 7.6% smaller artifact.

## Experiment 67 — depth 8 with L1/L2 regularization (`f73d748`)

- **Class:** Ablation of the depth-9 best.
- **Hypothesis:** The new L1/L2 penalties may reduce the need for depth 9. Test depth 8 with the best regularizers, 350 rounds, and the same feature fraction to see whether a simpler tree structure approaches the best AUC.
- **Research:** Earlier depth tests used weaker regularization; the recent gains at depth 9 motivate retesting one level shallower with `reg_lambda=3` and `reg_alpha=0.2` held fixed.
- **Change:** Reduced `max_depth` from 9 to 8, retaining 350 rounds, `reg_lambda=3`, and `reg_alpha=0.2`.
- **Result:** Eval AUC `0.7489` (34.8 seconds; status `ok`), down `0.0029` from the depth-9 best. Artifact size fell to 23.2 MB; training took 3.2 seconds.
- **Decision:** Discard; the artifact is smaller, but the score loss is material.

## Experiment 68 — slightly lower child-weight threshold (`44eedad`)

- **Class:** Follow-up to the depth-9 regularization gains.
- **Hypothesis:** With `reg_lambda=3` and `reg_alpha=0.2` already shrinking leaf weights, `min_child_weight=1.5` may permit useful smaller leaves and improve AUC over the current threshold of 2.
- **Research:** The previous child-weight sweep peaked at 2 before the L1/L2 additions; test a modest reduction on the new regularized best.
- **Change:** Reduced `min_child_weight` from 2 to 1.5, retaining depth 9, `reg_lambda=3`, and `reg_alpha=0.2`.
- **Result:** Eval AUC `0.7516` (35.9 seconds; status `ok`), down `0.0002` from the best. Artifact size rose to 40.6 MB; training took 4.0 seconds.
- **Decision:** Discard; the lower child threshold did not improve AUC and enlarged the artifact.

## Final summary

- **Best checkpoint:** Commit `118a7a6`, Eval AUC `0.7518`, on branch `oct1`. The configuration is depth 9, 350 rounds, learning rate `0.04`, `colsample_bytree=0.5`, `min_child_weight=2`, `gamma=0.1`, `reg_lambda=3`, and `reg_alpha=0.2`. It improves on the `0.7203` baseline by `0.0315`.
- **What worked:** Deeper trees through depth 9, a 0.5 per-tree feature fraction, `min_child_weight=2`, L2 regularization around 3, and mild L1 regularization at 0.2. The regularization gains compounded: L2=3 moved the model to 0.7511, then L1=0.1 and 0.2 raised it to 0.7515 and 0.7518.
- **What did not:** Depth 10, depth 8 with the stronger penalties, leaf-output capping, feature-weighted sampling, additional target-rate features, positive-class weighting, one-hot category splits, and the lower-gamma and alternate-round trials did not beat the best. Reducing to 300 rounds preserved a near-best `0.7514` with a 34.2 MB artifact; 275 rounds scored `0.7510` with a 31.6 MB artifact.
- **Next:** If continuing, refine `reg_alpha` around 0.2 with the depth-9/L2=3 configuration, then compare small round reductions against the score and artifact-size tradeoff.
