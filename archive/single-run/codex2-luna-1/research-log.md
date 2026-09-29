# Research log — sep28

Setup complete on branch `sep28`. The first experiment will be the untouched baseline, as required by `program.md`.

## Experiment 1 — baseline (`c294417`)

- Hypothesis: the untouched starter establishes the reference Eval AUC before any changes.
- Classification: baseline.
- Result: Eval AUC `0.7203`; status `keep`; run completed successfully in about 32 seconds.
- Observation: the starter uses native categorical XGBoost with six categorical columns, two numeric columns, 30 trees, depth 6, and learning rate 0.1. The next experiment requires external research before changing the model.

## Research before Experiment 2

- XGBoost's parameter documentation describes `max_depth`, `min_child_weight`, and `gamma` as complexity controls, and `subsample` / `colsample_bytree` as randomness controls for reducing overfitting: [XGBoost Parameters](https://xgboost.readthedocs.io/en/stable/parameter.html).
- XGBoost's categorical-data guide confirms that the existing pandas categorical representation with `enable_categorical=True` is the supported scikit-learn path: [Categorical Data](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html).
- A flight-delay study explicitly represents scheduled departure time as a continuous feature and includes carrier, origin, destination, and distance, motivating a time representation experiment: [Flight Delay Prediction Using a Hybrid Machine Learning Approach](https://engj.org/index.php/ej/article/download/4376/1156).

## Experiment 2 — scheduled-time representation (`132b310`)

- Hypothesis: converting HHMM scheduled departure to minutes since midnight and adding daily sine/cosine features would make time continuity easier for tree splits, especially around midnight.
- Classification: exploration.
- Change: retained the original `CRSDepTime` and added row-local `DepMinutes`, `DepTimeSin`, and `DepTimeCos` inside `prepare(df)`.
- Result: Eval AUC `0.7195`; status `discard`; 0.0008 below baseline. The transformation did not help on this split, so the branch is reverted to the baseline before the next experiment.

## Experiment 3 — more boosting rounds (`6acec81`)

- Hypothesis: the 30-tree starter was underfit; 100 trees at the same depth and learning rate should improve ranking without changing the representation.
- Classification: follow-up.
- Change: `n_estimators=30` → `100`.
- Result: Eval AUC `0.7306`; status `keep`; +0.0103 versus baseline. This is the current best and supports exploring the learning-rate/tree-count tradeoff around this larger ensemble.

## Experiment 4 — smaller learning rate (`b3f2c00`)

- Hypothesis: halving the learning rate and doubling the tree count would make boosting updates less abrupt and improve generalization.
- Classification: follow-up.
- Change: `n_estimators=200`, `learning_rate=0.05`.
- Result: Eval AUC `0.7325`; status `keep`; +0.0019 versus Experiment 3 and +0.0122 versus baseline. The lower-rate, longer ensemble is now best.

## Experiment 5 — deeper trees (`a1c479d`)

- Hypothesis: depth 8 would expose useful higher-order interactions among carrier, airports, and schedule while the 200k-row training set limits variance.
- Classification: exploration.
- Change: `max_depth=6` → `8`.
- Result: Eval AUC `0.7331`; status `keep`; +0.0006 versus Experiment 4. The current best uses 200 trees, learning rate 0.05, and depth 8.

## Experiment 6 — shallower-tree ablation (`6b108c3`)

- Hypothesis: depth 5 might remove noisy high-order splits and improve generalization.
- Classification: ablation/simplification.
- Change: `max_depth=8` → `5`.
- Result: Eval AUC `0.7299`; status `discard`; −0.0032 versus the current best. Deeper trees are useful here, so the branch is reverted to `a1c479d`.

## Experiment 7 — leaf regularization (`75ea692`)

- Hypothesis: increasing `min_child_weight` from 1 to 5 would suppress weak leaf splits while retaining depth-8 interactions.
- Classification: follow-up regularization.
- Change: add `min_child_weight=5`.
- Result: Eval AUC `0.7339`; status `keep`; +0.0008 versus the previous best. Moderate leaf regularization helps.

## Experiment 8 — stronger leaf regularization (`f8be9f8`)

- Hypothesis: `min_child_weight=10` might further reduce noisy splits after the gain at 5.
- Classification: follow-up.
- Change: `min_child_weight=5` → `10`.
- Result: Eval AUC `0.7327`; status `discard`; −0.0012 versus `75ea692`. The branch is reverted to the value 5.

## Experiment 9 — split-loss regularization (`f7f4a02`)

- Hypothesis: a small `gamma=0.1` would remove marginal splits on top of `min_child_weight=5`.
- Classification: follow-up regularization.
- Change: add `gamma=0.1`.
- Result: Eval AUC `0.7332`; status `discard`; −0.0007 versus `75ea692`. The extra split threshold did not help and the branch is reverted.

## Experiment 10 — route categorical feature (`53a349f`)

- Hypothesis: an explicit `Origin→Dest` category would expose route-specific delay behavior more directly than separate origin and destination categories.
- Classification: exploration.
- Change: add a training-fitted 4,290-level `Route` categorical feature, looked up row-locally in `prepare(df)`.
- Result: Eval AUC `0.7067`; status `discard`; −0.0272 versus the best. The artifact grew to 78.5 MB and evaluation slowed to 48 seconds. High-cardinality native categorical partitioning is a poor fit here, so the branch is reverted.

## Synthesis after 10 experiments

- Current best: `75ea692`, Eval AUC `0.7339`, using the original eight features plus `n_estimators=200`, `learning_rate=0.05`, `max_depth=8`, and `min_child_weight=5`.
- What helped: more boosting rounds produced the largest gain (`0.7203` → `0.7306`), a smaller learning rate with 200 rounds improved it again, and depth 8 plus moderate leaf regularization added smaller gains.
- What did not help: the cyclic/HHMM departure-time representation, depth 5, stronger leaf regularization, `gamma=0.1`, and the high-cardinality route category. The route feature also materially increased artifact and evaluation cost.
- Working theory: the task benefits mainly from sufficient boosting capacity and a moderate-complexity tree structure; naive high-cardinality interaction categories and generic time transforms are not reliable on this balanced split.
- Next direction: test lower-cardinality, row-local representations and controlled sampling/feature subsampling, with extra care around native categorical cardinality.

## Experiment 11 — row subsampling (`1687c30`)

- Hypothesis: `subsample=0.8` would decorrelate trees and improve generalization.
- Classification: exploration.
- Change: add `subsample=0.8`.
- Result: Eval AUC `0.7306`; status `discard`; −0.0033 versus `75ea692`. Full-row training is better here, so the branch is reverted.

## Experiment 12 — feature subsampling (`83e1386`)

- Hypothesis: `colsample_bytree=0.8` would decorrelate trees across the six categorical and two numeric inputs without discarding rows.
- Classification: follow-up to the controlled-randomness direction.
- Change: add `colsample_bytree=0.8` while leaving `subsample=1`.
- Result: Eval AUC `0.7397`; status `keep`; +0.0058 versus `75ea692`. Feature subsampling is a strong improvement and is now the current best.

## Experiment 13 — stronger feature subsampling (`0f9df9f`)

- Hypothesis: reducing `colsample_bytree` from 0.8 to 0.6 would add useful tree diversity without the signal loss seen from row subsampling.
- Classification: follow-up sweep.
- Change: `colsample_bytree=0.8` → `0.6`.
- Result: Eval AUC `0.7455`; status `keep`; +0.0058. The current best combines full-row training with 0.6 feature subsampling.

## Experiment 14 — excessive feature subsampling (`2201172`)

- Hypothesis: `colsample_bytree=0.4` might continue the diversity benefit seen at 0.8 and 0.6.
- Classification: follow-up sweep.
- Change: `colsample_bytree=0.6` → `0.4`.
- Result: Eval AUC `0.7436`; status `discard`; −0.0019 versus `0f9df9f`. The branch is reverted to 0.6.

## Experiment 15 — midpoint feature subsampling (`126a7da`)

- Hypothesis: `colsample_bytree=0.5` could match or exceed 0.6 while exposing slightly more diverse feature subsets.
- Classification: follow-up sweep.
- Change: `colsample_bytree=0.6` → `0.5`.
- Result: Eval AUC `0.7455`; status `discard` (tie); no improvement or simplicity gain over `0f9df9f`, so the branch is reverted.

## Experiment 16 — cumulative level-wise sampling (`be96702`)

- Hypothesis: adding `colsample_bylevel=0.8` on top of `colsample_bytree=0.6` would diversify splits within each tree.
- Classification: exploration.
- Change: add `colsample_bylevel=0.8`.
- Result: Eval AUC `0.7433`; status `discard`; −0.0022. The additional sampling over-regularizes the model and the branch is reverted.

## Experiment 17 — per-node sampling (`c00665f`)

- Hypothesis: `colsample_bynode=0.8` would diversify each split differently from level-wise sampling.
- Classification: exploration.
- Change: add `colsample_bynode=0.8` alongside `colsample_bytree=0.6`.
- Result: Eval AUC `0.7451`; status `discard`; −0.0004 versus the current best. The extra parameter is not worth the small regression.

## Experiment 18 — longer subsampled ensemble (`11ae0cd`)

- Hypothesis: feature subsampling reduces variance enough for additional boosting rounds to keep improving the ranking.
- Classification: follow-up.
- Change: `n_estimators=200` → `300` at `learning_rate=0.05`.
- Result: Eval AUC `0.7480`; status `keep`; +0.0025. More rounds remain useful with `colsample_bytree=0.6`.

## Experiment 19 — smoother longer schedule (`299a908`)

- Hypothesis: 400 trees at learning rate 0.04 could improve the ranking over 300 trees at 0.05.
- Classification: follow-up.
- Change: `n_estimators=400`, `learning_rate=0.04`.
- Result: Eval AUC `0.7479`; status `discard`; −0.0001 and a larger artifact. The simpler 300/0.05 schedule remains preferred.

## Experiment 20 — depth nine (`4582dd9`)

- Hypothesis: with feature subsampling reducing variance, one extra tree level could capture additional useful interactions.
- Classification: follow-up capacity refinement.
- Change: `max_depth=8` → `9`.
- Result: Eval AUC `0.7495`; status `keep`; +0.0015. The artifact is larger (30.5 MB), but the gain is meaningful enough to retain.

## Synthesis after 20 experiments

- Current best: `4582dd9`, Eval AUC `0.7495`, with 300 trees, learning rate 0.05, depth 9, `min_child_weight=5`, full-row training, and `colsample_bytree=0.6`.
- Strongest findings: model capacity and diversity interact favorably. Tree count improved the starter substantially; feature subsampling was the largest second-stage gain (`0.7339` → `0.7455`), and depth 9 added another `0.0015`.
- Negative findings: row subsampling, cumulative level/node sampling, high-cardinality route categories, generic cyclic time features, stronger leaf regularization, and a split-loss threshold all hurt or tied. The low-cardinality native categorical columns are more useful than a 4,290-level route category.
- Learning-rate schedule: 300/0.05 is marginally better and simpler than 400/0.04, but the round count is still not saturated; depth 9 remains promising despite a larger artifact.
- Next direction: refine capacity and regularization around this stronger ensemble, then test compact row-local temporal encodings or categorical split controls rather than high-cardinality lookup features.

## Experiment 21 — categorical one-hot threshold (`771f646`)

- Hypothesis: one-hot splitting for categories up to 32 levels would help month, day, weekday, and carrier while retaining partitioning for airports.
- Classification: exploration of native categorical handling.
- Change: add `max_cat_to_onehot=32`.
- Result: Eval AUC `0.7377`; status `discard`; −0.0118. Native partitioning is substantially better here, so the branch is reverted.

## Experiment 22 — depth ten (`60b1953`)

- Hypothesis: one more level would continue the depth-8 → 9 improvement under feature subsampling.
- Classification: follow-up capacity sweep.
- Change: `max_depth=9` → `10`.
- Result: Eval AUC `0.7504`; status `keep`; +0.0009. The artifact increased to 46.6 MB, so future capacity changes must justify their cost.

## Experiment 23 — lighter leaf threshold (`7eed099`)

- Hypothesis: depth 10 could benefit from allowing smaller leaves, reducing `min_child_weight` from 5 to 3.
- Classification: follow-up regularization/capacity interaction.
- Change: `min_child_weight=5` → `3`.
- Result: Eval AUC `0.7506`; status `keep`; +0.0002. The small gain supports retaining the lighter threshold.

## Experiment 24 — default leaf threshold (`99f1a0e`)

- Hypothesis: feature subsampling would make the default `min_child_weight=1` safe at depth 10.
- Classification: follow-up.
- Change: `min_child_weight=3` → `1`.
- Result: Eval AUC `0.7495`; status `discard`; −0.0011. The branch is reverted to 3.

## Experiment 25 — histogram resolution (`5688075`)

- Hypothesis: `max_bin=512` would improve the numeric splits for scheduled time and distance.
- Classification: exploration.
- Change: add `max_bin=512`.
- Result: Eval AUC `0.7495`; status `discard`; −0.0011 with a larger artifact. The default 256 bins are preferable.

## Experiment 26 — L2 regularization (`169cc38`)

- Hypothesis: deeper trees would generalize better with a modest increase in L2 leaf-weight penalty.
- Classification: targeted regularization exploration.
- Change: add `reg_lambda=2` (from the default 1).
- Result: Eval AUC `0.7511`; status `keep`; +0.0005. Mild L2 regularization helps the current deep ensemble.

## Experiment 27 — light L1 regularization (`20901be`)

- Hypothesis: `reg_alpha=0.1` would suppress weak leaf scores in addition to the successful L2 penalty.
- Classification: targeted regularization follow-up.
- Change: add `reg_alpha=0.1` alongside `reg_lambda=2`.
- Result: Eval AUC `0.7510`; status `discard`; −0.0001 and a larger artifact. Keep L2 only.

## Experiment 28 — overlong ensemble (`b491494`)

- Hypothesis: the current regularized depth-10 model would keep improving through 400 trees at learning rate 0.05.
- Classification: capacity follow-up.
- Change: `n_estimators=300` → `400`.
- Result: Eval AUC `0.7499`; status `discard`; −0.0012, with a 63.4 MB artifact. The 300-tree model is better and more compact.

## Experiment 29 — depth eleven (`01c296c`)

- Hypothesis: the depth-9 → 10 gain might continue one level further under L2 regularization.
- Classification: capacity follow-up.
- Change: `max_depth=10` → `11`.
- Result: Eval AUC `0.7494`; status `discard`; −0.0017, with a 72.9 MB artifact. Depth 10 is the better capacity point.

## Experiment 30 — stronger L2 tie (`9a7482d`)

- Hypothesis: increasing `reg_lambda` from 2 to 3 would further stabilize the depth-10 ensemble.
- Classification: regularization follow-up.
- Change: `reg_lambda=2` → `3`.
- Result: Eval AUC `0.7511`; status `discard` (tie). There is no measured gain or simplicity benefit, so the branch returns to L2=2.

## Experiment 31 — departure hour (`c37f5cc`)

- Hypothesis: a direct `CRSDepTime // 100` hour feature would capture coarse operational time blocks better than raw HHMM alone.
- Classification: compact feature exploration.
- Change: add row-local numeric `DepHour` inside `prepare(df)`.
- Result: Eval AUC `0.7492`; status `discard`; −0.0019. The current raw time representation is better here.

## Experiment 32 — categorical partition limit (`b60c0da`)

- Hypothesis: `max_cat_threshold=32` would regularize the 283-level airport fields while retaining useful native categorical splits.
- Classification: categorical regularization exploration.
- Change: add `max_cat_threshold=32`.
- Result: Eval AUC `0.7505`; status `discard`; −0.0006. The unrestricted default is better.

## Experiment 33 — DART dropout (`fce45dc`)

- Hypothesis: DART tree dropout at `rate_drop=0.1` could regularize the deep ensemble beyond the standard booster.
- Classification: model-family exploration.
- Change: `booster="dart"`, `rate_drop=0.1`.
- Result: status `crash` / training timeout; no Eval AUC. Training was killed at the 60-second harness limit, so this family is abandoned and the branch is reverted.

## Experiment 34 — loss-guided growth (`2e73de1`)

- Hypothesis: `grow_policy="lossguide"` would allocate tree capacity to the highest-loss-change branches more efficiently than depth-wise growth.
- Classification: tree-growth exploration.
- Change: use `tree_method="hist"`, `grow_policy="lossguide"`, `max_depth=0`, and `max_leaves=512`.
- Result: Eval AUC `0.7520`; status `keep`; +0.0009 versus the previous best. Training took 10.1 seconds and the artifact was 40.1 MB, both within limits.

## Experiment 35 — excessive loss-guided capacity (`384ce87`)

- Hypothesis: doubling the loss-guided leaf budget to 1024 would capture additional useful interactions.
- Classification: leaf-budget follow-up.
- Change: `max_leaves=512` → `1024`.
- Result: Eval AUC `0.7497`; status `discard`; −0.0023. Training increased to 17.8 seconds and the artifact to 72.7 MB, confirming overfit/cost; the branch is reverted.

## Experiment 36 — smaller loss-guided budget (`2e6d4f1`)

- Hypothesis: `max_leaves=256` would retain most of the loss-guided gain with less variance and a smaller artifact.
- Classification: ablation/simplification.
- Change: `max_leaves=512` → `256`.
- Result: Eval AUC `0.7508`; status `discard`; −0.0012. The 512-leaf setting is retained.

## Experiment 37 — interpolated leaf budget (`a811b97`)

- Hypothesis: `max_leaves=384` might balance the underfit 256-leaf and overfit 1024-leaf settings.
- Classification: follow-up leaf-budget sweep.
- Change: `max_leaves=512` → `384`.
- Result: Eval AUC `0.7516`; status `discard`; −0.0004. Keep 512 leaves.

## Experiment 38 — smooth loss-guided schedule (`b3406a0`)

- Hypothesis: loss-guided growth might benefit from 400 trees at learning rate 0.04 even though depth-wise growth did not.
- Classification: follow-up schedule test.
- Change: `n_estimators=400`, `learning_rate=0.04`.
- Result: Eval AUC `0.7517`; status `discard`; −0.0003, with a larger artifact and slower training. Keep 300/0.05.

## Experiment 39 — intermediate loss-guided rounds (`0d2316e`)

- Hypothesis: 350 trees at learning rate 0.05 might improve on the 300-tree model while avoiding the 400-tree overfit.
- Classification: capacity interpolation.
- Change: `n_estimators=300` → `350`.
- Result: Eval AUC `0.7514`; status `discard`; −0.0006. The 300-tree point remains best.

## Experiment 40 — loss-guided leaf regularization (`b8dd6c7`)

- Hypothesis: loss-guided growth would benefit from `min_child_weight=5` because it can pursue aggressive high-loss branches.
- Classification: regularization follow-up.
- Change: `min_child_weight=3` → `5`.
- Result: Eval AUC `0.7515`; status `discard`; −0.0005. Keep 3.

## Experiment 41 — calendar position (`804bfd7`)

- Hypothesis: a smooth annual position would complement separate Month and DayofMonth categories and capture seasonal drift.
- Classification: compact feature exploration.
- Change: add row-local `DayOfYear` using fixed 2005 calendar month offsets; no train/eval aggregation or lookup was used.
- Result: Eval AUC `0.7550`; status `keep`; +0.0030. This is the new best, with evaluation still within the five-minute limit (36.1 seconds).

## Experiment 42 — weekend indicator (`96ed450`)

- Hypothesis: a binary weekend distinction would expose a useful operational grouping that the 7-level weekday category may not express efficiently.
- Classification: calendar-feature follow-up.
- Change: add row-local `IsWeekend = (DayOfWeek >= 6)` while retaining `DayOfWeek`.
- Result: Eval AUC `0.7572`; status `keep`; +0.0022. Compact calendar features continue to add signal.

## Experiment 43 — log distance (`6e7d82e`)

- Hypothesis: `log1p(Distance)` would give histogram resolution more useful sensitivity on short routes.
- Classification: compact numeric feature exploration.
- Change: add row-local `DistanceLog`.
- Result: Eval AUC `0.7558`; status `discard`; −0.0014. Raw distance is sufficient, so the branch is reverted.

## Experiment 44 — month-end boundary (`0644000`)

- Hypothesis: flights near the end of a calendar month may have a distinct operational/travel pattern not captured by the continuous day-of-year feature.
- Classification: calendar-feature follow-up.
- Change: add row-local `IsMonthEnd` for the last three days of each fixed month.
- Result: Eval AUC `0.7583`; status `keep`; +0.0011. The boundary flag adds useful signal.

## Experiment 45 — month-start boundary (`7b90539`)

- Hypothesis: the first three days of the month would provide a complementary boundary signal.
- Classification: calendar-feature follow-up.
- Change: add row-local `IsMonthStart`.
- Result: Eval AUC `0.7553`; status `discard`; −0.0030. Month-end is useful, but month-start is not; the branch is reverted.

## Research before Experiment 46

- Flight-delay studies commonly add `Is_holiday` / holiday-calendar features alongside weekend and seasonal variables: [Predicting Flight Delays with Machine Learning](https://onlinelibrary.wiley.com/doi/10.1155/2024/3385463) and [Calibrated and Explainable Flight Delay Prediction](https://doi.org/10.1145/3786484.3786539).

## Experiment 46 — exact holiday flag (`4043ed7`)

- Hypothesis: exact 2005 U.S. federal-holiday dates would capture unusual travel/operations patterns beyond the learned calendar features.
- Classification: compact calendar exploration.
- Change: add row-local `IsHoliday` for ten fixed 2005 federal holiday dates.
- Result: Eval AUC `0.7559`; status `discard`; −0.0024. The exact-day flag is too sparse/blunt here, so the branch is reverted.

## Experiment 47 — wider month-end window (`643a9dc`)

- Hypothesis: extending `IsMonthEnd` from the last three days to the last five days would capture a broader month-end pattern.
- Classification: boundary-window follow-up.
- Change: threshold from `month_length - 2` to `month_length - 4`.
- Result: Eval AUC `0.7572`; status `discard`; −0.0011. Keep the narrower three-day window.

## Experiment 48 — narrower month-end window (`9ed4aea`)

- Hypothesis: the signal might be concentrated in the final two days rather than the final three.
- Classification: boundary-window refinement.
- Change: threshold from `month_length - 2` to `month_length - 1`.
- Result: Eval AUC `0.7572`; status `discard` (tie); no simplicity benefit over the three-day version, so the branch is reverted.

## Experiment 49 — Friday indicator (`57f1e1c`)

- Hypothesis: Friday would have a distinct pre-weekend travel pattern beyond the weekday category and weekend flag.
- Classification: calendar-feature follow-up.
- Change: add row-local `IsFriday`.
- Result: Eval AUC `0.7553`; status `discard`; −0.0030. The extra weekday flag is harmful, so the branch is reverted.

## Experiment 50 — cyclic annual seasonality (`da686c8`)

- Hypothesis: sine/cosine projections of the successful `DayOfYear` feature would model the December–January wraparound that tree thresholds cannot express naturally.
- Classification: calendar-feature follow-up.
- Change: add row-local `DayOfYearSin` and `DayOfYearCos`.
- Result: Eval AUC `0.7585`; status `keep`; +0.0002. The gain is small but positive, and the feature pair is compact.

## Experiment 51 — cyclic departure time (`26e5948`)

- Hypothesis: isolating daily sine/cosine projections might help after the annual calendar features, without the failed minute/hour columns.
- Classification: focused temporal-feature re-test.
- Change: add row-local `DepTimeSin` and `DepTimeCos` only.
- Result: Eval AUC `0.7539`; status `discard`; −0.0046. Scheduled-time cyclic features are consistently harmful here; the branch is reverted.

## Experiment 52 — calendar-model feature sampling (`5e01c82`)

- Hypothesis: adding calendar features changes the effective feature mix, so stronger per-tree subsampling might now be better than 0.6.
- Classification: targeted sampling refinement.
- Change: `colsample_bytree=0.6` → `0.5`.
- Result: Eval AUC `0.7606`; status `keep`; +0.0021. The sampling optimum shifted after feature engineering.

## Experiment 53 — stronger calendar-model sampling (`96f045b`)

- Hypothesis: the expanded feature set could support even stronger per-tree diversity at `colsample_bytree=0.4`.
- Classification: local subsampling sweep.
- Change: `colsample_bytree=0.5` → `0.4`.
- Result: Eval AUC `0.7608`; status `keep`; +0.0002. This is the new best, though the improvement is small.

## Experiment 54 — excessive calendar-model sampling (`1ad37ec`)

- Hypothesis: stronger diversity at `colsample_bytree=0.3` might continue the gains from 0.6→0.5→0.4.
- Classification: local subsampling sweep.
- Change: `colsample_bytree=0.4` → `0.3`.
- Result: Eval AUC `0.7577`; status `discard`; −0.0031. The useful lower boundary is 0.4.

## Experiment 55 — larger post-feature leaf budget (`43af86d`)

- Hypothesis: calendar features and stronger subsampling would allow a larger loss-guided budget.
- Classification: post-feature leaf-budget follow-up.
- Change: `max_leaves=512` → `768`.
- Result: Eval AUC `0.7606`; status `discard`; −0.0002, with a 46.8 MB artifact. Keep 512 leaves.

## Experiment 56 — lighter leaf threshold after feature engineering (`3e99055`)

- Hypothesis: `min_child_weight=2` might improve the calendar-enhanced loss-guided model between the rejected values 1 and 5.
- Classification: leaf-regularization refinement.
- Change: `min_child_weight=3` → `2`.
- Result: Eval AUC `0.7601`; status `discard`; −0.0007. Keep 3.

## Experiment 57 — lighter L2 penalty (`662e3ba`)

- Hypothesis: the stronger feature subsampling might make the default `reg_lambda=1` preferable to 2.
- Classification: regularization refinement.
- Change: `reg_lambda=2` → `1`.
- Result: Eval AUC `0.7608`; status `discard` (tie); the explicit parameter change has no measured gain. A subsequent simplification test removes the redundant default setting.

## Experiment 58 — default-parameter simplification (`69f7ce6`)

- Hypothesis: removing the explicit `reg_lambda=1` line would preserve the same model while simplifying the code, since 1 is XGBoost's default.
- Classification: ablation/simplification.
- Change: remove redundant `reg_lambda=1` from the classifier configuration.
- Result: Eval AUC `0.7608`; status `keep`; tied the prior score with simpler code. The current best is now the simplified commit.

## Experiment 59 — lighter L2 (`e2d1d44`)

- Hypothesis: `reg_lambda=0.5` could unlock useful leaf scores under 0.4 feature subsampling.
- Classification: targeted L2 refinement.
- Change: add `reg_lambda=0.5`.
- Result: Eval AUC `0.7600`; status `discard`; −0.0008. The default L2 value remains best.

## Experiment 60 — month-end/weekend interaction (`887375a`)

- Hypothesis: an explicit interaction would survive 0.4 feature subsampling more reliably than asking trees to select both component flags.
- Classification: calendar interaction follow-up.
- Change: add row-local `IsMonthEndWeekend = IsMonthEnd * IsWeekend`.
- Result: Eval AUC `0.7611`; status `keep`; +0.0003. The interaction is compact and improves the best score.

## Experiment 61 — intermediate feature sampling (`1f968f0`)

- Hypothesis: the local 0.3/0.4/0.5 sweep might peak at `colsample_bytree=0.35`.
- Classification: narrow sampling refinement.
- Change: `colsample_bytree=0.4` → `0.35`.
- Result: Eval AUC `0.7599`; status `discard`; −0.0012. Keep 0.4.

## Experiment 62 — weekend seasonal interaction (`abc4bf6`)

- Hypothesis: explicit `DayOfYear × IsWeekend` would preserve seasonal weekend structure under feature subsampling.
- Classification: compact calendar interaction exploration.
- Change: add row-local `WeekendDayOfYear`.
- Result: Eval AUC `0.7594`; status `discard`; −0.0017. The extra interaction is harmful, so the branch is reverted.

## Experiment 63 — shorter calendar ensemble (`e7c7835`)

- Hypothesis: calendar features would let loss-guided boosting peak before 300 rounds, allowing a simpler 250-tree model.
- Classification: capacity ablation/simplification.
- Change: `n_estimators=300` → `250`.
- Result: Eval AUC `0.7605`; status `discard`; −0.0006. Retain 300 rounds.

## Experiment 64 — seasonal month-end interaction (`acc458d`)

- Hypothesis: month-end effects would vary by annual position, motivating `DayOfYear × IsMonthEnd`.
- Classification: compact calendar interaction exploration.
- Change: add row-local `MonthEndDayOfYear`.
- Result: Eval AUC `0.7594`; status `discard`; −0.0017. Keep the month-end/weekend interaction only.

## Research before Experiment 65

- Target encoding can turn high-cardinality categories into numeric target-conditioned priors, but naive full-data encodings leak the row's own target. CatBoost's documentation and paper emphasize ordered statistics to prevent this leakage: [CatBoost categorical features](https://catboost.ai/docs/en/features/categorical-features), [CatBoost: Unbiased Boosting with Categorical Features](https://proceedings.neurips.cc/paper/7898-catboost-unbiased-boosting-with-categorical-features.pdf).

## Experiment 65 — smoothed low-cardinality target priors (`2768b71`)

- Hypothesis: smoothed train-fitted delay rates for carrier, origin, and destination would provide compact ordered priors alongside native categorical features.
- Classification: categorical-statistics exploration.
- Change: add global-prior-smoothed `CarrierDelayRate`, `OriginDelayRate`, and `DestDelayRate`; no counts were exposed as features.
- Result: Eval AUC `0.7605`; status `discard`; −0.0006. The priors did not add signal, and the branch is reverted. This also avoids relying on leakage-prone full-data target statistics.

## Experiment 66 — smoothed route prior (`a5e30e8`)

- Hypothesis: a heavily smoothed route delay rate would provide route information without the failed high-cardinality route category.
- Classification: categorical-statistics follow-up.
- Change: add a route-level train-fitted delay rate with smoothing weight 50.
- Result: Eval AUC `0.7535`; status `discard`; −0.0076. Route target statistics overfit or distort this split; target-encoding experiments are abandoned and the branch is reverted.

## Experiment 67 — week of year (`7f9d0e2`)

- Hypothesis: coarse week-level seasonality would complement exact `DayOfYear` under feature subsampling.
- Classification: compact calendar feature exploration.
- Change: add row-local `WeekOfYear`.
- Result: Eval AUC `0.7598`; status `discard`; −0.0013. Exact day-of-year is preferable.

## Experiment 68 — annual-cycle ablation (`df10a38`)

- Hypothesis: removing the small annual sine/cosine gain would simplify the feature set without changing the ranking materially.
- Classification: ablation/simplification.
- Change: remove `DayOfYearSin`, `DayOfYearCos`, and the unused NumPy import.
- Result: Eval AUC `0.7584`; status `discard`; −0.0027. Retain the cyclic annual features.

## Experiment 69 — route departure-time offset (`7fb174c`)

- Hypothesis: the deviation between a flight's scheduled departure and its route's train-fitted median departure could capture route-specific scheduling effects.
- Classification: compact train-fitted lookup exploration.
- Change: add row-local `RouteDepTimeOffset` from a route median of scheduled departure minutes.
- Result: Eval AUC `0.7592`; status `discard`; −0.0019. The route lookup is not useful here, so the branch is reverted.

## Experiment 70 — bounded loss-guided depth (`e510bc0`)

- Hypothesis: constraining loss-guided trees to `max_depth=10` might reduce variance while retaining the 512-leaf cap.
- Classification: final tree-growth refinement.
- Change: `max_depth=0` → `10` with `grow_policy="lossguide"`.
- Result: Eval AUC `0.7584`; status `discard`; −0.0027. The unbounded depth setting is better; the branch is reverted.

## Final summary

- Best kept commit: `887375a`, Eval AUC `0.7611`.
- Baseline: `c294417`, Eval AUC `0.7203`; total improvement: `+0.0408`.
- Final model: native categorical XGBoost with loss-guided histogram growth, 300 trees, learning rate 0.05, 512 leaves, `min_child_weight=3`, default L2, and `colsample_bytree=0.4`.
- Final features: the original raw fields plus row-local `DayOfYear`, annual sine/cosine projections, `IsWeekend`, `IsMonthEnd`, and `IsMonthEndWeekend`.
- What worked: more boosting capacity, feature subsampling, loss-guided growth, and compact calendar features. What did not: high-cardinality route categories/lookups, target-rate encodings, row sampling, DART, generic departure-time transforms, exact holiday flags, larger leaf budgets, and deeper/longer ensembles.
- The final branch is restored to the best kept commit. `results.tsv` and this research log remain uncommitted for archival by the human.

## Synthesis after 60 experiments

- Current best: `887375a`, Eval AUC `0.7611`, with 300 loss-guided histogram trees, 512 leaves, learning rate 0.05, `min_child_weight=3`, default L2, and `colsample_bytree=0.4`.
- Current features: original raw fields plus `DayOfYear`, `DayOfYearSin`, `DayOfYearCos`, `IsWeekend`, `IsMonthEnd`, and `IsMonthEndWeekend`. These calendar features account for nearly all recent gains.
- Best model refinements: loss-guided growth beat depth-wise growth; 0.4 feature subsampling is now best after feature expansion; the explicit default-L2 line was removed without score loss. Larger leaf budgets, alternate round schedules, and stronger/weaker leaf regularization did not improve.
- Remaining budget is about 39 minutes. Prioritize one or two compact interaction/feature ideas, then stop cleanly with the best kept commit and complete logs.

## Synthesis after 50 experiments

- Current best: `da686c8`, Eval AUC `0.7585`, with 300 loss-guided trees, 512 leaves, learning rate 0.05, `min_child_weight=3`, `reg_lambda=2`, `colsample_bytree=0.6`, and compact calendar features (`DayOfYear`, `IsWeekend`, `IsMonthEnd`, annual sine/cosine).
- The best improvements now come from row-local calendar structure: `DayOfYear` (+0.0030), `IsWeekend` (+0.0022), `IsMonthEnd` (+0.0011), and annual cyclic projections (+0.0002). These are safe under row-wise evaluation and generalize from the date fields.
- Model findings remain consistent: feature subsampling and loss-guided growth beat depth-wise growth; 512 leaves and 300 rounds are local optima. High-cardinality categories, holiday exact flags, generic hour/distance transforms, row sampling, DART, and larger capacity were negative.
- The run has about 55 minutes remaining. Continue only with compact, evidence-backed refinements, keep the best commit as the base, and reserve time for final logging, verification, and `harness.py stop`.

## Synthesis after 40 experiments

- Current best: `2e73de1`, Eval AUC `0.7520`, using 300 trees, learning rate 0.05, loss-guided histogram growth with 512 leaves, `min_child_weight=3`, `reg_lambda=2`, and `colsample_bytree=0.6`.
- Best overall theory: feature subsampling prevents overfitting enough to support deeper or loss-guided trees; loss-guided allocation adds a modest but repeatable gain over depth-wise depth 10. A 512-leaf budget is a narrow sweet spot.
- Stable negatives: route categories, one-hot categorical handling, category-threshold limiting, row sampling, extra sampling levels, cyclic/hour features, DART, larger leaf budgets, and longer/smoother schedules. The failure pattern favors compact native categories and targeted capacity.
- Remaining time should prioritize small, interpretable improvements around the best model (e.g. carefully isolated feature transforms or modest parameter refinements), while avoiding expensive model-family changes and oversized artifacts.

## Synthesis after 30 experiments

- Current best: `169cc38`, Eval AUC `0.7511`, with 300 trees, learning rate 0.05, depth 10, `min_child_weight=3`, `reg_lambda=2`, full-row training, and `colsample_bytree=0.6`.
- The reliable progression is capacity plus tree diversity: 30→100→200→300 trees helped; depth 6→8→9→10 helped; feature subsampling at 0.6 was the largest regularization gain. Mild L2 added another 0.0005.
- The current local optimum is constrained: 400 trees, depth 11, min-child 1, L2 3, finer histogram bins, extra sampling levels, and L1 all failed or tied. High-cardinality route and one-hot categorical experiments were especially poor.
- Evaluation cost is still acceptable (~31 seconds), but artifacts are now ~48 MB; further changes should seek AUC gains without unnecessary size or runtime increases.
- Next direction: test compact, row-local temporal transforms selectively and explore model choices that preserve native categorical partitioning; avoid adding many high-cardinality categories.
