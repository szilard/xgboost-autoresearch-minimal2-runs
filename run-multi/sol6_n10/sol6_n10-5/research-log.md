# Research log — sep29

## Baseline — 92e43e6

Unchanged starter: 30 trees, depth 6, learning rate 0.1, native categorical features. Eval AUC 0.7203; run 31.7 s. The 200K training rows are balanced and have only eight predictors. Every feature must have identical meaning for one-row and batch preparation.

## Experiment 1 — more boosting rounds (exploration)

Hypothesis: 30 trees at learning rate 0.1 are underfitting. Increase to 300 trees while holding other settings fixed. [XGBoost's tuning guide](https://xgboost.readthedocs.io/en/release_2.0.0/tutorials/param_tuning.html) recommends more rounds when using a smaller step size; [parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) describes this tradeoff. The AUC change will show whether the starter needs more capacity.

Result: commit 8dae695, AUC 0.7342 (+0.0139), keep. 32.8 s run. Clearly more boosting was needed.

## Experiment 2 — 600 rounds (follow-up)

Hypothesis: the 300-round model may still be underfitting. Double the rounds at the same learning rate and depth to test where additional capacity saturates. Based on the strong experiment 1 gain and XGBoost's step-size guidance above.

Result: commit d2de493, AUC 0.7299 (-0.0043 versus best), discard. More rounds at this step size overfit.

## Experiment 3 — 200 rounds (follow-up)

Hypothesis: the optimum may lie below 300 rounds because 600 was worse. Test 200 with all else fixed, bracketing the current best from below.

Result: commit 6169722, AUC 0.7345 (+0.0003), keep. Model is smaller as well. 200 seems near a useful range.

## Experiment 4 — 150 rounds (follow-up)

Hypothesis: because reducing from 300 to 200 helped slightly, reducing to 150 might regularize further while retaining most signal. This tests the lower edge of the likely useful range; 30 rounds was much worse.

Result: commit 7b3aec4, AUC 0.7332 (-0.0013), discard. 200 rounds remains best among 30, 150, 200, 300, 600 at depth 6.

## Experiment 5 — depth 4 (exploration)

Hypothesis: shallower trees may generalize better at 200 rounds by limiting high-order interactions. [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/release_2.0.0/tutorials/param_tuning.html) identifies max depth as a principal complexity control. Try depth 4 instead of 6 with all else fixed.

Result: commit 36b4a4b, AUC 0.7317 (-0.0028), discard. Shallower trees lose useful interactions.

## Experiment 6 — depth 8 (exploration)

Hypothesis: deeper trees may better capture interactions among airport, carrier, calendar and time while 200 rounds limit overfitting. Test depth 8 against depth 6. The opposing depth-4 result motivates checking this side of the complexity tradeoff.

Result: commit f02f697, AUC 0.7323 (-0.0022), discard. Depth 6 remains the best among 4, 6, 8.

## Experiment 7 — scheduled departure minute (exploration)

Hypothesis: the minute within an hour has recurring schedule patterns across the day that a single ordered HHMM field cannot efficiently share between hours. Add `CRSDepTime % 100` as one row-local feature. A [flight-delay feature engineering study](https://www.mdpi.com/2079-9292/13/24/4910) considers hour and minute extraction from scheduled time.

Result: commit aeeb23e, AUC 0.7344 (-0.0001); evaluation rose to 32.4 s. Discard: added complexity without gain.

## Experiment 8 — simplify categorical conversion (ablation/simplification)

Hypothesis: `pd.Categorical(values, categories=cat_levels[col])` already maps unknown values to missing, so the explicit per-row `isin`/`where` work is redundant. [pandas API documentation](https://pandas.pydata.org/docs/reference/api/pandas.Categorical.html) confirms this behavior. Remove it; expect identical AUC and faster row-by-row evaluation.

Result: commit f7fbc21, identical AUC 0.7345; eval time 20.9 s versus about 30.6 s. Keep: simpler and much faster.

## Experiment 9 — day of year (exploration)

Hypothesis: a continuous calendar index will let trees find season and date-specific disruptions more efficiently than separate categorical month and day fields. Compute day of year per row from fixed calendar lookups. [Flight-delay research](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0335141) considers day of year among relevant time features. No target information is used.

Result: commit 5d62e9f, AUC 0.7385 (+0.0040), keep. The date representation adds substantial signal.

## Experiment 10 — one-hot splits for small categoricals (exploration)

Hypothesis: isolating individual month, day, weekday or carrier values may work better than grouped category partitions now that day of year captures continuous calendar trends. Set `max_cat_to_onehot=32`; airports remain partitioned. [XGBoost categorical documentation](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) explains the threshold and split strategies.

Result: commit 2e3ed9d, AUC 0.7306 (-0.0079), discard. Partition splits suit these categorical variables better than one-hot splits.

## Synthesis after 10 experiments

Best is 0.7385 at 5d62e9f, up from baseline 0.7203. The main gains came from 200 rather than 30 trees and a continuous day-of-year feature. The model is sensitive to excess capacity: 600 trees and both depth 4 and 8 lost AUC versus 200 trees at depth 6. Minute-of-hour did not help, and switching small categoricals to one-hot splits harmed AUC. The redundant category-membership check could be removed with identical AUC and about 10 seconds less evaluation time. Working theory: this task needs calendar detail and moderate interaction capacity; native partition-based categorical splits are useful. Next explore route-specific information and regularization. New research: [an airline-route feature study](https://thesai.org/Publications/ViewPaper?Code=IJACSA&Issue=8&SerialNo=82&Volume=17) reports route-related signals; [XGBoost categorical documentation](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) explains partition splits for high-cardinality categories.

## Experiment 11 — origin-destination route (exploration)

Hypothesis: delay risk may depend on an airport pair beyond origin and destination separately. Add the route as a native categorical feature with levels fitted on train (4,290 distinct routes); compute each route from its row alone. The route study above motivates trying a direct pair interaction. Watch training and row-scoring time because this is high cardinality.

Result: commit 79ec58f, AUC 0.7125 (-0.0260); eval 38.4 s. Discard. The raw high-cardinality route category likely overfits and can be unknown at evaluation time; pandas warned on unseen routes. Seek smoother interactions or regularization instead.

## Experiment 12 — larger minimum child weight (exploration)

Hypothesis: suppressing splits with few supporting examples may improve generalization, especially for sparse airports and daily calendar conditions. Set `min_child_weight=10` on the best model. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) define this as a lower bound on child Hessian weight, making trees more conservative.

Result: commit 471eef6, AUC 0.7376 (-0.0009), discard. This degree of additional leaf regularization does not help.

## Experiment 13 — finer histogram bins (follow-up)

Hypothesis: default histogram binning (256 bins) may blur a 365-valued day-of-year feature. Raise `max_bin` to 512 to allow finer date splits. [XGBoost parameters](https://xgboost.readthedocs.io/en/latest/parameter.html) say higher max_bin increases split fidelity at a computation cost. All other settings revert to the best model.

Result: commit fc7cc57, AUC 0.7370 (-0.0015), discard. Finer bins did not improve the date signal and may allow too much fit to noise.

## Experiment 14 — categorical day of year (follow-up)

Hypothesis: numeric day of year captures seasons but a categorical copy can group noncontiguous dates with similar conditions. There are at most 365 calendar values, with more support per category than the route feature. Add a row-local categorical copy while retaining the numeric feature. [XGBoost categorical guide](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) describes partition splits.

Result: commit 57e7de1, AUC 0.7511 (+0.0126), keep. Grouping dates irrespective of adjacency is a major signal. Evaluation 28.4 s remains well within limits.

## Experiment 15 — remove numeric day of year (ablation/simplification)

Hypothesis: the categorical day representation now captures the date effect, so the numeric copy may be redundant or add noisy splits. Compute the same row-local calendar day for the categorical feature but remove the numeric predictor. Compare against 0.7511; keep if equal with simpler feature set or better.

Result: commit b2761f0, AUC 0.7512 (+0.0001). Keep: one fewer predictor with no loss. The categorical date appears to carry essentially all useful date signal.

## Experiment 16 — more categorical split candidates (follow-up)

Hypothesis: the day-of-year category has 365 levels, and the default cap on category candidates may omit useful date groups. Set `max_cat_threshold=128` so partition-based splits can consider more categories. [XGBoost parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html) describes this parameter as a limit for categorical partitions. Watch for overfitting and runtime.

Result: commit 607d5bc, AUC 0.7534 (+0.0022), keep. More categorical candidates help. Model gain analysis on the prior best ranked scheduled departure time first, then day-of-year category, carrier, airports and distance; month, day-of-month and weekday were lower. This guides later ablations but Eval AUC remains the keep/discard metric.

## Experiment 17 — 256 categorical candidates (follow-up)

Hypothesis: the 128-candidate improvement may continue toward the 365 date levels. Raise `max_cat_threshold` to 256 with everything else fixed. This directly tests whether the gain is still rising or becomes overfit.

Result: commit 198a368, AUC 0.7530 (-0.0004), discard. The 128 setting is better and less expansive.

## Experiment 18 — ablate redundant month and day predictors (ablation/simplification)

Hypothesis: `DayOfYearCat` uniquely determines month and day-of-month, so retaining those inputs as separate model columns may waste splits. Model gain analysis also ranked them low. Remove Month and DayofMonth from categorical predictor list while still reading them to build day of year. Compare AUC and runtime against 0.7534.

Result: commit 72b7a61, AUC 0.7533 (-0.0001), eval 22.7 s versus 27.4 s. Keep as essentially equal with two fewer predictors and faster row scoring.

## Experiment 19 — ablate weekday (ablation/simplification)

Hypothesis: weekday contributed very little model gain and may be redundant given exact date. Remove DayOfWeek from predictors, retaining date, carrier, airports, distance and time. Test whether the simpler model maintains AUC.

Result: commit 4108752, identical AUC 0.7533 and eval 20.2 s versus 22.7 s. Keep: fewer predictors and faster evaluation.

## Experiment 20 — categorical departure hour (exploration)

Hypothesis: delay risk may have non-monotone hour patterns that a numeric HHMM split uses many trees to express. Add a row-local categorical hour (`CRSDepTime // 100`) while keeping numeric scheduled time. [Flight-delay feature research](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0335141) uses departure-hour bins among its time variables.

Result: commit 67973bd, identical AUC 0.7533 but slower evaluation and extra feature; discard.

## Synthesis after 20 experiments

Highest observed AUC is 0.7534 at 607d5bc. The current kept commit 4108752 scores 0.7533 with fewer calendar predictors and evaluation near 20 s, so it wins on simplicity. A categorical day-of-year feature added roughly 0.013 AUC, and increasing categorical partition candidates to 128 added another 0.002. Broadening to 256 reduced AUC. Month, day-of-month and weekday are redundant once exact date is represented. A departure-hour category, a raw route category, stronger child-weight regularization and finer numeric bins did not help. Working theory: the model benefits from grouping specific calendar days and maintaining a moderate tree budget; extra sparse interactions overfit. Next test learning-rate/round combinations and other regularization. Research refresh: [XGBoost tuning notes](https://xgboost.readthedocs.io/en/release_2.0.0/tutorials/param_tuning.html) describe shrinkage with more rounds; [XGBoost early stopping docs](https://xgboost.readthedocs.io/en/stable/python/python_intro.html) suggest a possible later way to choose rounds from train-only validation; [monotonic constraints docs](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html) offer an optional time-of-day prior but warn of shallower trees with histogram training.

## Experiment 21 — smaller learning rate with more rounds (exploration)

Hypothesis: 0.05 learning rate with 400 trees may fit smoother than 0.1 with 200 while preserving similar total boosting strength. [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/release_2.0.0/tutorials/param_tuning.html) recommends increasing rounds when reducing step size. Use the current simpler feature set.

Result: commit 033052e, AUC 0.7558 (+0.0025), keep. Smoother boosting helps the categorical-date model; training still only 2.4 s.

## Experiment 22 — further shrinkage (follow-up)

Hypothesis: 0.025 learning rate with 800 trees might improve stability further at roughly the same cumulative step size. Double rounds and halve eta relative to experiment 21. This tests whether the gain is from smaller individual updates or has saturated.

Result: commit 80c423c, AUC 0.7571 (+0.0013), keep. Training 4.8 s, artifact 32.6 MB. The gain from smoother boosting continues but is diminishing.

## Experiment 23 — 1,600 finer rounds (follow-up)

Hypothesis: halving eta once more to 0.0125 with 1,600 trees could continue improving generalization. This holds approximate cumulative step size fixed, but doubles model size. Keep only if the AUC gain justifies that cost.

Result: commit d1383c3, AUC 0.7567 (-0.0004), 65.4 MB artifact and 9.5 s training. Discard. Best observed shrinkage/round combination is 0.025/800.

## Experiment 24 — row subsampling (exploration)

Hypothesis: 80% row subsampling per tree may reduce correlated fitting to noise while preserving enough data per tree. Set `subsample=0.8` with the best 800-tree configuration. [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/release_2.0.0/tutorials/param_tuning.html) recommends subsampling as an overfitting control.

Result: commit 94cde4f, AUC 0.7542 (-0.0029), discard. Row subsampling weakens this model.

## Experiment 25 — column subsampling (exploration)

Hypothesis: making each tree use about 80% of the six predictors could reduce dependence on any one field while keeping all rows. Set `colsample_bytree=0.8` with row sampling restored to 1. This differs from experiment 24 by sampling features rather than observations; [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) document the distinction.

Result: commit 0113eb6, AUC 0.7598 (+0.0027), keep. Feature sampling helps despite row sampling hurting; artifact decreased to 28.3 MB.

## Experiment 26 — stronger feature sampling (follow-up)

Hypothesis: the 0.8 gain may continue with more diverse trees. Set `colsample_bytree=0.6`, reducing features available to each tree further. If AUC falls, 0.8 is a better balance between variety and information.

Result: commit 71f229c, AUC 0.7597 (-0.0001), discard. The smaller artifact is not enough to outweigh a lower score with no code simplification.

## Experiment 27 — milder feature sampling (follow-up)

Hypothesis: allowing roughly one more predictor per tree than the 0.8 setting may improve split quality while still creating some variety. Test `colsample_bytree=0.9`. Together with 0.6 and 1.0 results, this brackets the useful sampling range.

Result: commit 9075122, AUC 0.7577 (-0.0021), discard. The 0.8 setting is best among 0.6, 0.8, 0.9 and 1.0.

## Experiment 28 — sample features per split (exploration)

Hypothesis: reselecting features at every node may give trees more varied interactions than one fixed subset per tree. Replace `colsample_bytree=0.8` with `colsample_bynode=0.8`, leaving all other settings fixed. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) distinguish the tree-level and node-level sampling.

Result: commit 7236be2, AUC 0.7575 (-0.0023), discard. Tree-level sampling works better than sampling at every split.

## Experiment 29 — depth 5 with date category (exploration)

Hypothesis: the enriched date feature and 800 smoother rounds may need less depth than the earlier 200-round starter. Test depth 5 rather than 6 with tree-level feature sampling fixed at 0.8. Earlier depth-4 failure used a different feature set and learning rate.

Result: commit 99a4493, AUC 0.7560 (-0.0038), discard. Depth 6 remains better in this richer model.

## Experiment 30 — depth 7 with date category (exploration)

Hypothesis: one extra level may capture interactions among date, airport, carrier and scheduled time that depth 6 misses, with feature sampling and small eta limiting overfit. Test depth 7 on the current best. Earlier depth 8 failed on the simpler baseline model.

Result: commit f63ee06, AUC 0.7604 (+0.0006), keep. Artifact increased to 53.3 MB, but training was 6.7 s and evaluation 20.7 s, within limits. This richer model can benefit from more interaction depth.

## Synthesis after 30 experiments

Best AUC is 0.7604 at f63ee06, up 0.0401 from baseline. The most effective ideas are categorical day of year, a 128-category partition threshold, small boosting steps (0.025/800), and sampling predictors per tree at 0.8. Day-of-year numerically, redundant month/day/weekday predictors, and categorical departure hour added little or no value. Raw route categories overfit badly; row subsampling and per-node feature sampling reduced AUC. Depth 7 now slightly beats 6, while depth 5 is substantially worse. Current theory: date-specific conditions interact with airport, carrier and time, and gentle boosting plus feature diversity help learn them. Fresh research: [XGBoost tree-method docs](https://xgboost.readthedocs.io/en/release_3.3.0/treemethod.html) note that `approx` may improve accuracy on objectives with non-constant Hessians; [parameter docs](https://xgboost.readthedocs.io/en/latest/parameter.html) describe leafwise growth and regularization as options. These suggest future experiments beyond depth alone.

## Experiment 31 — depth 8 on the enriched model (follow-up)

Hypothesis: since depth 7 improved on depth 6 after adding date categories and column sampling, depth 8 may capture more useful interactions. Test one additional level; stop exploring depth if it worsens AUC or makes the model too large for a marginal gain.

Result: commit a7acd5e, AUC 0.7599 (-0.0005), 98.9 MB artifact. Discard. Depth 7 is best among 5, 6, 7, 8 in this model.

## Experiment 32 — leafwise growth with 64 leaves (exploration)

Hypothesis: `lossguide` growth can place depth where gradient loss reduction is largest rather than expanding breadth-first, potentially fitting date-airport-time interactions efficiently. Set `grow_policy='lossguide'`, `max_leaves=64`, retaining max depth 7 and the rest of the best configuration. [XGBoost parameter docs](https://xgboost.readthedocs.io/en/latest/parameter.html) describe these controls.

Result: commit 2adefff, AUC 0.7599 (-0.0005), artifact 29.9 MB versus 53.3 MB. Discard on AUC, though the size reduction suggests a slightly higher leaf cap may be useful.

## Experiment 33 — leafwise growth with 96 leaves (follow-up)

Hypothesis: 64 leaves constrained the tree too much; 96 may recover AUC while retaining a smaller model than unrestricted depth-7 growth. Test `lossguide` with `max_leaves=96` on the best base.

Result: commit d0c10f7, AUC 0.7607 (+0.0003), artifact 43.0 MB versus 53.3 MB at the prior best. Keep for higher AUC and lower size.

## Experiment 34 — stronger L2 leaf regularization (exploration)

Hypothesis: leafwise growth may benefit from more conservative leaf values, especially where date-airport combinations are sparse. Set `reg_lambda=5` (default is 1) on the current best. [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/latest/parameter.html) describes lambda as L2 regularization on leaf weights.

Result: commit 6d7b80c, AUC 0.7612 (+0.0005), artifact 41.9 MB. Keep: extra L2 improves and slightly shrinks the model.

## Experiment 35 — further L2 regularization (follow-up)

Hypothesis: the lambda-5 gain may continue at 10; if it reverses, the useful regularization strength is bracketed. Set `reg_lambda=10` with all other settings unchanged.

Result: commit 3cab727, AUC 0.7615 (+0.0003), 41.3 MB artifact. Keep. Improvement continues but is smaller.

## Experiment 36 — L2 saturation check (follow-up)

Hypothesis: lambda 20 may continue smoothing high-variance leaf values, or become too conservative. Test `reg_lambda=20` once to locate saturation, then switch to other hypotheses.

Result: commit 652f857, AUC 0.7613 (-0.0002), discard. L2 benefit saturates near lambda 10.

## Experiment 37 — L1 leaf regularization (exploration)

Hypothesis: L1 shrinkage can suppress weak leaf contributions in a different way from L2, potentially improving the sparse date-airport interactions. Add `reg_alpha=1` while retaining the best lambda 10. [XGBoost parameter docs](https://xgboost.readthedocs.io/en/latest/parameter.html) define alpha as L1 regularization on weights.

Result: commit cf03e16, AUC 0.7623 (+0.0008), keep. L1 provides a distinct useful regularization effect.

## Experiment 38 — stronger L1 shrinkage (follow-up)

Hypothesis: alpha 2 may suppress more weak leaves and improve generalization, or overshrink real signals. Double `reg_alpha` with all other settings fixed, bracketing the useful level.

Result: commit a96e345, AUC 0.7641 (+0.0018), 38.5 MB artifact, keep. More L1 regularization helps substantially; test a stronger value next.

## Experiment 39 — alpha 4 (follow-up)

Hypothesis: alpha 4 may continue suppressing noisy leaf adjustments, though too much could underfit. Double again with the same tree structure and lambda to locate the useful range.

Result: commit 49c2871, AUC 0.7654 (+0.0013), 34.1 MB artifact, keep. L1 shrinkage is still beneficial and reduces model size.

## Experiment 40 — alpha 8 (follow-up)

Hypothesis: stronger L1 may continue to remove weak leaf effects, but the gain should eventually peak as real effects are removed. Test alpha 8 at the same lambda 10 and tree settings, then synthesize the first 40 experiments.

Result: commit 75bcb18, AUC 0.7611 (-0.0043), discard. Alpha 4 is the best of 0, 1, 2, 4 and 8.

## Synthesis after 40 experiments

Best AUC is 0.7654 at 49c2871, a +0.0451 gain from the baseline. Categorical day of year was the largest feature change. The model works best with 800 small updates at eta 0.025, 80% predictor sampling per tree, depth 7, leafwise growth capped at 96 leaves, lambda 10 and alpha 4. L1 shrinkage was especially useful and reduced artifact size; alpha 8 overcorrected. Raw route categories and row sampling were poor. Current theory: exact calendar effects and schedule/airport interactions are real, but many weak leaves should be suppressed. Fresh research: [XGBoost tree-method docs](https://xgboost.readthedocs.io/en/release_3.3.0/treemethod.html) say `approx` can sometimes improve binary objectives using Hessian-weighted sketches; [XGBoost sklearn guidance](https://xgboost.readthedocs.io/en/release_2.0.0/python/sklearn_estimator.html) describes train-only early stopping. These are different directions to test next.

## Experiment 41 — approximate tree method (exploration)

Hypothesis: for binary logistic loss, the `approx` method's changing Hessian-weighted split candidates may improve the trained trees compared with histogram cuts, at a training-time cost. Set `tree_method='approx'` on the best model. [XGBoost tree methods](https://xgboost.readthedocs.io/en/release_3.3.0/treemethod.html) support categorical data for `approx` and note this potential benefit.

Result: commit 922c318, AUC 0.7657 (+0.0003), keep. Training 20.5 s versus around 7 s with hist, still below the 60 s limit; artifact 34.2 MB.

## Experiment 42 — 1,000 rounds with approx (follow-up)

Hypothesis: the combination of approximate splits, L1/L2 regularization and leafwise growth may support more rounds than the 800 currently used. Raise to 1,000 at fixed eta 0.025. If AUC falls, 800 is a better stopping point for this configuration.

Result: commit 8ba2769, AUC 0.7669 (+0.0012), keep. Training 24.0 s, still comfortably within limit. The newer model was undertrained at 800 rounds.

## Experiment 43 — 1,200 rounds with approx (follow-up)

Hypothesis: the 800-to-1,000 gain suggests the current regularized model can still benefit from more boosting. Raise to 1,200 at the same eta, watching AUC and the 60 s training limit.

Result: commit 154aea8, AUC 0.7675 (+0.0006), keep. Training 27.6 s. Gains continue but are diminishing.

## Experiment 44 — 1,500 rounds with approx (follow-up)

Hypothesis: boosting may keep improving under the strong L1/L2 regularization, though gains are shrinking. Test 1,500 at eta 0.025 to find saturation; estimated training remains below 60 s.

Result: commit 28c9bad, AUC 0.7678 (+0.0003), keep. Training 35.5 s, artifact 58.8 MB. Improvement is marginal but no code complexity was added.

## Experiment 45 — 1,800 rounds with approx (follow-up)

Hypothesis: some signal may remain after 1,500 rounds, but the improvement is dwindling. Test 1,800 at the same eta once more; estimated training is below 60 s. If gain disappears or timeout approaches, stop increasing rounds.

Result: commit 08f66d8, same AUC 0.7678 but 69.1 MB artifact and 42.8 s training; discard on simplicity/runtime. 1,500 is the best practical round count seen.

## Experiment 46 — train-only early stopping (exploration)

Hypothesis: a 10% split from train.csv can choose a more suitable iteration than fixed 1,500 rounds for this model. Set 1,700 maximum rounds with AUC early stopping patience 50, fit on the remaining 90%, and let the unchanged harness Eval AUC decide whether to keep. [XGBoost sklearn guidance](https://xgboost.readthedocs.io/en/release_2.0.0/python/sklearn_estimator.html) describes validation splits and best-iteration prediction. No retraining or alternate result metric is used.

Result: commit 016b4ef, internal best iteration 1316, harness AUC 0.7660 (-0.0018), discard. Training on 90% of train.csv appears to cost more than adaptive round choice gains. No retraining was performed.

## Experiment 47 — one-hot carrier only (exploration)

Hypothesis: isolating individual carrier identities may work better than partitioning carrier categories, while preserving partition splits for high-cardinality airports and dates. Set `max_cat_to_onehot=21`; only `UniqueCarrier` has fewer than 21 levels. Earlier threshold-32 failure changed multiple categorical columns before the calendar feature was added, so this is a distinct test. [XGBoost categorical guide](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) explains the threshold behavior.

Result: commit 39b85c8, AUC 0.7659 (-0.0019), discard. Carrier partitioning remains better.

Three consecutive discards prompted a research pause. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) suggest `gamma` as a distinct split-loss filter not yet tested; [flight-delay feature research](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) emphasizes carrier-specific schedule patterns and available pre-flight timing, though external weather and row counts are outside this setup. Test split regularization first, then consider safe row-local schedule features.

## Experiment 48 — minimum split gain (exploration)

Hypothesis: `gamma=1` can prune weak partitions that survive L1/L2 leaf regularization, reducing overfit from specific dates and airports. [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) defines gamma as minimum loss reduction for a split. Start from the 0.7678 best.

Result: commit 52e8029, AUC 0.7607 (-0.0071), artifact fell to 20.7 MB. Discard. A penalty of 1 is far too strong for this model.

## Experiment 49 — mild split penalty (follow-up)

Hypothesis: gamma 0.1 may remove only the weakest partitions, unlike gamma 1, and improve generalization without a large loss of useful signal. Test a tenfold smaller penalty on the best model.

Result: commit de65812, AUC 0.7676 (-0.0002), discard. Even mild gamma adds no value beyond L1/L2 and leaf caps.

## Experiment 50 — time relative to origin schedule (exploration)

Hypothesis: the scheduled time relative to an airport's typical schedule may help share early/late-day patterns across origins. Fit median departure minute by Origin using only train.csv and add a per-row deviation inside `prepare()`. This uses no labels and no row counts; `prepare()` only maps a fixed lookup. [Flight-delay feature research](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) emphasizes temporal and airport characteristics; the specific deviation feature is an inference to test here.

Result: commit 975e5bf, AUC 0.7672 (-0.0006), eval time rose from about 21 to 24.9 s. Discard. The origin-relative time adds cost without meaningful signal.

## Synthesis after 50 experiments

Best AUC is 0.7678 at 28c9bad, +0.0475 over the baseline 0.7203. The latest gains came from `approx` tree construction and raising rounds from 800 to 1,500 under strong L1/L2 regularization. At 1,800 rounds the score stayed flat while time and artifact size grew. Train-only early stopping lost AUC because it reserved 10% of training rows. One-hot carrier splits, gamma, and an origin-median time deviation did not improve. Current theory: the selected date, airport, carrier, distance and time fields carry the available signal, and the model needs carefully constrained capacity to use them. Next explore safe spatial signals derived from train's route-distance graph, then revisit model constraints if useful. Fresh research: [geographic and operational airport graph study](https://www.sciencedirect.com/science/article/pii/S1000936122002436) motivates representing geographic relationships; [XGBoost interaction constraint docs](https://xgboost.readthedocs.io/en/release_2.0.0/tutorials/feature_interaction_constraint.html) suggest a later way to exclude spurious interactions.

## Experiment 51 — origin distances to anchor airports (exploration)

Hypothesis: geographic location affects weather and traffic patterns, but the model sees airport codes only as categories. Build an unlabeled airport-distance graph solely from train.csv route distances; shortest-path distances from ATL and LAX provide rough spatial coordinates for each origin. The row-local `prepare()` only maps these precomputed lookups. [Airport graph research](https://www.sciencedirect.com/science/article/pii/S1000936122002436) motivates spatial features; anchor distances are an inference adapted to the available columns.

Result: commit 9e0edae, AUC 0.7677 (-0.0001), evaluation 26.4 s versus about 21 s; discard due substantial complexity with no gain.

## Experiment 52 — restrict weak destination interactions (exploration)

Hypothesis: departure risk is chiefly a function of date, origin, carrier and departure time; distance/destination may contribute mostly as a separate route effect. Try disjoint interaction groups `[CRSDepTime, UniqueCarrier, Origin, DayOfYearCat]` and `[Distance, Dest]`, limiting spurious cross-group branches. [XGBoost interaction-constraint guide](https://xgboost.readthedocs.io/en/release_2.0.0/tutorials/feature_interaction_constraint.html) describes this regularization. If true cross-group effects are important, AUC will fall.

Result: commit d6d3bf8, AUC 0.7590 (-0.0088), discard. The disjoint grouping blocks important schedule-by-route interactions.

Plateau research after three discards: [XGBoost parameter docs](https://xgboost.readthedocs.io/en/latest/parameter.html) describe feature weights during column sampling and minimum child Hessian; [categorical guide](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) explains partition splits. The current .8 tree-level column sampling was useful, but it treats all six columns equally. Test a focused sampling change before adding more predictors.

## Experiment 53 — weighted feature sampling (exploration)

Hypothesis: with only six inputs and `colsample_bytree=0.8`, occasionally dropping both scheduled time and day-of-year may weaken trees. Give those two strongest predictors twice the sampling weight of the other four, keeping the same sampling rate. [XGBoost API docs](https://xgboost.readthedocs.io/en/release_3.3.0/python/python_api.html) define `feature_weights` as column-selection probabilities. This is a training-only parameter, and prediction still uses the full feature set.

Result: commit e74d044, AUC 0.7671 (-0.0007), discard. Equal sampling of the six features generalized better.

## Experiment 54 — smaller minimum child weight (exploration)

Hypothesis: with L1=4, L2=10 and a 96-leaf cap, the current model may already suppress noisy leaves, while the default `min_child_weight=1` blocks some small but useful date-airport patterns. Test 0.5 to allow a modest number of additional branches. The old `min_child_weight=10` loss was on a much less regularized model and tested the opposite direction. [XGBoost parameter docs](https://xgboost.readthedocs.io/en/latest/parameter.html) define this as a lower bound on child Hessian weight.

Result: commit a998e85, AUC 0.7679 (+0.0001), keep. The lower leaf-support threshold helps slightly under current L1/L2 regularization. Training remained 36.1 s.

## Experiment 55 — quarter child weight (follow-up)

Hypothesis: the gain from lowering minimum child Hessian weight from 1 to 0.5 may continue because the L1/L2 penalties can still suppress noisy leaves. Test 0.25 with all else fixed. If AUC falls, the small gain at 0.5 is likely near the useful limit.

Result: commit 34ca44c, AUC unchanged at 0.7679, but training and artifact size increased slightly. Discard; 0.5 is the simpler useful setting.

## Experiment 56 — 128 leaves under stronger regularization (follow-up)

Hypothesis: the 96-leaf cap was selected before L1=4, `approx`, 1,500 rounds, and `min_child_weight=0.5`. Those changes may make slightly wider leafwise trees useful without overfitting. Test 128 leaves with all other settings at the 0.7679 best. The earlier 64-leaf loss and 96-leaf gain motivate checking the upper side of this bracket in the changed context. [XGBoost parameters](https://xgboost.readthedocs.io/en/latest/parameter.html) describe the leaf cap for `lossguide` growth.

Result: commit aaa5a15, AUC unchanged at 0.7679 while the artifact grew from about 59 to 64 MB; discard. Capacity beyond 96 leaves adds size but no generalization.

## Experiment 57 — coarser numeric split bins (exploration)

Hypothesis: the `approx` method currently has 256 maximum bins for scheduled departure time and distance. Reducing to 128 might discourage splits on incidental minute or distance thresholds while leaving categorical date/airport partitions intact. Earlier increasing to 512 worsened a simpler `hist` model, so this tests the opposite direction on the current tree method. [XGBoost parameter docs](https://xgboost.readthedocs.io/en/latest/parameter.html) describe `max_bin` for `hist` and `approx`.

Result: commit 6d1aa20, AUC 0.7678 (-0.0001), discard. Coarser numeric cuts do not improve the best model.

Plateau research after experiments 55–57: a [flight-delay feature engineering paper](https://www.mdpi.com/2079-9292/13/24/4910) explicitly extracts week of year to capture seasonality and peak travel periods. [XGBoost categorical guide](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) explains that partition splits group levels with similar leaf responses. A coarser week category may pool adjacent dates while the existing exact-day category preserves disruptions.

## Experiment 58 — categorical week block (exploration)

Hypothesis: seven-day calendar blocks may supply a smoother seasonal signal than the exact day-of-year category alone, reducing the burden on trees to pool adjacent dates while retaining their ability to capture day-specific disruptions. Add a categorical week block computed solely from the row date, with Monday boundaries, alongside `DayOfYearCat`. The week feature idea comes from the [flight-delay temporal feature study](https://www.mdpi.com/2079-9292/13/24/4910); the exact bin calculation is adapted for this one-year dataset.

Result: commit 8056752, AUC 0.7674 (-0.0005), evaluation increased to 24.4 s; discard. The extra week grouping appears redundant with exact-day partitions.

## Experiment 59 — wider categorical partition search (follow-up)

Hypothesis: `max_cat_threshold=128` was chosen on a 200-round, less regularized histogram model. The current `approx` model with L1=4, L2=10, 1,500 rounds and `min_child_weight=0.5` may use a few more day-of-year or airport levels per partition without overfitting. Test 192, a middle value below the previously worse 256. [XGBoost categorical parameter docs](https://xgboost.readthedocs.io/en/latest/parameter.html) define the threshold as a cap on categories considered for partition splits.

Result: commit 73d0e18, AUC 0.7677 (-0.0002), discard. The extra categorical search did not translate into a better ranking.

Plateau research after five discards: [airport operations study](https://www.sciencedirect.com/science/article/pii/0191260785900688) finds strong weekday patterns that vary by airport; a [flight-delay study](https://www.sciencedirect.com/science/article/abs/pii/S0969699707000646) likewise found weekly variation. This suggests a simple pooled weekday feature, which the exact-day category may need many splits to reconstruct.

## Experiment 60 — restore weekday category (exploration)

Hypothesis: `DayOfWeek` may give the current strongly regularized model a pooled weekly pattern across the 365 exact dates, especially for airport-specific schedules. It was removed at experiment 19 with no AUC loss, but that used 200 histogram rounds before the current L1/L2, column sampling and approximate training. Add it back as a native category, with other settings fixed. The [weekday flight-delay analysis](https://www.sciencedirect.com/science/article/abs/pii/S0969699707000646) motivates this compact feature.

Result: commit 1ef3d77, AUC 0.7677 (-0.0002), slower evaluation and larger artifact; discard. Exact day-of-year appears adequate for weekly effects.

## Synthesis after 60 experiments

Best AUC is 0.7679 at a998e85, up 0.0476 from the 0.7203 baseline. Across the latest ten trials, lowering `min_child_weight` from 1 to 0.5 gave a small gain; 0.25 tied with more model size. Spatial anchor distances, interaction constraints, feature weighting, a wider leaf cap, coarser numeric bins, week category, wider categorical partitions, and reintroduced weekday all failed to improve. The stable date/airport/carrier/time/distance representation appears strong; further local capacity or redundant calendar changes have little benefit. Next direction: investigate a different ensemble regularizer or training objective that may alter tree correlation and generalization.

Research after experiment 60: the original [DART paper](https://arxiv.org/abs/1505.01866) describes tree dropout as a way to counter late-tree over-specialization beyond shrinkage; [XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) define `rate_drop` and `skip_drop`. [XGBoost forest guide](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) offers boosted forests as another ensemble direction. DART is more directly matched to the long 1,500-round model, so try mild dropout first.

## Experiment 61 — mild DART tree dropout (exploration)

Hypothesis: late trees in the 1,500-round model may specialize on residual subsets despite shrinkage and leaf penalties. Mild DART dropout could spread signal across trees and improve Eval AUC. Test `booster="dart"`, `rate_drop=0.01`, `skip_drop=0.5` with 1,500 rounds. Use `hist` construction to keep training below the 60 s limit; this changes split construction too, so treat the result as an architecture screen rather than isolating dropout. The [DART paper](https://arxiv.org/abs/1505.01866) motivates the mechanism.

Result: commit c643dd1, training timeout at 60 s, no Eval AUC; log as crash and discard. XGBoost 3.4.1 warned that `booster=dart` is deprecated and recommended dropout parameters on the tree booster. Try a smaller model with the supported parameter form.

## Experiment 62 — shorter supported dropout model (follow-up)

Hypothesis: the 1,500-round dropout timeout was a runtime issue rather than evidence on AUC. [Current XGBoost DART guide](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) says dropout slows training because it prevents prediction buffering, and the installed warning recommends dropout parameters directly on the tree booster. Try 1,000 histogram rounds with `rate_drop=0.01`, `skip_drop=0.5`; this should fit within 60 s and show whether dropout is promising enough to pursue.

Result: commit a7dc82d, training timeout at 60 s, no Eval AUC; log as crash and discard. Two dropout configurations failed the training limit, so stop pursuing dropout in this run.

## Experiment 63 — two-tree boosted forest (exploration)

Hypothesis: two column-sampled trees at each boosting round may average different airport/date partitions, reducing variance without the expensive DART dropout or the harmful row subsampling. Test `num_parallel_tree=2` over 1,500 histogram rounds at the same shrinkage and column sampling. Use histogram construction for the 60 s training limit and compare AUC against the 0.7679 best; a tiny tie will not justify the doubled tree count. [XGBoost boosted forest guide](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) describes combined random forest and boosting when both the round count and parallel tree count exceed one.

Result: commit 29f170e, AUC 0.7683 (+0.0004), keep. Training 27.6 s, evaluation 22.0 s, artifact 118.7 MB. The larger artifact is the cost of two trees per boosting round, but the single-parameter change creates a new best and remains within limits.

## Experiment 64 — three-tree boosted forest (follow-up)

Hypothesis: averaging three independently column-sampled trees per round might improve on the two-tree gain by making category partitions more stable. Test `num_parallel_tree=3` with all other settings fixed. Training should remain below 60 s based on the 27.6 s two-tree run; only keep if AUC gain justifies a further artifact increase.

Result: commit e83671e, AUC 0.7679 (-0.0004) with 178.8 MB artifact; discard. More parallel trees do not continue the two-tree gain.

## Experiment 65 — stronger column sampling in two-tree forest (follow-up)

Hypothesis: the two trees in each round may benefit from seeing more distinct subsets of the six predictors. Lower `colsample_bytree` from 0.8 to 0.6, with `num_parallel_tree=2` fixed. In the earlier single-tree model 0.6 was only 0.0001 below 0.8, while this forest can average complementary subsets. [XGBoost forest guide](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) uses column sampling to diversify trees.

Result: commit fefdc8a, AUC 0.7677 (-0.0006), discard. More column diversity makes each tree too weak even when averaged in pairs.

## Experiment 66 — row sampling in boosted forest (exploration)

Hypothesis: using 80% of training rows for each of the two trees per boosting round may create complementary trees and reduce overfit. `subsample=0.8` hurt the older single-tree model at experiment 24, but averaging two trees changes that variance tradeoff. Keep 0.8 column sampling and all other settings fixed. [XGBoost forest guide](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) describes row sampling as a source of forest diversity.

Result: commit c21c621, AUC 0.7673 (-0.0010), discard. Even averaging two trees does not recover the signal lost to row sampling.

Plateau research after experiments 64–66: [XGBoost monotonic guidance](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html) says a monotone rule can help when a strong relationship exists, but it can make histogram trees shallow. [EUROCONTROL operations analysis](https://www.eurocontrol.int/publication/eurocontrol-data-snapshot-59-better-first-wave-performance) notes delay accumulation during a day. A train.csv-only hourly check showed rates rise from hour 5 through about 20, then fall late at night; overnight flights also differ. A global monotone departure-time rule is therefore too strong. Retune regularization for the successful two-tree forest instead.

## Experiment 67 — less L1 in boosted forest (follow-up)

Hypothesis: averaging two trees per round can reduce variance, so L1=4 may suppress useful small airport/date effects more than it did in the single-tree model. Test `reg_alpha=2` on the 0.7683 two-tree forest with all other settings fixed. Earlier alpha=2 was worse in a single-tree histogram model, but this is a different ensemble. [XGBoost parameter docs](https://xgboost.readthedocs.io/en/latest/parameter.html) define L1 as leaf-weight regularization.

Result: commit d54b26b, AUC 0.7657 (-0.0026), discard. The larger artifact and accuracy loss show that strong L1 remains important with two trees per round.

## Experiment 68 — stronger L1 in boosted forest (follow-up)

Hypothesis: the alpha-2 loss suggests the two-tree forest still benefits from strong shrinkage; alpha 6 may further suppress weak duplicate leaf effects without the severe underfit seen at alpha 8 in the older single-tree setup. Test `reg_alpha=6` with the two-tree configuration fixed, then leave this parameter if AUC does not improve.

Result: commit 522e026, AUC 0.7667 (-0.0016), discard. Alpha 4 remains the best of 2, 4 and 6 for the two-tree forest.

Plateau research after experiments 64–68: [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/latest/tutorials/param_tuning.html) notes that random sampling and shrinkage interact with the needed boosting round count; [boosted forest documentation](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) confirms that each round boosts a small forest. Two trees per round changed the effective gradient steps compared with the single-tree model, so recheck round saturation rather than keep varying regularization.

## Experiment 69 — more two-tree boosting rounds (follow-up)

Hypothesis: the two-tree forest may still gain from additional gradient steps; its best round count need not match the single-tree model. Raise from 1,500 to 1,800 rounds with all other settings fixed. Training is expected below 60 s based on the 1,500-round 27.6 s fit; keep only if AUC improves enough to justify the larger artifact.

Result: commit cc135a1, AUC 0.7685 (+0.0002), keep. Training 32.5 s and artifact 139.5 MB. More boosting steps help the two-tree forest slightly.

## Experiment 70 — round saturation in boosted forest (follow-up)

Hypothesis: the two-tree forest may continue to improve beyond 1,800 rounds, but the gain is small and model size grows linearly. Test 2,100 rounds at fixed eta and regularization. If AUC does not improve, stop extending rounds.

Result: commit 921ce86, AUC 0.7684 (-0.0001), artifact 161.2 MB; discard. Forest round benefit saturates near 1,800.

## Synthesis after 70 experiments

Best AUC is 0.7685 at cc135a1, +0.0482 versus the baseline 0.7203. DART dropout timed out at both 1,500 and 1,000 histogram rounds. A two-tree boosted forest improved AUC to 0.7683, and 1,800 rounds raised it to 0.7685; three trees or 2,100 rounds did not help. Stronger column sampling, row sampling, and moving L1 away from 4 all hurt. Current theory: averaging two differently column-sampled trees each gradient step improves ranking, while strong leaf shrinkage and the six established inputs remain essential. Next investigate whether the forest can keep its accuracy with less tree depth or a different shrinkage/round balance, then consider complementary models if time permits.

Research after experiment 70: [XGBoost tuning guide](https://xgboost.readthedocs.io/en/release_2.0.0/tutorials/param_tuning.html) identifies depth as a main complexity control and suggests pairing lower eta with more rounds. The two-tree forest may be able to average shallower trees, reducing model size without losing AUC.

## Experiment 71 — shallower forest trees (ablation/simplification)

Hypothesis: the two trees per round may compensate for one less interaction level. Lower `max_depth` from 7 to 6 while retaining the 96-leaf cap and 1,800 rounds. In the earlier single-tree model depth 7 was slightly better than 6, but forest averaging changes the bias-variance balance. Keep if AUC improves or ties with meaningfully smaller trees.

Result: commit 643ddc5, AUC 0.7669 (-0.0016), artifact 92.7 MB; discard. Depth 7 captures important interactions even with two trees per round.

## Experiment 72 — deeper forest trees at fixed leaf cap (follow-up)

Hypothesis: depth 6 was too shallow, and the 96-leaf cap could prevent overgrowth at depth 8 while allowing a few longer airport/date/time interactions. Test `max_depth=8` in the 1,800-round two-tree forest. A previous depth-8 loss occurred in the older single-tree model, so this checks a changed ensemble and regularization context.

Result: commit 893c99d, AUC tied at 0.7685 but artifact grew to 156.4 MB and training to 36.8 s; discard. Depth 7 is the efficient choice.

## Experiment 73 — faster forest shrinkage (ablation/simplification)

Hypothesis: 1,500 rounds at eta 0.03 have roughly the same cumulative update budget as 1,800 rounds at eta 0.025, but 300 fewer two-tree stages. This may avoid weak late updates and shrink the artifact while preserving AUC. Earlier shrinkage tuning occurred in a different single-tree model; [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/release_2.0.0/tutorials/param_tuning.html) describes coupling step size and round count. Keep if AUC improves or ties with a substantially smaller model.

Result: commit 932ad94, AUC 0.7680 (-0.0005), artifact 117.9 MB; discard. The faster updates cost too much ranking accuracy despite a smaller model.

Plateau research after experiments 71–73: [XGBoost callback documentation](https://xgboost.readthedocs.io/en/stable/python/callbacks.html) and [LearningRateScheduler API](https://xgboost.readthedocs.io/en/release_3.0.0/python/python_api.html) support per-round learning rates. A schedule could use larger steps while broad patterns are learned, then smaller steps for late residuals. That differs from simply changing fixed eta/round count, which just lost AUC.

## Experiment 74 — descending learning rate (exploration)

Hypothesis: a linear rate schedule from 0.03 to 0.02 across 1,800 two-tree rounds preserves approximately the same total update budget as constant 0.025, but makes early trees stronger and late refinements gentler. The 0.03/1,500 fixed-rate experiment was worse; this isolates whether varying the step size over training helps. Use XGBoost's [LearningRateScheduler](https://xgboost.readthedocs.io/en/release_3.0.0/python/python_api.html).

Result: commit f470656, AUC 0.7679 (-0.0006), discard. The schedule adds complexity and does not improve ranking over constant 0.025.

## Experiment 75 — smaller constant learning rate (follow-up)

Hypothesis: unlike the unsuccessful descending schedule, a constant eta 0.02 may make all two-tree updates smoother and improve ranking. Use 2,250 rounds so eta times rounds remains 45, matching the 0.025/1,800 best. The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/release_2.0.0/tutorials/param_tuning.html) recommends more rounds with smaller eta. Training is expected below 60 s.

Result: commit d357ec1, AUC 0.7682 (-0.0003), artifact 175.4 MB; discard. Smoother fixed boosting does not improve the forest and costs more time and size.

Plateau research after experiments 74–75: [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/release_3.3.0/parameter.html) describes `lossguide` and `max_leaves` as separate controls on where and how much trees can grow. At depth 7, increasing the leaf cap from 96 toward the full 128 depth-limited leaves could allow additional useful branches while L1/L2 regularization protects against weak splits.

## Experiment 76 — wider leaf cap in two-tree forest (follow-up)

Hypothesis: the 96-leaf cap was selected on a much earlier single-tree model. Two-tree averaging with 1,800 rounds might benefit from 128 leaves per tree at the same depth 7. Test `max_leaves=128` with everything else fixed. Earlier 128 leaves tied on the single-tree approximate model, so this tests a changed ensemble and tree method.

Result: commit 7305e7d, AUC 0.7682 (-0.0003), artifact 149.2 MB; discard. Additional leaves do not improve the forest.

## Experiment 77 — smaller leaf cap in two-tree forest (ablation/simplification)

Hypothesis: if the useful 96-leaf configuration contains weak tail branches, 64 leaves may preserve AUC while materially reducing model size. The earlier 64-leaf single-tree model lost 0.0005, but averaging two trees may compensate. Test `max_leaves=64` with all other settings fixed; keep if it ties with a substantially smaller artifact or improves AUC.

Result: commit cb23fee, AUC 0.7675 (-0.0010), artifact 109.4 MB; discard. The size reduction is substantial but loses too much ranking accuracy. Leaf cap 96 remains best.

Plateau research after experiments 75–77: [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/latest/tutorials/param_tuning.html) lists `min_child_weight` as a core complexity control. With the leaf cap bracketed and L1 strongly necessary, a small change in child support is the remaining direct way to alter sparse date-airport branches in the successful forest.

## Experiment 78 — quarter child support in forest (follow-up)

Hypothesis: the two-tree forest may safely average rare useful branches when `min_child_weight` is reduced from 0.5 to 0.25. The single-tree test at 0.25 tied with larger size, but averaging two trees may turn that extra capacity into a gain. Keep only if AUC improves beyond 0.7685. [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines the threshold on child Hessian weight.

Result: commit e74f9bb, AUC 0.7681 (-0.0004), discard. Lower child support adds weak branches without a gain.

## Experiment 79 — default child support in forest (ablation/simplification)

Hypothesis: the two-tree ensemble may have reduced dependence on the 0.5 child threshold that gave only a 0.0001 single-tree gain. Remove the explicit `min_child_weight=0.5`, restoring the XGBoost default 1. Keep if AUC ties with simpler code and equal or smaller model, or if it improves.

Result: commit 429153c, AUC 0.7681 (-0.0004), discard. The 0.5 child threshold remains necessary despite the small original gain.

Plateau research after experiments 77–79: [XGBoost column-sampling docs](https://xgboost.readthedocs.io/en/latest/parameter.html) confirm that `colsample_bytree` selects columns once per tree, so the two trees in each boosted round may see different subsets. The 0.6 trial removed too much signal, while 0.8 works; a middle fraction can check the boundary of useful diversity.

## Experiment 80 — intermediate forest column sampling (follow-up)

Hypothesis: `colsample_bytree=0.7` may retain more signal than the 0.6 forest while making the two trees more diverse than at 0.8. Test this midpoint with the 1,800-round best and all other settings fixed. If it does not improve AUC, keep 0.8 and leave sampling tuning.

Result: commit 0ecf165, AUC tied at 0.7685 with essentially unchanged artifact and training time; discard because it offers no gain or simplification over 0.8.

## Synthesis after 80 experiments

Best AUC remains 0.7685 at cc135a1, +0.0482 over baseline. The latest ten experiments found no further gain: 2,100 rounds, depths 6 and 8, changed learning rates and a rate schedule, leaf caps 64 and 128, child weights 0.25 and 1, and intermediate column sampling all lost or tied without simplification. The 1,800-round two-tree forest at depth 7, 96 leaves, eta 0.025, alpha 4, lambda 10, and child weight 0.5 remains the strongest tested. Next check whether L2 regularization should shift in this ensemble; otherwise preserve the best commit.

Research after experiment 80: [XGBoost parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html) describes L2 as making leaf weights more conservative, and the [boosted-tree derivation](https://xgboost.readthedocs.io/en/latest/tutorials/model.html) shows lambda in the split-gain denominator. The two-tree forest may need a different degree of L2 shrinkage than the single-tree model that selected 10.

## Experiment 81 — less L2 in boosted forest (exploration)

Hypothesis: averaging two column-sampled trees could smooth leaf values enough to permit `reg_lambda=5` instead of 10, recovering some small but useful gradients. Test lambda 5 with alpha 4, 1,800 rounds, and all other best settings fixed. The earlier lambda-5 test used the older single-tree model.

Result: commit 944c7df, AUC 0.7680 (-0.0005), discard. Less L2 weakens generalization in the two-tree forest.

## Experiment 82 — more L2 in boosted forest (follow-up)

Hypothesis: because lambda 5 reduced AUC, more L2 smoothing could help the two-tree forest resist weak date-airport partitions. Test `reg_lambda=20` against the best 10 while keeping L1, leaves, rounds and sampling fixed. An earlier lambda-20 result was slightly worse in a single-tree setup, so this checks the ensemble context.

Result: commit fe30861, AUC 0.7677 (-0.0008), discard. Lambda 10 is best among 5, 10 and 20 in the forest.

## Experiment 83 — milder forest feature sampling (follow-up)

Hypothesis: allowing each of the two trees to see more predictors might improve split quality while preserving some diversity, especially with only six total predictors. Test `colsample_bytree=0.9` versus the 0.8 best. It hurt an older single-tree model, but the two-tree averaging changes the tradeoff. If it fails, conclude 0.8 remains the best sampling setting.

Result: commit 2e5c338, AUC 0.7669 (-0.0016), discard. Each tree needs enough column diversity; 0.8 is best among 0.6, 0.7, 0.8 and 0.9 tested in the forest.

## Final summary

The two-hour run completed 84 scored attempts including the baseline. Best Eval AUC: **0.7685** at commit **cc135a1** on branch **sep29**, up **0.0482** from the 0.7203 baseline. The final model uses categorical day of year, carrier, origin and destination plus scheduled departure time and distance; it trains a two-tree boosted forest for 1,800 histogram rounds with depth 7, 96 leaves, eta 0.025, column sampling 0.8, L1 4, L2 10 and minimum child weight 0.5.

What worked: a categorical date representation, more categorical split candidates, removing redundant calendar predictors, smaller learning steps, tree-level column sampling, leafwise growth, L1/L2 regularization, and finally a two-tree boosted forest with 1,800 rounds. What did not: raw route categories, one-hot carrier splits, row sampling, stronger interaction constraints, added week or weekday features, spatial anchor distances, DART dropout within the training limit, and further forest capacity or shrinkage changes.

Next, I would try a carefully measured ensemble of complementary histogram and approximate models within the 60 s training limit, or a new preflight signal that is available row by row. Keep the current commit until such a model clearly improves Eval AUC.
