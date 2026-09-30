# Research log — sep30

## Baseline — 92e43e6

The untouched starter model reached Eval AUC 0.7203. It uses 30 depth-6 trees at learning rate 0.1 and native categorical handling, with only scheduled departure time and distance as numeric features. Training took 1.1 seconds and row-wise evaluation took 30.2 seconds. This is the reference for all changes.

## Research before tuning

The [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) identify depth, child weight and gamma as complexity controls, and row/column sampling and learning rate as controls for overfitting. They also advise increasing rounds when lowering the learning rate. The [categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains one-hot versus partition splits, a later avenue for high-cardinality airports. A [primary study of airline departure delays](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) highlights month, day, carrier, origin, destination and scheduled departure time as relevant predictors. The training file has 200,000 balanced rows, no missing values, 283 origins and destinations, and a scheduled time stored as HHMM.

## Experiment 1 — more boosting rounds (exploration)

Hypothesis: 30 trees leave substantial bias on this 200,000-row problem. Increase only `n_estimators` to 300 at the same learning rate and depth. The XGBoost tuning notes describe the rounds/step-size tradeoff; this probes the rounds side first.

Result: Eval AUC 0.7342 (+0.0139), clear gain. Kept as 81c9904; training 2.6 seconds.

## Experiment 2 — 800 rounds (follow-up)

Hypothesis: the large gain from 30 to 300 trees suggests the ensemble may still be capacity-limited. Increase only `n_estimators` from 300 to 800 to test whether additional rounds help before changing features or regularization.

Result: Eval AUC 0.7273 (-0.0069 versus the best). Additional rounds at learning rate 0.1 overfit or otherwise degrade generalization. Discard 706260e and return to 81c9904.

## Experiment 3 — smaller learning rate (follow-up)

Hypothesis: 800 rounds were excessive at learning rate 0.1, but the [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommend pairing a lower step size with more rounds. Try 600 rounds at 0.05, keeping the total nominal boosting weight comparable to 300 at 0.1.

Result: Eval AUC 0.7359 (+0.0017). Kept as f3cceb5.

## Experiment 4 — day of year (exploration: feature engineering)

Hypothesis: the model currently sees month and day of month only as independent categorical values, requiring many splits to learn date-local effects. The [airline departure delay study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) includes day of year and holiday proximity. Add numeric day of year from each row's calendar fields so adjacent dates can share information. This calculation depends only on each row and fixed calendar offsets.

Result: Eval AUC 0.7381 (+0.0022). Kept as b91bf6b. Calendar locality appears useful.

## Experiment 5 — categorical departure hour (exploration: time encoding)

Hypothesis: raw HHMM time only permits ordered thresholds. A separate categorical hour could let the tree group nonadjacent hours and learn hour-specific interactions more compactly. The [scikit-learn time feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) discusses decomposing time into hour-of-day features. Add an hour category with fixed levels so row-wise evaluation matches training.

Result: Eval AUC 0.7394 (+0.0013), kept as c461628. The extra time representation helps.

## Experiment 6 — route category (exploration: categorical interaction)

Hypothesis: a route's delay propensity can differ from what origin and destination alone explain. The [airline study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) discusses historical route-level predictions, while [XGBoost's categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains partitioned categorical splits. Add a route category using 4,290 levels derived only from training predictors. The same fixed levels will be used for every evaluation row.

Result: Eval AUC 0.7111 (-0.0283); a very large drop. The route category is too sparse or has unstable partitions under these settings. Discard 5be3200 and avoid similarly large direct interaction categories for now.

## Experiment 7 — shallower trees (exploration: model complexity)

Hypothesis: [XGBoost's tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) identify tree depth as a control for overfitting. At 600 rounds, depth 6 may fit noise in airport/date interactions. Try depth 4 with the previously useful date and hour features; this also reduces model complexity.

Result: Eval AUC 0.7387 (-0.0007). Lower depth is close but not better; discard 3ac8d08 because code complexity is unchanged.

## Experiment 8 — depth 5 (follow-up)

Hypothesis: depth 4 loses some useful interactions but is close to depth 6. Depth 5 may retain the useful ones while giving a little more regularization than depth 6. This is a midpoint probe motivated by experiment 7, not an arbitrary repeat.

Result: Eval AUC 0.7395 (+0.0001) with a smaller model. Kept as 2ec4da5.

## Experiment 9 — minimum child weight 5 (exploration: leaf regularization)

Hypothesis: sparse airport/date leaves may be noisy even at depth 5. The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) states that larger `min_child_weight` blocks low-Hessian children. Raise it from 1 to 5 to test whether fewer fragile leaves improve AUC.

Result: Eval AUC 0.7394 (-0.0001). Discard 7ce6c63 because it adds a parameter without improving AUC.

## Experiment 10 — 80% row sampling (exploration: ensemble randomness)

Hypothesis: sampling rows independently for each tree may reduce correlation between trees and improve generalization. The [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) identify `subsample` as a noise-control lever. Test `subsample=0.8`, with all other settings from the best model.

Result: Eval AUC 0.7312 (-0.0083), a large drop. Discard 3d4717d. Sampling may destabilize categorical split estimates on this data.

## Synthesis after 10 experiments

The major capacity gain came from 30 to 300 trees (+0.0139); 800 at the original rate hurt, while 600 at half the rate gained a further 0.0017. Numeric day of year (+0.0022) and categorical departure hour (+0.0013) were the best feature changes. Depth 5 gave a tiny gain over 6. A 4,290-level route category, row subsampling, and 800 high-rate rounds were clearly harmful. Minimum child weight 5 and depth 4 were near misses. Current best: 0.7395, commit 2ec4da5. The leading theory is that smooth calendar structure and enough boosting rounds matter more than richer sparse categories; next test calendar/time representations and categorical split settings.

Fresh research: the [XGBoost categorical parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) says `max_cat_to_onehot` switches low-cardinality predictors from partition splits to single-category splits, while `max_cat_threshold` caps categories in a partition split to limit overfitting. The [scikit-learn time feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) gives several ways to represent periodic time. [Recent airport delay feature research](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) likewise emphasizes departure hour, season, carrier and airports. These suggest changing the split strategy and adding localized time features before trying another sparse route identity.

## Experiment 11 — one-hot category splits for small fields (exploration)

Hypothesis: partition splits across 7–31 calendar, carrier and hour levels may group unrelated values. Set `max_cat_to_onehot=32` so these fields use one-category splits, while 283-level airports remain partitioned. This is a direct test of the split choice described in the [XGBoost categorical guide](https://xgboost.readthedocs.io/en/stable/parameter.html).

Result: Eval AUC 0.7313 (-0.0082). Discard 1f07c22; partitioning small categorical predictors is helpful here.

## Experiment 12 — fewer candidate categories per partition (exploration)

Hypothesis: the high-cardinality airport fields may suffer from noisy partition searches. Set `max_cat_threshold=16` to limit categories considered per partition split, as described in the [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html). This changes airport split regularization while retaining partition splits for the smaller fields that experiment 11 showed are useful.

Result: Eval AUC 0.7427 (+0.0032), kept as f2405df. Constraining categorical partitions is effective.

## Experiment 13 — threshold 8 (follow-up)

Hypothesis: the 16-category cap reduced overfit in airport splits. Try 8 to test whether stronger regularization helps further or begins to lose useful airport groupings. Only this threshold changes.

Result: Eval AUC 0.7424 (-0.0003). A cap of 8 may be slightly too restrictive. Discard 0e1ae72.

## Experiment 14 — threshold 32 (follow-up)

Hypothesis: 8 is slightly worse than 16, so a somewhat larger category search could capture useful airport groups while still regularizing more than the original default. Try `max_cat_threshold=32` to test the other side of the apparent optimum.

Result: Eval AUC 0.7412 (-0.0015). The 16-category cap remains best; discard c74ba7a.

## Experiment 15 — carrier-origin interaction (exploration)

Hypothesis: airline performance at a specific origin may differ from the separate carrier and airport effects. There are 1,551 carrier-origin combinations in training, fewer than the 4,290 routes that failed in experiment 6. With the successful 16-category split cap, a fixed-level carrier-origin category may contribute useful local structure without the same degree of overfitting. This uses only row predictors and train-derived levels.

Result: Eval AUC 0.7364 (-0.0063). Even this smaller interaction category degrades performance. Discard 2ef374f.

## Plateau pause after experiment 15

Three candidates have failed since the 0.7427 gain. Category cap 16 appears near its useful range; direct high-cardinality interactions are unreliable. Research a different feature mechanism before another experiment.

The [airline departure delay study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) explicitly uses holiday proximity. The [2005 calendar](https://www.timeanddate.com/calendar/?year=2005) verifies Memorial Day, Labor Day and Thanksgiving dates; [OPM holiday rules](https://www.opm.gov/policy-data-oversight/pay-leave/pay-administration/fact-sheets/holidays-work-schedules-and-pay) define the major US holidays. This suggests a compact, smooth holiday-distance feature. The [scikit-learn target encoding example](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html) also warns that naive high-cardinality target means overfit without cross-fitting; I will avoid label-derived category lookups in this loop.

## Experiment 16 — distance to major holidays (exploration: calendar effect)

Hypothesis: a day-of-year tree needs several splits to capture multiple localized travel peaks. Add the distance in calendar days to the closest major US travel holiday in 2005 (New Year, Memorial Day, Independence Day, Labor Day, Thanksgiving, Christmas). This encodes a recurring holiday effect compactly and uses only fixed dates plus each row's day of year.

Result: Eval AUC 0.7434 (+0.0007). Kept as 223ef51; the simple calendar calculation earns its small gain.

## Experiment 17 — signed holiday proximity (ablation/follow-up)

Hypothesis: travel patterns often differ before and after a holiday. Replace absolute holiday distance with a signed offset from the nearest holiday, preserving the same one-column complexity while allowing the trees to distinguish those sides directly.

Result: Eval AUC 0.7427 (-0.0007); discard 3dbd66e and restore absolute distance.

## Experiment 18 — scheduled departure minute (exploration: time granularity)

Hypothesis: departure minute within an hour repeats across every hour but is hard to represent using raw HHMM thresholds. Add a numeric `CRSDepTime % 100` feature so the model can learn schedule-minute effects with shared splits across hours. This is a one-row transformation consistent with the [scikit-learn time feature guidance](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html).

Result: Eval AUC 0.7433 (-0.0001). The additional column costs complexity without a gain; discard 0fa76c2.

## Experiment 19 — distance from year boundary (exploration: cyclic season)

Hypothesis: winter conditions span late December and early January. A numeric day of year puts those dates at opposite ends, requiring two splits to share seasonal effects. Add distance to the nearest year boundary, `min(day-1, 365-day)`, to let one split capture the winter window. The [scikit-learn time feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) motivates periodic time representations.

Result: Eval AUC 0.7435 (+0.0001). Kept as 6bf8ffe, though the gain is small and evaluation became about three seconds slower.

## Experiment 20 — hour of week category (exploration: temporal interaction)

Hypothesis: delay patterns may depend jointly on weekday and departure hour (for example, weekday morning peaks). A fixed 168-level hour-of-week category can express that combination directly, unlike separate split paths through weekday and hour. The [scikit-learn cyclical time example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) analyzes hour-of-week demand structure. This feature uses only each row's weekday and scheduled hour.

Result: Eval AUC 0.7415 (-0.0020), with evaluation rising to 50 seconds. Discard 476792a.

## Synthesis after 20 experiments

The best improvement in the second group was capping categorical partition candidates at 16 (+0.0032). Smaller and larger caps were worse. Absolute holiday proximity added +0.0007; signed proximity lost that gain. Year-boundary distance added only +0.0001. Direct carrier-origin and hour-of-week categories hurt, as did one-hot splits for small categorical fields. The current best is 0.7435 at 6bf8ffe. The pattern suggests smooth time/calendar features and regularized native category partitions generalize better than explicit crossed categories. Next inspect which features the model uses, then explore training controls and simplifying redundant calendar columns.

Fresh research: the [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `max_bin` as the number of numeric histogram buckets and says increasing it improves split optimality at greater computation cost. The [XGBoost Python guide](https://xgboost.readthedocs.io/en/stable/python/python_intro.html) describes early stopping with a validation set as a way to choose boosting rounds. For later experiments, `grow_policy` and `max_leaves` offer a different capacity shape. Inspection of the saved best model's built-in feature importances shows CRSDepTime at 0.5556, well above other features, so departure-time resolution deserves a direct test.

## Experiment 21 — 512 numeric histogram bins (follow-up)

Hypothesis: the 1,162 distinct scheduled departure times are compressed into the default 256 numeric bins while CRSDepTime is the dominant model feature. Set `max_bin=512` so trees can consider finer departure-time boundaries. The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes this accuracy/computation tradeoff.

Result: Eval AUC 0.7431 (-0.0004). Extra resolution does not help; discard 78cd637.

## Experiment 22 — 128 numeric histogram bins (follow-up)

Hypothesis: finer bins slightly hurt, perhaps because exact scheduled minutes are noisy. Halve the default `max_bin` from 256 to 128 to test whether modest smoothing of numeric features improves generalization. This probes the opposite direction of experiment 21.

Result: Eval AUC 0.7426 (-0.0009). The default 256 bins remain best; discard 40b3087.

## Experiment 23 — early stopping on a training split (exploration: training procedure)

Hypothesis: the ideal boosting round count depends on the feature and category settings. Use 10% of `train.csv` as an internal validation set and XGBoost's AUC early stopping to choose from up to 1,500 rounds, as described in the [official XGBoost Python guide](https://xgboost.readthedocs.io/en/stable/python/python_intro.html). The external Eval AUC remains the only experiment metric; no other data are touched and there is no retraining.

Result: best internal iteration 514, external Eval AUC 0.7405 (-0.0030). The training-data reduction or validation selection outweighs the benefit here. Discard 02a9058.

## Experiment 24 — loss-guided tree growth (exploration: tree architecture)

Hypothesis: depthwise growth spends splits across branches that may not need them, while the [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) says `lossguide` grows the highest-gain node next. Use up to 32 leaves, matching depth 5's maximum leaf count, but allow unequal branch depths. This tests tree shape rather than total leaf capacity.

Result: Eval AUC 0.7425 (-0.0010). The original depthwise growth works better; discard 42301c4.

## Experiment 25 — stronger L2 leaf regularization (exploration)

Hypothesis: individual leaf scores may be too aggressive with 600 rounds. The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) says `reg_lambda` makes leaf weights more conservative. Raise it from its default 1 to 5, retaining the best category cap and features.

Result: Eval AUC 0.7456 (+0.0021), kept as 3f9ed33. Shrinking individual leaf effects helps generalization.

## Experiment 26 — L2 penalty 10 (follow-up)

Hypothesis: the jump from lambda 1 to 5 improved AUC; test 10 to see whether stronger shrinkage continues the trend. This changes only `reg_lambda`, not the learning rate or tree count.

Result: Eval AUC 0.7455 (-0.0001). Discard a7a0de8; lambda 5 remains best.

## Experiment 27 — split-loss penalty (exploration: split regularization)

Hypothesis: lambda 5 helped by restraining leaves. `gamma` is a different control: the [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) says it requires a minimum loss reduction for a split. Test `gamma=1` to prune weak refinements while retaining the successful L2 penalty.

Result: Eval AUC 0.7442 (-0.0014); discard eca9ba5. A split-gain threshold of 1 is too restrictive.

## Experiment 28 — remove day-of-month category (ablation/simplification)

Hypothesis: numeric day of year, holiday distance and month already encode most date information. The 31-level day-of-month category may encourage spurious month-day patterns. Remove it from model predictors while still using it to compute day of year; this simplifies the feature set and tests redundancy.

Result: Eval AUC 0.7419 (-0.0037); discard f8360d2. Day of month has unique signal despite the other calendar features.

## Experiment 29 — remove year-boundary distance (ablation/simplification)

Hypothesis: year-boundary distance delivered only +0.0001 before the L2 penalty was added. Test whether it remains useful under the stronger model regularization. Removing it cuts three lines and speeds row-wise preparation.

Result: Eval AUC 0.7452 (-0.0004 from the highest) and evaluation fell from about 44.5 to 41.3 seconds. This is close enough to count as equal given the simpler, faster feature code. Keep b17dad2 as the working branch; 3f9ed33 retains the highest raw Eval AUC so far (0.7456).

## Experiment 30 — remove holiday-distance lookup (ablation/simplification)

Hypothesis: with day of year, month, day of month and L2 regularization, the holiday-distance lookup may be redundant. Removing it saves five lines of fixed lookup logic and one row-wise map operation. Compare against the simpler b17dad2 model.

Result: Eval AUC 0.7442 (-0.0010 versus the current working model), too much loss for this simplification. Discard 6feaff3 and restore holiday distance.

## Synthesis after 30 experiments

Finer or coarser numeric bins, internal early stopping, and loss-guided growth all failed to improve the best model. `reg_lambda=5` gave +0.0021; 10 was about equal but not better, and `gamma=1` hurt. Removing day of month caused a large drop. Removing year-boundary distance cost only 0.0004 while making the code smaller and evaluation faster, so b17dad2 (0.7452) is the working commit; 3f9ed33 remains the highest raw AUC (0.7456). Removing holiday distance cost 0.0010 and was discarded. The strongest explanation remains that model variance from leaf scores and category partitions needed restraint while calendar effects carry real signal. Next research sampling, L1 regularization and diverse model combinations.

Fresh research: the [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `reg_alpha` as L1 regularization on leaf weights and distinguishes column sampling per tree, level and node. The [DART tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) describes tree dropout to reduce overfitting, though it can slow training. The [scikit-learn soft voting documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html) supports probability averaging for diverse classifiers. I will first test simpler single-model controls before paying the complexity cost of an ensemble.

## Experiment 31 — L1 leaf regularization (exploration)

Hypothesis: L2 leaf shrinkage helped; adding a modest L1 penalty may suppress weak leaf corrections while retaining strong ones. Test `reg_alpha=1` on the working model, as described in the [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html).

Result: Eval AUC 0.7467 (+0.0015 versus working model, +0.0011 versus highest earlier score), kept as 7271ab4. Both L1 and L2 penalties help.

## Experiment 32 — stronger L1 penalty (follow-up)

Hypothesis: alpha 1 improved AUC. Test alpha 3 to learn whether more aggressive suppression of small leaf scores continues to help or overshoots. All other settings stay fixed.

Result: Eval AUC 0.7500 (+0.0033), kept as 8fb26a6. Suppressing weak leaf corrections appears important on this data.

## Experiment 33 — L1 penalty 6 (follow-up)

Hypothesis: the gain from alpha 1 to 3 is large. Double the L1 penalty to 6 to locate where the improvement begins to saturate or reverse.

Result: Eval AUC 0.7524 (+0.0024), kept as b7de7fd. Stronger L1 still helps.

## Experiment 34 — L1 penalty 12 (follow-up)

Hypothesis: alpha 6 continues the trend. Double it to 12 to probe the boundary between useful suppression of noisy leaves and underfitting. The one-parameter change remains directly motivated by experiment 33.

Result: Eval AUC 0.7521 (-0.0003), so the useful range appears around alpha 6–12. Discard 761a1d0 and restore alpha 6.

## Experiment 35 — 900 rounds under strong L1 (follow-up)

Hypothesis: strong L1 reduces overfitting and might permit more boosting rounds than the current 600. Test 900 rounds at the same learning rate and alpha 6. This differs materially from the earlier 800-round test, which used much weaker regularization and a higher learning rate.

Result: Eval AUC 0.7550 (+0.0026), kept as 55d24a0. More rounds now help with strong L1 regularization.

## Experiment 36 — 1,400 rounds (follow-up)

Hypothesis: the gain from 600 to 900 rounds suggests the regularized model remains capacity-limited. Increase to 1,400 while keeping alpha 6 and learning rate 0.05 to look for saturation or overfitting.

Result: Eval AUC 0.7569 (+0.0019), kept as ee840c6. The strong L1 penalty continues to support more boosting.

## Experiment 37 — 2,200 rounds (follow-up)

Hypothesis: improvement has slowed but not stopped at 1,400 rounds. Increase to 2,200 to locate the peak before exploring other features or penalties. The observed trend motivates the larger step.

Result: Eval AUC 0.7579 (+0.0010), kept as fe9b741. Still improving, with 9.6 seconds of training.

## Experiment 38 — 3,500 rounds (follow-up)

Hypothesis: gains are diminishing but remain positive. Try 3,500 rounds to locate saturation while training is still comfortably below the 60-second limit. Keep alpha 6 and all features fixed.

Result: Eval AUC 0.7584 (+0.0005), kept as 52ecf7f. Training took 14.4 seconds; the AUC gain is small but code complexity is unchanged.

## Experiment 39 — 5,000 rounds (follow-up)

Hypothesis: the improvement from 2,200 to 3,500 rounds is small but positive. Test 5,000 to see whether the score peaks or remains underfit. Expected training time is below the 60-second ceiling; if the gain is negligible, prefer the smaller ensemble.

Result: Eval AUC 0.7581 (-0.0003), with training up to 20.9 seconds. Discard 0b5ecae; 3,500 rounds are enough at alpha 6.

## Experiment 40 — stronger L1 with 3,500 rounds (follow-up)

Hypothesis: alpha 12 was slightly worse than 6 at only 600 rounds, but it may need more boosting steps to compensate for stronger shrinkage. Test alpha 12 at the now-favored 3,500 rounds. This probes an interaction between regularization and ensemble length, not another search of alpha on the old short ensemble.

Result: Eval AUC 0.7591 (+0.0007), kept as de30335. Stronger L1 helps once enough rounds offset its slower learning.

## Synthesis after 40 experiments

L1 regularization became the main driver of this block: alpha 1, 3 and 6 raised AUC substantially on the 600-round model. With alpha 6, increasing rounds to 900, 1,400, 2,200 and 3,500 continued to help, reaching 0.7584; 5,000 declined slightly. At 3,500 rounds, alpha 12 edged up to 0.7591. Stronger L1 and more boosting rounds interact: settings that were too slow at 600 rounds can improve the longer model. Current best is de30335 (0.7591). Next explore whether alpha 12 needs a longer ensemble or a lower step size, then revisit alternative regularization and feature representations.

Fresh research: the [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) advise pairing smaller learning rates with more rounds. The [DART paper](https://proceedings.mlr.press/v38/korlakaivinayak15.html) identifies overspecialized late trees as a reason that long boosting ensembles can overfit and proposes dropout. The [XGBoost DART tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) warns that dropout can slow training, so it remains a later option if a simple long-ensemble adjustment stops helping.

## Experiment 41 — 5,000 rounds under alpha 12 (follow-up)

Hypothesis: the stronger L1 penalty has slowed learning enough that the 5,000-round setting, which was excessive at alpha 6, may now improve AUC. Test this interaction directly by changing only the round count from the 0.7591 model.

Result: Eval AUC 0.7587 (-0.0004). More rounds at the same rate do not help; discard 3d6008f.

## Experiment 42 — smaller learning rate with 5,000 rounds (follow-up)

Hypothesis: the 5,000-round model may overfit because each update is too large. The [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) suggest a smaller `eta` with more rounds. Test 5,000 rounds at learning rate 0.03 and alpha 12, giving a lower total nominal step than 3,500 at 0.05.

Result: Eval AUC 0.7591, exactly tied at the reported precision, but 5,000 rounds and a lower rate increase training time without simplifying code. Discard 73a2b2a.

## Experiment 43 — depth 6 under strong regularization (exploration)

Hypothesis: alpha 12 suppresses weak deep leaves. The earlier depth-6 model predated L1 regularization, so its slight disadvantage may no longer hold. Restore depth 6 on the best 3,500-round model to test whether deeper airport/time interactions now help.

Result: Eval AUC 0.7597 (+0.0006), kept as ad96767. Stronger regularization permits slightly deeper useful interactions.

## Experiment 44 — depth 7 (follow-up)

Hypothesis: depth 6 helped under alpha 12; depth 7 may capture additional airport, carrier and calendar interactions while L1 limits noisy leaves. Change only max depth to probe where that gain stops.

Result: Eval AUC 0.7589 (-0.0008) and more training time; discard 252544f. Depth 6 is the current best.

## Experiment 45 — tighter category cap under depth 6 (exploration)

Hypothesis: the deeper, longer model may overfit airport partitions differently from the earlier 600-round depth-5 model. Test `max_cat_threshold=8` under the current strong L1 setting. This revisits a previously close setting in a materially changed model regime.

Result: Eval AUC 0.7596 (-0.0001). Discard 599a272; category cap 16 remains best.

## Experiment 46 — L2 penalty 10 with L1 penalty 12 (exploration)

Hypothesis: the longer depth-6 model might still benefit from stronger smooth shrinkage alongside L1 sparsity. Earlier lambda 10 was nearly equal to 5 before the long model existed. Test lambda 10 now, keeping alpha 12 and all structural settings fixed.

Result: Eval AUC 0.7594 (-0.0003). Discard 2bc8cc4. The last three experiments were close discards, so pause for targeted research before the next change.

Plateau research: the [XGBoost interaction-constraints tutorial](https://xgboost.readthedocs.io/en/release_1.5.0/tutorials/feature_interaction_constraint.html) notes that deep trees may learn spurious interactions, but also that domain-informed constraints can help. A [flight-delay feature study](https://www.sciencedirect.com/science/article/pii/S2772415822000050) found departure time and carrier important, consistent with this model's time-dominated feature importance. The [scikit-learn VotingClassifier documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html) describes averaging predicted probabilities from classifiers. Since depth 5 and depth 6 each work well but likely make different errors, test a small soft-voting ensemble before imposing hand-written interaction rules.

## Experiment 47 — average depth-5 and depth-6 models (exploration: ensemble)

Hypothesis: averaging two strong models with different tree depths may cancel some variance in their predictions. Train both on the same allowed training data under alpha 12, then expose their mean `predict_proba` through the final model object. This follows the probability-averaging method described in the [scikit-learn ensemble documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html). The complexity cost is higher, so only a meaningful AUC gain would justify keeping it.

Result: Eval AUC 0.7603 (+0.0006), artifact 50.2 MB, training 30.8 seconds and evaluation 43.5 seconds. Kept as 019223f because the averaging code is concise and the external AUC improved, but a third member needs to earn its extra cost.

## Experiment 48 — add a tighter-category third model (follow-up)

Hypothesis: the depth-6 model with category cap 8 scored 0.7596 alone and may make different errors from the cap-16 models. Add it to the current equal-probability average to test whether split-strategy diversity outweighs the extra training and artifact size. Training should remain under 60 seconds.

Result: Eval AUC 0.7607 (+0.0004), artifact 79.4 MB, training 48.6 seconds. Kept provisionally as 1be96bd because it improved the score, but the extra model is costly and needs an ablation.

## Experiment 49 — remove depth-5 member (ablation/simplification)

Hypothesis: the two depth-6 models with different category caps may capture most of the 3-model ensemble's gain. Remove the depth-5 member and average only those two to test whether we can retain or improve AUC while cutting a third of the model size and training time.

Result: Eval AUC 0.7606 (-0.0001), artifact 58.8 MB versus 79.4 MB, training 33.8 seconds versus 48.6 seconds. Keep 6677757 as a clear simplicity win with essentially equal AUC. The 3-model commit 1be96bd retains the highest raw AUC by 0.0001.

## Experiment 50 — per-node column sampling (exploration: variance control)

Hypothesis: scheduled departure time dominates the model, and different categorical-cap models may still be highly correlated. The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) says `colsample_bynode` samples columns for each split. Set it to 0.8 in both ensemble members to encourage alternative airport/calendar paths and potentially reduce prediction variance.

Result: Eval AUC 0.7604 (-0.0002), with an extra parameter and no simplicity gain. Discard 5a3efd4.

## Synthesis after 50 experiments

Under the long alpha-12 model, depth 6 improved AUC to 0.7597; depth 7 hurt. Changing category cap to 8 or L2 from 5 to 10 gave close misses. A two-model probability average of depth 5 and 6 reached 0.7603; adding a cap-8 depth-6 member reached 0.7607, but removing depth 5 retained 0.7606 with substantially less time and artifact size. Node-level column sampling did not help. The current working model is the two-member category-cap ensemble at 6677757 (0.7606); the three-member ensemble at 1be96bd retains the highest raw AUC by only 0.0001. The next search should seek a different source of model diversity or a compact row-level feature that earns its evaluation cost.

Fresh research: a [flight-delay study](https://www.ideals.illinois.edu/items/112302/bitstreams/367637/data.pdf) represents recurring flight patterns using airline, airports, weekday and departure hour together. A [recent feature study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) describes carrier-specific practices and the compounding of delays later in the day. The [scikit-learn time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) emphasizes hour-of-day effects. Rather than reproduce a very sparse full flight identity, test just a carrier-by-hour category with roughly 480 potential levels.

## Experiment 51 — carrier by departure hour (exploration: feature interaction)

Hypothesis: the same departure hour may have different delay risk by airline because schedules and turnaround practices differ. Add one fixed-level category combining carrier and scheduled hour, fitted from training predictors only. Strong L1 regularization and the two category-cap models may control the overfitting that hurt earlier interaction categories.

Result: Eval AUC 0.7606, exactly tied at reported precision, but with six more lines, a 63.5 MB artifact and 48-second evaluation. Discard 0799c48; the extra interaction does not earn its cost.

Feature research: an [airport time-profile study](https://www.nature.com/articles/s41598-024-68884-9) treats schedule timing as an airport-specific pattern, and a [departure congestion study](https://www.sciencedirect.com/science/article/pii/S096969970600007X) discusses airport peak-period scheduling. The experiment instructions explicitly permit lookups fitted on `train.csv` and applied per row. I will test a simple origin-specific median schedule offset, without using row counts or labels.

## Experiment 52 — time versus origin median (exploration: train-fitted lookup)

Hypothesis: a 16:00 flight can be late in an airport's operating day at one origin but ordinary at another. Fit each origin's median scheduled departure time on `train.csv` predictors, then add the flight's difference from that fixed median. This is identical whether `prepare` receives one row or the full training frame.

Result: Eval AUC 0.7595 (-0.0011), with slower evaluation. Discard f37b235. The raw time plus origin category already carry the useful structure.

## Experiment 53 — cyclic annual phase (exploration: time representation)

Hypothesis: late December and early January share seasonal conditions. The [scikit-learn time feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) recommends sine/cosine coordinates for periodic values. Add sine and cosine of day of year to let the tree share broad seasonal effects across the year boundary while retaining raw day of year for local effects.

Result: Eval AUC 0.7615 (+0.0009), kept as 2c53d19. Both model members use the smooth annual coordinates effectively enough to outweigh three lines of code and about four seconds of evaluation.

## Experiment 54 — remove annual sine (ablation/simplification)

Hypothesis: cosine directly groups late December with early January, while raw day of year retains direction around the annual cycle. Remove the annual sine column to test whether the one-coordinate representation retains the gain with less work per row.

Result: Eval AUC 0.7608 (-0.0007), too much loss for deleting one line. Discard 0065794; both cyclic coordinates appear useful.

## Experiment 55 — cyclic daily phase (exploration: time representation)

Hypothesis: late-night and early-morning flights can share operational conditions, but raw HHMM and categorical hour place them at opposite ends of the day. Add sine and cosine of scheduled minutes since midnight, analogous to the successful annual cyclic features and the [scikit-learn time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html).

Result: Eval AUC 0.7602 (-0.0013) with evaluation rising to 52 seconds. Discard e74eaba. Annual periodicity helped, daily periodicity did not.

Inspection of both saved best-model members after experiment 55 shows that Month, Origin, DepHour and Dest have the largest built-in importances; Distance is low. An [airport network study](https://diposit.ub.edu/dspace/bitstream/2445/193698/1/729577.pdf) discusses how network structure and route design relate to delays. A numeric summary of each airport's typical route length may help share information across sparse airport categories. Such summaries will be fitted from training predictors only, with no row counts or target values.

## Experiment 56 — airport median route distance (exploration: train-fitted lookup)

Hypothesis: airports differ in their mix of short and long routes, which may affect operations even after the individual flight's distance is known. Add origin and destination median route distances fitted on `train.csv` predictors, then map them per row. This gives the model a smooth airport-profile signal without leaking labels or using prohibited counts.

Result: Eval AUC 0.7609 (-0.0006), with evaluation around 51 seconds. Discard 127a0ff. Three recent feature additions or simplifications have failed to improve the best, so research a new seasonal encoding before continuing.

Plateau research: a [flight-delay feature-engineering paper](https://www.mdpi.com/2079-9292/13/24/4910) explicitly uses week of year to capture seasonal and holiday trends; a [multi-year airport study](https://jairm.org/index.php/jairm/article/view/22/63) reports annual delay cycles. The annual sine/cosine gain suggests some seasonal information remains beyond month and day of year. A 53-level week category can group nonadjacent weeks with similar risk while retaining the original date features.

## Experiment 57 — categorical week of year (exploration: seasonal grouping)

Hypothesis: the model may benefit from pooling similar weeks across different parts of the year, such as winter and summer peaks. Add a fixed 53-level categorical week index derived from each row's day of year. The existing category-cap setting limits split complexity.

Result: Eval AUC 0.7619 (+0.0004), kept as 3b6fe6d. Week-level seasonality appears useful enough for one line of code.

## Experiment 58 — Monday-aligned week category (follow-up)

Hypothesis: the previous seven-day blocks start on January 1, 2005 (Saturday). Aligning weeks to Monday may better pool flights with the same weekly travel structure and holiday timing. In 2005, January 3 is the first Monday, so use that as week 1 while retaining a separate two-day stub for January 1–2.

Result: Eval AUC 0.7621 (+0.0002), kept as b614fa4. The calendar-aligned weekly grouping is slightly better.

## Experiment 59 — two-week season blocks (follow-up)

Hypothesis: 53 week categories may be noisier than needed for broad seasonal effects. Pool adjacent weeks into two-week blocks aligned to the same Monday calendar, roughly halving cardinality while preserving travel-season structure. This tests the granularity of the useful week feature.

Result: Eval AUC 0.7616 (-0.0005). Weekly granularity remains more useful; discard e9a2d18.

## Experiment 60 — numeric day of month (exploration: ordered calendar feature)

Hypothesis: day of month was important enough that removing it cost 0.0037, but it currently appears only as a categorical field and inside day of year. Add its numeric 1–31 value so contiguous ranges such as month-end can be represented by one threshold while keeping the categorical version for noncontiguous patterns.

Result: Eval AUC 0.7624 (+0.0003), kept as b088416. The extra ordered view is small but useful.

## Synthesis after 60 experiments

Carrier-hour interaction, origin-relative time and airport median distance did not help. Annual sine/cosine raised AUC to 0.7615, and both coordinates were needed. Daily sine/cosine hurt. A categorical week of year helped further, especially when aligned to Mondays, reaching 0.7621; coarsening to two-week blocks hurt. Numeric day of month raised the score to 0.7624. The strongest remaining pattern is calendar structure: trees benefit from multiple representations of the same date at different scales. Current best and working commit: b088416 (0.7624). Next test other low-cost ordered calendar views and whether the two-model ensemble still earns its complexity after these feature gains.

Fresh research: a [flight-delay feature-engineering study](https://www.mdpi.com/2079-9292/13/24/4910) highlights day of month, month and week of year as distinct temporal signals. A [flight-schedule analysis](https://www.sciencedirect.com/science/article/pii/S2666827021000517) describes periodic calendar vectors at several scales. The success of numeric day of month suggests another ordered representation may help without replacing the categorical fields.

## Experiment 61 — numeric month alongside category (exploration)

Hypothesis: month is the most important feature in both ensemble members, but categorical partitioning may not efficiently express contiguous seasonal spans. Add an ordered month number 1–12 while retaining the categorical month and annual sine/cosine features. This is a two-line feature with row-invariant fixed mapping.

Result: Eval AUC 0.7622 (-0.0002) and slower evaluation. Discard ed0a7d3; annual sine/cosine and day of year likely already supply the ordered view.

## Experiment 62 — numeric day of week alongside category (follow-up)

Hypothesis: the business-week sequence may have contiguous risk patterns (for example, Monday through Friday) that category partitions learn less efficiently. Add ordered weekday 1–7 while keeping the categorical weekday. This tests the same representation idea on a distinct calendar cycle after numeric month failed.

Result: Eval AUC 0.7625 (+0.0001), kept as 18f9729. The gain is tiny and adds two mapping lines plus about two seconds of evaluation; revisit if later ablations suggest it is redundant.

## Experiment 63 — remove cap-8 ensemble member (ablation/simplification)

Hypothesis: annual, weekly and ordered date features may have reduced variance enough that the second ensemble member is no longer worth its cost. Run the same training script with only the cap-16 model in the averaging wrapper. If AUC is about equal, later remove the wrapper too for a direct single-model implementation.

Result: Eval AUC 0.7613 (-0.0012), artifact 29.5 MB and training 19.3 seconds. The AUC loss is material, so discard fcf2b9f and retain the two-model ensemble.

## Experiment 64 — shallower models with richer date features (ablation/simplification)

Hypothesis: the new annual and weekly features may let depth-5 trees express useful patterns that previously required depth 6. Test two depth-5 models at category caps 16 and 8. If AUC remains close, smaller trees could cut artifact size and training cost.

Result: Eval AUC 0.7618 (-0.0007), artifact 41.3 MB and 30-second training. The simpler models lose more than the speed and size savings justify; discard c6a2567.

## Experiment 65 — hybrid depth and category cap (exploration: ensemble diversity)

Hypothesis: both-depth-5 lost some capacity, but a depth-5 cap-8 model may complement the current depth-6 cap-16 model more than two depth-6 models do. Test that pair to isolate whether diversity across both depth and categorical partition strength improves the probability average.

Result: Eval AUC 0.7624 (-0.0001), artifact 50.2 MB rather than 58.4 MB and training 33.1 rather than 36.3 seconds. Keep 1cfff61 as a simpler working model with essentially the same score. Raw highest remains 18f9729 at 0.7625.

## Experiment 66 — cap 12 for depth-5 member (follow-up)

Hypothesis: the depth-5 model already has fewer leaves, so the category cap of 8 might be too restrictive. Raise only its cap to 12, between the current two members' 8 and 16, to test whether more useful airport groups can be learned without losing ensemble diversity.

Result: Eval AUC 0.7624, tied at reported precision with no simplification. Discard bfca5be.

## Experiment 67 — cap 16 for both depths (follow-up)

Hypothesis: the 8-to-12 change was neutral. Test whether giving the shallower member the full 16-category partition capacity helps. This produces a depth-diverse ensemble with the same category cap, revisiting a pair that predated the recent calendar features.

Result: Eval AUC 0.7619 (-0.0005), so the tighter cap remains useful for the shallow model. Discard 883451a.

## Experiment 68 — L1 penalty 18 (follow-up: regularization under richer features)

Hypothesis: annual, weekly and numeric calendar features add split opportunities. A stronger L1 penalty may suppress weak leaves from those extra features while leaving the strong seasonal effects. Raise alpha from 12 to 18 in both hybrid ensemble members, keeping training time within the per-run limit.

Result: Eval AUC 0.7599 (-0.0025); alpha 18 is too aggressive despite its smaller 31.9 MB artifact. Discard bc19288.

## Experiment 69 — L1 penalty 8 (follow-up)

Hypothesis: stronger L1 lost too much signal. The best alpha for the richer feature set may be below 12 rather than above it. Test alpha 8 in both hybrid members; this is a directional response to experiment 68.

Result: Eval AUC 0.7626 (+0.0002 above the previous raw highest), kept as 39b2534. The stronger model uses a 59.8 MB artifact versus 50.2 MB at alpha 12, but changes no code complexity.

## Experiment 70 — L1 penalty 10 (follow-up)

Hypothesis: alpha 8 narrowly beat 12, while alpha 18 clearly hurt. Test the midpoint alpha 10 to locate the best regularization level for the current calendar-rich hybrid model. This is a bracketed comparison rather than an unrelated tweak.

Result: Eval AUC 0.7629 (+0.0003), artifact 54.4 MB, kept as aed1c3e. Alpha 10 is the best tested L1 setting for this feature-rich pair.

## Synthesis after 70 experiments

Removing an ensemble member cost 0.0012 AUC, so the paired models remain useful. Both-depth-5 and same-cap pairs lost accuracy. The depth-6 cap-16 plus depth-5 cap-8 pair preserved almost all AUC while reducing size and training. With the richer calendar features, alpha 18 clearly underfit, alpha 8 narrowly improved on 12, and alpha 10 reached the current best 0.7629. Ordered month did not help; ordered weekday did, but only by 0.0001. The strongest result is still from calendar representation plus sensible L1 regularization, with ensemble diversity giving a smaller but repeatable gain. Only a few minutes remain, so the next experiment should be a focused bracket around alpha 10 rather than a high-cost new architecture.

Fresh research after 70 experiments: the [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) distinguishes L1 leaf shrinkage from `min_child_weight`, which blocks splits with too little Hessian support. Since the richer date features increase split opportunities, a small child-weight floor is a different, targeted form of regularization. The current best alpha 10 is already inside the narrow productive L1 range, so test the new control once before the clock expires.

## Experiment 71 — minimum child weight 2 (exploration: split support)

Hypothesis: a few leaf splits on rare airport-calendar combinations may be weakly supported even after L1 shrinkage. Set `min_child_weight=2` in both ensemble members, a small change from the default 1, to filter those splits without the stronger effect of 5 that was tested much earlier under a different model.

Result: Eval AUC 0.7630 (+0.0001), artifact 54.0 MB, training 33.3 seconds and evaluation 55.6 seconds. Kept as 78b7ef8; the branch is at the highest measured Eval AUC.

## Final summary

Best Eval AUC: **0.7630**, commit **78b7ef8**. The untouched baseline was 0.7203, for a gain of 0.0427. The kept model averages two XGBoost classifiers with different depths and categorical partition caps. It uses 3,500 rounds at learning rate 0.05, strong L1 and moderate L2 regularization, and row-level calendar features: day of year, holiday distance, annual sine/cosine, Monday-aligned week, numeric day of month and weekday, and categorical departure hour. All feature lookups are fixed from the allowed training file or calendar constants; evaluation remained row-wise through the unmodified harness.

What worked: enough boosting rounds paired with L1 regularization; a 16-category partition cap; cyclic and weekly calendar views; and averaging two differently structured models. What did not: very sparse route or carrier-origin identities, row sampling, one-hot splits for small categorical fields, large numeric-bin changes, naive early stopping on a smaller training subset, and several redundant time and airport-profile features. Next I would test whether the two ensemble members should have different regularization strengths or whether a small number of calendar features can be removed without losing AUC. The holdout set remains untouched for the human's post-run evaluation.
