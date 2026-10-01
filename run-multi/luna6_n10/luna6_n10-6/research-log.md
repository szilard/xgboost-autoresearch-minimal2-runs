# Research log

## Baseline — 92e43e6

Ran the starter `train.py` unchanged to establish the reference score. It uses native categorical handling for month, day of month, day of week, carrier, origin, and destination; numeric scheduled departure time and distance; and an XGBoost classifier with 30 trees, depth 6, learning rate 0.1, and seed 42. Eval AUC: 0.7203. No code changes were made.

## Research before tuning

- The [XGBoost parameter tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) frames tuning as a bias-variance tradeoff, and recommends pairing a lower `eta` with more boosting rounds. It also describes row and column subsampling as ways to add randomness against overfitting.
- The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) explains the roles of `learning_rate`, `max_depth`, `min_child_weight`, and sampling parameters. The [categorical data guide](https://xgboost.readthedocs.io/en/stable/python/examples/categorical.html) confirms native categorical splits are a supported baseline approach.
- A study using airline data from 2000–2008 considers calendar-day and airline attributes, alongside weather ([Patgiri et al., 2020](https://arxiv.org/abs/2002.10254)). Its setup is not identical to this balanced dataset, so I use it only as domain context; calendar and carrier information are already present in the starter.

### Experiment 1 hypothesis — exploration, boosting-round schedule

The starter has only 30 boosting rounds. A lower learning rate paired with substantially more rounds may reduce the coarse update size while allowing useful corrections to accumulate, improving ranking on eval. I will try `n_estimators=200` and `learning_rate=0.05`, leaving features, depth, and other parameters unchanged. This tests the tuning-guide recommendation as a pair; it is not a feature-engineering change.

## Experiment 1 — d48b955 — keep

Raised boosting rounds from 30 to 200 and reduced learning rate from 0.1 to 0.05, keeping depth and features fixed. Eval AUC rose from 0.7203 to 0.7325 (+0.0122); run status was `ok`. The result supports the hypothesis that the starter's 30 rounds were limiting the model.

### Experiment 2 hypothesis — follow-up to a promising result

The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends pairing smaller `eta` with more rounds. To see whether finer updates help beyond the current result, I will double the rounds to 400 and halve the learning rate to 0.025. This keeps the simple rounds-times-rate scale constant while testing whether smaller steps improve ranking; all other settings stay fixed.

## Experiment 2 — 6c0a070 — discard

Doubled rounds to 400 and halved the learning rate to 0.025, keeping the rounds-times-rate scale at 10. Eval AUC was 0.7320, down 0.0005 from the best 0.7325; run status was `ok`. Finer updates did not improve the current best, so the branch returns to `d48b955`.

### Experiment 3 hypothesis — follow-up regularization

The XGBoost tuning guide identifies `subsample` as a way to add randomness and reduce overfitting. Starting from the best 200-round model, I will set `subsample=0.8` while keeping the remaining parameters fixed. Randomly omitting one fifth of rows for each tree may make its ranking less dependent on individual training examples.

## Experiment 3 — 2027640 — discard

Set `subsample=0.8` on the best configuration. Eval AUC fell to 0.7276, down 0.0049; run status was `ok`. Row subsampling hurt in this test, so I restore the full-data sampling configuration.

### Experiment 4 hypothesis — exploration of interaction capacity

The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) notes that higher `max_depth` increases model complexity and overfitting risk. Calendar, carrier, origin, and destination may interact in delay patterns; I will test depth 8 instead of 6 while keeping the best model's 200 rounds, 0.05 learning rate, full-row sampling, and other settings fixed. The eval score will show whether these extra interactions generalize.

## Experiment 4 — 847d706 — keep

Raised `max_depth` from 6 to 8 with all other settings fixed. Eval AUC rose from 0.7325 to 0.7331 (+0.0006); run status was `ok`. This is a small gain, consistent with additional interaction capacity helping, though depth can overfit.

### Experiment 5 hypothesis — follow-up depth exploration

Since depth 8 improved the best score, I will test `max_depth=10` on the same 200-round, 0.05-learning-rate setup. This checks whether the small gain continues with another increase in interaction capacity. The XGBoost documentation warns that deeper trees can overfit, so I will keep the setting only if eval AUC improves.

## Experiment 5 — 65835c1 — discard

Raised `max_depth` from 8 to 10. Eval AUC was 0.7328, down 0.0003 from the best depth-8 result; run status was `ok`. The improvement did not continue at depth 10, so I restore depth 8.

### Experiment 6 hypothesis — regularize leaf formation

The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says `min_child_weight` limits how readily a child node is created, with larger values making trees more conservative. On the best depth-8 model, setting it to 5 may discourage weak leaves from fitting sparse combinations of categorical and calendar features. I will change only this parameter.

## Experiment 6 — f36e0b2 — keep

Set `min_child_weight=5` on the best depth-8 model. Eval AUC rose from 0.7331 to 0.7339 (+0.0008); run status was `ok`. This supports some restriction on child creation for this feature set.

### Experiment 7 hypothesis — follow-up regularization strength

Since `min_child_weight=5` improved the score, I will test 10 on the same model. The higher threshold may suppress more weak leaves and improve generalization, or it may constrain useful splits. Only this parameter changes.

## Experiment 7 — ae6d598 — discard

Raised `min_child_weight` from 5 to 10. Eval AUC fell to 0.7327, down 0.0012 from the best; run status was `ok`. The stronger threshold appears too restrictive.

### Experiment 8 hypothesis — bracket the useful threshold

The default threshold of 1 gave 0.7331 at depth 8, 5 gave 0.7339, and 10 gave 0.7327. I will try 3 to test whether a less restrictive value than 5 retains more useful splits while still improving on the default. This is a targeted bracket of the best regularization parameter, not a broad sweep.

## Experiment 8 — aa7461b — discard

Reduced `min_child_weight` from 5 to 3. Eval AUC was 0.7332, down 0.0007 from the best; run status was `ok`. The bracket favors 5 over 3, 1, and 10, so I restore 5.

## Research before feature engineering

- Rebollo and Balakrishnan's air-traffic delay study uses temporal variables (hour, weekday, month) and spatial network variables based on origin-destination links. Its forecasts also use historical network delay states, which are unavailable in this experiment; I will borrow only the motivation to represent an individual route ([paper](https://web.mit.edu/hamsa/www/pubs/RebolloBalakrishnanTRC2014.pdf)).
- The [XGBoost categorical-data guide](https://xgboost.readthedocs.io/en/stable/python/examples/categorical.html) demonstrates native categorical features with pandas categoricals and `enable_categorical=True`, which the current model already uses.
- The [scikit-learn time-feature engineering example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) explains that raw ordinal time may obscure periodicity and demonstrates cyclic and periodic-spline encodings. I may test an hour representation after the route experiment.

### Experiment 9 hypothesis — exploration of a directed route feature

Origin and destination are present as separate categoricals. A directed origin-destination category can expose their joint relationship in one feature and may help the model distinguish routes with different delay behavior. I will fit a route-to-code lookup from training rows only, add the mapped route as a pandas categorical inside `prepare(df)`, and leave the remaining features and best hyperparameters unchanged. Unknown routes will map to missing. The feature is computed row by row, with no counts or statistics over `df`.

## Experiment 9 — 5293aa8 — discard

Added a directed origin-destination categorical feature with its category-code lookup fitted once on train. Eval AUC fell to 0.7067, down 0.0272, and eval time rose from about 31s to 43.4s; run status was `ok`. The high-cardinality route feature hurt this setup, so I restore the best hyperparameter-only model.

## Synthesis — first ten runs (baseline plus nine experiments)

- The strongest result is the 200-tree, 0.05-learning-rate setup with depth 8 and `min_child_weight=5` (commit `f36e0b2`, Eval AUC 0.7339, up 0.0136 from baseline 0.7203).
- More rounds paired with a smaller learning rate (400 / 0.025) did not improve the 200 / 0.05 result. Row subsampling at 0.8 also reduced AUC.
- Depth 8 helped slightly over depth 6; depth 10 was slightly worse. `min_child_weight=5` improved over the default and tested alternatives 3 and 10.
- The directed route category was a poor fit: it sharply reduced AUC and slowed row-by-row preparation. I will avoid this high-cardinality encoding for now.
- Next I will test an hour-of-day category derived from scheduled departure time. Flight-delay research found significant variation across hourly time-of-day categories, and the time-feature literature supports representing temporal cycles explicitly. This has low cardinality and keeps features row-local.

### Experiment 10 hypothesis — hourly departure category

Rebollo and Balakrishnan treat time-of-day as an hourly categorical variable and report that temporal variables matter in delay prediction ([paper](https://web.mit.edu/hamsa/www/pubs/RebolloBalakrishnanTRC2014.pdf)). I will derive `DepHour = CRSDepTime // 100`, fit its category levels on training rows, and add it as a categorical feature inside `prepare(df)`. The existing raw departure-time feature stays in place. Hour-level effects may be easier for the model to use than HHMM thresholds alone; all other code and hyperparameters stay fixed.

## Experiment 10 — 9e003e4 — discard

Added a training-learned categorical hour derived from scheduled HHMM departure time. Eval AUC was 0.7328, down 0.0011 from the best; run status was `ok`. The extra hourly category did not help beyond the raw time feature.

### Experiment 11 hypothesis — cyclic time representation

The [scikit-learn time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) describes sine/cosine features as a way to represent time-of-day without a discontinuity at midnight. This differs from the prior hourly category: it maps all times onto a continuous cycle, which tree splits may use to capture broad periodic patterns. I will convert HHMM into minutes since midnight, add sine and cosine of the 24-hour angle, and keep the raw feature and best model settings unchanged.

## Experiment 11 — 94d5531 — discard

Added sine and cosine of scheduled departure time after parsing HHMM to minutes since midnight. Eval AUC was 0.7338, effectively tied but 0.0001 below the best; run status was `ok`. The extra features did not justify keeping a slightly lower score, so I restore the simpler best model.

### Experiment 12 hypothesis — column subsampling

The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `colsample_bytree` as sampling features for each tree and notes that column-sampling settings can regularize tree construction. Row subsampling hurt, but feature subsampling is a distinct mechanism. I will set `colsample_bytree=0.8` on the best model, keeping everything else fixed, to test whether requiring trees to use different subsets of the eight existing features improves generalization.

## Experiment 12 — 8d4b94e — keep

Set `colsample_bytree=0.8` on the best hyperparameter setup. Eval AUC rose from 0.7339 to 0.7397 (+0.0058); run status was `ok`. This is the largest gain so far and supports per-tree feature sampling for this small feature set.

### Experiment 13 hypothesis — stronger column sampling

Because 0.8 helped substantially, I will test `colsample_bytree=0.6` while holding everything else fixed. Stronger feature sampling may further reduce reliance on a few noisy predictors; with only eight input features, it could also omit too much signal. This measures the direction directly.

## Experiment 13 — d9cccc0 — keep

Reduced `colsample_bytree` from 0.8 to 0.6. Eval AUC rose from 0.7397 to 0.7455 (+0.0058); run status was `ok`. The improvement continued at stronger feature sampling.

### Experiment 14 hypothesis — continue the sampling curve

I will reduce `colsample_bytree` to 0.4, which should make each tree consider a smaller subset of the available predictors. Since both 0.8 and 0.6 improved in sequence, stronger regularization may help further, although sampling too few of the eight features could remove important signal. All other settings remain fixed.

## Experiment 14 — 39a4655 — discard

Reduced `colsample_bytree` from 0.6 to 0.4. Eval AUC fell to 0.7436, down 0.0019 from the best; run status was `ok`. Stronger feature sampling went too far.

### Experiment 15 hypothesis — refine the column-sampling level

The tested values give 0.7397 at 0.8, 0.7455 at 0.6, and 0.7436 at 0.4. I will test the midpoint 0.5 to see whether it can retain the benefit of sampling four or more predictors while avoiding the loss at 0.4. This is a targeted refinement around the current best.

## Experiment 15 — 995de51 — discard

Set `colsample_bytree=0.5`. Eval AUC tied the displayed best at 0.7455; run status was `ok`. It did not simplify the model relative to the 0.6 setting, so I retain `d9cccc0` as the best configuration.

### Experiment 16 hypothesis — sampling within tree levels

The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says `colsample_bytree`, `colsample_bylevel`, and `colsample_bynode` act cumulatively. Per-tree sampling helped, while 0.5 tied rather than improved. I will add `colsample_bylevel=0.8` on top of the winning per-tree value 0.6 to test whether selecting a fresh subset at each depth adds useful diversity. Other settings remain fixed.

## Experiment 16 — 592f946 — discard

Added `colsample_bylevel=0.8` on top of `colsample_bytree=0.6`. Eval AUC fell to 0.7433, down 0.0022; run status was `ok`. Additional within-tree sampling hurt, so I restore the best per-tree-only configuration.

### Experiment 17 hypothesis — depth under feature sampling

Per-tree feature sampling raises AUC substantially, and the best model so far uses depth 8. Since sampling changes the number of candidate features per tree, a shallower tree may now generalize better while retaining the sampling gain. I will set `max_depth=6` under `colsample_bytree=0.6`, with the other winning settings fixed.

## Experiment 17 — 8a2a75c — discard

Reduced `max_depth` from 8 to 6 with `colsample_bytree=0.6`. Eval AUC fell to 0.7368, well below the best; run status was `ok`. The feature-sampled model appears to benefit from depth 8, so I restore that setting.

### Experiment 18 hypothesis — deeper interactions with feature sampling

The depth-6 model lost 0.0087 AUC relative to depth 8 under the winning `colsample_bytree=0.6` setting. I will test depth 10 with the same feature sampling. The extra depth may capture higher-order interactions while feature subsampling limits each tree's candidate predictors; this differs from the earlier depth-10 test, which used no column sampling.

## Experiment 18 — 9afe938 — keep

Raised `max_depth` from 8 to 10 while retaining `colsample_bytree=0.6`. Eval AUC rose from 0.7455 to 0.7502 (+0.0047); run status was `ok`. This shows that stronger feature sampling changed the useful depth: depth 10 had been slightly worse without column sampling.

## Research before categorical split experiment

The [XGBoost 3.4 parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) says `max_cat_to_onehot` selects one-hot-based splits for categorical features with fewer categories than the threshold, and partition-based splits for higher-cardinality features. It has been available since XGBoost 1.6; the installed version is 3.4.1. This offers a way to change how the starter's existing low-cardinality month, day, and carrier columns split without re-encoding high-cardinality airports.

### Experiment 19 hypothesis — one-hot splits for low-cardinality categories

I will set `max_cat_to_onehot=32` on the best configuration. This should make XGBoost consider one-hot splits for categories such as month, weekday, day of month, and carrier, while leaving airport origin and destination as partitioned categoricals. Individual levels may have distinct delay effects that are diluted when grouped; the parameter tests this while preserving native categorical handling.

## Experiment 19 — f9ead0a — discard

Set `max_cat_to_onehot=32`, causing one-hot splits for the starter's low-cardinality categorical features. Eval AUC fell to 0.7372, down 0.0130; run status was `ok`. Applying one-hot splits broadly to month, day-of-month, weekday, and carrier hurt, so I restore the best model.

## Synthesis — runs 11–20

- The best score is now 0.7502 at commit `9afe938`, a 0.0299 gain over the 0.7203 baseline. The winning settings are 200 trees, learning rate 0.05, depth 10, `min_child_weight=5`, and `colsample_bytree=0.6`.
- Per-tree feature sampling drove the largest gains: 0.8 improved AUC to 0.7397, then 0.6 to 0.7455. A more aggressive 0.4 fell back to 0.7436, and 0.5 tied 0.6. Sampling at each depth level also hurt. Keep per-tree sampling at 0.6 as the best result.
- Depth interacts strongly with sampling: depth 6 under 0.6 sampling fell to 0.7368, while depth 10 rose to 0.7502. More depth without sampling was not useful, so the gain comes from the combination.
- Broad one-hot splits for all low-cardinality categories hurt. A narrower threshold of 8 would affect only the weekday feature (seven levels) and can test whether the broad one-hot result was caused by one or more of the other categorical columns.
- Route categories, hour categories, and cyclic time features did not improve the score. Avoid adding more features until the next targeted categorical test is complete.

### Experiment 20 hypothesis — isolate weekday one-hot splits

The XGBoost docs describe `max_cat_to_onehot` as a category-count threshold. Setting it to 8 should use one-hot splits for the seven-level day-of-week column while leaving month, day-of-month, carrier, origin, and destination on partition-based splits. This isolates weekday handling after the broad threshold of 32 reduced AUC. I will change only this parameter on the current best setup.

## Experiment 20 — ce480a2 — discard

Set `max_cat_to_onehot=8`, which isolated one-hot splits to the seven-level weekday feature. Eval AUC fell to 0.7490, down 0.0012; run status was `ok`. Even this narrower one-hot setting did not help, so I restore the partition-based categorical configuration.

### Experiment 21 hypothesis — loss-guided tree growth

The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `lossguide` as expanding nodes with the highest loss change, while `depthwise` expands nodes closest to the root. The current best uses substantial depth plus per-tree feature sampling. Loss-guided growth may allocate that capacity to only the most promising branches. I will change only `grow_policy` to `lossguide`, retaining the existing depth-10 cap and other best parameters.

## Experiment 21 — bda4942 — discard

Changed the tree `grow_policy` to `lossguide`. Eval AUC tied the best at 0.7502, while training time increased from 3.6s to 7.2s; run status was `ok`. It added training cost without improving the score, so I retain the simpler depthwise model.

### Experiment 22 hypothesis — limit categorical partition search

The [XGBoost categorical parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) says `max_cat_threshold` limits the categories considered for each partition-based split to help prevent overfitting. The existing origin and destination features have many categories, so I will set `max_cat_threshold=32` on the best model. This tests a targeted regularization of airport-category splits while leaving their native categorical representation intact.

## Experiment 22 — 5d2aa82 — discard

Set `max_cat_threshold=32` to restrict categories considered in partition-based splits. Eval AUC fell to 0.7488, down 0.0014; run status was `ok`. This cap did not improve the existing categorical features, so I restore the default threshold.

### Experiment 23 hypothesis — L2 leaf-weight regularization

The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `reg_lambda` as L2 regularization on leaf weights; increasing it makes the model more conservative. On the depth-10, feature-sampled winner, `reg_lambda=5` may dampen noisy leaf scores without losing the useful tree structure. I will change only this parameter.

## Experiment 23 — 2620876 — keep

Set `reg_lambda=5` on the best model. Eval AUC rose from 0.7502 to 0.7515 (+0.0013); run status was `ok`. Stronger L2 leaf-weight regularization helped.

### Experiment 24 hypothesis — test stronger L2

Since increasing `reg_lambda` from its default 1 to 5 improved AUC, I will test 10 on the same configuration. This checks whether further damping of leaf weights improves generalization or begins to underfit.

## Experiment 24 — ec6116e — discard

Raised `reg_lambda` from 5 to 10. Eval AUC was 0.7514, down 0.0001 from the best; run status was `ok`. Stronger L2 regularization did not improve on 5, so I restore that setting.

### Experiment 25 hypothesis — bracket L2 strength

The default `reg_lambda=1` scored 0.7502, 5 scored 0.7515, and 10 scored 0.7514. I will test 3 to check whether a lower L2 value can capture most of the gain or whether the best region is nearer 5. This is a targeted midpoint test.

## Experiment 25 — ae1c329 — discard

Reduced `reg_lambda` from 5 to 3. Eval AUC was 0.7508, down 0.0007 from the best; run status was `ok`. The tested L2 values favor 5.

### Experiment 26 hypothesis — prune low-gain splits

The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `gamma` as the minimum loss reduction required for a split and says larger values make trees more conservative. With depth 10, `min_child_weight=5`, and `reg_lambda=5`, setting `gamma=1` may prune low-value branches while preserving strong splits. I will change only this parameter.

## Experiment 26 — 36fd132 — discard

Set `gamma=1` to require a minimum loss reduction for each split. Eval AUC was 0.7513, down 0.0002 from the best; run status was `ok`. Together with the last two L2 tests, this is the third consecutive discard with movement under 0.001, so I am researching before the next experiment.

## Plateau research before Experiment 27

The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `sampling_method="gradient_based"`: rows are sampled in proportion to a regularized gradient/Hessian magnitude, and on `hist` the subsample ratio may be lowered to 0.1. CPU support was added in XGBoost 3.2; the installed version is 3.4.1. This is distinct from the earlier uniform `subsample=0.8` experiment, which lowered AUC: gradient-based sampling may retain difficult examples more often than easy ones.

### Experiment 27 hypothesis — gradient-based row sampling

I will enable `tree_method="hist"`, set `sampling_method="gradient_based"`, and use `subsample=0.8` on the current best model. The gradient-weighted selection may focus training on difficult flight examples while sampling still adds some regularization. The prior uniform 0.8 result motivates matching its sampling fraction while changing the selection rule.

## Experiment 27 — 3c1fb4b — discard

Enabled CPU `hist` gradient-based sampling with `subsample=0.8`. Eval AUC was 0.7510, down 0.0005 from the best; run status was `ok`. Gradient-based sampling did not recover the loss from uniform row subsampling, so I restore the full-data configuration.

### Experiment 28 hypothesis — finer numeric histograms

The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) says `max_bin` controls histogram bins and that increasing it can improve split optimality at additional compute cost. The model has only two numeric predictors, including scheduled time, so 512 bins may offer more precise thresholds than the default 256. I will set `tree_method="hist"` explicitly and `max_bin=512`; `auto` already selects hist, so this makes the requirement for `max_bin` explicit without changing the effective tree method.

## Experiment 28 — d42ae87 — discard

Set the histogram tree method explicitly and increased `max_bin` from 256 to 512. Eval AUC was 0.7506, down 0.0009; run status was `ok`. Finer numeric histograms did not help, so I restore the default bin count.

### Experiment 29 hypothesis — DART dropout booster

The [XGBoost DART tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) describes dropping trees during training as a way to address overfitting, while retaining the regular `gbtree` parameters. I will test `booster="dart"` with `rate_drop=0.1` on the current best configuration. The model's feature and tree settings stay fixed; dropout may make the ensemble less dependent on earlier trees.

## Experiment 29 — 9f046c6 — crash

Tested `booster="dart"` with `rate_drop=0.1`. The harness killed training at the 60s limit before evaluation; status was `timeout-training`. DART's dropout overhead exceeded the run budget, so I restore the current best.

## Synthesis — runs 21–30

- The best remains commit `2620876` at Eval AUC 0.7515, up 0.0312 from the 0.7203 baseline. It uses 200 trees, depth 10, `min_child_weight=5`, `reg_lambda=5`, learning rate 0.05, and `colsample_bytree=0.6`.
- The major remaining gain came from combining per-tree column sampling with depth 10. Lower depth, per-level column sampling, or stronger/weaker L2 did not improve it.
- Categorical adjustments (one-hot thresholds and category caps) were consistently worse. Route and time-derived features did not help. Gradient-based row sampling did not overcome the loss from uniform sampling.
- Loss-guided growth tied the score but doubled training time; DART exceeded the one-minute training limit. Keep the simpler depthwise `gbtree` path.
- After finding the strong depth and regularization combination, tree count has not yet been retuned on that configuration. Next I will test 300 trees at the same learning rate to see whether more boosting rounds add signal.

### Experiment 30 hypothesis — revisit tree count on the best configuration

The original 400-round, 0.025-learning-rate experiment preceded the depth-10, feature-sampled, L2-regularized model. I will increase `n_estimators` from 200 to 300 while retaining learning rate 0.05 and all winning settings. The deeper, more regularized trees may benefit from additional rounds; this isolates that question.

## Experiment 30 — 3e9851b — keep

Raised `n_estimators` from 200 to 300 on the current best configuration. Eval AUC rose from 0.7515 to 0.7526 (+0.0011); run status was `ok`. More rounds helped after the other hyperparameters were tuned.

### Experiment 31 hypothesis — continue the round-count check

I will raise `n_estimators` from 300 to 400 while keeping learning rate 0.05 and all other settings fixed. The gain at 300 may continue, or the model may begin to overfit; this measures the next point on the same boosting-round curve.

## Experiment 31 — c8bc6c6 — discard

Raised `n_estimators` from 300 to 400 at learning rate 0.05. Eval AUC fell to 0.7518, down 0.0008 from the best; run status was `ok`. The score peaked before 400 rounds, so I restore 300.

### Experiment 32 hypothesis — refine tree count

The current configuration scored 0.7526 at 300 trees and 0.7518 at 400. I will test 350 to see whether an intermediate stopping point improves on 300. This brackets the observed drop while changing only `n_estimators`.

## Experiment 32 — bfa10cf — discard

Set `n_estimators=350`, between the 300-tree best and the lower 400-tree score. Eval AUC was 0.7522, down 0.0004; run status was `ok`. The tested count still favors 300.

### Experiment 33 hypothesis — slightly smaller update size

At 300 trees, learning rate 0.05 scored 0.7526; increasing the count at the same rate began to lower AUC. I will keep 300 trees and reduce the learning rate to 0.04. More conservative updates may curb overfitting while retaining enough rounds to learn the signal.

## Experiment 33 — f736154 — discard

Reduced learning rate from 0.05 to 0.04 at 300 rounds. Eval AUC was 0.7521, down 0.0005 from the best; run status was `ok`. Combined with the 350- and 400-round results, this is the third consecutive discard with movement under 0.001, so I am researching before the next experiment.

## Plateau research before Experiment 34

The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) distinguishes `reg_alpha` (L1 regularization on weights) from `reg_lambda` (L2); both make the model more conservative as they increase. `reg_lambda=5` helped, while nearby learning-rate and round-count changes plateaued. L1 may suppress weak leaf outputs in a different way from L2.

### Experiment 34 hypothesis — add moderate L1 regularization

I will set `reg_alpha=0.5` on the current best configuration, which uses `reg_lambda=5`. This tests whether a moderate L1 penalty complements the L2 penalty and further reduces noisy leaf weights. No other parameters change.

## Experiment 34 — 1f5f745 — keep

Set `reg_alpha=0.5` with `reg_lambda=5`. Eval AUC rose from 0.7526 to 0.7532 (+0.0006); run status was `ok`. L1 regularization added a small gain alongside L2.

### Experiment 35 hypothesis — increase L1 strength

Since `reg_alpha=0.5` improved AUC, I will test 1.0 with all other settings fixed. A stronger penalty may further suppress weak leaf weights or may begin to remove useful signal.

## Experiment 35 — 1feb2c2 — keep

Raised `reg_alpha` from 0.5 to 1.0. Eval AUC rose from 0.7532 to 0.7547 (+0.0015); run status was `ok`. Stronger L1 regularization helped again.

### Experiment 36 hypothesis — increase L1 again

Since `reg_alpha=1.0` improved the score, I will test 2.0 with all other settings fixed. The larger L1 penalty may further suppress weak leaf weights or begin to underfit.

## Experiment 36 — 522e867 — keep

Raised `reg_alpha` from 1.0 to 2.0. Eval AUC rose from 0.7547 to 0.7566 (+0.0019); run status was `ok`. The increasing L1 trend continues.

### Experiment 37 hypothesis — continue the L1 curve

I will test `reg_alpha=4.0`, doubling the value that just improved AUC. Stronger shrinkage may continue to reduce noisy leaf weights, or it may begin to underfit. All other settings stay fixed.

## Experiment 37 — 605c0bc — keep

Raised `reg_alpha` from 2.0 to 4.0. Eval AUC rose from 0.7566 to 0.7574 (+0.0008); run status was `ok`. The gain continues as L1 strength increases.

### Experiment 38 hypothesis — continue L1 search

The tested `reg_alpha` values 0.5, 1, 2, and 4 have each improved AUC. I will test 8. The stronger penalty may continue suppressing weak leaf weights or eventually underfit the data; all other parameters stay fixed.

## Experiment 38 — 7d9617b — discard

Raised `reg_alpha` from 4.0 to 8.0. Eval AUC fell to 0.7563, down 0.0011 from the best; run status was `ok`. Stronger L1 regularization went too far.

### Experiment 39 hypothesis — refine L1 strength

`reg_alpha=4.0` scored 0.7574 and 8.0 scored 0.7563. I will test 6.0 as the midpoint to see whether the optimum lies between them. This is a targeted bracket of the L1 value.

## Experiment 39 — 14137a5 — discard

Set `reg_alpha=6.0`, between the best 4.0 and worse 8.0. Eval AUC was 0.7573, 0.0001 below the best; run status was `ok`. Since it did not improve or simplify the model, I retain `605c0bc`.

## Synthesis — runs 31–40

- The best is commit `605c0bc` at Eval AUC 0.7574, up 0.0371 from the 0.7203 baseline. It uses 300 trees, depth 10, `min_child_weight=5`, `reg_lambda=5`, `reg_alpha=4`, learning rate 0.05, and `colsample_bytree=0.6`.
- On the earlier model without L1, 300 trees beat 200, while 350 and 400 were slightly worse. A learning rate of 0.04 at 300 rounds also fell slightly.
- L1 regularization gave the strongest recent gains: AUC rose at `reg_alpha` 0.5, 1, 2, and 4. At 8 it fell; 6 tied closely but was just below 4. This suggests the useful range is near 4.
- Training-time sampling, categorical split changes, DART, and finer numeric histograms did not improve the model. Keep the simple native-category, depthwise tree setup.
- The strong L1 penalty may shift the best boosting-round count by reducing overfitting. Next I will test 400 rounds on the newly regularized model.

### Experiment 40 hypothesis — tree count with L1 regularization

The 400-tree trial before L1 regularization scored below the 300-tree model. With `reg_alpha=4` now improving the model substantially, extra rounds may add useful signal without the same overfitting. I will raise `n_estimators` from 300 to 400 while keeping the new best's other settings fixed.

## Experiment 40 — 1311766 — keep

Raised `n_estimators` from 300 to 400 with `reg_alpha=4`. Eval AUC rose from 0.7574 to 0.7583 (+0.0009); run status was `ok`. The stronger L1 penalty allowed more rounds to help.

### Experiment 41 hypothesis — continue rounds under stronger L1

Since 400 trees improved over 300 after adding `reg_alpha=4`, I will test 500 with the same settings. L1 may continue to limit overfitting as the ensemble grows.

## Experiment 41 — 772c653 — keep

Raised `n_estimators` from 400 to 500 with `reg_alpha=4`. Eval AUC rose from 0.7583 to 0.7587 (+0.0004); run status was `ok`. The improvement continued, though it is smaller.

### Experiment 42 hypothesis — extend boosting rounds

Since 500 trees improved slightly over 400, I will test 600 with the same parameters. L1 regularization may permit the ensemble to continue improving, though the small gain suggests diminishing returns.

## Experiment 42 — 53d9248 — keep

Raised `n_estimators` from 500 to 600 with `reg_alpha=4`. Eval AUC rose from 0.7587 to 0.7589 (+0.0002); run status was `ok`. The score continues to climb, with diminishing returns.

### Experiment 43 hypothesis — one more round-count step

I will test 700 trees with the same settings. This checks whether the small improvement at 600 continues or whether boosting has reached its useful limit.

## Experiment 43 — 07196b7 — discard

Raised `n_estimators` from 600 to 700 with `reg_alpha=4`. Eval AUC tied the displayed best at 0.7589; run status was `ok`. It did not simplify the model, so I retain 600 trees. Ten runs have elapsed since the last research pass; I am researching before the next experiment.

## Research before Experiment 44 — per-node feature sampling

The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) distinguishes `colsample_bynode` (sample features each split) from `colsample_bylevel` (sample a subset shared across a tree level). Both combine multiplicatively with `colsample_bytree`. The earlier `colsample_bylevel=0.8` trial hurt on the pre-L1 model; fresh per-node choices may behave differently with the current deeper, L1-regularized model.

### Experiment 44 hypothesis — sample features per split

On the best model, I will set `colsample_bynode=0.8` in addition to `colsample_bytree=0.6`. Per-node choices may decorrelate branch decisions more effectively than a feature subset shared by each level. I will explicitly set `tree_method="hist"`, which is the method required for this column-sampling setting; the current `auto` setting selects hist. All other settings remain fixed.

## Experiment 44 — 167eb22 — keep

Set `colsample_bynode=0.8` and explicitly selected `tree_method="hist"` on the best configuration. Eval AUC rose from 0.7589 to 0.7601 (+0.0012), with run status `ok`. This is the new best; the per-node feature sampling hypothesis is supported.

### Experiment 45 hypothesis — ease per-node sampling

On the new best, raise `colsample_bynode` from 0.8 to 1.0 while keeping all other settings fixed. This will test whether the gain came from moderate per-node feature sampling or whether using every tree-level candidate at each split performs better with the already reduced `colsample_bytree=0.6`.

## Experiment 45 — 770643c — discard

Raised `colsample_bynode` from 0.8 to 1.0. Eval AUC fell from 0.7601 to 0.7589 (-0.0012), with run status `ok`. Restoring the 0.8 best setting.

### Experiment 46 hypothesis — stronger per-node feature sampling

Lower `colsample_bynode` from 0.8 to 0.6 while retaining `colsample_bytree=0.6`. The resulting smaller feature pool at each split may further reduce correlation among the deep trees, though it could also omit useful flight predictors. Keep all other parameters fixed.

## Experiment 46 — d2bb30f — discard

Lowered `colsample_bynode` from 0.8 to 0.6. Eval AUC fell to 0.7582 (-0.0019 versus the best), with run status `ok`. Restoring 0.8.

### Experiment 47 hypothesis — refine per-node sampling near 0.8

Test `colsample_bynode=0.9`, between the best 0.8 and the lower-scoring 1.0. The current results suggest a moderate feature subset is useful; 0.9 tests whether a less aggressive subset improves further. All other settings remain fixed.

## Experiment 47 — fb716d2 — discard

Raised `colsample_bynode` from 0.8 to 0.9. Eval AUC tied the best at 0.7601, with run status `ok`; since the candidate is not simpler, I retained 0.8.

### Experiment 48 hypothesis — combine per-level and per-node sampling

Test `colsample_bylevel=0.9` while retaining `colsample_bytree=0.6` and the winning `colsample_bynode=0.8`. A prior per-level-only test hurt on an earlier model, but the current model has L1 regularization and per-node sampling, so a modest per-level fraction may interact differently. All other settings remain fixed.

## Experiment 48 — 9dc74e7 — discard

Added `colsample_bylevel=0.9` while retaining per-tree 0.6 and per-node 0.8 sampling. Eval AUC fell to 0.7582 (-0.0019 versus the best), with run status `ok`. Additional per-level sampling did not help in this configuration; restoring the per-tree/per-node best.

### Experiment 49 hypothesis — retest boosting rounds with per-node sampling

Raise `n_estimators` from 600 to 700 on the new per-node-sampled best. The earlier 700-tree test tied before adding per-node sampling, but that extra feature randomness may change the useful ensemble length. All other settings remain fixed.

## Experiment 49 — 249985e — discard

Raised the per-node-sampled model from 600 to 700 trees. Eval AUC was 0.7598, down 0.0003 versus the best, with run status `ok`. Restoring 600 trees.

### Experiment 50 hypothesis — refine L1 near 4.0

Lower `reg_alpha` from 4.0 to 3.0 while retaining the current feature sampling and 600 trees. Earlier tests favored L1=4 over 2, while 6 was worse; 3.0 checks whether a slightly less sparse model can improve the current per-node-sampled configuration. All other settings remain fixed.

## Experiment 50 — dc8b602 — discard

Lowered `reg_alpha` from 4.0 to 3.0 on the per-node-sampled best. Eval AUC fell to 0.7578 (-0.0023), with run status `ok`. Retaining L1=4.0.

## Synthesis — runs 41–50

- The best is commit `167eb22` at Eval AUC 0.7601, up 0.0398 from the 0.7203 baseline. It uses 600 trees, depth 10, `min_child_weight=5`, `reg_lambda=5`, `reg_alpha=4`, learning rate 0.05, `colsample_bytree=0.6`, and `colsample_bynode=0.8`, with native categorical handling and histogram trees.
- The main gain in this block came from per-node feature sampling: `colsample_bynode=0.8` improved AUC by 0.0012. Values 0.6 and 1.0 were lower, while 0.9 tied; adding per-level sampling also hurt. The useful setting appears centered near 0.8.
- Retesting 700 trees with per-node sampling scored 0.7598, so 600 remains best. Reducing `reg_alpha` to 3.0 scored 0.7578, consistent with retaining 4.0.
- The model has now been tuned across tree depth, rounds, L1/L2, split constraints, and feature sampling. The next research direction is class weighting: XGBoost's tuning guide recommends `scale_pos_weight` for imbalanced classification when AUC is the metric, with the negative-to-positive count ratio as a typical value. I will test that ratio derived from the training labels, leaving evaluation untouched.

## Research before Experiment 51 — positive-class weighting

The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends balancing positive and negative weights with `scale_pos_weight` when optimizing AUC on an imbalanced dataset. The [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) gives the negative-to-positive instance ratio as a typical value. It separately suggests `max_delta_step` mainly when well-calibrated probabilities are needed. Since this experiment scores AUC, I will test the documented class-weight ratio.

### Experiment 51 hypothesis — weight delayed flights by the training class ratio

Set `scale_pos_weight` to the number of negative training examples divided by the number of positive training examples, computed from `y_train`. This gives the minority delayed class greater influence during fitting and may improve ranking quality. Keep all other parameters and the evaluation procedure fixed.

## Experiment 51 — b91ac78 — discard

Set `scale_pos_weight` to the negative-to-positive training-label ratio. Eval AUC tied the best at 0.7601, with run status `ok`; the full ratio did not improve ranking, so I retained the unweighted model.

### Experiment 52 hypothesis — partial class weighting

Test the square root of the negative-to-positive training-label ratio for `scale_pos_weight`. The full ratio tied the best; a milder weight may capture some benefit of emphasizing delayed flights without shifting the fit as strongly. All other parameters remain fixed.

## Experiment 52 — 25b08ca — discard

Set `scale_pos_weight` to the square root of the negative-to-positive training-label ratio. Eval AUC again tied the best at 0.7601, with run status `ok`; I retain the unweighted model.

### Experiment 53 hypothesis — cap leaf update size

Set `max_delta_step=1`. The XGBoost parameter reference says a positive value constrains leaf outputs and can make logistic updates more conservative, particularly under class imbalance. Full and partial class weighting tied on AUC; a bounded leaf step may regularize the deep, long-running ensemble differently. All other parameters remain fixed.

## Experiment 53 — 4f791fe — discard

Set `max_delta_step=1` to constrain leaf outputs. Eval AUC was 0.7595 (-0.0006 versus the best), with run status `ok`; I restored the unconstrained setting. This is the third consecutive non-improving experiment with less than 0.001 AUC movement, so I am researching a new direction before the next run.

## Plateau research before Experiment 54 — histogram resolution

The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `max_bin` as the maximum number of discrete bins for continuous features in `hist` and `approx`; increasing it gives more precise split candidates at higher compute cost. An earlier `max_bin=512` trial scored 0.7506, below the default-256 model. Since the model has only two continuous inputs, fewer bins may act as useful regularization by limiting threshold choices. I will test 128 bins against the default 256.

### Experiment 54 hypothesis — coarser numeric thresholds

Set `max_bin=128` with the existing histogram tree method. Coarser quantization may reduce overfitting to narrow thresholds in scheduled departure time and distance; the previous finer 512-bin setting did not help. Keep all other parameters fixed.

## Experiment 54 — 6f4909e — discard

Lowered `max_bin` from 256 to 128. Eval AUC fell to 0.7589 (-0.0012 versus the best), with run status `ok`; I restored the default 256 bins.

### Experiment 55 hypothesis — retune tree-level sampling with per-node sampling

Raise `colsample_bytree` from 0.6 to 0.7 while retaining `colsample_bynode=0.8`. The two column-sampling parameters combine; a slightly larger tree-level pool may pair better with the per-node sampling gain than the earlier 0.6 setting alone. All other parameters remain fixed.

## Experiment 55 — 77fa81a — keep

Raised `colsample_bytree` from 0.6 to 0.7 with `colsample_bynode=0.8`. Eval AUC rose from 0.7601 to 0.7605 (+0.0004), with run status `ok`. This is the new best.

### Experiment 56 hypothesis — continue tree-level sampling adjustment

Raise `colsample_bytree` from 0.7 to 0.8 while retaining `colsample_bynode=0.8`. The 0.7 setting improved slightly; increasing it once more tests whether the interaction continues to benefit from a broader feature set per tree.

## Experiment 56 — 605fe44 — discard

Raised `colsample_bytree` from 0.7 to 0.8 with `colsample_bynode=0.8`. Eval AUC fell to 0.7601 (-0.0004 versus the best), with run status `ok`; I restored 0.7.

### Experiment 57 hypothesis — shift sampling toward individual splits

Keep `colsample_bytree=0.7` and lower `colsample_bynode` from 0.8 to 0.7. The combined sampled fraction stays near the best prior combination (`0.6 × 0.8`), but this setting exposes more features per split on a per-tree basis and may alter useful feature diversity.

## Experiment 57 — 33a9d3a — discard

Lowered `colsample_bynode` from 0.8 to 0.7 while keeping `colsample_bytree=0.7`. Eval AUC fell to 0.7598 (-0.0007 versus the best), with run status `ok`; I restored 0.8.

### Experiment 58 hypothesis — slightly broader per-split pool

Raise `colsample_bynode` from 0.8 to 0.9 while retaining `colsample_bytree=0.7`. The 0.7 node fraction was slightly worse; the earlier 0.9 value tied when the tree fraction was 0.6, so this tests whether 0.9 combines better with the new tree-level setting.

## Experiment 58 — cdf9af9 — discard

Raised `colsample_bynode` from 0.8 to 0.9 while keeping `colsample_bytree=0.7`. Eval AUC tied the best at 0.7605, with run status `ok`; I retained 0.8. This is the third consecutive non-improving run within 0.001 AUC, triggering another research pass.

## Plateau research before Experiment 59 — split regularization

The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `min_child_weight` as the minimum Hessian sum needed to create a child, with larger values making trees more conservative. It defines `gamma` as the minimum loss reduction for another split. Earlier trials favored `min_child_weight=5` over 3 and 10 on a less regularized depth-8 model. The current model has depth 10, `reg_alpha=4`, and both tree-level and per-node feature sampling, so the useful split threshold may have shifted. I will retest the lower value under the improved configuration.

### Experiment 59 hypothesis — allow somewhat smaller child nodes

Lower `min_child_weight` from 5 to 3 while retaining the current best sampling and regularization. Strong L1 and feature sampling already suppress weak complexity; permitting smaller child Hessian totals may recover useful fine-grained splits. Keep all other parameters fixed.

## Experiment 59 — c3b0c6d — discard

Lowered `min_child_weight` from 5 to 3 on the current best sampling and regularization setup. Eval AUC was 0.7603 (-0.0002), with run status `ok`; I restored 5.

### Experiment 60 hypothesis — moderately stricter child threshold

Raise `min_child_weight` from 5 to 7. The earlier value of 10 was too restrictive on a less regularized model; 7 tests a moderate increase under the current depth-10, L1-regularized, feature-sampled setup. All other parameters remain fixed.

## Experiment 60 — baae952 — discard

Raised `min_child_weight` from 5 to 7. Eval AUC was 0.7602 (-0.0003 versus the best), with run status `ok`; I restored 5.

## Synthesis — runs 51–60

- The best is commit `77fa81a` at Eval AUC 0.7605, up 0.0402 from the 0.7203 baseline. It uses 600 trees, depth 10, `min_child_weight=5`, `reg_lambda=5`, `reg_alpha=4`, learning rate 0.05, `colsample_bytree=0.7`, and `colsample_bynode=0.8`, with native categorical handling and histogram trees.
- Retuning tree-level sampling alongside per-node sampling gave a small gain: 0.7 by tree / 0.8 by node improved by 0.0004. Raising tree sampling to 0.8 reduced the score; by-node values 0.7 and 0.9 did not beat 0.8.
- Full and square-root class-ratio weights tied the unweighted AUC. `max_delta_step=1` and 128 histogram bins were slightly worse. Keep the unweighted default and 256 bins.
- The retested child-weight values 3 and 7 both fell slightly below 5. Alpha 3 and 700 trees also remained below the current best; 600 rounds and L1=4 are retained.
- Per-tree and per-node feature sampling remain the main generalization gains. A moderate row-sampling trial may add useful randomness on top of the current feature subsampling, although an earlier `subsample=0.8` test on an older model lowered AUC.

## Research before Experiment 61 — row subsampling

The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `subsample` as the share of training rows randomly drawn before each boosting step. The [tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) lists row sampling as a way to add randomness and control overfitting. An earlier `subsample=0.8` trial lowered AUC on a less regularized model. The current model has stronger L1 and per-tree/per-node feature sampling, so a milder 0.9 row sample may behave differently.

### Experiment 61 hypothesis — mild row sampling

Set `subsample=0.9` to randomly omit one tenth of training rows each boosting round. This may add useful diversity on top of feature sampling while preserving most of the data per tree. All other parameters remain fixed.

## Experiment 61 — 1cb818b — discard

Set `subsample=0.9`. Eval AUC fell to 0.7593 (-0.0012 versus the best), with run status `ok`; I restored full row sampling.

### Experiment 62 hypothesis — very mild row sampling

Test `subsample=0.95` on the best model. The 0.9 fraction was too aggressive; omitting only 5% of rows may add a small amount of diversity without losing as much training signal.

## Experiment 62 — 7b53029 — discard

Set `subsample=0.95`. Eval AUC was 0.7598 (-0.0007 versus the best), with run status `ok`; I restored full row sampling.

### Experiment 63 hypothesis — near-full row sampling

Test `subsample=0.99`. The 0.9 and 0.95 values lowered AUC; sampling only 1% of rows out may retain any benefit from mild stochasticity while minimizing lost training signal.

## Experiment 63 — b0d3ef5 — keep

Set `subsample=0.99`. Eval AUC rose from 0.7605 to 0.7609 (+0.0004), with run status `ok`. This is the new best; near-full row sampling helped while 0.95 and 0.9 did not.

### Experiment 64 hypothesis — refine near-full row sampling

Raise `subsample` from 0.99 to 0.995. The small gain at 0.99 suggests the useful regularization may be very mild; this tests whether keeping even more training rows preserves or extends the improvement.

## Experiment 64 — e751c61 — discard

Raised `subsample` from 0.99 to 0.995. Eval AUC fell to 0.7603 (-0.0006 versus the best), with run status `ok`; I retained 0.99.

### Experiment 65 hypothesis — sample slightly more rows than the best

Lower `subsample` from 0.99 to 0.985. This intermediate value tests whether a little more row-level randomness than at 0.99 can improve on the narrow near-full-sampling peak.

## Experiment 65 — 4af9e04 — discard

Lowered `subsample` from 0.99 to 0.985. Eval AUC fell to 0.7605 (-0.0004 versus the best), with run status `ok`; I retained 0.99.

### Experiment 66 hypothesis — midpoint above the row-sampling peak

Test `subsample=0.9925`, between the 0.99 best and lower-scoring 0.995 result. This checks whether a slightly milder sample improves further.

## Experiment 66 — 56857e0 — discard

Raised `subsample` from 0.99 to 0.9925. Eval AUC was 0.7607 (-0.0002 versus the best), with run status `ok`; I retained 0.99. The tests at 0.985, 0.9925, and 0.995 all remained slightly below 0.99, so I am moving to a new direction.

## Plateau research before Experiment 67 — boosting rounds after row sampling

The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) describes reducing `eta` as a way to make updates more conservative and recommends more boosting rounds when doing so. The current learning rate remains 0.05, but the new `subsample=0.99` setting improved generalization slightly; this may also change how many rounds are useful. An earlier 700-tree test without row sampling did not help, so I will take a smaller step.

### Experiment 67 hypothesis — add a small number of rounds under mild row sampling

Raise `n_estimators` from 600 to 650 while keeping `subsample=0.99` and the rest of the best configuration fixed. The mild per-round row variation may allow a few more boosting steps before overfitting.

## Experiment 67 — f8f00d0 — discard

Raised `n_estimators` from 600 to 650 with `subsample=0.99`. Eval AUC was 0.7608 (-0.0001 versus the best), with run status `ok`; I restored 600 trees.

### Experiment 68 hypothesis — smaller tree-count increment

Test `n_estimators=625` with the 0.99 row sample. The 650-tree result was only 0.0001 below the best, so a 25-tree increase may retain any benefit without adding as many rounds.

## Experiment 68 — 560ad07 — discard

Raised `n_estimators` from 600 to 625 with `subsample=0.99`. Eval AUC was 0.7608 (-0.0001 versus the best), with run status `ok`; I restored 600 trees.

### Experiment 69 hypothesis — test slightly fewer rounds

Lower `n_estimators` from 600 to 575 while retaining `subsample=0.99`. The 625- and 650-tree variants were each just below the best, so a small reduction may locate the peak more precisely.

## Experiment 69 — 86ca7bc — discard

Lowered `n_estimators` from 600 to 575 with `subsample=0.99`. Eval AUC was 0.7608 (-0.0001 versus the best), with run status `ok`; I restored 600 trees. This is the third consecutive round-count trial within 0.001 AUC that did not improve the best.

## Plateau research before Experiment 70 — depth with mild row sampling

The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says increasing `max_depth` increases model complexity and overfitting risk. Earlier runs showed that feature sampling changed the useful depth: depth 10 was worse than 8 without column sampling, then improved substantially under `colsample_bytree=0.6`. The newer `subsample=0.99` setting adds a small amount of row randomness, so I will test whether it supports a small increase in depth.

### Experiment 70 hypothesis — one more level of tree depth

Raise `max_depth` from 10 to 11 with the current best `subsample=0.99` and feature sampling. The added capacity may capture useful interactions while mild row sampling and L1 regularization limit overfitting. Keep all other parameters fixed.

## Experiment 70 — 0002708 — keep

Raised `max_depth` from 10 to 11 with `subsample=0.99`. Eval AUC rose from 0.7609 to 0.7613 (+0.0004), with run status `ok`. This is the new best.

### Experiment 71 hypothesis — one further depth increment

Raise `max_depth` from 11 to 12 with all other settings fixed. The depth-11 model improved; one further level may capture useful interactions, though the extra complexity could overfit.

## Experiment 71 — b26515a — discard

Raised `max_depth` from 11 to 12 with `subsample=0.99`. Eval AUC was 0.7611 (-0.0002 versus the best), with run status `ok`; I restored depth 11.

### Experiment 72 hypothesis — lightly prune deeper trees

Set `gamma=0.5` with depth 11 and the best sampling/regularization. A small minimum loss reduction requirement may suppress weak extra splits while preserving useful interactions in the deeper trees.

## Experiment 72 — 8668b93 — discard

Set `gamma=0.5` with depth 11. Eval AUC fell to 0.7603 (-0.0010 versus the best), with run status `ok`; I restored the default zero threshold.

### Experiment 73 hypothesis — refine L2 under the new best

Lower `reg_lambda` from 5 to 4 while retaining depth 11 and `subsample=0.99`. Earlier trials favored L2=5 over 3 and 10, but the newer sampling and depth settings may shift the local optimum. Test a nearby value.

## Experiment 73 — eda4cc1 — discard

Lowered `reg_lambda` from 5 to 4 at depth 11 and `subsample=0.99`. Eval AUC was 0.7609 (-0.0004 versus the best), with run status `ok`; I restored L2=5.

### Experiment 74 hypothesis — slightly stronger L2

Raise `reg_lambda` from 5 to 6 under the current best. The nearby value 4 was lower; 6 tests the other side of the previous L2 optimum while retaining the updated depth and row sampling.

## Experiment 74 — 7f05ae9 — discard

Raised `reg_lambda` from 5 to 6 at depth 11. Eval AUC was 0.7604 (-0.0009 versus the best), with run status `ok`; I restored L2=5.

### Experiment 75 hypothesis — test L2 at 4.5

Set `reg_lambda=4.5`. The adjacent settings 4 and 6 both scored below 5; a midpoint checks whether a small reduction from the current best can retain performance.

## Experiment 75 — 9ab0eb1 — discard

Set `reg_lambda=4.5` at depth 11. Eval AUC was 0.7603 (-0.0010 versus the best), with run status `ok`; I restored L2=5.

### Experiment 76 hypothesis — refine L1 on the updated model

Raise `reg_alpha` from 4.0 to 4.5 while keeping the current depth-11 and `subsample=0.99` settings. Earlier tests centered the best L1 near 4; the deeper, mildly row-sampled model may prefer a slightly stronger sparse penalty.

## Experiment 76 — bb8814c — keep

Raised `reg_alpha` from 4.0 to 4.5 with depth 11 and `subsample=0.99`. Eval AUC rose from 0.7613 to 0.7619 (+0.0006), with run status `ok`. This is the new best.

### Experiment 77 hypothesis — continue the L1 refinement

Raise `reg_alpha` from 4.5 to 5.0 while keeping all other settings fixed. The midpoint improved; a modest further increase may strengthen useful sparsity.

## Experiment 77 — 26de1ad — keep

Raised `reg_alpha` from 4.5 to 5.0 with depth 11 and `subsample=0.99`. Eval AUC rose from 0.7619 to 0.7628 (+0.0009), with run status `ok`. This is the new best.

### Experiment 78 hypothesis — continue L1 refinement

Raise `reg_alpha` from 5.0 to 5.5 while keeping all other parameters fixed. The 5.0 value improved substantially; a nearby stronger penalty may further improve generalization.

## Experiment 78 — 7bd8288 — discard

Raised `reg_alpha` from 5.0 to 5.5 with depth 11 and `subsample=0.99`. Eval AUC was 0.7622 (-0.0006 versus the best), with run status `ok`; I restored 5.0.

### Experiment 79 hypothesis — fine-tune L1 near five

Test `reg_alpha=5.25` between the improved 5.0 and lower 5.5 settings. The L1 optimum appears near 5, and this midpoint may retain the gain.

## Experiment 79 — a1486b8 — discard

Raised `reg_alpha` from 5.0 to 5.25 at depth 11. Eval AUC was 0.7618 (-0.0010 versus the best), with run status `ok`; I restored 5.0.

### Experiment 80 hypothesis — test L1 just below the best

Set `reg_alpha=4.75` between the improved 4.5 and best 5.0 values. This checks the lower side of the narrow L1 peak.

## Experiment 80 — 0013c96 — discard

Lowered `reg_alpha` from 5.0 to 4.75 at depth 11. Eval AUC was 0.7620 (-0.0008 versus the best), with run status `ok`; I restored 5.0.

## Synthesis — runs 71–80

- The best is commit `26de1ad` at Eval AUC 0.7628, up 0.0425 from the 0.7203 baseline. It uses 600 trees, depth 11, `min_child_weight=5`, `reg_lambda=5`, `reg_alpha=5`, learning rate 0.05, `subsample=0.99`, `colsample_bytree=0.7`, and `colsample_bynode=0.8`, with native categories and histogram trees.
- Near-full row sampling at 0.99 improved the prior best from 0.7605 to 0.7609. Fractions 0.9, 0.95, 0.985, 0.9925, and 0.995 did not beat it.
- Depth 11 with the new row sample improved to 0.7613; depth 12 fell slightly. Counts 575, 625, and 650 were each just below 600.
- The largest gain in this block came from tuning L1 on the newer model: `reg_alpha=4.5` scored 0.7619 and 5.0 reached 0.7628. Values 4.75, 5.25, and 5.5 were lower, so retain 5.0. Nearby L2 values, a small gamma, and other child thresholds also did not improve the best.
- Restore and leave the branch at `26de1ad`, the best checkpoint. The timed session is complete.
