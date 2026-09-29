# Research log — sep29

## Baseline — 92e43e6

The unchanged starter reached Eval AUC 0.7203. It uses 30 depth-6 trees at learning rate 0.1 with native categorical splits. Training took 0.2 s and the row-wise evaluation took 30.5 s. This is the reference for subsequent experiments.

## Experiment 1 — more boosting rounds (follow-up)

Hypothesis: 30 boosting rounds underfit this 200,000-row dataset; 300 trees at the same learning rate should capture additional temporal and airport interactions. Only tree count changes to isolate this effect. This follows the [XGBoost tuning guide](https://xgboost.readthedocs.io/en/release_0.72/tutorials/param_tuning.html), which discusses tree complexity and the relationship between learning rate and rounds. The [categorical data guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) supports retaining native categorical splits for the existing airport and carrier columns.

Result: 0.7342 (+0.0139). Keep. The baseline had substantial capacity headroom. Training remained fast at 2.5 s total harness training phase.

## Experiment 2 — 800 trees (follow-up)

Hypothesis: the large gain from 30 to 300 rounds suggests more boosting could still improve ranking. Increase only `n_estimators` to 800, holding learning rate 0.1 and depth 6 fixed to map the capacity curve.

Result: 0.7273 (-0.0069). Discard. The model overfits or otherwise loses generalization beyond 300 rounds at this learning rate and depth.

## Experiment 3 — day of year (exploration: calendar features)

Hypothesis: neighboring dates can share year-specific disruption patterns that independent Month and DayofMonth categories cannot easily represent. Add numeric day of year from the row's month and day; keep all original features and 300 trees. This is inspired by [flight delay research](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057) using calendar and schedule variables and [scikit-learn's time feature engineering guide](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html). The new feature is row-local, so train and evaluation semantics match.

Initial run crashed because the date fields contain `c-` prefixes, not bare integers. This is a simple parsing error; fix and rerun the same feature.

Corrected run: 0.7378 (+0.0036 over best). Keep. Numeric day of year appears useful; evaluation cost rose by about 4 seconds but remains well inside the limit.

## Experiment 4 — depth 4 (follow-up: control overfitting)

Hypothesis: the 800-tree loss suggests that depth-6 trees may be too expressive for the available features. Try depth 4 at 300 trees, leaving all other settings unchanged. [XGBoost's parameter tuning guide](https://xgboost.readthedocs.io/en/release_0.72/tutorials/param_tuning.html) identifies max depth as a direct control on model complexity.

Result: 0.7382 (+0.0004). Keep. Shallower trees give a small improvement, suggesting complexity control matters.

## Experiment 5 — 600 depth-4 trees (follow-up)

Hypothesis: reduced depth may let boosting continue beyond 300 rounds without the depth-6 model's overfit. Double the rounds to 600 while holding the learning rate at 0.1.

Result: 0.7377 (-0.0005). Discard. Extra rounds still do not help at learning rate 0.1, even with depth 4.

## Experiment 6 — smaller learning rate, more rounds (exploration)

Hypothesis: 600 trees at learning rate 0.05 may match the effective boosting span of 300 at 0.1 while reducing overshoot. [XGBoost's tuning guide](https://xgboost.readthedocs.io/en/release_0.72/tutorials/param_tuning.html) recommends increasing rounds when reducing eta. Compare against kept depth-4, 300-tree model.

Result: 0.7390 (+0.0008). Keep. Gentler boosting helped a little and training remains under 3 seconds.

## Experiment 7 — route category (exploration: categorical interaction)

Hypothesis: an origin-destination pair can have a distinct delay profile that a depth-4 tree may struggle to express from separate airport columns. Add a native categorical route feature, with its category vocabulary fitted only on train. Unknown routes map to missing. [Flight delay research](https://www.sciencedirect.com/science/article/pii/S0969699720305755) discusses interacting origin and destination factors; [XGBoost's categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains partitioned categorical splits. All other settings remain at the best commit.

Result: 0.7136 (-0.0254). Discard. This high-cardinality cross badly hurts generalization and increases row-wise evaluation time to 48 s. Avoid similarly sparse composite categories unless regularization is addressed.

## Experiment 8 — categorical departure hour (exploration: time encoding)

Hypothesis: an hour category can group nonadjacent departure periods and expose time-of-day patterns without the sparse route category. Keep the original HHMM numeric feature and add a 24-level hour derived row by row. [Scikit-learn's time feature engineering example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) explores alternate encodings of time-of-day features.

Result: 0.7387 (-0.0003). Discard: no gain and slightly more preparation cost.

## Experiment 9 — row subsampling (exploration: regularization)

Hypothesis: sampling 80% of training rows for each tree will reduce correlated fits and improve generalization after the model's observed sensitivity to too many rounds. Change only `subsample` from its default 1 to 0.8. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) document row subsampling and its overfitting control.

Result: 0.7295 (-0.0095). Discard. Randomly removing rows per tree substantially hurts this setup; the useful signal may rely on all examples, especially rare airports.

## Experiment 10 — larger minimum child weight (exploration: regularization)

Hypothesis: increasing `min_child_weight` to 10 will suppress weak airport/date-specific leaf splits without discarding training rows. This tests a different complexity control than subsampling. [XGBoost's tuning guide](https://xgboost.readthedocs.io/en/release_0.72/tutorials/param_tuning.html) recommends min child weight for overfitting control.

Result: 0.7395 (+0.0005). Keep. Smoothing small leaves helped without slowing the run.

## Synthesis after 10 experiments

Best so far: 0.7395 at `adc94cb`, versus 0.7203 baseline. More rounds initially helped a lot, but 800 depth-6 trees and 600 depth-4 trees at learning rate 0.1 lost accuracy. Lower depth and learning rate gave modest additional gains. A numeric day-of-year feature provided the largest feature gain. High-cardinality route categories and row subsampling hurt substantially; categorical departure hour had no useful gain. Increasing minimum child weight helped slightly. My current theory is that local temporal structure matters and smooth, well-supported splits generalize better than sparse route memorization. Next I will research schedule- and airport-level features and categorical regularization before choosing another direction.

Research: [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) documents `max_cat_threshold` and L1/L2 regularization as ways to constrain categorical splits and leaf weights. A [UC Berkeley flight-delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) reports airport-specific operational patterns and time-of-day effects. The data here lack weather and aircraft lineage, so the next feature will summarize only scheduled departure times from the allowed training set.

## Experiment 11 — departure time relative to origin median (exploration: train-fitted lookup)

Hypothesis: each airport has its own flight schedule; scheduled time relative to that airport's typical departure time may represent early versus late operations in a way shallow trees can use. Fit the origin median HHMM on train once, then look it up per row in `prepare`. This is target-free and valid for row-wise evaluation. Keep the best model settings unchanged.

Result: 0.7394 (-0.0001). Discard under the simplicity criterion: essentially no gain and extra lookup/evaluation cost.

## Experiment 12 — lower categorical split threshold (exploration)

Hypothesis: restricting partition-based categorical splits to 16 categories rather than the default 64 could reduce overfit on 283-airport features while retaining all categories. This follows the [`max_cat_threshold` description](https://xgboost.readthedocs.io/en/stable/parameter.html). Change only this parameter.

Result: 0.7391 (-0.0004). Discard. Restricting categorical splits did not help.

Diagnostic on the kept model `adc94cb`: gain importances are dominated by CRSDepTime (0.473); Month is next (0.143), and Distance is lowest (0.012). This motivates a distance ablation. These importances are descriptive, not an evaluation metric.

## Experiment 13 — remove Distance (ablation/simplification)

Hypothesis: Distance contributes little relative to time and calendar features, and its small gain importance might reflect noise. Remove it from the training feature set; keep the simpler model if AUC is at least essentially equal.

Result: 0.7390 (-0.0005). Discard: one fewer list entry is only a minor simplification and the AUC loss is measurable. Three consecutive small misses have yielded less than 0.001 progress; pause for research before the next experiment.

Plateau research: [Microsoft's flight delay tutorial](https://learn.microsoft.com/en-us/fabric/data-science/r-flight-delay) suggests explicit holiday date features. The [US Office of Personnel Management's federal holiday calendar](https://www.opm.gov/policy-data-oversight/pay-leave/pay-administration/fact-sheets/holidays-work-schedules-and-pay) gives the holiday definitions. [Scikit-learn's time feature guide](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) shows that boosted trees can exploit derived temporal variables. The current model has month and numeric day-of-year but shallow trees may not isolate the several noncontiguous holiday windows efficiently.

## Experiment 14 — distance to major holidays (exploration: calendar signal)

Hypothesis: days near New Year's, Memorial Day, Independence Day, Labor Day, Thanksgiving, and Christmas may have unusual travel volumes and delay patterns. Add a numeric distance in days to the closest of these 2005 holidays, looked up by the row's day-of-year. Keep all model settings unchanged. The feature uses only fixed public calendar dates and each row's own date; it does not aggregate evaluation rows.

Result: 0.7394 (-0.0001). Discard: no measurable gain, additional calendar complexity and evaluation cost. DayOfYear and Month may already express enough of this signal.

## Experiment 15 — one-hot splits for small categories (exploration: encoding)

Hypothesis: with depth-4 trees, one-hot splits for Month, DayofMonth, DayOfWeek, and carrier may isolate important individual calendar/carrier effects more directly than partition-based splits. Set `max_cat_to_onehot=32`; airports remain partitioned because they each have 283 levels. [XGBoost's categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains this switch.

Result: 0.7300 (-0.0095). Discard. The original partition-based splits are substantially better for this feature set; do not pursue one-hot thresholds near this value.

## Experiment 16 — depth 3 (follow-up: simpler trees)

Hypothesis: depth 4 was better than depth 6, so depth 3 may further reduce overfitting while the 600 rounds still learn enough interactions. Only max depth changes; this also simplifies the trained trees.

Result: 0.7349 (-0.0046). Discard. Depth 3 removes too much interaction capacity. Depth 4 looks near the useful range.

## Experiment 17 — depth 5 (follow-up: bracket depth)

Hypothesis: depth 3 clearly underfits, while the earlier depth-6 configuration was less accurate than depth 4. Depth 5 at the current lower learning rate and higher child weight may be a better balance. Change only max depth from 4 to 5.

Result: 0.7395 (tie at displayed precision). Discard under the simplicity criterion: larger trees and 4.2 s training versus 2.8 s for no visible AUC gain.

## Experiment 18 — minimum child weight 25 (follow-up)

Hypothesis: raising child weight from the previously beneficial 10 to 25 may further smooth rare airport/date splits. Keep depth 4 and all features fixed to isolate the regularization strength.

Result: 0.7394 (-0.0001). Discard. Smoothing beyond 10 does not help at the displayed precision.

Plateau research: [XGBoost's tree-method documentation](https://xgboost.readthedocs.io/en/release_3.3.0/treemethod.html) notes that the histogram method trades split precision for speed and that more bins can recover accuracy. The [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says the default `max_bin` is 256 and increasing it offers better split candidates at higher computation cost. The kept model's gain importance assigns 47% to CRSDepTime, which has 1,162 distinct HHMM values in train. This suggests a focused test of finer numeric binning.

## Experiment 19 — 512 histogram bins (exploration)

Hypothesis: 512 rather than 256 bins will preserve more useful departure-time split candidates and improve AUC, while training should remain far under 60 seconds. Change only `max_bin`.

Result: 0.7387 (-0.0008). Discard. Finer numerical thresholds were not helpful, suggesting 256 bins are already sufficient or the extra resolution fits noise.

## Experiment 20 — 128 histogram bins (follow-up: test coarser splits)

Hypothesis: since finer 512-bin splits did not help, 128 bins may regularize noisy minute-level departure-time thresholds. This tests the opposite side of the default 256-bin setting rather than another small upward adjustment.

Result: 0.7385 (-0.0010). Discard. Both 128 and 512 bins are worse than the default 256; the current quantization appears adequate.

## Synthesis after 20 experiments

Best remains 0.7395 at `adc94cb`. The second block of experiments did not improve on it. A train-fitted origin schedule median, holiday distance, and categorical departure hour each added complexity without improving AUC. One-hot categorical splits caused a large drop. Depth 3 underfit; depth 5 tied but was more complex. Stronger child weight and changes to histogram bin count did not help. The current model seems to need interactions richer than depth 3 but not more depth or more boosting. Next I will research time-of-day feature transformations that add information unavailable to a simple HHMM threshold, rather than further refining tree knobs.

Research: a [flight forecasting paper](https://link.springer.com/article/10.1007/s13272-026-00941-7) names both hour and minute of scheduled departure as temporal features. [Scikit-learn's time-feature guide](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) discusses finer-grained time resolution. The current HHMM feature orders times of day but does not make minute-within-hour effects shared across hours. The hour category alone did not help; the minute component tests a different pattern.

## Experiment 21 — minute within hour (exploration: schedule encoding)

Hypothesis: flight schedules at :00, :15, :30, or :45 may have similar operational patterns across different hours; depth-4 trees cannot easily learn this repetition from HHMM alone. Add `CRSDepTime % 100` as numeric while retaining HHMM. This is row-local and cheap to calculate.

Result: 0.7389 (-0.0006). Discard. Repeated minute-of-hour patterns are not strong enough to improve this model.

## Experiment 22 — carrier by month category (exploration: compact interaction)

Hypothesis: airlines have different seasonal operating patterns, which separate carrier and month splits may not express efficiently in depth-4 trees. A carrier-month category has at most 240 levels, much smaller than the failed route category. Keep individual carrier and month features as fallbacks. [Airline delay research](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057) identifies seasonal and carrier factors, and [scikit-learn's categorical boosting example](https://scikit-learn.org/stable/auto_examples/ensemble/plot_gradient_boosting_categorical.html) notes the split-efficiency of native categories in shallow trees.

Result: 0.7403 (+0.0008). Keep. A moderate-size airline-season interaction is useful, unlike the much larger route category. Evaluation time grew to about 40 s but remains safe.

## Experiment 23 — carrier by day of week (follow-up)

Hypothesis: carriers run different weekday and weekend schedules, which can affect delay risk. A carrier-weekday category has at most 140 levels and should be better supported than a route key. Add it alongside the successful carrier-month feature; keep all other settings fixed.

Result: 0.7437 (+0.0034). Keep. The airline-weekday interaction is a clear improvement, suggesting schedule-specific carrier effects matter more than route identity here.

## Experiment 24 — month by weekday (follow-up: compact calendar interaction)

Hypothesis: weekday effects vary across seasons and holidays. A month-weekday native category has at most 84 levels, so it should be well supported and inexpensive to fit. Add it alongside the successful carrier interactions, keeping all hyperparameters fixed.

Result: 0.7455 (+0.0018). Keep. Modest-cardinality calendar interactions continue to help. Evaluation takes 48.4 s, still well inside its 5-minute limit.

## Experiment 25 — categorical day of year (exploration: date-specific signal)

Hypothesis: the numeric day-of-year feature captures contiguous seasons but cannot group several isolated disruption dates in one split. A 365-level categorical copy can represent date-specific patterns in this single-year data; each date has many training examples. Add it alongside the numeric date and existing interactions, leaving the rest unchanged. This is a row-local transform with a fixed 2005 calendar vocabulary.

Result: 0.7564 (+0.0109). Keep. Date identity is by far the strongest feature change after the initial capacity fix, consistent with shared daily disruptions across flights. The random train/eval split shares dates; this should be checked later on the held-out split by the human, but the agent does not access that split.

## Experiment 26 — remove numeric day of year (ablation/simplification)

Hypothesis: now that the full date is represented categorically, the numeric DayOfYear column may be redundant. Remove the numeric copy while retaining DateCategory, and keep this only if AUC is effectively unchanged or improves.

Result: 0.7564 (tie at displayed precision). Keep: one fewer model feature and about 1 second less evaluation time with no visible AUC loss.

## Experiment 27 — remove DayofMonth predictor (ablation/simplification)

Hypothesis: DateCategory already identifies the exact day within the year, so a separate day-of-month categorical predictor may be redundant. Remove only DayofMonth from the model input list while still reading it to construct DateCategory. Keep if AUC remains effectively equal.

Result: 0.7564 (tie at displayed precision). Keep. Removing the redundant predictor reduced evaluation time from 50.6 s to 47.0 s, with no visible loss.

## Experiment 28 — remove Month predictor (ablation/simplification)

Hypothesis: DateCategory encodes month and day jointly, while CarrierMonth and MonthWeekday retain explicit seasonal interactions. The standalone Month categorical may now be redundant. Remove it only from the model input list, retaining it as source data for the derived features.

Result: 0.7564 (tie at displayed precision). Keep. Evaluation became faster again, 42.7 s. Standalone Month is redundant in this configuration.

## Experiment 29 — remove standalone weekday (ablation/simplification)

Hypothesis: DateCategory fixes the weekday in this one-year dataset, and the carrier-weekday and month-weekday interactions explicitly preserve it where needed. Remove standalone DayOfWeek from the model input list, still using it to construct interactions. Keep if AUC is effectively unchanged.

Result: 0.7564 (tie at displayed precision). Keep. Evaluation dropped to 39.5 s, with no visible AUC loss. The model now uses fewer redundant calendar predictors.

Diagnostic on `32e7390`: model feature gain importance is CRSDepTime 0.471, DateCategory 0.151, CarrierMonth 0.114, Origin 0.092, Dest 0.079, CarrierWeekday 0.064, Distance 0.017, MonthWeekday 0.012, and standalone UniqueCarrier 0.000. These are model diagnostics only, not evaluation scores.

## Experiment 30 — remove standalone carrier (ablation/simplification)

Hypothesis: the fitted model does not split on standalone UniqueCarrier because the two carrier interactions capture its useful information. Remove only the standalone carrier predictor, retaining the raw field for constructing CarrierMonth and CarrierWeekday. Expect equal AUC with cheaper preparation.

Result: 0.7564 (tie at displayed precision). Keep. The model remains equally accurate and the row-wise evaluation took 35.8 s, down from 51.8 s immediately after DateCategory was added.

## Synthesis after 30 experiments

Best Eval AUC is 0.7564 at `56cdb69`, a +0.0361 improvement over the 0.7203 baseline. Moderate-cardinality interactions (CarrierMonth, CarrierWeekday, MonthWeekday) and a 365-level DateCategory were the major gains. The exact date feature alone added 0.0109 AUC. After adding it, numeric DayOfYear and standalone Month, DayofMonth, DayOfWeek, and carrier features could all be removed at unchanged displayed AUC, cutting evaluation time by about 16 seconds. The model still relies heavily on scheduled departure time and date; route identity was too sparse. Next I will investigate categorical partition limits for DateCategory and time-by-carrier effects.

Research: [XGBoost's categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) describes sorting categories by learned leaf value to search useful partitions. The [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `max_cat_threshold` as the number of categories considered at a partition split and an overfitting control. Because DateCategory has 365 levels and is useful, I will test a larger limit. [Airline schedule research](https://dspace.mit.edu/bitstream/handle/1721.1/30143/56017873-MIT.pdf) also discusses concentrated departure banks, motivating a later carrier-time interaction.

## Experiment 31 — more categorical split candidates (follow-up)

Hypothesis: permitting up to 128 categories at a partition split may let the date feature group more disruption days and improve AUC. Change only `max_cat_threshold` from its current default; note that more flexibility may also overfit.

Result: 0.7569 (+0.0005). Keep. More categorical partition candidates offered a small gain without meaningful runtime cost.

## Experiment 32 — categorical split threshold 256 (follow-up)

Hypothesis: the gain from 128 suggests the 365-level DateCategory may benefit from considering still more categories per partition. Raise `max_cat_threshold` to 256 with all else fixed. Compare the gain against any complexity or runtime cost.

Result: 0.7568 (-0.0001). Discard. Threshold 128 remains best; additional candidates offer no gain.

## Experiment 33 — carrier by departure hour (exploration: schedule interaction)

Hypothesis: individual airlines organize departures into waves, so the meaning of a scheduled hour may differ by carrier. Add a carrier-hour native category (at most 480 levels) while retaining numeric HHMM and the existing carrier calendar interactions. [Airline schedule research](https://dspace.mit.edu/bitstream/handle/1721.1/30143/56017873-MIT.pdf) describes concentrated departure banks. This composite is less sparse than the failed airport route key.

Result: 0.7555 (-0.0014). Discard. The carrier-hour cross adds cost and no useful signal beyond numeric HHMM and existing interactions.

## Experiment 34 — 1,000 trees with rich features (follow-up)

Hypothesis: the current date and carrier interaction features supply much more signal than the earlier feature set. The previous overfit at 800 trees used depth 6 and learning rate 0.1; 1,000 rounds with depth 4, rate 0.05, and child weight 10 may extract more without the same loss. Change only `n_estimators`.

Result: 0.7566 (-0.0003). Discard. Additional rounds are still unhelpful even with the richer features.

Plateau research: [Flight-delay causality research](https://doi.org/10.1016/j.ijtst.2022.01.007) reports heterogeneous weekday effects associated with schedules and origin geography. A [periodicity study](https://stars.library.ucf.edu/facultybib2000/6790/) found daily, weekly, and seasonal delay patterns at an airport. These support testing a location-weekday interaction. It is more granular than the successful carrier-weekday cross, but still far smaller than the failed route category.

## Experiment 35 — origin by weekday category (exploration: airport calendar)

Hypothesis: airports have different weekday congestion and operational schedules. Add a native categorical origin-weekday key, with levels learned from train. The key is row-local at evaluation; no row counts or target statistics are used. Leave all current model settings intact.

Result: 0.7460 (-0.0109). Discard. Even this smaller airport cross is too sparse/noisy; avoid further origin or destination crosses of similar cardinality.

## Experiment 36 — stronger L2 leaf regularization (exploration)

Hypothesis: the useful DateCategory and carrier interactions may still fit noisy date-specific leaf values. Increase `reg_lambda` from its default 1 to 10 to shrink leaf weights smoothly without removing any training rows. [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes this as a conservative regularization control.

Result: 0.7568 (-0.0001). Discard. Stronger L2 regularization does not improve the current model.

Plateau research: [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) distinguishes `depthwise` growth, which splits shallower nodes first, from `lossguide`, which chooses the highest-loss-reduction leaf. It also supports `max_leaves` as a tree-size limit. This may allocate a similar number of splits more effectively when date and schedule interactions are uneven across flights.

## Experiment 37 — leaf-guided growth (exploration: tree structure)

Hypothesis: 16-leaf, depth-at-most-6 trees can concentrate capacity on the strongest date/time branches while staying near the size of the current depth-4 trees. Set `grow_policy='lossguide'`, `max_leaves=16`, and `max_depth=6`; keep 600 rounds and all features fixed.

Result: 0.7558 (-0.0011). Discard. Leaf-guided allocation did not help at this leaf budget.

## Experiment 38 — approximate tree method (exploration: split search)

Hypothesis: `approx` recomputes quantile sketches using changing Hessian information in binary logistic boosting, whereas `hist` uses a global sketch. This may find better splits for date and departure time, at some training cost. [XGBoost's tree-method documentation](https://xgboost.readthedocs.io/en/release_3.3.0/treemethod.html) notes that `approx` can sometimes improve accuracy for nonconstant-Hessian objectives. Change only the tree method.

Result: 0.7580 (+0.0011). Keep. Approximate split search helps; training is 15.2 s instead of about 3 s but stays under the 60 s limit.

## Experiment 39 — depth 5 with approx (follow-up)

Hypothesis: with better Hessian-weighted split candidates from `approx`, a fifth interaction level may add useful date-by-airport structure. Keep 600 rounds and all features fixed, changing only max depth from 4 to 5. Training should remain within the 60 s limit.

Result: 0.7571 (-0.0009). Discard. The extra depth still hurts despite approximate split search.

## Experiment 40 — 400 approximate trees (follow-up: earlier stopping)

Hypothesis: 600 trees may be slightly past the best ranking point for the richer date features; earlier experiments showed that 1,000 hist trees lost accuracy. Use 400 rounds at the same rate and depth to check whether a shorter model generalizes better and runs faster.

Result: 0.7564 (-0.0016). Discard. Cutting 200 rounds loses useful fit; the current 600-round approx model remains best.

## Synthesis after 40 experiments

Best Eval AUC is 0.7580 at `18b41b8`, +0.0377 over baseline. Since experiment 30, raising the categorical split threshold to 128 helped slightly, and switching from histogram to approximate tree construction added 0.0011. More categorical candidates, sparse carrier-hour and origin-weekday crosses, more trees, stronger L2 regularization, leaf-guided trees, deeper trees, and fewer approximate rounds all lost accuracy. The model now scores row by row in about 36 s and trains in about 15 s. I will research whether averaging complementary XGBoost tree methods gives a worthwhile AUC gain within the training limit.

Research: [scikit-learn's VotingClassifier documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html) defines soft voting as averaging predicted class probabilities, with optional weights. `hist` and `approx` use different split construction, and each has succeeded on this dataset; averaging might reduce the variance of their errors. The extra model roughly doubles fit and artifact size, so it needs a meaningful AUC gain to justify complexity.

## Experiment 41 — average hist and approx XGBoost (exploration: ensemble)

Hypothesis: the 0.7569 hist model and 0.7580 approx model make partly independent ranking errors. Equal probability averaging could improve AUC beyond the stronger member. Train both on the same allowed training rows and feature transformation, then pass the fitted soft-voting model to the unchanged harness evaluation.

Result: 0.7586 (+0.0006). Keep provisionally. The standard soft-voting wrapper adds only about 1.4 s to training and little evaluation time, but the gain is modest for the extra model and code. Test whether a principled weight toward the stronger approximate model improves it further.

## Experiment 42 — three-to-one vote toward approx (follow-up)

Hypothesis: the approximate model is stronger alone (0.7580 versus 0.7569), so its predictions should dominate the blend while the hist model contributes complementary corrections. Use soft-voting weights 3:1; retain the same two fitted estimators and all features.

Result: 0.7586 (tie at displayed precision). Discard: equal voting is simpler and as accurate as far as the harness reports.

## Experiment 43 — seven-day date block (exploration: temporal smoothing)

Hypothesis: exact DateCategory captures individual 2005 days, but a 7-day block can group neighboring dates that share weather or demand conditions. Add a 53-level categorical week block alongside exact date. [Airport delay periodicity research](https://stars.library.ucf.edu/facultybib2000/6790/) reports weekly patterns. All model settings remain fixed.

Result: 0.7586 (tie at displayed precision). Discard because the extra feature adds evaluation cost without improving the score.

## Experiment 44 — remove month-weekday interaction (ablation/simplification)

Hypothesis: DateCategory encodes both month and weekday for this single year, so MonthWeekday may be redundant after date identity was added. Remove its train-fitted vocabulary and prepared feature while retaining the two carrier interactions. Keep the simpler model if AUC is essentially equal.

Result: 0.7586 (tie at displayed precision). Keep. Four lines removed and evaluation time fell to 31.8 s from roughly 36 s.

## Experiment 45 — remove carrier-month interaction (ablation/simplification)

Hypothesis: after DateCategory and CarrierWeekday were added, CarrierMonth may be redundant despite its early small gain. Remove its vocabulary and prepared column, retaining CarrierWeekday. Keep only if the simpler model's AUC holds up.

Result: 0.7573 (-0.0013). Discard. CarrierMonth remains useful despite the exact date feature; restore it.

Research: [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) distinguishes column sampling per tree, level, and node. Per-node sampling at 0.8 is a moderate way to diversify splits while keeping every training row. The earlier 0.8 row subsample hurt, but it tested a different mechanism before the date features were added.

## Experiment 46 — sample columns at each split (exploration: diversity)

Hypothesis: with seven available features, allowing 80% of columns at each node could reduce repeated reliance on CRSDepTime and improve both tree-method members' generalization. Add `colsample_bynode=0.8` to their shared parameters; keep all data rows and the same feature set.

Result: 0.7588 (+0.0002). Keep. This one-line regularizer gives a small AUC gain with no meaningful time penalty.

## Experiment 47 — sample columns per tree (exploration: sampling granularity)

Hypothesis: drawing 80% of features once per tree may create more complementary trees than redrawing at each node, especially for the hist/approx ensemble. Replace `colsample_bynode=0.8` with `colsample_bytree=0.8` to compare sampling granularity at the same fraction.

Result: 0.7596 (+0.0008). Keep. Per-tree feature diversity helps more than per-node sampling, with similar runtime.

## Experiment 48 — stronger per-tree column sampling (follow-up)

Hypothesis: `colsample_bytree=0.7` will exclude about one more of the seven features per tree than 0.8, potentially further diversifying the two-model ensemble. Change only this fraction; if AUC falls, 0.8 may be close to the useful balance.

Result: 0.7594 (-0.0002). Discard. Stronger feature removal did not improve on 0.8.

## Experiment 49 — lighter per-tree column sampling (follow-up)

Hypothesis: `colsample_bytree=0.9` retains about one more feature per tree than 0.8, testing whether the gain comes from mild diversity rather than stronger exclusion. This brackets the kept 0.8 against the failed 0.7 and the former no-sampling setting.

Result: 0.7593 (-0.0003). Discard. The 0.8 fraction outperformed both 0.7 and 0.9; stop tuning this knob.

Research: [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `gamma` as the minimum loss reduction for a further split. It regularizes by refusing weak branches rather than by shrinking all leaf outputs or sampling data. This could remove noisy splits created by date and carrier interactions.

## Experiment 50 — minimum split gain of 1 (exploration: pruning)

Hypothesis: a split-gain threshold of 1 will prune branches with small training benefit, improving generalization while preserving the strong date and time splits. Add `gamma=1` to the shared hist/approx parameters; keep feature and sampling settings unchanged.

Result: 0.7580 (-0.0016). Discard. Explicitly pruning weak splits removes useful structure; do not pursue stronger gamma values.

## Synthesis after 50 experiments

Best Eval AUC is 0.7596 at `3227d04`, +0.0393 above baseline. The fourth decade of tests found a modest gain from averaging hist and approx probabilities and a further gain from sampling 80% of columns per tree. Other sampling fractions were worse. Removing MonthWeekday made the feature set and row-wise evaluation simpler at equal displayed AUC; CarrierMonth remains necessary. A weekly date block and split-gain pruning did not help. The current ensemble fits in about 15.5 s and evaluates in about 32 s. With about 40 minutes left, I will research seed averaging to reduce variance from column sampling, then explore further only if it provides a material AUC gain.

Research: [scikit-learn's bagging example](https://scikit-learn.org/stable/auto_examples/ensemble/plot_bias_variance.html) shows that averaging randomized trees can reduce prediction variance. [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) confirms that `colsample_bytree` draws a new subset for each tree. This makes seed averaging meaningful in the current model. Training four members should take around twice the current 15.5 s, below the one-minute limit.

## Experiment 51 — two seeds of each tree method (exploration: ensemble variance)

Hypothesis: averaging seed 42 and seed 17 for both approx and hist models will smooth errors introduced by per-tree feature sampling. Keep the same features and hyperparameters, and use four equally weighted members. The extra artifact and fit cost must be justified by a noticeable AUC gain.

Result: 0.7600 (+0.0004). Keep provisionally. Training is 31 s, evaluation 32 s, and the saved artifact is 22.7 MB. The code is a short loop, but the computational cost doubled for a small gain. Further ablation will check whether both tree methods are needed at two seeds.

## Experiment 52 — two-seed approx only (ablation/simplification)

Hypothesis: the two approximate models may supply nearly all the benefit, and the weaker histogram members might dilute their ranking. Remove both hist estimators while averaging the same two approx seeds. Keep if AUC is equal or better, since the model and artifact are smaller.

Result: 0.7599 (-0.0001 versus the four-model ensemble). Keep as an effective tie with half as many models and about 5 s faster training. The best raw Eval AUC remains 0.7600 at `6a83fef`; the two-model branch is the simpler tradeoff.

## Experiment 53 — mixed-method two-model ensemble (ablation: diversity source)

Hypothesis: a histogram member with seed 17 may complement approximate seed 42 more than a second approximate seed does. Replace approximate seed 17 with histogram seed 17, keeping the same features, hyperparameters, and two-model cost. Keep only if the mixed pair matches or exceeds the current 0.7599 AUC.

Result: 0.7594 (-0.0005). Discard. A second approximate seed helps more than replacing it with one histogram seed.

## Experiment 54 — three-model ensemble (ablation: histogram contribution)

Hypothesis: adding histogram seed 42 to the two approximate seeds may capture most or all of the four-model ensemble's 0.0001 advantage while avoiding its fourth fit. Keep if AUC reaches at least 0.7600, or ties the two-model score with a meaningful benefit in another metric.

Result: 0.7600 (+0.0001 versus the two-model branch), matching the four-model best with one fewer estimator. Keep. Training took 28.7 s and evaluation 31.8 s. This is the best raw AUC at lower model count than the previous raw-best commit `6a83fef`.

Research note: [scikit-learn's TargetEncoder documentation](https://scikit-learn.org/1.4/modules/generated/sklearn.preprocessing.TargetEncoder.html) warns that fitting a target encoder and then transforming the same training rows leaks their labels; its training transform uses cross-fitting. I will leave route-level target encoding for a deliberate, leakage-safe implementation rather than inject a naive target mean into the row-wise `prepare` function.

## Experiment 55 — smaller minimum child weight (follow-up: rich-feature regularization)

Hypothesis: `min_child_weight=10` was selected before DateCategory and column-sampled seed averaging were introduced. The richer model may be oversmoothing date and airport interactions. Lower it to 5 in all three members; keep if Eval AUC improves. The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/release_0.72/tutorials/param_tuning.html) identifies this parameter as a tree complexity control.

Result: 0.7596 (-0.0004). Discard. The current weight of 10 still helps after the richer date feature and ensemble are added.

## Experiment 56 — L1 leaf regularization (exploration: sparse leaf effects)

Hypothesis: a modest `reg_alpha=1` can shrink noisy date- or airport-specific leaf weights while retaining the splits selected by the current tree structure. This is distinct from the failed gamma threshold, which removes splits entirely, and from L2=10, which shrank all leaves more strongly. The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `reg_alpha` as L1 regularization on leaf weights.

Result: 0.7603 (+0.0003), new best. Keep. Training remained 28.8 s. The small gain warrants checking whether a lighter or stronger L1 penalty is better.

## Experiment 57 — stronger L1 penalty (follow-up)

Hypothesis: since `reg_alpha=1` improved AUC, additional shrinkage may suppress residual noisy leaf effects. Increase only `reg_alpha` to 3 in all three members, leaving the ensemble and features fixed.

Result: 0.7610 (+0.0007), new best. Keep. L1 shrinkage appears well matched to the high-cardinality date and airport splits; training was 27.3 s.

## Experiment 58 — L1 penalty 8 (follow-up: upper bracket)

Hypothesis: the gains from L1 values 1 and 3 suggest the optimum may be above 3. Test 8 as a clearly stronger penalty in the same three-member ensemble, to bracket the useful range rather than making a tiny parameter step.

Result: 0.7573 (-0.0037). Discard. This is too much shrinkage; the useful range is below 8.

## Experiment 59 — L1 penalty 5 (follow-up: bracket midpoint)

Hypothesis: alpha 3 helped and alpha 8 hurt sharply. A midpoint value of 5 tests whether the optimum lies slightly above 3 or whether the model is already overregularized there. Only `reg_alpha` changes.

Result: 0.7607 (-0.0003). Discard. The useful L1 range is narrow and alpha 3 remains best among 1, 3, 5, and 8.

## Experiment 60 — remove histogram member under L1 (ablation/simplification)

Hypothesis: alpha 3 may reduce model variance enough that the histogram member contributes less than it did without L1. Remove only `hist_42` from the three-member ensemble. A tie at 0.7610 would make the two-member model preferable because it is faster and smaller; a clear loss will retain the full ensemble.

Result: 0.7605 (-0.0005). Discard. The third member still improves ranking under L1, and the reported training time fell by less than a second.

## Synthesis after 60 experiments

Best Eval AUC is 0.7610 at `34d5b22`, +0.0407 over the baseline. In the last ten tests, seed averaging and a three-model ensemble reached 0.7600; adding L1 leaf regularization was the main further gain. Alpha 3 was best among 0, 1, 3, 5, and 8. The histogram member remains useful even with L1. A lower minimum child weight and a mixed two-model pair both hurt. The date category, carrier interactions, column sampling, and regularized ensemble remain the strongest combination. With about 21 minutes left, I will search for a different, low-cost regularization or temporal representation that can improve beyond this local optimum.

Research: [scikit-learn's time feature engineering example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) explains that sine/cosine transforms remove the jump between the last and first values of a daily clock. The existing HHMM numeric feature has a discontinuity between late-night and early-morning departures, while the previous categorical hour and minute-only tests addressed different representations. [XGBoost's tuning notes](https://xgboost.readthedocs.io/en/release_2.0.0/tutorials/param_tuning.html) also support revisiting depth now that L1 constrains leaves, if time remains after the temporal test.

## Experiment 61 — cyclical departure time (exploration: periodic schedule representation)

Hypothesis: adding sine and cosine of scheduled minute-of-day will expose overnight continuity and broad daily phases to depth-4 trees while retaining raw HHMM for sharp time thresholds. The transform uses only each row's CRSDepTime, adds no lookups, and costs two numeric features. Keep only for a meaningful AUC improvement.

Result: 0.7611 (+0.0001), but training rose to 32.7 s and evaluation to 36.7 s. Discard under the simplicity criterion: two extra features and per-row trigonometry are not justified by this displayed gain.

## Experiment 62 — depth five under L1 (follow-up: regularized capacity)

Hypothesis: depth five hurt the approximate model before L1 regularization, but alpha 3 may now suppress the noisy leaf weights that made extra depth overfit. Increase `max_depth` from 4 to 5 in the current three-model ensemble; keep only for a clear gain because deeper trees cost more time and artifact size. This follows [XGBoost's bias-variance tuning notes](https://xgboost.readthedocs.io/en/release_2.0.0/tutorials/param_tuning.html).

Result: 0.7630 (+0.0020), new best. Keep. Training rose only to 30.2 s and evaluation remained 31.9 s. L1 regularization changes the depth tradeoff: the richer trees now capture useful interactions without the earlier loss.

## Experiment 63 — depth six under L1 (follow-up: capacity bracket)

Hypothesis: depth 5's clear gain may indicate remaining underfitting in the date, carrier, airport, and time interactions. Test depth 6 with alpha 3 and the same ensemble; the added capacity must outperform 0.7630 to justify larger trees.

Result: 0.7646 (+0.0016), new best. Keep. Training took 31.6 s. Under alpha 3, the model benefits from more complex interactions than depth 5 allowed.

## Experiment 64 — depth seven under L1 (follow-up: capacity bracket)

Hypothesis: the improvement from depths 4 to 5 to 6 suggests another depth increment might capture airport-date-time combinations. Test depth 7 with all other settings fixed. Discard if AUC does not improve clearly or training cost rises sharply.

Result: 0.7651 (+0.0005), new best. Keep: one parameter change bought a visible AUC gain. Training rose to 35.7 s but remains safely under the 60 s limit.

## Experiment 65 — depth eight under L1 (follow-up: capacity bracket)

Hypothesis: depth 7 still improved, but its smaller gain may signal the top of the capacity curve. Test depth 8 with the same alpha and ensemble. This is the last depth increment unless it produces a substantial gain, because training cost is rising.

Result: 0.7652 (+0.0001), new raw best. Keep: the code change is a single parameter and training rose only 2.0 s to 37.7 s. The diminishing gain argues against further depth increases; next I will retune regularization or rounds at this depth.

## Experiment 66 — stronger L1 at depth eight (follow-up: capacity control)

Hypothesis: the depth-8 ensemble has more leaf weights than the depth-4 model where alpha 3 beat alpha 5. Increasing `reg_alpha` to 5 may now control additional noisy leaves and let the deeper interactions generalize better. Change only alpha; keep if AUC improves.

Result: 0.7668 (+0.0016), new best. Keep. Training was 36.3 s. More leaf shrinkage is beneficial at depth 8, unlike at depth 4, reinforcing that the capacity and regularization settings need to be tuned together.

## Experiment 67 — alpha eight at depth eight (follow-up: regularization bracket)

Hypothesis: alpha 5's strong improvement at depth 8 suggests that the deeper model can use stronger shrinkage than the depth-4 model. Test alpha 8, which hurt at depth 4, to locate the upper side of this new capacity-regularization optimum.

Result: 0.7646 (-0.0022). Discard. The useful alpha is below 8 at this depth; alpha 5 remains best.

## Experiment 68 — 400 boosting rounds at depth eight (follow-up: training horizon)

Hypothesis: 600 rounds were selected for depth-4 trees. Depth-8 trees learn more interactions per round, so reducing to 400 may avoid late overfit and shorten training while retaining the alpha-5 regularized structure. Keep if AUC matches or improves the current best; a small loss might still merit a large runtime saving under the simplicity criterion.

Result: 0.7662 (-0.0006). Discard despite training falling to 24.9 s: the goal is highest AUC, and this is a material ranking loss relative to the small cost of the 600-round run.

## Experiment 69 — 800 boosting rounds at depth eight (follow-up: upper horizon bracket)

Hypothesis: reducing from 600 to 400 rounds hurt, so later boosting rounds still help the depth-8, alpha-5 model. Test 800 rounds to determine whether the useful horizon extends beyond 600, while watching the 60-second training limit. This is a 200-round step, not a cosmetic tweak.

Result: 0.7668 (tie), but training rose to 48.3 s from 36.3 s. Discard: the extra 200 rounds add cost without visible benefit. Six hundred rounds is the better horizon.

## Experiment 70 — remove histogram member at depth eight (ablation/simplification)

Hypothesis: deeper, more strongly regularized approximate trees may capture patterns that previously required a separate histogram model. Remove the histogram member only; if the two-model ensemble retains 0.7668 AUC, it is preferable for size and training cost. Earlier at depth 4 and alpha 3, this ablation lost 0.0005 AUC.

Result: 0.7666 (-0.0002), training 32.6 s versus 36.3 s. Discard. The histogram member still contributes a small ranking gain, and the training saving is modest.

## Synthesis after 70 experiments

Best Eval AUC is 0.7668 at `7271b31`, +0.0465 over baseline. Experiments 61–70 show that regularization and depth interact strongly: with alpha 3, depths 5–8 improved steadily; at depth 8, increasing alpha to 5 added another 0.0016. Alpha 8 overregularized. Four hundred rounds lost AUC and 800 tied at greater cost, so 600 remains best. The three-member ensemble still edges out its two-member ablation. Cyclical time features added only 0.0001 AUC at noticeable preparation cost and were discarded. With only a few minutes left, I will focus on simple feature or categorical-parameter ablations and then finalize at the best kept commit.

Research: [XGBoost's Python API](https://xgboost.readthedocs.io/en/release_3.3.0/python/python_api.html) defines gain importance as average split gain for a feature; the earlier fitted model assigned little gain to Distance. [Scikit-learn's correlated-feature example](https://scikit-learn.org/stable/auto_examples/inspection/plot_permutation_importance_multicollinear.html) cautions that importance alone can be misleading when predictors overlap. A direct retraining ablation is therefore more decisive than relying on the old importance value.

## Experiment 71 — remove Distance (ablation/simplification)

Hypothesis: the richer depth-8 ensemble may express route effects through Origin and Dest without Distance. The earlier depth-4 model lost 0.0005 when Distance was removed, but the model has changed substantially since then. Remove only Distance; keep if AUC is essentially equal, because it simplifies per-row preparation.

Result: 0.7656 (-0.0012). Discard. Distance remains useful even with deeper trees and the regularized ensemble.

## Experiment 72 — categorical split threshold 256 (follow-up: date partition search)

Hypothesis: at depth 8 and alpha 5, more candidate date-category partitions may help than at depth 4, where 256 scored 0.0001 below 128. Double `max_cat_threshold` from 128 to 256, changing no features or other parameters. The [XGBoost categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) describes partition-based category splits and their configurable threshold.

Result: 0.7670 (+0.0002), new best. Keep. The extra split candidates help slightly in the deeper regularized model; training took 37.7 s, safely within the limit.

## Final summary

Best Eval AUC: **0.7670 at `fad5697`**, up **0.0467** from the 0.7203 baseline. The strongest gains came from more boosting capacity, a categorical exact-date feature, compact carrier-calendar interactions, approximate plus histogram probability averaging with two approximate seeds, per-tree column sampling, L1 leaf regularization, and depth 8. At depth 8, alpha 5, 600 rounds, and a categorical split threshold of 256 gave the best observed result. High-cardinality route and origin-weekday categories, row subsampling, excess L1, removing Distance, and removing the histogram member hurt; 800 rounds tied at greater cost. Further work could test a leakage-safe, cross-fitted route encoding and validate the selected model on the human-only held-out split. No held-out data or post-hoc ground-truth tools were accessed during this run.
