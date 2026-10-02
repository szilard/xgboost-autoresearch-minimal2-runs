# Experiment oct2 — 2026-10-02

## Setup and rules

- Branch: `oct2`, starting commit `92e43e6`.
- Objective: highest harness Eval AUC within the two-hour clock; prefer simpler implementations for effectively equal results.
- Only training data is inspected. Evaluation is exclusively through the unchanged harness. No external data, additional packages, or human-only tools are used.
- Training data: 200,000 rows; eight predictors; binary N/Y target. Installed XGBoost 3.4.1, pandas 3.0.6, scikit-learn 1.9.1. Eight CPU cores.
- Training cap: 60 seconds including preparation. Evaluation cap: 300 seconds with one-row feature preparation.
- Results and this log remain uncommitted; only `train.py` is committed for experiments.

## Initial research

- [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html): adjust model complexity and stochastic regularization deliberately; smaller learning rates require more boosting rounds.
- [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html): depth, child weight, leaf regularization, sampling, and categorical split limits offer distinct controls. Candidate ranges will be adapted to the measured runtime rather than copied as defaults.
- [Native categorical features](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html): categorical partitioning can model groups of airports/carriers; retain consistent training-fitted category levels for inference.
- [Time-related feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html): motivates testing calendar and clock representations for this airline dataset. Any derived feature must be invariant to batch size.

## Experiment 00 — baseline

- Commit: `92e43e6`; classification: baseline.
- Hypothesis: establish the reference with the starter unchanged (30 trees, depth 6, learning rate 0.1).
- Status: running through `python3 harness.py run`.

- Result: Eval AUC **0.7203**; training phase 1.1s; evaluation 31.0s; total 32.0s. Kept as the initial reference.

## Experiment 01 — more boosting rounds

- Classification: follow-up to baseline.
- Hypothesis: 30 trees underfit; 300 trees should capture remaining signal without changing feature representation or tree depth.
- Change: `n_estimators=300`; all other starter choices unchanged.
- Source: initial XGBoost tuning notes.

- Commit: `2173302`. Result: **0.7342** AUC (+0.0139); training 2.5s, evaluation 30.6s. Keep: clear improvement for one parameter change.

## Experiment 02 — simplify categorical preparation

- Classification: ablation/simplification of experiment 01.
- Hypothesis: explicitly masking unknown values is redundant because pandas categorical construction with fixed levels already maps unknown values to missing. Removing the mask should preserve features exactly and reduce row-wise evaluation cost.
- Change: remove `.where(...isin(...))` from each categorical conversion.
- Validation planned: batch versus single-row equality and an unknown-category case, using training rows only.

- Commit: 81d7588. Result: **0.7342** AUC; decision: **keep**. Run time: 23.4s (training 2.5s, eval 20.9s, ok)
- Interpretation: Identical AUC with less code; evaluation fell from 30.6s to 20.9s. Keep the simplification.

## Experiment 03 — explicit calendar date

- Classification: exploration of feature representation.
- Hypothesis: combining month and day exposes both contiguous seasonal effects and date-specific disruptions that otherwise need several tree splits.
- Change: numeric day-of-year and categorical flight date; retain all original features and model settings.
- Sources: [Naul airline-delay study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) motivates day-of-year; [Movva and Menon](https://cs229.stanford.edu/proj2016/report/MenonMovva-PredictingFlightDelays-report.pdf) motivate retaining numerical and categorical calendar representations. No external data are imported.

- Commit: 657bbfc. Result: **0.7500** AUC; decision: **keep**. Run time: 30.8s (training 2.6s, eval 28.1s, ok)
- Interpretation: Calendar representation adds 0.0158 AUC with six straightforward lines. Keep; next test whether tree depth limits date/airport interactions.

## Experiment 04 — deeper calendar interactions

- Classification: follow-up to experiment 03.
- Hypothesis: depth 6 limits joint date, airport, carrier, and time effects. Increase only max_depth to 8 to measure the capacity benefit before adding regularization.
- Source: the initial parameter documentation and Movva/Menon airline study; its preferred depth motivates a test, not an assumption of transfer.

- Commit: c9843e8. Result: **0.7459** AUC; decision: **discard**. Run time: 32.5s (training 4.1s, eval 28.4s, ok)
- Interpretation: Depth 8 loses 0.0041 AUC, indicating excess capacity with current categorical splits. Revert to depth 6 and test leaf regularization.

## Experiment 05 — minimum leaf support

- Classification: exploration of regularization, motivated by depth-8 overfitting.
- Hypothesis: native airport/date partitions can form noisy small leaves; min_child_weight=20 should require stronger evidence while preserving depth-6 interactions.
- Change: add min_child_weight=20 to experiment 03. Other parameters fixed.
- Source: XGBoost parameter documentation, initial research.

- Commit: 89ac008. Result: **0.7505** AUC; decision: **keep**. Run time: 30.7s (training 2.6s, eval 28.1s, ok)
- Interpretation: Minimum child weight improves AUC by 0.0005 at essentially unchanged cost, with only one parameter added. Keep.

## Experiment 06 — origin and date interaction

- Classification: exploration of categorical feature crosses.
- Hypothesis: disruptions are local to an airport and date; a direct OriginDate feature lets native categorical splits share evidence across these pairs without spending multiple splits on the interaction.
- Change: add one origin/month/day categorical cross. Fit levels on training data; cache category indexes to keep row preparation practical. Unknown pairs map to missing.
- Source: [Google feature crosses](https://developers.google.com/machine-learning/crash-course/categorical-data/feature-crosses), read before this category of change, and the airline studies above. Sparsity is a concern, so begin with one cross and evaluate through the harness.

- Commit: 9acdaf9. Result: **0.7343** AUC; decision: **discard**. Run time: 68.2s (training 17.3s, eval 50.9s, ok)
- Interpretation: OriginDate loses 0.0162 AUC and more than doubles runtime. Sparse native category interactions overfit; revert. Geography inferred from training route distances is a possible smoother alternative.

## Experiment 07 — constrain categorical partitions

- Classification: follow-up to the regularization gain in experiment 05 and overfitting in experiment 06.
- Hypothesis: limiting categories considered per split to 16, down from the default 64, will curb noisy airport/date partitions.
- Change: `max_cat_threshold=16`; original feature set from experiment 05.
- Source: [XGBoost categorical parameters](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-categorical-feature).

### Research queue

[Classical multidimensional scaling](https://scikit-learn.org/stable/modules/generated/sklearn.manifold.ClassicalMDS.html) and [the scikit-learn example](https://scikit-learn.org/stable/auto_examples/manifold/plot_mds.html) suggest a later exploration: derive airport coordinates using only route distances observed in train.csv. Such coordinates might allow regional effects to generalize across airports without sparse airport/date identities. No external coordinates will be used.

- Commit: b661458. Result: **0.7533** AUC; decision: **keep**. Run time: 30.1s (training 2.2s, eval 27.9s, ok)
- Interpretation: AUC improves by 0.0028, and training is slightly faster. Restricting categorical partitions is a productive regularizer.

## Experiment 08 — smaller boosting steps

- Classification: follow-up to the regularized categorical model.
- Hypothesis: halve the learning rate while doubling rounds to retain similar overall boosting strength with smoother updates and more chances to average noisy category partitions.
- Change: 600 trees at learning_rate=0.05; all other settings from experiment 07.
- Source: XGBoost tuning notes on learning-rate shrinkage and additional rounds.
- Independent training-data prototype: all 284 airports form a connected route-distance graph; three-dimensional ClassicalMDS coordinates fit in 0.18s. This only checks feasibility for a future feature experiment and is not a predictive evaluation.

- Commit: b141cb3. Result: **0.7528** AUC; decision: **discard**. Run time: 32.6s (training 3.7s, eval 28.9s, ok)
- Interpretation: Matched-strength smaller steps lose 0.0005 AUC and double model size. Revert to 300 trees at 0.1; more trees are not uniformly beneficial.

## Experiment 09 — ablate categorical date

- Classification: ablation/simplification of experiment 03, with current regularization.
- Hypothesis: numeric day-of-year may capture the calendar benefit on its own; dropping categorical FlightDate could reduce noisy noncontiguous date grouping and inference work.
- Change: remove FlightDate only. Keep numeric DayOfYear and all original inputs.

- Commit: dab4d24. Result: **0.7423** AUC; decision: **discard**. Run time: 27.8s (training 2.2s, eval 25.6s, ok)
- Interpretation: Removing FlightDate loses 0.0110 AUC. Both calendar representations are useful; categorical dates capture effects not recovered by numeric thresholds.

## Synthesis after ten runs (00–09)

- Best: **0.7533**, commit b661458, versus baseline 0.7203 (+0.0330).
- More boosting rounds, explicit calendar dates, and conservative categorical partitions helped. The numeric-only calendar ablation lost 0.0110, demonstrating the contribution of FlightDate.
- Depth 8 and a sparse OriginDate cross hurt; greater capacity without shared statistical structure is not the next priority. Halving learning rate at matched boosting strength also failed.
- Simpler category handling retained predictions and cut baseline evaluation time by one third.
- Current theory: date-specific disruption patterns matter, but sparse categorical identities overfit. A smooth geographic representation may share evidence across nearby airports.
- Research refresh: searched [ClassicalMDS](https://scikit-learn.org/stable/modules/generated/sklearn.manifold.ClassicalMDS.html) and [XGBoost early stopping](https://xgboost.readthedocs.io/en/release_3.3.0/python/sklearn_estimator.html). Next: training-only geographic coordinates; later consider a single training-derived validation split for early stopping, without cross-validation or refitting.

## Experiment 10 — infer airport geometry from training distances

- Classification: exploration of a new, unsupervised feature family.
- Hypothesis: coordinates inferred from route distances let trees share date/season effects across nearby airports, avoiding the sparsity of OriginDate.
- Change: build a symmetric route-distance graph using training medians, complete missing distances with shortest paths, fit two-dimensional ClassicalMDS, and look up two coordinates for both endpoints in prepare.
- All fitting uses train.csv only; no labels enter the coordinate lookup, and no external geography is used. Source: scikit-learn ClassicalMDS documentation above.

- Commit: f9e0b10. Result: **0.7560** AUC; decision: **keep**. Run time: 37.8s (training 2.6s, eval 35.2s, ok)
- Interpretation: Training-only geographic coordinates improve AUC by 0.0027. The standard unsupervised lookup adds modest runtime (35.2s evaluation), with row invariance and serialization verified. Keep.

## Experiment 11 — deeper regularized geographic interactions

- Classification: follow-up to experiment 10.
- Hypothesis: depth 8 can now combine date, region, carrier, and departure time, while min_child_weight=20 and max_cat_threshold=16 curb the overfitting observed in experiment 04.
- Difference from experiment 04: this is the first deeper model with both stronger regularizers and numeric regional features; it tests capacity under a meaningfully changed representation, not a repeat of the earlier setting.
- Change: max_depth=8 only.

- Commit: 76be65b. Result: **0.7564** AUC; decision: **keep**. Run time: 38.3s (training 3.1s, eval 35.1s, ok)
- Interpretation: Depth 8 now improves AUC by 0.0004 with little runtime change. Capacity becomes useful after regularization and geographic features; keep.

## Experiment 12 — regional date interaction

- Classification: follow-up to the geographic feature gain, with a less sparse variant of experiment 06.
- Hypothesis: broad regions can pool local disruptions across nearby airports, making region/date identities more robust than individual airport/date identities.
- Change: cluster the training-derived airport coordinates into 12 regions with deterministic KMeans; add one categorical OriginRegionDate cross. Counts and labels are not used to fit geography or regions.
- Source: [scikit-learn KMeans documentation](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html), read before implementing clustering, and earlier feature-cross documentation.

- Commit: 1aa08cb. Result: **0.7548** AUC; decision: **discard**. Run time: 44.2s (training 4.8s, eval 39.4s, ok)
- Interpretation: Pooling airport/date identities into 12 regions still loses 0.0016 AUC and adds code/runtime. Keep the numeric coordinates alone and revert clustering.

## Experiment 13 — departure clock components

- Classification: exploration of scheduled-time feature engineering.
- Hypothesis: hour and minute-of-hour expose recurring schedule/bank patterns that require many raw-HHMM thresholds to isolate across the day.
- Change: add DepartureHour and DepartureMinute as numeric features. Keep raw scheduled time and all other current features.
- Source: initial [scikit-learn time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) and airline departure-time studies. These are deterministic row-local transforms.

- Commit: 775c03b. Result: **0.7550** AUC; decision: **discard**. Run time: 41.0s (training 3.2s, eval 37.8s, ok)
- Interpretation: Clock components lose 0.0014 AUC and increase evaluation cost. Raw scheduled time already captures the useful ordering; revert.

## Experiment 14 — stochastic regularization

- Classification: exploration of row and feature subsampling.
- Hypothesis: sampling 80% of rows and columns for each tree may reduce reliance on noisy date partitions and diversify interactions around the dominant scheduled-departure-time signal.
- Change: subsample=0.8, colsample_bytree=0.8; model size and feature set unchanged.
- Source: XGBoost tuning notes and subsampling parameter documentation from initial research.
- Training-model diagnostic only: best model gain importance ranks scheduled departure time first, followed by FlightDate and origin geography. This is not an additional evaluation metric.

- Commit: 46f4d0a. Result: **0.7503** AUC; decision: **discard**. Run time: 38.3s (training 3.0s, eval 35.2s, ok)
- Interpretation: Subsampling loses 0.0061 AUC. Three consecutive proposals failed, so revisit external research and change the learning objective rather than random parameter tweaking.

## Research pause after experiments 12–14

All three recent variants failed. The best remains 0.7564. Fresh search: [XGBoost learning to rank](https://xgboost.readthedocs.io/en/release_3.2.0/tutorials/learning_to_rank.html) and ranking parameter documentation. RankNet uses pairwise logistic loss; mean pair sampling can spread learning across the whole ranking rather than its top. This motivates a distinct objective experiment. Internal query grouping will use all training rows as one group, matching global binary ranking; the final metric remains exclusively harness Eval AUC.

## Experiment 15 — pairwise ranking objective

- Classification: exploration of a meaningfully different training objective.
- Hypothesis: optimizing sampled positive/negative ordering may improve AUC compared with pointwise probability loss.
- Change: XGBRanker with rank:pairwise, one training query, mean pair sampling with two pairs per row, and disabled query normalization to avoid shrinking one huge query below the leaf-weight threshold. Preserve the current tree settings and features.
- A small predict_proba adapter applies a sigmoid to rank scores for the unchanged harness interface. No additional evaluation or refit is introduced.

- Commit: 8c20eb0. Result: **0.7123** AUC; decision: **discard**. Run time: 54.3s (training 18.7s, eval 35.5s, ok)
- Interpretation: Pairwise ranking performs poorly at 0.7123. Training-row raw score range (-1.44 to 1.41 on 1000 rows) rules out sigmoid clipping as the cause. Revert to the simpler classification objective.

## Experiment 16 — early stopping on training-derived validation

- Classification: exploration of stopping criteria.
- Hypothesis: fixed 300-round models may overfit categorical dates; a single stratified 10% validation split from train.csv can select a useful stopping point.
- Change: learning_rate=0.05, cap of 2000 trees, 50-round AUC patience; train once on the remaining 90%. No cross-validation, retraining, or alternative final metric.
- Source: [XGBoost estimator and early-stopping documentation](https://xgboost.readthedocs.io/en/stable/python/sklearn_estimator.html), read immediately before implementation. Prediction uses best_iteration automatically; the harness evaluates the saved fitted model as usual.

- Commit: 7463074. Result: **0.7554** AUC; decision: **discard**. Run time: 40.3s (training 4.8s, eval 35.5s, ok)
- Interpretation: Early stopping selected 454 trees but yielded 0.7554 AUC. The stopping benefit did not offset reserving 10% of training rows. Revert; no full-data refit is performed.

## Experiment 17 — third geographic coordinate

- Classification: follow-up to the strongest recent feature gain in experiment 10.
- Hypothesis: a two-dimensional embedding compresses a curved and imperfect route-distance graph; a third coordinate may distinguish airports collapsed in the first two dimensions.
- Change: ClassicalMDS n_components=3 and a third origin/destination coordinate. All model settings return to experiment 11.
- Source: the previously researched ClassicalMDS formulation supports low-dimensional distance-preserving representations; this tests the retained dimension count.

- Commit: 6bcd483. Result: **0.7556** AUC; decision: **discard**. Run time: 41.6s (training 3.2s, eval 38.4s, ok)
- Interpretation: A third geographic coordinate loses 0.0008 AUC and increases evaluation work. Revert to the two-dimensional representation.

## Research refresh — honest target lookups

Read [scikit-learn target-encoding guidance](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html). It illustrates how using a row's own target in its encoding can overfit. This run does not introduce cross-validation: instead, reserve one fixed 25% partition only for lookup fitting, then train the trees once on the disjoint 75%. Call TargetEncoder.fit, never fit_transform. There are no scores on the partition and no refit. The only decision metric is the unchanged harness Eval AUC.

## Experiment 18 — delay-rate lookup features from disjoint training rows

- Classification: exploration of supervised group statistics with honest sample separation.
- Hypothesis: smoothed airport/date and date delay probabilities can capture local disruptions more robustly than sparse categorical identities.
- Change: fit three smooth=20 target encodings (OriginDate, DestDate, FlightDate) on 50,000 reserved training rows; store compact mappings and the prior. Train the existing XGBoost on the other 150,000 rows.
- prepare uses row keys and fixed mappings only; it never uses an incoming target to compute a feature. Unknown keys use the lookup prior. No row counts are output as features.
- Cost/tradeoff: fewer rows directly fit the trees, but the other labels contribute to learned lookup features. A substantial improvement is needed to justify the added code.

- Commit: b1f7634. Result: **0.7528** AUC; decision: **discard**. Run time: 46.0s (training 3.0s, eval 42.9s, ok)
- Interpretation: Honest target lookups yield 0.7528, below 0.7564, and add 27 lines. The benefit does not offset reserving 25% of rows from tree fitting. Revert the whole encoding design.

## Experiment 19 — stronger L2 leaf regularization

- Classification: follow-up to categorical regularization gains and recent overfitting failures.
- Hypothesis: even with a minimum child weight, small date/airport leaves can receive overly large updates. reg_lambda=20 should shrink leaf weights continuously rather than removing data or features.
- Change: set reg_lambda=20, versus the default 1, on the best full-data depth-8 geographic model.
- Source: XGBoost parameter documentation on L2 leaf-weight regularization.

- Commit: 36bab5e. Result: **0.7593** AUC; decision: **keep**. Run time: 39.3s (training 4.1s, eval 35.3s, ok)
- Interpretation: L2 shrinkage improves AUC by 0.0029 with one parameter and negligible extra runtime. This supports regularizing leaf updates instead of discarding training rows or adding sparse feature identities.

## Synthesis after twenty runs (00–19)

- Best: **0.7593**, commit 36bab5e, a gain of 0.0390 over baseline.
- Two-dimensional airport coordinates helped, and depth 8 became mildly useful after categorical regularization. A third coordinate and regional date cross failed.
- Strong L2 leaf shrinkage is the latest clear gain. Simple row/column subsampling alone hurt; pairwise ranking was substantially worse.
- Early stopping and honest target lookups, each reserving some training rows, did not beat the full-data model. Clock-component features also failed.
- Current theory: preserve full training support and regularize high-variance category/date interactions. Better features should add shared structure, as geography did, rather than sparse identities.
- Research refresh: searched/read [XGBoost random forests](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) and categorical split-strategy documentation. New directions: average randomized trees within boosting, then contrast partitioned categories with native one-hot splits.

## Experiment 20 — boosted randomized forests

- Classification: exploration of a different boosting architecture.
- Hypothesis: three randomized trees per round can average sampling noise, addressing the variance that made single-tree subsampling fail in experiment 14.
- Change: num_parallel_tree=3, subsample=0.8, colsample_bynode=0.8; retain 300 rounds and current L2 regularization. Feature sampling happens per split rather than dropping a feature for an entire tree.
- Source: XGBoost random-forest tutorial above. This remains one fitted classifier, one harness evaluation, and one serial experiment.

- Commit: b308ee8. Result: **0.7566** AUC; decision: **discard**. Run time: 44.6s (training 9.1s, eval 35.5s, ok)
- Interpretation: Boosted randomized forests score 0.7566, below the simpler deterministic model, and double training cost. Revert.

## Experiment 21 — simplify row preparation without changing features

- Classification: ablation/simplification of the best model's implementation.
- Hypothesis: reuse categorical dtypes and numeric lookup indexes, retrieve each airport's coordinates together, and construct one final DataFrame instead of repeatedly inserting columns. This should preserve every feature exactly while reducing row-wise overhead.
- Change: prepare implementation only; model, features, and train-fitted geography unchanged.
- Validation: compare old and new feature frames exactly on training rows including an unknown airport, then verify row invariance and serialization. Keep only if harness AUC is unchanged and runtime improves.

- Commit: 3892c89. Result: **0.7593** AUC; decision: **keep**. Run time: 20.6s (training 3.1s, eval 17.5s, ok)
- Interpretation: Exact feature equivalence confirmed; AUC remains 0.7593. Evaluation falls from 35.3s to 17.5s by removing repeated frame construction and dtype work. Keep the simpler execution path.

## Experiment 22 — stronger L2 regime

- Classification: follow-up to experiment 19.
- Hypothesis: the clear gain from lambda 1 to 20 indicates residual leaf-weight variance. Lambda 100 tests a substantially more conservative regime, especially for leaves near the child-weight floor.
- Change: reg_lambda=100 only; retain full training data and the faster equivalent preparation.

- Commit: 055e0f2. Result: **0.7614** AUC; decision: **keep**. Run time: 20.7s (training 3.2s, eval 17.5s, ok)
- Interpretation: Lambda 100 improves AUC by another 0.0021 without extra code or runtime. Stronger regularization remains productive; test an upper bracket rather than minor nearby tweaks.

## Experiment 23 — upper bracket for L2 shrinkage

- Classification: follow-up to experiments 19 and 22.
- Hypothesis: successive gains at lambda 20 and 100 suggest the optimum is in a strongly regularized regime. Lambda 500 is a fivefold upper bracket that should reveal whether further shrinkage starts underfitting.
- Change: reg_lambda=500 only. This tests a substantially different effective leaf penalty, not a cosmetic parameter variation.

- Commit: 5451bf3. Result: **0.7619** AUC; decision: **keep**. Run time: 20.7s (training 3.3s, eval 17.5s, ok)
- Interpretation: Lambda 500 adds 0.0005 AUC. Returns are diminishing, so retain it and switch to a different mechanism rather than continue an open-ended penalty sweep.

## Experiment 24 — one-hot rather than partitioned category splits

- Classification: exploration of categorical split strategy.
- Hypothesis: selecting individual airport/date categories may reduce arbitrary groupings and capture exceptional dates more directly. Strong current L2 could also make this representation underfit; the result will distinguish the regimes.
- Change: max_cat_to_onehot=512, enough to use native one-hot splits for all current categorical columns. Feature matrices and other model settings unchanged.
- Source: XGBoost categorical tutorial and parameters, refreshed at the twenty-run synthesis.

- Commit: fd37798. Result: **0.7417** AUC; decision: **discard**. Run time: 19.8s (training 2.5s, eval 17.3s, ok)
- Interpretation: Native one-hot splits lose 0.0202 AUC under lambda 500 and 300 rounds. This could reflect underfitting of individual categories, so test one adapted one-hot configuration before abandoning the strategy.

## Experiment 25 — allow one-hot categories enough capacity

- Classification: follow-up to experiment 24's possible underfitting.
- Hypothesis: one-hot splits need more rounds to cover many distinct dates/airports, and individual-category leaves should not inherit the very strong penalty optimized for grouped category partitions.
- Change: native one-hot threshold 512 with reg_lambda=20 and 1000 trees at learning_rate=0.1. Same features and depth.
- Difference from experiment 24: explicitly relax its two likely capacity bottlenecks. This is the final planned broad test of this split strategy if it remains uncompetitive.

- Commit: 1a8990e. Result: **0.7586** AUC; decision: **discard**. Run time: 22.9s (training 5.3s, eval 17.6s, ok)
- Interpretation: More capacity improves one-hot performance to 0.7586, but it remains below 0.7619 with over three times as many trees. Retain partitioned categorical splits.

## Experiment 26 — carrier and airport interactions

- Classification: exploration of persistent categorical interactions.
- Hypothesis: carrier operations differ by airport, and direct CarrierOrigin/CarrierDest identities may expose these stable effects with fewer tree splits.
- Difference from failed OriginDate: training has 1,551 CarrierOrigin and 1,559 CarrierDest combinations, versus 43,026 OriginDate combinations. These descriptors guide the experiment; no frequency/count features are added.
- Change: two categorical crosses with training-fitted, cached dtypes. Keep strong L2 regularization and all prior features.
- Source: prior feature-cross guidance and airline studies; this adapts the idea to substantially less sparse keys.

- Commit: 328588b. Result: **0.7485** AUC; decision: **discard**. Run time: 26.2s (training 4.2s, eval 22.0s, ok)
- Interpretation: Even less-sparse carrier/airport identities lose 0.0134 AUC. Direct categorical crosses have consistently hurt; retain the simpler shared geographic representation.

## Experiment 27 — finer numerical split resolution

- Classification: exploration of histogram resolution.
- Hypothesis: 256 histogram bins merge some of the 365 day-of-year values and 284 airport coordinates, and coarsen departure times. max_bin=512 may preserve useful thresholds while strong L2 limits added variance.
- Change: max_bin=512 only.
- Source: XGBoost max_bin documentation: greater split resolution trades additional computation for potential split quality. After the recent failed categorical variants, focus on continuous shared structure.

- Commit: 354acd1. Result: **0.7614** AUC; decision: **discard**. Run time: 20.6s (training 3.3s, eval 17.3s, ok)
- Interpretation: Finer histogram bins lose 0.0005 AUC. The default numerical resolution is adequate; revert.

## Experiment 28 — additive carrier effect

- Classification: exploration of structural interaction constraints.
- Hypothesis: failed carrier/airport crosses suggest that highly specific carrier interactions may overfit. Treat carrier as its own additive component while letting all other features interact freely.
- Change: disjoint interaction groups: UniqueCarrier alone, and every other feature together. Disjoint groups avoid the union behavior of overlapping constraints.
- Source: [XGBoost feature interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html), searched and read before this new category of change.

- Commit: 4106729. Result: **0.7520** AUC; decision: **discard**. Run time: 20.1s (training 2.9s, eval 17.3s, ok)
- Interpretation: The additive carrier restriction loses 0.0099 AUC. Carrier interactions are useful; the failed explicit crosses do not justify removing interactions altogether.

## Experiment 29 — loss-guided tree growth

- Classification: exploration of tree-growth structure.
- Hypothesis: allocate a comparable leaf budget to the most useful local interactions instead of imposing a uniform maximum depth. The best current model has median 67 leaves per tree (range 29–119), so max_leaves=64 is a meaningful matched-complexity starting point.
- Change: grow_policy=lossguide, max_depth=0, max_leaves=64; other parameters and features unchanged.
- Source: [XGBoost tree-booster parameters](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster). The leaf statistics are model metadata, not an additional predictive metric.

- Commit: 0f416c9. Result: **0.7630** AUC; decision: **keep**. Run time: 22.5s (training 4.9s, eval 17.6s, ok)
- Interpretation: Loss-guided growth improves AUC by 0.0011 with a comparable leaf budget. Flexible depth is useful when total leaves and leaf weights remain controlled.

## Synthesis after thirty runs (00–29)

- Best: **0.7630**, commit 0f416c9, versus baseline 0.7203 (+0.0427).
- L2 regularization from 20 to 100 to 500 produced further gains, with diminishing returns. Loss-guided growth at 64 leaves adds another improvement.
- Cached preparation preserved features and AUC exactly while reducing evaluation from about 35s to 17.5s.
- Boosted randomized forests, native one-hot variants, carrier/airport crosses, finer histograms, and an additive-only carrier effect all failed. Carrier interactions matter, but explicit crossed identities were unhelpful.
- Current theory: preserve categorical partitioning and meaningful interactions; control variance through weight shrinkage and flexible, bounded leaf allocation.
- Research refresh: searched tree-growth policy, interaction constraints, and [MDS methods](https://scikit-learn.org/stable/modules/generated/sklearn.manifold.MDS.html). A later feature direction is to refine the two-dimensional geometry with metric MDS rather than adding more dimensions or categories.

## Experiment 30 — larger loss-guided leaf budget

- Classification: follow-up to experiment 29.
- Hypothesis: loss-guided trees can spend additional leaves on localized useful interactions without the broad overfitting seen in an unconstrained depth expansion. Test whether the new 64-leaf cap is now restrictive under lambda 500.
- Change: max_leaves=128; all other settings unchanged.

- Commit: 5c0e2c0. Result: **0.7634** AUC; decision: **keep**. Run time: 25.2s (training 7.7s, eval 17.5s, ok)
- Interpretation: 128 loss-guided leaves improve AUC by 0.0004; training remains well within the limit at 7.7s including setup. Keep, then explore geometry quality rather than further leaf-count escalation.

## Experiment 31 — metric refinement of airport geometry

- Classification: follow-up to the geographic feature gain.
- Hypothesis: classical scaling fits centered inner products; metric MDS may preserve pairwise route-derived distances better in two dimensions and improve useful spatial thresholds.
- Change: replace ClassicalMDS with metric MDS initialized by classical scaling, one deterministic initialization, and 100 iterations. Same two features per endpoint, same distance graph, no external data or targets in the lookup.
- Source: [scikit-learn MDS documentation](https://scikit-learn.org/stable/modules/generated/sklearn.manifold.MDS.html), researched at the thirty-run synthesis.

- Commit: 602f1fa. Result: **0.7634** AUC; decision: **discard**. Run time: 25.4s (training 7.7s, eval 17.7s, ok)
- Interpretation: Metric MDS ties 0.7634 at reported precision but adds an iterative fitting step and more settings. Prefer the simpler classical scaling and revert.

## Experiment 32 — sparse date interaction under strong regularization

- Classification: follow-up combining the earlier OriginDate exploration with the successful regularization regime.
- Hypothesis: very strong L2 shrinkage and a smaller category-partition search may control the variance that made OriginDate fail before.
- Explicit difference from experiment 06: lambda is now 500 instead of 1; max_cat_threshold is 16 instead of 64; shared geometry and bounded loss-guided growth are present. This is one deliberate retest under a fundamentally different regularization regime.
- Change: add OriginDate, represented as a categorical airport-code/day-of-year key with a training-fitted cached dtype. Integer keys avoid repeated string construction; unknown airports yield missing categories. No counts are features.

- Commit: 2a9ce00. Result: **0.0000** AUC; decision: **crash**. Run time: 60.0s (training 60.0s, eval 0.0s, timeout-training)
- Interpretation: The harness killed training at 60 seconds, before evaluation. The high-cardinality cross is computationally unsuitable with the current loss-guided model; no AUC was obtained and the run is reverted.

## Experiment 33 — more rounds under strong shrinkage

- Classification: follow-up to the successful high-L2 loss-guided model.
- Hypothesis: lambda 500 suppresses leaf updates strongly, so the current 300 rounds may stop before useful residual structure has been learned. Increase rounds while preserving the variance controls.
- Change: n_estimators=900; remove the failed sparse cross by returning to experiment 30 first.
- Difference from experiment 08: stronger L2, geographic features, and loss-guided growth fundamentally change the boosting-duration tradeoff. This tests additional total boosting, not matched-strength smaller steps.
- Runtime estimate from the kept model: roughly 20–25s training, comfortably below the harness cap; actual timing remains authoritative.

- Commit: b63c618. Result: **0.7564** AUC; decision: **discard**. Run time: 38.8s (training 20.4s, eval 18.4s, ok)
- Interpretation: 900 rounds lose 0.0070 AUC despite strong L2. Additional total boosting overfits; return to 300 rounds.

## Experiment 34 — stronger minimum leaf support

- Classification: follow-up to regularization gains and overfitting in experiment 33.
- Hypothesis: a larger minimum Hessian sum will suppress small noisy local partitions before they are formed; this complements L2 weight shrinkage rather than changing boosting duration.
- Change: min_child_weight=100 instead of 20, with 300 rounds and current loss-guided model.
- Source: XGBoost minimum-child-weight parameter documentation from initial research.

- Commit: 78a6370. Result: **0.7640** AUC; decision: **keep**. Run time: 25.7s (training 8.0s, eval 17.7s, ok)
- Interpretation: Minimum child weight 100 improves AUC by 0.0006 at similar runtime. Retain the stronger support requirement.

## Experiment 35 — reject weak split gains

- Classification: follow-up to improved leaf regularization.
- Hypothesis: loss-guided growth can spend its final leaves on tiny apparent gains. gamma=1 requires a meaningful loss reduction before a split and may prune weak interactions that remain after support and L2 controls.
- Change: gamma=1 only. Source: XGBoost minimum-split-loss parameter documentation.

- Commit: 04863ec. Result: **0.7631** AUC; decision: **discard**. Run time: 22.8s (training 5.4s, eval 17.4s, ok)
- Interpretation: Gamma 1 reduces runtime but loses 0.0009 AUC. Small split gains still contribute useful signal; revert the extra threshold.

## Experiment 36 — cyclic departure-time representation

- Classification: exploration of periodic time features.
- Hypothesis: sine/cosine of scheduled minutes let a split pool times around midnight and express periodic bands with fewer leaves. Unlike the failed hour/minute features, these change the geometry of time neighborhoods.
- Change: add two row-local cyclic departure-time features while retaining raw HHMM.
- Source: [scikit-learn cyclic time feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html), read in the initial research.

- Commit: 506d2d2. Result: **0.7647** AUC; decision: **keep**. Run time: 25.7s (training 7.7s, eval 18.1s, ok)
- Interpretation: Cyclic time features improve AUC by 0.0007 with four clear lines and negligible runtime cost. Keep the periodic representation.

## Experiment 37 — distance-adjusted clock interaction

- Classification: follow-up/exploration from the useful cyclic time representation.
- Hypothesis: a simple departure-clock-plus-distance proxy exposes diagonal time/distance boundaries that axis-aligned splits otherwise approximate with several leaves; destination conditions may vary with that phase.
- Change: add (departure_minutes + Distance / 8) modulo 1440. The fixed 8 miles/minute scale is a rough feature-design assumption, not a measured travel time or calibrated arrival prediction.
- Source/motivation: earlier airline studies discuss scheduled time and distance; this specific interaction is an experimental inference from those inputs. No external schedules or geographic metadata are added.

- Commit: acd917d. Result: **0.7651** AUC; decision: **keep**. Run time: 25.7s (training 7.6s, eval 18.1s, ok)
- Interpretation: The one-line time/distance proxy improves AUC by 0.0004 at unchanged runtime. Keep the lightweight interaction.

## Experiment 38 — remove redundant day-of-month input

- Classification: ablation/simplification.
- Hypothesis: the complete numeric and categorical date features already encode day-of-month. Removing the standalone categorical day may reduce spurious pooling across unrelated months and slightly simplify row preparation.
- Change: drop DayofMonth from model categorical columns only; continue using it inside prepare to compute the full date.

- Commit: 18c7a8a. Result: **0.7647** AUC; decision: **discard**. Run time: 24.6s (training 7.3s, eval 17.3s, ok)
- Interpretation: Dropping standalone DayofMonth loses 0.0004 AUC for only a small runtime reduction. Retain the feature; it still helps pooling across dates.

## Experiment 39 — L1 leaf regularization

- Classification: exploration of a complementary regularizer.
- Hypothesis: L1 can set weak leaf updates to zero instead of only shrinking them continuously. reg_alpha=10 may suppress noisy residual structure while preserving strong signals under the current L2 penalty.
- Change: reg_alpha=10 only; all training rows and current features retained.
- Source: XGBoost regularization parameter documentation. Research refresh in progress also covers gradient-based CPU sampling and learning-rate callbacks for the next synthesis.

- Commit: 13f8f44. Result: **0.7631** AUC; decision: **discard**. Run time: 24.6s (training 6.6s, eval 18.0s, ok)
- Interpretation: L1 regularization loses 0.0020 AUC. Continuous L2 shrinkage and leaf support work better here than thresholding gradients with alpha 10.

## Synthesis after forty runs (00–39)

- Best: **0.7651**, commit acd917d (+0.0448 over baseline).
- A larger leaf support threshold, cyclic departure time, and a one-line time/distance interaction improved the model. The raw day-of-month feature still helped slightly.
- Metric MDS tied the simpler geometry; gamma and L1 penalties hurt. Extending to 900 rounds clearly overfit. Reintroducing the high-cardinality OriginDate feature timed out during training and was reverted without an AUC.
- Current theory: keep the richer time geometry and regularized local interactions, but control how late boosting updates accumulate.
- Research refresh: [gradient-based sampling on CPU](https://xgboost.readthedocs.io/en/release_3.2.0/parameter.html), [LearningRateScheduler API](https://xgboost.readthedocs.io/en/latest/python/python_api.html#xgboost.callback.LearningRateScheduler), and [DART dropout](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html). New planned directions are scheduled shrinkage, informative row sampling, and a bounded dropout trial.

## Experiment 40 — gradually decay learning rate

- Classification: exploration of the boosting schedule.
- Hypothesis: larger early steps can learn broad effects, while smaller late steps reduce noisy residual updates. Match approximately the original total learning-rate sum so this does not simply repeat the overlong 900-round test.
- Change: 500 rounds, initial learning rate 0.12, decayed by 0.997 each round through LearningRateScheduler; summed rates are about 31 versus the previous 30.
- Source: freshly researched callback API above. No validation split or refit is introduced.

- Commit: ca43bb3. Result: **0.7652** AUC; decision: **keep**. Run time: 31.2s (training 12.3s, eval 18.8s, ok)
- Interpretation: Scheduled shrinkage adds 0.0001 AUC. The gain is small, but the implementation is one standard callback and training remains only 12.3s; keep provisionally and favor simpler alternatives if later results tie.

## Experiment 41 — gradient-based row sampling

- Classification: exploration of informative sampling.
- Hypothesis: gradient/Hessian-based sampling can preserve informative observations while reducing redundant row work, avoiding the indiscriminate information loss of earlier uniform sampling.
- Change: tree_method=hist, sampling_method=gradient_based, subsample=0.5; keep all features and the selected schedule.
- Source: [XGBoost 3.2 parameter documentation](https://xgboost.readthedocs.io/en/release_3.2.0/parameter.html) and its [CPU support release note](https://xgboost.readthedocs.io/en/release_3.2.0/changes/v3.2.0.html). Installed version is 3.4.1.

- Commit: ed6c26d. Result: **0.7610** AUC; decision: **discard**. Run time: 32.6s (training 13.9s, eval 18.7s, ok)
- Interpretation: Gradient-based sampling lowers AUC to 0.7610 and slightly increases training time. Full-row training remains preferable; revert all sampling additions.

## Experiment 42 — relative route geometry

- Classification: follow-up to geographic and time/distance feature gains.
- Hypothesis: differences between destination and origin coordinates expose route direction directly, pooling patterns across routes without high-cardinality route identities. Trees otherwise need several endpoint thresholds to approximate these diagonal boundaries.
- Change: add two coordinate-difference features inside prepare. The coordinates still come solely from training route distances; no external airport metadata or target statistics are used.
- Source/motivation: previously researched geographic embeddings and feature interactions; this particular combination is an experimental inference.

- Commit: 3d4d94e. Result: **0.7658** AUC; decision: **keep**. Run time: 32.1s (training 13.4s, eval 18.7s, ok)
- Interpretation: Relative route geometry adds 0.0006 AUC with two straightforward lines and little runtime change. Keep the shared directional representation.

## Experiment 43 — cyclic annual seasonality

- Classification: follow-up to successful cyclic time and geographic features.
- Hypothesis: sine/cosine of day-of-year pool seasonal neighborhoods across the year boundary, potentially simplifying region/season interactions beyond raw month and date inputs.
- Change: two row-local annual cycle features; retain existing calendar representations.
- Source: initial cyclic feature engineering research. The fixed 365-day period matches the documented 2005 dataset.

- Commit: 061c8ab. Result: **0.7653** AUC; decision: **discard**. Run time: 31.9s (training 13.0s, eval 19.0s, ok)
- Interpretation: Annual cyclic features score 0.7653, below 0.7658. Existing calendar features already represent the useful seasonal structure; revert the extra columns.

## Experiment 44 — tighter category partition limit

- Classification: follow-up to the earlier category-regularization gain, under the current model.
- Hypothesis: with full dates and shared geographic features, small category groups may identify specific disruptions without pooling many unrelated categories. Test a fourfold tighter partition limit.
- Change: max_cat_threshold=4 instead of 16; model and feature set otherwise fixed.
- Difference from earlier threshold tuning: much stronger L2, larger child support, loss-guided growth, and new continuous time/route features now supply alternative shared structure.

- Commit: e447284. Result: **0.7623** AUC; decision: **discard**. Run time: 32.0s (training 13.3s, eval 18.7s, ok)
- Interpretation: Restricting category groups to four loses substantial AUC despite the newer continuous features and stronger regularization; retain threshold 16.

## Experiment 45 — broader category partitions under strong regularization

- Classification: follow-up to the categorical threshold bracket.
- Hypothesis: the threshold-four failure suggests the model needs shared groups, and strong L2/child support may now protect broader partitions from the overfitting seen early in the run.
- Change: max_cat_threshold=64 instead of 16. This is a fourfold broadening under the current feature set and regularization, rather than repeating the original weakly regularized model.
- Source: [XGBoost categorical parameters](https://xgboost.readthedocs.io/en/stable/parameter.html); category thresholds limit partition search and can control overfitting.

- Commit: ed2890d. Result: **0.7572** AUC; decision: **discard**. Run time: 30.3s (training 12.0s, eval 18.3s, ok)
- Interpretation: Broader partitions score 0.7572, a clear regression. Both ends of the deliberate category-threshold bracket underperform sixteen; retain sixteen and move to a different architecture.

## Experiment 46 — bounded tree dropout

- Classification: exploration of a different boosting architecture.
- Hypothesis: dropout can reduce dependence on early trees and overspecialization by later trees; ordinary longer boosting and row sampling have not helped here.
- Change: DART dropout rate 0.02 with skip probability 0.7 and forest normalization. Use 300 rounds at fixed rate 0.1 (total nominal strength 30 versus approximately 31 for the best schedule) and 64 leaves to bound dropout's prediction-cache overhead within 60 seconds. Keep all features and regularization.
- Sources: [DART original paper](https://proceedings.mlr.press/v38/korlakaivinayak15.html) and [XGBoost DART documentation](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html). Forest normalization scales a newly added tree by 1/(1+eta); skip_drop supplies occasional ordinary boosting steps. This trial compares a time-bounded architecture rather than isolating a single hyperparameter.

- Commit: d33dacb. Result: **0.0000** AUC; decision: **crash**. Run time: 60.0s (training 60.0s, eval 0.0s, timeout-training)
- Interpretation: DART exceeded the 60-second training limit even with 300 rounds and 64 leaves; no evaluation was produced. Prediction-cache overhead makes this architecture unattractive within the budget. Revert.

## Experiment 47 — departure relative to route schedule

- Classification: exploration of unsupervised group-relative schedule features.
- Hypothesis: the same departure time may represent an early or late service on different routes. A train-fitted route median exposes this relationship as one continuous feature, sharing evidence without adding route identity categories.
- Change: fit median scheduled departure minutes for each training origin/destination pair; prepare subtracts that lookup from each row's departure minutes. Unknown routes become NaN. No labels or frequency/count statistics enter the lookup.
- Source: program.md's explicit train-fitted route-median example and previously researched [airline-delay time features](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf). Whether relative timing adds value here is an experimental hypothesis.

- Commit: 2d88eec. Result: **0.7651** AUC; decision: **discard**. Run time: 33.7s (training 13.0s, eval 20.6s, ok)
- Interpretation: Route-relative scheduled departure scores 0.7651, below 0.7658, and adds lookup overhead. The proposed shared schedule context does not justify the extra feature here; revert.

## Experiment 48 — diagonal airport geography

- Classification: follow-up to geographic coordinate and route-direction gains.
- Hypothesis: axis-aligned trees may need many splits for diagonal regional boundaries in the arbitrary MDS coordinate frame. Add two diagonal projections for each endpoint while preserving the original coordinates.
- Change: Geo1+Geo2 and Geo1-Geo2 for Origin and Dest, computed row by row inside prepare. This is a fixed sparse linear feature expansion, not a new embedding or full Rotation Forest implementation.
- Source: [Kuncheva and Rodriguez, study of Rotation Forest](https://lucykuncheva.co.uk/papers/lkjrmcs07.pdf), especially the discussion of tree sensitivity to coordinate rotations and sparse transformations. Adapting this observation to a single boosted model is our hypothesis.

- Commit: da43460. Result: **0.7652** AUC; decision: **discard**. Run time: 32.8s (training 13.7s, eval 19.1s, ok)
- Interpretation: Diagonal coordinate features score 0.7652, below 0.7658. Retain the original MDS axes and route differences; extra orientations are unnecessary here.

## Experiment 49 — average complementary tree-growth models

- Classification: exploration of a small XGBoost ensemble.
- Hypothesis: loss-guided and depth-wise trees may make different ranking errors; averaging their probabilities can reduce variance while retaining the useful feature structure.
- Change: a standard soft VotingClassifier with two equal-weight XGBoost estimators. One is the current loss-guided 128-leaf model; the other uses depth-wise growth capped at depth eight. All other parameters/features remain identical. Both fit the full training data once, sequentially; no extra evaluation or data split is added.
- Source: [scikit-learn VotingClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html). The composition adds only standard estimator code and should cost about twice normal training time, still below 60 seconds.

- Commit: 4b00eff. Result: **0.7661** AUC; decision: **keep**. Run time: 35.3s (training 16.3s, eval 19.0s, ok)
- Interpretation: The two-model average improves AUC by 0.0003 to 0.7661. Training is only 15.3 seconds, and the composition is seven lines of standard scikit-learn code; keep provisionally, then ablate the faster depth-wise member alone to assess whether the ensemble is necessary.

## Synthesis after 50 runs (experiments 0–49)

- Current best is **0.7661** at **4b00eff**, versus 0.7203 baseline. The last block improved 0.7651 to 0.7661 through route coordinate differences, a mild learning-rate schedule, and a two-model average.
- Explicit shared numeric structure remains useful. Annual cycles, route-relative departure, and diagonal coordinate expansion failed to add value. Both much tighter and much broader native category partitions hurt, supporting the selected threshold of sixteen. DART exceeded the training budget even with reduced rounds/leaves; gradient-based row sampling also hurt.
- Working theory: date shocks and regularized geographic/time interactions dominate. Small differences in tree growth can complement each other, but the newly kept ensemble needs an ablation before accepting extra complexity permanently.
- Fresh research at this pause: [VotingClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html) supports direct probability averaging; [pandas holiday calendars](https://pandas.pydata.org/docs/user_guide/timeseries.html) provide deterministic calendar rules without external data files. Holiday proximity is a remaining domain feature suggested by the earlier airline-delay paper. Explore it only after checking whether the depth-wise ensemble member suffices alone.

## Experiment 50 — depth-wise model alone

- Classification: ablation/simplification of the promising two-model average.
- Hypothesis: the depth-wise member might itself account for the ensemble improvement, allowing removal of the voting wrapper and the expensive loss-guided member.
- Change: keep the depth-wise model's exact settings (depth eight, max_leaves=0, all other best parameters/features unchanged), remove cloning/VotingClassifier imports and wrapper. No features change.
- Source: the directly preceding ensemble result and XGBoost's previously researched growth-policy documentation.

- Commit: 5cdae40. Result: **0.7607** AUC; decision: **discard**. Run time: 22.7s (training 4.6s, eval 18.1s, ok)
- Interpretation: The depth-wise member alone scores 0.7607, well below both the loss-guided model and their average. Its contribution appears complementary; restore the ensemble.

## Experiment 51 — holiday proximity

- Classification: exploration of a pooled calendar signal.
- Hypothesis: dates near holidays share travel patterns that individual categorical dates do not directly pool. One numeric distance to the nearest observed US federal holiday may expose this common behavior.
- Change: generate holiday rules for the documented 2005 year, including neighboring year boundaries; add minimum absolute day distance in prepare. No external files, target aggregates, or row counts are used.
- Sources: [pandas holiday calendars](https://pandas.pydata.org/docs/user_guide/timeseries.html) and [Naul's airline-delay feature discussion](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf). Federal observed holidays are an approximate travel-calendar signal, not an assertion of actual airport congestion.

- Commit: dd1544c. Result: **0.7660** AUC; decision: **discard**. Run time: 35.6s (training 16.3s, eval 19.3s, ok)
- Interpretation: Holiday proximity gives 0.7660 versus 0.7661 and adds calendar-specific machinery. Apply the simplicity criterion and remove the feature.

## Experiment 52 — one intermediate-complexity model

- Classification: ablation/simplification of the promising ensemble.
- Hypothesis: averaging a strong loss-guided model with a much weaker depth-wise model may work primarily by reducing complexity. A single loss-guided model capped at 64 leaves could achieve this more simply.
- Change: remove the voting wrapper and its imports; use the current 500-round schedule and features with max_leaves=64. Keep all other regularization.
- Difference from the earlier 64-leaf test: child support increased from 20 to 100, the time/route features and learning-rate schedule are new, and the reference is now a two-model ensemble. This directly tests whether that ensemble's extra complexity is necessary.

- Commit: af68f30. Result: **0.7651** AUC; decision: **discard**. Run time: 26.7s (training 8.0s, eval 18.8s, ok)
- Interpretation: The single 64-leaf model scores 0.7651. Its faster fit does not justify losing 0.0010 AUC; restore the two-model average.

## Experiment 53 — weight the stronger ensemble member

- Classification: follow-up to the successful ensemble and its ablations.
- Hypothesis: the loss-guided model alone scores 0.7658 versus 0.7607 for the depth-wise member, yet equal averaging reaches 0.7661. A modest contribution from the weaker but complementary model may preserve diversity with less bias.
- Change: fixed soft-voting weights [3, 1], favoring the loss-guided member. This is one broad comparison, not a fine weight search or an evaluation-fitted meta-model.
- Source: [VotingClassifier weights](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html) and directly measured member/ensemble results.

- Commit: c439789. Result: **0.7666** AUC; decision: **keep**. Run time: 35.7s (training 16.5s, eval 19.1s, ok)
- Interpretation: Favoring the stronger loss-guided member improves AUC from 0.7661 to 0.7666 with one parameter and no runtime change. Keep the 3:1 weighting; no fine weight sweep is planned.

## Experiment 54 — date by half-day categories

- Classification: follow-up to the strongest calendar representation and successful time features.
- Hypothesis: delays can vary within a date, so grouping dates only by their whole-day effects may obscure morning-versus-afternoon disruptions. A date/half-day category exposes these shifts directly.
- Change: add a native category with 730 fixed levels, combining day-of-year and departure before/after noon. Retain whole-date and continuous/cyclic time features for shared structure. Unlike the failed 43,026-level airport/date cross, this is a small two-way split of 365 dates with substantial training support per category.
- Source: previously researched [feature crosses](https://developers.google.com/machine-learning/crash-course/categorical-data/feature-crosses), applied using native categories and fixed training-independent integer levels. This is a temporal interaction hypothesis, not a claim about observed weather.

- Commit: 781cd9f. Result: **0.7655** AUC; decision: **discard**. Run time: 41.0s (training 20.6s, eval 20.3s, ok)
- Interpretation: The date/half-day cross scores 0.7655 and increases training/evaluation time. Even this moderate cardinality expansion loses to shared whole-date effects with separate time features; revert.

## Experiment 55 — cap long loss-guided paths

- Classification: follow-up to the complementary deep/shallow ensemble.
- Diagnostic: inspected only our own saved c439789 training artifact, without scoring any data. Loss-guided trees have median 128 leaves, median maximum depth 30, and maximum depth 39; the depth-wise member has median 36 leaves and depth eight.
- Hypothesis: limiting the strongest model to depth sixteen may regularize long, specialized paths while retaining its 128-leaf budget and gain-prioritized growth. Native category partition chains can also legitimately be deep, so the outcome is uncertain.
- Change: loss-guided max_depth=16; the cloned depth-wise model still explicitly uses depth eight. Features, weights, and all other parameters stay fixed.
- Source: [XGBoost depth and growth-policy parameters](https://xgboost.readthedocs.io/en/stable/parameter.html), interpreted using the model structure diagnostic.

- Commit: cf9be5d. Result: **0.7657** AUC; decision: **discard**. Run time: 32.5s (training 13.8s, eval 18.7s, ok)
- Interpretation: The depth-sixteen cap scores 0.7657. Long loss-guided paths remain useful with small native category partitions; the modest runtime saving does not offset the AUC loss.

## Experiment 56 — remove numeric day-of-year

- Classification: ablation/simplification of the successful calendar representation.
- Hypothesis: categorical dates capture individual day effects, while month/day-of-month already offer seasonal structure. The additional numeric day-of-year column may now be redundant or encourage unnecessary temporal thresholds.
- Change: remove only the DayOfYear feature, retaining its intermediate calculation for FlightDate. This is the complementary ablation to experiment nine, which removed categorical dates and clearly lost AUC.
- Source/motivation: earlier calendar feature research and the prior asymmetric ablation; no new representation or data is introduced.

- Commit: 8d56c2d. Result: **0.7659** AUC; decision: **discard**. Run time: 35.9s (training 17.1s, eval 18.8s, ok)
- Interpretation: Removing numeric DayOfYear lowers AUC to 0.7659. Both numeric calendar ordering and categorical date effects remain useful, so restore the feature.

## Experiment 57 — remove the learning-rate schedule

- Classification: ablation/simplification of the small schedule improvement.
- Hypothesis: the schedule previously added only 0.0001 AUC before route features and model averaging. The ensemble may now provide enough stabilization that a simpler fixed-rate configuration matches or improves it.
- Change: remove the callback and use 300 rounds at rate 0.1, approximately matching the schedule's total nominal boosting strength (30 versus about 31). Both ensemble members receive this simpler configuration.
- Difference from experiment 40: new route differences plus the 3:1 deep/shallow ensemble materially change the reference; this directly tests whether a previously marginal addition remains necessary.

- Commit: fef6ca5. Result: **0.7662** AUC; decision: **discard**. Run time: 28.7s (training 10.0s, eval 18.7s, ok)
- Interpretation: The fixed-rate 300-round ensemble scores 0.7662, below 0.7666. Although training is faster, the existing one-line standard callback is simple and comfortably within budget, so retain it. Three consecutive small-loss discards trigger fresh research before the next change.

## Experiment 58 — hybrid categorical splitting

- Classification: exploration of mixed categorical handling after plateau research.
- Hypothesis: individual-category splits may represent low-cardinality calendar features cleanly, while dates and airports still need grouped partitions. The earlier all-one-hot failures need not imply that one-hot is bad for every feature.
- Change: max_cat_to_onehot=16, changing Month (12 levels) and DayOfWeek (7) only; carrier, day-of-month, airports, and FlightDate retain native partitions. Keep max_cat_threshold=16.
- Source: fresh [XGBoost categorical parameter research](https://xgboost.readthedocs.io/en/release_3.3.0/parameter.html). Checked the actual saved 3.4.1 model: current max_cat_to_onehot is 4. Latest development docs describe a future 3.5 default change, which is not assumed here.
- Other research considered max_delta_step, but its documented motivation is extreme class imbalance; that does not match this balanced training set, so it is lower priority.
- Additional training-only diagnostic: the best model's gain shares assign about 44% to FlightDate and about 16–17% each to Origin/Dest; destination coordinates have low gain. These are split diagnostics, not an independent evaluation or proof of feature irrelevance.

- Commit: 1eb67d2. Result: **0.7659** AUC; decision: **discard**. Run time: 35.9s (training 17.1s, eval 18.9s, ok)
- Interpretation: Using individual-category splits for month and weekday gives 0.7659. Grouped partitions remain preferable for both small and large categorical features here; revert.

## Experiment 59 — rebalance L2 against stronger structural regularization

- Classification: follow-up to the strong regularization and ensemble gains.
- Hypothesis: lambda=500 was selected before min_child_weight rose to 100 and before model averaging. Those later safeguards may make that much leaf-weight shrinkage unnecessary; weaker L2 could recover useful interaction strength.
- Change: reg_lambda=100 for both ensemble members, keeping child support, feature set, schedule, tree growth, and weights fixed.
- Difference from early lambda=100 experiments: loss-guided growth, larger child support, the new shared time/route features, and complementary model averaging all changed the bias/variance tradeoff. This is a broad fivefold comparison rather than a local parameter sweep.
- Source: [XGBoost regularization parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) and the run's sequence of regularization gains.

- Commit: b601683. Result: **0.7631** AUC; decision: **discard**. Run time: 35.5s (training 16.4s, eval 19.0s, ok)
- Interpretation: Reducing L2 to 100 drops AUC to 0.7631. Strong leaf-weight shrinkage is still needed despite larger child support and averaging; restore lambda 500.

## Synthesis after 60 runs (experiments 0–59)

- Best remains **0.7666 at c439789**, up from 0.7661 at the previous pause and 0.7203 baseline. A 3:1 weighted average of loss-guided and depth-wise models is better than either the equal average or the tested single-model simplifications.
- Ablations support keeping numeric calendar order, the learning-rate schedule, strong L2, and unrestricted loss-guided paths. The complementary shallow member is weak alone but useful in the average. Holiday proximity, date/half-day categories, and hybrid one-hot treatment of small calendar categories did not help.
- Working theory: a heavily regularized model captures date-specific and airport-specific effects, while the smaller ensemble member smooths some specialized decisions. Limiting individual tree paths or reducing L2 sacrifices useful structure.
- Fresh research: [correlated-feature importance example](https://scikit-learn.org/stable/auto_examples/inspection/plot_permutation_importance_multicollinear.html) motivates cautious feature ablation instead of equating low gain with irrelevance; [XGBoost feature weights](https://xgboost.readthedocs.io/en/stable/python/python_api.html) suggest biased column sampling that protects dominant calendar/airport features while varying secondary ones. No permutation scoring or extra predictive evaluation will be performed.
- Next: remove redundant destination coordinate columns, then consider weighted column sampling as a distinct follow-up to previously unsuccessful uniform sampling.

## Experiment 60 — remove destination coordinates as model inputs

- Classification: ablation/simplification of geographic features.
- Hypothesis: destination coordinates are exactly recoverable from origin coordinates plus route differences, and have very low training gain. Removing the duplicate view may simplify splitting without losing useful information.
- Change: prepare still looks up destination coordinates to compute route differences but exposes only origin coordinates and route differences, removing two model columns. Unknown-airport handling and row-local behavior are preserved.
- Source: the training-only gain diagnostic and the correlated-feature research above. Exact numerical redundancy does not guarantee redundancy for axis-aligned trees, so the harness result decides.

- Commit: 7df720f. Result: **0.7661** AUC; decision: **discard**. Run time: 36.0s (training 16.9s, eval 19.2s, ok)
- Interpretation: Removing destination coordinate inputs gives 0.7661. Numerical redundancy does not imply redundancy for axis-aligned trees; retain both endpoint coordinates and route differences.

## Experiment 61 — weighted column sampling

- Classification: exploration of selective feature randomization.
- Hypothesis: previous uniform row/column sampling could omit crucial calendar or airport predictors. Biased column sampling may preserve those signals while reducing dependence on the many correlated secondary features.
- Change: colsample_bytree=0.8 and sampling weights four for FlightDate/Origin/Dest, one for other features, in both ensemble members. No rows are subsampled. These three were the dominant training-gain predictors, not selected by an additional validation metric.
- Difference from experiments 14/20: retain every training row, prioritize essential predictors, use the stronger current regularization and the complementary ensemble.
- Source: [XGBoost feature_weights API](https://xgboost.readthedocs.io/en/stable/python/python_api.html) and [column-sampling parameters](https://xgboost.readthedocs.io/en/release_3.3.0/parameter.html). Confirmed feature_weights is present in the installed estimator's parameters.

- Commit: e84a01a. Result: **0.7661** AUC; decision: **discard**. Run time: 35.8s (training 17.0s, eval 18.9s, ok)
- Interpretation: Weighted column sampling scores 0.7661. Even when dominant categorical predictors are favored, feature randomization does not beat full-column training; revert the sampling configuration.

## Experiment 62 — preserve overnight travel-adjusted time

- Classification: ablation/simplification of the successful time-distance interaction.
- Hypothesis: wrapping the rough travel-adjusted time at midnight removes whether a long late flight extends into the next day and creates a discontinuity. An unwrapped value may preserve this useful distinction more simply.
- Change: remove only the modulo-1440 operation from TravelAdjustedTime, keeping the same design scale of eight miles per minute. The feature remains a rough interaction, not a true arrival-time estimate.
- Source/motivation: the prior gain from the row-local time-distance feature and the previously researched distinction between ordered and cyclic time representations.

- Commit: a66ced5. Result: **0.7662** AUC; decision: **discard**. Run time: 34.8s (training 16.0s, eval 18.8s, ok)
- Interpretation: Removing midnight wrapping scores 0.7662, below 0.7666. Restore the cyclic travel-adjusted clock. Fresh domain research was performed after the three small-loss discards.

## Experiment 63 — airport-relative route length

- Classification: exploration of unsupervised airport context.
- Hypothesis: an absolute flight distance can be unusually short or long for a given airport's network. Relative distance may share this operational distinction across airport identities, beyond geography alone.
- Change: fit median Distance by Origin and by Dest on training data; prepare exposes each row's distance divided by the corresponding median. No target, row-count, or frequency feature is used; unknown airport keys map to NaN.
- Sources: program.md explicitly permits train-fitted group medians; fresh [Sun airline-delay study](https://cs229.stanford.edu/proj2012/Sun-LearningToPredictFlightDelay.pdf) discusses airport effects and weak marginal distance patterns in its own data. The relative-distance feature is our experimental inference, not a method claimed by that paper. Weather and other unavailable fields are not imported.

- Commit: 35b2aef. Result: **0.7661** AUC; decision: **discard**. Run time: 37.7s (training 16.8s, eval 20.9s, ok)
- Interpretation: Airport-relative route lengths score 0.7661 and add lookup overhead. Retain the simpler raw distance plus learned geography and time-distance interaction.

## Experiment 64 — stronger L2 bracket

- Classification: follow-up to the clear failure of weaker leaf shrinkage.
- Hypothesis: the rich feature set and 500-round schedule may still benefit from stronger leaf-weight shrinkage. The fivefold weakening in experiment 59 hurt by 0.0035, so test the opposite side of the range.
- Change: reg_lambda=2000 instead of 500 in both ensemble members, with structure, child support, schedule, and weights unchanged. This completes a broad bracket rather than a fine local search.
- Source: previously researched XGBoost regularization guidance and the recent controlled lambda comparison.

- Commit: f69c18b. Result: **0.7632** AUC; decision: **discard**. Run time: 35.1s (training 16.1s, eval 19.0s, ok)
- Interpretation: Lambda 2000 scores 0.7632, essentially as poor as lambda 100 in the opposite direction. The broad bracket supports retaining 500.

## Experiment 65 — ordered day-of-month

- Classification: follow-up to calendar representation gains and the failed day-of-month removal.
- Hypothesis: keeping day-of-month information as an ordered number may pool neighboring days more usefully than arbitrary native categorical groups, while categorical FlightDate still handles specific day shocks.
- Change: remove DayofMonth from categorical columns and expose its parsed integer value; reuse that value for DayOfYear. All other features and model parameters stay unchanged.
- Difference from the earlier ablation: that trial removed day-of-month entirely; this retains the information while imposing an ordinal representation.
- Source: earlier calendar feature research supporting multiple temporal granularities, plus this run's numeric/categorical date ablations.

- Commit: 16bbebe. Result: **0.7666** AUC; decision: **keep**. Run time: 35.2s (training 17.1s, eval 18.0s, ok)
- Interpretation: Numeric day-of-month ties the best printed AUC at 0.7666 while removing one categorical encoder and reusing the parsed calendar value. Keep as a simpler representation; evaluation measured 17.6 seconds versus the prior best run's 18.7 seconds, without claiming the timing difference is statistically established.

## Experiment 66 — larger leaf budget under the final regularization

- Classification: follow-up to the earlier 64-to-128 leaf gain.
- Hypothesis: the richer time/route feature set and complementary model average may benefit from a larger loss-guided leaf budget, while min_child_weight=100 and lambda=500 control leaf reliability.
- Change: max_leaves=256 for the loss-guided member, leaving the depth-wise member at its explicit max_leaves=0/depth-eight configuration. All other parameters and the newly simplified day-of-month representation remain fixed.
- Difference from earlier leaf-budget tuning: stronger child support, the learning-rate schedule, added shared features, and model averaging now change the capacity tradeoff. This doubles capacity in one broad test, rather than repeating a previous configuration.
- Source: previously researched XGBoost loss-guided growth and max_leaves documentation.

- Commit: bdfa919. Result: **0.7667** AUC; decision: **keep**. Run time: 35.4s (training 17.3s, eval 18.1s, ok)
- Interpretation: The 256-leaf budget improves the printed AUC from 0.7666 to 0.7667 without adding code complexity or materially changing runtime. Keep this final configuration. The clock now reports TIME IS UP; no further experiment will be started.

## Final summary — two-hour experiment complete

- **Best Eval AUC: 0.7667**, commit **bdfa919** (`bdfa919c5fa2d904a5d433e15167d7db024ac0cc`), branch **oct2**. Baseline was **0.7203**, an absolute improvement of **0.0464**.
- Completed **67 harness runs**, including the baseline: **23 keep**, **42 discard**, and **2 training timeouts**. Both timeouts were logged and reverted. All **65 successful runs** have saved artifacts. The final run took **35.4 seconds** overall: **17.3 seconds** in the harness training phase and **18.1 seconds** in evaluation; model.fit itself took 16.3 seconds.
- Final model: a **3:1 probability average** of two 500-round XGBoost classifiers. The main member uses loss-guided growth with 256 leaves; the second uses depth-wise growth capped at eight. Both use min_child_weight=100, reg_lambda=500, max_cat_threshold=16, and the selected decreasing learning-rate schedule.
- Final features retain numeric and categorical calendar views, native carrier/airport categories, cyclic departure time, a simple time-distance interaction, and airport/route coordinates inferred only from training distances. Day-of-month is numeric, tying the best score with one fewer categorical encoder. Faster cached categorical types and lookups reduced per-row preparation overhead.
- What worked: full-date representation, strong L2 and child support, restrained categorical partition size, shared geographic/time features, loss-guided growth, and a small complementary ensemble. The final larger leaf budget added only 0.0001 AUC without additional code complexity.
- What did not work: high-cardinality categorical crosses, all-one-hot or mixed small-calendar one-hot handling, substantially different category thresholds, uniform or gradient-based row sampling, weighted column sampling, ranking objective, the tested train-split early stopping and honest target encoding, extra coordinate/holiday/group-median features, and most simplifications that removed useful calendar/geographic views. DART and the later airport/date cross exceeded the training limit.
- Interpretation: the large baseline improvement is supported by multiple substantial steps; the last few fourth-decimal changes are small and were selected on the same harness evaluation set. No independent generalization claim is made from those tiny differences.
- If another run is authorized, first test the final 256-leaf member alone, then compare alternate feature representations for the smaller ensemble member with fixed weights. These would directly test remaining ensemble complexity before adding more features.
- Final checks: branch points to the best kept commit; train.py has no uncommitted changes and is the only tracked file changed from the baseline; its last line remains save_and_evaluate(model, prepare). Feature changes passed batch-versus-single-row and cloudpickle checks, and the harness successfully evaluated saved artifacts. No held-out/source data, archived results, or human-only evaluation tools were used. Results and this research log remain uncommitted; timing and artifacts are left in place.
- Best artifact: `artifacts/bdfa919c5fa2d904a5d433e15167d7db024ac0cc.pkl`.
- The harness reported **TIME IS UP** after experiment 66. No new experiments were started. The final action is to stop the experiment clock.
