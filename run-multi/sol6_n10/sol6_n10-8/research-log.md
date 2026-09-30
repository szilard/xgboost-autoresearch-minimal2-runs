# Research log — sep30

## Baseline — 92e43e6

Untouched `train.py`: 30 trees, depth 6, learning rate 0.1, native categorical columns. Eval AUC 0.7203; run 31.9s (training 1.1s, evaluation 30.8s). This establishes the reference for subsequent changes.

## Research before experiment 1

The [XGBoost parameter tuning guide](https://xgboost.readthedocs.io/en/release_0.72/tutorials/param_tuning.html) identifies tree complexity, row and column sampling, and learning rate/round count as the main controls for generalization. The [categorical data guide](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) explains one-hot versus partitioned splits. Flight-delay work also points to scheduled departure time and route as useful signals ([example](https://github.com/longwind48/airline-delay-prediction)). These are candidate directions; I will test their effects on this data instead of importing other datasets or features.

## Experiment 1 — more rounds

Type: exploration. Hypothesis: 30 trees at learning rate 0.1 underfit. Increase only `n_estimators` to 150 and compare with baseline. Source: XGBoost tuning guide above.

Result: 0a85357, Eval AUC 0.7332 (+0.0129), kept. Training 2.2s and evaluation 30.5s. The large gain supports the underfitting hypothesis.

## Experiment 2 — 300 rounds

Type: follow-up. Hypothesis: the substantial gain from 30 to 150 trees suggests extra boosting rounds may still add signal. Increase only `n_estimators` to 300, retaining learning rate 0.1 and the same features. Source: [XGBoost tuning guide](https://xgboost.readthedocs.io/en/release_0.72/tutorials/param_tuning.html).

Result: c06a378, Eval AUC 0.7342 (+0.0010), kept. Gains are tapering but still positive.

## Experiment 3 — 600 rounds

Type: follow-up. Hypothesis: doubling rounds again can reveal whether the learning curve has reached its peak; the previous change still gained 0.0010 AUC. Increase only `n_estimators` to 600. Source: [XGBoost tuning guide](https://xgboost.readthedocs.io/en/release_0.72/tutorials/param_tuning.html).

Result: 273ff47, Eval AUC 0.7299 (-0.0043), discarded. The 0.1 learning rate overfits by 600 rounds; revert to c06a378.

## Research before route feature

The [XGBoost categorical data guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) says categorical splits can be one-hot or partition based. A first-party [airline delay project](https://github.com/longwind48/airline-delay-prediction) analyzes route and departure time as useful predictors. Training-only inspection found 4,290 route categories, with 107 appearing once. Sparse routes could overfit, so the result is uncertain.

## Experiment 4 — route category

Type: exploration. Hypothesis: an explicit origin–destination category lets XGBoost learn route-specific risk more efficiently than separate airport splits. Add a `Route` categorical feature constructed from each row, with category levels fixed from train only. Retain the 300-tree model. Source: XGBoost categorical guide above.

Result: 38e5e6d, Eval AUC 0.7050 (-0.0292), discarded. The high-cardinality route feature appears to overfit. Evaluation time rose from about 31s to 43s.

## Research before calendar feature

The [scikit-learn time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) discusses ordinal and cyclic representations of time, and notes that trees can model non-linear interactions with these features. A numeric day index may let neighboring dates share splits while retaining month and day categories.

## Experiment 5 — ordinal date

Type: exploration. Hypothesis: a numeric date index lets trees detect contiguous seasonal or storm periods that are awkward to express with separate month and day categories. Add `DateIndex = Month * 31 + DayofMonth`, computed from each row only, to the 300-tree model. Source: scikit-learn time-feature example above.

Result: b15bcba, Eval AUC 0.7378 (+0.0036), kept. Calendar adjacency adds useful information for splits.

## Experiment 6 — categorical departure hour

Type: follow-up to temporal feature. Hypothesis: hour-specific departure effects are easier to capture from a 24-level category than from repeated cuts on HHMM. Add scheduled departure hour as a category while keeping raw scheduled time and DateIndex. Source: [scikit-learn time-feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html), [first-party airline feature analysis](https://github.com/Prashant-4527/flight-delay-prediction).

Result: a01e533, Eval AUC 0.7369 (-0.0009), discarded. The categorical hour does not add useful signal on top of raw time.

## Experiment 7 — shallower trees

Type: exploration. Hypothesis: depth 6 may model overly specific combinations; depth 4 should improve generalization with 300 trees and DateIndex. Source: [XGBoost tuning guide](https://xgboost.readthedocs.io/en/release_0.72/tutorials/param_tuning.html) on controlling complexity via max_depth.

Result: e9c90ba, Eval AUC 0.7382 (+0.0004), kept. Shallower trees help a little and reduce training time.

## Experiment 8 — depth 3

Type: follow-up. Hypothesis: the gain from depth 6 to 4 may continue at depth 3, but too little capacity could underfit. Change only max_depth to 3 to bound the useful depth range. Source: XGBoost tuning guide above.

Result: ca9563e, Eval AUC 0.7342 (-0.0040), discarded. Depth 3 underfits; depth 4 is best of depths 3, 4, 6 tested.

## Experiment 9 — minimum child weight 5

Type: exploration. Hypothesis: increasing the minimum Hessian needed for a split can suppress thin, noisy leaves while retaining depth-4 interactions. Set `min_child_weight=5`; all else fixed. Source: [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html).

Result: 6e194b1, Eval AUC 0.7378 (-0.0004), discarded. Restricting thin leaves did not beat the simpler default.

## Experiment 10 — smaller learning rate and more rounds

Type: exploration. Hypothesis: 0.05 learning rate with 500 rounds can retain the benefit of the 300-round model while reducing sensitivity to noisy late boosting steps. This is a deliberate joint change because a lower rate requires more rounds. Source: [XGBoost tuning guide](https://xgboost.readthedocs.io/en/release_0.72/tutorials/param_tuning.html).

Result: 1282a28, Eval AUC 0.7381 (-0.0001), discarded under the simplicity criterion; the extra 200 trees do not improve AUC.

## Synthesis after 10 experiments

The starter's 30 rounds underfit badly. A moderate 300 rounds improved substantially, while 600 rounds overfit. An ordinal date from month and day gave a useful +0.0036; a high-cardinality route category lost 0.0292 and categorical hour added nothing. Depth 4 was slightly better than depth 6; depth 3 underfit. Raising minimum child weight to 5 and halving learning rate with compensating rounds did not improve on the simpler 300-round, depth-4 model. Current best: e9c90ba at 0.7382. The likely useful range is moderate model capacity plus compact temporal structure. Next investigate categorical split settings, training-only historical rates with sufficient smoothing, and sampling regularization.

## Research after 10 experiments

The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/release_0.72/tutorials/param_tuning.html) suggests row/column sampling as a noise-robust alternative to limiting tree complexity. The [XGBoost categorical parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `max_cat_threshold` as an overfitting control for partitioned category splits. The [scikit-learn target encoder example](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html) demonstrates severe overfitting when training examples receive an encoding fitted with their own labels; avoid direct target statistics without a valid training-only scheme. Sampling and categorical split settings are cleaner next tests.

## Experiment 11 — row sampling

Type: exploration. Hypothesis: `subsample=0.8` can reduce dependence on noisy flight records and improve Eval AUC without changing the tree shape or features. Source: XGBoost tuning guide above.

Result: 11bc47d, Eval AUC 0.7272 (-0.0110), discarded. Row sampling harms this dataset strongly.

## Experiment 12 — wider categorical partitions

Type: exploration. Hypothesis: origin/destination have 283 levels, so allowing up to 128 categories per partition split may capture broader airport groupings better than the default. Set `max_cat_threshold=128`, keeping all other settings. Source: [XGBoost categorical parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html).

Result: e4ee6ad, Eval AUC 0.7393 (+0.0011), kept. Wider category partition search helps.

## Experiment 13 — nearly full categorical partitions

Type: follow-up. Hypothesis: the gain at threshold 128 may continue when the partition search includes almost all 283 airport levels. Raise only `max_cat_threshold` to 256 to test the direction and overfitting limit. Source: XGBoost categorical parameter documentation above.

Result: f3e1bd5, Eval AUC 0.7389 (-0.0004), discarded. A moderate threshold beats nearly full partition search.

## Experiment 14 — one-hot categorical splits

Type: exploration. Hypothesis: single-category one-hot splits may avoid spurious grouping of airport categories and improve generalization. Set `max_cat_to_onehot=300` so every existing categorical feature uses one-hot splits; retain threshold 128 though it will not apply to these features. Source: [XGBoost categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html).

Result: c328885, Eval AUC 0.7323 (-0.0070), discarded. Airport grouping is helpful; one-hot single-airport splits are less effective.

## Experiment 15 — depth 5 with wider partitions

Type: follow-up. Hypothesis: with better categorical partitions, depth 5 may capture useful interactions missed at depth 4 without the overfitting of depth 6. Set only max_depth=5. Source: [XGBoost tuning guide](https://xgboost.readthedocs.io/en/release_0.72/tutorials/param_tuning.html).

Result: f95480a, Eval AUC 0.7383 (-0.0010), discarded. Depth 4 remains best with the wider categorical threshold.

## Research before leaf regularization

The [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `reg_lambda` as L2 regularization on leaf weights; larger values make the model more conservative. This differs from depth or minimum child weight because it shrinks leaf effects rather than forbidding a split.

## Experiment 16 — L2 leaf regularization

Type: exploration. Hypothesis: `reg_lambda=10` can shrink unreliable leaf estimates, especially for rarer airport categories, without removing useful depth-4 interactions. Retain all other best settings. Source: XGBoost parameter documentation above.

Result: 35a162a, Eval AUC 0.7382 (-0.0011), discarded. Stronger L2 shrinkage harms AUC.

## Experiment 17 — remove L2 leaf penalty

Type: follow-up. Hypothesis: because stronger L2 hurt, the default penalty may already be more than this model needs. Set `reg_lambda=0` to test less shrinkage, leaving everything else fixed. Source: [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html).

Result: 851df1c, Eval AUC 0.7391 (-0.0002), discarded. Default L2 remains best. Five consecutive changes since e4ee6ad have not improved the best score, so pause for new research.

## Plateau research before experiment 18

A [study using XGBoost for flight delays](https://www.sciencedirect.com/science/article/pii/S2772415822000050) reports scheduled departure time and weather among important predictors. Another [flight-delay study](https://doi.org/10.1145/3786484.3786539) emphasizes aligning weather and calendar information with local scheduled departure. This dataset has no weather columns, but a continuous scheduled date-and-time feature may let a shallow tree detect short periods of unusual delay risk without additional data or label aggregates. This is an inference from the sources, not a result they directly establish.

## Experiment 18 — scheduled date-time index

Type: exploration. Hypothesis: combining DateIndex and scheduled minutes into one chronological numeric feature can expose short weather or operational periods with a single tree split. Add DateTimeIndex while retaining separate date and HHMM columns. Source: flight-delay studies above.

Result: db7f4c7, Eval AUC 0.7387 (-0.0006), discarded. The combined timestamp adds cost without improving AUC.

## Experiment 19 — remove day-of-month category

Type: ablation/simplification. Hypothesis: DateIndex encodes calendar position and DayOfWeek covers weekly rhythm, so a separate DayofMonth category may be redundant and encourage memorization. Remove it from the feature list while still using it to calculate DateIndex. Source: [scikit-learn time-feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html).

Result: 27487b9, Eval AUC 0.7318 (-0.0075), discarded. Repeated within-month patterns matter beyond one-year chronological position.

## Experiment 20 — numeric day-of-month alongside category

Type: follow-up. Hypothesis: ordered day-of-month values may help the model share a split across nearby days (for example, start or end of month), while retaining the categorical feature needed for irregular repeated patterns. Add a numeric DayOfMonth feature. Source: [scikit-learn time-feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html).

Result: 139b69d, Eval AUC 0.7393 (tie), discarded under the simplicity criterion. The extra feature costs evaluation time without a measurable gain.

## Synthesis after 20 experiments

Current best is e4ee6ad, Eval AUC 0.7393 (+0.0190 over the untouched baseline). A moderate number of trees (300), depth 4, ordinal calendar date, and a categorical partition threshold of 128 account for the improvement. Row sampling, one-hot airport splits, more regularization, deeper trees, and high-cardinality route categories hurt. L2 penalty near its default is adequate. DayofMonth category is important even with DateIndex, while its numeric duplicate and a combined date-time feature add no value. The model appears to benefit from shared categorical airport groups and both chronological and repeated calendar patterns. Next investigate histogram resolution for numeric times, alternative temporal representations, and feature interactions that preserve broad support.

## Research after 20 experiments

The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) says histogram trees use 256 bins by default for continuous features; more bins can improve split optimality at greater training cost. CRSDepTime has 1,162 distinct values, Distance 1,267, and DateIndex spans most days of the year, so binning may discard useful resolution. The [XGBoost categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) also reinforces keeping partitioned categories for shared airport effects.

## Experiment 21 — 512 numeric bins

Type: exploration. Hypothesis: increasing `max_bin` from 256 to 512 allows finer schedule, distance, and date splits and improves ranking. Keep other best settings. Source: XGBoost parameter guide above.

Result: aef3338, Eval AUC 0.7378 (-0.0015), discarded. Finer numeric splits hurt generalization.

## Experiment 22 — 128 numeric bins

Type: follow-up. Hypothesis: because finer bins hurt, coarser bins may smooth noisy schedule or distance distinctions. Set `max_bin=128` to test the opposite side of default 256. Source: [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html).

Result: 33a3041, Eval AUC 0.7391 (-0.0002), discarded. Default 256 bins is best among 128, 256, 512.

## Research before alternate tree growth

The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `lossguide` as splitting the leaf with the highest loss change, versus depthwise growth at the nodes closest to the root. A leaf cap can hold total tree size roughly constant while allowing an asymmetric shape. This may let the model spend splits on airport/time combinations with stronger signals.

## Experiment 23 — loss-guided 16-leaf trees

Type: exploration. Hypothesis: asymmetric trees with 16 leaves can allocate model capacity to the most informative flight subgroups more effectively than depth-4 trees. Set `grow_policy=lossguide`, `max_depth=0`, and `max_leaves=16` as one coupled architecture change. Source: XGBoost parameter guide above.

Result: 21e9999, Eval AUC 0.7362 (-0.0031), discarded. The asymmetric growth policy is less effective than depthwise growth at this leaf budget.

## Research before compact feature interaction

The [scikit-learn categorical boosting example](https://scikit-learn.org/stable/auto_examples/ensemble/plot_gradient_boosting_categorical.html) explains that native category partitions can encode arbitrary category groupings in one split, whereas an ordinal representation can require deeper trees. Calendar-related month and weekday features appear in [flight-delay research](https://www.theseus.fi/bitstream/10024/889008/4/Sumay_Valkama_Ana.pdf). A combined month-weekday category has at most 84 levels, giving a shallower tree a direct way to group seasonal weekday regimes; whether these interactions generalize is an empirical question.

## Experiment 24 — month × weekday category

Type: exploration. Hypothesis: a low-cardinality month-weekday interaction captures seasonal differences in weekly delay patterns with a single partition split, freeing depth for carrier/airport effects. Add this category with levels fitted from train. Retain original month and weekday columns. Sources: categorical boosting example and flight-delay study above.

Result: 6a9d0cb, Eval AUC 0.7410 (+0.0017), kept. A compact categorical interaction adds a useful signal.

## Experiment 25 — carrier × weekday category

Type: follow-up to compact interaction. Hypothesis: weekly delay patterns differ by carrier, and a 20×7 category can expose them with one split while retaining the successful month-weekday feature. Source: [flight-delay XGBoost study](https://www.sciencedirect.com/science/article/pii/S2772415822000050) identifying carrier and departure time as influential, and [XGBoost categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html).

Result: 7ba8e0c, Eval AUC 0.7433 (+0.0023), kept. Carrier-specific weekly patterns appear useful.

## Experiment 26 — carrier × month category

Type: follow-up. Hypothesis: seasonal changes in each carrier's operations or exposure may be useful; a 20×12 interaction remains reasonably supported by 200K training rows. Add CarrierMonth category, retaining earlier interactions. Sources: [flight-delay XGBoost study](https://www.sciencedirect.com/science/article/pii/S2772415822000050), [XGBoost categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html).

Result: a7179cb, Eval AUC 0.7443 (+0.0010), kept. Carrier-specific seasonality helps.

## Experiment 27 — categorical calendar date

Type: exploration. Hypothesis: a calendar-date category can group isolated disruption days sharing elevated delay propensity while the numeric DateIndex keeps adjacency. Dates each have hundreds of sampled flights, so the category is much better supported than route. Add DateCat with levels fitted from train. Source: [flight-delay study on date and weather alignment](https://doi.org/10.1145/3786484.3786539), [XGBoost categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html).

Result: 74b3ade, Eval AUC 0.7561 (+0.0118), kept. Individual-day signal is strong, likely reflecting shared day-level disruptions; this is an inference from the result.

## Experiment 28 — remove numeric DateIndex

Type: ablation/simplification. Hypothesis: the categorical date may subsume the ordered DateIndex signal. Remove DateIndex from the model features while still using its row-wise value to construct DateCat. If equal or better, keep the simpler model. Source: the strong result of experiment 27.

Result: 2d09938, Eval AUC 0.7561 (tie), kept for one fewer model feature and about one second less evaluation time. The categorical date captures the useful calendar signal by itself.

## Experiment 29 — wider categorical partitions with DateCat

Type: follow-up. Hypothesis: DateCat has 365 levels, so raising max_cat_threshold from 128 to 256 may improve groupings of individual days. This differs from experiment 13 because DateCat was absent then. Source: [XGBoost categorical parameters](https://xgboost.readthedocs.io/en/stable/parameter.html).

Result: 390cfe9, Eval AUC 0.7568 (+0.0007), kept. The date category benefits from more partition candidates.

## Experiment 30 — full date partitions

Type: follow-up. Hypothesis: threshold 512 includes all 365 date levels and may improve further on the gain at 256. Only change max_cat_threshold. Source: XGBoost categorical parameter documentation above.

Result: 1ac7797, Eval AUC 0.7557 (-0.0011), discarded. Full partition search slightly overfits or selects less useful groups.

## Synthesis after 30 experiments

Current best is 390cfe9, Eval AUC 0.7568 (+0.0365 over the untouched baseline). Compact month-weekday, carrier-weekday, and carrier-month category interactions added 0.0050 AUC together on top of the prior best. A categorical calendar date then added 0.0118. Numeric DateIndex became redundant and was removed at equal AUC. With DateCat, a categorical partition threshold of 256 beats 128 and 512. The working theory is that day-level shared disruptions and medium-cardinality schedule/carrier interactions matter more than generic regularization or increasing tree size. Next investigate small time-of-day interactions, effects by airport/carrier, and whether any added categories can replace existing ones while keeping performance.

## Research after 30 experiments

A [UC Berkeley flight-delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) reports carrier-specific variation by departure hour, with later flights showing stronger delay accumulation. Its project uses more features than this dataset, but the carrier-time interaction is available here. The [XGBoost categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) supports grouping modest-cardinality interaction levels with partitioned splits. To avoid the sparse route-category problem, start with 3-hour blocks (at most 160 carrier-time levels).

## Experiment 31 — carrier × departure time block

Type: exploration. Hypothesis: carrier-specific schedule and late-day delay accumulation is easier for the depth-4 model to learn from a 20×8 category than from repeated splits on carrier and raw HHMM. Add CarrierTimeBlock for 3-hour scheduled blocks. Sources: Berkeley project and XGBoost categorical guide above.

Result: 1329127, Eval AUC 0.7559 (-0.0009), discarded. Three-hour buckets may smooth away carrier-specific hourly changes, or the raw time/carrier pair may already suffice.

## Experiment 32 — carrier × scheduled hour

Type: follow-up. Hypothesis: the Berkeley analysis reports hourly carrier differences; one-hour bins may retain signal lost by the three-hour interaction. Replace the prior proposed 3-hour bucket with 24 hourly levels per carrier, while starting from the best kept commit. Source: [Berkeley project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches).

Result: 6ca7bd1, Eval AUC 0.7531 (-0.0037), discarded. Carrier-hour interaction overfits or duplicates schedule information; three-hour bins were less harmful but still unhelpful.

## Experiment 33 — 450 trees with richer features

Type: follow-up to current best. Hypothesis: the new DateCat and compact carrier interactions may need more boosting steps than the older feature set. Increase n_estimators from 300 to 450 at learning rate 0.1. Unlike experiment 3, this tests the richer current feature set. Source: [XGBoost tuning guide](https://xgboost.readthedocs.io/en/release_0.72/tutorials/param_tuning.html).

Result: ac7c421, Eval AUC 0.7556 (-0.0012), discarded. Extra rounds still overfit with the richer feature set.

## Experiment 34 — 200 trees with richer features

Type: follow-up. Hypothesis: if 450 rounds hurt, the current feature set may peak before 300 rounds. Test 200 trees at the same rate, depth and features to bracket the optimum. Source: [XGBoost tuning guide](https://xgboost.readthedocs.io/en/release_0.72/tutorials/param_tuning.html).

Result: 7876199, Eval AUC 0.7552 (-0.0016), discarded. The richer feature set peaks near 300 rather than 200 or 450 rounds. Four consecutive discards since experiment 30 prompt a research pause.

## Plateau research before feature ablations

[Research on feature selection for boosted trees](https://proceedings.mlr.press/v108/han20a.html) discusses redundancy and interaction preservation. In this particular 2005-only dataset, DateCat uniquely determines month and weekday, so MonthWeekday is a deterministic function of another model feature. Keeping it may still help shallow trees through a direct grouping, but it also adds competing splits and evaluation cost. A controlled ablation will resolve this.

## Experiment 35 — remove MonthWeekday

Type: ablation/simplification. Hypothesis: DateCat now subsumes most month-weekday information, so removing MonthWeekday may preserve ranking with less complexity. Delete its level lookup and prepared feature, retaining all others. Source: feature-selection research above and current feature definitions.

Result: 2b6a167, Eval AUC 0.7568 (tie), kept. Evaluation time fell from about 51s to 47s. The explicit month-weekday pair is redundant with DateCat for this model.

## Experiment 36 — remove CarrierWeekday

Type: ablation/simplification. Hypothesis: DateCat plus carrier may also make CarrierWeekday redundant. Remove only this interaction to test whether it still helps after categorical date was added. Source: the controlled ablation result in experiment 35 and [feature-selection research](https://proceedings.mlr.press/v108/han20a.html).

Result: 655b321, Eval AUC 0.7556 (-0.0012), discarded. CarrierWeekday still improves shallow-tree ranking despite being derivable from DateCat and carrier.

## Experiment 37 — remove CarrierMonth

Type: ablation/simplification. Hypothesis: CarrierMonth may be redundant now that DateCat encodes month, even though CarrierWeekday remains helpful. Remove only CarrierMonth, restoring CarrierWeekday first. Source: experiments 35–36.

Result: d7a0aba, Eval AUC 0.7555 (-0.0013), discarded. CarrierMonth still adds useful interaction information.

## Experiment 38 — remove standalone Month

Type: ablation/simplification. Hypothesis: DateCat determines month, and CarrierMonth retains carrier-season interaction, so standalone Month may be redundant. Remove it from cat_cols only, keeping its use in derived features. Source: results of experiments 35–37 and [feature-selection research](https://proceedings.mlr.press/v108/han20a.html).

Result: 241b32b, Eval AUC 0.7568 (tie), kept. Removing Month leaves ranking unchanged with fewer prepared categories.

## Experiment 39 — remove standalone DayOfWeek

Type: ablation/simplification. Hypothesis: DateCat also determines weekday, and CarrierWeekday retains carrier-specific weekly effects. Remove DayOfWeek from cat_cols while retaining its use in the interaction. Source: experiment 38 and the deterministic date relationships in this one-year dataset.

Result: cce1d75, Eval AUC 0.7568 (tie), kept. Evaluation time fell to about 39s from about 43s.

## Experiment 40 — remove standalone DayofMonth

Type: ablation/simplification. Hypothesis: DateCat now captures individual calendar dates and may subsume the standalone DayofMonth category. Earlier removal hurt before DateCat existed; this explicitly retests on the new representation. Remove DayofMonth from cat_cols only. Source: experiments 19 and 27–39.

Result: 62092a2, Eval AUC 0.7564 (-0.0004), kept as a near-equal simplification. Evaluation time fell from about 39s to 36s. Highest measured AUC remains 0.7568 at cce1d75.

## Synthesis after 40 experiments

The first 30 experiments produced a peak of 0.7568 from categorical date, two carrier-calendar interactions, and a partition threshold of 256. Experiments 31–40 showed that carrier-hour interactions and changing the tree count hurt. DateCat made MonthWeekday and the standalone Month/DayOfWeek categories redundant at unchanged AUC; removing standalone DayofMonth cost only 0.0004 while reducing evaluation cost. CarrierWeekday and CarrierMonth each still contributed about 0.0012–0.0013 when ablated. The current branch is a leaner 0.7564 model at 62092a2, with the highest observed 0.7568 at cce1d75. Next inspect learned feature usage and pursue features tied to airport/day effects without sparse high-cardinality crosses.

## Research after 40 experiments

Inspection of the saved model at 62092a2 found total split gain concentrated in DateCat, CarrierMonth, CRSDepTime, Origin, and Dest; CarrierWeekday contributed less and Distance very little. Standalone UniqueCarrier did not appear in the gain report. [XGBoost's API documentation](https://xgboost.readthedocs.io/en/stable/python/python_api.html) confirms that `get_score` omits features unused in any split. [Scikit-learn's inspection guide](https://scikit-learn.org/stable/modules/permutation_importance.html) warns that importance measures can be misleading with correlated predictors, so removal must still be checked by retraining and harness evaluation.

## Experiment 41 — remove standalone carrier

Type: ablation/simplification. Hypothesis: standalone UniqueCarrier can be removed because the current model makes no split on it, while CarrierMonth and CarrierWeekday retain its useful interactions. Remove it only from cat_cols, not from the derived pair keys. Source: saved-model inspection and XGBoost API documentation above.

Result: 8e532a7, Eval AUC 0.7564 (tie), kept. Evaluation time fell to 31.3s; the standalone carrier column was indeed redundant for this model.

## Experiment 42 — remove Distance

Type: ablation/simplification. Hypothesis: Distance contributes only a tiny fraction of total split gain in the inspected model, so omitting it may preserve ranking with fewer inputs. Remove Distance from num_cols while retaining CRSDepTime. Source: saved-model inspection and the caution in [scikit-learn's inspection guide](https://scikit-learn.org/stable/modules/permutation_importance.html) that final judgment requires measured performance.

Result: e230b92, Eval AUC 0.7555 (-0.0009), discarded. Distance still adds a small generalizable signal despite its low total gain.

## Research before geographic proxy

[Flight-delay research](https://www.mdpi.com/2079-9292/13/24/4910) uses airport latitude and longitude for spatial context. The [UC Berkeley project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) also treats airport location as a useful feature family. This dataset supplies route distances but no coordinates, so distance from an airport to several reference hubs is a train-fitted proxy for broad geography. This is an inference and may be too coarse. Training-only inspection found direct route-distance links from 88.5% of observed origins to ATL, 85.7% to ORD, and 77.7% to LAX; missing links will map to NaN.

## Experiment 43 — origin distance to reference hubs

Type: exploration. Hypothesis: three numeric origin-to-hub distances let shallow trees share regional behavior across airports and interact with DateCat for day-specific disruptions. Fit each lookup from train's route distances only and map rows by Origin during prepare. Sources: spatial flight-delay studies above.

Result: 9e85bec, Eval AUC 0.7564 (tie), discarded under the simplicity criterion. Nine added code lines and about five extra evaluation seconds yield no gain.

## Research before carrier-airport interaction

[Research on airline delay propagation and schedule buffers](https://doi.org/10.1016/j.tre.2021.102333) includes hub-origin indicators, and [research on airport delays](https://www.sciencedirect.com/science/article/pii/S0191261509001313) discusses the interaction between a carrier's presence at an airport and congestion. This motivates a carrier–origin feature. The training set has 1,551 such levels, with 403 appearing fewer than 20 times, so high-cardinality overfitting is a concrete risk. The experiment tests whether the well-supported levels outweigh that risk.

## Experiment 44 — carrier × origin category

Type: exploration. Hypothesis: carrier-specific origin-airport operations and hub practices contain signal beyond separate Origin and CarrierMonth/Weekday columns. Add CarrierOrigin category fitted from train, with no row counts or target statistics as features. Sources: airline-airport studies above.

Result: c1fbfee, Eval AUC 0.7475 (-0.0089), discarded. Sparse carrier-origin categories overfit, like the route category. Three consecutive discards without improvement prompt another research pause.

## Plateau research before holiday feature

The [U.S. Office of Personnel Management holiday rules](https://www.opm.gov/policy-data-oversight/pay-leave/pay-administration/fact-sheets/holidays-work-schedules-and-pay/) identify major federal holidays, and a [flight-delay study](https://doi.org/10.1145/3786484.3786539) finds holiday/weekend indicators informative during peak-demand periods. DateCat already identifies each calendar day, but distance to a holiday can share information across nearby days with different labels. The dates are fixed exogenous calendar facts; the feature uses no data-file statistics or target values.

## Experiment 45 — distance to major holiday

Type: exploration. Hypothesis: a numeric distance to New Year's Day, Memorial Day, Independence Day, Labor Day, Thanksgiving, or Christmas can group adjacent high-travel dates and improve ranking beyond DateCat alone. Precompute the 2005 distance lookup once, then map each row's date key. Sources: OPM holiday rules and flight-delay study above.

Result: f05b25a, Eval AUC 0.7571 (+0.0007 versus the current lean branch, +0.0003 versus the previous best), kept. The holiday feature is compact and uses known calendar facts; its small gain needs cautious interpretation.

## Experiment 46 — restore DayofMonth with holiday feature

Type: follow-up to the simplification experiments. Hypothesis: standalone DayofMonth lost 0.0004 AUC when removed, and may now complement the holiday-proximity feature. Restore it to cat_cols and test whether the gain warrants the extra category and evaluation cost. Source: experiment 40 and the holiday result in experiment 45.

Result: 1731628, Eval AUC 0.7568 (-0.0003), discarded. DayofMonth remains redundant enough to omit.

## Experiment 47 — minimum split gain

Type: exploration. Hypothesis: DateCat supplies many possible partitions, so requiring a minimum loss reduction (`gamma=1`) can prune noisy weak splits while preserving strong calendar and airport effects. Retain the lean holiday model. Source: [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html).

Result: 48da428, Eval AUC 0.7558 (-0.0013), discarded. Pruning weak splits at this threshold removes useful signal.

## Research before weekly feature

A [flight-delay feature engineering study](https://www.mdpi.com/2079-9292/13/24/4910) uses ISO week of year to capture seasonal and peak-travel trends. The [scikit-learn time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) discusses extracting multiple calendar scales. DateCat already marks each date, but a 53-level week category may pool adjacent dates with shared conditions while leaving daily distinctions available.

## Experiment 48 — ISO calendar week category

Type: exploration. Hypothesis: grouping adjacent 2005 dates by ISO week provides a medium-scale temporal feature that DateCat alone cannot express in one split. Fit the lookup from 2005 calendar rules and train's date levels; map rows inside prepare. Sources: studies above.

Result: 608fb66, Eval AUC 0.7565 (-0.0006), discarded. The week category adds cost without useful signal. Three consecutive discards since the holiday feature prompt another research pause.

## Plateau research before tree-method comparison

The [XGBoost tree-method guide](https://xgboost.readthedocs.io/en/release_1.4.0/treemethod.html) explains that `approx` rebuilds a Hessian-weighted quantile sketch for each tree, whereas `hist` uses one global sketch. It notes `approx` can sometimes improve accuracy with non-constant Hessian objectives, at higher computation cost. Binary logistic training has changing Hessians, so the alternate split candidates are a plausible distinct direction. The [current XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) confirms both `hist` and `approx` support the relevant setup.

## Experiment 49 — approximate tree method

Type: exploration. Hypothesis: Hessian-weighted per-tree sketching may choose better schedule and distance thresholds than the default histogram method, improving AUC. Set `tree_method="approx"` only. Sources: XGBoost tree-method and parameter guides above.

Result: 3adab4c, Eval AUC 0.7565 (-0.0006), discarded. Training time rose from about 1s to 6.7s without AUC gain.

## Experiment 50 — depth 5 with date and holiday features

Type: follow-up to current feature set. Hypothesis: an extra tree level may now capture interactions among DateCat, holiday distance, carrier-calendar pairs, and airports. Earlier depth-5 results predated DateCat and holiday proximity. Change only max_depth from 4 to 5. Source: [XGBoost tuning guide](https://xgboost.readthedocs.io/en/release_0.72/tutorials/param_tuning.html).

Result: b57eeb6, Eval AUC 0.7534 (-0.0037), discarded. The current feature set still favors depth 4.

## Synthesis after 50 experiments

The best Eval AUC is 0.7571 at f05b25a (+0.0368 over baseline). Categorical date is the largest single gain. CarrierMonth and CarrierWeekday remain useful explicit interactions; standalone carrier, month, and weekday can be removed without loss. Holiday proximity adds a smaller gain. Sparse route and carrier-origin categories overfit; geographic proxy distances tied while adding complexity. Weekly categories, stronger split pruning, approximate tree construction, and extra depth did not help. The current lean model trains in about 1s and evaluates in about 34s. Next test a train-fitted route schedule statistic and a compact carrier-holiday interaction, then settle on the best measured commit before time expires.

## Experiment 51 — departure time relative to route schedule

Type: exploration. Hypothesis: a flight scheduled unusually early or late for its origin-destination route has different delay risk even after the global departure-time feature. Fit each route's median scheduled departure minute from train.csv only; map that schedule into prepare and subtract it from each row's scheduled departure minute. Unknown routes receive a missing value. This follows the train-fitted route statistic example in program.md and the [UC Berkeley flight delay feature engineering project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches), which identifies departure-time blocks as relevant.

Result: 8eeca4e, Eval AUC 0.7567 (-0.0004), discarded. Route-relative time did not improve ranking and increased evaluation time.

## Experiment 52 — carrier by holiday proximity

Type: follow-up to the holiday-distance gain. Hypothesis: carriers may react differently to peak holiday travel. A compact categorical interaction of carrier with whether a flight is within three days of a listed holiday can expose this without a sparse route-like category. Fit its category levels from train only; all six holiday dates remain calendar facts rather than target-derived features. Source: the holiday-distance result in Experiment 46 and the calendar interactions already in the retained model.

Result: 30e01f7, Eval AUC 0.7569 (-0.0002), discarded. The interaction does not add useful generalizable signal.

## Plateau research after Experiment 52

The recent route, carrier-holiday, calendar-week, and tree-structure variants all scored below the retained 0.7571 model. The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/release_0.72/tutorials/param_tuning.html) describes subsampling, column sampling, and learning-rate/tree-count tradeoffs as standard ways to control generalization. Earlier subsampling and extra depth hurt; a slightly smaller learning rate with proportionally more trees is the next limited comparison. This is a parameter follow-up rather than another high-cardinality feature search.

## Experiment 53 — modestly slower boosting

Type: parameter follow-up. Hypothesis: 0.08 learning rate with 375 trees gives similar cumulative step size to 0.1 with 300 trees but less sensitivity to individual trees. Experiment 10's 0.05/500 and Experiment 36's 0.1/450 were on different or earlier feature configurations; this is a narrow test on the holiday model. Source: XGBoost tuning guide cited above.

Result: 623eb9d, Eval AUC 0.7571 (tie), discarded because it requires 75 more trees without improving AUC.

## Experiment 54 — signed distance to nearest holiday

Type: holiday-feature follow-up. Hypothesis: pre-holiday congestion and post-holiday recovery have different delay patterns, so the direction of the nearest major holiday matters beyond absolute distance. Add a signed difference in days to the nearest of the same six fixed 2005 holidays, retaining the absolute feature. This is a calendar-only transformation and remains row-wise at evaluation. Source: the modest holiday-distance gain in Experiment 46.

Result: c1134bc, Eval AUC 0.7571 (tie), discarded because the additional feature increased evaluation time.

## Experiment 55 — scheduled airport-hour activity

Type: exploration. Hypothesis: the proportion of an origin airport's training flights scheduled in a given hour is a proxy for local schedule congestion, and may explain delays beyond clock time and airport identity. Fit origin-hour flight counts and origin totals from train.csv only, then map their ratio at evaluation. This is unsupervised and uses no target statistic. Source: the [UC Berkeley flight-delay feature engineering project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) identifies scheduled departure time as important; this test extends it to airport-specific schedule concentration.

Result: 1201543, Eval AUC 0.7561 (-0.0010), discarded. Schedule concentration is noisy or redundant once airport and clock time are in the model.

## Plateau research after Experiment 55

The last three tests produced two ties with greater complexity and one lower score. The [XGBoost categorical parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `max_cat_threshold` as a bound on partition split search. Earlier DateCat tests found 256 better than 128 and 512; an intermediate value may provide a small regularization improvement with the current lean holiday feature set. This is a narrow final tuning direction, with the simpler 0.7571 branch retained unless a run beats it.

## Experiment 56 — intermediate categorical threshold

Type: follow-up. Hypothesis: threshold 192 may retain most useful day and airport category partitions while reducing the overfitting seen at 512. Set only max_cat_threshold from 256 to 192. Source: XGBoost categorical parameter documentation above and Experiments 29–31.

Result: d93e338, Eval AUC 0.7557 (-0.0014), discarded. The 256 threshold remains preferable.

## Experiment 57 — slightly higher minimum child weight

Type: final parameter check. Hypothesis: the current high-cardinality date feature may have a few low-support leaves, so min_child_weight=2 could smooth them while preserving the strong interactions. The earlier min_child_weight=5 test was on a different feature set and may have pruned too strongly. Change only this parameter. Source: [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html).

Result: 40f546a, Eval AUC 0.7572 (+0.0001), kept. Moderate split support gives a small measured gain at similar runtime.

## Experiment 58 — minimum child weight 3

Type: follow-up. Hypothesis: the gain at weight 2 may continue with slightly firmer leaf support. Raise only min_child_weight from 2 to 3. Source: XGBoost parameter guide above.

Result: 75301c8, Eval AUC 0.7567 (-0.0005), discarded. Weight 2 is the better setting.

## Final summary

Completed 58 experiments within the two-hour research window. Best measured Eval AUC: 0.7572 at commit 40f546a, versus untouched baseline 0.7203 (+0.0369). The final model uses 300 depth-4 trees at learning rate 0.1, categorical origin, destination, and day, carrier-weekday and carrier-month categories, distance to major holidays, max_cat_threshold 256, and min_child_weight 2. Scheduled departure time and route distance remain numeric inputs. Training takes about 1.2s and evaluation about 34.6s.

The strongest gain came from categorical day-of-year style encoding; compact carrier-calendar interactions and holiday proximity added smaller gains. Higher tree counts, deep trees, sparse route/category crosses, approximate tree construction, and several extra schedule/geography features reduced score or tied with more complexity. A future run could validate the tiny +0.0001 min_child_weight gain across other evaluation splits and explore external weather data only if the task allows it. The selected commit is the highest measured score in this run.
