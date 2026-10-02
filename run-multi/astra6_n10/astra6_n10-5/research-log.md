# Research log: oct2

## Setup — 2026-10-02

- Fresh branch: `oct2`, created directly from current HEAD `92e43e6`.
- Read `program.md`, `README-autoresearch.md`, `train.py`, and `harness.py`.
- Confirmed `data/train.csv` and `data/eval.csv` exist without opening either file.
- Required dependencies are installed; no packages were added.
- Initialized `results.tsv` with the required tab-separated header only.
- Baseline training code is unchanged. No experiments have run and the two-hour clock has not started.
- Await user confirmation before starting the clock; first experiment will run the unchanged baseline through the harness.

Setup deviation: the initial batch accidentally read `prepare.py` before its prohibition in `program.md` was known. It was not executed or modified. No eval, holdout, or source data were opened, and no archived results or human-only evaluation tools were read.

## Experiment 1 — baseline — 92e43e6

Unchanged starter: 30 trees, depth 6, learning rate 0.1. Eval AUC **0.7203**, training 1.1 s, evaluation 30.7 s. **Keep** as the baseline.

## Initial research

Read [XGBoost parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html), [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html), [categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html), and [airline-delay research](https://arxiv.org/html/2408.02802v1). Investigate capacity first, then regularization and row-local calendar/time/route features. Candidate ranges: depth 4–10, learning rate 0.03–0.15, child weight 1–100, subsample 0.6–1.0. Train has 200,000 complete, balanced rows and eight predictors. Only training data was inspected. Group counts will not be features.

## Experiment 2 — follow-up

Hypothesis: 30 trees underfit; increase to 300 while holding depth and learning rate fixed. Motivation: baseline is inexpensive and leaves substantial training headroom. Source: XGBoost tuning guide above.

Result: commit d5db16a, Eval AUC **0.7342**, **keep**. Run time: 33.4s (training 2.6s, eval 30.9s, ok).

## Experiment 3 — follow-up

Hypothesis: the 0.0139 gain from more rounds suggests residual underfitting. Test 1,000 trees against 300 to probe the capacity limit with all other settings unchanged. Source: initial XGBoost tuning research.

Result: commit 1bc04f9, Eval AUC **0.7253**, **discard**. Run time: 37.5s (training 6.7s, eval 30.9s, ok).

## Experiment 4 — ablation/simplification

Hypothesis: remove redundant isin/where before categorical construction, preserving exactly the fixed-category mapping. [pandas.Categorical documentation](https://pandas.pydata.org/docs/reference/api/pandas.Categorical.html) specifies unknown values become NaN. Expect equal AUC and lower per-row cost. The 1,000-tree result suggests overfitting beyond 300 trees.

Result: commit 83aa804, Eval AUC **0.7342**, **keep**. Run time: 23.3s (training 2.5s, eval 20.8s, ok).

## Experiment 5 — exploration

Hypothesis: month and day separately make date-specific disruptions hard to learn. Add a categorical calendar-date interaction, with levels fitted only on train. Inference from airline temporal modeling research and [scikit-learn time-feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html). No outcomes or row counts enter this feature. Experiment 4 also passed batched/single-row equivalence and unknown-category checks.

Result: commit 1367ab9, Eval AUC **0.7500**, **keep**. Run time: 29.0s (training 2.6s, eval 26.4s, ok).

## Experiment 6 — follow-up

Hypothesis: new date interactions are useful but small leaves can overfit. Increase min_child_weight from 1 to 20, requiring more evidence per leaf; keep all other settings unchanged. Source: XGBoost parameter reference.

Result: commit d2a5ebd, Eval AUC **0.7517**, **keep**. Run time: 29.1s (training 2.6s, eval 26.5s, ok).

## Experiment 7 — follow-up

Hypothesis: date, airport and carrier effects need deeper interactions. With min_child_weight=20 now improving generalization, test depth 8 versus 6 at the same 300 rounds. Source: XGBoost tuning guide complexity tradeoff. Date features passed one-row/batch consistency checks.

Result: commit 86f3f5d, Eval AUC **0.7460**, **discard**. Run time: 30.2s (training 3.8s, eval 26.4s, ok).

## Experiment 8 — follow-up

Hypothesis: depth 8 overfits; smaller boosting steps may better estimate categorical effects. Set learning_rate=0.05 and n_estimators=600, maintaining the rough step-size-times-rounds product of the best 300/0.1 model. Source: XGBoost tuning guide recommends increasing rounds when reducing eta.

Result: commit 91078a9, Eval AUC **0.7525**, **keep**. Run time: 30.5s (training 4.3s, eval 26.3s, ok).

## Experiment 9 — exploration

Hypothesis: categorical dates ignore calendar adjacency. Add numeric day-of-year alongside the categorical date so trees can pool contiguous seasonal/weather periods. Fixed non-leap-year month offsets are appropriate to the repository-described 2005 data. Source: scikit-learn time-feature engineering; this is an adaptation to tree thresholds.

Result: commit 08b3321, Eval AUC **0.7525**, **discard**. Run time: 35.2s (training 4.4s, eval 30.8s, ok).

## Experiment 10 — exploration

Hypothesis: limiting categorical partition candidates reduces noisy airport/date groupings. Set max_cat_threshold=16 (default 64), preserving all other settings. [XGBoost categorical parameters](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-categorical-feature) explicitly describe this as an overfitting control.

Result: commit e834e0a, Eval AUC **0.7522**, **discard**. Run time: 30.1s (training 3.7s, eval 26.4s, ok).

## Synthesis after 10 experiments

Best: **0.7525**, commit **91078a9** (baseline 0.7203). More trees initially help, but 1,000 at eta 0.1 and depth 8 both hurt. Calendar-date categories deliver the largest feature gain. Child weight 20 and smaller learning steps help. Numeric day-of-year adds no score; categorical threshold 16 is slightly worse. Removing redundant category filtering saves about 10 seconds per evaluation. Working theory: daily disruptions and categorical effects matter, but capacity must be restrained. Next explore explicit route/carrier interactions, time-of-day features, and stochastic regularization before revisiting tree count.

Research refresh: searched categorical regularization, explicit feature interactions and boosted forests. Read [Wide & Deep](https://arxiv.org/abs/1606.07792) for categorical cross-product motivation and [XGBoost forest tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) for averaging within boosting. These motivate new feature crosses and a later variance-reduction test, not adopting their evaluation procedures. Berkeley project page was inaccessible (403); no detailed claims are taken from it.

## Experiment 11 — exploration

Hypothesis: an explicit Origin-Dest route category captures route-specific service patterns that depth-6 trees may miss. Fit levels only on train. Store category levels as pandas Index objects so larger fixed vocabularies can be reused efficiently across row-wise preparation. The underlying category mapping remains unchanged. Source: feature-cross reasoning from Wide & Deep, adapted to native categorical trees.

Result: commit f943154, Eval AUC **0.7342**, **discard**. Run time: 31.8s (training 6.6s, eval 25.2s, ok).

## Experiment 12 — exploration

Hypothesis: high-cardinality route partitions overfit severely, reinforcing a variance-control direction. Test subsample=0.8 on the retained date model to decorrelate gradient estimates without adding features. Source: XGBoost tuning and forest tutorials. The failed route test also showed category Index reuse is efficient; revisit that independently if needed.

Result: commit fd28d69, Eval AUC **0.7479**, **discard**. Run time: 30.9s (training 4.6s, eval 26.2s, ok).

## Research refresh after unsuccessful categorical/regularization tests

Read [XGBoost maintainer RFC 12130](https://github.com/dmlc/xgboost/issues/12130), which proposes addressing selection bias from sorting categories and selecting splits using the same gradient statistics. This is a proposal, not an assumed installed feature. It motivates testing the existing one-hot split mode. Development documentation also changes the default in a future version; installed XGBoost remains 3.4.1 and no dependency changes are made.

## Experiment 13 — exploration

Hypothesis: native one-category-versus-rest splits reduce over-adaptive categorical partitioning. Set max_cat_to_onehot=1000, exceeding all current feature cardinalities. Keep feature set, depth, learning rate and rounds fixed so the effect of split strategy is isolated. Source: RFC above and stable categorical tutorial.

Result: commit f81b566, Eval AUC **0.7356**, **discard**. Run time: 29.2s (training 2.9s, eval 26.2s, ok).

## Experiment 14 — exploration

Hypothesis: one-hot splitting at the partition-tuned budget underfits (artifact 1.7 MB versus roughly 23 MB and faster training). Test a distinct one-hot capacity regime: 2,000 trees, depth 10, eta 0.05, min_child_weight 20. This is not a repetition of the failed partition depth test: isolating categories requires more decisions/rounds than grouping categories. If this also fails, abandon this representation for now. Sources: categorical tutorial and maintainer RFC.

Result: commit 8ab7c16, Eval AUC **0.7498**, **discard**. Run time: 38.6s (training 10.7s, eval 27.9s, ok).

## Experiment 15 — ablation/simplification

Hypothesis: FlightDate already determines month/day/weekday; remove those three input columns to simplify the model and reduce noisy competing splits. Retained-model gain inspection found no weekday splits, low gains for month/day, and dominant scheduled departure time/date effects. These are training diagnostics, not additional evaluation metrics. Larger one-hot trees improved that representation but remained below the partition model; abandon it for now.

Result: commit ad433dd, Eval AUC **0.7526**, **keep**. Run time: 23.6s (training 3.9s, eval 19.6s, ok).

## Experiment 16 — exploration

Hypothesis: separate scheduled hour and minute reveal within-hour schedule structure obscured by HHMM ordering and histogram binning. Retain original CRSDepTime and add two row-local numeric components. Sources: airline paper on HHMM transformation and scikit-learn time-feature engineering. No aggregate schedule volumes are used.

Result: commit a647682, Eval AUC **0.7518**, **discard**. Run time: 27.5s (training 5.1s, eval 22.4s, ok).

## Experiment 17 — exploration

Hypothesis: a training-only validation split can select a less overfit boosting horizon. Use 90% of train for fitting and 10% for early stopping, stratified with fixed seed 2026. Cap at 2,500 trees with patience 80 and AUC stopping; do not retrain on more data. The harness remains the sole experiment metric. Source: [official early-stopping guide](https://xgboost.readthedocs.io/en/stable/python/sklearn_estimator.html#early-stopping).

Result: commit b4a2ce2, Eval AUC **0.7499**, **discard**. Run time: 22.3s (training 2.8s, eval 19.5s, ok).

Early-stopping detail: experiment 17 selected 271 rounds; its harness score did not beat the retained model. No refit on additional data was performed.

## Experiment 18 — exploration

Hypothesis: nearby airports share regional conditions, but independent airport categories cannot express that proximity efficiently. Infer a three-dimensional airport embedding from training route distances: symmetrize median edge distances, fill missing pairs with shortest paths, then use classical multidimensional scaling. Add the origin and destination coordinates alongside the existing categories. No external airport dataset, outcomes, route volumes, or row-count features are used. Sources: [scikit-learn Isomap/MDS](https://scikit-learn.org/stable/modules/manifold.html) and [SciPy shortest paths](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.shortest_path.html). The embedding is an approximate learned geography, not asserted true coordinates. All fitting occurs once on train; prepare only looks up saved coordinates.

Result: commit 1685830, Eval AUC **0.7518**, **discard**. Run time: 35.6s (training 4.6s, eval 31.0s, ok).

Observation: Embedding lookups passed batch/single-row equivalence; 284 airports form a connected training graph. Added coordinates did not improve AUC and cost about 11 extra evaluation seconds.

## Experiment 19 — exploration

Hypothesis: target-adaptive airport partitions can crowd out lower-variance numeric geographic splits. Replace Origin/Dest category inputs with the six learned coordinates, retaining carrier/date categories and raw time/distance. This changes the airport representation rather than merely adding more columns. Motivation: geometry was a close miss and the maintainer RFC identifies categorical-vs-numeric split-selection bias. Reuse only the code from this run's experiment 18, never archived results.

Result: commit dc58fd7, Eval AUC **0.7561**, **keep**. Run time: 28.0s (training 4.0s, eval 24.0s, ok).

Observation: AUC gains 0.0035 while replacing nominal airport splits with numeric geography. This supports testing capacity specifically for the new representation; keep despite modest embedding code complexity.

## Experiment 20 — follow-up

Hypothesis: deeper trees now learn useful spatial/date interactions because airport identity uses ordered numeric coordinates rather than adaptive category partitions. Test depth 8 versus 6 with all other settings fixed. Distinct from experiment 7: airport representation has changed and its measured effect is +0.0035 AUC.

Result: commit 9cf889f, Eval AUC **0.7550**, **discard**. Run time: 29.9s (training 5.5s, eval 24.3s, ok).

## Synthesis after 20 experiments

Best: **0.7561**, **dc58fd7**. Date plus restrained partition-based boosting remains useful. Explicit routes, hour/minute components, subsampling, one-hot splits (even with higher capacity), and a training-only early-stop split all failed to improve the retained model. Removing redundant month/day/weekday inputs simplified and slightly improved it. Inferred airport geography initially did not help when added to airport categories, but replacing those categories produced a 0.0035 gain. This supports the theory that nominal airport splits can overfit and crowd out geographic sharing. Depth 8 still loses slightly with geography. Next test leaf regularization, geographic regions/date interactions, and potentially constrained interactions or ensemble averaging.

Research refresh: searched official sources on L2/leaf regularization, k-means clustering, and [feature interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html). K-means could give compact region groupings from the learned coordinates; constraints could prevent overly specific endpoint combinations. These are hypotheses for new experiments, not assumptions that they will help.

## Experiment 21 — follow-up

Hypothesis: regularize leaf predictions while preserving learned geography/date interactions. Set reg_lambda=20 versus default 1. Unlike raising minimum child weight or limiting depth, this shrinks accepted leaf updates without directly removing their splits. Source: XGBoost parameter reference.

Result: commit cb509ac, Eval AUC **0.7576**, **keep**. Run time: 27.9s (training 3.9s, eval 23.9s, ok).

## Experiment 22 — ablation/simplification

Hypothesis: the third embedding dimension captures graph distortion rather than useful geography. Retain the two leading eigen-directions only, removing two prepared columns and lookup calls. Source: MDS dimensionality tradeoff from scikit-learn documentation. The stronger L2 model gained 0.0015 AUC and is retained.

Result: commit c51fccb, Eval AUC **0.7579**, **keep**. Run time: 24.5s (training 3.7s, eval 20.7s, ok).

## Experiment 23 — follow-up

Hypothesis: stronger support requirements reduce noisy date partitions deep in geographic trees. Increase min_child_weight from 20 to 100, retaining L2=20 and depth=6. Distinct from L2 shrinkage: this rejects splits with low aggregate Hessian rather than merely shrinking their weights. Source: XGBoost parameter reference.

Result: commit c41d817, Eval AUC **0.7591**, **keep**. Run time: 24.4s (training 3.8s, eval 20.6s, ok).

## Experiment 24 — follow-up

Hypothesis: after leaf shrinkage and support constraints helped, a minimum gain of 5 can reject weak residual splits that fit noise late in boosting. Add gamma=5 with all other settings fixed. This controls split benefit, distinct from sample support and weight shrinkage. Source: XGBoost parameter reference.

Result: commit 2c25a2a, Eval AUC **0.7534**, **discard**. Run time: 22.8s (training 2.3s, eval 20.6s, ok).

## Experiment 25 — exploration

Hypothesis: k-means regions encode non-axis-aligned geographic groupings compactly. Fit 12 clusters on the two-dimensional airport coordinates (one observation per airport, no flight-count weighting). Add origin and destination region categories alongside coordinates. Source: [KMeans API](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html); use fixed seed and ten initializations. All region assignments are training-fitted lookups.

Result: commit a0b0d22, Eval AUC **0.7591**, **discard**. Run time: 32.6s (training 4.1s, eval 28.5s, ok).

## Experiment 26 — exploration

Hypothesis: regional day-specific disruptions need an explicit interaction even when region main effects add nothing. Add OriginRegionDate using the same 12 train-fitted geographic clusters, without the failed region main-effect columns. Category levels are fitted on train and stored as a reusable Index. Stronger child/L2 regularization distinguishes this from the much earlier failed raw-route cross. Sources: geographic grouping and categorical-cross research already read.

Result: commit bfd4afd, Eval AUC **0.7471**, **discard**. Run time: 34.1s (training 5.8s, eval 28.3s, ok).

Observation: The large loss reinforces avoiding high-cardinality categorical crosses. Compact numeric geography remains preferable.

## Experiment 27 — exploration

Hypothesis: averaging four sampled trees within each boosting round reduces variance while retaining geography/date signal. Set num_parallel_tree=4, subsample=0.8 and colsample_bynode=0.8. Keep 600 rounds and eta 0.05. This is boosted forest averaging, distinct from the earlier single-tree row-sampling test with nominal airports. Source: [official XGBoost forest tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html).

Result: commit 45209f9, Eval AUC **0.7617**, **keep**. Run time: 40.0s (training 18.3s, eval 21.7s, ok).

Observation: Averaging improves AUC by 0.0026 and trains in 18.3 seconds, comfortably below 60 seconds.

Additional research: read [XGBoost learning-to-rank](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html) and [Gao & Zhou, AUC pairwise optimization](https://www.ijcai.org/Proceedings/15/Papers/137.pdf). A later objective exploration could use uniformly sampled binary pairs and pairwise logistic loss, with the unchanged harness AUC. Ranking normalization and gradient scale must be handled deliberately; no ranking metric or query-specific evaluation will replace the harness.

## Experiment 28 — ablation/simplification

Hypothesis: some of experiment 27's improvement may come from column sampling rather than averaging. Remove num_parallel_tree=4, retaining the same row/node-column sampling. If AUC holds, keep the much smaller/faster model. Source: XGBoost forest tutorial and the measured result of experiment 27.

Result: commit 3ac54d3, Eval AUC **0.7610**, **discard**. Run time: 25.1s (training 4.3s, eval 20.7s, ok).

Observation: Sampling supplies much of the gain, but four-tree averaging adds 0.0007 AUC for one parameter and remains within the training limit.

## Experiment 29 — exploration

Hypothesis: relative departure time separates early/late services within a route, making schedule context easier to use than an absolute clock alone. Fit route median scheduled departure minutes on train, then look up and subtract it in prepare. This follows the allowed lookup example in program.md and the earlier time-feature research. It uses no targets, counts, or inference-batch statistics; unseen routes map to NaN.

Result: commit 9a1eda4, Eval AUC **0.7616**, **discard**. Run time: 44.6s (training 18.0s, eval 26.6s, ok).

## Experiment 30 — exploration

Hypothesis: pairwise logistic loss may improve discrimination by directly learning positive-negative ordering. Use XGBRanker rank:pairwise with a single global training group, mean pair sampling (one sampled pair per row), and both ranking normalizations disabled to preserve the plain pairwise loss. Retain the best feature set and tree/regularization settings. A small wrapper applies a fixed sigmoid to ranking scores to provide predict_proba; this is monotonic and does not aggregate inference rows. No evaluation or metric is changed: save_and_evaluate remains the final call. Sources: official learning-to-rank/parameter docs and Gao & Zhou AUC consistency paper read above. The theoretical connection motivates a test, not a finite-sample guarantee.

Result: commit 21c3810, Eval AUC **0.7587**, **discard**. Run time: 62.1s (training 40.5s, eval 21.6s, ok).

Observation: Pairwise objective trains within 60 seconds but scores below the logistic classifier; retain logistic loss. AUC-theory motivation did not translate into a finite-data gain under this configuration.

## Synthesis after 30 experiments

Best: **0.7617**, **45209f9**. Stronger L2 and minimum child weight helped geographic features; two embedding dimensions beat three while simplifying preparation. A hard split-gain penalty underfit. Region main effects were redundant and region-date categories overfit badly, as raw routes did earlier. Sampled boosting improved substantially; four-tree averaging added 0.0007 over sampling alone. Route-relative schedule time was a near miss. Pairwise ranking ran successfully but scored lower than logistic classification. Current theory: compact ordered airport geometry plus date effects benefits from soft regularization and model averaging; high-cardinality crosses are an unreliable way to add capacity.

Research refresh: read [XGBoost tree methods](https://xgboost.readthedocs.io/en/stable/treemethod.html) and [LightGBM best-first tree guidance](https://lightgbm.readthedocs.io/en/stable/Parameters-Tuning.html). Investigate XGBoost loss-guided growth with a small leaf budget, interaction constraints, and better distance embeddings. The LightGBM reference informs tree-growth reasoning only; models remain XGBoost and no package is installed.

## Experiment 31 — exploration

Hypothesis: loss-guided growth can spend a fixed number of leaves on useful spatial/date interactions instead of using a uniform depth cap. Use grow_policy=lossguide, max_depth=0, max_leaves=31. Retain strong leaf support/L2 constraints and four-tree sampled averaging. Sources: tree-method and leaf-wise tuning guides above.

Result: commit c4abe21, Eval AUC **0.7617**, **discard**. Run time: 41.6s (training 19.7s, eval 21.9s, ok).

Observation: Matched AUC with a somewhat smaller artifact, but added growth controls and slightly increased training time. Retain the clearer depth-limited configuration.

## Experiment 32 — exploration

Hypothesis: shortest-path completion overestimates distances between unobserved airport pairs, distorting the useful two-dimensional geometry. Starting from classical MDS, refine coordinates by minimizing relative distance stress on observed training routes only, with a weak anchor to the initial positions. This is unsupervised lookup fitting; labels and row counts are not features. Sources: [MDS stress formulation](https://scikit-learn.org/stable/modules/manifold.html#multi-dimensional-scaling-mds) and [SciPy L-BFGS-B](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-lbfgsb.html). Keep model settings unchanged. Added optimizer complexity must earn a meaningful AUC gain.

Result: commit a6a20c3, Eval AUC **0.7617**, **discard**. Run time: 39.1s (training 17.5s, eval 21.6s, ok).

Observation: Analytic gradient and row consistency checks passed, but optimizer added complexity without AUC gain. Retain classical MDS.

## Experiment 33 — exploration

Hypothesis: an additive origin-side plus destination-side structure captures local daily disruptions without memorizing full date-route combinations. Use two disjoint feature-interaction groups, duplicating shared time/carrier/date fields for the destination group. This is deliberate: [XGBoost interaction documentation](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html) explains that overlapping groups can reopen interactions, so disjoint aliases enforce the intended separation. Original group uses time/carrier/date/origin coordinates; destination group uses its aliases, distance and destination coordinates. Keep the rest of the model fixed.

Result: commit 17ad95d, Eval AUC **0.7612**, **discard**. Run time: 44.6s (training 19.7s, eval 24.8s, ok).

Observation: Inspected all fitted trees and verified each obeys a single disjoint feature group. Constraints reduce AUC by 0.0005; keep unconstrained trees.

## Plateau research after experiment 33

Three recent candidates were within 0.0005 of the retained score without improvement. Researched finer histogram resolution and rotation-sensitive decision trees. [XGBoost tree methods](https://xgboost.readthedocs.io/en/stable/treemethod.html) suggests higher max_bin can improve approximate split quality. [Rotation Forest](https://www.lucykuncheva.co.uk/papers/jrlkcatpami06.pdf) motivates testing alternate coordinate axes, adapted here as simple geographic sum/difference features rather than implementing its full ensemble algorithm.

## Experiment 34 — exploration

Hypothesis: 256 histogram bins merge useful scheduled-time and airport-coordinate thresholds, especially less common airports. Increase max_bin to 1024 to improve numeric split resolution while holding model capacity and features fixed. Source: XGBoost tree-method reference. This is a new numeric discretization test, not another depth/round tweak.

Result: commit 6b63ebf, Eval AUC **0.7618**, **keep**. Run time: 39.4s (training 17.8s, eval 21.6s, ok).

Observation: Small positive AUC change with no added feature complexity or material runtime cost.

## Experiment 35 — exploration

Hypothesis: add sums and differences of the two geographic coordinates so axis-aligned trees can express diagonal regional boundaries with fewer splits. Add the two projections for each endpoint, retaining the original coordinates. This is a fixed 45-degree basis augmentation, not a random rotation search. Motivation: Rotation Forest's observation that tree classifiers are sensitive to feature axes. Author PDF fetch timed out; indexed primary-paper excerpt and the [author's institutional record](https://research.bangor.ac.uk/en/publications/rotation-forest-a-new-classifier-ensemble-method/) were available. All projections remain row-local.

Result: commit 018f3a0, Eval AUC **0.7635**, **keep**. Run time: 45.5s (training 18.6s, eval 26.9s, ok).

Observation: Four additional numeric columns from two straightforward lines improve AUC by 0.0017; retain the diagonal geographic basis.

## Experiment 36 — follow-up

Hypothesis: a full category partition scan can improve date groupings now that averaging and stronger support/L2 penalties control variance. Set max_cat_threshold=512, above the 365 calendar-date levels. Distinct from experiment 10, which reduced the scan to 16 on a much less regularized nominal-airport model. Checked the [version-pinned implementation](https://raw.githubusercontent.com/dmlc/xgboost/v3.4.1/src/tree/hist/evaluate_splits.h): EnumeratePart caps scan length with min(max_cat_threshold, n_bins_feature). The unresolved issue 10844 contains a questioner's interpretation, so the source code is the basis for this hypothesis.

Result: commit f28748e, Eval AUC **0.7631**, **discard**. Run time: 47.1s (training 20.0s, eval 27.2s, ok).

## Experiment 37 — follow-up

Hypothesis: smaller updates help the now-averaged geographic model fit smoothly without changing approximate total boosting strength. Use 1,200 rounds at eta 0.025 instead of 600 at 0.05. Distinct from experiment 8 because the representation, regularization, and within-round averaging all changed. Measured 18.6-second training suggests the doubled rounds should fit the 60-second limit. Source: XGBoost tuning guide on shrinkage/round tradeoff.

Result: commit 49eae26, Eval AUC **0.7638**, **keep**. Run time: 65.1s (training 37.2s, eval 27.9s, ok).

Observation: AUC improves by 0.0003; training 37.2 seconds remains within the limit.

## Experiment 38 — exploration

Hypothesis: smooth annual sine/cosine features help geographic trees share seasonal patterns across dates, including year-end continuity. Retain the date category for daily disruptions and add two cyclic day-of-year features, using fixed non-leap-year offsets for 2005. Distinct from experiment 9's raw ordinal day because this representation is periodic and the model now has useful shared geographic features. Re-read the trigonometric section of [scikit-learn's time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) before implementing.

Result: commit e0392e7, Eval AUC **0.7635**, **discard**. Run time: 73.3s (training 38.2s, eval 35.0s, ok).

## Experiment 39 — exploration

Hypothesis: gradient-based importance sampling can focus computation on informative residuals and reduce sampling variance. Set sampling_method=gradient_based and subsample=0.5, keeping four-tree averaging and all other settings. Rechecked [official sampling documentation](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster), which supports this on CPU from version 3.2 with hist. Installed 3.4.1 satisfies that requirement. This is distinct from uniform subsampling.

Result: commit 9c46136, Eval AUC **0.7632**, **discard**. Run time: 79.6s (training 51.6s, eval 28.0s, ok).

Observation: No AUC gain and training rises to 51.6 seconds; retain uniform sampling.

## Experiment 40 — follow-up

Hypothesis: with the same 4,800-tree budget and approximate total boosting strength, eight-tree averaging over 600 rounds at eta 0.05 may reduce variance more effectively than four trees over 1,200 rounds at eta 0.025. Change those three coupled parameters together to compare allocation of the same compute/model budget. Source: XGBoost forest tutorial and experiments 27/28/37.

Result: commit ce60acd, Eval AUC **0.7640**, **keep**. Run time: 65.0s (training 37.0s, eval 28.0s, ok).

Observation: Eight-tree averaging yields 0.7640 at essentially the same runtime and model size as four-tree averaging over twice as many rounds.

## Synthesis after 40 experiments

Best: **0.7640**, **ce60acd**, versus baseline 0.7203. Finer numeric histograms helped slightly, while geographic sum/difference projections gave a meaningful 0.0017 gain with only two lines. Smaller boosting steps added a little; reallocating the same 4,800 trees to eight trees per round added another 0.0002. Broader category search, seasonal cycles, gradient-based sampling, loss-guided growth, refined MDS, and disjoint endpoint constraints did not improve the model. Current theory: simple numeric spatial transformations and averaging are effective; extra adaptive categorical interactions and elaborate fitting are less reliable.

Research refresh: searched official ordinal-encoding and monotonic-constraint references. Consider adding fixed airport identity order alongside geographic coordinates (less adaptive than categorical partitions), selective one-hot handling for the low-cardinality carrier, and continuous route geometry. Later investigate regularization/budget tradeoffs. Avoid cosmetic seed searches and full-training target encodings that would introduce self-target bias.

## Experiment 41 — exploration

Hypothesis: destination-minus-origin coordinate differences make route direction explicit. Trees otherwise need multiple thresholds to compare endpoint positions. Add two continuous route-vector components, retaining raw distance and endpoint coordinates. This shares directional patterns across routes and avoids the large categorical route vocabulary that previously overfit. Motivation: the successful geographic/diagonal features and MDS geometry research; this is an inference for this dataset, not an asserted external result.

Result: commit 8a99d53, Eval AUC **0.7633**, **discard**. Run time: 68.9s (training 37.9s, eval 30.9s, ok).

Observation: Direction differences lowered AUC relative to endpoint geometry alone; retain the simpler endpoint representation.

## Experiment 42 — exploration

Hypothesis: fixed alphabetical airport codes can recover airport-specific operational differences alongside smooth geography without adaptive categorical partitioning. Add one numeric code per endpoint, fitted on the training airport vocabulary, with unknown airports mapped to NaN. The arbitrary order is a restrictive representation, not a geographic assumption. Based on [OrdinalEncoder documentation](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.OrdinalEncoder.html), implementing the same fixed-code mapping with existing pandas lookups to keep per-row preparation lightweight.

Result: commit 0a79e59, Eval AUC **0.7633**, **discard**. Run time: 69.2s (training 37.8s, eval 31.3s, ok).

## Experiment 43 — exploration

Hypothesis: averaging independently boosted models reduces variance from entire boosting trajectories, beyond averaging trees within each round. Use two XGBoost models with four trees per round, 600 rounds, eta 0.05, and fixed seeds 42 and 2026. Average probabilities equally with sklearn VotingClassifier. This preserves the 4,800-tree total budget of experiment 40; seeds and weights are fixed before evaluating, with no seed selection. Both fit the same training set; no CV, additional metric, or extra data. Source: [official soft-voting documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html).

Result: commit 2b15c0c, Eval AUC **0.7637**, **discard**. Run time: 65.6s (training 37.3s, eval 28.3s, ok).

### Plateau research after experiment 43

Three close discards leave 0.7640 as best. Reviewed official [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) for selective one-hot categorical splits and weight regularization. Also read sklearn's [target-encoding cross-fitting example](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html); avoid naive full-training target encodings because of self-target leakage, and do not add cross-validation under this program.

## Experiment 44 — follow-up

Hypothesis: adaptive carrier partitions may overfit local geographic/date interactions. Set max_cat_to_onehot=32, so the 20 carrier levels use singleton splits while FlightDate retains partition splits. Different from experiments 13/14, which forced all categories into singleton splits and had a much less regularized feature/model foundation. The official threshold documentation supports selecting the lower-cardinality feature this way.

Result: commit ab6096e, Eval AUC **0.7597**, **discard**. Run time: 61.1s (training 33.2s, eval 28.0s, ok).

## Experiment 45 — follow-up

Hypothesis: the 0.0017 gain from diagonal geographic axes in experiment 35 indicates axis-aligned tree partitions benefit from alternative spatial orientations. Add the four intermediate projection directions at 22.5-degree spacing, retaining existing axes. This changes the available geographic boundary directions while adding no new data. The slopes sqrt(2)-1 and sqrt(2)+1 are fixed geometric choices, not searched angles. Motivated by the previously researched Rotation Forest paper and the observed projection gain.

Result: commit 599ccec, Eval AUC **0.7638**, **discard**. Run time: 83.1s (training 41.9s, eval 41.2s, ok).

Observation: Extra projections add evaluation cost and do not improve AUC. Training split-gain diagnostics on retained ce60acd rank FlightDate, departure time, and carrier highest; these are not additional evaluation metrics.

## Experiment 46 — follow-up

Hypothesis: stronger L2 shrinkage suppresses noisy conditional date/carrier leaf effects while retaining the useful geographic partitions. Increase reg_lambda from 20 to 100; this is a meaningful regularization step relative to min_child_weight=100, rather than a tiny parameter nudge. Experiment 21 improved from lambda 1 to 20 before forest averaging was introduced. Source: [XGBoost tree-booster regularization documentation](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster).

Result: commit 401c67e, Eval AUC **0.7632**, **discard**. Run time: 64.8s (training 36.7s, eval 28.1s, ok).

## Experiment 47 — ablation/simplification

Hypothesis: depth-five trees may remove unreliable high-order date/carrier/geography interactions while retaining the main effects. Reduce max_depth from 6 to 5 at the same 600 rounds and eight trees per round. Earlier depth-eight trials hurt, and lambda 100 just hurt, so this tests simpler interaction structure rather than stronger leaf shrinkage. Based on the previously read [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html). Equal AUC would favor the smaller trees.

Result: commit f385c1a, Eval AUC **0.7621**, **discard**. Run time: 58.4s (training 31.0s, eval 27.4s, ok).

## Experiment 48 — exploration

Hypothesis: periodic departure-clock features make after-midnight flights adjacent to late-night flights and may improve shared delay patterns at the day boundary. Add sine/cosine of minute-of-day while retaining raw CRSDepTime. This differs from the rejected separate hour/minute and annual-season encodings. Every feature is a deterministic function of the row. Source: [scikit-learn cyclical feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html).

Result: commit 9071072, Eval AUC **0.7639**, **discard**. Run time: 70.8s (training 37.7s, eval 33.1s, ok).

## Experiment 49 — ablation/simplification

Hypothesis: row sampling plus eight-tree averaging may provide enough diversity without omitting strong predictors at individual nodes. Remove colsample_bynode=0.8 so all features are eligible. Training split-gain diagnostics on the retained model show FlightDate, CRSDepTime, and carrier dominate; feature sampling sometimes suppresses them. This isolates column sampling, unlike experiment 28, which removed within-round averaging while keeping sampling. Source: [XGBoost forest tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html), which discusses row and column sampling.

Result: commit d8db291, Eval AUC **0.7620**, **discard**. Run time: 65.5s (training 37.4s, eval 28.1s, ok).

Observation: All-feature splits produce a larger artifact and lower AUC; retain per-node column sampling.

## Experiment 50 — exploration

Hypothesis: first fitting broad main effects and low-order interactions with shallow trees may reduce the pressure for noisy high-order categorical interactions in subsequent trees. Fit 200 depth-two rounds, then continue the same booster with the retained 600 depth-six rounds; all other settings remain fixed. This trains on the same data throughout and saves one combined booster, with no extra evaluation or model averaging. Expected training cost stays below 60 seconds. Source: official [XGBoost continuation example](https://xgboost.readthedocs.io/en/latest/python/examples/continuation.html); the depth schedule itself is a hypothesis for this dataset.

Result: commit ec5a136, Eval AUC **0.7632**, **discard**. Run time: 71.1s (training 42.9s, eval 28.2s, ok).

## Synthesis after 50 experiments

Best remains **0.7640**, **ce60acd**. None of experiments 41–50 improved it. Removing column sampling or reducing depth clearly hurt; carrier singleton splits were particularly damaging. Stronger L2 and shallow warm-up also hurt. Clock cycles, more spatial angles, and independent-model averaging came close but added no gain worth retaining. This supports the current balance of grouped date/carrier splits, depth-six interactions, modest L2, geographic coordinates, and within-round averaging. Avoid adding complexity merely because an idea sounds plausible.

Research refresh: searched official spectral-embedding documentation, XGBoost continuation, L1 regularization, and learning-rate schedules. Next compare local-neighborhood airport geometry, stronger averaging at matched tree budget, and targeted regularization or support changes. These test representation, variance, and interaction support rather than arbitrary nearby parameter values.

## Experiment 51 — exploration

Hypothesis: local airport neighborhoods expose nonlinear regional boundaries that global distance-preserving coordinates can miss. Add four spectral coordinates from a 16-nearest-neighbor graph built on the existing train-only shortest-path distances. Four dimensions allow separate broad geographic components plus local variation; the neighborhood size is fixed, not selected by a sweep. Existing MDS coordinates remain. No label, row-frequency, or external-data information is used in the embedding. Source: [scikit-learn SpectralEmbedding documentation](https://scikit-learn.org/stable/modules/generated/sklearn.manifold.SpectralEmbedding.html), specifically precomputed nearest-neighbor affinities and Laplacian eigenmaps.

Result: commit c987e43, Eval AUC **0.7642**, **keep**. Run time: 82.7s (training 41.3s, eval 41.4s, ok).

Observation: Small gain with an eight-line standard-library-method addition, retained for a direct simplification test next; do not treat 0.0002 as established statistical improvement.

## Experiment 52 — ablation/simplification

Hypothesis: spectral geometry alone may supply the useful airport structure, making the explicit MDS eigendecomposition redundant. Replace the combined global/local representation with four spectral axes and diagonal projections of its last two axes. This removes the custom centering/eigendecomposition code and reduces geographic feature count from sixteen to twelve. Same 16-neighbor affinity, training data, and model settings. Equal AUC favors this simplification. Source: the spectral-embedding documentation and experiment 51.

Result: commit f7a3f3e, Eval AUC **0.7635**, **discard**. Run time: 73.2s (training 37.9s, eval 35.3s, ok).

## Experiment 53 — exploration

Hypothesis: independently estimated airport/date delay means may recover operational and daily effects without adaptive high-cardinality partitions. Reserve a fixed random 20% of train.csv exclusively for fitting the three mean lookups (Origin, Dest, FlightDate); train XGBoost on the disjoint remaining 80%. The unsupervised airport geometry still uses train.csv only. Existing features remain. This is one training-design split, not cross-validation or an additional evaluation; no model training row contributes its own target to a lookup. Unknown categories map to NaN. These are mean-target features, not row-count/frequency features.

Source: section 3.2 of [CatBoost: unbiased boosting with categorical features](https://papers.neurips.cc/paper_files/paper/2018/file/14491b756b3a51daac41c24863285549-Paper.pdf) describes independent training partitions for target statistics and the cost in data efficiency. Its term “holdout TS” refers here solely to a subset of train.csv; no held-out repository data is accessed. This resolves the leakage concern noted after experiment 43 without adding prohibited cross-validation.

Result: commit 3254722, Eval AUC **0.7606**, **discard**. Run time: 95.9s (training 49.2s, eval 46.8s, ok).

Observation: Batch/single-row feature parity passed on 12 training rows. AUC loss suggests the target means do not compensate for the loss of booster training data; discard the whole split-encoding design.

## Experiment 54 — follow-up

Hypothesis: more within-round averaging may further reduce split variance now that geographic features offer several competing representations. Compare 16 trees per round for 300 rounds at eta 0.1 with the current 8 trees for 600 rounds at eta 0.05. Total tree count remains 4,800 and approximate total boosting strength is matched. Experiment 40 favored moving from four to eight trees per round at matched budget; this is one further test of that evidence-based allocation hypothesis. Source: [XGBoost forest tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html).

Result: commit e770ebd, Eval AUC **0.7643**, **keep**. Run time: 83.1s (training 41.8s, eval 41.3s, ok).

Observation: Tiny AUC gain at almost identical runtime and model size, with no additional code complexity. Unsupervised inspection of the four spectral coordinate extremes confirms distinct regional orderings; no evaluation rows or extra performance metrics were used.

## Experiment 55 — follow-up

Hypothesis: sixteen-tree averaging may now support finer geographic/date interactions with less variance than the earlier single-tree models. Reduce min_child_weight from 100 to 50 while keeping the strong averaging and other regularization. This relaxes the minimum Hessian support substantially, allowing narrower regional events; experiment 23's support gain occurred before averaging and spectral geometry. Source: [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster).

Result: commit fe1b7ec, Eval AUC **0.7647**, **keep**. Run time: 83.1s (training 41.9s, eval 41.2s, ok).

## Experiment 56 — exploration

Hypothesis: an airport's typical route length describes its operating network and may distinguish nearby airports that geometry alone treats similarly. Add the median observed route distance for each origin/destination airport, using the already fitted unique-route distance table so repeated flights do not act as frequency weights. Fit lookups only on train; preserve all rows for XGBoost training. This follows the allowed fitted-group-statistic approach in program.md and the previously researched airline feature-engineering work, but the airport-network interpretation is a hypothesis for this dataset. No target or count features are used.

Result: commit 5eedfb5, Eval AUC **0.7646**, **discard**. Run time: 87.7s (training 43.2s, eval 44.5s, ok).

## Experiment 57 — follow-up

Hypothesis: after relaxing minimum leaf support, L1 regularization can suppress weak residual leaf updates while preserving larger regional effects. Add reg_alpha=10, keeping the successful minimum support of 50, lambda 20, and sixteen-tree averaging. This is weight shrinkage rather than the rejected gamma-based split pruning, and does not add feature complexity. Source: [XGBoost L1 regularization documentation](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster), reviewed during the synthesis after experiment 50.

Result: commit b4d75f0, Eval AUC **0.7615**, **discard**. Run time: 75.5s (training 34.9s, eval 40.7s, ok).

Observation: The artifact shrank from 91.9 MB to 41.3 MB, but the 0.0032 AUC loss is too large for that simplicity/runtime benefit.

## Experiment 58 — follow-up

Hypothesis: after adding local geometry and relaxing minimum leaf support, the best model may benefit from more boosting steps. Increase rounds from 300 to 400 at eta 0.1 and sixteen trees per round, extending both total boosting strength and tree budget by one third. This tests added capacity, unlike the matched-budget averaging comparisons. The measured 41.9-second training time projects to roughly 56 seconds, leaving a modest margin within the 60-second cap. Source: XGBoost tuning guidance on balancing learning rate and boosting rounds.

Result: commit 461f747, Eval AUC **0.7641**, **discard**. Run time: 98.4s (training 56.4s, eval 42.0s, ok).

Observation: Training reached 56.4 seconds but AUC declined; additional boosting capacity is not beneficial at the current settings.

## Experiment 59 — follow-up

Hypothesis: weekday may help the spatial model share recurring regional travel patterns across otherwise unrelated flight dates. Restore DayOfWeek as a categorical input while retaining FlightDate, without restoring Month or DayofMonth. Experiment 15 removed all three together before geographic features and forest averaging; this isolates the potentially useful weekly grouping on the mature model. Motivation: the calendar features in the previously read [airline-delay study](https://arxiv.org/html/2408.02802v1) and current geographic interactions.

Result: commit 0cf64a1, Eval AUC **0.7648**, **keep**. Run time: 86.3s (training 42.8s, eval 43.6s, ok).

## Experiment 60 — ablation/simplification

Hypothesis: after stronger averaging, smaller leaves, and weekday restoration, the modest spectral gain may be redundant. Remove the spectral embedding and its eight prepared columns, retaining global MDS coordinates and their diagonal projections. This removes eight lines, an import, and substantial row-by-row preparation cost. Rechecking the component after several retained changes is useful because experiment 51's original gain was only 0.0002. A result within 0.0001 of the current best is acceptable for this substantial simplification.

Result: commit 30ace33, Eval AUC **0.7640**, **discard**. Run time: 70.1s (training 39.3s, eval 30.9s, ok).

## Synthesis after 60 experiments

Best: **0.7648**, **0cf64a1**, versus baseline 0.7203. Stronger within-round averaging and smaller leaves work together; weekday restoration added a small gain. Combining global and local geographic representations remains useful: removing local coordinates now costs 0.0008, and removing global coordinates also hurt. Independent-partition target means, typical airport route distance, strong L1 shrinkage, and more boosting rounds did not improve results. The model still fits comfortably below the training cap at about 43 seconds.

Research refresh: read the official [weighted-column-sampling example](https://xgboost.readthedocs.io/en/latest/python/examples/feature_weights.html), refreshed [histogram resolution guidance](https://xgboost.readthedocs.io/en/stable/parameter.html), and inspected the [version-pinned learning-rate callback](https://raw.githubusercontent.com/dmlc/xgboost/v3.4.1/python-package/xgboost/callback.py). Confirmed locally that installed XGBModel accepts feature_weights in its constructor. Next directions: sampling balance between feature families, learning-rate schedules at matched total strength, and remaining simple ablations.

## Experiment 61 — exploration

Hypothesis: sixteen correlated airport-coordinate columns can crowd out the five basic flight/calendar fields under uniform feature sampling. Give geographic columns weight 0.5 and other columns weight 1.0, keeping colsample_bynode=0.8. This retains random spatial subsets, unlike experiment 49's removal of column sampling, while making the core fields more consistently available. Source: the official weighted-column-sampling example cited in the synthesis. Weights depend only on feature family, not labels or evaluation results.

Result: commit e175e6b, Eval AUC **0.7638**, **discard**. Run time: 87.9s (training 44.3s, eval 43.6s, ok).

## Experiment 62 — exploration

Hypothesis: larger initial updates followed by smaller residual updates can learn broad patterns quickly and limit late noise fitting. Replace the fixed 0.1 learning rate with 300 linearly spaced rates from 0.16 to 0.04. Their sum is exactly 30, matching the current total learning-rate sum; tree count and all other settings remain unchanged. The version-pinned [LearningRateScheduler source](https://raw.githubusercontent.com/dmlc/xgboost/v3.4.1/python-package/xgboost/callback.py) confirms it runs after each iteration, so initialize with the first rate and provide the shifted list to apply the intended schedule exactly.

Result: commit 4ba0799, Eval AUC **0.7649**, **keep**. Run time: 87.5s (training 43.8s, eval 43.7s, ok).

Observation: Tiny gain with a standard callback and a slightly smaller artifact; retain for further ablations without interpreting the difference as statistical certainty.

## Experiment 63 — ablation/simplification

Hypothesis: with sixteen-tree averaging and per-node column sampling, using every training row in each tree may reduce sampling noise in narrow regional/date effects. Remove subsample=0.8, retaining column randomness. This isolates row sampling, unlike experiment 49's column-sampling ablation; the forest remains randomized by feature selection. Source: [XGBoost forest tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html).

Result: commit 3b22ae5, Eval AUC **0.7632**, **discard**. Run time: 79.4s (training 35.9s, eval 43.5s, ok).

Observation: Training is faster and the artifact smaller, but AUC falls by 0.0017; row subsampling remains useful.

## Experiment 64 — follow-up

Hypothesis: the now strongly averaged model may benefit from one additional interaction level to describe localized date/carrier/geography effects. Increase depth from six to seven, keeping 300 scheduled-rate rounds and sixteen trees per round. Earlier depth-eight trials preceded the strong averaging, L2 regularization, and local geometry; smaller leaves recently helped in experiment 55. Expected training time is near the limit but below 60 seconds based on earlier depth scaling. Source: XGBoost guidance on tree complexity and variance control.

Result: commit c944125, Eval AUC **0.7650**, **keep**. Run time: 94.6s (training 50.5s, eval 44.2s, ok).

Observation: A small gain with one parameter change; training rises to 50.5 seconds and artifact size to 137.9 MB, both within the experiment limits.

## Experiment 65 — follow-up

Hypothesis: rare departure-time and distance boundaries may still be merged by histogram quantization. Increase max_bin from 1024 to 2048, above the observed training cardinalities of CRSDepTime (1162) and Distance (1267); airport coordinates have at most 284 values. This targets the remaining numeric resolution limit rather than an arbitrary small bin-count adjustment. No counts are supplied as model features. Source: [XGBoost max_bin documentation](https://xgboost.readthedocs.io/en/stable/parameter.html), refreshed after experiment 60.

Result: commit a8dea74, Eval AUC **0.7651**, **keep**. Run time: 94.7s (training 50.5s, eval 44.2s, ok).

## Experiment 66 — exploration

Hypothesis: categorical departure-hour splits can group nonadjacent hours with similar conditional delay patterns, while the raw clock retains minute-level resolution. Add one fixed-vocabulary 24-hour categorical feature. This differs from experiment 16's numeric hour/minute fields and experiment 48's trigonometric clock features. Unknown/missing clock values remain missing and the category vocabulary is fixed independently of the input batch. Sources: previously reviewed XGBoost categorical partitioning documentation and airline time-feature research.

Result: commit b4347d2, Eval AUC **0.7628**, **discard**. Run time: 103.9s (training 56.0s, eval 47.8s, ok).

## Experiment 67 — follow-up

Hypothesis: the consistent small gains from reallocating four to eight to sixteen trees per round may extend to thirty-two trees. Use 150 rounds with 32 trees each and a decreasing learning-rate schedule from 0.32 to 0.08. Total tree count stays 4,800 and total rate sum stays 30; this compares stronger averaging with fewer, larger updates under the current depth-seven model. This is the final planned matched-budget averaging comparison, motivated by experiments 40 and 54 and the XGBoost forest documentation.

Result: commit bee1f30, Eval AUC **0.7649**, **discard**. Run time: 94.4s (training 50.1s, eval 44.4s, ok).

## Experiment 68 — ablation/simplification

Hypothesis: caching categorical vocabularies as pandas Index objects avoids reconstructing the same category metadata for every evaluated row, preserving all feature values and the fitted model. Wrap the already fitted sorted vocabularies in pd.Index once at module scope. The earlier route experiment also tried reusable category indices, but its new route feature confounded that change; this is the isolated preparation-speed comparison. Source: previously reviewed [pandas Categorical documentation](https://pandas.pydata.org/docs/reference/api/pandas.Categorical.html). Exact AUC equality and reduced repeated preparation work favor retaining this small cleanup. Started before the clock deadline; no additional experiment will start once time is up.

Not run: prepared commit **a7bdbc9**, but the harness refused to start because the two-hour clock had expired. No training or evaluation occurred and no metric exists, so this unrun proposal is not a row in results.tsv. The hypothesis above was written while preparing the attempt; its expectation of starting before the deadline was not met. Revert this unevaluated cleanup to the best evaluated commit.

## Final summary

The two-hour experiment clock is exhausted. **67 experiments completed**, all with successful harness evaluations; one additional preparation-only cleanup was refused at launch after the deadline and was reverted. Results contain 23 kept rows, 44 discarded rows, and 0 crashes.

Best retained Eval AUC: **0.7651**, commit **a8dea74**, branch **oct2**. Baseline: **0.7203**, commit 92e43e6. Absolute improvement: **0.0448**. The retained run took **50.5 seconds for training** and **44.2 seconds for evaluation**, within their separate limits. Its saved artifact is artifacts/a8dea7406c3042a7bb41f1cc597fa8729488ed0e.pkl.

The retained model combines FlightDate and weekday/carrier categories with raw scheduled departure time and distance; global MDS and local spectral airport coordinates fitted solely from training route distances; diagonal global geographic projections; and a depth-seven XGBoost classifier with minimum child weight 50, lambda 20, 2048 bins, row/column sampling, and sixteen trees per round. Its 300-round learning-rate schedule decreases from 0.16 to 0.04, yielding 4,800 trees and a total rate sum of 30.

What worked: useful date identity, train-only geographic sharing instead of high-cardinality airport categories, diagonal projections, moderate regularization, averaging, relaxed leaf support after averaging, and a few small gains from weekday, learning-rate scheduling, depth, and numeric resolution. The final ablations continued to support both global/local geometry and both row/column sampling. Small late AUC differences should be understood as observed evaluation differences, not established statistical improvements.

What did not work: raw route categories, naive extra category crosses, broad one-hot replacement, several calendar/clock encodings, independent probability ensembles at the same tree budget, overly strong L1/L2 or split pruning, a shallow warm-up, more boosting rounds, and independent-partition target means that reduced booster training data. Thirty-two-tree averaging did not beat sixteen trees.

Next: first isolate category-index caching as a preparation-speed improvement in a fresh run. Then ablate individual spectral coordinates and compare simpler local-neighborhood representations; these may preserve the geographic gain with fewer prepared features. No further experiments were started after the harness reported TIME IS UP. The setup-time file-read deviation is documented near the start of this log.

Final audit: every completed experiment has exactly one results row; the branch points to the best kept commit; train.py is committed and is the only changed tracked file relative to the starting commit; its final evaluation call is intact; the best artifact exists. Results and research log remain uncommitted as requested.
