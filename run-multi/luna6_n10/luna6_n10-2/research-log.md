# Research Log

## Setup
- Run tag and branch: `sep30`.
- Data check: `data/train.csv` and `data/eval.csv` are present.
- Experiment clock: started; two-hour budget.

## Experiment 1 — starter baseline
- Commit: `92e43e6`.
- Hypothesis: establish the starter model's Eval AUC before making changes.
- Change: none; ran the starter `train.py` as provided.
- Result: Eval AUC `0.7203`; status `ok`; run time `31.9s`.
- Observation: baseline training and row-by-row evaluation completed within the harness limits; artifact was saved for this commit.

## Experiment 2 plan — slower learning with more rounds
- Hypothesis: the 30-tree starter may stop boosting too early; reducing the learning rate to `0.05` while increasing to 300 trees should let the model build a more refined ranking without changing the feature set or tree structure.
- Category: follow-up to the baseline.
- Research: the [XGBoost parameter tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) advises increasing boosting rounds when reducing `eta` and frames complexity as a bias/variance tradeoff.
- Planned change: `n_estimators=300`, `learning_rate=0.05`; leave all other settings unchanged.
- Outcome: Eval AUC `0.7348` (`ok`, 33.3s), improving the baseline by `0.0145`; kept commit `1455db4`.

## Experiment 3 plan — reduce tree depth
- Hypothesis: with 300 rounds now providing more boosting capacity, depth-6 trees may fit overly specific splits. Reducing only `max_depth` to 4 may improve generalization while preserving the gain from the lower learning rate.
- Category: follow-up to the promising Experiment 2.
- Research basis: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `max_depth` as controlling tree complexity and warns that larger values can increase overfitting.
- Planned change: `max_depth=4`; retain 300 estimators and learning rate 0.05.
- Outcome: Eval AUC `0.7300` (`ok`, 32.4s), below Experiment 2's `0.7348`; discarded commit `1c9a9d0` and reverted to the best kept model. This suggests depth 6's extra split capacity helped on this split.

## Experiment 4 plan — encode scheduled departure time on a daily cycle
- Hypothesis: the model receives scheduled departure time as an `HHMM` integer. Adding the hour and a sine/cosine position on the 24-hour clock may make the midnight wraparound and hour-scale congestion patterns easier to learn.
- Category: exploration — first feature-engineering change.
- Research: scikit-learn's [time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) shows a sine/cosine pair preserving adjacency across midnight; a [flight-delay study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) includes scheduled departure time among its predictors.
- Planned change: add row-wise scheduled hour, `DepTimeSin`, and `DepTimeCos` in `prepare(df)` only. The transform uses only each row's `CRSDepTime`; it fits no statistics and reads no files.
- Outcome: Eval AUC `0.7341` (`ok`, 39.9s), slightly below the `0.7348` best, with longer evaluation and three added features; discarded commit `fa646c2` and reverted to the simpler best model.

## Experiment 5 plan — row subsampling
- Hypothesis: depth 4 reduced AUC, so keep the model's depth-6 split capacity and test whether sampling 80% of rows per boosting round reduces variance without that loss of capacity.
- Category: follow-up to the best model.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says `subsample` randomly selects training rows each round and can help prevent overfitting.
- Planned change: add `subsample=0.8`; all other parameters and features stay fixed.
- Outcome: Eval AUC `0.7283` (`ok`, 33.3s), `0.0065` below the best; discarded commit `f40a95c` and restored the best model. Row subsampling at 0.8 hurt this run.

## Experiment 6 plan — test deeper trees
- Hypothesis: depth 4 lost `0.0048` AUC relative to depth 6. Depth 8 may capture useful interactions among airport, carrier, and schedule features that the current trees cannot express.
- Category: follow-up to the depth comparison.
- Research: the [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) describes depth as a complexity control with a bias/variance tradeoff; this tests whether the current setting is on the underfit side.
- Planned change: `max_depth=8` only; keep all other settings fixed.
- Outcome: Eval AUC `0.7343` (`ok`, 34.6s), slightly below the best; the artifact grew from about 7.5 MB to 25.5 MB. Discarded commit `c3c50b5` and returned to depth 6.

## Experiment 7 plan — allow smaller child nodes
- Hypothesis: rare airport/carrier combinations may need smaller leaf partitions. Lowering `min_child_weight` from its default 1 to 0.5 can allow those splits while retaining depth 6.
- Category: follow-up hyperparameter exploration on the kept model.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `min_child_weight` as the minimum Hessian sum in a child and says larger values make the model more conservative.
- Planned change: set `min_child_weight=0.5` only.
- Outcome: Eval AUC `0.7336` (`ok`, 33.1s), below the best; discarded commit `e923dc4` and restored the baseline regularization.

## Experiment 8 plan — explicit route category
- Hypothesis: separate `Origin` and `Dest` features do not directly identify a route. An `Origin-Dest` category may expose route-specific delay patterns and interactions to the trees.
- Category: exploration — new categorical feature.
- Research: an [airline departure-delay study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) discusses historical delay averages by route and flight number. XGBoost's [categorical data tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) documents pandas `category` inputs with `enable_categorical=True`.
- Planned change: derive each row's route from `Origin` and `Dest`, fit the route category list once from `train`, and look it up inside `prepare(df)`. Unseen routes map to missing. No target statistics or row counts are used.
- Outcome: Eval AUC `0.7086` (`ok`, 51.6s); the artifact expanded to 50.9 MB. The explicit route category hurt substantially, so discarded commit `2d9f0ea` and restored the best model.

## Experiment 9 plan — finer boosting steps
- Hypothesis: the 300-tree, 0.05 model improved AUC substantially over the starter. Doubling rounds and halving the learning rate to 600 and 0.025 tests whether smaller sequential updates produce a better ranking at comparable total step scale.
- Category: follow-up to the strongest result.
- Research: the [XGBoost parameter tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends increasing boosting rounds when reducing `eta`.
- Planned change: set `n_estimators=600`, `learning_rate=0.025`; hold the other features and parameters fixed.
- Outcome: Eval AUC `0.7344` (`ok`, 35.0s), slightly below the best; the artifact doubled to 15.2 MB. Discarded commit `ed0c63f` and restored 300 trees at 0.05.

## Experiment 10 plan — halve the winning tree count
- Hypothesis: if 150 trees at learning rate 0.05 retains nearly all of the `0.7348` AUC, it would be a simpler and smaller model than the 300-tree winner. A clear loss would confirm the extra rounds are useful.
- Category: ablation/simplification of the winning model.
- Research: the [XGBoost parameter tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) frames boosting rounds and learning rate as a bias/variance tradeoff.
- Planned change: reduce `n_estimators` from 300 to 150; keep learning rate 0.05 and all other settings fixed.
- Outcome: Eval AUC `0.7304` (`ok`, 32.4s), `0.0044` below the best; discarded commit `20fbbf3` and restored 300 trees.

## Synthesis after 10 experiments
- Best kept result: AUC `0.7348`, commit `1455db4` (300 trees, learning rate 0.05, depth 6), up `0.0145` from baseline.
- What helped: increasing rounds while lowering the learning rate from the starter settings produced the clear gain.
- What did not: depth 4 and 8, row subsampling, lower `min_child_weight`, cyclical departure-time features, the raw route category, and 600 trees at 0.025 all failed to beat the best. Halving the winning tree count lost `0.0044` AUC.
- Current theory: the starter's 30 rounds were the main limitation. The existing airport, carrier, schedule and distance features already carry useful signal; adding a high-cardinality route category without a stronger prior is noisy, and depth 6 appears adequate.
- Next direction: investigate leakage-safe training-set group delay-rate encodings (for broader groups such as carrier and airport), with leave-one-out training values and fixed train-fitted lookups at scoring time. Avoid exposing raw group counts.

## Experiment 11 plan — smoothed group delay-rate features
- Hypothesis: native categories let XGBoost partition airports and airlines, but explicit shrunk delay-rate estimates may give the trees useful broad priors from those groups. Use only `UniqueCarrier`, `Origin`, and `Dest`; the sparse route category already hurt.
- Category: exploration — target-statistic feature engineering.
- Research: scikit-learn's [TargetEncoder reference](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html) describes shrinking category means toward the global mean and recommends cross-fitting to prevent leakage. The [CatBoost paper](https://proceedings.neurips.cc/paper/2018/hash/14491b756b3a51daac41c24863285549-Abstract.html) analyzes target leakage in categorical statistics. The experiment will use leave-one-out values only to build training features (no model validation or cross-validation), and full train-fitted group lookups at scoring time.
- Planned change: fit group positive-label sums and sizes on `train` for carrier, origin, and destination. In `prepare(train)`, subtract each row's own label before applying an `alpha=50` shrinkage toward the train-wide prior; after fitting features, switch to full lookup values for eval rows. Counts are used only to form the smoothed rate, never emitted as columns. Unknown groups fall back to the global prior.
- Outcome: Eval AUC `0.6052` (`ok`, 45.0s). The fixed train lookups and leave-one-out training features ran within limits, but the rates transferred poorly to eval; discarded commit `759afa7` and restored the best model.

## Experiment 12 plan — finer histogram bins
- Hypothesis: the winning model has only two numeric inputs (`CRSDepTime` and `Distance`). Doubling the histogram resolution may allow more useful split thresholds on these features without changing tree depth or boosting rounds.
- Category: follow-up hyperparameter exploration, split resolution.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says `max_bin` controls the number of histogram bins and that increasing it can improve split optimality at higher computation cost. It also documents `auto` as equivalent to `hist`, so the parameter applies here.
- Planned change: set `max_bin=512` only.
- Outcome: Eval AUC `0.7342` (`ok`, 33.7s), slightly below the best; discarded commit `81e159f` and restored default binning.

## Experiment 13 plan — treat scheduled hour as categorical
- Hypothesis: the cyclical numeric features were roughly level with the winner, but the model may benefit from learning hourly blocks without imposing an ordinal split order. A 24-level categorical hour isolates that representation while retaining raw `CRSDepTime`.
- Category: follow-up feature ablation on departure time.
- Research: scikit-learn's [time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) notes hour is a discrete 24-value feature that can be treated categorically. XGBoost's [categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) documents native pandas categorical splits; a [flight-delay feature study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) highlights hourly departure-time blocks as relevant.
- Planned change: derive `ScheduledDepHour` from each row's `CRSDepTime`, with allowed levels fitted once on `train`; add it as a pandas categorical feature. No statistics are computed from the input frame.
- Outcome: Eval AUC `0.7348` (`ok`, 37.1s), tied with the best to four decimals but added a feature and increased evaluation time; discarded commit `39284e0` under the simplicity criterion.

## Experiment 14 plan — replace raw time with hour category
- Hypothesis: the hour category alone matched the best score when added to raw time. Removing raw `CRSDepTime` now tests whether its finer HHMM value adds useful signal beyond the hour groups; a near-tie with one fewer input would be simpler.
- Category: ablation/simplification of Experiment 13.
- Research: the [scikit-learn time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) discusses discrete hour levels as categorical values, and XGBoost's [categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) documents the native splits used here.
- Planned change: remove `CRSDepTime` from the model's numerical columns and retain only the train-level categorical hour derived from it; keep `Distance` and all model settings.
- Outcome: Eval AUC `0.7336` (`ok`, 36.6s), `0.0012` below the best; removing raw `CRSDepTime` lost useful signal, so discarded commit `a9a04db` and restored the full-time model.

## Experiment 15 plan — mild column sampling
- Hypothesis: row subsampling at 0.8 hurt, but sampling features per tree is a different source of variation. With only eight input columns, a mild 0.9 ratio may add tree diversity while retaining most candidate features.
- Category: follow-up regularization experiment.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `colsample_bytree` as the fraction of features sampled for each tree; the [tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) discusses randomness as a way to control overfitting.
- Planned change: set `colsample_bytree=0.9` only.
- Outcome: Eval AUC `0.7352` (`ok`, 33.0s), a new best by `0.0004`; artifact size was 7.2 MB. Kept commit `d02ebef`.

## Experiment 16 plan — strengthen column sampling
- Hypothesis: `colsample_bytree=0.9` improved AUC slightly. Testing 0.8 checks whether a stronger but still mild amount of per-tree feature diversity gives a further gain; this differs from row subsampling, which samples examples rather than predictors.
- Category: follow-up to the promising Experiment 15.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) specifies that `colsample_bytree` independently samples features for each tree.
- Planned change: lower `colsample_bytree` from 0.9 to 0.8; retain all else.
- Outcome: Eval AUC `0.7371` (`ok`, 32.9s), improving Experiment 15 by `0.0019`; artifact size fell to 6.9 MB. Kept commit `0068857` as the new best.

## Experiment 17 plan — continue the column-sampling trend
- Hypothesis: the tested ratios improved from 0.9 to 0.8. A 0.7 ratio may add further useful diversity across the eight existing features; each tree still sees most predictors.
- Category: follow-up to the improving Experiment 15–16 sequence.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines the ratio as per-tree feature sampling.
- Planned change: lower `colsample_bytree` from 0.8 to 0.7 only.
- Outcome: Eval AUC `0.7386` (`ok`, 32.9s), improving the 0.8 ratio by `0.0015`; artifact size was 6.4 MB. Kept commit `54f89a2` as the new best.

## Experiment 18 plan — sample fewer features per tree
- Hypothesis: column sampling has improved at every tested step from 0.9 through 0.7. Continue one step to 0.6 to test whether the trend holds when each tree sees roughly five of the eight input columns.
- Category: follow-up to the promising column-sampling sequence.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines per-tree sampling and notes that column sampling ratios combine multiplicatively with other `colsample_by*` settings; only `colsample_bytree` is varied here.
- Planned change: lower `colsample_bytree` from 0.7 to 0.6.
- Outcome: Eval AUC `0.7404` (`ok`, 33.1s), improving the 0.7 ratio by `0.0018`; artifact size was 6.1 MB. Kept commit `fa3a42b` as the new best.

## Experiment 19 plan — test half of the features per tree
- Hypothesis: reducing `colsample_bytree` has improved AUC at each tested ratio from 0.9 to 0.6. A ratio of 0.5 tests whether this remains helpful when each tree uses about four of the eight predictors.
- Category: follow-up to the improving column-sampling sequence.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines the fraction as a per-tree setting.
- Planned change: set `colsample_bytree=0.5` only.
- Outcome: Eval AUC `0.7404` (`ok`, 33.1s), tied with the 0.6 ratio to four decimals, with the same artifact size and run time; discarded commit `ee4e826` and restored 0.6.

## Experiment 20 plan — test aggressive column sampling
- Hypothesis: ratios 0.6 and 0.5 tied at the best score. A 0.4 ratio checks whether still more feature diversity helps or whether limiting each tree to roughly three of eight inputs removes too much signal.
- Category: follow-up to the promising column-sampling sequence.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) documents per-tree column sampling; this tests a clearly stronger sampling regime than the previous runs.
- Planned change: set `colsample_bytree=0.4` only.
- Outcome: Eval AUC `0.7397` (`ok`, 33.3s), below the 0.6 best; discarded commit `6ab2b01` and restored `colsample_bytree=0.6`.

## Synthesis after 20 experiments
- Best kept result: AUC `0.7404`, commit `fa3a42b` (300 trees, learning rate 0.05, depth 6, `colsample_bytree=0.6`), up `0.0201` from baseline.
- Strongest result so far: per-tree feature sampling. AUC improved monotonically from ratios 0.9 (`0.7352`) to 0.6 (`0.7404`); 0.5 tied, while 0.4 slipped to `0.7397`. This points to useful regularization from feature diversity, with a likely plateau near one-half of the columns.
- Other findings: 30 rounds underfit; 300 at 0.05 was substantially better, while 150 and 600 rounds were worse. Depth 6 beat 4 and 8. Row subsampling, larger histogram bins, cyclical/hour features, route categories, and the leave-one-out group-rate features failed to improve the best score.
- Current theory: this small feature set benefits from limiting which predictors compete within each tree; explicit feature additions and deeper trees mainly add noise or cost.
- Next direction: research a different tree-level regularization method, then test whether dropout during boosting complements the successful column sampling.

## Experiment 21 plan — DART tree dropout
- Hypothesis: the best result came from randomizing which features each tree sees. DART also removes existing trees while fitting each new tree, which may reduce over-specialization and complement `colsample_bytree=0.6`.
- Category: exploration — alternate boosting regularization.
- Research: the [XGBoost DART guide](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) describes dropout as a way to address overfitting and uses `rate_drop` to control it. The original [DART paper](https://arxiv.org/abs/1505.01866) motivates tree dropout as a remedy for over-specialization in boosted trees.
- Planned change: switch to `booster="dart"` with `rate_drop=0.1`; retain the best tree count, learning rate, depth, and 0.6 column-sampling ratio.
- Outcome: no AUC; the run hit `timeout-training` at 60s and was logged as a crash. The log also reported that `booster="dart"` is deprecated in installed XGBoost 3.4.1. Discarded commit `ab25271` and restored the best `gbtree` model.

## Experiment 22 plan — retry dropout with the current API
- Hypothesis: the 0.1 DART run timed out after 60s using the deprecated `booster="dart"` alias. XGBoost's current parameter reference says to use the default tree booster directly with dropout parameters; a lower 0.05 rate may retain some tree dropout while reducing training overhead enough to finish.
- Category: follow-up/fix to Experiment 21's timeout.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says dropout parameters such as `rate_drop` can be used with tree boosters; the [DART guide](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) notes dropout can slow training.
- Planned change: keep the default `gbtree` booster and add `rate_drop=0.05`; keep the winning 300-tree, depth-6, 0.6-column-sampling settings.
- Outcome: no AUC; the current `rate_drop=0.05` API also hit `timeout-training` at 60s. Logged as a crash and discarded commit `808598d`. Tree dropout is too slow for this experiment's training limit, so this direction is closed.

## Experiment 23 plan — one-hot splits for small categories
- Hypothesis: month and day-of-week have few levels and may benefit from category-versus-rest splits instead of partitioning levels together. Raising `max_cat_to_onehot` to 16 should change the split strategy for those low-cardinality fields while leaving larger fields partitioned.
- Category: exploration — native categorical split strategy.
- Research: XGBoost's [categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains one-hot versus partition-based splits; its [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `max_cat_to_onehot` as the threshold selecting between them.
- Planned change: set `max_cat_to_onehot=16`; keep the model, features, and `colsample_bytree=0.6` unchanged.
- Outcome: Eval AUC `0.7388` (`ok`, 32.9s), below the 0.6 column-sampling best; discarded commit `8e87e41` and restored the default categorical split threshold.

## Experiment 24 plan — isolate weekday one-hot splits
- Hypothesis: threshold 16 changed the split strategy for both month (12 levels) and day-of-week (7 levels), and possibly any other small field. Threshold 8 should isolate one-hot splits for the seven-level weekday field while leaving month partitioned; this tests whether the loss came from month rather than weekday.
- Category: follow-up ablation of Experiment 23's categorical split strategy.
- Research: XGBoost's [categorical parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says categories below `max_cat_to_onehot` use one-hot splits and larger categories use partitioning.
- Planned change: set `max_cat_to_onehot=8` only.
- Outcome: Eval AUC `0.7401` (`ok`, 33.3s), slightly below the best; discarded commit `9245181` and restored XGBoost's default categorical threshold.

## Experiment 25 plan — sample features at each level
- Hypothesis: per-tree feature sampling improved AUC through 0.6. Adding a moderate 0.8 `colsample_bylevel` ratio may create further diversity between levels while keeping the successful per-tree ratio fixed.
- Category: follow-up to the promising column-sampling result.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `colsample_bylevel` as per-level feature sampling and notes that `colsample_by*` ratios work cumulatively.
- Planned change: add `colsample_bylevel=0.8`; retain `colsample_bytree=0.6` and all other settings.
- Outcome: Eval AUC `0.7412` (`ok`, 33.3s), improving the 0.6 per-tree model by `0.0008`; artifact size was 5.9 MB. Kept commit `8945086` as the new best.

## Experiment 26 plan — strengthen level sampling
- Hypothesis: adding `colsample_bylevel=0.8` improved the per-tree-only best. Lowering it to 0.7 tests whether slightly stronger diversity across levels helps, while keeping `colsample_bytree=0.6` fixed.
- Category: follow-up to the promising nested column-sampling result.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says `colsample_by*` ratios combine cumulatively, so this changes the effective features available at each depth.
- Planned change: reduce `colsample_bylevel` from 0.8 to 0.7 only.
- Outcome: Eval AUC `0.7414` (`ok`, 33.3s), a small improvement over 0.8 per-level sampling; artifact size was 5.5 MB. Kept commit `5717a13` as the new best.

## Experiment 27 plan — continue level sampling
- Hypothesis: per-level sampling improved from 0.8 to 0.7. Test 0.6 to see whether more level-to-level variation helps further, accepting that the cumulative ratio leaves fewer candidates at each level.
- Category: follow-up to the improving nested column-sampling sequence.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) states that per-tree and per-level sampling ratios combine multiplicatively.
- Planned change: lower `colsample_bylevel` from 0.7 to 0.6; keep `colsample_bytree=0.6`.
- Outcome: Eval AUC `0.7414` (`ok`, 33.6s), tied with the 0.7 per-level ratio to four decimals; artifact size was unchanged. Discarded commit `62faab0` and restored 0.7.

## Experiment 28 plan — suppress weak splits
- Hypothesis: nested column sampling is the strongest regularization result. Requiring a small positive loss reduction before adding a split may remove weak branches that remain after sampling and improve generalization.
- Category: follow-up regularization experiment.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `gamma` as the minimum loss reduction required for another split; larger values make the model more conservative.
- Planned change: set `gamma=0.1` only, retaining the best sampling ratios.
- Outcome: Eval AUC `0.7416` (`ok`, 33.1s), a small improvement over the 0.7 per-level model; artifact size remained 5.5 MB. Kept commit `9b67a6d` as the new best.

## Experiment 29 plan — increase the split-loss threshold
- Hypothesis: `gamma=0.1` improved AUC slightly. A value of 1.0 tests whether a stronger penalty on low-gain splits compounds that gain or becomes too conservative.
- Category: follow-up to the promising Experiment 28.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says larger `gamma` requires greater loss reduction before adding a split.
- Planned change: increase `gamma` from 0.1 to 1.0 only.
- Outcome: Eval AUC `0.7387` (`ok`, 33.3s), below the `gamma=0.1` best; discarded commit `f5e3d13` and restored 0.1.

## Experiment 30 plan — bracket the split-loss threshold
- Hypothesis: `gamma=0.1` slightly improved AUC, while `gamma=1.0` reduced it. A moderate `gamma=0.3` tests whether the useful threshold lies between those settings.
- Category: follow-up to the `gamma` comparison.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `gamma` as the minimum loss reduction for a split and notes that larger values make trees more conservative.
- Planned change: set `gamma=0.3` only; retain the winning column-sampling ratios.
- Outcome: Eval AUC `0.7417` (`ok`, 33.3s), a small new best; artifact size was 5.4 MB. Kept commit `08a8d02`.

## Synthesis after 30 experiments
- Best kept result: AUC `0.7417`, commit `08a8d02` (300 trees, learning rate 0.05, depth 6, `colsample_bytree=0.6`, `colsample_bylevel=0.7`, `gamma=0.3`), up `0.0214` from baseline.
- Main gains: more boosting rounds at a lower learning rate produced the initial jump; per-tree column sampling from 0.9 to 0.6 produced the largest later gain; per-level sampling at 0.7 and a small split-loss threshold improved the best again.
- Stable settings: depth 6 and 300 rounds remain strong. Depth 4/8, 150/600 rounds, row sampling, added time/route features, target-rate features, finer bins, and one-hot categorical thresholds did not beat the best. DART timed out twice at the training limit.
- Current theory: this feature set benefits from more rounds and randomized predictor subsets, while modest split regularization removes weak interactions. Richer feature engineering and stronger regularization overfit or cost too much.
- Next direction: research node-level feature sampling as another way to add tree diversity, then test it on top of the current best if it fits the time limit.

## Experiment 31 plan — add node-level feature sampling
- Hypothesis: tree-level sampling at 0.6 and level-level sampling at 0.7 have both improved AUC. A mild `colsample_bynode=0.9` may add split-level diversity while preserving most of the current candidate features; the cumulative sampling ratio becomes 0.378.
- Category: follow-up to the promising nested column-sampling result.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `colsample_bynode` as the fraction of columns sampled for each node and says the `colsample_by*` ratios combine cumulatively. The [XGBoost random forest tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) also describes per-node column sampling.
- Planned change: add `colsample_bynode=0.9`; retain `colsample_bytree=0.6`, `colsample_bylevel=0.7`, and `gamma=0.3`.
- Outcome: Eval AUC `0.7343` (`ok`, 33.1s), below the 0.7417 best; artifact size fell from 5.4 MB to 3.7 MB. Discarded commit `707027c` and restored the best model. The additional node-level feature sampling removed too much useful capacity at this setting.

## Experiment 32 plan — modestly increase L2 leaf-weight regularization
- Hypothesis: the winning model combines column sampling with `gamma=0.3`. Raising the default L2 penalty from 1 to 2 may shrink noisy leaf weights and complement those controls without reducing the feature set further.
- Category: exploration — a new regularization parameter, informed by the small improvement from modest `gamma`.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says `reg_lambda` is L2 regularization on leaf weights and that increasing it makes the model more conservative.
- Planned change: set `reg_lambda=2.0` only; retain the 300-tree model, sampling ratios, and `gamma=0.3`.
- Outcome: Eval AUC `0.7418` (`ok`, 33.0s), a marginal improvement over the previous 0.7417 best; artifact size stayed 5.4 MB. Kept commit `9e4b5cf`.

## Experiment 33 plan — strengthen L2 leaf-weight regularization
- Hypothesis: `reg_lambda=2.0` produced a small gain. Increasing it to 4.0 tests whether stronger leaf-weight shrinkage gives a further improvement or makes this already sampled model too conservative.
- Category: follow-up to the small improvement from Experiment 32.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says larger `reg_lambda` makes the model more conservative.
- Planned change: raise `reg_lambda` from 2.0 to 4.0 only; leave the winning tree count, feature sampling, and `gamma` unchanged.
- Outcome: Eval AUC `0.7414` (`ok`, 33.2s), below the 0.7418 best; artifact size was 5.1 MB. Discarded commit `d289990` and restored `reg_lambda=2.0`.

## Experiment 34 plan — add a small L1 leaf-weight penalty
- Hypothesis: `reg_lambda=2.0` gave a marginal gain, while 4.0 was too conservative. A small L1 penalty may suppress weak leaf weights through sparsity while retaining the current L2 and split controls.
- Category: exploration — a distinct leaf-weight regularizer.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `reg_alpha` as L1 regularization on weights and says increasing it makes the model more conservative.
- Planned change: add `reg_alpha=0.1`; retain `reg_lambda=2.0` and all other settings.
- Outcome: Eval AUC `0.7419` (`ok`, 32.9s), a new best by `0.0001`; artifact size stayed 5.4 MB. Kept commit `dbec724`.

## Experiment 35 plan — increase L1 leaf-weight penalty
- Hypothesis: `reg_alpha=0.1` gave a small gain. Raising it to 0.5 tests whether a stronger sparse-weight effect helps further or becomes too restrictive.
- Category: follow-up to the promising L1 result.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `reg_alpha` as L1 regularization on weights; larger values make the model more conservative.
- Planned change: increase `reg_alpha` from 0.1 to 0.5 only, holding `reg_lambda=2.0` fixed.
- Outcome: Eval AUC `0.7420` (`ok`, 33.2s), a new best; artifact size increased slightly to 5.6 MB. Kept commit `2f4ac8d`.

## Experiment 36 plan — test stronger L1 leaf-weight penalty
- Hypothesis: increasing `reg_alpha` from 0.1 to 0.5 improved AUC slightly. Raising it to 1.0 tests whether the gain continues or stronger shrinkage removes useful leaf weights.
- Category: follow-up to the improving L1 sequence.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says larger L1 penalty makes the model more conservative.
- Planned change: increase `reg_alpha` from 0.5 to 1.0 only; retain `reg_lambda=2.0` and all other settings.
- Outcome: Eval AUC `0.7418` (`ok`, 33.2s), below the 0.7420 best; artifact size returned to 5.4 MB. Discarded commit `2a85514` and restored `reg_alpha=0.5`.

## Experiment 37 plan — cap categories considered in partition splits
- Hypothesis: airport categorical splits may benefit from a stricter cap on candidate categories. This tests partition-split complexity separately from the earlier `max_cat_to_onehot` experiments, which changed one-hot versus partition strategy.
- Category: exploration — categorical split regularization.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says `max_cat_threshold` limits the number of categories considered per split and is used by partition-based splits to prevent overfitting. The [categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) describes how categorical partition splits work.
- Planned change: set `max_cat_threshold=32` only; keep the winning `reg_lambda=2.0` and `reg_alpha=0.5` settings.
- Outcome: Eval AUC `0.7411` (`ok`, 33.5s), below the 0.7420 best; artifact size was 5.3 MB. Discarded commit `068c5bf`. The 32-category cap appears too restrictive in this configuration.

## Experiment 38 plan — allow more categorical split candidates
- Hypothesis: `max_cat_threshold=32` reduced AUC, suggesting the cap may have removed useful partition options. A value of 128 tests whether considering more categories improves airport-category splits.
- Category: follow-up bracket to Experiment 37's categorical split cap.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines this as the maximum number of categories considered for each partition-based split.
- Planned change: set `max_cat_threshold=128` only; retain the best `reg_lambda=2.0` and `reg_alpha=0.5` configuration.
- Outcome: Eval AUC `0.7415` (`ok`, 33.1s), below the 0.7420 best; artifact size was 5.4 MB. Discarded commit `dab0a42`. A higher categorical split cap also failed to recover the best score.

## Experiment 39 plan — grow nodes by loss reduction
- Hypothesis: the current depthwise policy expands nodes closest to the root. Loss-guided growth prioritizes whichever eligible node has the largest loss change and may allocate depth more usefully under the same depth limit.
- Category: exploration — alternate tree-growth policy.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `grow_policy="depthwise"` as splitting closest to the root and `grow_policy="lossguide"` as splitting nodes with the highest loss change; it supports these policies with histogram or approximate tree methods.
- Planned change: set `grow_policy="lossguide"` only, retaining `max_depth=6` and all winning regularization and sampling settings.
- Outcome: Eval AUC `0.7420` (`ok`, 33.8s), tied with the best at displayed precision; artifact was 5.6 MB. Discarded commit `0e83b3b` because it added a parameter without improving AUC or simplifying the code.

## Experiment 40 plan — require more Hessian weight in child nodes
- Hypothesis: the earlier `min_child_weight=0.5` run on the less-regularized model lost AUC. Testing 2.0 on the current best examines whether a stronger child threshold complements column sampling, `gamma=0.3`, and leaf-weight regularization by preventing weak splits.
- Category: exploration — tree-complexity regularization.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `min_child_weight` as the minimum sum of instance Hessians in a child and says larger values make the algorithm more conservative.
- Planned change: set `min_child_weight=2.0` only; retain the current winning tree count, feature sampling, and weight penalties.
- Outcome: Eval AUC `0.7420` (`ok`, 33.2s), tied with the best at displayed precision; artifact was 5.4 MB. Discarded commit `b14d999`, since the change neither improved AUC nor simplified the model.

## Synthesis after 40 experiments
- Best kept result: AUC `0.7420`, commit `2f4ac8d`, up `0.0217` from the 0.7203 baseline. It uses 300 trees, learning rate 0.05, depth 6, `colsample_bytree=0.6`, `colsample_bylevel=0.7`, `gamma=0.3`, `reg_lambda=2.0`, and `reg_alpha=0.5`.
- Recent gains were small but consistent when adding moderate leaf-weight shrinkage: L2=2.0 reached 0.7418; L1=0.1 and 0.5 reached 0.7419 and 0.7420. Stronger L2=4.0 and L1=1.0 fell back.
- Tree/node and categorical-split experiments did not improve the best: node sampling at 0.9 scored 0.7343; category caps 32 and 128 scored 0.7411 and 0.7415; loss-guided growth and `min_child_weight=2.0` tied at 0.7420 and were discarded as unnecessary complexity.
- Current theory: this small tabular feature set responds best to moderate boosting with tree/level feature sampling, a small split threshold, and modest L1/L2 leaf regularization. The remaining opportunity may be encoding useful flight-time structure more directly, since earlier hour/cyclical feature attempts were made before finding the current model settings.
- Next direction: research flight-delay timing features and test a focused time-of-day representation on top of the current best.

## Experiment 41 plan — encode scheduled departure time as minutes and a cycle
- Hypothesis: prior hour/category and cyclical-feature experiments were run before the current regularized model and retained or substituted a raw HHMM value. HHMM has uneven numeric gaps (for example, the boundary between 09:59 and 10:00) and a day-boundary discontinuity. Replacing it with minutes since midnight plus sine/cosine features may preserve ordering and capture wraparound.
- Category: follow-up feature engineering based on the 40-run synthesis and flight-delay literature.
- Research: the XGBoost study [“Revealing influence of meteorological conditions and flight factors on delays Using XGBoost”](https://doi.org/10.1016/j.jcmds.2022.100030) reports departure time as an influential factor. A peer-reviewed study on [probabilistic flight-delay prediction](https://www.mdpi.com/2226-4310/8/6/152) includes time of day among its departure-delay features.
- Planned change: remove raw `CRSDepTime` from numeric inputs; derive per-row minutes after midnight and its sine/cosine with a 24-hour period in `prepare(df)`. Keep `Distance`, categorical features, and winning model parameters unchanged.
- Outcome: Eval AUC `0.7410` (`ok`, 39.6s), below the 0.7420 best; artifact size was 6.0 MB. Discarded commit `a7124f0` and restored raw `CRSDepTime`. This time transformation did not help with the current model.

## Experiment 42 plan — refine the per-tree sampling ratio
- Hypothesis: `colsample_bytree=0.6` was the strongest setting in the earlier sweep, while 0.5 tied an earlier result before the later regularizers. Testing 0.55 narrows the interval around the current best to check for a better balance between feature diversity and split options.
- Category: follow-up parameter refinement.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `colsample_bytree` as the fraction of columns sampled when constructing each tree and notes that feature-sampling ratios combine cumulatively with level/node sampling.
- Planned change: reduce `colsample_bytree` from 0.6 to 0.55 only.
- Outcome: Eval AUC `0.7420` (`ok`, 33.4s), tied with the best at displayed precision; artifact size was 5.6 MB. Discarded commit `1802759` since it did not improve AUC or simplify the code.

## Experiment 43 plan — test the higher side of the per-tree sampling optimum
- Hypothesis: a 0.55 per-tree ratio tied the current 0.6 best. Raising the ratio to 0.65 checks whether retaining slightly more features helps now that L1 and L2 regularization have been added.
- Category: follow-up parameter refinement around the best sampling ratio.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines per-tree column sampling and its cumulative interaction with per-level sampling.
- Planned change: increase `colsample_bytree` from 0.6 to 0.65 only.
- Outcome: Eval AUC `0.7425` (`ok`, 33.5s), a new best by `0.0005`; artifact size was 6.2 MB. Kept commit `229a148`.

## Experiment 44 plan — continue the per-tree sampling sweep
- Hypothesis: increasing the per-tree sampling ratio from 0.6 to 0.65 improved the regularized model. A ratio of 0.7 tests whether allowing still more features to compete at tree level helps.
- Category: follow-up to the improving per-tree sampling setting.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `colsample_bytree` and its cumulative interaction with `colsample_bylevel`.
- Planned change: increase `colsample_bytree` from 0.65 to 0.7 only.
- Outcome: Eval AUC `0.7425` (`ok`, 33.2s), tied with the 0.65 best; artifact size was 6.2 MB. Discarded commit `d624185`, retaining the smaller per-tree sampling setting.

## Experiment 45 plan — ease per-level feature sampling slightly
- Hypothesis: the 0.65 per-tree ratio improved AUC, while 0.7 tied at the tree-level sweep's high side. Raising `colsample_bylevel` from 0.7 to 0.75 tests whether more feature availability at each level complements the new per-tree setting.
- Category: follow-up to the improved per-tree sampling result.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `colsample_bylevel` as the fraction sampled at each depth and says feature-sampling ratios combine cumulatively.
- Planned change: set `colsample_bylevel=0.75` only; retain `colsample_bytree=0.65`.
- Outcome: Eval AUC `0.7425` (`ok`, 33.2s), tied with the best at displayed precision; artifact size was 6.2 MB. Discarded commit `a00aeb8` and restored the 0.7 per-level setting.

## Experiment 46 plan — add one level of tree depth
- Hypothesis: depth 6 beat both depth 4 and depth 8 in the earlier sweep. Testing depth 7 on the current regularized model checks whether the L1/L2 and split penalties permit a small increase in interaction depth.
- Category: follow-up to the previously best depth setting.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `max_depth` as the maximum depth and warns that increasing it makes trees more complex and more likely to overfit.
- Planned change: increase `max_depth` from 6 to 7 only; keep all other best settings fixed.
- Outcome: Eval AUC `0.7462` (`ok`, 33.7s), a large new best by `0.0037`; artifact size rose to 11.5 MB. Kept commit `11d2952` because the score gain is material.

## Experiment 47 plan — test another level of tree depth
- Hypothesis: depth 7 materially improved the current model, despite an earlier depth-8 run losing under weaker regularization. Testing depth 8 now checks whether the tuned column and weight penalties continue to control overfitting at greater interaction depth.
- Category: follow-up to the strong depth-7 gain.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `max_depth` as maximum tree depth and notes that deeper trees increase complexity and overfit risk.
- Planned change: increase `max_depth` from 7 to 8 only; retain all other settings.
- Outcome: Eval AUC `0.7479` (`ok`, 34.3s), a further improvement of `0.0017`; artifact size grew to 20.3 MB. Kept commit `3230961`.

## Experiment 48 plan — continue the increasing-depth sequence
- Hypothesis: raising depth from 6 to 7 and then 8 improved AUC under the tuned feature and leaf regularization. Testing depth 9 checks whether another level captures useful interactions before overfitting or model size becomes costly.
- Category: follow-up to the consistent depth gains.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) warns that deeper trees increase complexity and overfit risk.
- Planned change: increase `max_depth` from 8 to 9 only; retain all other best settings.
- Outcome: Eval AUC `0.7502` (`ok`, 35.4s), a further gain of `0.0023`; training took 4.0s and artifact size grew to 35.3 MB. Kept commit `e0c4be1`.

## Experiment 49 plan — extend the depth sweep
- Hypothesis: depth 7, 8, and 9 improved sequentially under the tuned sampling and leaf penalties. Testing depth 10 checks whether deeper interactions still generalize or the increasing complexity begins to overfit.
- Category: follow-up to the consistent depth improvements.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) warns that deeper trees are more complex and more likely to overfit.
- Planned change: increase `max_depth` from 9 to 10 only.
- Outcome: Eval AUC `0.7488` (`ok`, 35.9s), below the depth-9 best; training took 4.8s and artifact size rose to 59.7 MB. Discarded commit `d50e718` and restored depth 9.

## Synthesis after 50 experiments
- Best kept result: AUC `0.7502`, commit `e0c4be1`, up `0.0299` from the 0.7203 baseline. It uses 300 trees, learning rate 0.05, depth 9, `colsample_bytree=0.65`, `colsample_bylevel=0.7`, `gamma=0.3`, `reg_lambda=2.0`, and `reg_alpha=0.5`.
- Increasing depth under the tuned sampling and leaf penalties was the strongest recent direction: depth 7 scored 0.7462, depth 8 0.7479, and depth 9 0.7502. Depth 10 fell to 0.7488 and nearly doubled the artifact from depth 9 to 59.7 MB, locating a useful stopping point.
- Per-tree sampling 0.65 improved the earlier best by 0.0005; 0.55, 0.7, and per-level 0.75 tied at displayed precision. Keep the simpler 0.65/0.7 pair.
- Time encodings, node sampling, categorical thresholds, loss-guided growth, and stronger `min_child_weight` did not improve the best. Moderate L1/L2 regularization made the deeper trees productive.
- Current theory: the model needed more interaction depth once column sampling and leaf-weight penalties controlled the added capacity. Depth 9 balances useful interactions and artifact size better than depth 10.
- Next direction: research the interaction between tree count/learning rate and the newly deeper trees; test whether fewer rounds preserve AUC while reducing model size, or whether a different shrinkage level improves it.

## Experiment 51 plan — reduce the number of deeper trees
- Hypothesis: depth 9 greatly increased per-tree capacity and AUC at 300 estimators. Reducing to 250 may retain most of the gain with a smaller ensemble and less opportunity to overfit. An earlier 150-tree run lost under shallower, less-regularized settings, so this checks the interaction with the current model.
- Category: exploration — tree count with the newly deeper structure.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes learning-rate shrinkage per boosting step; the [parameter-tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) notes that tree count and step size interact.
- Planned change: reduce `n_estimators` from 300 to 250 only; keep learning rate 0.05 and depth 9.
- Outcome: Eval AUC `0.7502` (`ok`, 34.3s), tied with the best at displayed precision; training fell to 3.6s and artifact size to 30.6 MB from 35.3 MB. Kept commit `ccb4580` as the simpler equivalent model.

## Experiment 52 plan — further reduce the depth-9 ensemble
- Hypothesis: reducing 300 estimators to 250 preserved AUC and reduced artifact size. A 200-tree model tests whether this simplification can go further while retaining the deeper trees' gain.
- Category: follow-up to the equal-score smaller model.
- Research: the [XGBoost parameter-tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) notes that the number of boosting rounds interacts with step size and model fit.
- Planned change: reduce `n_estimators` from 250 to 200 only; retain `learning_rate=0.05` and depth 9.
- Outcome: Eval AUC `0.7497` (`ok`, 33.8s), down `0.0005`; training took 3.1s and artifact size fell to 25.1 MB. Discarded commit `0c3819b` to retain the 250-tree higher-scoring model.

## Experiment 53 plan — locate the tree-count knee
- Hypothesis: 250 trees tied the 300-tree AUC, while 200 trees lost 0.0005. Testing 225 narrows the interval to see if fewer than 250 trees preserve the best AUC and reduce artifact size.
- Category: follow-up to the promising smaller ensemble.
- Research: the [XGBoost parameter-tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) describes the interaction between learning-rate step size and the number of boosting rounds.
- Planned change: set `n_estimators=225` only, keeping learning rate 0.05 and depth 9.
- Outcome: Eval AUC `0.7502` (`ok`, 34.2s), tied with the best at displayed precision; training took 3.3s and artifact size fell to 27.9 MB from 30.6 MB. Kept commit `25df0cd` as the simpler equivalent model.

## Experiment 54 plan — reduce the tree count toward the AUC knee
- Hypothesis: 225 trees retained the best AUC, while 200 trees lost 0.0005. Testing 215 narrows the useful boundary and may reduce artifact size further without changing AUC.
- Category: follow-up tree-count refinement.
- Research: the [XGBoost parameter-tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) describes the interaction between learning-rate step size and number of boosting rounds.
- Planned change: set `n_estimators=215` only; keep all other settings fixed.
- Outcome: Eval AUC `0.7501` (`ok`, 34.2s), within `0.0001` of the best; training took 3.3s and artifact size fell to 26.8 MB. Kept commit `4c43a6b` as a simpler near-equivalent model.

## Experiment 55 plan — reduce the ensemble slightly further
- Hypothesis: 215 trees remained within 0.0001 of the best at smaller model size. Testing 210 checks whether another small reduction preserves the near-best AUC.
- Category: follow-up to the smaller depth-9 ensemble.
- Research: the [XGBoost parameter-tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) notes the interaction between boosting-round count and learning rate.
- Planned change: set `n_estimators=210` only.
- Outcome: Eval AUC `0.7503` (`ok`, 34.0s), a new best; training took 3.2s and artifact size fell to 26.1 MB. Kept commit `6eba65f`.

## Experiment 56 plan — refine the minimum-round boundary
- Hypothesis: 210 trees improved AUC over 215 and 200 trees lost 0.0005. Testing 205 narrows the transition point and may preserve the new best with a smaller model.
- Category: follow-up tree-count refinement.
- Research: the [XGBoost parameter-tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) notes the interaction between boosting rounds and learning rate.
- Planned change: set `n_estimators=205` only.
- Outcome: Eval AUC `0.7502` (`ok`, 34.1s), within `0.0001` of the 0.7503 best; training took 3.1s and artifact size fell to 25.5 MB. Kept commit `bab4665` as a smaller near-equivalent model.

## Experiment 57 plan — probe just below 205 trees
- Hypothesis: 205 trees kept AUC within 0.0001 of the 210-tree best at smaller size. Testing 202 checks whether that score holds with a few fewer rounds before the drop seen at 200.
- Category: follow-up tree-count refinement.
- Research: the [XGBoost parameter-tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) discusses the interaction between rounds and step size.
- Planned change: reduce `n_estimators` from 205 to 202 only.
- Outcome: Eval AUC `0.7498` (`ok`, 34.0s), down 0.0004 from the retained 205-tree setting; training took 3.1s and artifact size was 25.3 MB. Discarded commit `9d9f420`; stop reducing the tree count below 205.

## Experiment 58 plan — pair a smaller learning step with more rounds
- Hypothesis: the depth-9 model's 205-tree score is near the best. A slightly smaller learning rate with more rounds may improve generalization; 230 × 0.045 gives a cumulative step-size product close to 205 × 0.05 while taking smaller individual steps.
- Category: exploration — learning-rate/tree-count interaction.
- Research: the [XGBoost parameter-tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) says reducing `eta` makes updates more conservative and should be paired with more boosting rounds.
- Planned change: set `n_estimators=230` and `learning_rate=0.045` as a paired change; retain the depth-9 sampling and regularization settings.
- Outcome: Eval AUC `0.7499` (`ok`, 34.4s), below the 0.7502 best; training took 3.5s and artifact size was 29.0 MB. Discarded commit `ce6e38a` and restored 205 trees at learning rate 0.05.

## Experiment 59 plan — lower the split-loss threshold for deep trees
- Hypothesis: `gamma=0.1` was nearly tied with `gamma=0.3` at depth 6. Deeper trees now win under stronger feature and leaf-weight regularization; lowering gamma may let them use additional informative splits.
- Category: follow-up to the deeper-tree gain and earlier gamma comparison.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `gamma` as the minimum loss reduction required for a split; smaller values allow more splits.
- Planned change: reduce `gamma` from 0.3 to 0.1 only.
- Outcome: Eval AUC `0.7496` (`ok`, 34.3s), below the 0.7502 depth-9 best; training took 3.1s and artifact size was 25.6 MB. Discarded commit `5bcbff1` and restored `gamma=0.3`.

## Experiment 60 plan — use the approximate tree method
- Hypothesis: the current plateau persisted across count, learning-rate, and split-threshold refinements. `approx` uses weighted sketching to build split candidates rather than the default histogram method and may expose useful thresholds for the deeper model.
- Category: exploration — alternate split-construction algorithm.
- Research: the [XGBoost tree-method guide](https://xgboost.readthedocs.io/en/stable/treemethod.html) describes `approx` as sketch-based split construction. The [categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) lists `approx` and `hist` as supported methods for categorical features; the [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says `auto` is equivalent to `hist`.
- Planned change: set `tree_method="approx"` only; retain 205 estimators, depth 9, and all best sampling and regularization settings.
- Outcome: Eval AUC `0.7499` (`ok`, 37.6s), below the 0.7502 depth-9 best; training took 6.5s and artifact size was 24.9 MB. Discarded commit `da23158`; the alternate split method ran slower without improving AUC.

## Synthesis after 60 experiments
- Highest observed AUC: `0.7503`, commit `6eba65f` (210 trees, depth 9, learning rate 0.05, `colsample_bytree=0.65`, `colsample_bylevel=0.7`, `gamma=0.3`, `reg_lambda=2.0`, `reg_alpha=0.5`), up `0.0300` from baseline. The current branch is at commit `bab4665`, 205 trees and AUC `0.7502`, a near-equal score with a smaller 25.5 MB artifact.
- Depth 9 was the strongest structure: 7→8→9 improved 0.7462→0.7479→0.7502; depth 10 dropped to 0.7488 and grew the artifact to 59.7 MB.
- Tree-count refinements found 205–225 rounds near the best. 210 reached the top observed score; 205 and 225 were within 0.0001, while 202 and 200 lost 0.0004–0.0005. A paired 230-tree, 0.045 learning-rate run fell to 0.7499.
- Gamma 0.1 and the `approx` tree method did not help the depth-9 model. Recent runs now suggest a plateau around 0.75 AUC.
- Current theory: feature subsampling plus moderate L1/L2 penalties make higher depth useful, but capacity beyond depth 9 overfits; there may still be room to regulate tree shape without losing deep interactions.
- Next direction: research leaf-limited growth with `max_leaves` and `lossguide`, then test whether selective, capped growth can retain the depth-9 gain with controlled complexity.

## Experiment 61 plan — cap loss-guided trees at 256 leaves
- Hypothesis: the 205-tree, depth-9 model improved AUC but large depth-10 trees overfit. Loss-guided growth prioritizes the nodes with the largest loss change; capping each tree at 256 leaves while retaining `max_depth=9` may concentrate capacity and limit model size.
- Category: exploration — leaf-limited tree growth.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `lossguide` as splitting nodes with the highest loss change and `max_leaves` as the leaf cap. The [Python API reference](https://xgboost.readthedocs.io/en/stable/python/python_api.html) states that 0 means no leaf limit.
- Planned change: add `grow_policy="lossguide"` and `max_leaves=256`; retain `max_depth=9` and all other current settings.
- Outcome: Eval AUC `0.7494` (`ok`, 35.7s), below the 0.7502 retained best; training took 4.7s and artifact size fell to 16.9 MB. Discarded commit `e5ab8be`; the 256-leaf cap was too restrictive for the current score target.

## Experiment 62 plan — relax the loss-guided leaf cap
- Hypothesis: a 256-leaf cap reduced AUC by 0.0008. Raising it to 384 may restore split capacity while still restricting the largest depth-9 trees, which can reach 512 leaves.
- Category: follow-up to the leaf-limited growth experiment.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `max_leaves` as a cap and `lossguide` as prioritizing nodes by loss change.
- Planned change: use `grow_policy="lossguide"` with `max_leaves=384`; retain `max_depth=9` and all other settings.
- Outcome: Eval AUC `0.7503` (`ok`, 36.3s), matching the highest observed score; training took 5.4s and artifact size was 22.9 MB, smaller than the 25.5 MB current branch. Kept commit `0b85c54` as an equal-score, smaller-model result.

## Experiment 63 plan — reduce the leaf cap while preserving the top score
- Hypothesis: a 384-leaf loss-guided cap matched the highest AUC, while 256 leaves lost 0.0008. Testing 320 narrows the range and may further reduce model size without losing the score.
- Category: follow-up to the promising leaf-limited growth setting.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `max_leaves` as the per-tree leaf limit.
- Planned change: reduce `max_leaves` from 384 to 320 only; keep loss-guided growth and depth 9.
- Outcome: Eval AUC `0.7502` (`ok`, 35.9s), within `0.0001` of the highest observed score; training took 5.1s and artifact size fell to 20.1 MB from 22.9 MB. Kept commit `cae42d9` as the smaller near-equivalent model.

## Experiment 64 plan — tighten the leaf cap again
- Hypothesis: 320 leaves retained AUC within 0.0001 of the top result. Testing 288 may reduce the model further while preserving the same near-best score; the 256-leaf run provides a lower comparison point.
- Category: follow-up to the useful leaf-limited growth setting.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `max_leaves` as the leaf limit under the tree method.
- Planned change: reduce `max_leaves` from 320 to 288 only.
- Outcome: Eval AUC `0.7496` (`ok`, 35.9s), down `0.0006` from the 320-leaf result; training took 5.0s and artifact size was 18.6 MB. Discarded commit `90e3dc7` and restored 320 leaves.

## Experiment 65 plan — refine the minimum useful leaf count
- Hypothesis: 320 leaves stayed within 0.0001 of the top score, while 288 lost 0.0006. Testing 304 narrows the boundary and may retain near-best AUC at lower size.
- Category: follow-up leaf-cap refinement.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `max_leaves` as the maximum number of leaves.
- Planned change: set `max_leaves=304` only.
- Outcome: Eval AUC `0.7493` (`ok`, 35.9s), below the 0.7502 result at 320 leaves; training took 5.0s and artifact size was 19.5 MB. Discarded commit `8f3d9ea` and restored 320 leaves.

## Experiment 66 plan — test an intermediate leaf cap above 320
- Hypothesis: 320 leaves stayed within 0.0001 of the top, 384 reached the top score, while 304 dropped sharply. Testing 352 checks whether a somewhat larger cap recovers 0.7503 without the full 384-leaf size.
- Category: follow-up to the best leaf-limited growth setting.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `max_leaves` as the maximum leaf count.
- Planned change: increase `max_leaves` from 320 to 352 only.
- Outcome: Eval AUC `0.7492` (`ok`, 36.0s), below both the 320- and 384-leaf results; training took 5.2s and artifact size was 21.3 MB. Discarded commit `130ea0a` and restored the 320-leaf branch.

## Experiment 67 plan — test a 400-leaf loss-guided cap
- Hypothesis: 384 leaves matched the highest AUC, while 320 was within 0.0001 and smaller. Testing 400 checks whether a little more split capacity improves beyond the current 0.7503 peak.
- Category: follow-up to the promising 384-leaf setting.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `max_leaves` as the maximum number of leaves per tree.
- Planned change: increase `max_leaves` from 320 to 400 only.
- Outcome: Eval AUC `0.7500` (`ok`, 36.3s), below the 0.7502 result at 320 leaves and the 0.7503 result at 384; training took 5.5s and artifact size was 23.5 MB. Discarded commit `b4394b4` and restored 320 leaves.

## Experiment 68 plan — retune tree count under the leaf cap
- Hypothesis: 210 trees gave the highest AUC in the depthwise model, while 205 trees with a 320-leaf loss-guided cap retained a near-best score. Increasing the capped model to 210 checks whether the previous tree-count optimum transfers.
- Category: follow-up to the leaf-capped model.
- Research: the [XGBoost parameter-tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) notes that boosting-round count and step size interact.
- Planned change: set `n_estimators=210` only; keep `max_leaves=320` and all other settings.
- Outcome: Eval AUC `0.7503` (`ok`, 36.1s), matching the highest observed score; training took 5.2s and artifact size was 20.6 MB, smaller than the 22.9 MB 384-leaf model. Kept commit `b2529d9` as the best score/size combination.

## Experiment 69 plan — narrow the cap below 320 leaves
- Hypothesis: with 210 trees, a 320-leaf cap reached the top observed AUC. Testing 312 checks whether a slightly smaller cap preserves that score and reduces artifact size.
- Category: follow-up to the successful tree-count/leaf-cap combination.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `max_leaves` as the maximum leaf count.
- Planned change: reduce `max_leaves` from 320 to 312 only.
- Outcome: Eval AUC `0.7493` (`ok`, 36.2s), below the 0.7503 result at 320 leaves; training took 5.2s and artifact size was 20.4 MB. Discarded commit `9441405` and restored 320 leaves.

## Experiment 70 plan — add five rounds to the capped model
- Hypothesis: 210 trees at 320 leaves matched the top observed AUC. Testing 215 checks whether a few more rounds improve on that result while keeping the compact leaf cap.
- Category: follow-up to the best leaf-capped model.
- Research: the [XGBoost parameter-tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) describes boosting-round and learning-rate interactions.
- Planned change: set `n_estimators=215` only; retain the 320-leaf cap and all other parameters.
- Outcome: Eval AUC `0.7503` (`ok`, 36.3s), tied with 210 trees; training took 5.3s and artifact size grew to 21.1 MB. Discarded commit `6712b94` and restored the smaller 210-tree model.

## Synthesis after 70 experiments
- Highest and current best: AUC `0.7503`, commit `b2529d9`, up `0.0300` from the 0.7203 baseline. It uses 210 trees, depth 9, learning rate 0.05, `colsample_bytree=0.65`, `colsample_bylevel=0.7`, `gamma=0.3`, `reg_lambda=2.0`, `reg_alpha=0.5`, loss-guided growth, and `max_leaves=320`; artifact size was 20.6 MB.
- Loss-guided, leaf-capped growth retained the top score with a smaller model than depthwise growth. 384 leaves at 205 trees also scored 0.7503 but produced a 22.9 MB artifact; 320 leaves at 210 trees was smaller and matched it.
- The leaf-cap response was irregular: 256/288/304/312/352/400 scored 0.7492–0.7500, while 320 and 384 reached 0.7502–0.7503. Keep 320/210 as the best size/score balance.
- The count sweep around the cap found 205, 210, and 215 all within 0.0001 at display precision; 210 had the smallest artifact among these at top AUC.
- Current theory: deeper interactions are valuable when model growth is directed by gain and bounded at a leaf count; small changes around that structural boundary can alter categorical splits sharply.
- Next direction: test whether a coarser histogram bin count regularizes the numeric splits in this deep, leaf-capped model.

## Experiment 71 plan — reduce numeric histogram resolution
- Hypothesis: the deep leaf-capped model may overfit numeric split thresholds. Lowering `max_bin` from the default 256 to 128 reduces candidate thresholds and may act as additional regularization; a previous 512-bin run on the shallow model did not help.
- Category: exploration — histogram split resolution.
- Research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `max_bin` as the maximum number of discrete bins for continuous features and notes that more bins improve split optimality at higher computation cost.
- Planned change: add `max_bin=128` only; retain the 210-tree, depth-9, 320-leaf model and other settings.
- Outcome: Eval AUC `0.7493` (`ok`, 35.7s), down `0.0010` from the 0.7503 best; training took 5.0s and artifact size was 20.8 MB. Discarded commit `0e76664` and restored the 256-bin default.

## Final summary
- Best kept commit: `b2529d9`, Eval AUC `0.7503` (+0.0300 over baseline `92e43e6`, 0.7203). Configuration: 210 trees, learning rate 0.05, depth 9, per-tree sampling 0.65, per-level sampling 0.7, `gamma=0.3`, `reg_lambda=2.0`, `reg_alpha=0.5`, loss-guided growth capped at 320 leaves. Artifact size was 20.6 MB.
- What worked: moderate column sampling and L1/L2 leaf penalties made deeper trees productive; depth 9 substantially outperformed depth 6. Loss-guided growth with a 320-leaf cap and 210 rounds matched the highest observed AUC while keeping the artifact smaller than the uncapped deep model.
- What did not: extra time encodings, route/target-rate features, row subsampling, DART, categorical-threshold changes, lower `gamma`, `approx` tree construction, and coarse `max_bin=128` did not improve the best. Depth 10 overfit and increased model size sharply; overly low leaf caps lost AUC.
- With more time: refine `max_leaves` around 320 with the selected 210-round model and test a midpoint histogram resolution between 128 and 256.
