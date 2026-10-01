# Research log

## Baseline — 92e43e6

- Ran the unchanged starter model: 30 trees, depth 6, learning rate 0.1, native categorical columns.
- Eval AUC: 0.7203; run status: ok; run time: 31.1s.
- This is the reference score for the `oct1` run.

## Initial research

- XGBoost's [parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommend controlling tree complexity with parameters such as `max_depth`, `min_child_weight`, and `gamma`, and using row/column sampling to add randomness. They also suggest reducing the learning rate while increasing boosting rounds.
- The [categorical data tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) describes native categorical splits and the `max_cat_to_onehot` threshold between one-hot-like and partition-based categorical splits.
- The available features make time-of-day transforms and train-fitted route/airport context plausible later directions. Any lookup features must be fit on train only and remain fixed per row during `prepare`; target-based features need leakage-safe construction.

## Experiment 1 hypothesis

Follow-up to the baseline. Increase the ensemble from 30 to 200 trees and reduce the learning rate from 0.1 to 0.05, leaving depth and the feature representation fixed. The baseline may be limited by too few boosting steps; smaller steps with more rounds are a standard way to refine the additive fit. Keep the change only if eval AUC improves enough to justify the extra training cost.

## Experiment 1 — cc04906

- Follow-up: increased `n_estimators` from 30 to 200 and lowered `learning_rate` from 0.1 to 0.05; kept depth and features fixed.
- Eval AUC: 0.7325 (up 0.0122 from baseline); run status: ok; run time: 33.1s.
- Decision: keep. This supports the hypothesis that the starter's 30 rounds were too few for a smaller update size.

## Experiment 2 hypothesis

Exploration: test whether an explicit scheduled departure-hour category helps alongside the raw `CRSDepTime` value. The current HHMM integer imposes a numeric split order; a category lets the model group hours by their learned signal while retaining the fine-grained raw value. XGBoost supports native categorical splits ([categorical data tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html)). Scikit-learn's [time-related feature engineering example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) discusses discrete time-step categories as one representation, though its benchmark is bike demand and much of its encoding comparison uses linear models. A [flight-delay feature-engineering project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) reports time-of-day differences, including elevated delays late at night, on a different and newer dataset. This motivates a small, train-fitted hour category; it does not guarantee a gain here.

Add only `DepHour`, derived row-wise as `CRSDepTime // 100`, with category levels fitted on `train`. Keep model settings and other features unchanged.

## Experiment 2 — c845268

- Exploration: added a `DepHour` categorical feature derived from `CRSDepTime // 100`, with levels fitted from train; retained raw scheduled time and all previous settings.
- Eval AUC: 0.7319 (0.0006 below the best kept score); run status: ok; run time: 37.4s.
- Decision: discard and return to cc04906. The extra feature did not improve this model on the eval split.

## Experiment 3 hypothesis

Follow-up to the best model cc04906. Raise `max_depth` from 6 to 8 while keeping 200 trees, learning rate 0.05, and features fixed. Deeper trees may capture interactions among carrier, airports, schedule, and distance that the current trees cannot express. XGBoost's [tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) warn that increasing tree complexity can overfit, so the eval result will determine whether the extra depth is useful.

## Experiment 3 — 4100a47

- Follow-up: increased `max_depth` from 6 to 8; kept the 200-tree, 0.05 learning-rate model and features fixed.
- Eval AUC: 0.7331 (up 0.0006 from the best kept score); run status: ok; run time: 34.0s.
- Decision: keep. The modest gain suggests some additional tree capacity is useful.

## Experiment 4 hypothesis

Follow-up to the depth-8 improvement. Keep `max_depth=8` and increase `min_child_weight` from its default 1 to 10. This requires more Hessian mass before splitting a child and should suppress fragile small leaves in the deeper trees. XGBoost's [parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) describe larger `min_child_weight` as a more conservative setting. This tests whether regularized depth-8 trees retain or improve the AUC gain.

## Experiment 4 — 4135243

- Follow-up: set `min_child_weight=10` at depth 8; kept all other settings and features fixed.
- Eval AUC: 0.7327 (0.0004 below the best kept score); run status: ok; run time: 33.4s.
- Decision: discard and return to 4100a47. This regularization setting reduced the eval AUC slightly.

## Experiment 5 hypothesis

Exploration of stochastic regularization. Set `subsample=0.8` on the depth-8 best model while holding every other setting fixed. Sampling 80% of rows for each tree may reduce variance and improve generalization after the deeper-tree gain. XGBoost's [parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommend row sampling as one way to add randomness and control overfitting.

## Experiment 5 — 49a7750

- Exploration: set `subsample=0.8` at depth 8; all other settings and features stayed fixed.
- Eval AUC: 0.7307 (0.0024 below the best kept score); run status: ok; run time: 33.8s.
- Decision: discard and return to 4100a47. Row sampling hurt on this eval split.

## Experiment 6 hypothesis

Exploration: add a train-leveled directional `Route` category (`Origin-Dest`) while retaining both airport columns and all current settings. A route may have a relationship with delay risk that separate origin and destination splits require multiple tree levels to express. This is an inference, not a result established for this dataset. A U.S. flight-delay study uses origin and destination as pre-departure categorical features ([feature table in the paper](https://engj.org/index.php/ej/article/download/4376/1156)); a more recent project also reports geographic and network context as useful flight feature families ([UC Berkeley project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches)). XGBoost's [categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains how category values can be grouped through partition-based splits. Composite routes may be sparse, so this is a single-feature experiment with a clear eval-based keep/discard decision.

`Route` will be derived from each row, with the allowed category levels fitted once from train. No route counts or target aggregates are added.

## Experiment 6 — a1e9cd0

- Exploration: added a train-leveled categorical `Route` made from `Origin-Dest`; retained both airport columns and the depth-8 model.
- Eval AUC: 0.7068 (0.0263 below the best kept score); run status: ok; run time: 52.5s, including 47.5s evaluation.
- Decision: discard and return to 4100a47. The composite route category substantially hurt AUC and increased the row-by-row preparation cost, consistent with sparse high-cardinality routes being a poor fit in this setup.

## Experiment 7 hypothesis

Follow-up to the best model 4100a47. Increase `n_estimators` from 200 to 400 while holding the learning rate at 0.05, depth 8, and all features fixed. Since going from 30 to 200 trees improved AUC substantially, more boosting rounds may continue to improve the fit; this tests for diminishing returns or overfitting without changing the step size.

## Experiment 7 — 389a42a

- Follow-up: increased `n_estimators` from 200 to 400 at learning rate 0.05, depth 8, and the same features.
- Eval AUC: 0.7336 (up 0.0005 from the best kept score); run status: ok; run time: 35.3s.
- Decision: keep. The small positive gain motivates one more direct check of the round count.

## Experiment 8 hypothesis

Follow-up to the 400-tree improvement. Increase `n_estimators` from 400 to 800 while holding the learning rate at 0.05, depth at 8, and features fixed. The earlier increase from 200 to 400 helped slightly; another doubling tests whether additional rounds continue to refine ranking or begin to overfit.

## Experiment 8 — 99336d9

- Follow-up: increased `n_estimators` from 400 to 800 at learning rate 0.05 and depth 8.
- Eval AUC: 0.7309 (0.0027 below the best kept score); run status: ok; run time: 39.5s.
- Decision: discard and return to 389a42a. Doubling rounds at the same step size appears to overfit this eval split.

## Experiment 9 hypothesis

Follow-up to the 800-tree overfit. Set `n_estimators=800` and `learning_rate=0.025`, keeping depth 8 and features fixed. The product of rounds and learning rate is close to the kept 400-tree, 0.05 setting, but the smaller per-tree updates may yield a smoother fit and avoid the regression from 800 trees at 0.05. This follows XGBoost's guidance to pair smaller steps with more rounds.

## Experiment 9 — 97033e4

- Follow-up: increased rounds to 800 and lowered learning rate to 0.025, keeping depth 8 and the same features.
- Eval AUC: 0.7347 (up 0.0011 from the previous best); run status: ok; run time: 40.9s.
- Decision: keep. Smaller steps with more rounds recovered the regression from 800 rounds at 0.05 and improved the score.

## Synthesis after the first 10 runs

The best score is now 0.7347 at commit 97033e4. The baseline was 0.7203. The strongest gains so far came from replacing the 30-tree starter with more rounds at a smaller learning rate, then increasing depth from 6 to 8. Increasing rounds from 200 to 400 at 0.05 added a small gain; doubling to 800 at 0.05 hurt, while 800 at 0.025 improved the score. This suggests the useful capacity depends on taking smaller steps as rounds increase.

The explicit scheduled-hour category was slightly worse, and the high-cardinality route category sharply reduced AUC while slowing row-wise preparation. `min_child_weight=10` and `subsample=0.8` also reduced AUC. The current best theory is that this feature set benefits from a more expressive, carefully shrunk booster; sparse composite categories and heavier regularization have not helped.

For the next direction, recent XGBoost tuning research supports testing `gamma`: the [parameter guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) lists it among tree-complexity controls, and the [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines it as the minimum loss reduction required for another split. This is distinct from `min_child_weight`; try a moderate positive value at the current best settings to see whether pruning weak splits improves generalization.

## Experiment 10 hypothesis

Follow-up to the best model 97033e4. Set `gamma=1.0`, keeping 800 trees, learning rate 0.025, depth 8, and the feature set fixed. The positive split threshold should prune weak partitions and may reduce overfitting while retaining strong airport/carrier/time splits. Keep only if eval AUC improves.

## Experiment 10 — e956267

- Follow-up: added `gamma=1.0` to the best 800-tree, 0.025 learning-rate model at depth 8.
- Eval AUC: 0.7342 (0.0005 below the best kept score); run status: ok; run time: 36.1s.
- Decision: discard and return to 97033e4. This split threshold was slightly too conservative for the best model.

## Experiment 11 hypothesis

Exploration of feature sampling. Set `colsample_bytree=0.8` on 97033e4 while keeping `subsample=1.0` and all other settings fixed. This varies the feature subset used for each tree, which may reduce tree correlation without dropping training examples; it differs from the unsuccessful row-sampling trial. XGBoost's [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `colsample_bytree` as the fraction of columns sampled per tree and its [tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) list it as a randomness-based overfitting control.

## Experiment 11 — f053bbd

- Exploration: set `colsample_bytree=0.8` with row `subsample=1.0` at the best 800-tree, 0.025, depth-8 settings.
- Eval AUC: 0.7423 (up 0.0076 from the best kept score); run status: ok; run time: 39.4s.
- Decision: keep. Feature sampling produced the largest improvement so far, suggesting that the full set of features at every split allowed correlated trees to overfit.

## Experiment 12 hypothesis

Follow-up to the colsample improvement. Lower `colsample_bytree` from 0.8 to 0.7 while keeping rows, rounds, learning rate, depth, and features fixed. If slightly stronger per-tree feature randomness helps, this may improve diversity further; the risk is leaving too few of the eight input features for some trees.

## Experiment 12 — 2e73448

- Follow-up: lowered `colsample_bytree` from 0.8 to 0.7 at the 800-tree, 0.025, depth-8 settings.
- Eval AUC: 0.7456 (up 0.0033 from the best kept score); run status: ok; run time: 38.7s.
- Decision: keep. Stronger feature sampling improved the score again.

## Experiment 13 hypothesis

Follow-up to the gains at `colsample_bytree=0.8` and 0.7. Lower it to 0.6 while keeping all other settings fixed. Another improvement would suggest stronger per-tree feature randomness is still useful; the downside is that trees may omit too many useful columns.

## Experiment 13 — 8d6638a

- Follow-up: lowered `colsample_bytree` from 0.7 to 0.6 with all other settings fixed.
- Eval AUC: 0.7489 (up 0.0033 from the best kept score); run status: ok; run time: 39.0s.
- Decision: keep. The score improved again with stronger column sampling.

## Experiment 14 hypothesis

Follow-up to the consistent gains from colsample 0.8, 0.7, and 0.6. Lower `colsample_bytree` to 0.5, leaving the rest fixed. This tests whether the same regularization trend continues; with eight input columns, it will make each tree much less feature-rich and could now underfit.

## Experiment 14 — c698671

- Follow-up: lowered `colsample_bytree` from 0.6 to 0.5.
- Eval AUC: 0.7489 (tied the best score to four decimals); run status: ok; run time: 39.3s.
- Decision: keep. Each tree sees a smaller feature subset at the same reported AUC, so this is a simpler, more regularized setting.

## Experiment 15 hypothesis

Continue the improving/tied column-sampling trend by lowering `colsample_bytree` from 0.5 to 0.4. Keep the 800-tree, 0.025 learning-rate, depth-8 model unchanged otherwise. This tests the boundary where extra randomness may start to underfit, since each tree will see only about three of the eight inputs.

## Experiment 15 — da70770

- Follow-up: lowered `colsample_bytree` from 0.5 to 0.4.
- Eval AUC: 0.7480 (0.0009 below the best kept score); run status: ok; run time: 38.5s.
- Decision: discard and return to c698671. At 0.4, the stronger feature sampling began to underfit.

## Experiment 16 hypothesis

Follow-up to both the depth-8 gain and the colsample 0.5 gain. Raise `max_depth` from 8 to 10 with `colsample_bytree=0.5`, keeping rounds, learning rate, and rows fixed. The smaller feature subset regularizes each tree, which may allow more depth to express useful interactions without the same overfit risk as depth 10 with all columns. XGBoost's tuning guide warns that deeper trees add complexity, so this is an explicit eval-gated test.

## Experiment 16 — 8c50c03

- Follow-up: increased `max_depth` from 8 to 10 while using `colsample_bytree=0.5`.
- Eval AUC: 0.7486 (0.0003 below the best kept score); run status: ok; run time: 44.3s.
- Decision: discard and return to c698671. The extra depth did not improve AUC.

## Experiment 17 hypothesis

Ablation/simplification of c698671. Reduce `max_depth` from 8 to 6 at `colsample_bytree=0.5`, keeping rounds, learning rate, and features fixed. The stronger column sampling may provide enough regularization that depth 8 is no longer needed. If AUC is about equal, the shallower trees would be a useful simplification; otherwise retain depth 8.

## Experiment 17 — a8e9c6b

- Ablation: reduced `max_depth` from 8 to 6 at `colsample_bytree=0.5`.
- Eval AUC: 0.7429 (0.0060 below the best kept score); run status: ok; run time: 36.2s.
- Decision: discard and return to c698671. Depth 8 remains useful even with stronger feature sampling.

## Experiment 18 hypothesis

Exploration of categorical split strategy. Set `max_cat_to_onehot=13` on c698671, keeping all other settings fixed. This should use one-hot-style splits for the 7-level weekday and 12-level month features while leaving the higher-cardinality day-of-month, carrier, origin, and destination features partitioned. XGBoost's [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines this as the category-count threshold for choosing one-hot versus partition-based splits; the [categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains that partition-based splits group categories by their learned output. Testing a higher threshold checks whether these calendar features benefit from individual category splits instead of grouped partitions.

## Experiment 18 — 88ca92a

- Exploration: raised `max_cat_to_onehot` to 13, switching the calendar categories to one-hot-style categorical splits while leaving higher-cardinality features partitioned.
- Eval AUC: 0.7453 (0.0036 below the best kept score); run status: ok; run time: 38.5s.
- Decision: discard and return to c698671. Partition-based splits performed better for these features in this setup.

## Experiment 19 hypothesis

Follow-up to the 800-tree, 0.025 model with `colsample_bytree=0.5`. Increase `n_estimators` to 1200 while holding learning rate, depth, and all other settings fixed. The stronger feature sampling may provide enough regularization for additional boosting rounds to help; this tests whether the 800-round result was still underfit or already near its optimum.

## Experiment 19 — b58d8b3

- Follow-up: increased rounds from 800 to 1200 at learning rate 0.025 and `colsample_bytree=0.5`.
- Eval AUC: 0.7478 (0.0011 below the best kept score); run status: ok; run time: 42.6s.
- Decision: discard and return to c698671. The ensemble already peaked near 800 rounds.

## Synthesis after the first 20 runs

The best result is 0.7489 at c698671, up 0.0286 from the 0.7203 baseline. The kept model has 800 trees, learning rate 0.025, depth 8, and `colsample_bytree=0.5`. The major improvement came from reducing the fraction of columns each tree sees: 0.8 scored 0.7423, 0.7 scored 0.7456, 0.6 scored 0.7489, and 0.5 tied at 0.7489; 0.4 fell to 0.7480. Keeping 0.5 gives the same reported score with fewer candidate features per tree.

Round count matters with learning rate: 800 trees at 0.05 hurt, while 800 at 0.025 improved; 1200 at 0.025 was slightly worse than 800. Depth 8 beat depth 6, while depth 10 did not help. Row subsampling, `min_child_weight=10`, `gamma=1`, and a higher categorical one-hot threshold all hurt. The explicit hour category was slightly worse, and the composite route category was strongly worse and slower.

The strongest current theory is that the starter's useful signals are already represented by its individual features, but full-feature trees overfit. Moderate column sampling improves diversity, while more trees and depth help only within a suitable learning-rate range. High-cardinality interactions have not generalized well.

## Research at the 20-run pause

A TU Delft flight-delay thesis reports that a prior XGBoost flight-delay study represented scheduled departure time as sine and cosine of minutes within the day, to make midnight and end-of-day times adjacent ([thesis discussion](https://repository.tudelft.nl/file/File_dd877cbc-4b73-480c-ae5f-155c76b8e2e1)). The scikit-learn [time-related feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) describes the same continuity benefit for periodic time features, while showing that the result depends on the estimator. This supports testing the small transformation with the current XGBoost model rather than assuming it will help.

## Experiment 20 hypothesis

Exploration: add `DepTimeSin` and `DepTimeCos`, computed from `CRSDepTime` converted from HHMM into minutes after midnight. Retain raw `CRSDepTime` and all other features/settings, including `colsample_bytree=0.5`. The periodic pair may let the model recognize that late-night and early-morning departures are close across midnight. The transformation is row-wise and needs no train-fitted statistics. Keep it only if eval AUC improves.

## Experiment 20 — 1d15843

- Exploration: added sine and cosine of scheduled departure minutes within the day while retaining raw `CRSDepTime` and all prior settings.
- Eval AUC: 0.7491 (up 0.0002 from the best kept score); run status: ok; run time: 44.5s.
- Decision: keep. This is a small gain from a compact, row-wise transformation that encodes continuity across midnight.

## Experiment 21 hypothesis

Ablation of the raw scheduled-time input. Remove `CRSDepTime` from `num_cols` while retaining the derived `DepTimeSin` and `DepTimeCos` columns. If AUC stays about equal, the two periodic features can replace the raw HHMM value with a more coherent time representation and one fewer input feature; if it drops, retain raw time as complementary fine-grained signal.

## Experiment 21 — c0e00f4

- Ablation: removed raw `CRSDepTime` from model inputs while retaining `DepTimeSin` and `DepTimeCos`.
- Eval AUC: 0.7482 (0.0009 below the 0.7491 result); run status: ok; run time: 43.5s.
- Decision: keep as a near-equal simplification. The model uses one fewer input feature and keeps the more coherent periodic time representation.

## Experiment 22 hypothesis

Follow-up to the feature-set change. Raise `colsample_bytree` from 0.5 to 0.6 with the cyclical-only time representation. This adds more feature candidates per tree (the model now has nine inputs), which may help the model use both periodic time components alongside existing predictors. Keep rounds, learning rate, depth, and row sampling unchanged.

## Experiment 22 — 02ede7a

- Follow-up: raised `colsample_bytree` from 0.5 to 0.6 after replacing raw `CRSDepTime` with its cyclic pair.
- Eval AUC: 0.7461 (0.0021 below the best score for the simplified representation); run status: ok; run time: 44.2s.
- Decision: discard and return to c0e00f4. The 0.5 ratio remains better with the cyclic-only input set.

## Experiment 23 hypothesis

Exploration of node-level feature sampling. Add `colsample_bynode=0.8` on c0e00f4, retaining `colsample_bytree=0.5` and all other settings. This selects a further subset of the tree's sampled columns when evaluating each split, which may add useful local diversity after tree-level sampling produced the main gain. XGBoost's [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes the `colsample_by*` parameters as cumulative; the additional sampling may also remove too many of the useful features, so keep only if AUC improves.

## Experiment 23 — 59124d9

- Exploration: added `colsample_bynode=0.8` on top of `colsample_bytree=0.5` for the cyclical-only time features.
- Eval AUC: 0.7477 (0.0005 below the best simplified score); run status: ok; run time: 44.8s.
- Decision: discard and return to c0e00f4. Additional node-level sampling did not help.

## Experiment 24 hypothesis

Exploration: add `colsample_bylevel=0.8` to c0e00f4, retaining `colsample_bytree=0.5`. Unlike the unsuccessful per-node sampling trial, this samples a consistent feature set per tree level and may preserve useful structure among sibling splits while adding some randomness at depth. XGBoost documents the level and node variants as cumulative sampling controls ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)). The trial will show whether level-wise sampling complements the successful tree-wise setting.

## Experiment 24 — 86dfd86

- Exploration: added `colsample_bylevel=0.8` on top of `colsample_bytree=0.5` using the cyclical-only time representation.
- Eval AUC: 0.7491, up 0.0009 from the best simplified score and matching the highest score so far; run status: ok; run time: 44.1s.
- Decision: keep. Level-wise sampling complemented the tree-wise setting on this input representation.

## Experiment 25 hypothesis

Follow-up to the level-sampling gain. Lower `colsample_bylevel` from 0.8 to 0.6 while keeping `colsample_bytree=0.5` and all other settings fixed. If stronger level-wise randomness helps, AUC may improve further; the risk is that each split sees too few features.

## Experiment 25 — 34dafde

- Follow-up: lowered `colsample_bylevel` from 0.8 to 0.6 while retaining `colsample_bytree=0.5`.
- Eval AUC: 0.7471 (0.0020 below the best score); run status: ok; run time: 42.7s.
- Decision: discard and return to 86dfd86. More aggressive level-wise sampling reduced AUC.

## Experiment 26 hypothesis

Follow-up to the 0.8 level-sampling gain. Raise `colsample_bylevel` to 0.9 at `colsample_bytree=0.5`, with all remaining settings fixed. This is a milder per-level restriction than 0.8, testing whether the best result can be retained with slightly more candidate features at each depth.

## Experiment 26 — 09ec1ee

- Follow-up: raised `colsample_bylevel` from 0.8 to 0.9.
- Eval AUC: 0.7491, tied the best score to four decimals; run status: ok; run time: 43.0s.
- Decision: discard and return to 86dfd86. The 0.8 setting reaches the same score with more regularization.

## Experiment 27 hypothesis

Follow-up to the best boosting schedule under tree/level feature sampling. Set `n_estimators=1000` and `learning_rate=0.02`, keeping depth 8, `colsample_bytree=0.5`, `colsample_bylevel=0.8`, and the cyclical-only feature set fixed. This keeps the rounds-times-rate product close to the current 800-by-0.025 setting while using smaller per-tree updates, testing whether a finer boosting path improves AUC.

## Experiment 27 — fa88947

- Follow-up: used 1000 trees at learning rate 0.02, with the same depth and feature sampling as 86dfd86.
- Eval AUC: 0.7488 (0.0003 below the best score); run status: ok; run time: 45.0s.
- Decision: discard and return to 86dfd86. The finer, longer boosting schedule did not improve the result.

## Experiment 28 hypothesis

Ablation/simplification of the best boosting schedule. Try 600 trees at learning rate 0.03, keeping depth 8, tree-level sampling 0.5, level-wise sampling 0.8, and features fixed. The smaller ensemble may retain nearly all of the AUC while reducing model size and training time; if it loses more than a small amount, keep 800 trees at 0.025.

## Experiment 28 — 9847dec

- Ablation: reduced the ensemble to 600 trees and raised the learning rate to 0.03.
- Eval AUC: 0.7478 (0.0013 below the best score); run status: ok; run time: 41.9s.
- Decision: discard and return to 86dfd86. The smaller ensemble did not preserve the AUC gain.

## Experiment 29 hypothesis

Follow-up to the successful combined tree/level sampling model. Raise `colsample_bytree` from 0.5 to 0.6 while retaining `colsample_bylevel=0.8`. Earlier, tree sampling at 0.6 without level sampling hurt on the cyclical-only inputs. Adding level-wise sampling changes which columns survive at each depth and may make a slightly larger tree-level subset useful; this tests that interaction directly.

## Experiment 29 — b48f01b

- Follow-up: raised `colsample_bytree` to 0.6 while retaining `colsample_bylevel=0.8` on cyclical-only time inputs.
- Eval AUC: 0.7474 (0.0017 below the best score); run status: ok; run time: 43.5s.
- Decision: discard and return to 86dfd86. The interaction between higher tree-level sampling and level-wise sampling did not improve the result.

## Synthesis after the first 30 runs

The best AUC is 0.7491, up 0.0288 from the 0.7203 baseline. The best compact setup is at 86dfd86: 800 trees, learning rate 0.025, depth 8, `colsample_bytree=0.5`, `colsample_bylevel=0.8`, and cyclical departure time features in place of raw HHMM. Adding the departure-time sine/cosine pair produced a small gain; removing raw HHMM lost 0.0009, then level-wise column sampling recovered that difference. A higher level sample (0.9) tied but was less regularized; 0.6 reduced AUC. Additional node sampling, 600 or 1000 trees, and a higher tree-level sample did not improve the result.

The earlier pattern still holds: moderate column sampling is the strongest regularizer, depth 8 is useful, and the best round count is near 800 at a small learning rate. High-cardinality route, explicit hour category, and categorical one-hot strategy remain poor. The current model's original categorical month and weekday features still have no smooth periodic representation.

## Research at the 30-run pause

The official scikit-learn [time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) applies sine/cosine encodings to month (period 12) and weekday (period 7), and explains that a periodic pair removes the discontinuity between the last and first value. A flight-delay study using XGBoost reports that delay patterns differ by month and day of week ([IET paper](https://ietresearch.onlinelibrary.wiley.com/doi/abs/10.1049/itr2.12071)); its airport and region differ from this experiment, so the evidence motivates a test rather than a score expectation. The TU Delft flight-delay thesis also describes cyclic year/day encodings in prior flight-delay work ([thesis](https://repository.tudelft.nl/file/File_dd877cbc-4b73-480c-ae5f-155c76b8e2e1)).

## Experiment 30 hypothesis

Exploration: add `MonthSin`, `MonthCos`, `DayOfWeekSin`, and `DayOfWeekCos` as row-wise features, retaining the existing categorical columns and the current best model settings. These pairs may let trees model seasonal and weekly patterns smoothly across year/week boundaries, while the categorical versions retain their ability to express sharp individual month or weekday effects. Four features broaden the representation, so keep only if eval AUC improves.

- Initial attempt for Experiment 30 (commit 4f36c85) crashed before fitting: `Month` is read as a string, so the first sine/cosine calculation could not multiply it by a float. This is a straightforward input-type issue; parse the row values numerically and rerun the same feature experiment.

- Corrected rerun (commit 4a34cd3): parsed the month and weekday values numerically before applying sine/cosine transforms. Eval AUC was 0.7481 (0.0010 below the best), status ok, run time 52.1s. Decision: discard the four calendar-cycle features and return to 86dfd86; they did not improve over the categorical features.

## Research before Experiment 31

The scikit-learn `VotingClassifier` documentation defines soft voting as averaging each fitted classifier's predicted class probabilities ([official documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html)). XGBoost documents `random_state` as its random seed and `colsample_bytree` as the column-sampling ratio for each tree ([official Python API](https://xgboost.readthedocs.io/en/stable/python/python_api.html)). The current model samples columns at both tree and level scopes, so independently seeded copies can differ in their sampled feature subsets. I will test whether equal-weight probability averaging reduces seed-specific errors enough to improve AUC; three copies also triple model size and training, so the gain must justify that cost.

## Experiment 31 hypothesis

Exploration: fit three copies of the current best XGBoost model with seeds 42, 43, and 44, holding all features and hyperparameters fixed, then combine them with scikit-learn soft voting. Independent seeds change the sampled columns under the current tree and level sampling settings; averaging their class probabilities may smooth seed-specific prediction noise. Keep this only if the eval AUC gain is meaningful relative to the tripled model size and fit time.

## Experiment 31 — e4277f3

- Exploration: averaged predicted probabilities from three copies of the best model with seeds 42, 43, and 44; kept the feature set and all other model settings fixed.
- Eval AUC: 0.7491, tied the best single-model score; run status: ok; run time: 57.6s (training about 20s).
- Decision: discard and return to 86dfd86. The ensemble did not improve AUC and requires three models for prediction.

## Research before Experiment 32

The scikit-learn time-feature example recommends encoding periodic clock values with sine and cosine using the matching period ([official example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html)). Flight-delay research also includes scheduled arrival time as a predictor alongside departure time, airports, and other schedule information ([IET Intelligent Transport Systems paper](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057)). This supports testing the destination-local scheduled arrival clock separately from departure time, while keeping the current model configuration fixed.

## Experiment 32 hypothesis

Feature exploration: add sine and cosine of scheduled arrival time (`CRSArrTime`, one day = 1440 minutes) to the current departure-time cycles. Arrival clock may encode destination-local congestion patterns and complementary time-of-day effects. Retain the original categoricals and current departure cycles. Keep the additions only if eval AUC improves.

## Experiment 32 — 2504985

- Exploration: attempted to add cyclical scheduled arrival time features.
- The run crashed before fitting because `CRSArrTime` is not a column in the training data; run status: crash; run time: 0.9s.
- Decision: discard and return to 86dfd86. The hypothesized feature is unavailable in this dataset, so there is no code correction to apply.

## Research before Experiment 33

The official XGBoost parameter guide defines `reg_lambda` as L2 regularization on leaf weights and states that increasing it makes the model more conservative ([XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html)). The default is 1. Since the current best already benefits from column subsampling, I will test whether a moderately stronger L2 penalty complements that regularization.

## Experiment 33 hypothesis

Follow-up: increase `reg_lambda` from its default 1 to 5, holding the current features, tree depth, learning schedule, and column sampling fixed. A stronger L2 penalty may reduce overconfident leaf updates and improve generalization. Keep only if eval AUC improves.

## Experiment 33 — 3164ed2

- Follow-up: raised `reg_lambda` from the default 1 to 5 with all other settings fixed.
- Eval AUC: 0.7495, a new best (up 0.0004); run status: ok; run time: 43.4s.
- Decision: keep. Stronger leaf-weight regularization modestly improved the current best without adding features or prediction cost.

## Experiment 34 hypothesis

Follow-up to Experiment 33: raise `reg_lambda` from 5 to 10, with all other settings fixed. The increase to 5 improved eval AUC by 0.0004; a stronger L2 penalty may continue that trend, though excessive shrinkage could erase useful splits. Keep only if it beats 0.7495.

## Experiment 34 — 7386e7b

- Follow-up: raised `reg_lambda` from 5 to 10.
- Eval AUC: 0.7495, tied the best; run status: ok; run time: 43.8s.
- Decision: discard and return to 3164ed2. The stronger penalty did not improve on `reg_lambda=5`.

## Research before Experiment 35

The official XGBoost parameter guide also defines `reg_alpha` as L1 regularization on tree weights (default 0); like L2, increasing it makes the model more conservative ([XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html)). L2 at 5 improved the best model while increasing it to 10 tied, so I will test a moderate L1 penalty alongside the retained L2 value.

## Experiment 35 hypothesis

Follow-up regularization test: add `reg_alpha=0.5` to the kept `reg_lambda=5` model, holding all other settings fixed. L1 shrinkage may dampen weak leaf updates and complement the L2 gain. Keep only if eval AUC exceeds 0.7495.

## Experiment 35 — a08e305

- Follow-up: added `reg_alpha=0.5` while retaining `reg_lambda=5`.
- Eval AUC: 0.7504, a new best (up 0.0009); run status: ok; run time: 43.1s.
- Decision: keep. L1 regularization complemented the L2 gain and improved AUC without adding features or prediction cost.

## Experiment 36 hypothesis

Follow-up to the positive L1 result: increase `reg_alpha` from 0.5 to 1.0 while retaining `reg_lambda=5`. If the improvement came from pruning weak leaf updates, a somewhat stronger L1 penalty may help further; if it is already near the useful range, AUC may fall. Keep only if it beats 0.7504.

## Experiment 36 — f900bd1

- Follow-up: raised `reg_alpha` from 0.5 to 1.0, retaining `reg_lambda=5`.
- Eval AUC: 0.7516, a new best (up 0.0012); run status: ok; run time: 43.3s.
- Decision: keep. The stronger L1 setting continued the improvement.

## Experiment 37 hypothesis

Follow-up: raise `reg_alpha` from 1 to 2, preserving `reg_lambda=5` and all other settings. Two successive L1 increases improved AUC; test whether more shrinkage helps further before changing other dimensions. Keep only if it beats 0.7516.

## Experiment 37 — 015fbff

- Follow-up: raised `reg_alpha` from 1 to 2, retaining `reg_lambda=5`.
- Eval AUC: 0.7527, a new best (up 0.0011); run status: ok; run time: 43.1s.
- Decision: keep. Stronger L1 regularization continued improving eval AUC.

## Experiment 38 hypothesis

Follow-up to the continuing positive trend: raise `reg_alpha` from 2 to 4 with `reg_lambda=5` and all other settings unchanged. The doubled L1 values have improved sequentially, so test one more step on that path. Keep only if it beats 0.7527.

## Experiment 38 — 96b7d39

- Follow-up: raised `reg_alpha` from 2 to 4, retaining `reg_lambda=5`.
- Eval AUC: 0.7538, a new best (up 0.0011); run status: ok; run time: 42.3s. The artifact also shrank from about 41 MB to 34 MB.
- Decision: keep. L1 regularization has improved sequentially at 0.5, 1, 2, and 4.

## Experiment 39 hypothesis

Follow-up: increase `reg_alpha` from 4 to 8 while retaining `reg_lambda=5`. Each tested doubling improved eval AUC, so continue the geometric progression once more to locate where the gains level off. Keep only if it beats 0.7538.

## Experiment 39 — dacc195

- Follow-up: raised `reg_alpha` from 4 to 8, retaining `reg_lambda=5`.
- Eval AUC: 0.7531, 0.0007 below the best; run status: ok; run time: 42.2s.
- Decision: discard and return to 96b7d39. The doubling trend stopped; the useful L1 range is below 8.

## Research before Experiment 40

A 2025 UC Berkeley flight-delay project reports that delay rates vary by departure hour within each carrier, with late-night worsening consistent with delays compounding through the day ([project feature analysis](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches)). XGBoost's categorical-data guide explains that native categorical splits can partition categories into groups, rather than requiring numeric ordering ([official categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html)). This motivates one compact interaction category made from carrier and scheduled departure hour. It will use only fields in `train.csv`; unseen carrier-hour combinations at evaluation will be treated as missing.

## Experiment 40 hypothesis

Exploration: add a categorical `CarrierDepHour` feature combining `UniqueCarrier` and the hour parsed from `CRSDepTime`, with levels learned from training rows. Carrier-specific schedules may have different delay profiles by hour, and a single interaction category may let the model learn this with fewer sequential splits than separate carrier and time features. Keep only if eval AUC improves.

## Experiment 40 — 7a28e51

- Exploration: added a train-fitted `CarrierDepHour` categorical interaction from carrier and scheduled departure hour.
- Eval AUC: 0.7510, 0.0028 below the best; run status: ok; run time: 51.9s.
- Decision: discard and return to 96b7d39. This interaction did not help beyond the existing carrier and smooth departure-time features.

## Synthesis after 40 experiments

The best eval AUC is now 0.7538, up 0.0335 from the 0.7203 baseline. The kept model is `96b7d39`: 800 trees, depth 8, learning rate 0.025, tree and level column sampling at 0.5 and 0.8, `reg_lambda=5`, and `reg_alpha=4`, using categorical month/day/carrier/origin/destination plus cyclical departure time. The clearest recent result is leaf regularization: raising L2 from its default to 5 helped, while 10 tied; adding L1 and increasing it through 4 produced successive gains, but 8 regressed. The best artifact also shrank from about 48 MB at alpha 0.5 to 34 MB at alpha 4.

The carrier-by-departure-hour interaction was worse, as were calendar sine/cosine features and a three-seed probability ensemble. Scheduled arrival time could not be tested because `CRSArrTime` is absent from the input schema. Earlier results still favor moderate column sampling and cyclical departure time; route identity, explicit hour category, additional row subsampling, and alternate boosting round counts did not help. Next, probe the L1 optimum more finely around 4, then consider a different model-regularization mechanism if that local search stops improving.

## Research at the 40-run pause

For the interaction test, a Berkeley flight-delay project found hour-specific delay patterns within carriers, while XGBoost's categorical tutorial describes partition-based native category splits. The interaction was plausible from those findings but did not improve eval AUC here. No feature interaction is being retained from that run.

## Experiment 41 hypothesis

Local follow-up: test `reg_alpha=3` between the better values 2 and 4, keeping `reg_lambda=5` and all other settings fixed. This will check whether the improvement at 4 comes from a broad range or a sharper optimum. Keep only if it exceeds 0.7538.

## Experiment 41 — 3278656

- Local follow-up: set `reg_alpha=3`, retaining `reg_lambda=5`.
- Eval AUC: 0.7537, 0.0001 below the best; run status: ok; run time: 42.7s.
- Decision: discard and return to 96b7d39. This is effectively tied at four decimals, but value 4 is slightly higher.

## Experiment 42 hypothesis

Local follow-up: test `reg_alpha=3.5` between the near-best value 3 and the best value 4. Keep `reg_lambda=5` and all other settings fixed; the midpoint may retain the 4.0 gain while avoiding over-shrinkage. Keep only if it exceeds 0.7538.

## Experiment 42 — eddfe38

- Local follow-up: set `reg_alpha=3.5`, retaining `reg_lambda=5`.
- Eval AUC: 0.7534, 0.0004 below the best; run status: ok; run time: 42.9s.
- Decision: discard and return to 96b7d39. The local optimum remains at `reg_alpha=4` among tested values.

## Experiment 43 hypothesis

Regularization interaction follow-up: reduce `reg_lambda` from 5 to its default 1 while holding the newly established `reg_alpha=4` setting. L2 helped when L1 was zero, but the stronger L1 penalty may make some L2 shrinkage redundant. Keep only if this combination exceeds 0.7538.

## Experiment 43 — 28ffd02

- Regularization interaction: lowered `reg_lambda` from 5 to 1 while retaining `reg_alpha=4`.
- Eval AUC: 0.7541, a new best (up 0.0003); run status: ok; run time: 42.7s.
- Decision: keep. With strong L1 regularization, the default L2 value outperformed 5, showing that the two penalties interact.

## Experiment 44 hypothesis

Follow-up to Experiment 43: set `reg_lambda=0` while keeping `reg_alpha=4`. The move from lambda 5 to 1 improved AUC under strong L1 shrinkage; removing L2 entirely will test whether a lower value further improves that balance. Keep only if it beats 0.7541.

## Experiment 44 — 4939dd5

- Regularization interaction: reduced `reg_lambda` from 1 to 0 while retaining `reg_alpha=4`.
- Eval AUC: 0.7542, a new best (up 0.0001); run status: ok; run time: 42.8s.
- Decision: keep. Removing L2 gave a small gain under the strong L1 setting.

## Experiment 45 hypothesis

Follow-up to the new best: raise `reg_alpha` from 4 to 5 while retaining `reg_lambda=0`. The earlier alpha sweep peaked at 4 with lambda 5, but reducing L2 improved the alpha-4 model; the L1 optimum may shift when those penalties are combined. Keep only if it beats 0.7542.

## Experiment 45 — c99d72d

- Follow-up: raised `reg_alpha` from 4 to 5 with `reg_lambda=0`.
- Eval AUC: 0.7545, a new best (up 0.0003); run status: ok; run time: 42.6s.
- Decision: keep. The best L1 value shifted upward after removing L2.

## Experiment 46 hypothesis

Follow-up: increase `reg_alpha` from 5 to 6 with `reg_lambda=0`. The change from 4 to 5 improved eval AUC after removing L2, so test a modest additional L1 increase. Keep only if it beats 0.7545.

## Experiment 46 — 84f5e9c

- Follow-up: raised `reg_alpha` from 5 to 6 with `reg_lambda=0`.
- Eval AUC: 0.7542, 0.0003 below the best; run status: ok; run time: 42.4s.
- Decision: discard and return to c99d72d. The strongest tested L1 setting is still 5.

## Experiment 47 hypothesis

Local follow-up: test `reg_alpha=4.5` with `reg_lambda=0`, halfway between the previous best at 4 and the current best at 5. A modestly weaker penalty may retain the L1 gain while improving on both endpoints. Keep only if it beats 0.7545.

## Experiment 47 — 77ac988

- Local follow-up: set `reg_alpha=4.5`, retaining `reg_lambda=0`.
- Eval AUC: 0.7543, 0.0002 below the best; run status: ok; run time: 43.2s.
- Decision: discard and return to c99d72d. The best tested value remains 5.

## Experiment 48 hypothesis

Final local L1 probe: test `reg_alpha=5.5` with `reg_lambda=0`, between the best value 5 and the lower-scoring value 6. If this does not improve, stop the local alpha sweep and research a new direction.

## Experiment 48 — fb32518

- Local follow-up: set `reg_alpha=5.5`, retaining `reg_lambda=0`.
- Eval AUC: 0.7545, tied the best; run status: ok; run time: 42.4s.
- Decision: discard and return to c99d72d. The simpler value 5 reaches the same AUC.

## Plateau note after Experiment 48

Three consecutive L1 refinements (alpha 6, 4.5, and 5.5) did not improve on alpha 5; results were within 0.0003 of the best. Stop the local sweep and research a different regularization method.

## Research before Experiment 49

The official XGBoost DART tutorial describes dropping prior trees during boosting as a way to address overfitting, with the rate controlled by `rate_drop`; it notes DART can train more slowly than `gbtree` ([official DART documentation](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html)). Its example uses `rate_drop=0.1` and `skip_drop=0.5`. This is a meaningfully different regularization method from the leaf penalties just tuned, so I will compare it under the current best features and leaf settings.

## Experiment 49 hypothesis

Exploration: switch the current best from `gbtree` to `dart`, using the documented `rate_drop=0.1` and `skip_drop=0.5`, while retaining 800 rounds, depth 8, learning rate 0.025, column sampling, `reg_alpha=5`, and `reg_lambda=0`. Dropping prior trees may reduce overfitting beyond leaf regularization. Keep only if eval AUC improves; DART also adds training overhead.

## Experiment 49 — 74f08ab

- Exploration: tried DART with `rate_drop=0.1` and `skip_drop=0.5` on the current best model.
- Training exceeded the harness's 60-second cap and was killed before evaluation; run status: timeout-training; no AUC.
- Decision: discard and return to c99d72d. The harness cannot evaluate this configuration within its runtime limit. The log also warned that explicit `booster="dart"` is deprecated in the installed XGBoost version; check the replacement syntax before any retry.

## Research and correction before Experiment 50

The installed XGBoost warning recommends using the tree booster with dropout parameters rather than specifying the legacy `booster="dart"`. The current official DART tutorial confirms that dropout is controlled by `rate_drop` on tree models and that the legacy DART booster name remains available for compatibility ([DART documentation](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html); [parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html)). Retry the same 800-round DART configuration without the deprecated booster selector. The official tutorial also warns that DART can train more slowly; if the corrected form still exceeds the harness cap, drop this direction.

## Experiment 50 hypothesis

Correction/rerun of the DART experiment: remove only the explicit `booster="dart"` argument and retain `rate_drop=0.1` and `skip_drop=0.5` as the current XGBoost interface specifies. This tests the intended dropout configuration with supported syntax. Keep only if the run finishes within the harness cap and improves on 0.7545.

## Experiment 50 — 59da363

- Corrected DART interface by removing the deprecated `booster="dart"` selector and setting `rate_drop=0.1`, `skip_drop=0.5` on the tree booster.
- Training again exceeded the 60-second cap and was killed before evaluation; run status: timeout-training; no AUC.
- Decision: discard and return to c99d72d. Even with the current interface, tree dropout cannot be evaluated within this harness's training limit.

## Synthesis after 50 experiments

The best eval AUC is 0.7545, up 0.0342 from the 0.7203 baseline, at `c99d72d`. The best setup uses 800 trees, depth 8, learning rate 0.025, `colsample_bytree=0.5`, `colsample_bylevel=0.8`, `reg_alpha=5`, and `reg_lambda=0`, with cyclical departure time and the original categorical calendar, carrier, and airport inputs. Leaf regularization is the strongest recent gain. L1 improvements from 0.5 through 5 were substantial, while 6 and 8 regressed; values 4.5 and 5.5 did not beat 5. L2 helped at default L1, but with alpha 4, lowering lambda from 5 to 1 and then 0 improved AUC, and alpha 5/lambda 0 gave the best result.

Carrier-by-departure-hour interactions, cyclical month/weekday features, and a three-seed ensemble did not improve the score. Scheduled-arrival features were unavailable. DART was tried with both the legacy selector and current dropout parameters; both exceeded the 60-second training cap. The recent local search supports keeping alpha near 5 and lambda at zero. With limited time left, probe small nonzero lambda values under alpha 5, then stop if they do not improve.

## Research at the 50-run pause

The official XGBoost DART tutorial describes tree dropout as an overfitting control and confirms that `rate_drop`/`skip_drop` configure dropout on tree models. Both attempted forms timed out under this harness, so DART is not retained. Official source: [DART tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html).

## Experiment 51 hypothesis

Regularization follow-up: retain `reg_alpha=5` and add a small `reg_lambda=0.5`. At alpha 4, lambda 0 slightly beat lambda 1, but alpha 5 has not been tested with nonzero lambda; a small L2 term might complement the strongest L1 setting. Keep only if it exceeds 0.7545.

## Experiment 51 — 26c605a

- Regularization follow-up: added `reg_lambda=0.5` to `reg_alpha=5`.
- Eval AUC: 0.7539, 0.0006 below the best; run status: ok; run time: 42.8s.
- Decision: discard and return to c99d72d. The L1-only setting remains better.

## Research before Experiment 52

The official XGBoost parameter reference defines `gamma` (`min_split_loss`) as the minimum loss reduction required for a split; larger values make trees more conservative ([parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html)). A `gamma=1` trial earlier in the run did not help with the then-current leaf settings. Since strong L1 regularization now improves the model, a smaller split threshold may complement it by rejecting only weak splits.

## Experiment 52 hypothesis

Follow-up regularization test: add `gamma=0.5` to the current best (`reg_alpha=5`, `reg_lambda=0`). The prior gamma 1 result was negative before tuning leaf regularization; a milder split penalty may now complement strong L1 shrinkage. Keep only if it beats 0.7545.

## Experiment 52 — 8dd3134

- Follow-up: added `gamma=0.5` to the current `reg_alpha=5`, `reg_lambda=0` model.
- Eval AUC: 0.7508, 0.0037 below the best; run status: ok; run time: 41.0s. Artifact size dropped to about 22 MB.
- Decision: discard and return to c99d72d. This split threshold pruned too much useful structure despite the smaller artifact.

## Experiment 53 hypothesis

Follow-up to Experiment 52: reduce the split threshold from `gamma=0.5` to `gamma=0.1`, keeping the current `reg_alpha=5`, `reg_lambda=0` model otherwise fixed. The larger threshold removed useful structure; this mild value tests whether a small amount of split pruning can help without the same AUC cost. Keep only if it beats 0.7545.

## Experiment 53 — 22ecba3

- Follow-up: reduced gamma from 0.5 to 0.1 with `reg_alpha=5`, `reg_lambda=0`.
- Eval AUC: 0.7543, 0.0002 below the best; run status: ok; run time: 42.1s.
- Decision: discard and return to c99d72d. The smaller split penalty recovered most of the lost AUC but did not beat the no-gamma model.

## Experiment 54 hypothesis

One final small-gamma test: set `gamma=0.05` with `reg_alpha=5`, `reg_lambda=0`. Since gamma 0.1 was nearly tied and 0.5 was too strong, the smaller threshold may retain weak regularization without pruning as many useful splits. Keep only if it beats 0.7545.

## Experiment 54 — 3f2640e

- Follow-up: reduced gamma to 0.05 with `reg_alpha=5`, `reg_lambda=0`.
- Eval AUC: 0.7544, 0.0001 below the best; run status: ok; run time: 42.8s.
- Decision: discard and return to c99d72d. This was effectively tied but did not exceed the zero-gamma model.

## Plateau note after Experiment 54

Three consecutive gamma settings (0.5, 0.1, 0.05) failed to beat the best model and stayed within 0.0037, with the smallest values nearly tied. Stop gamma tuning and research another regularization dimension.

## Research before Experiment 55

XGBoost's parameter guide identifies `max_cat_threshold` as a way to prevent overfitting in partition-based categorical splits, and its tuning guide lists it among model-complexity controls ([parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html), [tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)). The model uses native categories for `Origin` and `Dest`, which have many levels. This is distinct from the earlier `max_cat_to_onehot` experiment: it limits category candidates considered for each partition split.

## Experiment 55 hypothesis

Categorical regularization exploration: set `max_cat_threshold=32` on the current best model, retaining all other settings. Limiting category candidates may reduce overfitting in airport partitions while preserving native categorical splits. Keep only if it beats 0.7545.

## Experiment 55 — b442a2e

- Categorical regularization: set `max_cat_threshold=32`.
- Eval AUC: 0.7539, 0.0006 below the best; run status: ok; run time: 42.9s.
- Decision: discard and return to c99d72d. The lower partition threshold did not help.

## Experiment 56 hypothesis

Categorical follow-up: raise `max_cat_threshold` from 32 to 128, keeping the current model unchanged otherwise. The lower threshold reduced AUC; allowing more categories to participate in partition splits may preserve useful airport distinctions. Keep only if it beats 0.7545.

## Experiment 56 — 331b789

- Categorical follow-up: raised `max_cat_threshold` from 32 to 128.
- Eval AUC: 0.7541, 0.0004 below the best; run status: ok; run time: 42.7s.
- Decision: discard and return to c99d72d. Neither the reduced nor increased threshold beat the default behavior.

## Research before Experiment 57

XGBoost's parameter tuning guide distinguishes complexity controls from randomness controls and lists `subsample` alongside `colsample_bytree` as a way to make training more robust to noise ([official tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)). Row subsampling at 0.8 was tested earlier, before the strong L1/L2 regularization improvements. I will check the same sampling rate under the current best leaf settings to see whether the interaction changes its effect.

## Experiment 57 hypothesis

Regularization interaction: set `subsample=0.8` while retaining `reg_alpha=5`, `reg_lambda=0`, and the current tree/level column sampling. The earlier 0.8 trial did not help before the L1 gain; with smaller leaf updates, row sampling may add complementary diversity. Keep only if it beats 0.7545.

## Experiment 57 — 97d5b7b

- Regularization interaction: added `subsample=0.8` to the alpha-5, lambda-0 model.
- Eval AUC: 0.7519, 0.0026 below the best; run status: ok; run time: 44.4s.
- Decision: discard and return to c99d72d. Row sampling again hurt despite the stronger leaf penalty.

## Research before Experiment 58

The official XGBoost parameter reference defines `min_child_weight` as the minimum Hessian weight required in a child and says larger values make splitting more conservative ([parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html)). The earlier value 10 was too restrictive and did not help. A smaller value of 3 may prune only the weakest leaves while complementing `reg_alpha=5`.

## Experiment 58 hypothesis

Follow-up: set `min_child_weight=3` on the current best, holding `reg_alpha=5` and `reg_lambda=0` fixed. This tests a moderate lower bound on child support, between the default 1 and the previously unhelpful 10. Keep only if it beats 0.7545.

## Experiment 58 — d06b3e4

- Follow-up: set `min_child_weight=3` on the alpha-5, lambda-0 model.
- Eval AUC: 0.7538, 0.0007 below the best; run status: ok; run time: 42.5s.
- Decision: discard and return to c99d72d. The moderate child threshold did not improve on the default.

## Experiment 59 hypothesis

Follow-up to Experiment 58: set `min_child_weight=2`, retaining `reg_alpha=5` and `reg_lambda=0`. The value 3 was slightly too restrictive; a lighter threshold may constrain the smallest children without reducing AUC. Keep only if it beats 0.7545.

## Experiment 59 — e2f47c7

- Follow-up: set `min_child_weight=2` on the alpha-5, lambda-0 model.
- Eval AUC: 0.7543, 0.0002 below the best; run status: ok; run time: 43.4s.
- Decision: discard and return to c99d72d. Child weight 2 remained below the default setting.

## Experiment 60 hypothesis

Final child-weight refinement: try `min_child_weight=1.5` with `reg_alpha=5`, `reg_lambda=0`. Values 2 and 3 were worse, but the lighter 1.5 setting could preserve most of the default model while pruning only very small children. Keep only if it beats 0.7545.

## Experiment 60 — 1151369

- Follow-up: set `min_child_weight=1.5` on the alpha-5, lambda-0 model.
- Eval AUC: 0.7540, 0.0005 below the best; run status: ok; run time: 44.1s.
- Decision: discard and return to c99d72d. A child-weight threshold above 1 did not help.

## Synthesis after 60 experiments

The current best remains 0.7545 at `c99d72d`, up 0.0342 from baseline. It uses 800 trees, depth 8, learning rate 0.025, column sampling 0.5 by tree and 0.8 by level, L1 regularization `reg_alpha=5`, no L2 penalty, and cyclical departure time with the original categorical predictors. The major recent advance came from L1 regularization; the best L1 value is near 5. L2 at 0.5, split penalties from 0.05 to 0.5, child-weight thresholds 1.5 to 3, row sampling at 0.8, and category thresholds 32/128 all failed to beat the best. DART cannot finish under the harness training cap.

The earlier conclusions still hold: cyclical departure time and moderate column subsampling improved AUC; calendar cycles and carrier-hour interaction did not. With only a few minutes left, test one depth increase under the stronger L1 setting, then use the remaining time for a final focused refinement if it is promising.

## Experiment 61 hypothesis

Follow-up: raise `max_depth` from 8 to 9 while retaining the best leaf regularization (`reg_alpha=5`, `reg_lambda=0`) and all other settings. Stronger L1 shrinkage may support one extra split level without the overfitting seen in less-regularized models. Keep only if it beats 0.7545.

## Experiment 61 — 36676ee

- Follow-up: increased depth from 8 to 9 under the best L1/L2 settings.
- Eval AUC: 0.7551, a new best (up 0.0006); run status: ok; run time: 44.1s.
- Decision: keep. One additional split level improved AUC under stronger L1 regularization.

## Experiment 62 hypothesis

Follow-up to the positive depth-9 result: increase `max_depth` to 10, retaining the current L1/L2 settings and all other parameters. Strong L1 regularization may still control the extra complexity. Keep only if it beats 0.7551.

## Experiment 62 — 8e355d8

- Follow-up: increased depth from 9 to 10 under the best L1/L2 settings.
- Eval AUC: 0.7582, a new best (up 0.0031); run status: ok; run time: 45.6s. Artifact size increased to about 69 MB.
- Decision: keep. The deeper trees captured useful structure under strong L1 regularization.

## Experiment 63 hypothesis

Follow-up to the strong depth-10 gain: increase `max_depth` to 11, keeping `reg_alpha=5` and `reg_lambda=0`. L1 shrinkage may continue to control the added tree complexity. Keep only if it beats 0.7582 and finishes within the training cap.

## Experiment 63 — c161b49

- Follow-up: increased depth from 10 to 11 under the best L1/L2 settings.
- Eval AUC: 0.7583, a new best (up 0.0001); run status: ok; run time: 47.8s. Artifact size increased to about 97 MB.
- Decision: keep. The score improved slightly, though the larger model cost should be revisited if a later depth ties.

## Experiment 64 hypothesis

Last depth follow-up within the remaining budget: increase `max_depth` to 12 with `reg_alpha=5` and `reg_lambda=0`. Depth 11 edged out 10; one more level may capture useful interactions, but keep only if it beats 0.7583 and finishes before the harness clock expires.

## Experiment 64 — 72ddc2a

- Follow-up: increased depth from 11 to 12 under the best L1/L2 settings.
- Eval AUC: 0.7594, a new best (up 0.0011); run status: ok; run time: 49.2s. Artifact size increased to about 123 MB.
- Decision: keep. The score gain justified retaining depth 12 at the end of the time budget.

## Final run summary

The best score is 0.7594 at `72ddc2a`, improving 0.0391 over the 0.7203 baseline. The final model uses 800 trees, depth 12, learning rate 0.025, `colsample_bytree=0.5`, `colsample_bylevel=0.8`, `reg_alpha=5`, and `reg_lambda=0`, with cyclical scheduled departure time and the original categorical month/day/carrier/airport features plus distance. The most important late-stage result was that stronger L1 regularization made deeper trees productive: AUC rose from 0.7545 at depth 8 to 0.7551 at depth 9, 0.7582 at depth 10, 0.7583 at depth 11, and 0.7594 at depth 12. The depth-12 artifact is about 123 MB.

The harness clock reported `TIME IS UP` after Experiment 64. No further experiments were started; the clock was stopped as required.
