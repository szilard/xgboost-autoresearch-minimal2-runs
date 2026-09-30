# sep30 experiment log

## Baseline — 92e43e6

Unchanged starter model: 30 trees, depth 6, learning rate 0.1, native categorical features. Eval AUC 0.7203; 31.6 s total (1.1 s training, 30.5 s evaluation). The clock started after branch creation and results initialization.

## Initial research

- XGBoost's [parameter tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) suggests managing complexity with tree depth and child weight, adding row/column sampling to reduce overfitting, and using more rounds when reducing the learning rate.
- The [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) documents depth, child weight, sampling and categorical split parameters. Its `auto` tree method uses `hist`.
- XGBoost's [categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) describes native categorical splits and the one-hot versus partition threshold.
- [Air travel delay feature engineering](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) identifies time of day, weekday, season, carrier and route as relevant predeparture feature families. Any use here must rely solely on the available train columns and preserve one-row scoring semantics.

## Experiment 1 hypothesis — more boosting rounds (exploration)

At learning rate 0.1, 30 depth-6 trees may underfit. Try 200 trees while holding all other settings fixed. The XGBoost tuning guide notes that reducing the step size requires more boosting rounds; more rounds may help even at the current rate. Compare Eval AUC and training time to baseline.

Result: 2e17a0b, Eval AUC 0.7345 (+0.0142), 32.9 s total and 2.0 s training. Kept. The large gain suggests the starter was underfit.

## Experiment 2 hypothesis — extend to 500 rounds (follow-up)

Keep the same learning rate and depth, extending 200 to 500 rounds. This tests whether the substantial first gain is still on an upward learning curve or whether overfitting has begun. Training is far below the one-minute cap.

Result: dc3ed1f, Eval AUC 0.7312 (-0.0033 versus 200), 34.5 s total. Discarded and reset to 2e17a0b. Excess rounds at this depth/rate hurt generalization.

## Experiment 3 hypothesis — 120 rounds (follow-up)

Test 120 rounds at unchanged depth and learning rate. The optimum may occur before 200; this isolates the round-count effect without adding regularization or changing the feature representation.

Result: c79dbf8, Eval AUC 0.7317 (-0.0028 versus 200), 32.3 s total. Discarded and reset to 2e17a0b. The best tested round count is 200, between 120 and 500.

## Experiment 4 hypothesis — shallower trees (exploration)

Test depth 4 instead of 6 with 200 rounds. Per the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html), lower depth reduces model complexity and may improve generalization on the limited predeparture features. This isolates depth at the current best round count.

Result: 5a4bada, Eval AUC 0.7317 (-0.0028 versus depth 6), 32.3 s total. Discarded and reset to 2e17a0b. Simpler trees at unchanged rounds underfit; feature construction is a more promising next direction.

## Plateau research

The [XGBoost categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains that native categorical splits can partition values with similar leaf responses. This suggests testing its partition threshold later, especially for carrier, origin and destination. A [flight-delay feature study](https://www.mdpi.com/2079-9292/13/24/4910) specifically derives departure hour and minute from `CRSDepTime` in HHMM form to expose daily patterns. Because the starter includes raw HHMM only, hour extraction is a low-cost, row-stable first feature trial.

## Experiment 5 hypothesis — scheduled departure hour (exploration)

Add `DepHour = CRSDepTime // 100` inside `prepare(df)` while keeping raw HHMM. A separate hour column may let trees learn the daily delay pattern with fewer splits; it has identical semantics for full training frames and one-row evaluation.

Result: ad03c63, Eval AUC 0.7354 (+0.0009), 34.6 s total. Kept. The small improvement is worth one simple row-stable feature.

## Experiment 6 hypothesis — scheduled departure minute (follow-up)

Add `DepMinute = CRSDepTime % 100`, keeping hour and raw HHMM. Flight schedules tend to use preferred minute positions, and this exposes them directly to the model. This is a single new feature, matching the hour/minute construction in the flight-delay study cited above.

Result: 8f5ee85, Eval AUC 0.7334 (-0.0020), 36.0 s total. Discarded and reset to ad03c63. Departure minute appears noisy or redundant after raw HHMM and hour.

## Experiment 7 hypothesis — direct route category (exploration)

The training set has 4,290 origin-destination pairs. Add a `Route` category using levels fitted once on train, with unseen routes mapped to missing. [Flight-delay research](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) treats route as useful operational context, and [XGBoost's categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) supports partitioning high-cardinality categories. This may capture route-specific risk that separate airport splits need more depth to express.

Result: 27bb150, Eval AUC 0.7082 (-0.0272), 48.2 s total including 45.3 s evaluation. Discarded and reset to ad03c63. The high-cardinality route appears to overfit and adds per-row scoring cost.

## Experiment 8 hypothesis — minimum child weight 10 (exploration)

The default `min_child_weight=1` permits small, noisy airport/category leaves. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says increasing this threshold makes trees more conservative. Try 10 at depth 6 and 200 rounds to retain interactions while limiting small groups.

Result: a0a3e1e, Eval AUC 0.7348 (-0.0006), 34.4 s total. Discarded and reset to ad03c63. This level of leaf-size regularization did not improve the best model.

## Experiment 9 hypothesis — row subsampling 0.8 (exploration)

Use `subsample=0.8` with otherwise unchanged 200-round model. The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) identifies row sampling as a way to reduce overfitting; stochastic trees may be robust to sparse airport-category combinations without changing tree depth.

Result: f386389, Eval AUC 0.7265 (-0.0089), 34.7 s total. Discarded and reset to ad03c63. Full-row training performs much better on this already-undersampled dataset.

## Experiment 10 hypothesis — numeric month (exploration)

Add `MonthNum` from the existing `Month` string while keeping the category. The [flight-delay feature research](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) notes seasonal effects. Numeric month may expose adjacent-month changes that native category splits require more structure to learn. A single added column is inexpensive to score row by row.

Result: 85a255b, Eval AUC 0.7354 (equal to best at four decimal places), 36.9 s total. Discarded and reset to ad03c63 under the simplicity rule: an extra column did not add measurable value.

## Synthesis after ten experiments

Best: ad03c63, Eval AUC 0.7354. Moving from 30 to 200 trees supplied most of the gain (+0.0142); a separate departure-hour feature added a small +0.0009. Fewer (120) and many more (500) rounds both hurt. Shallower depth 4, higher child weight 10, and row subsampling 0.8 did not help; full-row depth-6 trees seem to need capacity for this sparse categorical problem. The direct 4,290-level route category failed badly and slowed row-by-row evaluation. Departure minute and numeric month were redundant. Current theory: useful signal is in scheduled time and existing airport/carrier categories, while very sparse direct interactions overfit. Next try a smoother boosting schedule, different categorical regularization, and compact calendar/time features rather than another huge category.

## Research refresh after ten experiments

The [XGBoost sklearn guide](https://xgboost.readthedocs.io/en/stable/python/sklearn_estimator.html) explains early stopping using an internal validation split, but doing so would reduce data available for the saved model, so first test a rate/rounds change on the full train set. The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends lower learning rate together with more boosting rounds. The [categorical parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) also offers `max_cat_threshold` to limit categorical split search; this may be worth testing after the boosting schedule.

## Experiment 11 hypothesis — half learning rate, double rounds (exploration)

Try learning rate 0.05 and 400 rounds, versus best 0.1 and 200 rounds. Similar total step size with smaller individual updates might reduce overfitting and refine the airport/time interactions. This is the coupled rate/round change recommended by XGBoost's tuning guide.

Result: f43d4fb, Eval AUC 0.7351 (-0.0003), 35.9 s total. Discarded and reset to ad03c63. Smoother boosting did not improve enough to justify twice as many trees.

## Experiment 12 hypothesis — tighter categorical partition threshold (exploration)

Try `max_cat_threshold=16` versus XGBoost's default on the 283-level Origin/Dest categories. The [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says this limits categories considered for partition splits to prevent overfitting. It may regularize airport splits more directly than changing all leaves or rows.

Result: 4c407eb, Eval AUC 0.7385 (+0.0031), 34.4 s total. Kept. Airport categorical partition regularization appears important.

## Experiment 13 hypothesis — threshold 8 (follow-up)

Reduce `max_cat_threshold` from 16 to 8, holding all else fixed. This tests whether the gain continues with stronger categorical restriction or whether 16 already strikes a good balance.

Result: 4154543, Eval AUC 0.7378 (-0.0007), 34.5 s total. Discarded and reset to 4c407eb. Eight looks too restrictive.

## Experiment 14 hypothesis — threshold 32 (follow-up)

Test 32, between the winning 16 and the prior default (64). The lower 8 result suggests a minimum level of category flexibility is needed; this checks whether a less aggressive restriction beats 16.

Result: 99d5169, Eval AUC 0.7355 (-0.0030), 34.6 s total. Discarded and reset to 4c407eb. Sixteen is clearly better than both 8 and 32 among tested values.

## Experiment 15 hypothesis — deeper trees with category regularization (follow-up)

With `max_cat_threshold=16` controlling the high-cardinality airport splits, test depth 7 instead of 6. The previous depth-4 test underfit before categorical regularization was added; extra depth may now capture useful carrier-airport-time interactions without the overly broad category partitions.

Result: 7d45ecc, Eval AUC 0.7375 (-0.0010), 35.0 s total. Discarded and reset to 4c407eb. The category threshold helped without needing another level of tree depth.

## Plateau research before experiment 16

A [flight-delay study](https://www.mdpi.com/2226-4310/8/6/152) includes day of year, day of month and season among schedule-derived features. A [study of departure-delay clustering](https://onlinelibrary.wiley.com/doi/full/10.1002/asmb.2846) reports daily weather effects on delay cascades. With this dataset's random same-year split, a combined calendar date could expose day-level disruption effects that separate month and day-of-month splits cannot express cheaply. Unlike a route key (4,290 levels), the date has about 365 levels and many observations per level. This is an inference to test, not a known result for this dataset.

## Experiment 16 hypothesis — flight date category (exploration)

Add a `FlightDate` category from Month and DayofMonth, with levels fitted on train. It may capture nationwide day-specific disruptions and holidays. No aggregates or counts enter `prepare(df)`; the feature is determined from each row's scheduled date and has the same meaning during one-row evaluation.

Result: 85ab8e0, Eval AUC 0.7486 (+0.0101), 39.8 s total. Kept. Day-specific information is a major missing signal in the earlier model. Evaluation rose to 37.8 s but remains far below the five-minute limit.

## Experiment 17 hypothesis — ordered day of year (follow-up)

Add numeric `DayOfYear` alongside the categorical date. The category captures sharp shocks, while the ordered day number could help trees group nearby dates for smoother seasonal patterns. This uses fixed 2005 calendar offsets and each row's month/day, so one-row scoring is unchanged semantically.

Result: 4ed1d7d, Eval AUC 0.7478 (-0.0008), 44.1 s total. Discarded and reset to 85ab8e0. The ordered date adds computation and no measurable gain over the categorical date.

## Experiment 18 hypothesis — more rounds with date feature (follow-up)

The new 365-level date category adds useful structure absent during earlier round-count trials. Test 300 rather than 200 trees at the same learning rate, depth, and category threshold. Additional rounds may model date-airport-time interactions that were impossible to learn before the date feature existed.

Result: 299b503, Eval AUC 0.7499 (+0.0013), 40.3 s total. Kept. The richer date model benefits from more rounds, unlike the earlier no-date model.

## Experiment 19 hypothesis — 450 rounds with date (follow-up)

Raise rounds from 300 to 450 at unchanged rate and features. This checks whether the date-added learning curve continues upward or overfitting begins before 450.

Result: b80c281, Eval AUC 0.7496 (-0.0003), 40.8 s total. Discarded and reset to 299b503. Extra rounds add no meaningful gain and cost model size.

## Experiment 20 hypothesis — tighter date category threshold (follow-up)

With the new 365-level FlightDate category in place, retry `max_cat_threshold=8` at the best 300 rounds. Threshold 8 was worse before the date was added, but the date introduces many more categorical values and may benefit from stronger split regularization.

Result: a262e03, Eval AUC 0.7455 (-0.0044), 40.4 s total. Discarded and reset to 299b503. Threshold 16 remains the best tested value with and without date.

## Synthesis after twenty experiments

Best: 299b503, Eval AUC 0.7499. The date category was the second major step after raising boosting rounds, lifting AUC by +0.0101; 300 rather than 200 rounds then added +0.0013. Numeric day of year was redundant with the date category. At this point 450 rounds gave no further benefit and stronger categorical restriction hurt. Earlier, threshold 16 improved airport/category handling by +0.0031. The model appears to benefit from shared day-level conditions and enough boosting capacity to combine them with airport and schedule features. Direct sparse route categories and indiscriminate row subsampling were counterproductive. Next investigate simple training-fitted group statistics, categorical representation, and compact schedule interactions with careful attention to label leakage and one-row inference.

## Research refresh after twenty experiments

The [scikit-learn TargetEncoder guide](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html) recommends cross-fitting training encodings to avoid target leakage, and the [CatBoost paper](https://arxiv.org/abs/1706.09516) explains why direct target statistics can shift training predictions. A carefully cross-fitted lookup might be useful later, but it is considerably more complex under this one-row `prepare` contract. First test a simpler categorical representation change from [XGBoost's categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html): choosing one-hot rather than partition splits for the low-cardinality calendar fields.

## Experiment 21 hypothesis — one-hot small calendar categories (exploration)

Set `max_cat_to_onehot=13`, so Month (12 levels) and DayOfWeek (7) can use one-hot splits while DayofMonth, carrier, airports and FlightDate continue to use partition splits. Individual calendar values may matter more than grouping them by response at every node. This changes one model parameter and adds no per-row preparation cost.

Result: c97805c, Eval AUC 0.7493 (-0.0006), 40.8 s total. Discarded and reset to 299b503. Partition splits for the calendar fields are marginally better.

## Experiment 22 hypothesis — column sampling (exploration)

Try `colsample_bytree=0.8`. The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) names column sampling as an overfitting control. With FlightDate now influential, stochastic feature subsets may create complementary trees and reduce reliance on any one feature; unlike row sampling, every tree still sees the complete training sample.

Result: a3f6349, Eval AUC 0.7509 (+0.0010), 40.3 s total. Kept. Column stochasticity helps in the date-rich model, in contrast to row subsampling.

## Experiment 23 hypothesis — stronger column sampling (follow-up)

Reduce `colsample_bytree` from 0.8 to 0.6, leaving other settings unchanged. If the 0.8 gain comes from forcing complementary trees, more feature diversity may help; if 0.6 removes too much context per tree, performance should fall.

Result: 4f8f38d, Eval AUC 0.7522 (+0.0013), 40.5 s total. Kept. Stronger tree-level feature sampling continues to help.

## Experiment 24 hypothesis — column sampling 0.4 (follow-up)

Lower `colsample_bytree` to 0.4. This is a substantive increase in feature diversity: each tree sees around four of the ten features. If the model still improves, weaker per-tree context is compensated by ensemble diversity; otherwise this locates a practical lower bound.

Result: 100512d, Eval AUC 0.7495 (-0.0027), 40.1 s total. Discarded and reset to 4f8f38d. Removing six of ten features per tree is too aggressive.

## Experiment 25 hypothesis — more rounds under column sampling (follow-up)

At `colsample_bytree=0.6`, each tree sees fewer predictors, so 400 rather than 300 rounds may be useful despite 450 having been unhelpful before column sampling. Test this interaction while leaving the strong date and categorical threshold unchanged.

Result: d492962, Eval AUC 0.7528 (+0.0006), 40.6 s total. Kept. Feature sampling permits a modest benefit from more rounds.

## Experiment 26 hypothesis — 600 rounds under column sampling (follow-up)

Increase from 400 to 600 rounds. The best model still gains with more trees under column sampling; this larger step checks whether capacity is still limiting or whether the gain has peaked.

Result: 8974095, Eval AUC 0.7516 (-0.0012), 41.3 s total. Discarded and reset to d492962. The optimum is closer to 400 rounds than 600 at this sampling rate.

## Experiment 27 hypothesis — sample columns per node (exploration)

Replace `colsample_bytree=0.6` with `colsample_bynode=0.6` at 400 rounds. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) distinguishes sampling once per tree from sampling at each split. Node sampling may retain access to all feature families across a tree while preventing any one feature from dominating every decision.

Result: c3d828e, Eval AUC 0.7510 (-0.0018), 40.9 s total. Discarded and reset to d492962. Tree-level sampling creates a better ensemble than split-level sampling here.

## Experiment 28 hypothesis — stronger L2 leaf regularization (exploration)

Set `reg_lambda=5` instead of default 1 at the best 400-tree, 0.6 column-sampling model. Per the [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html), L2 shrinkage makes leaf predictions more conservative. It may reduce noise in date-airport combinations while retaining the useful tree structure.

Result: 4c9b227, Eval AUC 0.7560 (+0.0032), 40.4 s total. Kept. Shrinking leaf estimates helps substantially in the date-rich model.

## Experiment 29 hypothesis — L2 regularization 10 (follow-up)

Double `reg_lambda` from 5 to 10. If date-airport leaf estimates still contain noise, additional shrinkage may improve ranking; if 5 is enough, stronger regularization should underfit.

Result: 41f3a6a, Eval AUC 0.7578 (+0.0018), 40.8 s total. Kept. Stronger leaf shrinkage continues to help.

## Experiment 30 hypothesis — L2 regularization 20 (follow-up)

Double `reg_lambda` again to 20 with all other settings fixed. The monotone improvement from 1 to 5 to 10 suggests the noisy date interactions may tolerate stronger shrinkage. This tests whether that trend continues.

Result: df4c373, Eval AUC 0.7597 (+0.0019), 41.0 s total. Kept. The best tested L2 penalty is now 20.

## Synthesis after thirty experiments

Best: df4c373, Eval AUC 0.7597. The last ten trials added nearly +0.010 AUC: tree-level column sampling at 0.6, 400 rounds, and L2 penalties 5→10→20 each helped. Extreme column sampling 0.4, 600 rounds, and node-level sampling hurt. This points to a model with stable, moderately sparse trees and conservative leaf values. FlightDate remains the decisive engineered feature. The current best is still compact: one extra date category, one hour feature, and four explicit model parameters beyond the starter's 30 rounds. Next determine the L2 optimum, then test another regularizer or change the schedule representation if research suggests a clear reason.

## Research refresh after thirty experiments

The [XGBoost DART tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) proposes tree dropout to address overfitting but warns training is slower. Given the one-minute training cap, it is a later candidate. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) identifies `gamma` as minimum split loss and `reg_alpha` as L1 leaf regularization, both distinct from L2 shrinkage. These are useful directions after locating the L2 optimum.

## Experiment 31 hypothesis — L2 regularization 40 (follow-up)

Double `reg_lambda` from 20 to 40. All three prior increases improved AUC, so a broad next step is justified. The result will show whether leaf shrinkage still helps or has crossed into underfitting.

Result: 860e78d, Eval AUC 0.7599 (+0.0002), 40.5 s total. Kept because complexity is unchanged, though the gain is much smaller than for earlier doublings.

## Experiment 32 hypothesis — L2 regularization 80 (follow-up)

Test one more broad doubling from 40 to 80 to see whether the curve has peaked. The diminishing gain at 40 suggests stronger shrinkage may now underfit; this should bracket the useful range.

Result: 8879acb, Eval AUC 0.7596 (-0.0003), 40.7 s total. Discarded and reset to 860e78d. Tested L2 optimum is around 20–40; further numerical refinement is unlikely to add much.

## Experiment 33 hypothesis — minimum split gain (exploration)

Add `gamma=1` to the best L2-40 model. Unlike L2 shrinkage, `gamma` in the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) rejects splits whose loss reduction is too small. That could prune weak date-airport interactions without changing the strong larger patterns.

Result: 12dc88b, Eval AUC 0.7537 (-0.0062), 39.8 s total. Discarded and reset to 860e78d. A unit minimum split gain prunes too much signal.

## Experiment 34 hypothesis — modest L1 leaf regularization (exploration)

Try `reg_alpha=1` with current L2=40, leaving gamma at default 0. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines L1 as another leaf-weight regularizer. It may suppress small noisy leaf outputs without blocking the underlying split entirely, unlike gamma.

Result: 0fc37e2, Eval AUC 0.7608 (+0.0009), 41.1 s total. Kept. A modest L1 penalty helps beyond L2 alone.

## Experiment 35 hypothesis — L1 regularization 3 (follow-up)

Increase `reg_alpha` from 1 to 3 at fixed L2=40. This tests whether the gain from soft-thresholding weak leaves continues with stronger L1 or whether sparse leaf outputs start to lose signal.

Result: 40006ea, Eval AUC 0.7625 (+0.0017), 41.2 s total. Kept. L1=3 improves more than L1=1.

## Experiment 36 hypothesis — L1 regularization 6 (follow-up)

Double `reg_alpha` to 6. The gain from 1 to 3 suggests continued noise reduction; this broad step checks whether the useful range extends further.

Result: 481c109, Eval AUC 0.7623 (-0.0002), 40.3 s total. Discarded and reset to 40006ea. L1=3 is the best tested value; gains have peaked or are within rounding noise.

## Experiment 37 hypothesis — remove departure hour (ablation/simplification)

The `DepHour` feature added +0.0009 early, before FlightDate and heavy leaf regularization. Delete it now to measure whether it still helps in the current best model. If AUC stays about equal, the simpler and slightly faster preparation wins.

Result: 0d3b852, Eval AUC 0.7626 (+0.0001), 39.6 s total with 36.7 s evaluation. Kept as a simplification win. The date-rich regularized model no longer needs the separate hour feature.

## Experiment 38 hypothesis — remove day of month category (ablation/simplification)

`FlightDate` encodes both month and day, while the separate DayofMonth category also consumes a slot under 0.6 column sampling. Remove DayofMonth from `cat_cols` while retaining it as input to FlightDate. If the combined date is sufficient, this should simplify preparation and give other predictors more per-tree exposure.

Result: 8d46815, Eval AUC 0.7615 (-0.0011), 35.3 s total. Discarded and reset to 0d3b852. Separate day-of-month grouping still contributes, despite being derivable from FlightDate.

## Experiment 39 hypothesis — remove month category (ablation/simplification)

Now remove Month from `cat_cols` while retaining it for FlightDate. The previous ablation showed day-of-month remains useful; month might be fully represented by the combined date and was also ineffective as a numeric add-on in an earlier run. This tests its unique contribution to the current model.

Result: 1ef6611, Eval AUC 0.7589 (-0.0037), 35.4 s total. Discarded and reset to 0d3b852. Month remains important for grouping dates into seasons.

## Experiment 40 hypothesis — remove day of week (ablation/simplification)

DayOfWeek can be inferred from a specific date in this one-year dataset, yet the separate category may help group similar weekdays. Remove it to test whether FlightDate and other calendar fields already provide the information; keep the simpler model if performance holds.

Result: faf4324, Eval AUC 0.7604 (-0.0022), 35.4 s total. Discarded and reset to 0d3b852. Direct weekday grouping remains valuable.

## Synthesis after forty experiments

Best: 0d3b852, Eval AUC 0.7626. L2 reached a plateau around 20–40 (40 is marginally best), while L1=3 added another +0.0026 over no L1. Gamma=1 was too restrictive. Removing departure hour was a simplification win, with no loss of AUC and faster row-by-row scoring. The three other calendar ablations all lost accuracy: date, month, day-of-month and weekday represent different useful groupings even when one mathematically determines the others. The best model is about +0.0423 AUC above the starter. Next explore tree-growth allocation and perhaps a validated round-selection method rather than more tiny parameter sweeps.

## Research refresh after forty experiments

The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) distinguishes depthwise tree growth, which expands shallower nodes first, from `lossguide`, which expands the nodes with highest gain. `max_leaves` can cap leaf-wise growth. This could help allocate split capacity to the few useful calendar-airport interactions, although it could also focus too much on noisy subgroups. The [XGBoost sklearn guide](https://xgboost.readthedocs.io/en/stable/python/sklearn_estimator.html) also describes early stopping on an internal validation split as a later way to select rounds without using Eval AUC for that choice.

## Experiment 41 hypothesis — gain-guided tree growth (exploration)

Use `grow_policy="lossguide"` with `max_leaves=64` and the same depth 6. Compared with depthwise growth, this spends split budget on the most informative branches first. The 64-leaf cap keeps tree size comparable to a full depth-6 tree.

Result: 691770c, Eval AUC 0.7626 (equal to best), 39.4 s total. Discarded and reset to 0d3b852 because the extra growth-policy settings add complexity without measurable value.

## Experiment 42 hypothesis — finer numeric histograms (exploration)

Increase `max_bin` from its default 256 to 512. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) notes that more bins can improve split optimality at a compute cost. Raw CRSDepTime and Distance each have over 1,000 unique train values; finer bins may preserve useful schedule thresholds.

Result: 3513c60, Eval AUC 0.7623 (-0.0003), 40.0 s total. Discarded and reset to 0d3b852. The added numeric resolution does not help enough to pay its compute cost.

## Experiment 43 hypothesis — wider category partitions after regularization (follow-up)

Raise `max_cat_threshold` from 16 to 32 at the current date-rich model with L1=3, L2=40, and column sampling 0.6. Threshold 32 previously lost before these changes; stronger leaf regularization may now allow more categorical flexibility without overfitting.

Result: 6f16c47, Eval AUC 0.7647 (+0.0021), 39.4 s total. Kept. The useful categorical split range widened after regularization.

## Experiment 44 hypothesis — category threshold 64 (follow-up)

Double `max_cat_threshold` to 64, the prior default. The newly regularized leaves may tolerate a larger search over date and airport categories. Compare to 32 to locate the current categorical capacity limit.

Result: 4a78915, Eval AUC 0.7647 (equal to best at four decimals), 39.4 s total. Discarded and reset to 6f16c47 because artifact size rose from 9.1 MB to 9.8 MB without a measurable gain. A separate no-explicit-threshold ablation can test whether the setting is needed at all.

## Experiment 45 hypothesis — remove explicit category threshold (ablation/simplification)

Delete `max_cat_threshold=32` and let XGBoost use its default. If the resulting model matches the 64 trial, it should preserve the best AUC while making `train.py` simpler. This also checks that no explicit threshold is needed after the stronger L1/L2 regularization.

Result: 15aa6fc, Eval AUC 0.7647 (equal), 39.5 s total. Kept as a simplification win: one fewer explicit parameter at the same measured AUC and run time. The artifact is 9.8 MB versus 9.1 MB for threshold 32, a minor cost.

## Experiment 46 hypothesis — smoother boosting with strong regularization (exploration)

Reduce learning rate from 0.1 to 0.05 and double rounds from 400 to 800. The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) couples these changes. The earlier rate test predates FlightDate, column sampling and strong L1/L2; those additions may make smaller per-round updates worthwhile now.

Result: 830b2a8, Eval AUC 0.7657 (+0.0010), 42.4 s total with 6.1 s training. Kept. The smoother schedule now helps. Artifact size doubled to 18.9 MB but remains practical; no new feature-preparation complexity was added.

## Experiment 47 hypothesis — more rounds at lower rate (follow-up)

Raise rounds from 800 to 1100 while keeping rate 0.05. With stronger regularization, the lower-rate model may still be underfit at 800; this tests whether additional rounds improve ranking or merely add size and noise.

Result: cd5d24a, Eval AUC 0.7660 (+0.0003), 43.6 s total with 6.6 s training. Kept provisionally for the higher AUC, though the artifact grew from 18.9 MB to 24.6 MB for a small gain.

## Experiment 48 hypothesis — 1500 rounds at lower rate (follow-up)

Increase to 1500 trees at rate 0.05. The small 800→1100 gain suggests saturation; this broader step tests whether additional capacity is still useful enough to justify a larger model.

Result: b54cc17, Eval AUC 0.7654 (-0.0006), 45.5 s total. Discarded and reset to cd5d24a. Round count has peaked near 1100 at rate 0.05.

## Experiment 49 hypothesis — depth 5 after strong regularization (exploration)

Try `max_depth=5` instead of 6 at the current date-rich, 1100-tree model. The old depth-4 trial was before date, column sampling and strong leaf penalties. A moderately shallower tree may now generalize as well with fewer leaf interactions and a smaller artifact.

Result: 7f856c1, Eval AUC 0.7652 (-0.0008), 42.2 s total. Discarded and reset to cd5d24a. Artifact size fell to 14.8 MB, but the AUC loss is not a simplification win when code length is unchanged.

## Experiment 50 hypothesis — depth 7 with strong leaf penalties (exploration)

Test depth 7 at the best 1100-round model. The earlier depth-7 trial preceded L1/L2 shrinkage and lower learning rate, so additional interactions may now be safer. Compare with depth 6 before deciding whether tree capacity should change.

Result: e343a44, Eval AUC 0.7660 (equal), 44.9 s total. Discarded and reset to cd5d24a because the artifact grew from 24.6 MB to 39.0 MB without a gain.

## Synthesis after fifty experiments

Best: cd5d24a, Eval AUC 0.7660. In the last ten trials, stronger leaf regularization allowed a wider categorical threshold; the XGBoost default then matched explicit threshold 32 and simplified code. Halving learning rate to 0.05 and raising rounds to 1100 added a modest +0.0013 total, while 1500 rounds overfit. Depth 5 lost accuracy and depth 7 tied with a much larger model, so depth 6 is well supported. The best model now combines the date category with the original schedule and airport/carrier fields, 1100 trees, column sampling 0.6, L1=3 and L2=40. Next test whether selective row sampling or a different training objective can improve the plateau, while keeping the existing evaluation intact.

## Research refresh after fifty experiments

The current [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says `sampling_method="gradient_based"` is available for CPU `hist` since XGBoost 3.2.0; it samples rows in proportion to gradient/hessian magnitude. The installed version is 3.4.1. This may retain difficult observations better than the uniform 0.8 row sampling that failed early. The installed sklearn API text still contains an older GPU-only note, so compatibility must be checked by the harness run.

## Experiment 51 hypothesis — gradient-based row sampling (exploration)

Try `sampling_method="gradient_based"`, `subsample=0.7`, and explicit `tree_method="hist"` at the current best settings. Uniform row sampling at 0.8 hurt before date and stronger regularization; gradient-based selection may reduce variance while focusing training on hard flight cases. A crash or timeout will be logged and reverted.

Result: a5fd733, Eval AUC 0.7625 (-0.0035), 47.3 s total with 10.7 s training. Discarded and reset to cd5d24a. Gradient sampling was compatible with CPU hist but harmed AUC and added cost.

## Experiment 52 hypothesis — moderate child weight (exploration)

Try `min_child_weight=5` at the current L1/L2-regularized model. The old weight-10 test was before FlightDate, column sampling and the stronger penalties. A moderate minimum may now avoid wasting splits on tiny groups while retaining more structure than the old 10 setting.

Result: 968e2a7, Eval AUC 0.7660 (equal), 43.3 s total. Discarded and reset to cd5d24a: one more explicit parameter for no measurable gain. Multiple recent discards indicate a plateau; research before trying another direction.

## Plateau research before experiment 53

The [scikit-learn cross-fitting example](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html) demonstrates that target encoding on the same labels used to train a downstream model can leak, especially with many categories. [Flight-delay work](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) finds airport effects vary with temporal conditions. I will test one train-fitted Origin×Month delay-rate feature using deterministic folds based only on row predictors. Each row's lookup is fitted from train rows in the other folds, so its own label never contributes; this is cross-fitting a feature, not cross-validation as an evaluation metric. No row counts become features.

## Experiment 53 hypothesis — out-of-fold airport-season rate (exploration)

Add `OriginMonthRate`, a target mean fitted separately on four of five deterministic train folds and mapped according to the row's fold. The same fold and lookup logic runs inside `prepare(df)` for both the full training frame and one-row evaluation. This may expose airport-specific seasonal risk that would require many categorical tree splits to learn. The added complexity is justified only by a material AUC gain.

Result: be1db91, Eval AUC 0.7640 (-0.0020), 57.6 s total including 50.6 s evaluation. Discarded and reset to cd5d24a. The added 17 lines and 14 s per-row scoring cost are not warranted; native categorical splits already capture this information more effectively.

## Experiment 54 hypothesis — column sampling 0.7 after regularization (follow-up)

Raise `colsample_bytree` from 0.6 to 0.7 in the current 1100-tree L1/L2 model. Earlier 0.6 beat 0.8 before strong leaf penalties and lower learning rate. With more rounds and shrinkage, extra feature access per tree may now improve interactions.

Result: 604c1cc, Eval AUC 0.7654 (-0.0006), 43.5 s total. Discarded and reset to cd5d24a. More features per tree did not help.

## Experiment 55 hypothesis — column sampling 0.5 (follow-up)

Test 0.5, below the winning 0.6. The earlier 0.4 setting was too sparse before the final regularization and schedule; 0.5 may be a useful middle point with the larger 1100-tree ensemble. This brackets the current optimum rather than repeating the 0.7 trial.

Result: fc5b844, Eval AUC 0.7659 (-0.0001), 43.7 s total. Discarded and reset to cd5d24a. Column sampling 0.6 remains the best tested fraction.

## Plateau research before experiment 56

The [XGBoost sklearn guide](https://xgboost.readthedocs.io/en/stable/python/sklearn_estimator.html) explains early stopping on a manually held-out subset of the training data, and [XGBoost prediction guidance](https://xgboost.readthedocs.io/en/stable/prediction.html) confirms the sklearn predictor uses the best iteration automatically. This offers a different way to choose boosting rounds without another Eval-driven numeric sweep. It trades away a small portion of fitting rows, so the only decision metric remains the harness Eval AUC.

## Experiment 56 hypothesis — early stopping on 5% of train (exploration)

Reserve 5% of `train.csv` for an internal stratified validation slice. Allow up to 1600 rounds with AUC early stopping after 80 unimproved rounds. The best iteration may avoid the minor overfitting observed above 1100, but training on 95% of rows may cost predictive signal. No retrain is performed.

Result: 746142b, best internal iteration 831, Eval AUC 0.7655 (-0.0005), 42.6 s total. Discarded and reset to cd5d24a. The loss of fitting rows and added code did not improve the saved model.

## Experiment 57 hypothesis — one-hot carrier splits (exploration)

Set `max_cat_to_onehot=21`, allowing one-hot splits for 20-level carrier and the smaller Month/DayOfWeek categories while retaining partitions for airports, DayofMonth and FlightDate. The earlier 13 threshold before strong leaf regularization lost slightly, but it did not change carrier handling. Specific airline effects may be easier to isolate through one-hot splits.

Result: ec73329, Eval AUC 0.7637 (-0.0023), 43.6 s total. Discarded and reset to cd5d24a. Partition splits are better for carrier and calendar under the current regularized model.

## Plateau research before experiment 58

The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) and [sklearn API](https://xgboost.readthedocs.io/en/stable/python/python_api.html) support per-feature weights to change selection probability during column sampling. Read-only inspection of the current saved model's training split gains shows FlightDate largest (362k), then CRSDepTime (165k), Origin (126k), Dest (123k), with remaining fields lower. With `colsample_bytree=0.6`, the dominant date feature is omitted from a substantial fraction of trees; a moderate selection weight could help without changing feature definitions.

## Experiment 58 hypothesis — preferential date sampling (exploration)

Give FlightDate weight 2 and every other feature weight 1 when XGBoost samples tree columns. This biases the sampling probability while still allowing the other predictors to form complementary trees. If it overconcentrates trees on date-specific patterns, AUC should drop and the change will be discarded.

Result: 736a556, Eval AUC 0.7650 (-0.0010), 42.9 s total. Discarded and reset to cd5d24a. Increasing exposure to the strongest feature appears to reduce ensemble diversity.

## Experiment 59 hypothesis — reduce date selection weight (follow-up)

Give FlightDate weight 0.5 and other features 1. The failed weight-2 trial suggests date may already dominate enough; de-emphasizing it under column sampling may force better complementary airport and time trees while retaining date in some trees.

Result: 433d40e, Eval AUC 0.7657 (-0.0003), 43.7 s total. Discarded and reset to cd5d24a. Uniform feature-selection weights remain best and keep the code simpler.

## Experiment 60 hypothesis — category threshold 32 at lower learning rate (follow-up)

Reintroduce `max_cat_threshold=32` in the current 1100-tree, rate-0.05 model. At 400 trees and rate 0.1 it tied the default threshold at four decimals, but the smoother, longer ensemble might benefit from slightly more constrained date/airport partitions and a smaller artifact.

Result: e12e720, Eval AUC 0.7657 (-0.0003), 42.9 s total. Discarded and reset to cd5d24a. The default categorical threshold remains best at the lower rate.

## Synthesis after sixty experiments

Best: cd5d24a, Eval AUC 0.7660. The last ten trials did not improve it. Gradient-weighted row sampling reduced accuracy and slowed training. Minimum child weight 5 tied while adding complexity. Out-of-fold Origin×Month target encoding was leakage-safe but hurt and raised evaluation time. Internal early stopping chose 831 rounds on 95% of train and scored below the full-data model. Changing carrier split style, reweighting date selection, and tweaking column or category sampling also failed. The best model's compact feature construction and the full 200K training rows now seem more valuable than another engineered lookup. Remaining time should focus on one or two distinct training controls, then leave the branch at the best commit.

## Research refresh after sixty experiments

The [XGBoost random-forest tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) documents that `num_parallel_tree>1` together with multiple boosting rounds builds a boosted forest: each round adds a small ensemble of trees. Since this model already benefits from column sampling, two parallel trees could reduce variation while keeping about the same total number of trees. This changes the booster structure without adding data-preparation cost.

## Experiment 61 hypothesis — two trees per boosting round (exploration)

Set `num_parallel_tree=2` and 550 boosting rounds (about 1100 total trees), retaining the current rate and other settings. Parallel feature-sampled trees may capture complementary airport/date structure per round better than the sequential one-tree model. Training and evaluation remain under the same harness limits.

Result: c99f402, Eval AUC 0.7647 (-0.0013), 44.9 s total. Discarded and reset to cd5d24a. Sequential trees remain more effective and slightly cheaper.

## Experiment 62 hypothesis — L1 regularization 4 at lower rate (follow-up)

Test `reg_alpha=4` versus best 3. The prior alpha sweep used 400 rounds at learning rate 0.1, while the current model has 1100 rounds at 0.05. A slightly stronger leaf sparsity penalty may better offset the extra trees without adding code complexity.

Result: 7135a4c, Eval AUC 0.7665 (+0.0005), 42.8 s total. Kept. The optimum shifted upward with the longer, slower boosting schedule.

## Experiment 63 hypothesis — L1 regularization 5 (follow-up)

Increase `reg_alpha` from 4 to 5, unchanged otherwise. This checks whether the gain from the prior step continues or whether 4 is near the best value; the change has no code-complexity cost.

Result: f6cd530, Eval AUC 0.7659 (-0.0006), 43.2 s total. Discarded and reset to 7135a4c. L1=4 is best among the tested values at this schedule.

## Experiment 64 hypothesis — lower L2 with L1=4 (follow-up)

Reduce `reg_lambda` from 40 to 20 while retaining the new best L1=4 and rate-0.05 schedule. L2=20 was close to 40 before these changes; a slightly less shrunk leaf may now improve ranking without added code complexity.

Result: 0569a41, Eval AUC 0.7669 (+0.0004), 42.9 s total. Kept. The lower-rate, L1=4 model benefits from less L2 shrinkage.

## Experiment 65 hypothesis — L2 regularization 10 (follow-up)

Halve L2 again to 10 as a final bracket. If the shift toward lower L2 continues, AUC may rise; if leaf predictions become too variable, the score should fall. This is a one-value change with no new preparation code.

Result: b49036f, Eval AUC 0.7667 (-0.0002), 43.0 s total. Discarded and reset to 0569a41. The best tested L2 is 20 at the final L1=4, lower-rate schedule.

## Final summary

Best Eval AUC: **0.7669**, commit **0569a41**. Baseline was 0.7203 at 92e43e6, a gain of 0.0466. The decisive improvements were raising tree count, combining Month and DayofMonth into a train-fitted FlightDate category, using moderate tree-level column sampling, and adjusting L1/L2 leaf regularization with a lower learning rate. The best code removed an eventually redundant departure-hour feature and does all preparation row by row with stable train-fitted category levels. Direct route categories, extra date numerics, row sampling, target encoding, internal early stopping and larger/deeper ensembles did not help. If continuing in another run, I would investigate a validated weather or airport-region signal that is available before departure and permissible under the data rules; no such external data was used here.
