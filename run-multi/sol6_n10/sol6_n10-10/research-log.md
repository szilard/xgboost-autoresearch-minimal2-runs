# Research log — sep30

## Baseline — 92e43e6

Untouched starter: 30 trees, depth 6, learning rate 0.1, native categoricals. Eval AUC 0.7203. Training took 1.1s and row-wise evaluation 30.5s.

## Experiment 1 — more boosting rounds (exploration)

Hypothesis: 30 trees at learning rate 0.1 leave useful structure unfitted. Increase to 300 trees with all other settings unchanged. This follows the [XGBoost parameter tuning guide](https://xgboost.readthedocs.io/en/release_1.3.0/tutorials/param_tuning.html), which discusses learning rate and boosting rounds together. Training data have 200,000 balanced rows with no missing values.

Result: 2825ddc, Eval AUC 0.7342 (+0.0139). Keep. Strong evidence the starter was underfit.

## Experiment 2 — 800 trees (follow-up)

Hypothesis: the gain from 30 to 300 trees may continue with more boosting rounds, though overfitting may eventually reverse it. Test 800 trees at unchanged depth and learning rate. Training time at 300 was 2.5s, leaving ample margin under the 60s limit.

Result: e901956, Eval AUC 0.7273 (-0.0069 vs 300). Discard. This configuration overfits well before 800 trees.

## Experiment 3 — depth 4 (exploration)

Hypothesis: depth-6 trees fit noise by 300 rounds. Try depth 4 to reduce interaction complexity while holding rounds at 300. The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/release_1.3.0/tutorials/param_tuning.html) identifies `max_depth` as a primary control on overfitting.

Result: d3bbde9, Eval AUC 0.7343 (+0.0001); keep as a simplification win. Artifact shrank from 7.5 MB to 2.1 MB and training fell from 2.5s to 1.9s.

## Experiment 4 — 600 depth-4 trees (follow-up)

Hypothesis: the shallower trees should overfit more slowly than depth 6, and 300 rounds may underfit them. Increase to 600 rounds at depth 4; contrast with the failed 800-round depth-6 result.

Result: 438c332, Eval AUC 0.7359 (+0.0016). Keep; shallow trees still benefited from additional boosting.

## Experiment 5 — 1,000 depth-4 trees (follow-up)

Hypothesis: the depth-4 learning curve may still be rising at 600 rounds. Test 1,000 rounds to bracket the optimum at the current learning rate.

Result: 5542fb0, Eval AUC 0.7332 (-0.0027). Discard; current optimum is below 1,000 rounds.

## Experiment 6 — ordered calendar features (exploration)

Hypothesis: months and days have ordered seasonal structure that may be easier for depth-4 trees to model numerically while retaining categorical splits for noncontiguous effects. Add numeric versions of Month, DayofMonth and DayOfWeek. A [flight-delay model write-up](https://github.com/Prashant-4527/flight-delay-prediction) uses schedule and calendar features, while the [XGBoost categorical tutorial](https://xgboost.readthedocs.io/en/release_3.2.0/tutorials/categorical.html) explains how category splits differ from numeric thresholds. Parsing is row-local and stable under the harness's one-row calls.

Initial attempt 96dad92 crashed before evaluation: the three date columns have `c-` prefixed values (for example `c-11`). Correct the parser by stripping the fixed prefix and rerun the same hypothesis.

Corrected run e4c852f: Eval AUC 0.7359 (unchanged) and evaluation rose from ~30s to 37s. Discard the extra feature code; XGBoost's existing categorical splits already captured these calendar effects well enough.

## Experiment 7 — carrier × origin category (exploration)

Hypothesis: an airline's delay risk may differ by its origin airport; explicit interactions can expose that effect to shallow trees. The [flight-delay route write-up](https://github.com/AhmedFaizanDev/flight-delay-risk-prediction) uses route and airline combinations, and [XGBoost's categorical guide](https://xgboost.readthedocs.io/en/release_3.2.0/tutorials/categorical.html) supports native category partitions. Carrier-origin has 1,551 combinations in train, with 99.5% of rows in combinations observed at least ten times. Fit levels on train and apply the same levels to each row at evaluation.

Result: 9f00606, Eval AUC 0.7227 (-0.0132). Discard. A high-cardinality interaction appears to overfit despite most combinations appearing many times. Evaluation rose to 38s and emitted warnings for unseen carrier-origin levels.

## Experiment 8 — 80% row subsampling (exploration)

Hypothesis: bagging 80% of training rows per tree will reduce variance at 600 rounds, where more rounds alone overfit. [XGBoost's tuning guide](https://xgboost.readthedocs.io/en/release_1.3.0/tutorials/param_tuning.html) recommends `subsample` to control overfitting; the [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines it as a new sample each boosting iteration. Test `subsample=0.8` with all other settings at the current best.

Result: 077de99, Eval AUC 0.7211 (-0.0148). Discard. Row subsampling is a poor fit for this configuration; do not combine it into subsequent changes without a specific rationale.

### Research pause after discarded directions

The [original flight-delay assignment](https://mlcourse.ai/book/topic10/assignment10_flight_delays_kaggle.html) mentions a route feature. The [XGBoost categorical parameter reference](https://xgboost.readthedocs.io/en/release_3.3.0/parameter.html) identifies `max_cat_to_onehot` and `max_cat_threshold` as ways to change categorical splitting. Rather than add another high-cardinality interaction immediately, test the treatment of existing lower-cardinality categories. More rounds helped until a clear overfit point; ordered date copies, a carrier-origin interaction and row subsampling did not help.

## Experiment 9 — one-hot splits for small categories (exploration)

Hypothesis: forcing one-category-at-a-time splits for calendar fields and carrier may avoid noisy partitions and improve generalization, while retaining partition splits for origin and destination. Set `max_cat_to_onehot=32` as described in the [XGBoost categorical docs](https://xgboost.readthedocs.io/en/release_3.2.0/tutorials/categorical.html). The category cardinalities are 7–31 for calendar/carrier and 283 for airports.

Result: d76b17c, Eval AUC 0.7229 (-0.0130). Discard. Partition splits on small categories are useful here; one-hot splits remove useful grouping ability.

## Experiment 10 — minimum child weight 5 (exploration)

Hypothesis: depth-4 trees can still isolate noisy small groups. Raising `min_child_weight` from the default 1 to 5 should discourage fragile splits while preserving the effective native categorical partitions. [XGBoost's tuning guide](https://xgboost.readthedocs.io/en/release_1.3.0/tutorials/param_tuning.html) names it as a direct complexity control. All other settings remain at the best commit.

Result: 9821e4e, Eval AUC 0.7352 (-0.0007). Discard; no simplicity gain over the default.

### Synthesis after 10 experiments

The strongest change was adding boosting rounds: 30 to 300 raised AUC from 0.7203 to 0.7342. Shallow depth-4 trees allowed 600 rounds and the best AUC so far, 0.7359 at 438c332. Larger ensembles overfit: depth-6/800 and depth-4/1,000 both fell. Numeric calendar copies were neutral and slower. A high-cardinality carrier-origin feature, row subsampling, and forcing one-hot category splits all lost about 0.013–0.015 AUC. Raising minimum child weight to 5 was marginally worse. The working theory is that native categorical partitions and moderate depth/boosting capture most available signal; changes that disrupt categorical grouping or add fragile interactions are risky. Next directions: route features suggested by the original assignment, schedule-time transformations, and targeted regularization or learning-rate changes.

## Experiment 11 — explicit flight route (exploration)

Hypothesis: an origin-destination route can express directional route effects more directly than two independent airport features. The [original flight-delay assignment](https://mlcourse.ai/book/topic10/assignment10_flight_delays_kaggle.html) uses a `Flight` feature built from Origin and Dest for its second benchmark. Test a native categorical route alongside the existing airport features. There are 4,290 routes in train; unseen routes will map to missing using levels fitted on train.

Result: 4ed95b7, Eval AUC 0.7053 (-0.0306). Discard. Native partitioning on a 4,290-level route is much too flexible for this training set, even though a route feature worked in a different encoding in the original assignment.

## Experiment 12 — category threshold 16 (exploration)

Hypothesis: the 283-level airport features may also permit overly broad category partitions. Restricting `max_cat_threshold` to 16 should make those splits more conservative without changing the feature set. [XGBoost's current tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) lists this parameter under complexity control and the [parameter reference](https://xgboost.readthedocs.io/en/release_3.3.0/parameter.html) defines the number of categories considered per split.

Result: e3007c7, Eval AUC 0.7379 (+0.0020). Keep. The model also shrank from 4.2 MB to 3.3 MB. This supports conservative categorical partitioning as a useful regularizer.

## Experiment 13 — category threshold 8 (follow-up)

Hypothesis: if 16 category candidates per split regularizes airports profitably, 8 may further reduce noisy airport splits. Test one tighter value, with all other settings unchanged.

Result: 62c8a60, Eval AUC 0.7400 (+0.0021). Keep. Continued improvement and a 2.9 MB artifact suggest high-cardinality category split complexity was a limiting factor.

## Experiment 14 — category threshold 4 (follow-up)

Hypothesis: the trend from the default threshold to 16 and 8 may continue toward a more constrained partition. Test `max_cat_threshold=4` to locate the useful range.

Result: 0047d44, Eval AUC 0.7352 (-0.0048). Discard. The useful threshold lies above 4; 8 remains best.

## Experiment 15 — category threshold 12 (follow-up)

Hypothesis: the optimum may sit between 8 (0.7400) and 16 (0.7379). Test 12 as one interior value; after this, move to a different mechanism rather than over-tuning a single parameter.

Result: 50f75ee, Eval AUC 0.7386 (-0.0014). Discard. The tested optimum remains 8. Move on from this parameter.

## Experiment 16 — half learning rate, double rounds (exploration)

Hypothesis: smaller boosting steps can generalize better while keeping roughly the same aggregate learning budget. Change learning rate 0.1→0.05 and rounds 600→1,200, leaving depth 4 and category threshold 8. [XGBoost's tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) specifically says to increase rounds when reducing `eta`.

Result: 666c33b, Eval AUC 0.7393 (-0.0007) with larger/slower model. Discard; the current 0.1 rate is preferable.

## Experiment 17 — 800 trees with conservative category splits (follow-up)

Hypothesis: threshold 8 limits overfitting enough to shift the optimal tree count above 600. Test 800 trees at learning rate 0.1; this differs from the earlier 1,000-tree trial because categorical partitions are now much more constrained.

Result: ccfb6b4, Eval AUC 0.7401 (+0.0001). Keep under the strict higher-AUC rule; the gain is very small and model size increased from 2.9 to 3.8 MB, so it remains a candidate for later simplification.

## Experiment 18 — 1,000 trees with category threshold 8 (follow-up)

Hypothesis: a few more rounds may lift the tiny 800-tree gain, but continued overfitting should reveal the peak. Test 1,000 rounds at the regularized category threshold.

Result: 0ceff5c, Eval AUC 0.7405 (+0.0004). Keep. Category threshold 8 does allow more rounds than the default threshold did. The gain is modest; test a wider step to find the upper limit.

## Experiment 19 — 1,400 trees with threshold 8 (follow-up)

Hypothesis: conservative categorical splits may still benefit from more rounds. A 400-round step should make an overfit reversal visible if the curve has peaked, without spending time on cosmetic increments.

Result: f7bcb99, Eval AUC 0.7398 (-0.0007). Discard. Best tested tree count at threshold 8 is 1,000.

## Experiment 20 — depth 3 with category threshold 8 (exploration)

Hypothesis: shallower trees may further control overfitting after category regularization, possibly permitting the same AUC with less model complexity. Test depth 3 at the current 1,000 rounds, holding all else fixed. The prior depth-6 to depth-4 simplification preserved AUC and enabled more rounds.

Result: 5bb6705, Eval AUC 0.7373 (-0.0032). Discard. Depth 3 loses interactions needed by this dataset at 1,000 rounds.

### Synthesis after 20 experiments

The biggest finding in this block is that limiting categorical partitions works. Threshold 16 improved AUC to 0.7379 and threshold 8 to 0.7400, while threshold 4 fell to 0.7352 and threshold 12 scored 0.7386. With threshold 8, 1,000 rounds reached the current best 0.7405 (0ceff5c), though the last 400 rounds gave only 0.0005 over 600. 1,400 rounds regressed. The route category from the original assignment was a poor fit with native XGBoost categorical partitioning, at 0.7053; its encoding differed from the assignment's one-hot method. Half learning rate with doubled rounds and depth 3 both underperformed. The working theory is that a moderate categorical split budget is crucial, depth 4 supports useful airport/time interactions, and the current tree count is near the useful limit. Next: inspect new regularization and feature ideas, then test a different way to capture schedule structure.

## Experiment 21 — carrier-origin with threshold 8 (follow-up)

Hypothesis: the earlier carrier-origin category collapsed AUC partly because default categorical partitioning was too flexible. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says `max_cat_threshold` limits categories per partition split to prevent overfitting. Retest the same interaction under the now-successful threshold 8; a better result would show that the interaction needs strong regularization, while another loss would rule out this feature family.

Result: fcc5e28, Eval AUC 0.7302 (-0.0103). Better than the same interaction under the default category threshold (0.7227), but still clearly worse than the current model. Discard; do not pursue native high-cardinality interaction categories further.

## Experiment 22 — minute within departure hour (exploration)

Hypothesis: airlines' choice of scheduled minute may encode operational patterns. A [flight-delay solution](https://gist.github.com/akatasonov/fc5f031791a3ad0344bb78272008de4f) extracts both hour and minute from HHMM departure time. The existing raw HHMM feature is ordinal and cannot represent a minute pattern repeated every hour with one split. Add numeric `DepMinute = CRSDepTime % 100` only. All train times have valid minute values and 72% are scheduled at multiples of five.

Result: 720ccf2, Eval AUC 0.7409 (+0.0004). Keep. The one-line time feature adds a small gain with ~2s more evaluation time.

## Experiment 23 — categorical departure minute (follow-up)

Hypothesis: scheduled minutes have recurring non-ordinal patterns (for example :00, :15, :30, :45); treating minute as a category may group them more effectively than numeric thresholds. Recast only `DepMinute` as categorical with fixed 0–59 levels and retain the threshold-8 regularization.

Result: 65ebdd2, Eval AUC 0.7398 (-0.0011). Discard. Numeric minute generalizes better than native categorical minute, and evaluates faster.

## Experiment 24 — five-minute scheduling flag (ablation/simplification)

Hypothesis: much of the numeric minute gain may come from whether a departure is scheduled on a five-minute boundary. The [flight-delay solution](https://gist.github.com/akatasonov/fc5f031791a3ad0344bb78272008de4f) explicitly uses a modulo-five flag. Replace the 60-value minute feature with a single binary `OnFiveMinute` flag to test a simpler explanation of the gain.

Result: b2fdcf4, Eval AUC 0.7401 (-0.0008). Discard. Numeric minute contains useful information beyond the five-minute boundary flag.

## Experiment 25 — stronger L2 regularization (exploration)

Hypothesis: 1,000 rounds may leave small noisy leaf effects even after limiting categorical splits. Increase `reg_lambda` from its default 1 to 5, keeping the best feature set and all other parameters. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes L2 leaf-weight regularization as making a model more conservative.

Result: 9baa86e, Eval AUC 0.7418 (+0.0009). Keep. L2 regularization complements the small categorical threshold.

## Experiment 26 — L2 regularization 10 (follow-up)

Hypothesis: the gain from L2=5 may continue if leaf weights remain noisy. Test `reg_lambda=10` with all else unchanged to bracket a useful regularization range.

Result: 88ae22f, Eval AUC 0.7434 (+0.0016). Keep. Leaf-weight shrinkage is strongly beneficial at the current tree count.

## Experiment 27 — L2 regularization 20 (follow-up)

Hypothesis: improvement from L2=1 to 5 to 10 has not yet flattened. Test 20 to find whether the smoother leaf weights continue to generalize or begin to underfit.

Result: 4b97422, Eval AUC 0.7426 (-0.0008). Discard. Best tested L2 strength is 10.

## Experiment 28 — 1,400 rounds under L2=10 (follow-up)

Hypothesis: L2=10 suppresses noisy late-round leaf effects, so the 1,400-round configuration that previously overfit under default L2 may now improve. Hold all settings except boosting rounds fixed.

Result: c700b43, Eval AUC 0.7425 (-0.0009). Discard. L2 helps at 1,000 rounds but does not support the longer ensemble.

## Experiment 29 — require split gain (exploration)

Hypothesis: after limiting category partitions and shrinking leaf weights, pruning low-gain splits may remove remaining noise. Set `gamma=1`, which the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines as the minimum loss reduction for a split. This directly regularizes tree structure rather than leaf values.

Result: 0c6c0b7, Eval AUC 0.7350 (-0.0084). Discard. The 2.1 MB artifact versus 5.2 MB baseline for this experiment shows `gamma=1` pruned too aggressively; a much smaller threshold may be worth one test.

## Experiment 30 — mild split penalty (follow-up)

Hypothesis: `gamma=0.1` may prune only the weakest late-round splits without the severe underfitting seen at 1. Test an order-of-magnitude lower split-gain threshold.

Result: 2df2c90, Eval AUC 0.7415 (-0.0019). Discard. Split penalties do not complement the current model.

### Synthesis after 30 experiments

Reintroducing carrier-origin under threshold 8 improved it relative to the original attempt but remained far below best, so native high-cardinality interactions are a poor direction. Extracting numeric departure minute raised AUC to 0.7409; categorical minute and a five-minute flag were worse. L2 leaf regularization was the major gain in this block: strength 5 scored 0.7418 and 10 scored the current best 0.7434 at 88ae22f. Strength 20 regressed. L2 did not make 1,400 rounds worthwhile, and both mild and strong split-gain penalties worsened results. Current theory: the model needs fairly rich splits but conservative category grouping and leaf values. Next search for useful numeric binning or safe train-fitted airport statistics rather than more high-cardinality identifiers.

## Experiment 31 — calendar date category (exploration)

Hypothesis: date-specific events such as nationwide weather may drive delays. A [flight-delay study](https://pmc.ncbi.nlm.nih.gov/articles/PMC12685205/) includes day-of-year among its time features. The best model's total gain is high for both Month and DayofMonth, and all 365 calendar dates have 330–890 train rows. Add a month-day category with levels fitted on train; threshold 8 and L2=10 should contain overfitting. No target statistics are used.

Result: c395647, Eval AUC 0.7548 (+0.0114). Keep. This is a large gain without label-derived features; the 365 observed dates are shared between train and the row-wise evaluation. Artifact size rose to 9.5 MB and evaluation to 37.6s, both comfortably within limits.

## Experiment 32 — category threshold 16 with date (follow-up)

Hypothesis: adding a 365-level date category may shift the useful category-partition budget. Raise `max_cat_threshold` from 8 to 16 to let a split group more dates, while retaining L2=10. Previously threshold 16 lost on the model without CalendarDate; this experiment specifically tests the interaction with the new feature.

Result: c3e2538, Eval AUC 0.7543 (-0.0005). Discard; threshold 8 remains better with the date feature.

## Experiment 33 — ordered date alongside categorical date (follow-up)

Hypothesis: the categorical date isolates days with unusual conditions, while a numeric day order can share information across adjacent dates and model a smoothly varying seasonal effect. Add a chronological month-day ordinal (31 slots per month, preserving order) alongside CalendarDate. The [flight-delay study](https://pmc.ncbi.nlm.nih.gov/articles/PMC12685205/) uses day-of-year as a temporal feature. This is computed row by row from schedule fields only.

Result: 82e389e, Eval AUC 0.7544 (-0.0004) and evaluation rose to 41.8s. Discard; ordered date adds little beside the categorical date.

## Experiment 34 — train-fitted daily delay rate (exploration)

Hypothesis: a numeric date-level risk estimate may expose daily disruption directly and let trees spend splits on interactions with airline and airport. Daily train rates range roughly 0.21–0.76, with at least 330 rows per date. Fit one lookup on `train.csv` only and map it inside `prepare`, so it is identical for a row processed alone or in a batch. The [scikit-learn target-encoding guide](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html) warns that full-data target encodings can overfit; this test is limited to the 365 well-populated dates, and only the harness Eval AUC will decide whether to retain it. No row count is used as a feature.

Result: a121b70, Eval AUC 0.7547 (-0.0001) with more code and slower evaluation. Discard; the categorical date already captures the useful daily variation without target-derived features.

## Experiment 35 — month × weekday category (exploration)

Hypothesis: recurrent weekday effects vary by season, and combining Month and DayOfWeek may make that interaction easy for a depth-4 tree while pooling four or five dates per group. Add a low-cardinality 84-level category from these two existing schedule fields. This complements the single-date category with a smoother recurring pattern; no group statistics or labels are used.

Result: eebf107, Eval AUC 0.7532 (-0.0016) and slower evaluation. Discard. The single-date category is a more useful calendar representation.

### Research pause on the calendar plateau

The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes L2 leaf penalties and category-threshold limits as complementary controls. A [research paper on categorical tree features](https://pmc.ncbi.nlm.nih.gov/articles/PMC9140774/) emphasizes the variance risk of high-cardinality splits. The date category has strong signal; extra encodings have not helped. Retune structural regularization around that single feature rather than adding more overlapping calendar categories.

## Experiment 36 — L2=20 with date feature (follow-up)

Hypothesis: the 365-level date category increases model flexibility, so it may benefit from more leaf shrinkage than the pre-date optimum L2=10. Test 20 while holding all else fixed; the earlier L2=20 loss was measured before CalendarDate existed.

Result: 48a07f0, Eval AUC 0.7543 (-0.0005). Discard. Stronger L2 does not improve the date model.

## Experiment 37 — L2=5 with date feature (follow-up)

Hypothesis: the added date signal may make the earlier L2=10 penalty slightly too strong; the loss at 20 suggests trying the lower side. Test L2=5 with CalendarDate and all other settings fixed.

Result: 8ee0bda, Eval AUC 0.7537 (-0.0011). Discard. L2=10 remains the best tested strength for the date model.

## Experiment 38 — depth 5 with calendar date (exploration)

Hypothesis: the date feature takes a split to isolate a daily disruption, leaving only three further levels for airport, carrier and time interactions at depth 4. Test depth 5 with the same 1,000 rounds, L2=10 and category threshold 8. The earlier depth comparison preceded the date feature.

Result: af4111d, Eval AUC 0.7568 (+0.0020). Keep. More interaction depth helps once CalendarDate is included; model size rose to 16.6 MB but time remains safe.

## Experiment 39 — depth 6 with calendar date (follow-up)

Hypothesis: another split level may capture airport-specific daily disruption or carrier effects. Test depth 6 at the same 1,000 rounds. If it loses, depth 5 brackets the useful complexity; if it gains, follow up by checking a smaller tree count for efficiency.

Result: c94450b, Eval AUC 0.7562 (-0.0006) with a 27.3 MB artifact. Discard. Depth 5 is the better complexity level at 1,000 rounds.

## Experiment 40 — 700 depth-5 trees (ablation/simplification)

Hypothesis: deeper trees learn date interactions faster, so 1,000 rounds may be beyond their useful peak. Test 700 rounds at depth 5. Equal or better AUC would also reduce model size and training cost.

Result: 40aee18, Eval AUC 0.7552 (-0.0016). Discard; 1,000 rounds are more effective for depth 5.

### Synthesis after 40 experiments

The date interaction was decisive: adding month-day as a category raised AUC from 0.7434 to 0.7548. The signal is plausible because every 2005 date has hundreds of training rows and daily delay rates vary widely. Extra calendar encodings (ordinal date, month-weekday) and a train-fitted daily target-rate lookup did not help. Threshold 16 and L2 values 5 and 20 all scored below the existing threshold 8/L2=10 settings with date. Depth 5 raised AUC to the current best 0.7568 (af4111d), while depth 6 lost and 700 depth-5 rounds underfit. The working theory is that date-specific conditions and their interactions with airport, carrier and time are the main remaining signal; optimization should focus on useful split selection at depth 5.

### Research pause after 40 experiments

The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) identifies column sampling, leaf-wise growth and numeric histogram bins as distinct controls on split selection. The [tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) describes column sampling as a way to limit variance. Before those structural changes, finish bracketing the tree count at depth 5: 700 underfit, while 1,000 is best.

## Experiment 41 — 1,200 depth-5 trees (follow-up)

Hypothesis: AUC rose from 700 to 1,000 trees at depth 5. Test 1,200 rounds to see whether the learning curve is still rising or has reached an overfit peak. All other settings remain fixed.

Result: 245d3cd, Eval AUC 0.7570 (+0.0002). Keep under the higher-AUC rule, although the gain is small for 200 more trees and a 19.9 MB artifact.

## Experiment 42 — 1,500 depth-5 trees (follow-up)

Hypothesis: a wider 300-round step should reveal whether the tiny 1,200-round improvement continues or reverses. This brackets the useful tree count before trying a new split-selection mechanism.

Result: 4d494b3, Eval AUC 0.7569 (-0.0001) and 24.8 MB artifact. Discard; the curve has flattened and 1,200 trees remain best.

## Experiment 43 — column sampling per tree (exploration)

Hypothesis: CalendarDate can dominate splits and make trees correlated. Sampling 80% of features per tree may encourage complementary airport, carrier and time structure without removing any rows. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `colsample_bytree` as sampling columns anew for each tree, distinct from the row subsampling that failed earlier. Test 0.8 at the current best settings.

Result: e4b6d74, Eval AUC 0.7570 (equal). Artifact shrank to 17.4 MB and training was slightly faster, but this adds a parameter without AUC improvement or a meaningful code simplification. Discard; try one milder value before moving on.

## Experiment 44 — 90% column sampling (follow-up)

Hypothesis: a smaller amount of column sampling may retain more of the strong date and time signal while still diversifying trees. Test 0.9, in contrast to the equal-AUC result at 0.8.

Result: 5559e8c, Eval AUC 0.7571 (+0.0001). Keep under the higher-AUC rule; artifact is a little smaller than without sampling.

## Experiment 45 — 512 numeric histogram bins (exploration)

Hypothesis: scheduled departure time has 1,162 distinct values; default 256 histogram bins may merge time boundaries relevant to delay risk. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says increasing `max_bin` can improve split optimality at a compute cost. Test 512 bins, leaving categorical handling and all other parameters unchanged.

Result: 95dcc64, Eval AUC 0.7569 (-0.0002). Discard. Finer numeric split resolution did not help.

## Experiment 46 — 128 numeric histogram bins (follow-up)

Hypothesis: after 512 bins failed to improve, coarser bins may smooth noisy departure-time and distance thresholds. Test 128, half the default resolution, before closing this parameter family.

Result: c48dbe3, Eval AUC 0.7565 (-0.0006). Discard. Default 256 bins remain best.

## Experiment 47 — leaf-wise growth with 16 leaves (exploration)

Hypothesis: depthwise growth may spend splits on weak branches; with date/airport interactions, allocating up to 16 leaves to the highest-gain branches could generalize better and reduce model size. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `grow_policy="lossguide"` as prioritizing highest loss change and `max_leaves` as a leaf cap. Keep depth 5 as an additional safeguard and set max_leaves 16.

Result: fe82352, Eval AUC 0.7565 (-0.0006), 12.0 MB artifact. Discard. The cap may be too tight; test 24 leaves once.

## Experiment 48 — leaf-wise growth with 24 leaves (follow-up)

Hypothesis: allowing 24 leaves may retain useful date interactions that a 16-leaf budget removed while still allocating splits by loss gain and keeping the model smaller than uncapped depthwise trees.

Result: e2191ac, Eval AUC 0.7581 (+0.0010), 17.2 MB artifact. Keep. Selective allocation of roughly 24 leaves is effective at depth 5.

## Experiment 49 — leaf-wise growth with 32 leaves (follow-up)

Hypothesis: the improvement from 16 to 24 leaves may continue with the full depth-5 leaf budget of 32. Test 32 to locate whether the gain comes from leaf-wise ordering or the 24-leaf cap.

Result: 663082c, Eval AUC 0.7571 (-0.0010) and model size returned to 18.7 MB, essentially the uncapped depthwise result. Discard; the 24-leaf cap is the useful part.

## Experiment 50 — leaf-wise growth with 28 leaves (follow-up)

Hypothesis: the best leaf budget may lie between 24 (0.7581) and 32 (0.7571). Test 28 as one interior value, then move to another parameter rather than repeatedly nudging this cap.

Result: 08b50c9, Eval AUC 0.7580 (-0.0001) and a larger model than 24 leaves. Discard; 24 is the best tested cap.

### Synthesis after 50 experiments

At depth 5, 1,200 rounds gave a tiny gain over 1,000 and 1,500 flattened, so the current tree count is near optimal. Column sampling at 0.9 raised AUC by 0.0001, while 0.8 tied the prior best and was discarded for extra complexity. Finer (512) and coarser (128) numeric histograms both underperformed the default 256. Leaf-wise growth with a 24-leaf cap made the clearest gain in this block, reaching the current best 0.7581 at e2191ac; 16 leaves underfit, and 28 or 32 leaves were worse. The cap appears more important than growth order. Next: test whether allowing greater depth under the same leaf budget captures specific date × airport patterns without increasing leaf count.

### Research pause after 50 experiments

The [XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) describe depth and leaf count as separate limits, and leaf-wise growth as prioritizing the split with highest loss gain. A [review of leaf-wise models](https://www.nature.com/articles/s41598-026-40125-1_reference.pdf) notes that leaf-wise growth can go deeper and that a depth or leaf cap is useful. We have already selected a 24-leaf budget; the next test changes depth while holding that budget fixed.

## Experiment 51 — depth 6 under 24-leaf cap (follow-up)

Hypothesis: permitting one deeper path while retaining 24 leaves may capture a specific date-airport-carrier-time interaction without the overfitting seen in unrestricted depth-6 trees. Set depth 6; keep all else fixed.

Result: 637c1b0, Eval AUC 0.7566 (-0.0015). Discard. Depth 5 remains better even under a fixed leaf budget.

## Experiment 52 — minimum child weight 5 with date model (exploration)

Hypothesis: some of the 24 leaves may still isolate small noisy subsets after date and airport splits. Increase `min_child_weight` from 1 to 5 to reject those splits. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines this as a minimum sum of Hessian weight in a child; the earlier weak result at depth 4 preceded CalendarDate and leaf-wise growth.

Result: 08a978c, Eval AUC 0.7571 (-0.0010), 13.9 MB artifact. Discard. Weight 5 prunes too much; one milder value will test whether the effect can be useful.

## Experiment 53 — minimum child weight 2 (follow-up)

Hypothesis: a small increase from 1 to 2 may remove only the most fragile date-specific leaves without the underfitting seen at 5. Test it at the current best settings.

Result: cc86993, Eval AUC 0.7581 (equal), 16.3 MB artifact versus 17.2 MB. Discard: the smaller artifact is minor and it adds another code parameter without an AUC gain.

## Experiment 54 — L1 leaf regularization (exploration)

Hypothesis: L2=10 smoothly shrinks all leaf weights, while a modest L1 penalty may suppress only very weak late-round leaves. Test `reg_alpha=1` with all current best parameters. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines alpha as L1 regularization on weights.

Result: 3d3de30, Eval AUC 0.7619 (+0.0038), 15.7 MB artifact. Keep. Sparsifying weak leaf effects complements L2 and the 24-leaf cap very well.

## Experiment 55 — L1 strength 2 (follow-up)

Hypothesis: the gain at L1=1 may continue with stronger suppression of small leaf weights. Test `reg_alpha=2`, changing only this value.

Result: dc26125, Eval AUC 0.7632 (+0.0013), 14.0 MB artifact. Keep. The improvement continues, with a smaller model.

## Experiment 56 — L1 strength 4 (follow-up)

Hypothesis: AUC and model size improved at L1=1 and 2, so test a wider step to 4 to locate the point where useful leaf effects begin to be suppressed.

Result: e64295d, Eval AUC 0.7632 (equal at four-decimal precision), artifact fell from 14.0 MB to 12.4 MB. Keep as a smaller-model simplification with the same single-parameter code complexity.

## Experiment 57 — L1 strength 8 (follow-up)

Hypothesis: if 4 retains AUC with a smaller model, 8 may preserve or improve it further, or reveal the underfitting boundary. Test a doubled L1 penalty.

Result: af26e33, Eval AUC 0.7623 (-0.0009). Discard. L1=8 starts removing useful effects; 4 remains best on AUC and model size among the tied bests.

## Experiment 58 — 1,600 trees under L1=4 (follow-up)

Hypothesis: stronger L1 regularization suppresses weak late-round updates and may shift the useful boosting count above 1,200. Test a wide step to 1,600 rounds; the prior 1,500-round plateau was measured before L1 was added.

Result: 33a193f, Eval AUC 0.7634 (+0.0002), 16.3 MB artifact. Keep. L1 does make a longer ensemble marginally useful.

## Experiment 59 — 2,000 trees under L1=4 (follow-up)

Hypothesis: the tiny gain from 1,200 to 1,600 rounds might continue, but a 400-round step will reveal whether the curve is flattening or overfitting. Test 2,000 rounds at unchanged L1=4.

Result: 10bcb24, Eval AUC 0.7629 (-0.0005), 20.1 MB artifact. Discard. 1,600 rounds remain best with L1=4.

## Experiment 60 — remove column sampling (ablation/simplification)

Hypothesis: column sampling supplied only a 0.0001 gain before L1, and L1 now supplies much stronger regularization. Remove `colsample_bytree=0.9` to see whether it is still useful. Equal or better AUC would simplify code and remove randomness.

Result: f0ba87d, Eval AUC 0.7628 (-0.0006). Discard. Mild column sampling still contributes to generalization even with L1.

### Synthesis after 60 experiments

The last block found a much more effective regularizer: L1 leaf penalties. Adding alpha 1 raised AUC from 0.7581 to 0.7619, alpha 2 to 0.7632, and alpha 4 tied 0.7632 with a smaller artifact. Alpha 8 was too strong. With alpha 4, 1,600 rounds reached the current best 0.7634 (33a193f); 2,000 overfit. Removing column sampling after L1 made AUC worse, so it remains useful. Greater depth under the 24-leaf cap and minimum child weights 2/5 did not improve. Remaining time should focus on interactions among the few effective parameters, not more high-cardinality feature additions.

### Research pause after 60 experiments

The [XGBoost model guide](https://xgboost.readthedocs.io/en/latest/tutorials/model.html) shows L1 and L2 penalties enter the leaf-weight calculation differently; the [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) documents both. Since a longer ensemble became useful after L1, recheck the lower L1 strength at the 1,600-round count before trying any more feature changes.

## Experiment 61 — L1=2 at 1,600 rounds (follow-up)

Hypothesis: L1=2 and 4 tied at 1,200 rounds, but the larger 1,600-round ensemble may benefit from a different penalty. Test alpha 2 at 1,600 to isolate that interaction.

Result: e10cd5b, Eval AUC 0.7627 (-0.0007), 18.6 MB artifact. Discard; L1=4 remains better at 1,600 rounds.

## Experiment 62 — L1=5 at 1,600 rounds (follow-up)

Hypothesis: alpha 4 beats 2 in the longer ensemble, but alpha 8 previously underfit at 1,200 rounds. Test 5 as one nearby value to check whether the optimum is slightly above 4.

Result: f95e976, Eval AUC 0.7632 (-0.0002), 15.4 MB artifact. Discard; alpha 4 remains best at 1,600 rounds.

## Experiment 63 — 20 leaves with L1=4 (ablation/simplification)

Hypothesis: L1 shrinks weak leaves, so the previously optimal 24-leaf cap may now allow unnecessary splits. Test 20 leaves with the best 1,600-round/L1=4 model; equal or better AUC would reduce model complexity.

Result: 12b4005, Eval AUC 0.7639 (+0.0005), 14.7 MB artifact. Keep. Strong L1 shifts the useful leaf budget downward.

## Experiment 64 — 16 leaves with L1=4 (follow-up)

Hypothesis: if 20 leaves improve AUC and size, 16 may continue the trend or show the lower bound. This is the final leaf-budget probe before the clock expires.

Result: fc90376, Eval AUC 0.7639 (equal at four-decimal precision), 12.7 MB artifact versus 14.7 MB at 20 leaves. Keep as a smaller model with no additional code complexity.

## Final summary

The best Eval AUC is 0.7639 at commit fc90376, up 0.0436 from the untouched baseline's 0.7203. The final model uses a row-local month-day category, numeric departure minute, depth-5 XGBoost with 1,600 trees, category threshold 8, L2=10, L1=4, 0.9 column sampling, and leaf-wise growth capped at 16 leaves. The artifact is 12.7 MB and evaluation stays well within its five-minute limit.

What worked: more boosting rounds than the starter, conservative categorical partitions, L2 and especially L1 leaf penalties, the calendar-date category, depth 5 for date interactions, and a restrained leaf budget. What did not: high-cardinality route or carrier-origin categories, duplicate calendar encodings, a train-fitted daily target rate, heavy row sampling, one-hot category splits, extra numeric histogram resolution, gamma penalties, and ensembles beyond the useful boosting range. A useful next test would be a smaller leaf cap (for example 12) at L1=4, followed by checking whether the final date feature and departure-minute feature still contribute independently. The held-out ground truth remains for the human's post-run evaluation.
