# Research log — sep30

## Baseline — 92e43e6

Unchanged starter: 30 trees, depth 6, learning rate 0.1, native categorical splits. Eval AUC 0.7203; run completed in 31.4 seconds.

## Research before tuning

- [XGBoost parameter tuning](https://xgboost.readthedocs.io/en/release_0.72/tutorials/param_tuning.html): smaller learning rates generally need more boosting rounds; depth and minimum child weight control complexity, while row and column sampling can reduce overfitting.
- [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html): `max_depth`, `min_child_weight`, `subsample`, `colsample_bytree`, `reg_lambda` and `reg_alpha` provide different regularization controls.
- [UC Berkeley flight delay feature engineering project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches): scheduled timing, airline and airport identity can carry delay information. We have these columns and can derive hour, route and calendar features from each row.

## Experiment 1 — a1ad80b

Classification: follow-up to baseline. Hypothesis: 30 boosting rounds underfits; 200 rounds at the same learning rate should improve ranking without changing features. One parameter changes, so the result isolates boosting duration.

Result: 0.7345, a gain of 0.0142. Keep. Training remained fast at about 2 seconds.

## Experiment 2 — planned

Classification: follow-up. Hypothesis: the sizable gain from 30 to 200 rounds suggests additional rounds may still improve ranking. Try 500 rounds with all other settings fixed; this also reveals whether overfitting begins at the current depth.

Result: 0.7312, lower by 0.0033; discard. This setting appears to overfit or otherwise overshoot the useful boosting range.

## Experiment 3 — planned

Classification: follow-up. Hypothesis: 500 rounds at learning rate 0.05 may refine the model more gently than 200 rounds at 0.1 and avoid the degradation from 500 at 0.1. This follows XGBoost's guidance to trade smaller step size for more rounds.

Result: 0.7362, 0.0017 above the best. Keep. The lower learning rate appears useful at this boosting duration.

## Experiment 4 — planned

Classification: follow-up. Hypothesis: depth 6 may fit noisy flight-specific interactions; reducing depth to 4 should regularize while retaining the benefit of 500 small updates. [XGBoost's tuning notes](https://xgboost.readthedocs.io/en/release_0.72/tutorials/param_tuning.html) identify depth as a primary complexity control.

Result: 0.7337, lower by 0.0025; discard. Some interactions beyond depth 4 matter.

## Experiment 5 — planned

Classification: exploration (first engineered feature). Hypothesis: the raw `CRSDepTime` encodes HHMM, so its numeric spacing is wrong across hour boundaries. Add minutes after midnight while retaining the raw time. [This flight delay project](https://github.com/longwind48/airline-delay-prediction) found the same conversion useful; it is computed independently for each row.

Result: 0.7362, no improvement; discard for simplicity. In hindsight, converting HHMM to minute of day preserves ordering, so a tree can already make equivalent threshold splits on the raw value. The extra column is redundant here.

## Experiment 6 — planned

Classification: exploration. Hypothesis: a categorical departure hour lets a single tree split group nonadjacent hours and may capture repeating time-of-day patterns more efficiently than thresholds on HHMM. The [Berkeley feature analysis](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) identifies scheduled departure hour as a useful temporal field.

Result: 0.7356, down 0.0006; discard. The base numeric HHMM likely already captures enough time-of-day structure, and the extra categorical feature did not repay its complexity.

## Experiment 7 — planned

Classification: follow-up. Hypothesis: `min_child_weight=5` should suppress noisy splits in small leaves at depth 6 while preserving interactions that depth 4 lost. This is a different form of regularization per the [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html).

Result: 0.7349, down 0.0013; discard. The default leaf weight is better for this setup.

## Experiment 8 — planned

Classification: exploration. Hypothesis: an origin-destination route category can expose route-specific delay patterns that depth-6 trees may struggle to learn through two separate high-cardinality airport features. [Flight delay modeling work](https://github.com/AhmedFaizanDev/flight-delay-risk-prediction) uses route combinations, and [XGBoost's categorical guide](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) describes partition splits for high-cardinality categories. Fit route levels on train once, then apply the same dtype row by row.

Result: 0.7071, much worse; discard. There are 4,290 observed routes with median support 32 in the training data, so the new category is likely too sparse. The run completed but emitted a few pandas warnings for unseen eval routes; they were mapped to missing.

## Experiment 9 — planned

Classification: exploration. Hypothesis: `subsample=0.8` may make boosting less sensitive to individual flights and improve ranking at 500 trees. This tests the [XGBoost tuning guide's](https://xgboost.readthedocs.io/en/release_0.72/tutorials/param_tuning.html) suggestion to add sampling randomness as regularization.

Result: 0.7283, down 0.0079; discard. Stochastic row sampling harms this dataset at this tree count.

## Synthesis after 10 total runs

Best is 0.7362 at 39bd22c (500 trees, learning rate 0.05, depth 6). More learning at a smaller step was beneficial; 500 trees at 0.1 overdid it. Depth 4 and stronger minimum child weight both hurt, so moderate interactions and smaller leaves matter. Engineered departure minute/hour features did not help, while a sparse route category hurt badly. Row subsampling also hurt. The best model's gain-based feature importance places `CRSDepTime` first by a wide margin; I will investigate whether histogram resolution or categorical split handling can capture its structure better, and search for other ideas before the next run.

## Research after 10 runs

The current [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/release_3.2.0/parameter.html) states that `max_bin` defaults to 256 and increasing it improves split optimality at a computation cost. The training set has 1,162 distinct scheduled departure times, so the histogram may merge useful time thresholds. The [categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains one-hot versus partition splits, and the [tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) identify `gamma` and categorical thresholds as alternatives to depth and child-weight regularization. I will test bin resolution first, then revisit categorical split choices and tree growth.

## Experiment 10 — planned

Classification: exploration. Hypothesis: `max_bin=512` gives the dominant `CRSDepTime` feature finer candidate thresholds than the default 256 without adding features, improving AUC. The increased computation should remain within the one-minute training limit.

Result: 0.7364, up 0.0002 from the best with a single parameter and no noticeable training time cost; keep. The gain is small enough that a follow-up is needed before attributing it confidently to finer time splits.

## Experiment 11 — planned

Classification: follow-up. Hypothesis: `max_bin=1024` brings the histogram close to the 1,162 distinct scheduled departure times and may yield a further gain if split quantization was limiting. Other settings stay fixed.

Result: 0.7360, 0.0004 below the best; discard. The 512-bin setting remains preferred. Inspecting the saved best model's configuration confirmed `max_cat_to_onehot=4` and `max_cat_threshold=64` by default in installed XGBoost 3.4.1.

## Experiment 12 — planned

Classification: exploration of categorical splitting. Hypothesis: `max_cat_to_onehot=32` will let the model isolate specific months, weekdays, days of month and carriers, while airports still use partition splits. This may improve calendar and carrier signal with minimal code. [XGBoost's categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains the split distinction.

Result: 0.7234, much worse; discard. Partition splits are substantially better for calendar and carrier categories here.

## Experiment 13 — planned

Classification: exploration of categorical partition capacity. Hypothesis: `max_cat_threshold=128`, up from the default 64, may allow finer grouping among the 283 origin and destination airports. This tests whether the current cap omits useful airport contrasts, while retaining partition splits that worked well for smaller categories.

Result: 0.7358, down 0.0006; discard. Enlarging the candidate set did not help.

## Experiment 14 — planned

Classification: follow-up. Hypothesis: `max_cat_threshold=32` may regularize airport partitions better than the default 64. The loss at 128 suggests more candidates might be fitting noise, so the opposite direction is worth testing.

Result: 0.7365, up 0.0001 from best. Keep provisionally because it is one simple parameter; the movement is tiny and may be evaluation noise.

## Experiment 15 — planned

Classification: follow-up. Hypothesis: `max_cat_threshold=16` may regularize the airport partitions further if 32 was better than 64 and 128. A larger change in this direction will clarify whether the 0.0001 gain was meaningful.

Result: 0.7381, up 0.0016; keep. Tighter categorical partitions appear helpful, though the cap also affects 20 carriers and 31 day-of-month values. The effect is too large to dismiss as the previous 0.0001 movement.

## Experiment 16 — planned

Classification: follow-up. Hypothesis: `max_cat_threshold=8` may improve generalization further if the same regularization trend holds. This is an informative boundary test because it also limits month (12 values), unlike 16.

Result: 0.7402, up 0.0021; keep. The monotonic improvement from 128 to 64 to 32 to 16 to 8 strongly suggests categorical partitions were overly flexible at the default cap.

## Experiment 17 — planned

Classification: follow-up. Hypothesis: `max_cat_threshold=4` may continue this regularization trend, with each categorical partition permitted to consider only a few levels. This is a substantial change from 8 rather than a cosmetic tweak.

Result: 0.7337, down 0.0065; discard. The cap became too restrictive, so the useful range lies above 4.

## Experiment 18 — planned

Classification: follow-up. Hypothesis: `max_cat_threshold=12` may outperform 8 while avoiding the overfitting seen at 16. This brackets the optimum after 4 was much worse and 16 was better than default but worse than 8.

Result: 0.7413, up 0.0011; keep. This cap allows all 12 month values while limiting larger categories, which could explain the gain over 8.

## Experiment 19 — planned

Classification: follow-up. Hypothesis: `max_cat_threshold=10` may retain the benefit of tight airport/carrier partitions but test whether limiting month partitions below 12 causes the drop seen at 8. This isolates the importance of crossing the month cardinality boundary.

Result: 0.7404, down 0.0009; discard. Twelve remains best, and allowing all months may be part of why.

## Synthesis after 20 total runs

Best Eval AUC is 0.7413 at 8542ea5, up 0.0210 from baseline. The strong result of this block is `max_cat_threshold=12`: 128, 64, 32, 16, 8, 4, and 10 were all worse, with broad flexibility or very tight caps both harmful. The 512 histogram bin increase helped slightly, but 1,024 did not. Forcing one-hot splits on small categories was much worse than partitioning. A useful theory is that categorical effects matter, yet unrestricted grouping of airports and other categories overfits; a cap near 12 balances that. Next I will research calendar representations and alternate tree regularization before exploring a new direction.

## Research after 20 runs

The [XGBoost categorical tutorial](https://xgboost.readthedocs.io/en/release_3.2.0/tutorials/categorical.html) clarifies that categorical partitions group categories by outcome similarity, whereas numeric features split at ordered thresholds. A [flight delay study](https://doi.org/10.1145/3786484.3786539) reports calendar and holiday signals alongside scheduled flight fields. The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `gamma` and `grow_policy=lossguide` as different controls on tree structure. I will first add a compact numeric day-of-year feature, then investigate tree structure or regularization if it does not help.

## Experiment 20 — planned

Classification: exploration of calendar features. Hypothesis: a numeric day of year gives trees contiguous seasonal and holiday-period boundaries that are harder to express using separate categorical month and day-of-month splits. It is computed from each row only and retains the existing calendar categories.

Result: 0.7431, up 0.0018; keep. Date continuity supplies useful signal beyond separate month/day categories.

## Experiment 21 — planned

Classification: follow-up. Hypothesis: a categorical date alongside numeric day of year may capture day-specific flight disruption patterns shared between train and eval flights in the same year. Unlike the failed route feature, there are only 365 possible dates across 200,000 training rows. The [flight delay calendar study](https://doi.org/10.1145/3786484.3786539) supports searching for date-specific effects, while the numeric date retains smooth seasonality.

Result: 0.7494, up 0.0063; keep. A daily shared signal is much stronger than the smooth date feature alone. This should also be testable on the held-out random flight split after the run, because the date categories are fitted independently from labels and apply row by row.

## Experiment 22 — planned

Classification: follow-up. Hypothesis: with a 365-level Date category, `max_cat_threshold=16` rather than 12 may capture more irregular high-risk dates per partition. The earlier cap tuning happened before Date was added, so its optimum may have shifted.

Result: 0.7515, up 0.0021; keep. The Date feature benefits from a less restrictive partition cap.

## Experiment 23 — planned

Classification: follow-up. Hypothesis: `max_cat_threshold=32` may allow the Date feature to represent more date-specific shocks, despite having hurt the model before Date existed. This larger step brackets the new optimum and checks whether the gain at 16 continues.

Result: 0.7534, up 0.0019; keep. More date categories considered per split again improved AUC, despite the tradeoff for older categorical fields.

## Experiment 24 — planned

Classification: follow-up. Hypothesis: `max_cat_threshold=64` may keep improving the model by allowing even richer groupings of the 365 date levels. This returns the cap to its XGBoost default, but in a materially different feature space with Date.

Result: 0.7542, up 0.0008; keep. The default cap now outperforms lower values. If it remains best, removing the explicit parameter will be a simplification ablation.

## Experiment 25 — planned

Classification: follow-up. Hypothesis: `max_cat_threshold=128` may capture further date-specific effects now that Date is the main new categorical feature. This checks whether the rising trend from 12 through 64 continues or begins to overfit.

Result: 0.7554, up 0.0012; keep. More flexible Date partitions still help. Training remains well within one minute.

## Experiment 26 — planned

Classification: follow-up. Hypothesis: `max_cat_threshold=256` could improve Date grouping further, approaching its 365 levels. This is the last broad increase before changing direction; overfitting may finally appear.

Result: 0.7561, up 0.0007; keep. The gain continues, albeit smaller. Because 256 still truncates the 365 Date levels, one full-cap test is warranted before changing direction.

## Experiment 27 — planned

Classification: follow-up. Hypothesis: `max_cat_threshold=512` will allow all Date levels to be considered at a split and may yield a final gain. If it is worse, 256 is a clear stopping point for this parameter.

Result: 0.7565, up 0.0004; keep. This covers every observed Date category and also every airport category, so larger values cannot add candidates. The gains from 128 onward diminish, as expected.

## Experiment 28 — planned

Classification: follow-up. Hypothesis: with Date providing a strong new signal, 750 trees at learning rate 0.05 may capture additional date-airport and date-carrier interactions. The 500-tree count was selected before Date existed; training is currently only about four seconds.

Result: 0.7547, down 0.0018; discard. Boosting longer begins to overfit even with Date.

## Experiment 29 — planned

Classification: ablation/simplification. Hypothesis: Date deterministically encodes Month, DayofMonth, DayOfWeek and numeric DayOfYear in this single-year dataset, and the best model's gain importance for those four features is tiny. Remove them from X while retaining Date; this should reduce redundant splits and speed row-by-row preparation. If AUC stays equal or rises, the simpler pipeline wins.

Result: 0.7554, down 0.0011; discard. Evaluation became faster (25 versus 38 seconds), but the score loss is larger than the small code simplification warrants. Low individual gain importance did not mean the calendar fields were dispensable together.

## Synthesis after 30 total runs

Best Eval AUC is 0.7565 at 56fae62, up 0.0362 from baseline. Numeric day of year added 0.0018, then categorical Date added 0.0063. Once Date existed, widening `max_cat_threshold` from 12 to 512 gave a series of smaller gains totaling 0.0071, a reversal of the earlier result without Date. Date-specific variation seems to be the strongest new signal; `CRSDepTime` still has the highest gain importance. More boosting rounds hurt, and dropping all separate calendar fields lost 0.0011. I will search for ways to model date-time interactions and regularize trees without relying on sparse composite categories.

## Research after 30 runs

The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/latest/parameter.html) describes `gamma` as a minimum split gain and `grow_policy=lossguide` as choosing the node with greatest loss reduction, rather than splitting depthwise. It also identifies L2 regularization and column sampling as distinct controls. A [flight delay paper](https://arxiv.org/abs/2002.10254) emphasizes day-wise variation, consistent with the large Date gain. I will first test whether a modest minimum split gain regularizes the high-cardinality Date partitions, then consider a leaf-wise growth policy if needed.

## Experiment 30 — planned

Classification: exploration. Hypothesis: `gamma=1` may suppress weak Date and airport splits without reducing the number of boosting rounds or the useful partition candidate set. This is a different regularizer from the category cap and child weight previously tried.

Result: 0.7552, down 0.0013; discard. Pruning splits by gain hurt the strong Date model.

## Experiment 31 — planned

Classification: exploration. Hypothesis: `grow_policy='lossguide'` with at most 32 leaves may spend capacity on the strongest date-time interactions rather than filling the tree depthwise. XGBoost's [parameter guide](https://xgboost.readthedocs.io/en/latest/parameter.html) distinguishes these growth policies. The depth-6 bound remains for safety.

Result: 0.7559, down 0.0006; discard. The smaller leaf budget outweighed any benefit of different allocation.

## Experiment 32 — planned

Classification: exploration. Hypothesis: `reg_lambda=0` may preserve useful variation in the Date effect by reducing leaf-weight shrinkage. The added split-gain and leaf-count constraints both hurt, suggesting the current model may need rather than less flexibility. This tests the [XGBoost L2 control](https://xgboost.readthedocs.io/en/latest/parameter.html) independently.

Result: 0.7558, down 0.0007; discard. Some L2 shrinkage is beneficial.

## Experiment 33 — planned

Classification: follow-up. Hypothesis: `reg_lambda=5` may shrink noisy leaf values while preserving split structure. Since removing the default L2 weight hurt, a stronger weight is worth testing; unlike gamma, this does not forbid the split outright.

Result: 0.7552, down 0.0013; discard. The default value 1 is better than both 0 and 5.

## Experiment 34 — planned

Classification: exploration of deeper interactions. Hypothesis: depth 7 may capture local Date × airport × time effects that depth 6 misses. The earlier depth-4 test preceded Date and showed that shallower trees hurt; with Date now strong, one extra level is worth testing. The [XGBoost guide](https://xgboost.readthedocs.io/en/latest/parameter.html) warns depth raises complexity, so a modest one-level increase is appropriate.

Result: 0.7534, down 0.0031; discard. Deeper date interactions overfit or otherwise dilute the signal.

## Experiment 35 — planned

Classification: follow-up. Hypothesis: depth 5 may improve generalization now that Date exposes daily effects directly. It tests the opposite direction after depth 7 lost AUC, while remaining less restrictive than the earlier depth-4 trial before Date existed.

Result: 0.7560, down 0.0005; discard. Depth 6 remains the best among 5, 6 and 7 with Date.

## Experiment 36 — planned

Classification: follow-up to learning-rate gains. Hypothesis: 800 rounds at learning rate 0.03 may improve over 500 at 0.05 by taking smaller updates, while retaining similar total boosting strength. The 750-round test at 0.05 was worse, so lower learning rate is necessary for a longer run. [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommend increasing rounds as the step size falls.

Result: 0.7565, tied best to four decimals; discard because it adds 300 trees and two changed hyperparameters without a measurable gain.

## Experiment 37 — planned

Classification: ablation/simplification. Hypothesis: 400 trees at learning rate 0.05 may preserve Date signal while reducing model size and training time. Since 750 trees at this rate worsened AUC and 800 at lower rate only tied, the original 500 may be slightly beyond the useful range.

Result: 0.7565, tied best to four decimals; keep for simplicity. It removes 20% of the trees with no measured AUC loss.

## Experiment 38 — planned

Classification: ablation/simplification. Hypothesis: 300 trees may further reduce model size while retaining the same ranking. The prior 400-tree tie suggests the model had surplus rounds; this tests a further 25% reduction rather than another tiny adjustment.

Result: 0.7556, down 0.0009; discard. About 400 trees is a useful lower bound at this learning rate.

## Experiment 39 — planned

Classification: ablation/simplification. Hypothesis: restoring the default 256 histogram bins may retain the same AUC now that categorical Date supplies much of the new signal. The 512-bin gain was only 0.0002 before Date existed; removing this parameter would simplify the model and possibly speed fitting.

Result: 0.7558, down 0.0007; discard. The finer histogram still helps despite Date.

## Synthesis after 40 total runs

Best remains 0.7565, now at simpler 400-tree commit 68eee3f. This block did not raise AUC: gamma, loss-guided growth with 32 leaves, stronger or weaker L2, and depth 5 or 7 all hurt. A lower learning rate with more trees tied but was more complex; 400 trees tied the 500-tree score, while 300 lost AUC. The 512-bin setting remains useful. The best theory is that the model has enough tree capacity, and new row-stable features may have more upside than further global regularization. I will research additional time and flight-schedule representations next.

## Research after 40 runs

A [flight-factor XGBoost study](https://www.sciencedirect.com/science/article/pii/S2772415822000050) identifies departure time and carrier as influential alongside weather. Another [flight delay study](https://link.springer.com/article/10.1007/s13272-026-00941-7) treats scheduled hour and minute as available preflight fields. The [XGBoost categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains that categorical partitioning can group nonadjacent values, while our numeric scheduled time splits only at thresholds. Since the numeric time dominates feature importance and the earlier 24-level hour category did not help, I will test an exact scheduled-time category that can capture repeated timetable patterns.

## Experiment 40 — planned

Classification: exploration. Hypothesis: a categorical scheduled departure HHMM feature may group nonadjacent departure slots with similar delay risk and preserve minute-level timetable information that the earlier hour category lost. It is computed from each row alone with fixed valid HHMM levels. The numeric time stays in the model.

Result: 0.7342, down 0.0223; discard. There were 1,162 distinct scheduled times with median support 73; the category seems too granular or distracts from the strong numeric ordering.

## Experiment 41 — planned

Classification: follow-up. Hypothesis: 15-minute departure blocks (96 categories) may capture time-of-day groups without the sparsity of exact scheduled times. This is finer than the earlier 24-hour category and is stable per row. The [flight-delay feature literature](https://pmc.ncbi.nlm.nih.gov/articles/PMC12685205/) discusses departure-hour bins as useful temporal features, though this experiment tests a finer block size.

Result: 0.7576, up 0.0011; keep. Moderate granularity works where exact HHMM failed.

## Experiment 42 — planned

Classification: ablation/follow-up. Hypothesis: 30-minute blocks (48 categories) may improve generalization by pooling more flights per category and simplifying the time feature. This checks the coarse side of the useful range between the failed 24-hour feature and successful 96 quarter-hour levels.

Result: 0.7563, down 0.0013; discard. Thirty minutes is too coarse relative to the 15-minute feature.

## Experiment 43 — planned

Classification: follow-up. Hypothesis: 10-minute blocks (144 categories) may retain useful departure-bank detail beyond 15 minutes without the extreme sparsity of exact HHMM. This tests the finer side of the time-block range.

Result: 0.7566, down 0.0010; discard. The 96-level quarter-hour feature is the best tested time granularity; no more nearby block sizes are justified.

## Experiment 44 — planned

Classification: exploration of a targeted interaction. Hypothesis: carrier-by-quarter-hour categories may encode airline-specific schedule banks more directly than separate carrier and time splits. There are at most 20 × 96 combinations, much denser than the failed route category. [Flight-factor research](https://www.sciencedirect.com/science/article/pii/S2772415822000050) identifies both departure time and carrier as influential; XGBoost's [categorical partitioning](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) can group combinations with similar effects.

Result: 0.7360, down 0.0216; discard. The 1,502 observed combinations had median support 103, yet the high-cardinality category still hurt badly. Composite categories appear unhelpful here even when not extremely rare.

## Experiment 45 — planned

Classification: exploration of calendar hierarchy. Hypothesis: a coarse week-of-year category may pool neighboring dates and capture persistent seasonal or weather patterns that the 365-level Date category represents less efficiently. It is one row-derived feature with 53 levels. [Flight-delay feature research](https://www.mdpi.com/2079-9292/13/24/4910) describes week-of-year as a seasonal signal.

Result: 0.7568, down 0.0008; discard. Date and original calendar fields already carry sufficient seasonal context.

## Experiment 46 — planned

Classification: exploration of tree construction. Hypothesis: `tree_method='approx'` may discover better candidate splits for the dominant scheduled-time feature and rich categories than the default histogram method. [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/latest/parameter.html) distinguishes approximate quantile-sketch growth from the optimized histogram method; both support native categorical features. The experiment changes only the tree builder.

Result: 0.7567, down 0.0009; discard. Training rose to 12.5 seconds versus around four for `hist`, so the approximation did not repay its cost.

## Experiment 47 — planned

Classification: exploration. Hypothesis: `colsample_bytree=0.8` may reduce over-reliance on scheduled time and let Date, airports and carrier learn complementary patterns in trees where it is absent. This differs from the row subsampling that hurt earlier. [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/latest/parameter.html) describes column sampling as a regularization control.

Result: 0.7586, up 0.0010; keep. Feature diversity per tree appears useful, perhaps compensating for the dominance of scheduled time.

## Experiment 48 — planned

Classification: follow-up. Hypothesis: `colsample_bytree=0.6` may increase diversity further and improve ranking. This removes roughly two more features per tree than 0.8, a material change given the small feature set, and will show when the ensemble loses too much information.

Result: 0.7596, up 0.0010; keep. Diversity continues to help.

## Experiment 49 — planned

Classification: follow-up. Hypothesis: `colsample_bytree=0.4` may further reduce domination by the scheduled-time feature, but it risks depriving individual trees of enough context. This larger step checks the lower edge of a useful feature-sampling range.

Result: 0.7590, down 0.0006; discard. The useful range is between 0.4 and 0.8, with 0.6 best among tested values.

## Synthesis after 50 total runs

Best Eval AUC is 0.7596 at ff00774, up 0.0393 from baseline. A 15-minute departure block category added 0.0011; exact scheduled-time categories and 10- or 30-minute blocks were worse. A carrier-by-time composite category lost 0.0216 despite median support above 100, reinforcing that simple features are safer than high-cardinality combinations. Week-of-year and the `approx` tree method did not help. Column sampling improved AUC from 0.7576 to 0.7596 at 0.6, but 0.4 lost ground. Date, scheduled time, and their manageable marginal categories remain the strongest signals. I will research ways to balance tree diversity and boosting strength next.

## Research after 50 runs

The [XGBoost column-sampling documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) distinguishes sampling a column subset once per tree from sampling at each split; the rates accumulate if combined. Its [random-forest tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) describes boosting multiple randomized trees per round. The [DART tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) proposes tree dropout but warns training can be slower. [scikit-learn's ensemble guide](https://scikit-learn.org/stable/modules/ensemble.html) documents probability averaging across diverse classifiers. These suggest several diversity mechanisms; I will compare per-node and per-tree column sampling first, then consider a modest ensemble if no simple configuration improves.

## Experiment 50 — planned

Classification: exploration. Hypothesis: `colsample_bynode=0.6` may offer the same rough candidate count at each split as current tree-level sampling while allowing each tree to access all features somewhere. This could preserve useful date-time interactions with more local diversity. Replace rather than combine the tree-level 0.6 setting to isolate sampling granularity.

Result: 0.7586, down 0.0010; discard. Whole-tree feature sampling was better than independent sampling at each node.

## Experiment 51 — planned

Classification: exploration of boosted forests. Hypothesis: `num_parallel_tree=2` with 200 rounds (about 400 trees total) may average two differently column-sampled trees per boosting update, reducing variance without growing the model. [XGBoost's random-forest tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) explicitly allows this combination of parallel trees and multiple rounds.

Result: 0.7558, down 0.0038; discard. Pairing parallel trees within each boosting step was worse than the 400-step single-tree sequence.

## Experiment 52 — planned

Classification: exploration of model averaging. Hypothesis: soft voting across two full 400-tree models with different random seeds may reduce column-sampling variance while preserving the strong boosted sequence. [scikit-learn's ensemble guide](https://scikit-learn.org/stable/modules/ensemble.html) describes averaging predicted probabilities for diverse classifiers. This costs a second model and will be kept only for a meaningful AUC gain.

Result: 0.7611, up 0.0015; keep. Nine extra lines and a second model buy a meaningful gain, with training still only about 6.5 seconds and evaluation time essentially unchanged.

## Experiment 53 — planned

Classification: follow-up. Hypothesis: averaging a third independently seeded model may reduce remaining column-sampling variance. This adds one more full model, so a trivial AUC movement would not justify keeping it.

Result: 0.7621, up 0.0010; keep. One additional estimator entry and roughly four more seconds training are a reasonable trade for this gain.

## Experiment 54 — planned

Classification: follow-up. Hypothesis: five independent seeds may further average away model variance. Add two estimators; given the extra model weight, keep only if the AUC gain remains material.

Result: 0.7620, down 0.0001; discard. Three seeds seem sufficient, and the extra training/model size is not justified.

## Experiment 55 — planned

Classification: exploration of ensemble diversity. Hypothesis: replacing the third 0.6-column-sampling model with an 0.8 model may add complementary predictions better than a third random seed. The single 0.8 model was slightly weaker but still competitive, and this keeps ensemble size at three.

Result: 0.7615, down 0.0006; discard. Equal-parameter seeded models averaged better than this particular mixed-rate ensemble.

## Experiment 56 — planned

Classification: exploration. Hypothesis: mild row sampling (`subsample=0.9`) may add complementary diversity to each of the three models. The earlier 0.8 row sampling hurt a single model before Date, the 15-minute feature, and column sampling existed; a smaller change in this new setting is worth a targeted test.

Result: 0.7607, down 0.0014; discard. The full-row setting remains preferable even in the ensemble.

## Experiment 57 — planned

Classification: ablation/simplification. Hypothesis: DayOfWeek is determined by Date in this single-year dataset; removing it may give column-sampled trees more chances to select the stronger schedule and airport features, while reducing preparation work. The combined calendar ablation hurt before column sampling, but a single-column test in the current model is distinct.

Result: 0.7612, down 0.0009; discard. Even a redundant calendar signal helps the randomized trees, so feature importance and determinism alone do not justify removal.

## Experiment 58 — planned

Classification: follow-up to column sampling in the ensemble. Hypothesis: with three-seed averaging already reducing variance, `colsample_bytree=0.7` may retain more per-tree context than 0.6 while preserving enough diversity. This retunes sampling for the ensemble rather than repeating the earlier single-model test.

Result: 0.7615, down 0.0006; discard. The 0.6 rate remains best in the ensemble.

## Experiment 59 — planned

Classification: exploration of a different booster. Hypothesis: DART tree dropout at a low rate may improve ranking over a single standard booster by reducing dependence on early trees. The [XGBoost DART tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) notes potential quality gains but slower training. Try one model first to stay within the one-minute training limit; only consider an ensemble if this base model is competitive.

Result: training exceeded the 60-second limit before evaluation; log as crash and discard. This booster is too slow at 400 rounds on this machine.

## Synthesis after 60 total runs

Best Eval AUC is 0.7621 at 3b584f3, up 0.0418 from baseline. Three independently seeded models averaged with soft voting produced a meaningful gain over one; five seeds did not improve further. Mixing column-sampling rates, boosting parallel trees, sampling rows, changing to per-node column sampling, and dropping DayOfWeek each lost AUC. DART was too slow for the training limit. The reliable ingredients remain Date, 15-minute departure blocks, 400 rounds at 0.05, and 0.6 feature sampling per tree. Next I will focus on compact changes compatible with this ensemble and the 60-second training cap.

## Research after 60 runs

The [XGBoost monotonic-constraint tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html) supports constraining a named numeric feature while leaving the others free, and notes that more histogram bins can preserve useful split candidates. Earlier [flight-delay analysis](https://github.com/longwind48/airline-delay-prediction) found average delay tends to increase through the day; the relation can have local nonmonotonic bumps. The model already has a separate categorical quarter-hour feature for those bumps. I will test whether an increasing prior on numeric scheduled time improves generalization, keeping other features unconstrained.

## Experiment 60 — planned

Classification: exploration of domain prior. Hypothesis: constraining `CRSDepTime` to have a nondecreasing effect may help learn accumulated daily delay risk while the quarter-hour category handles local departures from that trend. XGBoost's named-feature constraint makes this a one-parameter change.

Result: 0.7609, down 0.0012; discard. Even with quarter-hour categories, forcing a monotonic raw-time effect removed useful flexibility.

## Experiment 61 — planned

Classification: exploration of cyclic calendar encoding. Hypothesis: sine and cosine of day of year may let a tree group winter dates across the December/January boundary in one split and model smooth seasonal effects beside the categorical Date. The features are deterministic per row, with no fitted statistics.

The [scikit-learn time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) shows how sine and cosine eliminate the artificial jump at a cycle boundary. It also cautions that expressive tree models can already learn many periodic patterns, so the added features need to earn their complexity here.

Result: 0.7621, tied best; discard. The cyclic features add code and runtime without an AUC gain.

## Experiment 62 — planned

Classification: exploration of leaf sparsity. Hypothesis: mild L1 regularization (`reg_alpha=0.1`) may suppress noisy leaf weights across the three seeded models while retaining their useful diversity. Keep the feature set and all other parameters fixed.

The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `reg_alpha` as L1 regularization on leaf weights.

Result: 0.7615, down 0.0006; discard. Even mild L1 regularization slightly reduced ranking quality.

## Experiment 63 — planned

Classification: local parameter search. Hypothesis: `colsample_bytree=0.5` may yield a better balance of per-model diversity and feature access for the three-seed average, between previously tested 0.4 and the current 0.6.

Result: 0.7612, down 0.0009; discard. The ensemble appears to need at least the current feature access per tree.

## Experiment 64 — planned

Classification: local parameter search. Hypothesis: 450 boosting rounds per ensemble member may recover useful later-stage corrections that 400 rounds omit. The single-model 500-round setting tied 400 rounds before ensemble averaging, so this is a direct check under the stronger ensemble.

Result: 0.7626, up 0.0005; keep. A small increase in rounds helped the three-model average.

## Experiment 65 — planned

Classification: local parameter search. Hypothesis: 500 rounds could continue the ensemble improvement if its members still gain useful corrections after round 450. All other settings stay fixed.

Result: 0.7625, down 0.0001; discard. The extra 50 rounds added runtime without improving ranking.

## Experiment 66 — planned

Classification: exploration of smaller leaves. Hypothesis: reducing `min_child_weight` from its default 1 to 0.5 could preserve fine-grained date and departure-time interactions that the model currently skips. The 450-round ensemble may average away some extra variance. [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) explains that this parameter sets the minimum child Hessian sum, so a lower setting permits smaller leaves.

Result: 0.7622, down 0.0004; discard. Smaller leaves added variance that the ensemble did not fully offset.

## Experiment 67 — planned

Classification: follow-up to the 450-round gain. Hypothesis: 425 rounds might retain the gain over 400 while stopping before the plateau apparent at 500. This specifically tests whether the best improvement requires all 50 added rounds.

Result: 0.7625, down 0.0001; discard. 450 rounds remain the best tested ensemble length.

## Research after three small discards

The [scikit-learn time-feature study](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) examines multiple representations of date and hour; a [flight-delay feature-engineering project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) identifies seasonality and departure-time blocks as useful temporal signals. Our existing Date and quarter-hour features capture each axis separately. A continuous scheduled minute within the year could represent a local time window spanning adjacent dates with one tree split. This is a model-based inference from the sources, not a documented feature recipe.

## Experiment 68 — planned

Classification: exploration of temporal interaction. Hypothesis: a numeric `ScheduledMinuteOfYear` will help trees identify multi-hour disruptions that cross midnight or date boundaries, without requiring separate Date and departure-time splits. It is computed from each row alone.

Result: 0.7622, down 0.0004; discard. Existing Date and departure-time representations already captured the useful temporal structure.

## Experiment 69 — planned

Classification: exploration of ensemble capacity. Hypothesis: depth-5 trees may be individually less expressive but generalize better after averaging three seeded models. The earlier single-model depth-5 result was only 0.0005 below depth 6 before quarter-hour features and feature subsampling were added, so the ensemble context could change the tradeoff.

Result: 0.7601, down 0.0025; discard. The ensemble benefits from depth-6 interactions.

## Synthesis after 70 total runs

The strongest advance in this block was extending the three-model ensemble from 400 to 450 rounds: Eval AUC increased from 0.7621 to 0.7626. At 425 and 500 rounds the score was 0.7625, so the useful extra boosting is narrow. Lower feature sampling, L1 regularization, smaller leaves, shallower trees, and an additional numeric time coordinate all reduced AUC. The current best combines full categorical Date partitioning with departure-quarter blocks and three independently seeded depth-6 models. Further small changes should focus on a different training mechanism or a compact feature with a clear reason, not more arbitrary calendar encodings.

## Research after 70 total runs

The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/release_3.3.0/parameter.html) documents gradient-based row sampling for histogram trees on CPU and GPU. It preferentially retains rows with large regularized gradients. Uniform row sampling at 0.9 previously hurt, but gradient-based sampling could retain informative hard examples while increasing diversity across the three members. The installed XGBoost version is 3.4.1, which supports this setting.

## Experiment 70 — planned

Classification: exploration of gradient-based row sampling. Hypothesis: `sampling_method="gradient_based"` with `subsample=0.9` may diversify ensemble members while preserving high-gradient rows that uniform sampling would drop. The prior uniform 0.9 result was 0.7607 at 400 rounds, so this tests a specific change in which rows are kept.

Result: 0.7610, down 0.0016; discard. Gradient-aware sampling did not recover the loss from dropping rows.

## Experiment 71 — planned

Classification: follow-up to the ensemble gain. Hypothesis: four independent seeds at 450 rounds may slightly improve average ranking over three. At 400 rounds, five seeds scored 0.7620 against three seeds at 0.7621; this checks whether the better 450-round members change the ensemble-size tradeoff.

Result: 0.7626, tied best; discard. A fourth member adds training cost without ranking gain.

## Experiment 72 — planned

Classification: exploration of learning-rate schedule. Hypothesis: 500 rounds at learning rate 0.04 may give finer corrections than 450 rounds at 0.05, while keeping the total boosting strength close. The prior 500-round test at 0.05 scored 0.7625, so this tests whether its extra rounds need smaller steps.

Result: 0.7616, down 0.0010; discard. Smaller boosting steps did not help the ensemble.

## Experiment 73 — planned

Classification: ablation and simplification. Hypothesis: categorical `Date` might carry the useful day-of-year signal by itself; if removing numeric `DayOfYear` holds AUC, the feature set becomes simpler. The numeric value remains an intermediate for constructing Date but is not given to XGBoost.

Result: 0.7610, down 0.0016; discard. Numeric day-of-year ordering still helps beside the categorical date.

## Experiment 74 — planned

Classification: exploration of histogram resolution. Hypothesis: 768 bins may allow more precise cuts for scheduled time and distance in the 450-round ensemble. Earlier, 512 beat 256 and 1024 bins before the categorical Date feature was added; the stronger model could have a different optimum. The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) explains that more bins can improve split optimality at some computation cost.

Result: 0.7618, down 0.0008; discard. Finer histogram resolution did not improve this ensemble.

## Final summary

The best Eval AUC is **0.7626** at commit **`3be07a8`** on branch `sep30`, up **0.0423** from the original 0.7203 baseline. This model uses categorical Date and 15-minute departure blocks, numeric day of year, full categorical partitioning up to 512 categories, 512 histogram bins, 450 depth-6 rounds at learning rate 0.05, 0.6 feature sampling per tree, and a soft average of three independently seeded XGBoost classifiers.

The largest feature gain came from categorical Date. Quarter-hour departure blocks and per-tree feature sampling added smaller gains; averaging three seeds added another meaningful improvement. Increasing ensemble rounds from 400 to 450 was the best change in the final block. Route and carrier-time combination categories, exact scheduled-time categories, row sampling, smaller leaves, depth changes, L1 regularization, extra calendar encodings, a fourth/fifth model, and finer histograms did not improve the kept model. A DART run exceeded the training limit.

If more time were available, I would investigate a compact representation of local airport/date disruption risk fitted only on training data, with careful treatment of target leakage. This would require a new design rather than another small hyperparameter adjustment. The evaluation here is solely the harness's Eval AUC; no held-out ground-truth data was accessed.
