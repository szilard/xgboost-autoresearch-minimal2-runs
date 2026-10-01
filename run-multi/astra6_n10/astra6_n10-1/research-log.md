# XGBoost experiment research log

## Setup — 2026-10-01 UTC

- Run tag and branch: `oct1`, created directly from the current HEAD.
- Starting commit: `92e43e6`.
- Read `program.md`, `README-autoresearch.md`, `train.py`, and `harness.py`.
- Verified that `data/train.csv` and `data/eval.csv` exist and are nonempty, using file metadata only.
- Verified imports: Python 3.14.4, NumPy 2.5.3, pandas 3.0.6, XGBoost 3.4.1, scikit-learn 1.9.1, and cloudpickle 3.1.2. No packages installed.
- Initialized `results.tsv` with its header only. Keep both logs uncommitted.
- Baseline `train.py` and `harness.py` are unchanged.
- Experiment clock has not started; setup only was requested.

## Baseline — pending

After the user confirms the start, the first action is `python3 harness.py start`, followed by the unchanged baseline through `python3 harness.py run > run.log 2>&1`.

Record baseline AUC after that run. Research external sources before the first non-baseline experiment and throughout the two-hour session as specified in `program.md`.

## Experiment 0 — baseline (`92e43e6`)

- AUC: **0.7203**, kept. Harness runtime 31.8s (training phase 1.0s; evaluation phase 30.7s).
- The starter uses 30 trees, depth 6, learning rate 0.1 and native categorical features.
- The two-hour clock was started before any experiment work.

## Initial research

Read the [official tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html), [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html), and [categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html). These motivate testing boosting capacity first, then controlled regularization and categorical representations. Candidate ranges are experimental choices: 150–1200 trees, depths 3–10, learning rates 0.03–0.15, child weights 1–100, and categorical thresholds 8–64.

Also found [scikit-learn's temporal feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) and [Berkeley's airline feature engineering project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches). These suggest calendar, schedule and route representations as later explorations using only the permitted training data.

## Experiment 1 — more boosting capacity

- Parent: `92e43e6`. Class: **exploration**.
- Hypothesis: the baseline's 30 trees underfit; increasing to 300 at unchanged depth and step size should learn more useful interactions.
- Source: official XGBoost tuning guide above. One model change; schema logging is diagnostic only.

- Result: **0.7342 AUC**, **keep**, commit `8498a51`. Run time: 33.6s (training 2.5s, eval 31.1s, ok)
- Interpretation: A substantial gain of 0.0139 supports initial underfitting. Training remains far below the limit.

## Experiment 2 — extend the boosting horizon

- Parent: `8498a51`. Class: **follow-up**.
- Hypothesis: the 0.0139 gain from 30 to 300 trees suggests remaining bias. Test 900 trees, holding all other settings fixed, to locate the useful boosting horizon before feature engineering.
- Source: initial XGBoost tuning research; this specifically tests saturation versus continued benefit.

- Result: **0.7264 AUC**, **discard**, commit `7819b07`. Run time: 36.7s (training 5.8s, eval 30.8s, ok)
- Interpretation: AUC fell by 0.0078 from 300 trees; extra rounds overfit with these settings. Revert to 300 before changing representation.

## Experiment 3 — simplify categorical preparation

- Parent: `8498a51`. Class: **ablation/simplification**.
- Hypothesis: explicit `isin`/`where` is redundant when supplying fixed categories to pandas; remove it to preserve the model and reduce row-by-row evaluation cost.
- Source: [pandas.Categorical API](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.Categorical.html) documents unknown values becoming NaN.
- This is useful because evaluation takes about 31 seconds versus less than 3 seconds for training at 300 trees.

- Result: **0.7342 AUC**, **keep**, commit `92dde03`. Run time: 23.4s (training 2.5s, eval 20.9s, ok)
- Interpretation: Identical AUC with three fewer lines and evaluation reduced from 30.8s to 20.7s. Keep the simplification. pandas emits a future-version warning for unseen categories; current missing-value behavior is correct.

## Experiment 4 — ordinal day of year

- Parent: `92dde03`. Class: **exploration** (calendar feature engineering).
- Hypothesis: separate month/day categories make consecutive-date patterns expensive to express. Add a deterministic day-of-year feature for this non-leap-year dataset, preserving the existing categorical columns.
- Source: [scikit-learn temporal feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html). The application to airline day-specific effects is my hypothesis.
- Feature uses only each row and fixed calendar offsets. Check batched versus single-row output on training examples before fitting.

- Result: **0.7378 AUC**, **keep**, commit `b2a9a7e`. Run time: 25.2s (training 2.5s, eval 22.7s, ok)
- Interpretation: AUC improved by 0.0036. A direct calendar coordinate helps; all three batch-versus-row consistency checks passed.

## Experiment 5 — categorical flight date

- Parent: `b2a9a7e`. Class: **follow-up**.
- Hypothesis: the ordinal calendar gain indicates missing date structure. A native categorical flight date can express non-contiguous high-risk days and airport/date interactions, alongside the smoother ordinal coordinate.
- Source: [XGBoost categorical partitioning](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html). No labels or evaluation rows are used to construct the feature.

- Result: **0.7500 AUC**, **keep**, commit `a0babd2`. Run time: 28.2s (training 2.7s, eval 25.5s, ok)
- Interpretation: AUC increased by 0.0122 to 0.7500; irregular date effects are substantially useful. Retain both calendar representations.

## Experiment 6 — reuse category indexes

- Parent: `a0babd2`. Class: **ablation/simplification** of preprocessing.
- Hypothesis: fixed pandas Index objects and direct codes eliminate repeated category-index construction and handle unknowns explicitly without the pandas future warning, with identical feature values and AUC.
- Sources: [Index.get_indexer](https://pandas.pydata.org/docs/reference/api/pandas.Index.get_indexer.html) returns -1 for unseen values; [Categorical.from_codes](https://pandas.pydata.org/docs/reference/api/pandas.Categorical.from_codes.html) uses -1 for missing values.
- Keep only if predictions are unchanged and the implementation improves runtime/unknown handling.

- Result: **0.7500 AUC**, **keep**, commit `6dc3119`. Run time: 18.3s (training 2.7s, eval 15.6s, ok)
- Interpretation: AUC remains 0.7500, warnings are gone, and evaluation fell from 25.2s to 15.4s. Keep the simpler runtime path and explicit unknown handling.

## Experiment 7 — scheduled hour and minute

- Parent: `6dc3119`. Class: **exploration**.
- Hypothesis: hour and minute-of-hour expose coarse departure windows and timetable patterns that are awkward to express with the raw HHMM number. Add both numeric components, keeping the original time.
- Source: the scikit-learn temporal feature engineering example in initial research; adaptation to HHMM scheduling is my hypothesis.

- Result: **0.7501 AUC**, **keep**, commit `b4324a4`. Run time: 20.5s (training 2.7s, eval 17.7s, ok)
- Interpretation: AUC increased only 0.0001. Keep provisionally because the change is two simple lines; later ablation should test whether either component is redundant.

## Experiment 8 — categorical origin/destination route

- Parent: `b4324a4`. Class: **exploration**.
- Hypothesis: a route category directly exposes airport-pair effects and pools routes with similar residuals in one split, instead of requiring repeated nested origin/destination splits.
- Source: [AutoCross paper](https://arxiv.org/abs/1904.12857) motivates categorical interactions generally; use a single domain-informed cross here, not its automated search algorithm.
- Fit route vocabulary on training only and map unseen routes to missing. No frequency/count features.

- Result: **0.7301 AUC**, **discard**, commit `3c68ca1`. Run time: 26.9s (training 3.9s, eval 22.9s, ok)
- Interpretation: AUC dropped by 0.0200 and the artifact grew from about 12 MB to 54 MB. High-cardinality route partitioning overfits strongly with current regularization; discard.

## Experiment 9 — restrict categorical split search

- Parent: `b4324a4`. Class: **follow-up** to useful categorical dates and the failed sparse route cross.
- Hypothesis: limiting categorical partitions to `max_cat_threshold=16` will reduce noisy category grouping while retaining date/airport structure. Route remains removed.
- Source: [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-categorical-feature) describes this as categorical regularization.

- Result: **0.7492 AUC**, **discard**, commit `2256c88`. Run time: 20.1s (training 2.4s, eval 17.7s, ok)
- Interpretation: AUC fell by 0.0009; this categorical restriction removes useful flexibility. Restore the default threshold.

## Experiment 10 — minimum child weight

- Parent: `b4324a4`. Class: **follow-up** to date-feature gains.
- Hypothesis: `min_child_weight=20` discourages leaves supported by very few observations, reducing variance without globally restricting categorical groups as experiment 9 did.
- Source: initial official XGBoost parameter/tuning documentation. Only this regularization parameter changes.

- Result: **0.7502 AUC**, **keep**, commit `9535d70`. Run time: 20.4s (training 2.7s, eval 17.7s, ok)
- Interpretation: AUC improved marginally to 0.7502. Keep this inexpensive regularization provisionally and next test tree depth, a different control on interaction complexity.

## Synthesis after experiments 1–10

Best: **0.7502**, versus 0.7203 baseline. Boosting from 30 to 300 trees and representing flight date as a category produced the meaningful gains. More boosting on the original features and a high-cardinality route category overfit. Restricting categorical partitions to 16 did not help. Hour/minute components and minimum child weight contributed only 0.0001 each and remain candidates for later ablation.

Precomputing category indexes reduced evaluation overhead materially without changing AUC. All engineered features pass training-batch versus individual-row checks. A training split-gain diagnostic from `b4324a4` is dominated by FlightDate (45.4%), Origin (21.2%), Dest (20.0%) and scheduled time (11.0%). These are model diagnostics, not independent evidence of predictive utility; high-cardinality features can receive optimistic importance.

Research refresh: searched and read the [CatBoost paper](https://arxiv.org/abs/1706.09516) on target-statistic leakage/prediction shift and [XGBoost ranking documentation](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html) on pairwise losses. Do not naively add full-training target means for sparse groups. Candidate new directions: shallower models, shrinkage with more rounds, a compact-feature ablation, lower-cardinality carrier/airport crosses, and eventually a pairwise objective. Continue selecting by the unchanged harness AUC only.

## Experiment 11 — shallower interactions

- Parent: `9535d70`. Class: **follow-up**.
- Hypothesis: depth 4 reduces memorization of airport/date combinations and should improve generalization even though depth 6 achieves greater training split gain. Keep 300 rounds and all features unchanged for a clean depth test.
- Source: initial XGBoost bias–variance guidance; route overfitting and the gain diagnostic motivate this direction.

- Result: **0.7522 AUC**, **keep**, commit `fb076c5`. Run time: 19.6s (training 2.0s, eval 17.7s, ok)
- Interpretation: AUC improved by 0.0020 and model size fell from 11.4 MB to 3.1 MB. Shallower interactions generalize better.

## Experiment 12 — smaller steps with a matched boosting horizon

- Parent: `fb076c5`. Class: **follow-up**.
- Hypothesis: At depth 4, use 600 trees with learning rate 0.05 instead of 300 at 0.1. The matched total step budget tests whether finer boosting updates improve the bias–variance balance.
- Source: [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html); unlike experiment 2, shrinkage and tree depth differ.

- Result: **0.7531 AUC**, **keep**, commit `e8189d9`. Run time: 20.8s (training 3.0s, eval 17.8s, ok)
- Interpretation: AUC increased by 0.0009 to 0.7531. Finer boosting updates improve the shallow model at essentially the same training cost.

## Experiment 13 — remove redundant calendar components

- Parent: `e8189d9`. Class: **ablation/simplification**.
- Hypothesis: Month, day of month and weekday are already represented jointly by FlightDate in this one-year dataset. Remove the three original calendar categories while retaining ordinal and categorical date; this may preserve accuracy with fewer columns and faster preparation.
- Source: Our experiment 4/5 gains and the training gain diagnostic; this is a direct ablation, not an assumed importance ranking.

- Result: **0.7533 AUC**, **keep**, commit `9b60da6`. Run time: 18.0s (training 2.8s, eval 15.2s, ok)
- Interpretation: AUC improved to 0.7533 while evaluation dropped from 17.5s to 15.0s. The date representations suffice for these calendar components.

## Experiment 14 — stochastic row sampling

- Parent: `9b60da6`. Class: **exploration**.
- Hypothesis: Use subsample=0.8 so each tree sees a different subset of training rows. This may reduce reliance on noisy airport/date residuals while retaining enough examples for stable categorical splits.
- Source: [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html), randomness as an overfitting control.

- Result: **0.7435 AUC**, **discard**, commit `23487a4`. Run time: 18.5s (training 3.1s, eval 15.4s, ok)
- Interpretation: AUC fell by 0.0098. Randomly withholding rows makes category statistics noisier here; restore full-row training.

## Experiment 15 — one-category-versus-rest splits

- Parent: `9b60da6`. Class: **exploration**.
- Hypothesis: Set max_cat_to_onehot=1024 so current categories use one-versus-rest splits. This limits arbitrary grouping of airports/dates and may reduce category-partition overfitting, at the cost of needing more trees.
- Source: [XGBoost categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html). This changes split representation rather than adding sparse crosses.

- Result: **0.7250 AUC**, **discard**, commit `9274568`. Run time: 17.6s (training 2.3s, eval 15.3s, ok)
- Interpretation: AUC dropped to 0.7250 and artifact size shrank to 1 MB, consistent with underfitting at this limited one-category split capacity. Discard this configuration, but test a deliberately larger one-hot model before rejecting the representation.

## Experiment 16 — give one-category splits sufficient capacity

- Parent: `9b60da6`. Class: **follow-up**.
- Hypothesis: Experiment 15 sharply reduced expressivity. Test 2400 depth-6 trees with one-versus-rest categorical splits and learning rate 0.05. This substantially expands the number of airport/date interactions the restricted split form can learn.
- Source: Categorical tutorial plus experiment 15; this is a capacity test specific to the changed representation, not another extension of the original partition model.

- Result: **0.7466 AUC**, **discard**, commit `8d139a9`. Run time: 24.3s (training 8.4s, eval 15.9s, ok)
- Interpretation: More capacity recovered much of the one-hot loss, but 0.7466 remains 0.0067 below the compact partition model. Reject the one-hot direction for now.

## Experiment 17 — carrier and month interaction

- Parent: `9b60da6`. Class: **exploration**.
- Hypothesis: A carrier/month category pools seasonal airline effects across dates. Unlike the discarded route feature, it has only a few hundred possible levels and substantially more observations per level.
- Source: [AutoCross](https://arxiv.org/abs/1904.12857) and categorical feature combinations in the [CatBoost paper](https://arxiv.org/abs/1706.09516); choose a small domain-informed interaction.

- Result: **0.7572 AUC**, **keep**, commit `5a96fa7`. Run time: 21.0s (training 2.9s, eval 18.0s, ok)
- Interpretation: AUC increased by 0.0039 to 0.7572. A compact interaction generalizes where the sparse route cross failed.

## Experiment 18 — carrier and weekday interaction

- Parent: `5a96fa7`. Class: **follow-up**.
- Hypothesis: Add carrier/weekday alongside carrier/month to capture airline-specific weekly schedules. It has fewer levels than the successful seasonal cross, with more support per combination.
- Source: AutoCross and CatBoost feature-combination research; experiment 17 supplies the direct empirical motivation.

- Result: **0.7560 AUC**, **discard**, commit `baa9226`. Run time: 23.8s (training 3.1s, eval 20.8s, ok)
- Interpretation: AUC fell by 0.0012; the weekly cross adds complexity without useful generalization. Retain the seasonal carrier interaction only.

## Experiment 19 — airport and season interactions

- Parent: `5a96fa7`. Class: **exploration**.
- Hypothesis: Origin/quarter and destination/quarter categories expose regional seasonal effects while keeping cardinality below airport/month or route crosses. Airport seasonal conditions may be missing from the shallow date model.
- Source: Domain temporal/geographic feature ideas from the Berkeley airline project and the successful carrier/month experiment; quarter coarsening is our hypothesis to avoid sparse interactions.

- Result: **0.7489 AUC**, **discard**, commit `01df91b`. Run time: 26.9s (training 3.8s, eval 23.1s, ok)
- Interpretation: AUC dropped by 0.0083. Even coarsened airport crosses overfit with this categorical representation; remove them.

## Experiment 20 — geographic coordinates inferred from training distances

- Parent: `5a96fa7`. Class: **exploration**.
- Hypothesis: Infer a three-dimensional airport embedding from observed route distances, then add endpoint coordinates. Continuous geography may share regional effects across nearby airports without sparse airport/season categories.
- Source: [Classical MDS and airport distances](https://pmc.ncbi.nlm.nih.gov/articles/PMC4675631/), [Isomap](https://scikit-learn.org/stable/modules/generated/sklearn.manifold.Isomap.html), and [SciPy shortest paths](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.shortest_path.html). Fit only on train route-distance medians; no external airport data, labels or count features.

- Result: **0.7563 AUC**, **discard**, commit `d612648`. Run time: 26.8s (training 3.4s, eval 23.4s, ok)
- Interpretation: AUC 0.7563 is lower by 0.0009; inferred geography adds 24 lines and preparation cost without an improvement. Discard.

## Synthesis after experiments 11–20

Best: **0.7572** at `5a96fa7`. Shallower trees, smaller learning-rate updates, removal of redundant calendar categories, and carrier/month interactions helped. Row subsampling and one-category splits failed; the latter remained worse after a substantial capacity increase. Airline/weekday, airport/quarter and inferred geographic coordinates did not improve generalization. Grouping choices matter: the compact seasonal airline cross helps, while sparse airport or route crosses overfit.

The best model still uses full training rows, native categorical partitions, 600 depth-4 trees, learning rate 0.05 and minimum child weight 20. All completed runs meet the limits and all row-consistency checks pass.

Research refresh: investigated [XGBoost random forests/parallel trees](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html), [early stopping](https://xgboost.readthedocs.io/en/release_3.3.0/python/sklearn_estimator.html), [target-encoding leakage](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html), and [interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html). Also researched distance-derived geographic embeddings; experiment 20 rejected that idea empirically. Next test structural regularization that excludes airport-pair interactions, followed by model growth policy, an internal training-only stopping split, and label-independent schedule lookups.

## Experiment 21 — exclude direct origin-destination interactions

- Parent: `5a96fa7`. Class: **exploration**.
- Hypothesis: Disallow Origin and Dest from sharing a decision path, while both may interact with time, date, carrier and other numeric features. The poor route-cross experiments suggest unconstrained route interactions may add noise.
- Source: [Official interaction-constraint tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html); this restriction is a hypothesis, not a causal claim.

- Result: **0.7564 AUC**, **discard**, commit `4110e4c`. Run time: 21.9s (training 3.8s, eval 18.1s, ok)
- Interpretation: AUC fell to 0.7564, so discard. The official tutorial warns that overlapping groups can re-admit features deeper in a path: this configuration is not proof that all origin/destination paths were excluded, and no stronger conclusion is drawn.

## Experiment 22 — pairwise ranking objective

- Parent: `5a96fa7`. Class: **exploration**.
- Hypothesis: Train XGBoost on sampled positive/negative ranking pairs instead of pointwise logistic loss. Random groups of 1000 training rows keep pair construction manageable; rank scores are monotonically mapped to probabilities for the unchanged harness interface.
- Source: [XGBoost learning-to-rank tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html) and its pair sampling/normalization parameters. AUC is a ranking metric, but improved harness AUC remains to be tested.

- Result: **0.7534 AUC**, **discard**, commit `63a0395`. Run time: 22.9s (training 5.0s, eval 17.9s, ok)
- Interpretation: AUC 0.7534 is lower by 0.0038. The direct ranking surrogate does not beat logistic boosting here; remove the wrapper and restore classification.

## Experiment 23 — training-only early stopping

- Parent: `5a96fa7`. Class: **exploration**.
- Hypothesis: Use a stratified 10 percent split of train.csv to stop a 3000-round depth-4 model at learning rate 0.03, with patience 100. This tests a data-selected boosting horizon while keeping the final harness as the only experiment score; do not retrain on the stopping subset afterward.
- Source: [XGBoost sklearn early-stopping documentation](https://xgboost.readthedocs.io/en/release_3.3.0/python/sklearn_estimator.html). All stopping data comes from train.csv.

- Result: **0.7539 AUC**, **discard**, commit `787334d`. Run time: 22.3s (training 4.2s, eval 18.1s, ok)
- Interpretation: Early stopping chose 775 rounds at learning rate 0.03. Harness AUC was 0.7539, below the full-training model by 0.0033; discard this split-based training procedure.

## Experiment 24 — departure time relative to route schedule

- Parent: `5a96fa7`. Class: **exploration**.
- Hypothesis: Fit median departure minutes for each route on training rows, then expose the median and each flight departure offset. A continuous schedule reference may generalize better than the discarded route category.
- Source: The train-fitted route-median example in program.md, plus the temporal feature engineering research. This uses schedule values only, not label means or row-count features.

- Result: **0.7542 AUC**, **discard**, commit `8641a38`. Run time: 23.8s (training 3.0s, eval 20.8s, ok)
- Interpretation: AUC fell by 0.0030. These unsupervised route schedule summaries do not help the current model; discard.

## Experiment 25 — loss-guided tree growth with a fixed leaf budget

- Parent: `5a96fa7`. Class: **exploration**.
- Hypothesis: Grow trees by best available loss reduction with at most 16 leaves instead of a uniform depth-4 limit. This keeps a similar leaf budget but permits asymmetric paths where a date/airport effect needs more conditions.
- Source: [XGBoost grow_policy and max_leaves parameters](https://xgboost.readthedocs.io/en/stable/parameter.html).

- Result: **0.7551 AUC**, **discard**, commit `533953e`. Run time: 21.2s (training 3.1s, eval 18.1s, ok)
- Interpretation: AUC fell to 0.7551. The asymmetrically deeper trees do not generalize as well as depth-4 trees.

## Experiment 26 — sample feature columns while retaining all rows

- Parent: `5a96fa7`. Class: **exploration**.
- Hypothesis: Use colsample_bytree=0.8 to diversify trees and occasionally learn without the dominant categorical date. Unlike failed row subsampling, each available categorical feature retains all of its training observations.
- Source: XGBoost parameter/tuning documentation and the contrast with experiment 14.

- Result: **0.7565 AUC**, **discard**, commit `ff52642`. Run time: 20.9s (training 2.9s, eval 18.0s, ok)
- Interpretation: AUC 0.7565 is lower by 0.0007. Feature sampling alone does not improve the full-row model.

## Experiment 27 — independently fitted airport-date target statistics

- Parent: `5a96fa7`. Class: **exploration**.
- Hypothesis: Reserve half of train.csv to estimate smoothed origin/date and destination/date delay rates, and fit the classifier on the other half. The lookup labels are independent of each model-fitting row; these features may express local daily disruptions that shallow trees miss.
- Source: The independent-split target-statistic method discussed in [CatBoost](https://arxiv.org/abs/1706.09516). Counts are only denominators for smoothing, never feature columns. No cross-validation, additional evaluation metric, or refit on the encoder rows.

- Result: **0.7486 AUC**, **discard**, commit `7bc9f1e`. Run time: 23.0s (training 2.4s, eval 20.6s, ok)
- Interpretation: AUC fell to 0.7486. The independently fitted lookup features do not compensate for reducing classifier training to 100000 rows.

## Experiment 28 — ordered airport-date target statistics from all training rows

- Parent: `5a96fa7`. Class: **exploration**.
- Hypothesis: Adapt ordered target statistics using two deterministic hashes of raw input fields. For each airport/date lookup, use only training keys with strictly smaller hashes, excluding ties. The same row receives the same feature in a batch or alone; its label is never used to produce its own lookup feature. Average the two orderings to reduce prefix variance and train the classifier on all rows.
- Source: [CatBoost ordered target statistics](https://arxiv.org/abs/1706.09516). Our adaptation also uses prefix lookups at inference, instead of switching to full-group means. No input label, row index, frequency feature, cross-validation score, or additional dataset enters feature preparation.

- Complexity gate, set before reading final AUC: require at least +0.002 AUC for the ordered-lookup implementation. Saved-artifact checks confirm feature invariance to input-label changes and batch size.

- Result: **0.7592 AUC**, **keep**, commit `fa32973`. Run time: 55.8s (training 13.2s, eval 42.6s, ok)
- Interpretation: AUC improves by exactly 0.0020 to 0.7592, meeting the predeclared complexity gate. All 200000 rows train the classifier, with own-key ties excluded from lookup prefixes. The saved prepare also passed label-invariance and batch-invariance checks. Retain.

## Experiment 29 — ordered carrier-date delay rates

- Parent: `fa32973`. Class: **follow-up**.
- Hypothesis: Add a carrier/date rate using the same two independent input-hash orderings. Daily airline disruptions may add information beyond airport/date rates and the existing carrier/month category, without extra encoding machinery.
- Source: Ordered-target-statistic research and experiment 28; the seasonal airline improvement in experiment 17 motivates the finer temporal interaction.

- Result: **0.7576 AUC**, **discard**, commit `821efff`. Run time: 58.7s (training 14.6s, eval 44.1s, ok)
- Interpretation: AUC decreased from 0.7592 to 0.7576. Airport/date context is useful, but this extra airline/date rate is not; remove it.

## Experiment 30 — average four deterministic input orderings

- Parent: `fa32973`. Class: **follow-up**.
- Hypothesis: Increase ordered airport/date statistics from two to four hash orderings. Averaging more prefixes should reduce variance while preserving identical row-wise behavior and excluding each matching input key from its own statistics.
- Source: The CatBoost paper investigates multiple permutations; here the test specifically concerns variance of our row-invariant prefix features, with the same data, groups and model.

- Result: **0.7596 AUC**, **keep**, commit `372184b`. Run time: 86.9s (training 23.4s, eval 63.5s, ok)
- Interpretation: AUC improved by 0.0004 to 0.7596. The algorithm is unchanged and the extra orderings reduce prefix variation, at the cost of 23.4s training phase and 63.5s evaluation phase; both remain within limits.

## Synthesis after experiments 21–30

Best: **0.7596** at `372184b` (+0.0393 versus baseline). Interaction constraints, pairwise loss, training-only early stopping, route-schedule summaries, loss-guided growth and column sampling did not beat the compact classifier. Independent split-based target encodings lost too much model-training data. In contrast, ordered prefix lookups based on input-only hashes let every training row be fitted while excluding its own input key from its encoded statistics; these gained 0.0020, with four orderings adding 0.0004. Carrier/date rates did not help.

The ordered features pass both batch/single-row and input-label-invariance checks. There is no inference switch to whole-group target means: the same prefix rule is used on training and evaluation inputs. The best run took 23.4s for the training phase and 63.5s for evaluation, safely under both limits.

Research refresh: read [XGBoost boosted random forests](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html), [systemic US airport delay propagation](https://arxiv.org/abs/1301.1136) and [spatiotemporal propagation learning](https://arxiv.org/abs/2207.06959). Regional sharing and within-day context are candidate extensions of the ordered statistics, but first test regularization and model averaging on the now more informative features.

## Experiment 31 — stronger L2 leaf regularization

- Parent: `372184b`. Class: **follow-up**.
- Hypothesis: Set reg_lambda=20 to shrink noisy leaf scores now that ordered rate features provide direct daily context. This targets leaf estimates rather than the unsuccessful categorical threshold and row-sampling controls.
- Source: XGBoost parameter documentation; the new feature representation changes the useful regularization balance.

- Result: **0.7597 AUC**, **keep**, commit `35ea020`. Run time: 85.5s (training 23.0s, eval 62.5s, ok)
- Interpretation: AUC improved marginally to 0.7597 with a one-parameter change. Keep, while treating the 0.0001 gain as small.

## Experiment 32 — fit identical prefix lookups with grouped NumPy sorting

- Parent: `35ea020`. Class: **ablation/simplification**.
- Hypothesis: Replace repeated per-group DataFrame construction with factorized group IDs and lexicographic sorting, keeping the exact sorted hashes and label-prefix sums. Also select the hash input frame once per prepare call. Expect identical AUC and faster preparation.
- Source: [NumPy lexsort](https://numpy.org/doc/stable/reference/generated/numpy.lexsort.html) and [pandas factorize](https://pandas.pydata.org/docs/reference/api/pandas.factorize.html). This is a computational simplification, with no intended feature or model change.

- Result: **0.7597 AUC**, **keep**, commit `9c71431`. Run time: 66.5s (training 8.5s, eval 58.0s, ok)
- Interpretation: AUC remains 0.7597. All 349392 saved group tables match the prior artifact at every valid search boundary, including duplicate-key exclusions. Training phase dropped from 23.0s to 8.5s; total runtime from 85.5s to 66.5s. Keep the computational simplification.

## Experiment 33 — average feature-randomized trees within boosting

- Parent: `9c71431`. Class: **exploration**.
- Hypothesis: Set num_parallel_tree=4 and colsample_bynode=0.8, retaining every training row. Averaging four different split choices per boosting step may reduce variance in the richer rate-feature model without the harmful row subsampling from experiment 14.
- Source: [XGBoost boosted random-forest support](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html). This tests feature-randomized parallel trees; it is not a standalone random forest.

- Result: **0.7609 AUC**, **keep**, commit `f8ab17e`. Run time: 74.0s (training 17.5s, eval 56.5s, ok)
- Interpretation: AUC improved by 0.0012 to 0.7609. Averaging randomized split choices helps the rate-feature model; total training phase is 17.5s, leaving ample headroom.

## Experiment 34 — ordered airport and date main-effect rates

- Parent: `f8ab17e`. Class: **follow-up**.
- Hypothesis: Add ordered rates for Origin, Dest and calendar date separately. These broadly supported main effects may complement the noisier airport/date interactions and make baseline risk easier to represent numerically.
- Source: Ordered target-statistic research, with all lookups using the same input-only hashes and strict exclusion rule as the successful airport/date rates.

- Result: **0.7604 AUC**, **discard**, commit `193cea8`. Run time: 85.1s (training 24.3s, eval 60.8s, ok)
- Interpretation: AUC fell to 0.7604 while the artifact grew to 117 MB. Remove the broad rates and keep only the useful airport/date interactions.

## Experiment 35 — weaker smoothing of ordered airport-date rates

- Parent: `f8ab17e`. Class: **follow-up**.
- Hypothesis: Reduce smoothing from 20 to 5 prior observations. The four-order average and parallel trees already reduce variance; weaker shrinkage may preserve genuine sharp daily disruption signals at airports.
- Source: Prior smoothing in the CatBoost target-statistic formulation; this changes estimator bias rather than which rows contribute to each prefix.

- Result: **0.7605 AUC**, **discard**, commit `44084f9`. Run time: 73.9s (training 17.4s, eval 56.6s, ok)
- Interpretation: AUC 0.7605 is lower by 0.0004; the original stronger prior remains preferable.

## Experiment 36 — ordered regional daily disruption rates

- Parent: `f8ab17e`. Class: **exploration**.
- Hypothesis: Infer airport geometry from training route distances, cluster airports into 12 regions, and add ordered region/date rates for both endpoints. Regional pooling may stabilize local daily disruption signals. This differs from experiment 20, which supplied raw coordinates rather than pooled daily label statistics. Require at least +0.002 AUC for the added complexity.
- Source: [Spatiotemporal propagation learning](https://arxiv.org/abs/2207.06959), classical MDS, and KMeans documentation. All geometry and all prefix statistics are fitted exclusively on train.csv.

- Result: **0.7631 AUC**, **keep**, commit `ca7fab4`. Run time: 82.3s (training 22.9s, eval 59.5s, ok)
- Interpretation: AUC increased by 0.0022 to 0.7631, clearing the predeclared complexity gate. Regional pooling is useful when applied to daily disruption statistics, although raw coordinate features were not. Training phase 22.9s, evaluation 59.5s.

## Experiment 37 — origin-region disruption rates within six-hour windows

- Parent: `ca7fab4`. Class: **follow-up**.
- Hypothesis: Add an ordered origin-region/date/six-hour-block rate. Regional daily averages may obscure localized disruption periods; the coarser geographic grouping should retain more support than airport-by-hour keys.
- Source: [Within-day delay propagation](https://arxiv.org/abs/1304.2528) and [spatiotemporal modeling](https://arxiv.org/abs/2207.06959). Blocks use scheduled local departure time only, with midnight mapped consistently.

- Result: **0.7628 AUC**, **discard**, commit `2de9d78`. Run time: 85.8s (training 24.4s, eval 61.5s, ok)
- Interpretation: AUC 0.7628 is lower by 0.0003, and the artifact is larger. Daily regional rates suffice for now; remove the finer time grouping.

## Experiment 38 — remove marginal time components

- Parent: `ca7fab4`. Class: **ablation/simplification**.
- Hypothesis: Delete separate departure hour and minute columns, retaining raw scheduled time. Their initial contribution was only 0.0001, and the richer regional/rate model may no longer need them. Remove one-time schema/example logging as cleanup with no modeling effect.
- Source: Experiment 7 and the simplicity criterion; this tests feature deletion rather than another expansion.

- Result: **0.7632 AUC**, **keep**, commit `fa40e78`. Run time: 79.6s (training 21.6s, eval 58.0s, ok)
- Interpretation: AUC improved slightly to 0.7632 with five fewer lines and a shorter evaluation phase. Keep the simplification.

## Experiment 39 — resource-bounded dropout boosting

- Parent: `fa40e78`. Class: **exploration**.
- Hypothesis: Test DART with 300 rounds at learning rate 0.1, one tree per round, rate_drop=0.05, skip_drop=0.8 and forest normalization. Dropout may reduce overspecialization. Fewer parallel trees bound the extra prediction cost; this is a practical DART configuration, not a clean one-parameter ablation.
- Source: [Original DART paper](https://proceedings.mlr.press/v38/korlakaivinayak15.html) and [XGBoost DART tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html).

- Result: **0.7641 AUC**, **keep**, commit `85dc0fb`. Run time: 102.0s (training 44.6s, eval 57.4s, ok)
- Interpretation: AUC improves by 0.0009 to 0.7641. Training phase 44.6s and evaluation 57.4s fit the limits. Installed XGBoost warns that the legacy dart booster name is deprecated; its recommended ordinary-tree interface accepts the same dropout parameters.

## Experiment 40 — use the supported tree-dropout interface

- Parent: `85dc0fb`. Class: **ablation/simplification**.
- Hypothesis: Remove the deprecated booster=dart alias and retain rate_drop, skip_drop and forest normalization. The installed library and official tutorial say these enable dropout directly in the tree booster, so predictions should be unchanged without the warning.
- Source: [Current XGBoost DART tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) and the installed-library warning from experiment 39.

- Result: **0.7641 AUC**, **keep**, commit `3528c97`. Run time: 100.3s (training 43.4s, eval 56.8s, ok)
- Interpretation: AUC remains 0.7641 and the deprecation warning is gone. Keep the one-line simplification; training phase 43.4s and evaluation 56.8s.

## Synthesis after experiments 31–40

Best: **0.7641** at `3528c97` (+0.0438 versus baseline). L2 regularization helped slightly; four feature-randomized trees per boosting step helped more. Broad airport/date main-effect rates and weaker prior smoothing did not help. Distance-derived geographic regions became useful when paired with ordered daily disruption rates (+0.0022), although raw geometry had previously failed. Finer six-hour grouping did not improve AUC. Deleting marginal time components improved simplicity and slightly improved score.

A grouped-array implementation preserved all 349392 original prefix tables at every valid query boundary and reduced the training phase from 23.0s to 8.5s. This released enough time for stronger model experiments. A resource-bounded dropout configuration then improved AUC to 0.7641; its supported non-legacy interface gives the same score without warnings.

Research refresh: read the [DART paper](https://proceedings.mlr.press/v38/korlakaivinayak15.html), its [XGBoost implementation](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html), [CPU gradient-based sampling](https://xgboost.readthedocs.io/en/release_3.2.0/parameter.html), and [histogram versus Hessian-weighted tree methods](https://xgboost.readthedocs.io/en/stable/treemethod.html). Next compare deeper ordinary trees, finer numeric binning, adaptive row sampling, and the variance/computation tradeoff of additional input orderings.

## Experiment 41 — deeper ordinary boosting on the richer representation

- Parent: `3528c97`. Class: **follow-up**.
- Hypothesis: Return to the best ordinary-boosting configuration from experiment 38, but increase depth from 4 to 6. Ordered airport/region rates may now support useful higher-order interactions, unlike the original-feature depth test. Compare against both the old ordinary model (0.7632) and current dropout best (0.7641).
- Source: XGBoost bias–variance guidance plus the substantial representation change since the early depth experiments.

- Result: **0.7582 AUC**, **discard**, commit `b1fa2f2`. Run time: 88.0s (training 29.6s, eval 58.4s, ok)
- Interpretation: Extra depth reduced AUC from 0.7641 to 0.7582 despite more trees. Keep the shallower dropout model; the ordered daily rates do not need this interaction capacity.

## Experiment 42 — Finer numeric histogram bins

- Parent: `3528c97`. Class: **follow-up**.
- Hypothesis: Increasing max_bin from 256 to 1024 may preserve useful distinctions among continuous ordered rates and scheduled departure times. This changes numeric resolution while retaining the successful dropout model.
- Source: https://xgboost.readthedocs.io/en/stable/treemethod.html — histogram accuracy can improve with more bins; https://xgboost.readthedocs.io/en/stable/parameter.html — max_bin cost and accuracy tradeoff.

- Result: **0.7638 AUC**, **discard**, commit `8264d91`. Run time: 101.5s (training 44.2s, eval 57.3s, ok)
- Interpretation: The finer bins reached 0.7638, slightly below the 0.7641 baseline; numeric quantization is not the current bottleneck. Revert to the default 256 bins.

## Experiment 43 — Gradient-based row sampling

- Parent: `3528c97`. Class: **exploration**.
- Hypothesis: Retain 60% of rows per tree with importance proportional to regularized gradients. Unlike experiment 14 uniform sampling, this prioritizes difficult examples and may regularize dropout boosting without losing as much categorical information.
- Source: https://xgboost.readthedocs.io/en/stable/parameter.html — gradient_based uses sqrt(g^2 + lambda*h^2), supports CPU since 3.2, and requires hist.

### Integrity and next-step research

The saved `3528c97` artifact passed synthetic checks for identical batch/single-row features, unknown-category handling, and feature independence from the supplied target label. No additional metric was computed. Its training split-gain diagnostic puts the two region/date rates first; numeric DayOfYear has very little gain. This motivates a later date-feature ablation, without treating training importance as an evaluation score.

Read https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html: soft voting averages predicted probabilities and fits fresh clones of constituent estimators. A two-model average could combine the strongest ordinary and dropout models within the one-minute training limit. Read https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html: constraints can regularize a plausible directional relationship; numerical histogram resolution can restrict feasible splits. A later experiment can constrain the ordered daily rates to increasing effects.

- Result: **0.7595 AUC**, **discard**, commit `e906e0e`. Run time: 106.9s (training 49.9s, eval 57.0s, ok)
- Interpretation: Importance-weighted subsampling also hurts, scoring 0.7595 versus 0.7641. The daily categorical and ordered features appear to benefit from full row coverage; sampling is slower too.

## Experiment 44 — Average the strongest ordinary and dropout models

- Parent: `3528c97`. Class: **exploration**.
- Hypothesis: The ordinary four-tree-per-round model scored 0.7632 and dropout scored 0.7641. Equal probability averaging may reduce their different errors. Fit both fresh on the same training features; no validation-derived weights or extra evaluation. Expected training phase about 55 seconds. Require at least 0.0005 gain for the second model.
- Source: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html — soft voting averages probabilities and fits cloned estimators.

- Result: **0.0000 AUC**, **crash**, commit `cad60d4`. Run time: 60.0s (training 60.0s, eval 0.0s, timeout-training)
- Interpretation: The ensemble exceeded the 60-second training limit before evaluation. Its ordinary member inherited dropout controls (skip_drop=1), which may still activate dropout bookkeeping. Retry once with dropout parameters entirely absent from that member and explicit per-model fit timings.

## Experiment 45 — Avoid dropout bookkeeping in the ordinary ensemble member

- Parent: `3528c97`. Class: **follow-up**.
- Hypothesis: The previous budget estimate assumed ordinary boosting speed. Remove all dropout-related parameters from that estimator rather than setting a skip probability of one, so it can use ordinary prediction caching. Keep both model capacities and equal voting unchanged. Retain the same 0.0005 improvement gate.
- Source: https://xgboost.readthedocs.io/en/stable/tutorials/dart.html — dropout disables ordinary prediction-buffer advantages; https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html — soft voting.

- Follow-up source check: XGBoost 3.4.1 source confirms the suspected cause: `HasDropout()` is true whenever `skip_drop` is nonzero, even with zero drop rate. Source: https://github.com/dmlc/xgboost/blob/v3.4.1/src/gbm/gbtree.h#L114-L116 . The retry removes that control from the ordinary member.

- Result: **0.7649 AUC**, **keep**, commit `a3e1e77`. Run time: 112.9s (training 54.8s, eval 58.1s, ok)
- Interpretation: The corrected ensemble trained within the limit (54.8 seconds including preparation) and improved to 0.7649, a 0.0008 gain that clears the predeclared complexity gate. Ordinary fitting took 11.3 seconds, confirming the dropout bookkeeping diagnosis.

## Experiment 46 — Single ordinary model matched to dropout capacity

- Parent: `a3e1e77`. Class: **ablation/simplification**.
- Hypothesis: Replace the ensemble with one ordinary 300-round, learning-rate-0.1 model while retaining the same features and regularization. This isolates dropout from changes in learning rate and tree count, and tests whether a much cheaper single model can retain the ensemble score.
- Source: https://xgboost.readthedocs.io/en/stable/tutorials/dart.html — ordinary boosting uses cached predictions; comparison keeps dropout-member capacity fixed.

- Result: **0.7613 AUC**, **discard**, commit `c813bc0`. Run time: 69.2s (training 11.6s, eval 57.5s, ok)
- Interpretation: The matched-capacity ordinary model scored 0.7613. This confirms dropout itself is useful, beyond the changed learning rate/tree count, and the much cheaper model is not an adequate replacement for the 0.7649 ensemble.

## Experiment 47 — Batch queries against frozen ordered-statistic tables

- Parent: `a3e1e77`. Class: **follow-up**.
- Hypothesis: Grouping query positions by lookup key lets NumPy search each fixed training table for an array of hashes instead of individual scalars. No statistics will be aggregated over the query frame. Identical per-row features with faster training preparation would create room for better feature estimates under the 60-second cap. Require exact feature equivalence and a material preparation-time saving.
- Source: https://numpy.org/doc/stable/reference/generated/numpy.searchsorted.html — the v argument is vectorized and side=left retains strict-prefix semantics.

- Differential verification: all 200000 training rows have exactly identical features and labels between the saved reference and candidate artifacts. Preparation-only timing in this diagnostic: 8.517s before, 3.074s after. This is a functional/timing check, not a metric evaluation.

- Result: **0.7649 AUC**, **keep**, commit `cb16b38`. Run time: 108.6s (training 50.0s, eval 58.5s, ok)
- Interpretation: All 200000 training rows matched exactly. AUC remains 0.7649, while the training phase falls from 54.8 to 50.0 seconds and isolated preparation from 8.517 to 3.074 seconds. The two added lines replace millions of scalar searches with batched calls and create usable headroom under the training cap.

## Experiment 48 — Eight ordered-statistic permutations

- Parent: `cb16b38`. Class: **follow-up**.
- Hypothesis: Doubling the fixed input-hash orderings from four to eight should reduce noise in daily target-rate estimates, motivated by the earlier two-to-four improvement. The vectorized lookup path now makes the larger tables feasible within the training budget. Require at least 0.0005 AUC improvement to justify doubled lookup storage.
- Source: https://papers.neurips.cc/paper/7898-catboost-unbiased-boosting-with-categorical-features.pdf — multiple permutations reduce ordered-statistic variance. Keep identical prefix rules in training and inference.

- Result: **0.7647 AUC**, **discard**, commit `09b3174`. Run time: 143.8s (training 52.2s, eval 91.6s, ok)
- Interpretation: Eight permutations score 0.7647, below the four-permutation 0.7649, while increasing the artifact to 182.2 MB and evaluation to 91.6 seconds. Revert: additional order averaging is not a useful cost tradeoff here.

## Experiment 49 — More local airport regions

- Parent: `cb16b38`. Class: **follow-up**.
- Hypothesis: Increase distance-derived KMeans regions from 12 to 24. The daily region rates are the highest-gain training features; finer geographic pooling may separate localized disruptions that a larger region averages together. Keep the same four orderings and smoothing to isolate spatial scale.
- Source: https://arxiv.org/abs/2207.06959 — geographic proximity and airline scheduling capture complementary delay propagation relationships; adaptation here uses only route distances from train.csv.

- Result: **0.7648 AUC**, **discard**, commit `144d443`. Run time: 109.0s (training 50.1s, eval 58.9s, ok)
- Interpretation: The finer regional grouping scored 0.7648 versus 0.7649. It does not justify a change; the current 12-region pooling has a slightly better locality/variance balance on the evaluation split.

## Experiment 50 — Remove redundant numeric day-of-year

- Parent: `cb16b38`. Class: **ablation/simplification**.
- Hypothesis: Numeric DayOfYear had almost zero split gain in the saved model. Retain the FlightDate categorical and all date-based lookup keys, but stop exposing a duplicate ordinal date column; this may reduce distractor splits and simplifies the feature set.
- Source: Training-only gain diagnostic from experiment 43; https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html — control capacity and avoid unnecessary complexity.

- Result: **0.7652 AUC**, **keep**, commit `c1e763d`. Run time: 106.9s (training 50.7s, eval 56.2s, ok)
- Interpretation: Removing the weak ordinal date feature improves AUC to 0.7652 and reduces the feature set. Keep this simplification; the categorical date and ordered daily rates retain date context.

## Synthesis after 50 experiments

Best kept model: `c1e763d`, 0.7652 AUC, versus baseline 0.7203. The ordinary/dropout probability average gained 0.0008; a matched-capacity ordinary model confirmed dropout has a real contribution. Finer bins, deeper trees, and gradient-weighted row sampling did not help. Eight hash orderings and 24 regions were close but worse and were reverted. Removing numeric day-of-year improved the simpler feature set. Vectorized fixed-table queries were verified exactly on all 200000 training rows and recovered about five seconds of training headroom.

Current theory: daily disruption estimates and carefully regularized categorical interactions matter more than finer numerical resolution or extra capacity. Next test directional constraints on the daily rates, direct carrier/airport interactions, and a smoother representation of the global date effect. Fresh research: https://arxiv.org/abs/2104.00629 supports regularized target encoding over arbitrary integer encodings; https://scikit-learn.org/stable/auto_examples/ensemble/plot_monotonic_constraints.html and https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html motivate domain-based monotonicity. The Micci-Barreca ACM full text was unavailable, so no claim about its detailed implementation is relied upon.

## Experiment 51 — Increasing constraints on daily delay-rate features

- Parent: `c1e763d`. Class: **exploration**.
- Hypothesis: Holding the flight context fixed, larger ordered daily delay rates should usually imply greater delay risk. Constrain the four numeric rates to increasing effects in both ensemble members, reducing flexibility to fit noisy reversals without constraining raw airport, date, or time features.
- Source: https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html — named-feature constraints and their regularizing role; the direction is a domain hypothesis, not a theorem.

- Result: **0.7649 AUC**, **discard**, commit `63770b9`. Run time: 107.0s (training 51.1s, eval 56.0s, ok)
- Interpretation: Increasing constraints score 0.7649 versus 0.7652. The directional prior does not improve this model, possibly because noisy correlated rate estimates need more flexible conditional effects. Revert.

## Experiment 52 — Replace categorical date with an ordered global daily rate

- Parent: `c1e763d`. Class: **ablation/simplification**.
- Hypothesis: A four-ordering global DateRate can capture daily network disruption on a smooth numeric scale. Replace FlightDate and its calendar-offset construction, retaining airport and region daily rates and CarrierMonth. This tests whether direct regularized date effects work better than categorical date partitions.
- Source: https://arxiv.org/abs/2104.00629 — regularized target encoding for categorical features; https://papers.neurips.cc/paper/7898-catboost-unbiased-boosting-with-categorical-features.pdf — strict ordered prefixes exclude the query row and its ties.

- Result: **0.7599 AUC**, **discard**, commit `d9091e7`. Run time: 103.2s (training 47.8s, eval 55.5s, ok)
- Interpretation: The numeric global date rate scores 0.7599, substantially worse than 0.7652. Categorical date carries useful conditional structure beyond a single daily delay propensity; retain it.

## Experiment 53 — Hierarchical smoothing of airport daily rates

- Parent: `c1e763d`. Class: **exploration**.
- Hypothesis: The current sparse airport/day rates shrink toward 0.5 even during a broad regional disruption. For each ordering, shrink an airport/day prefix mean toward its matching region/day prefix rate instead, retaining both features. Regional priors use exactly the same strict hash prefix and never include the query row or ties. This adapts regularized target encoding to the geography already learned from training distances. Require at least 0.0005 improvement for the extra feature logic.
- Source: https://arxiv.org/pdf/2104.00629 — smoothing noisy category effects; https://papers.neurips.cc/paper/7898-catboost-unbiased-boosting-with-categorical-features.pdf — ordered target statistics. Regional rather than global smoothing is our hypothesis, not a claimed recipe from either paper.

- Result: **0.7647 AUC**, **discard**, commit `1edb4c1`. Run time: 106.5s (training 50.0s, eval 56.4s, ok)
- Interpretation: Hierarchical smoothing scores 0.7647, below the simpler 0.7652 model. Letting the trees combine the separate airport and region rates works better than imposing this particular pooling rule.

## Experiment 54 — Carrier-by-origin categorical interaction

- Parent: `c1e763d`. Class: **exploration**.
- Hypothesis: Airlines can have different operating performance at different departure airports. A CarrierOrigin categorical cross makes this interaction available in one split, analogous to the successful CarrierMonth feature but denser than the failed full Route category. Require at least 0.0003 gain for the extra feature.
- Source: https://arxiv.org/abs/1904.12857 — categorical feature crossing can expose useful interactions; https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html — native partition-based handling.

- Result: **0.7649 AUC**, **discard**, commit `cce1b56`. Run time: 112.0s (training 52.2s, eval 59.8s, ok)
- Interpretation: The carrier-origin cross scores 0.7649, below 0.7652, and increases artifact size to 127.3 MB. Existing raw carrier/airport and CarrierMonth interactions are sufficient for this configuration.

## Experiment 55 — Shallower trees with engineered interaction features

- Parent: `c1e763d`. Class: **ablation/simplification**.
- Hypothesis: Airport/date rates and CarrierMonth already encode high-order interactions. Reducing both ensemble members from depth four to three may prevent unnecessary residual interactions, following the poor depth-six result, while reducing model size and training cost.
- Source: https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html — max_depth controls model complexity; earlier depth-six experiment fell to 0.7582.

- Result: **0.7630 AUC**, **discard**, commit `7cd625b`. Run time: 96.1s (training 39.8s, eval 56.3s, ok)
- Interpretation: Depth three scores 0.7630, too much loss for the smaller artifact and 39.8-second training phase. Combined with the depth-six failure, depth four remains the supported capacity choice.

## Experiment 56 — Weight-aware dropout selection

- Parent: `c1e763d`. Class: **follow-up**.
- Hypothesis: Forest-normalized dropout gives trees unequal weights. Sampling dropped trees in proportion to those weights may regularize dominant contributions more effectively than uniform selection. Change only the dropout member; the ordinary ensemble member remains free of dropout controls.
- Source: https://xgboost.readthedocs.io/en/stable/parameter.html — sample_type=weighted selects dropped trees in proportion to their weight; https://proceedings.mlr.press/v38/korlakaivinayak15.pdf — refreshed DART algorithm and normalization research while experiment 55 ran.

- Result: **0.7650 AUC**, **discard**, commit `1eee476`. Run time: 106.6s (training 50.2s, eval 56.4s, ok)
- Interpretation: Weighted tree dropout scores 0.7650 versus 0.7652. Uniform tree selection remains marginally better, with the same training cost.

## Experiment 57 — Broader geographic pooling

- Parent: `c1e763d`. Class: **follow-up**.
- Hypothesis: Twenty-four regions did not improve over twelve. Test six regions to emphasize more stable broad daily disruption estimates, while the separate airport/day rates retain local information. This probes the other side of the geographic bias-variance tradeoff rather than another fine subdivision.
- Source: https://arxiv.org/abs/2207.06959 — geographic and network dependencies in flight delays; experiments 36 and 49 established the usefulness and limits of regional pooling.

- Result: **0.7641 AUC**, **discard**, commit `67db199`. Run time: 106.0s (training 50.2s, eval 55.8s, ok)
- Interpretation: Six regions score 0.7641, worse than both the 12-region best and the 24-region trial. The original intermediate spatial scale remains the strongest tested setting.

## Experiment 58 — Allow balanced partitions of high-cardinality categories

- Parent: `c1e763d`. Class: **follow-up**.
- Hypothesis: Increase max_cat_threshold from 64 to 256. The categorical split implementation scans bounded prefixes in both directions, so the current limit omits middle partitions for the 365-level date feature. More balanced partitions may represent broad date and airport effects without extra tree depth. This follows the earlier loss from reducing the threshold to 16.
- Source: https://github.com/dmlc/xgboost/blob/v3.4.1/src/tree/hist/evaluate_splits.h#L133-L150 — bounded forward/backward category scans; https://xgboost.readthedocs.io/en/stable/parameter.html — max_cat_threshold.

### Training-only split-gain diagnostic

For saved best `c1e763d`, non-leaf split-gain quantiles at 10%, 25%, 50%, 75% are dropout [14.418, 35.751, 59.257, 92.026] and ordinary [9.650, 29.817, 54.948, 85.150]. No prediction metric was computed. This motivates a modest gamma=10 pruning test rather than choosing an arbitrary large threshold.

- Result: **0.7635 AUC**, **discard**, commit `25b19ea`. Run time: 107.6s (training 51.5s, eval 56.2s, ok)
- Interpretation: The broader categorical search scores 0.7635 versus 0.7652. Although it offers middle partitions, the original threshold provides useful regularization on these categories. Revert.

## Experiment 59 — Prune weak residual splits

- Parent: `c1e763d`. Class: **ablation/simplification**.
- Hypothesis: Set gamma=10 to reject the weakest split improvements in both ensemble members. Saved-model split-gain diagnostics put this near the lower tenth of ordinary-model splits and below the lower tenth for dropout, making it a modest pruning threshold rather than a large capacity reduction.
- Source: https://xgboost.readthedocs.io/en/stable/parameter.html — gamma is the minimum loss reduction required for a split; training-only split-gain diagnostic recorded above.

- Result: **0.7641 AUC**, **discard**, commit `15eb2ba`. Run time: 96.6s (training 40.6s, eval 56.1s, ok)
- Interpretation: Pruning improves speed and size but lowers AUC to 0.7641, losing 0.0011. Keep the unpruned model: the weak residual splits collectively carry useful signal.

## Experiment 60 — Expose the learned geographic regions as categories

- Parent: `c1e763d`. Class: **exploration**.
- Hypothesis: The model sees regional daily rates but not the region identity itself. Add OriginRegion and DestRegion categorical features using the same existing training-distance clusters, enabling different seasonal or carrier effects by region without raw continuous coordinates or new lookup fitting.
- Source: https://arxiv.org/abs/2207.06959 — geographic context and spatiotemporal interactions; https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html — native categories. Earlier raw-coordinate trial lacked the now-successful regional daily context.

- Result: **0.7649 AUC**, **discard**, commit `b8583fe`. Run time: 110.6s (training 50.3s, eval 60.3s, ok)
- Interpretation: Region identities score 0.7649 versus 0.7652. The daily-rate features already capture the useful geographic context. Revert the extra categories; their unknown-region conversion also produced a pandas deprecation warning, which would need fixed-vocabulary codes if this idea were retained.

## Synthesis after 60 experiments

Best remains `c1e763d`, 0.7652 AUC. The last block tested stronger structural alternatives: monotonicity, global date-rate replacement, hierarchical airport/region smoothing, a carrier-origin cross, shallower trees, weighted dropout, six regions, broader category partitions, gain pruning, and explicit region categories. None beat the retained model. The large losses from replacing FlightDate, changing depth, and broader category partitions reinforce the importance of categorical date interactions at moderate capacity. Twelve regions and independent airport/region rates remain supported; extra geographic identity and hierarchical coupling do not help.

Fresh research revisited the original DART normalization algorithm (https://proceedings.mlr.press/v38/korlakaivinayak15.pdf), the documented tree-versus-forest normalization (https://xgboost.readthedocs.io/en/stable/tutorials/dart.html), and L1 weight regularization (https://xgboost.readthedocs.io/en/stable/parameter.html). In the remaining time, test normalization, stronger rate smoothing, and concise feature/representation simplifications. No additional metrics or held-out data have been used.

## Experiment 61 — Tree-normalized dropout

- Parent: `c1e763d`. Class: **follow-up**.
- Hypothesis: Change dropout normalization from forest to tree. Weighting a new tree relative to individual dropped trees rather than their summed weight may preserve a different useful balance of early and late learners and complement the ordinary ensemble member. Keep drop frequency, tree count, learning rate, and all features fixed.
- Source: https://xgboost.readthedocs.io/en/stable/tutorials/dart.html — tree and forest normalization formulas; https://proceedings.mlr.press/v38/korlakaivinayak15.pdf — original dropout normalization algorithm.

- Result: **0.7638 AUC**, **discard**, commit `3c442d3`. Run time: 107.0s (training 50.4s, eval 56.6s, ok)
- Interpretation: Tree normalization scores 0.7638 versus 0.7652. The forest-normalized dropout model remains the better complement to ordinary boosting.

## Experiment 62 — Stronger smoothing for ordered daily rates

- Parent: `c1e763d`. Class: **follow-up**.
- Hypothesis: Increase the prior weight from 20 to 50 for all four ordered rates. The earlier reduction to five hurt; stronger pooling toward the fixed balanced-class prior may reduce noisy daily fluctuations without adding features or lookup tables.
- Source: https://arxiv.org/pdf/2104.00629 — regularized target encodings shrink noisy category effects; https://papers.neurips.cc/paper/7898-catboost-unbiased-boosting-with-categorical-features.pdf — ordered prefix statistics with a prior.

- Result: **0.7646 AUC**, **discard**, commit `1c304fc`. Run time: 106.4s (training 50.2s, eval 56.2s, ok)
- Interpretation: Stronger smoothing scores 0.7646, below 0.7652. With both weaker and stronger tested smoothing worse, the retained prior weight of 20 has the best supported balance.

## Experiment 63 — Remove raw distance from the prediction features

- Parent: `c1e763d`. Class: **ablation/simplification**.
- Hypothesis: Raw Distance had relatively low training split gain, while the pipeline now uses route distances to fit geographic groups and keeps raw airports. Remove only the raw numeric Distance predictor; retain it in the fixed input fingerprint and geographic lookup fitting. This tests redundancy without changing the ordered-rate samples.
- Source: Saved-model training-only feature-gain diagnostic; https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html — simplify unnecessary feature/model complexity.

- Simplicity gate for this small raw-feature ablation: retain only if rounded AUC is no worse than the best; geographic fitting still needs Distance, so a score reduction is not justified by the limited code saving.

- Result: **0.7635 AUC**, **discard**, commit `f74f043`. Run time: 105.9s (training 50.2s, eval 55.7s, ok)
- Interpretation: Removing raw distance scores 0.7635, so distance still adds useful context beyond airport identities and daily geographic rates. Restore it.

## Experiment 64 — Store exact integer prefix totals compactly

- Parent: `c1e763d`. Class: **ablation/simplification**.
- Hypothesis: Every stored prefix total is an integer bounded by the training row count. Use uint32 rather than float64 for these fitted totals, guarded against overflow, while retaining uint64 hashes and float64 feature arithmetic. This should reduce artifact size with exactly identical features and AUC; require full differential verification before keeping.
- Source: https://numpy.org/doc/stable/reference/generated/numpy.iinfo.html — integer dtype bounds; the prefix totals are sums of binary training labels.

- Differential verification: Exactly equal: 379828 frozen lookup tables and all 200000 training-row features. Saved candidate also passes row/batch and supplied-label independence checks. No additional metric was computed.

- Result: **0.7652 AUC**, **keep**, commit `204378f`. Run time: 109.8s (training 50.7s, eval 59.1s, ok)
- Interpretation: All 379828 stored lookup tables and all 200000 training-row features match exactly, and saved-function row/batch and supplied-label checks pass. AUC is unchanged at 0.7652 while artifact size drops from 104.4 to 90.1 MB. Keep the exact compact representation.

## Experiment 65 — Remove raw carrier while retaining CarrierMonth

- Parent: `204378f`. Class: **ablation/simplification**.
- Hypothesis: CarrierMonth already contains carrier identity. Removing the separate raw carrier category may avoid redundant partitions and one categorical conversion per inference row while retaining the combined carrier/season context. Keep only if rounded AUC is no worse.
- Source: The successful removal of redundant numeric day-of-year motivates this analogous ablation; https://arxiv.org/abs/1904.12857 discusses categorical crossed representations.

- Result: **0.7644 AUC**, **discard**, commit `4f50437`. Run time: 105.3s (training 49.4s, eval 55.9s, ok)
- Interpretation: The raw-carrier ablation scores 0.7644 versus 0.7652. CarrierMonth does not fully replace the useful simpler carrier partitions at this tree capacity; restore the raw category.

## Experiment 66 — L1 regularization of leaf weights

- Parent: `204378f`. Class: **exploration**.
- Hypothesis: Set reg_alpha=10 in both ensemble members. The earlier gain-pruning trial removed useful weak splits; an L1 penalty instead shrinks leaf corrections and may stabilize sparse categorical effects. Keep all features, dropout controls, and tree capacity fixed.
- Source: https://xgboost.readthedocs.io/en/stable/parameter.html — reg_alpha is L1 regularization on leaf weights; this parameter was researched during the experiment-60 synthesis.

- Result: **0.7647 AUC**, **discard**, commit `fc7a31f`. Run time: 106.2s (training 49.9s, eval 56.3s, ok)
- Interpretation: L1 regularization reduces artifact size to 80.6 MB but lowers AUC to 0.7647. Restore the exact compact 0.7652 model. This was the final experiment, launched before the clock deadline and allowed to finish under the harness time limits.

## Final summary

The full two-hour experiment is complete. Branch: `oct1`. Selected commit: `204378f` (`204378fba6dfadf540f029608dfdd4eef0d43ed3`). Best retained Eval AUC: **0.7652**, from baseline **0.7203**, an absolute increase of **0.0449**. Completed 67 harness runs including the baseline: 25 kept, 41 discarded, and 1 training-timeout failure. The final run began before the deadline and finished afterward; no experiments were launched after expiry.

The selected artifact is `artifacts/204378fba6dfadf540f029608dfdd4eef0d43ed3.pkl`, 90.1 MB. It averages a 300-round dropout XGBoost model with an ordinary 600-round model using four feature-randomized trees per round. Both use depth four, full row coverage, minimum child weight 20 and L2 regularization 20. Features include scheduled departure time, distance, raw carrier/airport categories, categorical flight date, CarrierMonth, and four ordered daily delay rates at airport and training-distance-derived regional levels. Twelve geographic regions and four deterministic input-hash orderings were retained.

What worked: categorical date and carrier/month context; strict-prefix target statistics; geographic pooling of daily disruption rates; moderate tree capacity and regularization; combining ordinary and dropout boosting; removal of redundant numeric day-of-year. Fixed-vocabulary categorical codes, vectorized frozen-table queries, and compact integer prefix totals improved execution or storage while preserving behavior.

What did not: excessive depth or boosting capacity, row subsampling, forced one-hot encoding, sparse route crosses, extra carrier/airport crosses, raw coordinates or explicit region identities, finer numeric bins, weaker or stronger smoothing, eight orderings, six or 24 regions, global-rate replacement of categorical date, hierarchical pooling, monotonic constraints, gain pruning, altered dropout normalization/selection, and L1 regularization. Raw distance and raw carrier ablations also lost useful signal.

Verification: all 379828 stored lookup tables and all 200000 training-row features were exactly preserved by integer compaction. The selected saved artifact passes exact batch/single-row and supplied-label independence checks, handles an unseen carrier and airport, and produces finite normalized probabilities. Only train.py differs from the starting commit; the evaluation harness is unchanged, the selected source is committed, its final save_and_evaluate call remains last, and all results are logged. Logs and timing files remain uncommitted as required.

Only the harness Eval AUC was used for model selection. No additional prediction metric, held-out test data, archived results, or human-only tooling was used. Small rounded AUC differences have not been assigned statistical significance. Next research direction: derive route-network neighborhood disruption rates from training data, retaining strict row-level label exclusion and batch-invariant preparation, to complement the geographic groups.
