# Research log — sep29

## 1. Baseline — `92e43e6`

The unchanged starter achieved Eval AUC 0.7203 in 31.7 seconds (training 1.1 seconds, evaluation 30.6 seconds). This is the reference for subsequent changes.

## 2. More boosting rounds — planned

**Follow-up.** Raise `n_estimators` from 30 to 200, keeping all other settings fixed. Hypothesis: 30 rounds at learning rate 0.1 leave substantial bias; more rounds should capture schedule and carrier effects. XGBoost's [tuning guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) links the learning rate to the number of boosting rounds. Its [parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes the complexity controls to revisit if extra rounds overfit.

Result: Eval AUC 0.7345 at `9178649`, a gain of 0.0142. Training remains fast (2.0 seconds including startup). Keep.

## 3. Longer boosting trajectory — planned

**Follow-up.** Increase from 200 to 500 rounds with all else fixed. The large gain from 30 to 200 suggests the model may still be capacity limited; this run measures whether performance continues to rise or begins to overfit.

Result: Eval AUC 0.7312 at `94c9738`, down 0.0033 from 200 rounds. Discard. The longer trajectory appears to overfit.

## 4. Bracket the round count — planned

**Follow-up.** Try 300 rounds, midway between the successful 200 and the worse 500. Hypothesis: the peak may be slightly above 200; this checks the shoulder of the curve without changing tree complexity.

Result: Eval AUC 0.7342 at `fcd6b7d`, 0.0003 below the 200-round model. Discard.

## 5. Shorter boosting trajectory — planned

**Follow-up.** Try 150 rounds. The 300 and 500 results show that adding trees beyond 200 loses AUC; 150 checks whether 200 is already past the peak or near it.

Result: Eval AUC 0.7332 at `c3d4b7a`, below 200 rounds. Discard. Keep 200 as the current best round count.

## 6. Shallower trees — planned

**Exploration.** At 200 rounds, reduce `max_depth` from 6 to 4. The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) identifies depth as a direct complexity control. Hypothesis: shallower trees will avoid fitting sparse carrier and airport combinations too closely, and can improve held-out ranking even with the same number of rounds.

Result: Eval AUC 0.7317 at `930ba08`, down 0.0028. Discard. The task appears to need interactions that depth four captures less well.

## 7. Increase minimum leaf weight — planned

**Exploration.** Set `min_child_weight=10` while restoring depth six and 200 rounds. The [parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) says this prevents splits with too little child Hessian. Hypothesis: it preserves deep interactions while reducing splits on rare airport and carrier combinations.

Result: Eval AUC 0.7344 at `116355a`, 0.0001 below the simpler default; discard. It suggests this regularizer can be increased substantially without much harm.

## 8. Intermediate leaf weight — planned

**Follow-up.** Try `min_child_weight=5`, between the default 1 and the nearly tied 10. Hypothesis: moderate regularization may improve ranking while retaining useful rare splits lost at 10.

Result: Eval AUC 0.7334 at `3235952`, below both the default and 10. Discard. This regularizer does not show a useful trend.

## 9. Row subsampling — planned

**Exploration.** Set `subsample=0.8` with 200 trees and default split constraints. The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) lists row subsampling as a way to make boosting more robust to noise. Hypothesis: varied training rows per tree could reduce dependence on unusual flight records.

Result: Eval AUC 0.7275 at `940b466`, down 0.0070. Discard. Row subsampling does not suit this setup.

## 10. Scheduled departure components — planned

**Exploration.** Add departure hour and minute columns derived from the `CRSDepTime` HHMM number inside `prepare(df)`. An [airline-delay feature engineering study](https://www.mdpi.com/2079-9292/13/24/4910) uses the hour and minute components to represent daily congestion patterns and within-hour effects. Hypothesis: the minute component may reveal schedule conventions shared across hours that tree splits on the raw HHMM value cannot express compactly. Both features depend only on each row.

Result: Eval AUC 0.7334 at `182a22a`, below the simpler 200-tree model. Discard.

## Synthesis after 10 runs

The large change from 30 to 200 boosting rounds yielded the only gain so far (+0.0142 AUC); the best is 0.7345 at `9178649`. The 150, 300 and 500 round tests bracket 200 as a reasonable count. Shallower trees lost useful interactions. Minimum leaf weight changes did not improve ranking, and row subsampling hurt substantially. Decomposing HHMM into hour and minute added no signal worth its cost. The next direction is to expose meaningful combinations of existing categorical fields, especially full calendar dates and routes, while checking that single-row evaluation stays fast.

The [XGBoost categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains partition-based splits and the importance of consistent category levels at inference. A [flight-delay study](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0335141) describes day-of-year and departure-time bins as temporal features. I will first test a numeric day-of-year, which is simpler than a 365-level category.

## 11. Day of year — planned

**Exploration.** Add numeric day-of-year from the `c-N` month and day fields, using fixed 2005 month offsets. Hypothesis: a continuous calendar coordinate lets a tree isolate seasonal windows or specific disruption dates with fewer splits than separate month/day categories. This is computed from each row alone.

Result: Eval AUC 0.7385 at `b0b805b`, +0.0040 over the previous best. Keep. Per-row evaluation rose by roughly five seconds but stayed well within the limit.

## 12. Exact date category — planned

**Follow-up.** Add a 365-level categorical version of day-of-year alongside the numeric version. XGBoost's [categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains how category partitioning groups values with similar leaf effects. Hypothesis: it may group non-adjacent unusual dates and capture weather or holiday events without many numeric splits.

Result: Eval AUC 0.7511 at `e2ff093`, +0.0126. Keep. The exact-date category carries substantial signal, likely shared date-level disruption patterns across training and evaluation rows.

## 13. Remove numeric date coordinate — planned

**Ablation/simplification.** Retain `DateCategory` but omit the numeric `DayOfYear` model column. Hypothesis: the new date category supplies most of the gain, making the numeric calendar feature unnecessary. Keep the smaller feature set if AUC is essentially unchanged.

Result: Eval AUC 0.7512 at `12f2ac8`, 0.0001 higher with one fewer feature. Keep.

## 14. Route category — planned

**Exploration.** Add an origin-destination route as one categorical feature, with levels fitted on `train`. A [flight-delay feature engineering paper](https://thesesjournal.com/index.php/1/article/download/1199/926/2029) constructs a route field from airport codes, and XGBoost's [categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) supports partition-based category splits. Hypothesis: route identity captures travel corridor effects beyond separate origin and destination splits. Roughly 4,290 distinct routes occur in training, so evaluation speed must also be checked.

Result: Eval AUC 0.7319 at `aa16a62`, down 0.0193; per-row evaluation increased to 48.6 seconds. Discard. The route category appears too sparse or distracts from more useful splits.

## 15. Broader categorical split search — planned

**Follow-up.** Raise `max_cat_threshold` to 128 on the best date-category model. The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) says this caps the categories considered at each partition split. Hypothesis: considering more of the 365 dates could form better groupings for shared delay events, at some cost in split search and overfitting.

Result: Eval AUC 0.7534 at `01e23f8`, +0.0022. Keep. The wider date split search helped at little runtime cost.

## 16. Further categorical split expansion — planned

**Follow-up.** Raise `max_cat_threshold` from 128 to 256, approaching the 365 date levels. Hypothesis: additional candidate date groupings may continue the observed gain; a drop would signal overfitting or diminishing returns.

Result: Eval AUC 0.7530 at `a9e142b`, down 0.0004. Discard; 128 remains best.

## 17. More rounds with date feature — planned

**Follow-up.** Test 300 boosting rounds while retaining `DateCategory` and `max_cat_threshold=128`. The earlier 300-round run was done before the strong date feature existed; that result may not carry over. Hypothesis: richer date splits may need a longer boosting path to refine the remaining airport and carrier interactions.

Result: Eval AUC 0.7522 at `8b66258`, down 0.0012. Discard. More rounds again appear to overfit.

## 18. Fewer rounds with date feature — planned

**Follow-up.** Test 150 rounds on the date-category model. If date effects are learned early, stopping before 200 may give better ranking. This rechecks the earlier round-count conclusion under the new feature set.

Result: Eval AUC 0.7530 at `814068c`, down 0.0004. Discard; 200 rounds remains best with the date feature too.

## 19. Moderately shallower date model — planned

**Exploration.** Reduce depth from six to five at 200 rounds, retaining date category and categorical threshold 128. The date feature now gives direct access to important calendar effects, so one less interaction level may lower variance without losing much capacity. The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) identifies depth as a primary complexity control.

Result: Eval AUC 0.7538 at `7407438`, +0.0004. Keep. The best tree depth changed after adding date identity.

## 20. Depth four with explicit dates — planned

**Follow-up.** Reduce depth from five to four, still using 200 rounds. Depth four failed before the date category existed, but that feature may now supply the relevant calendar combinations directly. This checks whether the shallow-tree gain continues.

Result: Eval AUC 0.7526 at `bd468d9`, down 0.0012. Discard. Five is the best tested depth for the date model.

## Synthesis after 20 runs

The strongest advance was exposing exact date as a categorical field. The numeric date coordinate improved AUC, but became redundant once `DateCategory` was available; removing it slightly improved AUC and simplified the model. A categorical split threshold of 128 improved on the default; 256 lost a little. At the new feature set, 200 boosting rounds and depth five are the best tested choices. A high-cardinality route category badly hurt both AUC and evaluation time. Current best: 0.7538 at `7407438`. The next research pass will focus on how XGBoost handles moderate-cardinality categories and on tree histogram settings for the departure-time variable.

The [XGBoost categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains one-hot versus partition-based category splits; the [tree-method guide](https://xgboost.readthedocs.io/en/stable/treemethod.html) notes that a larger `max_bin` can sometimes improve histogram accuracy. I will test categorical split behavior first, then numeric bin precision.

## 21. One-hot splits for small categories — planned

**Exploration.** Set `max_cat_to_onehot=13`, making the seven weekday and twelve month levels eligible for one-hot splits, while leaving carrier, airports and dates partitioned. Hypothesis: isolating specific weekdays or months may work better than partitioning them into gradient-sorted groups, especially now that exact date is also available.

Result: Eval AUC 0.7541 at `58b90e8`, +0.0003. Keep. The moderate-cardinality split mode matters modestly.

## 22. One-hot splits through carrier and day-of-month — planned

**Follow-up.** Raise `max_cat_to_onehot` to 32. This extends one-hot eligibility to twenty carriers and 31 day-of-month values while still partitioning airports and exact dates. Hypothesis: carrier-specific delays and recurring calendar-day effects are better isolated one at a time; a decline would favor grouped splits for these fields.

Result: Eval AUC 0.7496 at `961000d`, down 0.0045. Discard. One-hot splitting either carrier or day-of-month (or both) loses useful groupings.

## 23. Isolate carrier split mode — planned

**Ablation.** Test `max_cat_to_onehot=21`, adding the 20-level carrier to one-hot eligibility while leaving 31-level day-of-month partitioned. This identifies whether carrier was responsible for the decline at threshold 32; if not, day-of-month likely was.

Result: Eval AUC 0.7494 at `ef6ab4e`, down 0.0047. Discard. Carrier one-hot splitting caused nearly all of the threshold-32 loss; carrier grouping is important.

## 24. Weekday-only one-hot splits — planned

**Ablation.** Set `max_cat_to_onehot=8`, so weekday uses one-hot splits but month returns to partitioning. The successful threshold-13 change combined both. This isolates whether weekday one-hot alone yields the improvement, and may find a better mixed split strategy.

Result: Eval AUC 0.7537 at `ba93d1c`, below 0.7541 with month and weekday both one-hot. Discard. Month one-hot contributed the improvement.

## 25. Finer numeric histograms — planned

**Exploration.** Increase `max_bin` from its default 256 to 512 while restoring threshold 13. The [XGBoost tree-method guide](https://xgboost.readthedocs.io/en/stable/treemethod.html) says additional histogram bins can yield more accurate split candidates. Hypothesis: finer departure-time and distance cutoffs may improve ranking; category handling stays fixed.

Result: Eval AUC 0.7543 at `a6f25ac`, +0.0002, with training time rising from about one to five seconds. Keep provisionally: the added code is one parameter and time remains far below the limit.

## 26. Very fine numeric histograms — planned

**Follow-up.** Increase `max_bin` to 1024. Both numeric fields have more distinct values than 512; this tests whether the small gain continues or is saturated. Training time is expected to rise but should stay within 60 seconds.

Result: Eval AUC 0.7552 at `1632d1c`, +0.0009. Keep. The measured training time was about one second, so the previous run's five seconds appears to reflect runtime variability.

## 27. Cover every distinct numeric value — planned

**Follow-up.** Raise `max_bin` to 2048, above the observed unique counts of both `CRSDepTime` (1,162) and `Distance` (1,267). Hypothesis: near-exact numeric split placement may improve time/distance boundaries; a decrease would show overfitting or diminishing returns.

Result: Eval AUC 0.7548 at `bb6fd10`, down 0.0004. Discard. The gain from finer bins saturates around 1024.

## 28. Remove redundant day-of-month predictor — planned

**Ablation/simplification.** Remove `DayofMonth` from the model columns while retaining it to construct `DateCategory`. Exact date already determines day-of-month, so the separate category may consume splits without adding information. Hypothesis: equal or better AUC with fewer predictors and slightly faster evaluation.

Result: Eval AUC 0.7547 at `8911b4c`, down 0.0005. Evaluation fell from about 36.6 to 32.9 seconds, but the raw field and date transformation remain necessary, so code complexity barely changes. Discard in favor of higher AUC.

## 29. Remove weekday predictor — planned

**Ablation/simplification.** Remove `DayOfWeek` from model columns, retaining all other features. Exact 2005 date determines weekday, so it may be redundant. Hypothesis: the date category captures enough weekly pattern that omitting weekday could reduce split competition; a loss would show that direct weekly grouping remains useful.

Result: Eval AUC 0.7552 at `1a89bc0`, equal to the best at the reported precision. Evaluation dropped by roughly four seconds. Keep as a simplification; the date category carries the weekday signal adequately.

## 30. Larger minimum child weight with dates — planned

**Exploration.** Set `min_child_weight=10` on the simplified date model. The earlier test without date almost tied the default, and [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes it as preventing splits with little child Hessian. Hypothesis: with 365 date levels, requiring broader leaves may reduce overfitting on date-specific subsets.

Result: Eval AUC 0.7548 at `2fa7c2d`, down 0.0004. Discard. This regularizer again brings no measurable benefit.

## Synthesis after 30 runs

Current best is 0.7552 at `1a89bc0`, compared with 0.7203 baseline. One-hot splitting for month (with threshold 13) helped slightly, while one-hot carrier splitting hurt sharply; carrier needs grouped category splits. Increasing numeric histogram bins to 1024 helped, but 2048 did not. Removing weekday preserved AUC and sped row-wise evaluation; removing day-of-month lost a little AUC. Minimum child weight 10 remains unhelpful even with the date category. I will research other conservative ways to control tree growth and seek new domain features that do not rely on target leakage or row counts.

The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) identifies `gamma` as a minimum split-gain filter and `reg_lambda` as leaf-weight regularization. A [flight-delay study](https://www.mdpi.com/2079-9292/13/24/4910) also uses calendar week and hourly timing features; these remain options after testing tree regularization.

## 31. Minimum split gain — planned

**Exploration.** Set `gamma=1` on the current best model. Hypothesis: preventing weak additional splits may curb date-category overfitting while keeping the larger leaves and interactions that `min_child_weight=10` constrained too bluntly.

Result: Eval AUC 0.7551 at `39c2bdd`, 0.0001 below the simpler default. Discard.

## 32. Stronger L2 leaf regularization — planned

**Exploration.** Set `reg_lambda=5` (default 1). XGBoost's [parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) says L2 regularization makes leaf scores more conservative. Hypothesis: shrinking large leaf effects, especially for subsets of dates, may improve unseen-row ranking without banning splits.

Result: Eval AUC 0.7551 at `0bd9c3a`, 0.0001 below the simpler default. Discard. Three consecutive conservative parameter changes now failed with less than 0.001 movement, so pause for targeted research rather than trying another nearby setting.

The [flight-delay temporal-feature study](https://www.mdpi.com/2079-9292/13/24/4910) uses calendar week to capture holiday and peak-travel periods. This suggests a new feature family: weekly grouping may share information across nearby dates, while the existing exact-date category still captures exceptional days. The [UC Berkeley project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) also emphasizes time-of-day and seasonal operational patterns; I will test week grouping first.

## 33. Calendar week category — planned

**Exploration.** Add an ISO-style week-of-year category from the existing day-of-year calculation, using the fixed 2005 calendar. Hypothesis: nearby days share weather and travel-demand patterns, and a week category provides a smoother grouping than 365 separate dates. It is row-wise and uses no data aggregation.

Result: Eval AUC 0.7553 at `7874817`, only +0.0001, while evaluation rose by about four seconds and the week arithmetic adds complexity. Discard under the simplicity criterion.

## 34. Categorical departure hour — planned

**Exploration.** Add departure hour as a 24-level categorical feature. The earlier numeric hour-plus-minute experiment failed before the date feature existed; this test isolates the hour and lets XGBoost group non-adjacent hours. The [UC Berkeley project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) uses hourly departure blocks to represent operational cycles. Hypothesis: this will expose repeated time-of-day risk patterns more efficiently than splits on raw HHMM.

Result: Eval AUC 0.7546 at `fa66ce4`, down 0.0006. Discard. Raw HHMM with fine histograms captures time of day adequately.

The [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) contrasts depth-wise expansion (nearest-root nodes first) with loss-guided expansion (highest split gain first), with `max_leaves` as a size cap. This offers a way to use deeper interactions only where the data supports them.

## 35. Loss-guided trees with 16 leaves — planned

**Exploration.** Switch to histogram loss-guided growth, remove the depth cap and limit each tree to 16 leaves. Hypothesis: concentrated splits on important date/airport subsets may fit the heterogeneous delay patterns better than uniformly depth-limited trees, while controlling total leaf count.

Result: Eval AUC 0.7506 at `22e7d9f`, down 0.0046. Discard. The 16-leaf cap may be too restrictive or the growth policy unsuitable.

## 36. Loss-guided trees with 32 leaves — planned

**Follow-up.** Repeat loss-guided growth with 32 leaves, matching the maximum leaf count of a full depth-five tree. This distinguishes inadequate capacity at 16 leaves from a weakness in the policy itself.

Result: Eval AUC 0.7523 at `0a8a153`, down 0.0029. Discard. Extra leaves recovered part of the loss, but still lag the depth-wise model. Return to depth five.

Read-only inspection of the best artifact's split importances shows no splits on `Month`; `DayofMonth` receives only five. `CRSDepTime` has the highest average split gain, while `DateCategory` is used most often. This suggests a straightforward simplification before more feature additions.

## 37. Remove unused month predictor — planned

**Ablation/simplification.** Remove `Month` from the model columns but retain it for constructing `DateCategory`. Also remove `max_cat_to_onehot=13`, since no remaining categorical predictor has fewer than 13 levels. Hypothesis: the model should have essentially identical AUC with fewer feature conversions per evaluation row. If it does, keep the simpler code.

Result: Eval AUC 0.7552 at `49a0877`, equal to the best, with evaluation down to 28.7 seconds. Keep the simpler model.

## 38. Slower learning with more trees — planned

**Exploration.** Change learning rate from 0.1 to 0.05 and boosting rounds from 200 to 400, keeping the product roughly constant. The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends increasing rounds when reducing the step size. Hypothesis: smaller updates may give smoother date and airport effects and improve Eval AUC without changing feature engineering.

Result: Eval AUC 0.7556 at `ca2d591`, +0.0004; training remained fast (1.9 seconds). Keep.

## 39. Further shrinkage — planned

**Follow-up.** Try learning rate 0.025 with 800 trees, preserving the same approximate total update scale. Hypothesis: if the gain from 0.1 to 0.05 reflects smoother boosting, another halving may continue it; otherwise the effect is saturated.

Result: Eval AUC 0.7558 at `f6288f2`, +0.0002, with training at 3.7 seconds. Keep.

## 40. Very small boosting steps — planned

**Follow-up.** Halve to learning rate 0.0125 and increase to 1,600 trees. This tests the limit of the observed shrinkage trend at roughly constant total update scale. Training is expected to remain under the one-minute limit.

Result: Eval AUC 0.7559 at `cb38f40`, +0.0001, while training time doubled to 7.4 seconds and model size approximately doubled. Discard under the simplicity criterion; retain 0.7558 at 800 trees.

## Synthesis after 40 runs

The best balance is currently 0.7558 at `f6288f2`, with 800 depth-five trees, learning rate 0.025, 1024 histogram bins and the exact-date category. Removing unused month and weekday predictors retained AUC and returned evaluation to about 29 seconds. Conservative split and leaf regularizers gave no useful gain, and loss-guided tree growth was worse. Smaller learning rates improved AUC, but the gains diminished rapidly: moving from 800 to 1,600 trees bought just 0.0001. I will now revisit low-cost calendar context and look for train-derived numeric context that remains stable during row-wise evaluation.

The [XGBoost DART guide](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) describes tree dropout as an alternative for large ensembles, though it warns training can be slower. The [flight-delay temporal feature study](https://www.mdpi.com/2079-9292/13/24/4910) again supports day-of-year and time-of-day context. I will first test a cheap numeric day coordinate now that the separate month predictor has been removed, then consider dropout or train-fitted airport context.

## 41. Restore numeric calendar coordinate — planned

**Exploration.** Add numeric `DayOfYear` alongside `DateCategory`. This was not helpful when Month was a model feature and the histogram was coarser; both conditions have changed. Hypothesis: after removing Month, the numeric calendar coordinate may restore smooth seasonal ordering while the date category handles exceptional days. It is already computed inside `prepare`, so this adds one cheap column.

Result: Eval AUC 0.7557 at `f8712d5`, 0.0001 below the best with extra evaluation work. Discard. Exact-date partitioning still suffices.

An [airport schedule-profile study](https://www.nature.com/articles/s41598-024-68884-9) finds airport-specific daily schedule structure relevant to delay behavior. As an inference from that work, a flight's scheduled time relative to its origin airport's typical scheduled time might be a useful low-cost proxy. The median is fitted once on `train`, not recalculated on each `prepare` input.

## 42. Departure time relative to origin median — planned

**Exploration.** Compute a training-fitted median `CRSDepTime` for each origin, then add `CRSDepTime - origin_median` inside `prepare`. Hypothesis: a departure that is early or late relative to an airport's usual schedule may carry different delay risk, and this gives the tree a direct airport-time interaction. Unseen origins map to missing, which XGBoost handles.

Result: Eval AUC 0.7558 at `48c43ff`, tied the best while adding a fitted lookup and about three seconds of per-row evaluation. Discard under the simplicity criterion.

The [XGBoost DART guide](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) reports slower training and warns that prediction with DART may require an explicit iteration range. The fixed harness calls `predict_proba` without one; adding a wrapper solely for DART would add complexity, so I will test a simpler regularizer first. The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) lists feature subsampling as a way to reduce overfitting.

## 43. Tree-level feature subsampling — planned

**Exploration.** Set `colsample_bytree=0.9` on the current 800-tree model. With seven model columns, each tree should omit roughly one, encouraging reliance on alternatives to the very strong departure-time and date splits. Hypothesis: this modest diversification may improve unseen-row ranking without altering the feature pipeline.

Result: Eval AUC 0.7561 at `af74b1b`, +0.0003. Keep.

## 44. Stronger tree-level feature subsampling — planned

**Follow-up.** Reduce `colsample_bytree` to 0.8. The 0.9 gain suggests some feature diversification helps; this tests whether more trees trained without the dominant date or time feature continue to improve AUC, or lose essential information.

Result: Eval AUC 0.7560 at `1ff626d`, down 0.0001. Discard in favor of 0.9.

## 45. Mild row subsampling with feature subsampling — planned

**Exploration.** Add `subsample=0.9` to the best `colsample_bytree=0.9` model. Row subsampling at 0.8 hurt the early model, but the current model has many more rounds and the date category. Hypothesis: a milder row sample may complement feature diversification without losing too many examples of rare dates or airports. The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) identifies both sampling controls as robustness tools.

Result: Eval AUC 0.7578 at `a0633cb`, +0.0017. Keep. The current, richer model benefits from mild row sampling.

## 46. Stronger row subsampling with feature sampling — planned

**Follow-up.** Change `subsample` from 0.9 to 0.8 while keeping `colsample_bytree=0.9`. Hypothesis: the gain may continue if overfitting is still the limit; a decline would point to 0.9 as the better tradeoff for sparse date-airport combinations.

Result: Eval AUC 0.7566 at `ca72b84`, down 0.0012. Discard. At 0.8, too many relevant date-airport examples may be omitted per tree.

## 47. Slightly lighter row subsampling — planned

**Follow-up.** Test `subsample=0.95`, between the best 0.9 and the earlier no-subsampling result of 0.7561 with the same column setting. This brackets whether the optimum is near 0.9 or nearer full-row training.

Result: Eval AUC 0.7589 at `f754d30`, +0.0011. Keep. Mild stochastic row selection is helpful; the optimum is closer to full training than to 0.8.

## 48. Very light row subsampling — planned

**Follow-up.** Test `subsample=0.975`, between 0.95 and 1.0. Hypothesis: if 0.95 is still suppressing useful rare-date examples, a lighter sample may do better; otherwise 0.95 is near the peak.

Result: Eval AUC 0.7591 at `ae7e6d8`, +0.0002. Keep. A very small amount of row randomness still helps substantially versus 1.0.

## 49. Near-full row sample — planned

**Follow-up.** Test `subsample=0.99`, between 0.975 and full rows. This checks whether the small gain continues toward 1.0 or whether the improvement requires withholding at least a few percent of rows per tree.

Result: Eval AUC 0.7582 at `3ae17df`, down 0.0009. Discard. The tested peak is near 0.975.

## 50. Stronger column sampling with near-full rows — planned

**Exploration.** With `subsample=0.975` fixed, reduce `colsample_bytree` from 0.9 to 0.8. The earlier column-only test lost just 0.0001; row sampling could change its effect. Hypothesis: complementary row and feature randomness may improve ranking, while a decline would confirm 0.9 as the better feature setting.

Result: Eval AUC 0.7594 at `f77e5aa`, +0.0003. Keep. Row and feature sampling interact: 0.8 columns lost slightly without row sampling but helps with it.

## Synthesis after 50 runs

Current best is 0.7594 at `f77e5aa`, a gain of 0.0391 over the unchanged baseline. Explicit date identity remains the largest single source of improvement; the compact model now uses raw time, distance, day-of-month, carrier, origin, destination and date category. Slower learning brought small gains. Mild row sampling brought a larger gain, peaking around 0.975; more aggressive row sampling hurt. Feature sampling at 0.8 became helpful when paired with row sampling. Next I will examine whether these sampling settings change the best tree depth or categorical split limit, rather than continuing tiny sampling increments.

The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) notes that column and row sampling add randomness, while depth controls tree complexity. It also documents `gradient_based` row sampling on CPU with histogram trees as a later option. I will first retest tree depth in the now sampled model, then consider a sampling-method change.

## 51. Deeper trees under sampling — planned

**Follow-up.** Increase `max_depth` from five to six with row sampling 0.975 and column sampling 0.8. Depth six was slightly worse before sampling. Hypothesis: regularization from sampling may now let additional airport-date-time interactions generalize.

Result: Eval AUC 0.7602 at `9646522`, +0.0008. Keep. The sampling controls changed the optimal complexity direction.

## 52. Depth seven under sampling — planned

**Follow-up.** Increase depth from six to seven while retaining the same sampling and boosting settings. Hypothesis: the added interaction level may continue the gain; a decline would locate the complexity peak near six.

Result: Eval AUC 0.7597 at `191fe17`, down 0.0005. Discard. Six is the best tested sampled-tree depth.

## 53. Wider date-category split limit under sampling — planned

**Follow-up.** Raise `max_cat_threshold` from 128 to 160 at depth six. The earlier 256 test lost slightly, but the current sampled model has more trees and depth. Hypothesis: allowing a few more date categories in candidate partitions may help the richer model isolate disruption days without reaching the overly broad 256 limit. The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes this limit as a categorical overfitting control.

Result: Eval AUC 0.7607 at `d897245`, +0.0005. Keep.

## 54. Continue date-category split expansion — planned

**Follow-up.** Increase `max_cat_threshold` from 160 to 192. The gain from 128 to 160 suggests more candidate date partitions may still help; this tests the next step before the previously weak 256 setting.

Result: Eval AUC 0.7610 at `3202d29`, +0.0003. Keep.

## 55. Date-category split limit 256 in sampled model — planned

**Follow-up.** Raise `max_cat_threshold` to 256. This previously scored below 128 in the unsampled model, but the current model has both row/feature sampling and greater depth; the two recent increases helped. Hypothesis: broader candidate partitions may now generalize, or 192 will prove the peak.

Result: Eval AUC 0.7607 at `4fae37e`, down 0.0003. Discard. The date split search appears near its useful limit.

## 56. Upper shoulder of date split limit — planned

**Follow-up.** Test `max_cat_threshold=224`, between the 192 best and 256 decline. This checks whether 192 is a sharp local peak or whether modestly broader partitions can still improve ranking.

Result: Eval AUC 0.7610 at `9fa18f9`, tied 192. Discard and retain the smaller split search.

## 57. More boosting rounds under sampling — planned

**Follow-up.** Increase rounds from 800 to 1,000 at learning rate 0.025, with sampled depth-six trees and threshold 192. The added randomness and deeper trees may change the useful stopping point. Hypothesis: extra rounds will finish fitting date-airport interactions that the sampled trees learn more slowly; a decline would signal overfitting.

Result: Eval AUC 0.7607 at `a8a6f2f`, down 0.0003. Discard; more rounds overfit slightly.

## 58. Fewer boosting rounds under sampling — planned

**Follow-up.** Test 600 rounds to bracket the 800-round best from below. Hypothesis: the richer depth-six trees might reach their peak before 800; if AUC falls, 800 is well supported as the current count.

Result: Eval AUC 0.7595 at `6000ad2`, down 0.0015. Discard; 800 rounds remains best.

## 59. Gradient-based row sampling — planned

**Exploration.** Set histogram `sampling_method="gradient_based"` and `subsample=0.5`. The current [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) says this method samples rows in proportion to gradient and Hessian magnitude and supports CPU histogram trees, allowing lower sample fractions. Hypothesis: focusing trees on harder flight records could improve ranking while preserving speed. This is a new sampling regime, so compare the combined method and rate against the best uniform 0.975 sample.

Result: Eval AUC 0.7555 at `ab84b0e`, down 0.0055, with longer training. Discard. The hard-row emphasis at half the data is not useful here.

## 60. Node-level feature sampling — planned

**Exploration.** Replace `colsample_bytree=0.8` with `colsample_bynode=0.8`, keeping uniform row sampling 0.975. The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) distinguishes sampling features once per tree from sampling at each split. Hypothesis: node-level sampling may create more varied date, time and airport interactions within each tree while still discouraging dominant splits.

Result: Eval AUC 0.7593 at `6072e56`, down 0.0017. Discard. Tree-level feature sampling remains better.

## Synthesis after 60 runs

The current best is 0.7610 at `3202d29`. With row and tree-level feature sampling, depth six surpassed depth five, but seven was worse. A date-category split limit of 192 improved on 128 and 160; 224 tied and 256 fell. At these settings, 800 boosting rounds outperformed 600 and 1,000. Gradient-based row sampling at 0.5 and per-node feature sampling both lost AUC. These patterns suggest the stochastic model is useful but sensitive to the exact random sample. The next direction is to test whether averaging independently sampled models can reduce that variance without changing the feature pipeline.

The [scikit-learn soft-voting documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html) confirms that `VotingClassifier` fits clones of each estimator and averages probabilities. Its [bagging example](https://scikit-learn.org/stable/auto_examples/ensemble/plot_bias_variance.html) demonstrates variance reduction from averaging randomized trees. This motivates a two-seed XGBoost ensemble; both members will use the same `train.csv` and `prepare`.

## 61. Average two independently sampled models — planned

**Exploration.** Train two copies of the current XGBoost model with seeds 42 and 43, then average probabilities with `VotingClassifier(voting="soft")`. Hypothesis: different row and feature draws can offset unstable splits and improve unseen-row ranking. The cost is roughly double the model size and fit time, so a tiny AUC gain would not justify keeping it.

Result: Eval AUC 0.7614 at `8e583e7`, +0.0004, but artifact size reached 58.3 MB and fit time 10.1 seconds versus about five for one model. Discard under the simplicity criterion.

## 62. Moderate minimum child weight in sampled depth-six model — planned

**Exploration.** Set `min_child_weight=3`. Prior tests of 5 and 10 were before the final combination of date partitions, depth six and stochastic sampling. Hypothesis: a modest leaf constraint will curb occasional sparse date-airport splits without losing as much capacity as 10. The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes this parameter as the minimum child Hessian weight.

Result: Eval AUC 0.7605 at `e1fa82d`, down 0.0005. Discard. Additional leaf restraint still hurts.

## 63. Relax minimum child weight — planned

**Follow-up.** Set `min_child_weight=0.5`, below the default 1. Because increasing this constraint repeatedly lost AUC, the model may benefit from a few finer date-airport splits. Row and feature sampling may still control overfitting. A gain would support that interpretation; a loss would keep the default.

Result: Eval AUC 0.7614 at `daed238`, +0.0004. Keep. Finer leaves helped the sampled depth-six model.

## 64. Further relaxed child weight — planned

**Follow-up.** Set `min_child_weight=0.25`. If extra fine splits are genuinely useful, this may continue the gain; a decline would show that 0.5 provides enough flexibility.

Result: Eval AUC 0.7611 at `832c342`, down 0.0003. Discard; 0.5 balances leaf flexibility best so far.

## 65. L1 shrinkage for finer leaves — planned

**Exploration.** Add `reg_alpha=0.5` to the `min_child_weight=0.5` model. The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes L1 shrinkage of leaf weights. Hypothesis: now that smaller leaves are allowed, suppressing weak leaf effects may preserve useful date-airport interactions while filtering noise.

Result: Eval AUC 0.7614 at `6289384`, tied the simpler default. Discard.

## 66. Relax L2 shrinkage for finer leaves — planned

**Exploration.** Set `reg_lambda=0.1` instead of the default 1. The successful lower `min_child_weight` suggests some useful small effects were being suppressed; weaker L2 shrinkage may let them contribute. Sampling remains the main overfitting control. The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes this as L2 regularization on leaf weights.

Result: Eval AUC 0.7607 at `e5e3a92`, down 0.0007. Discard. The default L2 shrinkage is useful.

## 67. Slightly stronger L2 shrinkage — planned

**Follow-up.** Set `reg_lambda=2`, just above the default 1. Since reducing L2 hurt, a modest increase may suppress noisy fine leaves while retaining the benefit of `min_child_weight=0.5`. This is more targeted than the earlier jump to 5.

Result: Eval AUC 0.7606 at `6c7a943`, down 0.0008. Discard. The default L2 setting is best of these tests. Three consecutive regularization changes were discarded with less than 0.001 movement; pause for research and a different feature family.

Research on [airport-level delay prediction](https://proceedings.mlr.press/v82/vandal18a.html) emphasizes airport characteristics, while a [flight-factor study](https://www.sciencedirect.com/science/article/pii/S2772415822000050) finds carrier effects important. I infer that a carrier's operations at a particular origin may differ from either average effect alone. The proposed combined category has about 1,551 observed training levels, versus 4,290 for the failed route category; it remains a sparsity risk.

## 68. Carrier at origin category — planned

**Exploration.** Add a train-fitted categorical `UniqueCarrier-Origin` combination inside `prepare`, retaining the original carrier and airport fields. Hypothesis: carrier-specific origin operations may affect departure delay in ways a depth-six tree does not efficiently capture from separate categories. Evaluation speed and overfitting are the main risks.

Result: Eval AUC 0.7479 at `1d3dbaf`, down 0.0135; evaluation rose to 37.0 seconds. Discard. Another high-cardinality combination overfit, like the route feature.

## 69. Decaying learning rate — planned

**Exploration.** Use XGBoost's [LearningRateScheduler callback](https://xgboost.readthedocs.io/en/stable/python/callbacks.html) to decay the rate from 0.05 toward 0.01 across 800 trees. The sum of rates is close to the current constant-rate run, but early trees can learn broad effects faster and later trees can refine them with smaller steps.

Result: Eval AUC 0.7601 at `d2b03b6`, down 0.0013. Discard. The current constant learning rate performs better.

### Synthesis after 70 experiments

The strongest gains have come from an exact calendar-date category, more histogram bins, longer boosting at a smaller constant learning rate, and modest row/column sampling. The latest depth-six model and `min_child_weight=0.5` reached 0.7614. Stronger or weaker L2 regularization, a learning-rate decay, and high-cardinality carrier/route combinations did not help. The working theory is that date and time effects matter, but very sparse pairwise categories overfit. A [flight-delay feature study](https://www.mdpi.com/2079-9292/13/24/4910) explicitly groups departures into two-hour periods; the [XGBoost categorical tutorial](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) describes category partitioning that might model non-monotonic period effects.

## 70. Two-hour departure periods — planned

**Exploration.** Add a 12-level categorical feature computed from scheduled HHMM departure time, while retaining the raw time. Earlier numeric hour/minute additions did not help, but categorical partitioning can group disjoint busy periods in one split. The category is derived independently for each row.

Result: Eval AUC 0.7601 at `98647e6`, down 0.0013 and slower evaluation. Discard.

## 71. Cross-fitted origin-day delay rate — planned

**Exploration.** Estimate a smoothed delay rate for each origin and calendar day from `train.csv`, excluding the row's deterministic fold when looking up its feature. [Scikit-learn's target-encoding example](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html) explains why cross-fitting avoids training-label leakage; [delay-propagation research](https://arxiv.org/abs/1206.6859) motivates local airport conditions. The lookup is fitted only on training data, and each row's fold depends only on its input fields, so `prepare` gives the same feature whether called on a batch or one row. Smoothing toward the global training rate should limit noise in sparse origin-days.

Result: Eval AUC 0.7581 at `945972c`, down 0.0033; artifact grew to 31.9 MB and evaluation to 41.1 seconds. Discard. Sparse local label aggregates did not justify their cost.

## 72. Remove day-of-month predictor — planned

**Ablation/simplification.** The exact-date category already contains the day of month. Remove the standalone categorical `DayofMonth` feature to check whether its recurring monthly pattern helps generalization or simply competes with the stronger date feature. A tied score would favor the smaller representation.

Result: Eval AUC 0.7615 at `b927226`, up 0.0001 with one fewer predictor and evaluation down to 25.7 seconds. Keep as a simplification.

## 73. Restore broad month category — planned

**Follow-up.** Add `Month` as a standalone category on the simpler date-based model. A month effect can pool evidence across its days while the date category captures specific weather and disruptions. The earlier month ablation was tied under a different depth and sampling setup; this tests whether the current depth-six model can use both scales.

Result: Eval AUC 0.7616 at `289b542`, up only 0.0001 with an added predictor and about four seconds slower evaluation. Discard under the simplicity criterion.

## 74. Cross-fitted date delay rate — planned

**Exploration.** Add a smoothed target-encoded date feature, with a deterministic five-fold exclusion so each training row is encoded without its own label. Dates have far more observations than origin-day pairs, so their target rates should have much less variance. The [scikit-learn target-encoding example](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html) motivates the fold exclusion. Keep the existing date category as well to test whether its supervised grouping and a numeric risk estimate complement each other.

Result: Eval AUC 0.7599 at `fe44583`, down 0.0016 with slower evaluation. Discard. The native date category remains the simpler, stronger representation.

## 75. More features per tree after day ablation — planned

**Follow-up.** Raise `colsample_bytree` from 0.8 to 0.9 now that the standalone day-of-month predictor is gone. With fewer columns, this may let more trees use both date and airport information while retaining row subsampling. The earlier 0.9 setting was tested with the larger predictor set and shallower trees.

Result: Eval AUC 0.7596 at `a21c88e`, down 0.0019. Discard. The leaner feature set still benefits from stronger per-tree column sampling.

## 76. Loss-guided growth with full depth-six capacity — planned

**Follow-up.** Try `grow_policy="lossguide"` with up to 64 leaves and the existing depth-six limit. [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) says this policy splits nodes with the highest loss change first. Earlier 16- and 32-leaf caps hurt, so this test preserves the full capacity while changing where splits are allocated.

Result: Eval AUC 0.7615 at `0695224`, tied but with extra parameters and slower training. Discard.

## 77. Approximate tree construction — planned

**Exploration.** Set `tree_method="approx"` while keeping the best feature set and hyperparameters. The [XGBoost tree-method documentation](https://xgboost.readthedocs.io/en/release_3.3.0/treemethod.html) describes its weighted quantile sketch; it may choose different numeric thresholds than the current histogram method for long boosting sequences. The training time limit is the main risk.

Result: Eval AUC 0.7607 at `a174d30`, down 0.0008 and about three times slower training. Discard.

## 78. Light tree dropout — planned

**Exploration.** Try XGBoost's DART booster with a small 1% tree dropout and a 50% chance of skipping dropout each round. The [DART paper](https://arxiv.org/abs/1505.01866) describes reducing late-tree specialization; this might improve generalization after 800 small boosting steps. Keep the rest of the best model fixed to isolate the booster change. Training may exceed the one-minute limit.

Result: `4cbe61b` timed out after 60 seconds of training; no Eval AUC. The installed XGBoost also warns that `booster="dart"` is deprecated in favor of dropout parameters on the tree booster. Discard.

## 79. Shorter dropout run — planned

**Follow-up.** Use 400 trees at learning rate 0.05 and keep light dropout via `rate_drop` and `skip_drop` on the default tree booster. The nominal learning-rate sum matches the 800-tree baseline, and halving the rounds should fit the training limit. This tests the regularization idea without a timeout or deprecated booster setting.

Result: `e986d16` also timed out after 60 seconds of training; no Eval AUC. Discard. Dropout is impractical under this harness limit.

## 80. Small minimum split gain — planned

**Follow-up.** Add `gamma=0.1` to the current `min_child_weight=0.5` model. [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/release_1.7.0/tutorials/param_tuning.html) treats these as complementary controls on tree complexity. Lower child weight helped finer effects, but a small split-gain threshold might suppress noisy branches without losing the broad benefit. The earlier `gamma=1` test used a different model and was nearly tied.

Result: Eval AUC 0.7615 at `ce56a19`, tied with extra complexity. Discard.

### Synthesis after 80 experiments

Removing standalone day of month was the sole keeper in the last ten runs: AUC rose to 0.7615, and evaluation became faster. Month and gamma changes each only tied or added 0.0001 with extra complexity. Cross-fitted date and origin-day label rates underperformed native categorical splitting; approximate trees trained slower and underperformed; dropout exceeded the one-minute training limit at both 800 and 400 rounds. [XGBoost's tuning guide](https://xgboost.readthedocs.io/en/release_1.7.0/tutorials/param_tuning.html) groups depth, child weight, split gain, and sampling as complexity controls; we have already covered much of that space. The next useful tests should focus on small, low-cost feature ablations or representations that let the model share temporal patterns across dates.

## 81. Restore weekday without day-of-month — planned

**Follow-up.** Add categorical `DayOfWeek` to the simplified feature set. Weekday was previously redundant alongside day of month and date; after removing day of month, it may provide recurring operational patterns across dates. [Air-travel delay feature research](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) identifies weekday as a plausible temporal driver. Keep only if the gain exceeds its added complexity.

Result: Eval AUC 0.7611 at `d0b0039`, down 0.0004 and slower evaluation. Discard.

## 82. Remove destination predictor — planned

**Ablation/simplification.** Departure delay should depend most directly on origin operations and scheduled time, though destination restrictions may also affect departures. Remove `Dest` to measure its actual contribution in the current model. A near-tie would favor a smaller, faster model.

Result: Eval AUC 0.7543 at `202e399`, down 0.0072. Discard. Destination conditions or route structure carry substantial predictive signal.

## 83. Remove distance predictor — planned

**Ablation/simplification.** Origin and destination together partly determine flight length, so `Distance` might be redundant. Remove it to test whether the model needs the explicit continuous measure, while retaining both airport categories. A near-tie would reduce the feature set and make evaluation cheaper.

Result: Eval AUC 0.7592 at `a31a120`, down 0.0023. Discard. Explicit flight length adds information beyond the airport categories.

## 84. Favor exact date during column sampling — planned

**Follow-up.** The exact-date feature produced the biggest gain in this study, but `colsample_bytree=0.8` excludes some columns on each tree. Assign twice the sampling weight to `DateCategory`, keeping the number of sampled columns unchanged. [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) supports `feature_weights` for this purpose. This may keep date context in more trees while preserving ensemble diversity.

Result: Eval AUC 0.7610 at `5ca184e`, down 0.0005. Discard. Overrepresenting date reduced the useful diversity from column sampling.

## 85. Lower date sampling weight — planned

**Follow-up.** Give `DateCategory` half the sampling weight of the other predictors. The previous test suggests that trees using the non-date predictors independently may be useful; this tests the other side of the bracket while keeping the same number of columns per tree. A substantial loss would confirm the default uniform weighting is appropriate.

Result: Eval AUC 0.7577 at `206121d`, down 0.0038. Discard. Uniform feature sampling is best of the tested weights.

## 86. Slightly stronger row sampling on lean model — planned

**Follow-up.** Lower `subsample` from 0.975 to 0.95 after removing day of month. The earlier bracket found 0.975 ahead by only 0.0002 with the larger feature set; a leaner model may benefit from slightly more row diversity while the 800 trees average out sampling noise.

Result: Eval AUC 0.7605 at `79f9aa6`, down 0.0010. Discard. The 0.975 row fraction remains better.

## 87. Tighter category candidate cap on lean model — planned

**Follow-up.** Lower `max_cat_threshold` from 192 to 160 after removing day of month. This caps category candidates considered per partition, acting as a mild constraint on the high-cardinality date and airport features. The earlier setting scored 0.0003 below 192 with the larger feature set; this checks the interaction with the leaner model.

Result: Eval AUC 0.7612 at `6103369`, down 0.0003. Discard.

## 88. Cross-fitted origin delay rate — planned

**Exploration.** Add a smoothed origin-airport delay rate, with a deterministic five-fold exclusion for every row, alongside the categorical origin code. Origin had a substantial effect in the ablations, and grouping all dates at an airport gives far more observations than the failed origin-day rate. [Scikit-learn's cross-fitting example](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html) explains why training rows should be encoded from other folds. The lookup remains fixed from `train.csv` and row-local during preparation.

Result: Eval AUC 0.7607 at `136247c`, down 0.0008 and ten seconds slower evaluation. Discard. Native categorical handling remains more effective for origin.

## 89. Categorical distance bands — planned

**Exploration.** Add 250-mile categorical bands alongside raw `Distance`. The distance ablation showed meaningful signal, and [aviation delay research](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057) includes flight distance among factors; bands could let one categorical split group nonadjacent flight-length regimes. Keep only if the gain justifies the added feature.

Result: Eval AUC 0.7608 at `ac07ac5`, down 0.0007 and slower evaluation. Discard. Raw distance was enough.

## 90. Two-tree boosted forest — planned

**Exploration.** Use `num_parallel_tree=2` for 400 rounds at learning rate 0.05, keeping the total tree count and nominal learning-rate sum comparable to the 800-round single-tree model. [XGBoost's random-forest tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) describes boosting a small forest each round. Two independently sampled trees may stabilize updates and improve generalization while staying within the training limit.

Result: Eval AUC 0.7608 at `09a0454`, down 0.0007. Discard.

### Synthesis after 90 experiments

The best remains `b927226` at 0.7615. In the last ten runs, weekday, category bands, local target encodings, altered feature weights, row sampling, and a two-tree boosted forest all scored lower; destination and distance ablations showed both remain necessary. The current six predictors appear to capture most of the signal available from these columns. Recent changes are mostly within 0.001, so a new structural constraint is more informative than another nearby numeric setting. [XGBoost documents monotonic constraints](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html), and [airline delay-propagation research](https://arxiv.org/abs/1304.2528) studies delay accumulation through the day.

## 91. Monotonic scheduled departure time — planned

**Exploration.** Constrain predicted delay risk to increase as scheduled departure time increases, holding other predictors fixed. This encodes within-day delay propagation and may reduce noisy time splits while retaining date, carrier, airport, and distance interactions. Overnight schedules and airport-specific patterns may violate the assumption, so the evaluation will decide.

Result: Eval AUC 0.7583 at `3d749b1`, down 0.0032. Discard. A globally monotonic time effect is too restrictive for these schedules.

## 92. Shallower trees on lean model — planned

**Ablation/simplification.** Lower `max_depth` from 6 to 5 after removing the standalone day-of-month feature. Earlier depth five trailed depth six with a larger feature set; the leaner representation may need less interaction capacity. A tied score would produce a smaller model.

Result: Eval AUC 0.7592 at `8fb42a6`, down 0.0023. Discard. Depth six is needed even without day of month.

## 93. Intermediate finer histogram bins — planned

**Follow-up.** Raise `max_bin` from 1024 to 1536. A prior 2048-bin test was slightly worse, but 1024 had substantially improved over 512; this intermediate setting may sharpen scheduled-time and distance thresholds without the full noise of 2048 bins. Keep only for a meaningful AUC gain.

Result: Eval AUC 0.7611 at `54cda5b`, down 0.0004. Discard. The 1024-bin setting remains best.

## 94. Nine hundred boosting rounds — planned

**Follow-up.** Increase boosting from 800 to 900 rounds at the same learning rate. An earlier 1000-round model declined, but the best point may be between 800 and 1000 after removing day of month. The extra trees increase model size, so a very small gain would not be worth keeping.

Result: Eval AUC 0.7618 at `8eb7b32`, up 0.0003 over the 800-tree model with unchanged evaluation time. Keep; the modest 12.5% tree increase is one parameter change.

## 95. Eight hundred fifty rounds — planned

**Follow-up.** Test 850 rounds between the prior 800-tree 0.7615 model and the new 900-tree 0.7618 model. If it matches 900, prefer the smaller ensemble; if the gain continues toward 900, keep the new best.

Result: Eval AUC 0.7616 at `ede5b04`, down 0.0002 from 900. Discard.

## 96. Nine hundred fifty rounds — planned

**Follow-up.** Test 950 rounds on the other side of the new 900-tree best. The earlier 1000-round result used the larger feature set, so it does not settle whether the leaner representation benefits from more training. An improvement would refine the optimum; a decline would bracket it near 900.

Result: Eval AUC 0.7618 at `0d67fd7`, tied with 900 but slower training and a larger artifact. Discard under the simplicity criterion.

## 97. More category candidates with longer boosting — planned

**Follow-up.** Raise `max_cat_threshold` from 192 to 224 on the new 900-round model. This may allow finer partitions of high-cardinality date and airport categories after the longer boosting sequence. A previous 224 test tied 192 with the old feature set, so keep only for a clear improvement.

Result: Eval AUC 0.7618 at `5c081f1`, tied with an extra setting change. Discard.

## 98. Stronger column sampling at 900 rounds — planned

**Follow-up.** Lower `colsample_bytree` from 0.8 to 0.75 on the 900-tree model. Extra boosting rounds may average the additional feature-sampling variance while reducing overfit of date/airport interactions. The prior 0.9 test hurt, so the lower side remains untested on this lean representation.

Result: Eval AUC 0.7618 at `5659eea`, tied without a simplification. Discard.

## 99. Intermediate child-weight constraint — planned

**Follow-up.** Set `min_child_weight=0.75` between the prior best 0.5 and the default 1.0. The longer 900-round model may benefit from slightly stronger restraint on small leaves while retaining most of the finer effects that 0.5 unlocked. This is a direct bracket rather than a new feature.

Result: Eval AUC 0.7616 at `5fed552`, down 0.0002. Discard. The smaller 0.5 child weight remains best.

## 100. Slightly fewer histogram bins — planned

**Follow-up.** Try `max_bin=768` with the 900-tree model. [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) explains that more bins improve split precision at a compute cost. The earlier 512-bin setting lost accuracy and 1536 also declined, so this checks whether a moderate reduction from 1024 can retain or improve AUC while reducing quantization work.

Result: Eval AUC 0.7618 at `a1907b5`, tied with no runtime advantage. Discard.

### Synthesis after 100 experiments

The lean six-feature model improved from 0.7615 to 0.7618 by raising boosting rounds from 800 to 900. The bracketing 850-round model was lower; 950 tied at larger size. Tweaks to category candidate caps, feature sampling, child weight, and bin counts did not improve it. The consistent finding is that the exact-date category with origin, destination, carrier, scheduled time, and distance captures useful interactions; removing destination, distance, or depth hurts. Cross-fitted target rates and extra categorical bands added complexity without AUC gains. The next step is a final check at 1000 rounds on the lean model, then leave the 900-round model if it does not clearly improve.

## 101. One thousand rounds on lean model — planned

**Follow-up.** Test 1000 boosting rounds at the same learning rate. The 950-round run tied 900; this checks whether the AUC can rise again with longer boosting after day-of-month removal. The added artifact size means a tie should be discarded.

Result: Eval AUC 0.7617 at `bc8cdc8`, down 0.0001 and slower. Discard. The best boosting length is 900 rounds among the tested settings.

## Final summary

The best kept commit is `8eb7b32`, Eval AUC **0.7618**, versus the starter baseline 0.7203 (gain 0.0415). It uses the exact calendar date as a categorical feature alongside scheduled departure time, distance, carrier, origin, and destination; 900 depth-six trees at learning rate 0.025; 1024 histogram bins; category threshold 192; row sampling 0.975; column sampling 0.8; and minimum child weight 0.5. The final branch points to this commit.

The largest improvement came from the exact-date category. Finer histogram bins, smaller learning rate with more rounds, moderate sampling, depth six, and lower child weight added incremental gains. Removing standalone month, weekday, and day-of-month predictors preserved or improved accuracy while simplifying preparation. High-cardinality route/carrier combinations, cross-fitted delay-rate lookups, extra time/distance bands, approximate trees, altered feature weights, monotonic time, and boosted forests did not help. DART-style dropout exceeded the 60-second training limit.

If another run is authorized, a targeted test of date/airport interaction constraints or a genuinely new permitted schedule feature would be more informative than retuning the narrow hyperparameter ranges that plateaued here. `results.tsv` records all 101 experiments after the baseline; the final training code is committed, and the results log remains untracked for archiving.
