# Research log

## Setup — 2026-10-02

- Run branch: `oct2`, created directly from the current HEAD.
- Starting commit: `92e43e6`.
- Read `program.md`, `README-autoresearch.md`, `train.py`, and `harness.py`.
- Confirmed that `data/train.csv` and `data/eval.csv` exist and are nonempty; no data contents inspected during setup.
- Verified imports of pandas, NumPy, XGBoost, scikit-learn, cloudpickle, and the harness.
- Baseline: unchanged `train.py`, with 30 trees, maximum depth 6, learning rate 0.1, native categorical features, and random seed 42.
- Budget after confirmation: 2 hours total, with 60 seconds for training and 300 seconds for evaluation per experiment.
- Experiment clock has not started. The first run will establish the baseline; web research is required before the first non-baseline experiment.

## Experiments

No experiments run yet.

### 01 — Baseline — `92e43e6` — keep

Unchanged starter: Eval AUC **0.7203**, training 0.2s, evaluation 31.2s. Training data has 200,000 rows, balanced labels, eight features, and no missing values. Only training data was inspected.

### Initial research

- [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html): balance tree complexity against regularization; smaller learning rates need more rounds; subsampling can reduce variance.
- [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html): investigate depth 4–8, learning rates 0.03–0.1, child weights 1–40, row subsampling 0.7–1, and categorical split thresholds. These are experiment ranges chosen for this dataset, not universal recommendations.
- [XGBoost categorical handling](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html): categorical partitions can group airports/carriers; control their flexibility separately from tree depth.
- [Scikit-learn time feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html): compare ordinal calendar/time features and periodic encodings.
- [BTS departure statistics](https://www.transtats.bts.gov/ontime/Departures.aspx): scheduled times use local 24-hour clocks. Derive hour/minute features from HHMM within prepare.

### 02 — More boosting rounds

Classification: follow-up to the baseline. Hypothesis: 30 trees underfit; 300 at the same depth and learning rate can learn residual route/calendar effects. Change only n_estimators. Source: XGBoost tuning guidance above.

Result: `417d86a`, Eval AUC **0.7342** (+0.0139), training 1.9s, evaluation 30.6s. Keep: the starter was substantially underfit.

### 03 — Simplify categorical preparation

Classification: ablation/simplification of the current best. Fixed pandas categories already convert unseen values to missing, so removing redundant isin/where preserves semantics and should reduce per-row evaluation overhead. No modeling change.

Result: `5ab6349`, Eval AUC **0.7342**, training 1.7s, evaluation 20.7s (down from 30.6s). Keep as a simplification. Current pandas maps unknown categories to missing but emits a future-version warning; no dependency changes are planned. [Pandas categorical API](https://pandas.pydata.org/docs/reference/api/pandas.Categorical.html).

### 04 — Calendar-date category

Classification: exploration. Hypothesis: combining month and day gives trees direct access to particular-day conditions and holiday effects that require multiple splits with separate calendar fields. Add a Date category with levels fitted only on train. Source: scikit-learn time feature engineering and XGBoost categorical partitioning docs linked above. Features remain row-local.

Result: `2ec49f1`, Eval AUC **0.7503**, keep. Training 1.9s, evaluation 26.4s. Gain +0.0161; date identity exposes useful effects beyond separate month/day categories.

### 05 — Regularize small leaves

Classification: follow-up. Increase min_child_weight from 1 to 20 to reduce variance in sparse date/airport interactions while retaining all features. Source: XGBoost parameter documentation (minimum child Hessian).

Result: `18e3edb`, Eval AUC **0.7507**, keep. Training 1.9s, evaluation 26.4s. Small +0.0004 gain for one parameter; keep.

### 06 — Deeper interactions

Classification: follow-up. Increase max_depth from 6 to 8 while retaining min_child_weight 20, testing whether richer date/airport/carrier/time interactions outweigh added variance. Source: XGBoost depth/complexity documentation.

Result: `a11cbdb`, Eval AUC **0.7465**, discard. Eval AUC fell by 0.0042; richer trees overfit at this boosting budget. Training 2.9s, eval 27.3s. Revert to depth 6.

### 07 — Remove redundant calendar inputs

Classification: ablation/simplification. Date is a deterministic combination of month/day and determines weekday within this dataset year. In the best model, train-based gain importance for DayOfWeek is zero, Month 0.002, DayofMonth 0.009. Remove the three separate calendar fields, retaining Date; test whether performance survives with fewer columns and faster prepare.

Additional research: [Systemic delay propagation](https://www.nature.com/articles/srep01159) motivates route/carrier/schedule interactions without importing any external data. [CatBoost paper](https://arxiv.org/abs/1706.09516) highlights target-statistic leakage: avoid naïve in-sample target-mean features and preserve row-local transforms.

Result: `13794b1`, Eval AUC **0.7505**, keep. Eval AUC -0.0002, treated as about equal for a substantial simplification: six features instead of nine; evaluation 19.7s instead of 26.4s. Keep under the simplicity rule.

### 08 — Shallower trees

Classification: follow-up. Depth 8 hurt by 0.0042; test depth 4 against the simplified depth-6 model with the same 300 rounds and child-weight constraint. This explicitly tests the lower-variance direction rather than a nearby arbitrary depth.

Result: `57c1201`, Eval AUC **0.7529**, keep. AUC +0.0024 over the simpler depth-6 model; evaluation 19.3s. Shallower interactions generalize better than depth 6 or 8 so far.

### 09 — Smaller boosting steps

Classification: follow-up. Halve learning_rate to 0.05 and double rounds to 600, preserving nominal cumulative shrinkage while allowing finer corrective steps. Unlike experiment 02 this tests learning-rate granularity rather than increasing the boosting budget. Source: XGBoost tuning guidance.

Result: `40f4253`, Eval AUC **0.7538**, keep. AUC +0.0009; evaluation 19.6s. Smaller steps improve the shallow model.

### 10 — Carrier-origin interaction

Classification: exploration. Add one categorical interaction for carrier and origin (1,551 observed combinations), allowing airline-at-airport effects without consuming two tree levels. Levels are fitted on train only. Source: systemic delay propagation paper; this interaction is an inference motivated by network/schedule dependence, not a claim directly evaluated in the paper.

Result: `4dfc0ce`, Eval AUC **0.7458**, discard. AUC -0.0080; evaluation 26.6s. The 1,551-level interaction introduces considerable variance despite leaf-weight regularization. Drop it.

### Synthesis after 10 experiments

Best kept model: `40f4253`, AUC **0.7538** (baseline 0.7203). Calendar date is the largest feature improvement; shallower trees and smaller boosting steps help. Removing redundant calendar columns preserved performance and sped up evaluation. Depth 8 and the sparse carrier-origin category hurt. Current theory: time of departure and date carry broad signal, while aggressive category grouping learns noisy fine-grained effects. Next: control categorical split flexibility, then add row-local time representations or train-fitted schedule summaries.

Research refresh: [Gradient boosting regularization](https://scikit-learn.org/stable/auto_examples/ensemble/plot_gradient_boosting_regularization.html) motivates testing row subsampling with shrinkage. [XGBoost stable parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) document max_cat_threshold and one-hot controls; use stable behavior compatible with installed 3.4.1, not development-version defaults. [Airline-delay feature engineering project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) suggests schedule/rotation structure, but external weather, traffic counts, and actual-flight observations are unavailable or forbidden here.

### 11 — Restrict categorical partitions

Classification: follow-up. Set max_cat_threshold=16 (versus default 64) to reduce overfitting in date/airport partitions. This targets categorical split flexibility separately from tree depth; source: XGBoost stable parameters.

Result: `f1c0483`, Eval AUC **0.7463**, discard. AUC -0.0075. Restricting categorical partitions globally underfits important date/airport groupings; this differs from sparse interaction-category overfitting.

### 12 — Broader categorical partitions

Classification: follow-up. Test max_cat_threshold=256 against default 64, allowing partitions over larger portions of the 365 dates and 283 airports. The strong failure at 16 motivates the opposite flexibility direction; no sparse interaction feature is included.

Result: `684fa10`, Eval AUC **0.7556**, keep. AUC +0.0018. Broad partitions help date and airport features; sparse cross-categories were the problematic source of variance.

### 13 — Departure minute within hour

Classification: exploration. Add CRSDepTime % 100 as DepMinute, preserving original HHMM. Hypothesis: minute-of-hour reflects scheduling conventions across hours; a tree on raw HHMM cannot express repeated minute patterns efficiently. Sources: BTS clock format and scikit-learn time feature engineering. Computed solely from each row.

Result: `3769a89`, Eval AUC **0.7547**, discard. AUC -0.0009; evaluation 21.1s. Schedule-minute detail did not generalize with this model.

### 14 — Ordered calendar coordinate

Classification: exploration. Retain categorical Date and add month*32+day as a numeric ordering. Trees can now select contiguous calendar intervals as well as categorical date groups. The numeric gaps between months do not affect tree threshold ordering. Source: scikit-learn time-related feature engineering.

Result: `0b3b7c8`, Eval AUC **0.7556**, discard. AUC unchanged at four-decimal reporting precision; extra feature/code and evaluation overhead are not justified. Evaluation 23.5s.

### 15 — Stochastic boosting

Classification: exploration. Set subsample=0.8, keeping the current 600 rounds and learning rate 0.05. Hypothesis: training each tree on a different subset reduces variance in categorical splits. Source: scikit-learn gradient boosting regularization example.

Result: `63ea704`, Eval AUC **0.7533**, discard. AUC -0.0023. Random row removal adds noise rather than improving these categorical partitions. Three discarded directions prompted research into a different representation.

### 16 — Airport distance embedding

Classification: exploration. Fit an undirected graph from training-only median route distances, compute shortest-path distances, and use classical multidimensional scaling to produce three airport coordinates. Add each coordinate for origin and destination. Hypothesis: smooth geographic/network coordinates share statistical strength across airports. No labels or row-count features are used. Sources: [Isomap rationale](https://arxiv.org/abs/2006.10858), [SciPy shortest_path](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.shortest_path.html), and delay-propagation research. This is an adaptation to the observed route network, not a claim that the embedding is exact geography. All lookup fitting is at module level; prepare only maps one row's airport identifiers.

Result: `b91302e`, Eval AUC **0.7556**, discard. AUC unchanged; 27 extra lines and evaluation 30.0s are not worthwhile. Saved-artifact prepare passed exact batch-versus-single-row equality on 12 training rows, including an intentionally unseen airport. No counts or targets used in embedding.

### 17 — Training-only early stopping

Classification: exploration. Split 10% of train for stratified early stopping, allow up to 4,000 trees, and stop after 100 rounds without internal AUC improvement. Fit once on the remaining 90%; no cross-validation or refit. The only experiment score remains harness Eval AUC. Source: [XGBoost sklearn early stopping](https://xgboost.readthedocs.io/en/stable/python/sklearn_estimator.html). Hypothesis: a validation-selected boosting length can improve on 600 fixed rounds despite reserving training rows.

Result: `ec594d2`, Eval AUC **0.7533**, discard. Selected 715 trees, training 3.4s, AUC 0.7533. Reserving 20,000 training rows cost more than adaptive stopping gained. No refit or cross-validation was performed.

### 18 — Stronger leaf shrinkage

Classification: follow-up. Return to the full-data best and set reg_lambda=30 rather than default 1. Hypothesis: regularizing leaf predictions reduces variance without losing data or suppressing broad category partitions. Motivated by the depth and early-stopping results. Source: [XGBoost boosted-tree regularization](https://xgboost.readthedocs.io/en/stable/tutorials/model.html).

Result: `185c83d`, Eval AUC **0.7551**, discard. AUC -0.0005; the current model does not benefit from this stronger uniform leaf penalty.

### 19 — Route-relative schedule

Classification: exploration. Fit median scheduled departure minute for each origin-destination route on train only. Inside prepare add the mapped median and this row's minute offset from it. No row counts or labels enter the lookup. Hypothesis: route-specific schedule position provides context not captured easily by shallow trees on airport IDs. Sources: the program's approved route-median example, [pandas grouped medians](https://pandas.pydata.org/docs/reference/api/pandas.core.groupby.SeriesGroupBy.median.html), and the Berkeley airline scheduling feature study.

Result: `28143c8`, Eval AUC **0.7529**, discard. AUC -0.0027; evaluation 25.5s. The train-fitted schedule summaries did not help. Documentation URL correction: https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.api.typing.SeriesGroupBy.median.html (old pandas API path returned 404); Berkeley page was available via search excerpt but direct fetch returned 403.

### 20 — Pairwise ranking objective

Classification: exploration. Use XGBRanker rank:pairwise with all training rows in one query, mean pair sampling (one pair per sample), and normalization disabled. AUC is a positive-versus-negative ordering probability, so pairwise logistic loss is an aligned surrogate (inference, not guaranteed improvement). Use 400 rounds at 0.075 for similar nominal shrinkage within the training limit. A small predict_proba adapter applies a monotone sigmoid to ranking scores; the harness and its metric are unchanged. Source: [XGBoost learning to rank](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html).

Result: `33efee6`, Eval AUC **0.7210**, discard. AUC 0.7210, training 17.0s. This objective/optimization configuration is substantially worse and adds an adapter; discard.

### Synthesis after 20 experiments

Best remains `684fa10`, AUC **0.7556**. Broader category partitions improved on 0.7538; limiting partitions globally underfit. Extra minute/calendar coordinates, route schedule summaries, and airport distance embeddings did not improve AUC. Row subsampling, L2=30, and withholding 10% for early stopping also hurt. Early stopping selected 715 trees, close to the current 600. Pairwise ranking was a large regression. Current theory: broad date and airport grouping is useful, but extra sparse representations and noise are not. Need distinguish partition-induced variance from capacity limits using one-hot splits and alternative tree growth before piling on more features.

Research refresh: [Categorical data](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) distinguishes one-hot equality splits from category partitions. [Feature interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html) offer targeted control over combinations. Pairwise ranking documentation has been read; its objective alignment alone did not translate into a better model here.

### 21 — One-hot categorical splits

Classification: exploration. Set max_cat_to_onehot=512 so each current category feature uses equality splits. Keep 600 trees and all other best parameters to isolate representation. Hypothesis: one-at-a-time categories may reduce the variance of data-dependent category grouping; this is a different split family, not a nearby max_cat_threshold variation.

Result: `93bce25`, Eval AUC **0.7139**, discard. AUC 0.7139: severe underfitting relative to partition splits is plausible because each equality split isolates only one level.

### 22 — Capacity follow-up for one-hot splits

Classification: follow-up to a diagnostic result. Increase one-hot model rounds fivefold to 3,000 at learning rate 0.05; broad partitions represent many category effects per split while equality splits cannot. This tests whether experiment 21 failed from inadequate capacity rather than rejecting the encoding after an unfair small-tree budget.

Result: `cfb5ac6`, Eval AUC **0.7354**, discard. AUC improved over 600-round one-hot but only to 0.7354; broad category partitions remain decisively better. Training 6.7s.

### 23 — Average subsampled trees within boosting

Classification: exploration. Use num_parallel_tree=4 and subsample=0.8 with the best partition-based model. Experiment 15 showed a single subsampled tree per step is noisy; averaging four independently sampled trees tests whether that noise can be reduced while retaining useful diversity. Source: [XGBoost random forest and boosting combination](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html). Keep all columns available to isolate row-sampling diversity.

Result: `396e388`, Eval AUC **0.7557**, keep. AUC 0.7557 (+0.0001), training about 12.7s and evaluation 19.8s. Marginal gain, but only two settings added and well within the training limit. Keep provisionally; later simplification should revisit the extra trees.

### 24 — Extend averaged boosting

Classification: follow-up. Double boosting rounds from 600 to 1,200 with the four-tree averaging model. Hypothesis: reduced step noise may support additional residual learning; this capacity test is distinct from the earlier one-hot budget follow-up and from the 90%-training early-stopping trial.

Result: `6e7c8fe`, Eval AUC **0.7522**, discard. AUC -0.0035; training 25.4s and evaluation 20.3s. Longer averaged boosting overfits; restore 600 rounds.

### 25 — Loss-guided tree shape

Classification: exploration. Keep a 16-leaf budget (the maximum for depth 4) but use grow_policy=lossguide and max_depth=0, permitting uneven tree shapes. Hypothesis: allocate splits to difficult subpopulations without increasing total leaf count. Sources: XGBoost growth parameters and [LightGBM leaf-wise growth explanation](https://lightgbm.readthedocs.io/en/stable/Features.html); algorithmic motivation only, no new package.

Result: `6668b69`, Eval AUC **0.7558**, keep. AUC +0.0001; training about 15s, evaluation 20.1s. Small gain with a comparable leaf budget; keep for follow-up and revisit simplicity later.

### 26 — Coarser numeric histograms

Classification: ablation/simplification. Set max_bin=64 rather than 256, affecting scheduled departure time and distance while leaving categorical partitions intact. Hypothesis: coarse thresholds reduce sensitivity to timetable-specific minute/distance noise. The negative minute-feature result motivates this direction. Source: XGBoost max_bin documentation.

Result: `fa64975`, Eval AUC **0.7560**, keep. AUC +0.0002 with coarser numeric thresholds; evaluation 19.9s. Keep as modestly better regularization.

### 27 — Direct categorical-code preparation

Classification: ablation/simplification. Reuse fixed pandas Index objects and build output columns directly with Categorical.from_codes. Index.get_indexer maps unknown values to -1 (missing category). Preserve column order and every feature value; eliminate repeated category-index construction and dataframe column replacement. Sources: pandas Index.get_indexer and Categorical.from_codes APIs. Verify against the saved previous prepare on training and synthetic unseen-category rows.

Result: `6d0a6ad`, Eval AUC **0.7560**, keep. AUC exactly preserved at 0.7560; evaluation 9.3s versus 19.9s. Compared saved old/new prepare on 40 reversed training rows with synthetic unseen airport/carrier values: feature values, column order, dtypes, labels, and bulk/single-row equality all passed.

### 28 — Remove within-step averaging

Classification: ablation/simplification. Remove subsample=0.8 and num_parallel_tree=4, restoring one full-data tree per boosting step while retaining loss-guided growth and coarse bins. Averaging only added 0.0001 before those later changes; test whether it is still worth four times as many trees.

Result: `5737031`, Eval AUC **0.7532**, discard. AUC -0.0028 despite much faster training. Averaging matters with loss-guided growth, so restore it.

### 29 — Categorical departure hour

Classification: exploration. Add departure hour modulo 24 as a category, retaining raw HHMM. Unlike experiment 13's minute-within-hour detail, this provides a coarse, non-contiguous grouping of hours across the daily cycle. Source: scikit-learn time feature engineering and native categorical partitioning docs. Fixed clock-domain categories preserve single-row semantics.

Result: `f038a4f`, Eval AUC **0.7557**, discard. AUC -0.0003 with extra feature and evaluation cost (11.8s). Retain the simpler raw-time representation.

### 30 — Smoothed logistic targets

Classification: exploration. Use a custom logistic objective with soft targets 0.05/0.95, retaining the true binary labels for model classes and harness evaluation. Gradient is sigmoid(margin)-soft_target; Hessian remains p*(1-p). Hypothesis: reduce overconfident category/leaf estimates without removing observations. Source: [When Does Label Smoothing Help?](https://arxiv.org/abs/1906.02629); this is an adaptation from neural-network research, not an established claim for this dataset. [XGBoost custom objectives](https://xgboost.readthedocs.io/en/stable/tutorials/custom_metric_obj.html) and the installed classifier code confirm raw-margin gradients and binary-logistic prediction link. No custom evaluation metric.

Result: `e8a1c17`, Eval AUC **0.7560**, discard. AUC unchanged at 0.7560; extra objective code and training overhead are unjustified.

### Synthesis after 30 experiments

Best kept: `6d0a6ad`, AUC **0.7560**. Four-tree averaging, loss-guided 16-leaf growth, and 64 numeric bins produced small gains together; removing averaging afterward cost 0.0028, so it is not redundant. Longer boosting overfit. One-hot splitting remained poor even with 3,000 rounds. Categorical hour and label smoothing added no value. The preparation rewrite exactly preserved features and halved evaluation time to ~9s; saved-artifact row consistency is verified. Current theory: there is limited additional signal in available columns, so improve how broad categorical effects are regularized, while continuing distinct structural exploration.

Research refresh: XGBoost's model tutorial treats gamma as a cost per new leaf, distinct from weight shrinkage; next test requires stronger split evidence. Also investigated [DART](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) and [DART paper](https://arxiv.org/abs/1505.01866) as a future way to reduce dependence among successive trees. Its training cost needs to be respected under the one-minute limit.

### 31 — Require stronger split evidence

Classification: follow-up. Set gamma=20 while retaining the 16-leaf cap. Hypothesis: stop adding leaves whose loss improvement is too small, especially in late boosting rounds; unlike L2 this can reduce tree size directly. Source: XGBoost model tutorial and parameter documentation.

Result: `25ba33e`, Eval AUC **0.7560**, discard. AUC unchanged. Inspection of the best model shows every split gain exceeds 24.39 and all trees have 16 leaves, so gamma=20 was below the smallest selected gain and did not bind.

### 32 — Calibrated split penalty

Classification: follow-up. Use gamma=60, near the observed median training split gain (59.65), rather than the non-binding value 20. The best model's 10th/90th gain percentiles are 39.26/129.99. This explicitly tests an active leaf penalty and should produce variable tree sizes. Source: training-only tree diagnostics and XGBoost gain/regularization formula.

Result: `ff25add`, Eval AUC **0.7406**, discard. AUC -0.0154; training became faster and artifact smaller, confirming strong pruning. Many of the weaker selected splits carry useful signal, so revert the penalty.

### 33 — Tree dropout

Classification: exploration. Use DART with rate_drop=0.02 and skip_drop=0.8, 300 rounds at eta=0.1, one tree per step, and full rows. The intent is to discourage dependence on specific earlier trees. Sources: DART paper and XGBoost DART tutorial read during the last synthesis. A callback stops fitting after 45s if necessary, allowing completion within the 60s harness training limit; no alternative metric or evaluation is added.

Result: `24be976`, Eval AUC **0.7524**, discard. AUC 0.7524; completed all 300 rounds in 44.5s, evaluation 9.0s. The time guard did not truncate training; dropout did not beat the incumbent.

### 34 — Independent-sample airport-date estimates

Classification: exploration. Reserve a stratified 25% of train solely to fit smoothed target means for Origin-Date and Dest-Date. Fit XGBoost once on the remaining 75%, with the fixed means looked up identically in prepare for training and evaluation. No row's label is used to construct its own model-training features. Use TargetEncoder.fit, never fit_transform; no cross-validation, extra metric, or refit. Outputs are two smoothed means, not counts/frequencies. Unknown combinations use the encoder prior. Source: [TargetEncoder leakage discussion](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html); the repository forbids cross-validation, so use one disjoint encoding/model partition instead. Hypothesis: airport-specific conditions on a date are more informative than globally grouped dates, enough to offset the smaller tree-training sample.

Result: `115054e`, Eval AUC **0.0000**, crash. Stopped the owned experiment process group after 189.9s of evaluation; no AUC was produced. Generic TargetEncoder.transform cost ~54.5ms per row under load. Direct frozen posterior lookups matched its outputs exactly, including unseen keys, and took ~0.4ms for both lookups. This is a preparation performance failure, not a model-quality result.

### 35 — Fast independent airport-date lookups

Classification: follow-up/fix of experiment 34. Keep the same disjoint 25% encoder / 75% model split and fitted smoothing. Extract fixed pandas Series lookups from the encoder and apply them directly inside prepare. Unknown keys use the same learned prior. Exact equivalence was checked before changing code; no new hypothesis about model quality or new data is introduced.

Result: `ad2d9c6`, Eval AUC **0.7530**, discard. AUC 0.7530; training 14.3s and evaluation 13.1s. Performance fix succeeded, but the encoding/model data tradeoff did not beat the full-data best.

### 36 — Smaller independent encoding partition

Classification: follow-up. Reduce encoder-only allocation from 25% to 10%, leaving 90% for XGBoost, with unchanged keys/smoothing. Hypothesis: more tree-training rows may compensate for noisier airport-date means. This tests the concrete sample-allocation cost also observed in the early-stopping experiment; retain strict disjointness and fixed row-local lookups.

Result: `de71ad2`, Eval AUC **0.7551**, discard. AUC 0.7551; improved versus 25% encoder allocation but still below 0.7560 with extra preprocessing. End this direction rather than adding more partition complexity.

### 37 — Smaller loss-guided trees

Classification: ablation/simplification. Halve max_leaves from 16 to 8 while retaining averaging and broad category partitions. Hypothesis: fewer regions per tree reduce variance more cleanly than a hard split-gain cutoff. This changes structural capacity, not the already-tested depth-4/depth-8 setup.

Result: `53c6a9c`, Eval AUC **0.7508**, discard. AUC -0.0052. Smaller trees lose useful interactions even with broad categorical splits; restore the incumbent.

### 38 — Larger averaged trees

Classification: follow-up. Test max_leaves=32, bounding the other side of the current 16-leaf capacity. Unlike the earlier depth-8 trial, this retains four-tree averaging, coarse bins, broad categorical partitions, and a strict 32-leaf cap. Hypothesis: averaging may allow more localized interactions without the old deep-tree overfitting.

Result: `4eedd90`, Eval AUC **0.7549**, discard. AUC -0.0011; both 8 and 32 leaves underperform 16 with the current averaging configuration.

### 39 — Finer boosting updates

Classification: follow-up. Use 1,200 rounds at eta=0.025 instead of 600 at 0.05. Preserve nominal total shrinkage, testing update granularity. Experiment 24 increased rounds without lowering eta and overfit; this is a distinct comparison. Source: XGBoost shrinkage/rounds guidance.

Result: `56bee7d`, Eval AUC **0.7563**, keep. AUC +0.0003; training 29.9s, evaluation 10.0s. Finer updates help slightly without increasing nominal cumulative shrinkage.

### 40 — Origin-region date category

Classification: exploration. Cluster airports into eight groups using their shortest-path distance profiles from training-only median route distances, then add a native categorical OriginRegionDate. This pools spatially related airports on each date while allowing all rows to train the classifier. Unlike experiment 16, the representation explicitly combines region with date; unlike target encoding, it uses no labels in lookup fitting. Sources: [Spatiotemporal propagation learning](https://arxiv.org/abs/2207.06959), SciPy shortest paths, and clustering of distance representations. Adaptation only: no external weather/network data, traffic counts, or neural network. Stop fitting after 48s if needed to respect the harness limit.

Result: `bb021a0`, Eval AUC **0.7442**, discard. AUC 0.7442; all 1200 rounds completed in 43.9s. Artifact grew to 264.2MB and evaluation 15.0s. Large categorical interactions overfit; reject the added geometry/cluster machinery.

### Synthesis after 40 experiments

Best: `56bee7d`, AUC **0.7563**, baseline **0.7203**. Smaller updates helped modestly. Leaf budget 16 beats both 8 and 32. A non-binding split penalty changes nothing, and a binding penalty loses signal. DART did not improve. Independent airport-date target means were implemented without self-label leakage or cross-validation, but reserving rows for encoding hurt net performance; a direct-lookup rewrite fixed their initial evaluation slowness. Region-date categorical crossing also hurt badly and enlarged the artifact. Current theory: the six raw/date features contain most usable signal; retain all rows and improve ensemble stability. Avoid costly high-cardinality interaction features unless a materially different mechanism is proposed.

Research refresh: [Spatiotemporal delay learning](https://arxiv.org/abs/2207.06959) motivated the regional trial, whose negative result limits this adaptation. [XGBoost forests](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) recommends column randomness as well as row randomness; test that next. Also consider gradient-based sampling and learning-rate schedules described by XGBoost rather than repeating more feature crosses.

### 41 — Feature subsampling within trees

Classification: follow-up. Add colsample_bynode=0.8 to the four-tree averaged model. Hypothesis: different available features at each split diversify trees beyond row subsampling and reduce dependence on the dominant time feature. Source: XGBoost forest tutorial and column-sampling parameters.

Result: `2b28215`, Eval AUC **0.7578**, keep. AUC +0.0015, training 28.0s and evaluation 10.0s. Feature diversity gives a clearer gain than recent fine regularization changes.

### 42 — Gradient-based row sampling

Classification: exploration. Use sampling_method=gradient_based and subsample=0.5 with explicit hist trees. XGBoost's stable docs support this on CPU from 3.2, and installed version is 3.4.1. Hypothesis: gradient-informed selection preserves split information with fewer sampled rows. Sources: [MVS research](https://arxiv.org/abs/1910.13204) and [XGBoost sampling parameters](https://xgboost.readthedocs.io/en/stable/parameter.html); the paper motivates the category of method, not equivalence of implementations.

Result: `001819d`, Eval AUC **0.7542**, discard. AUC -0.0036; training 43.4s versus 28.0s for uniform sampling. Gradient-informed row selection did not improve this configuration.

### 43 — Decreasing learning-rate schedule

Classification: exploration. Replace constant eta=0.025 with a linear decline from 0.045 to 0.005 over 1,200 rounds, preserving mean shrinkage. Hypothesis: faster early fitting and conservative later corrections improve the boosting path without extra trees. Source: [XGBoost LearningRateScheduler API](https://xgboost.readthedocs.io/en/stable/python/python_api.html#xgboost.callback.LearningRateScheduler); installed 3.4.1 callback source confirmed after-iteration updates, so schedule advances to the next round.

Result: `69432c6`, Eval AUC **0.7572**, discard. AUC -0.0006; no gain from the added callback. Retain constant eta=0.025.

### 44 — Fewer parallel trees after feature subsampling

Classification: ablation/simplification. Reduce num_parallel_tree from 4 to 2 with row and node-level feature sampling unchanged. Hypothesis: the feature diversity introduced in experiment 41 may preserve accuracy with half as many trees. Earlier experiment 28 removed both parallel trees and row sampling, before feature sampling existed, so it did not isolate this comparison. Source: XGBoost random-forest tutorial cited above.

Result: `e8fd76c`, Eval AUC **0.7568**, discard. AUC -0.0010 despite halving training to 14.3s and the artifact to 26.4MB. The accuracy loss is larger than recent simplification tolerances; retain four trees.

### 45 — Stronger feature diversity

Classification: follow-up to experiment 41. Set colsample_bynode=0.5 instead of 0.8, exposing three rather than four of the six features at each split. Hypothesis: stronger decorrelation improves the four-tree average; this tests the strength of the newly successful mechanism, not a new random seed. Source: XGBoost column-sampling parameter documentation.

Result: `05aab0c`, Eval AUC **0.7575**, discard. AUC -0.0003; stronger feature sampling does not improve on 0.8. Keep the simpler established setting.

### 46 — Remove little-used distance feature

Classification: ablation/simplification. Remove Distance from numeric inputs. Training-model diagnostics on this run's incumbent artifact show only 57 Distance splits out of 72,000 and total gain 2,108 versus millions for dates/airports. Importance is not an independent evaluation, so use the harness to test whether removing this apparently redundant route proxy preserves quality. This also changes the available sampling pool from six to five features; colsample_bynode=0.8 still exposes four features. Recent research: [interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html), [interaction research](https://arxiv.org/abs/2007.05758), and [soft voting](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html).

Result: `540c5d9`, Eval AUC **0.7573**, discard. AUC -0.0005. Its small split usage did not imply that removal was free, and runtime barely changed; restore Distance.

### 47 — Monotonic daytime delay accumulation

Classification: exploration. Constrain the main departure-time effect to increase between 05:00 and 20:00. Clip CRSDepTime to that range, and add an unconstrained NightTime feature present only outside it, preserving observed overnight and late-evening exceptions. Descriptive training-label means rise from 0.186 at 05:00 to 0.653 at 20:00, then decline to 0.559 at 23:00; these are diagnostics, never count/target-mean features. Hypothesis: the constraint suppresses noisy local reversals while retaining night behavior. Source: [XGBoost monotonic constraints](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html). Batch/single-row feature equality will be checked. This adds one feature and changes the sampling pool, a limitation of the comparison.

Result: `0851c8b`, Eval AUC **0.7563**, discard. AUC -0.0015; training 37.1s and evaluation 10.6s. Even with night exceptions the shape restriction and added representation did not help; batch/single-row equality passed.

### 48 — Sample features once per tree

Classification: follow-up to experiment 41. Replace colsample_bynode=0.8 with colsample_bytree=0.8. Keep the same four-feature subset size, but hold it fixed throughout each tree. Hypothesis: whole-tree diversity limits overly specific combinations and allows some trees to specialize in simpler global effects. Source: [XGBoost column sampling semantics](https://xgboost.readthedocs.io/en/stable/parameter.html).

Result: `237dc64`, Eval AUC **0.7578**, discard. AUC equals 0.7578; training 27.3s and artifact 48.9MB. No meaningful code simplification, so preserve the incumbent. The alternate sampling geometry may be useful as a complementary ensemble member.

### 49 — Larger minimum leaf support

Classification: follow-up. Increase min_child_weight from 20 to 100, leaving leaf budget 16 and all ensemble settings fixed. Hypothesis: the many date/airport partitions shown in training diagnostics benefit from stronger support requirements at their most specific leaves. The earlier successful change was from 1 to 20 before categorical and ensemble changes; this tests whether that mechanism extends to the current model. Source: [minimum child Hessian documentation](https://xgboost.readthedocs.io/en/stable/parameter.html).

Result: `dbaf9b2`, Eval AUC **0.7576**, discard. AUC -0.0002, training 29.1s. Stronger leaf support is roughly comparable but offers no simplification or gain.

### 50 — Date as a shared additive effect

Classification: exploration. Use disjoint interaction groups: Date alone, and all five other features together. Hypothesis: global date conditions account for much of the calendar signal, while specific date-airport combinations may overfit; restricting them could improve generalization. This deliberately tests the role of interactions rather than dropping Date. Sources: [XGBoost interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html) and [Goyal et al.](https://arxiv.org/abs/2007.05758).

Result: `dfd5fab`, Eval AUC **0.7325**, discard. AUC -0.0253 to 0.7325. Calendar interactions are essential, not merely an overfitting nuisance. Restore unrestricted interactions.

### Synthesis after 50 experiments

Best remains `2b28215`, AUC **0.7578**. Feature sampling is the clearest recent improvement. Sampling once per tree matches node-level sampling, but fewer averaged trees lose accuracy. More aggressive feature/row sampling, decaying learning rates, larger minimum leaf support, dropping Distance, and daytime monotonicity did not improve. Removing date interactions caused a large drop, showing that calendar signal depends strongly on flight context. Preserve those interactions; explore training order and averaging independently trained models instead of adding more sparse feature crosses.

Research refresh: [XGBoost training continuation](https://xgboost.readthedocs.io/en/stable/python/examples/continuation.html) permits staged training within one booster; [base margins](https://xgboost.readthedocs.io/en/stable/tutorials/intercept.html) provide an alternative composition mechanism; [soft voting](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html) averages model probabilities. [Refresh updater](https://xgboost.readthedocs.io/en/stable/python/examples/update_process.html) can re-estimate existing leaf values; any trial here would use the identical training rows, never additional data. These are new mechanisms to explore, with their time/complexity costs measured.

### 51 — Additive warm-up before interaction boosting

Classification: exploration. Fit 600 depth-one rounds at eta=0.1, then continue the same booster with the incumbent 1,200 unrestricted 16-leaf rounds at eta=0.025. Both stages use exactly the same full training rows and four parallel trees; no validation, extra metric, or retrain on more data. Hypothesis: estimate stable global effects first so interaction trees focus on residual structure. Unlike experiment 50, the final stage allows all date interactions. Source: XGBoost continuation documentation.

Result: `b358af6`, Eval AUC **0.7524**, discard. AUC 0.7524, training 36.2s. The staged global-first fit did not improve the unrestricted model; discard the extra stage.

### 52 — Average complementary sampling geometries

Classification: exploration/follow-up to experiments 41 and 48. Soft-vote the incumbent node-sampled model and a tree-sampled model using weights 2:1. The second model uses 600 rounds at eta=0.05 (same cumulative shrinkage), keeping total training comfortably under 60 seconds; no data split, validation, or extra evaluation. Hypothesis: independent boosting paths with different feature restrictions make complementary errors. Source: [scikit-learn VotingClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html). The 2:1 weights are fixed before running, favoring the fully tested incumbent.

Result: `3a77ba5`, Eval AUC **0.7586**, keep. AUC +0.0008, training 44.6s and evaluation 11.0s. Keep: ten straightforward lines using an installed standard ensemble class, with a measurable gain and safe training duration.

### 53 — Reduce thread coordination overhead

Classification: ablation/simplification of computation. Set n_jobs=4 for both ensemble members instead of all eight available CPUs. Hypothesis: six-feature histogram building may be limited by thread coordination, so fewer workers can preserve predictions while reducing runtime; any saved time would support stronger averaging under the 60s limit. Source: XGBoost parameter guidance to consider thread contention. Judge the same harness AUC and measured runtime, never a separate score.

Result: `f22a597`, Eval AUC **0.7586**, discard. AUC unchanged at 0.7586, training 46.2s versus 44.6s. Fewer workers did not reduce overhead enough to help; restore automatic use of available CPUs.

### 54 — Replace independent ensemble with larger internal average

Classification: ablation/simplification. Remove VotingClassifier and its two-model configuration, and increase the incumbent single XGBoost model to eight parallel trees. Hypothesis: greater averaging within each boosting step can preserve the ensemble gain with a simpler prediction object and fewer dependencies. Expected training is near 56s from the four-tree timing, so the harness limit may bind; a timeout will be logged as failure. Source: XGBoost boosted random-forest tutorial.

Result: `367ab5d`, Eval AUC **0.7578**, discard. AUC 0.7578, below the two-model ensemble and no better than four parallel trees. Training 57.5s and artifact 106.0MB make this a poor tradeoff; independent boosting paths appear more useful than larger within-step averages.

### 55 — Squared-probability loss in the complementary model

Classification: exploration. Keep the main logistic model unchanged, but train the second tree-sampled model on 2*(sigmoid(margin)-y)^2. Use its exact gradient 4*(p-y)*p*(1-p) and positive Gauss-Newton/expected curvature 4*(p*(1-p))^2, floored only for numerical stability. Scaling matches logistic gradient and curvature at p=0.5. Hypothesis: bounded probability loss emphasizes a different set of errors and improves the vote. Sources: [Brier scoring rule](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.brier_score_loss.html), [custom-objective curvature guidance](https://xgboost.readthedocs.io/en/stable/tutorials/advanced_custom_obj.html), and [robust classification loss research](https://papers.nips.cc/paper_files/paper/2008/hash/f5deaeeae1538fb6c45901d524ee2f98-Abstract.html). This is a Brier-style loss adaptation, not an implementation of SavageBoost. Only harness AUC will evaluate the model; synthetic derivative checks validate the implementation.

Result: `a65b3f1`, Eval AUC **0.7587**, discard. AUC 0.7587, a raw +0.0001 versus the kept model, but eight extra lines and custom curvature are not justified by such a small gain. Keep the standard-logistic 0.7586 ensemble under the simplicity criterion. Synthetic derivative checks passed; training 43.7s.

### 56 — Equal voting weights

Classification: ablation/simplification. Remove the explicit 2:1 weights, using VotingClassifier's default equal average. Experiment 48 found the two sampling geometries equally strong individually, so the initial preference for the node-sampled member may be unnecessary. Hypothesis: removing that extra setting preserves or improves AUC. This is a single pre-specified weighting ablation, not a sweep over weights.

Result: `a004c80`, Eval AUC **0.7587**, keep. AUC +0.0001 to 0.7587 while removing an explicit weighting choice. This matches the custom-loss trial with simpler standard objectives; training 41.6s.

### 57 — L1 regularization of leaf scores

Classification: exploration. Add reg_alpha=20 to both ensemble members. Training diagnostics on the single-model incumbent gave median leaf Hessian 1,267 and median absolute unshrunk leaf score 0.172; a penalty of 20 should shrink weak corrections while leaving strong global effects comparatively intact. Hypothesis: thresholding weak leaf updates improves ranking without changing the interaction structure. Unlike prior L2 and split-gain penalties, L1 can set weak updates to zero. Source: [XGBoost regularization parameters](https://xgboost.readthedocs.io/en/stable/parameter.html).

Result: `6be1e88`, Eval AUC **0.7450**, discard. AUC fell to 0.7450; artifact shrank to 61.7MB. The penalty is much too aggressive for this categorical model, despite seemingly modest scale relative to final leaf statistics. Revert.

### 58 — Cyclic clock coordinates

Classification: exploration. Retain raw HHMM and add sine/cosine of minutes since midnight with period 1,440. Hypothesis: a circular representation can group late-night and post-midnight departures and expose useful non-monotonic splits with fewer conditions. Unlike the failed monotonic trial, this imposes no shape restriction; unlike the minute-of-hour and hour-category trials, it represents the entire daily cycle smoothly. Source: [scikit-learn time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html). This also changes feature-sampling availability; if successful, ablate redundant time coordinates. All calculations are row-local and will receive a batch/single-row equality check.

Result: `d28be07`, Eval AUC **0.7582**, discard. AUC 0.7582, -0.0005, with training up to 50.5s. Row-local invariance passed, but extra time features did not improve the ensemble.

### 59 — Regularize leaf values after fixing category partitions

Classification: exploration/follow-up to 57. After the standard equal-weight ensemble fit, refresh only its smaller tree-sampled member on the identical full X_train/y_train, preserving every split and applying reg_alpha=20 to new leaf values. Hypothesis: leaf-only shrinkage can help without corrupting category ordering. Source inspection of [v3.4.1 CalcWeightCat](https://raw.githubusercontent.com/dmlc/xgboost/v3.4.1/src/tree/split_evaluator.h) shows it calls the general regularized weight function, explaining why final leaf sizes alone were a poor guide for experiment 57. [Refresh updater source](https://raw.githubusercontent.com/dmlc/xgboost/v3.4.1/src/tree/updater_refresh.cc) supports categorical traversal and fixed structures. No rows are added, no validation/refit on more data occurs. Set tree_method=approx only to make the sklearn input a regular DMatrix; the explicit refresh updater performs no new sketching/splitting. Cost may approach the harness training limit.

Result: `ff6c959`, Eval AUC **0.7580**, discard. AUC 0.7580, training 50.4s. Much less harmful than applying L1 during split construction, but still below the incumbent. An artifact comparison confirmed every split and category partition was unchanged. Discard the extra refresh stage.

### 60 — L1 on the category-statistic scale

Classification: evidence-driven follow-up to 57 and 59. Apply reg_alpha=1 during ordinary fitting of both members, with no refresh stage. The source confirmed that the penalty also enters per-category ranking statistics, whose support is much smaller than final leaf support; alpha=20 was therefore badly scaled. Hypothesis: a unit penalty can damp very weak category scores without broadly collapsing their ordering. This is a single mechanism-informed correction, not a parameter sweep. Source: [v3.4.1 categorical split evaluator](https://raw.githubusercontent.com/dmlc/xgboost/v3.4.1/src/tree/split_evaluator.h).

Result: `12237ac`, Eval AUC **0.7593**, keep. AUC +0.0006 to 0.7593, training 43.1s. A penalty scaled to individual category statistics succeeds where the leaf-scale penalty failed, with only one standard parameter.

### Synthesis after 60 experiments

Best: `12237ac`, AUC **0.7593**, baseline **0.7203**. Independent node-/tree-sampled models improve over larger within-step averages, and equal voting weights simplify and improve the ensemble. Additive warm-up, cyclic clock features, and post-fit leaf refresh did not help. A custom squared-probability loss gave only a negligible gain and was rejected; equal standard-logistic voting matched it more simply. Strong L1 was harmful because it also affects per-category ordering; source-guided reduction to alpha=1 improved AUC. This is evidence that categorical sorting stability, not simply final leaf size, is a useful remaining direction.

Research refresh: searched [categorical split thresholds](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) and [feature-weighted column sampling](https://xgboost.readthedocs.io/en/stable/python/examples/feature_weights.html). Also read [tree-method differences](https://xgboost.readthedocs.io/en/stable/treemethod.html): Hessian-weighted sketches can differ from fixed hist bins, at higher cost. Installed 3.4.1 uses max_cat_to_onehot=4; do not import the development-version default. Next test the default L2 contribution to category ordering, selective one-hot treatment of only the small carrier field, and whether row sampling remains necessary alongside two forms of column diversity.

### 61 — Remove L2 bias from category ordering

Classification: evidence-driven follow-up. Set reg_lambda=0 while retaining the newly useful reg_alpha=1. Source inspection shows categorical sorting uses -(soft_threshold(gradient, alpha))/(hessian+lambda). Hypothesis: mild L1 can suppress weak categories while removing the default denominator offset reduces bias among sparse categories. This differs from the much stronger L2 trial in experiment 18 and is motivated by the newly established sorting mechanism.

Result: `dc1fa8c`, Eval AUC **0.7593**, discard. AUC unchanged at 0.7593, with no runtime or simplicity advantage. Keep the default L2 value and avoid the extra setting.

### 62 — One-hot splits only for the small carrier field

Classification: exploration. Set max_cat_to_onehot=32, so only the 20-level UniqueCarrier uses equality splits; Origin, Dest, and Date retain native category partitions. Hypothesis: preserving distinct carrier effects while still pooling the high-cardinality fields improves local interactions. Earlier experiments 21–22 forced every category field to one-hot and were poor; this selectively changes only the low-cardinality field. Source: [categorical split thresholds](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html).

Result: `7dd78fc`, Eval AUC **0.7576**, discard. AUC -0.0017 to 0.7576. Native category grouping remains useful even for the 20-level carrier field.

### 63 — Remove row subsampling after adding column diversity

Classification: ablation/simplification. Delete subsample=0.8, using all training rows for each tree. Keep both node- and tree-level feature sampling across the ensemble. Hypothesis: column diversity may now provide sufficient decorrelation, allowing more stable category statistics from full rows. Earlier row-sampling comparisons predated this two-model feature-sampled ensemble and did not test that redundancy. If accuracy holds, this removes a parameter and a source of sampling variance.

Result: `3fda6a7`, Eval AUC **0.7582**, discard. AUC -0.0011, training improved to 36.3s. Accuracy loss outweighs the deleted parameter. Separately verified kept artifact 12237ac: source/artifact preparation equality, batch/single-row equality, unseen-category handling, no CSV reads during preparation, and finite normalized probabilities all passed.

### 64 — Restore default numeric split resolution

Classification: ablation/simplification and follow-up. Remove max_bin=64 to use the default 256 bins. Hypothesis: the stronger ensemble and mild categorical L1 may now support finer departure-time thresholds without overfitting; removing the override also simplifies configuration. The original coarse-bin comparison preceded both major ensemble improvements. Source: [XGBoost tree-method guidance](https://xgboost.readthedocs.io/en/stable/treemethod.html) on hist accuracy and max_bin.

Result: `810a559`, Eval AUC **0.7593**, keep. AUC unchanged at 0.7593, training 42.5s. Removing the coarse-bin override is a simplification win; retain the default.

### 65 — Favor departure time in feature sampling

Classification: exploration. Give CRSDepTime feature weight 2 and every other input weight 1 in both ensemble members. Hypothesis: keeping the strong daily time effect available more often improves the ensemble while still randomizing categorical context. Unlike the failed cyclic expansion, this adds no transformed columns or new split geometry. Source: [XGBoost feature-weighted column-sampling demo](https://xgboost.readthedocs.io/en/stable/python/examples/feature_weights.html); installed constructor support was checked. Weights are fixed beforehand and use feature identity, never row frequencies.

Result: `c47723c`, Eval AUC **0.7590**, discard. AUC 0.7590, -0.0003, without a runtime advantage. Uniform feature selection remains preferable and simpler.

### 66 — Standard depth-four trees in the mature ensemble

Classification: ablation/simplification. Replace unlimited-depth loss-guided growth with max_depth=4, removing max_leaves and grow_policy overrides. Both structures allow at most 16 leaves, but the depth cap limits long conditional paths. Hypothesis: feature diversity plus mild L1 now makes the ordinary growth policy sufficient, and the shorter paths may generalize better. The original growth-policy comparison preceded these changes and yielded only +0.0001, making it a useful simplification to revisit. Source: XGBoost growth-policy documentation.

Result: `f165a32`, Eval AUC **0.7584**, discard. AUC -0.0009, training 38.4s. The simpler growth configuration loses enough accuracy to retain the current leaf-guided model.

### 67 — More expressive complementary member

Classification: follow-up/exploration. Increase max_leaves to 32 only in the 600-round tree-sampled member; the main 1,200-round model remains at 16 leaves. Hypothesis: a finer interaction model can contribute useful complementary predictions even though a larger standalone model lost in experiment 38. This now includes mild L1 and averages across different model structures; date interactions have already proved essential. Expected training remains under 60s. Source: XGBoost ensemble and growth-policy guidance.

Result: `83404be`, Eval AUC **0.7609**, keep. AUC +0.0016 to 0.7609, training 48.3s and artifact 102.6MB. One standard setting gives a clear gain; keep the mixture of 16- and 32-leaf models.

### 68 — Isolate the stronger complementary member

Classification: ablation/simplification. Train only the 600-round eta=0.05 tree-sampled 32-leaf model, removing the main model and VotingClassifier. Hypothesis: the new member may account for most of the gain and could replace the ensemble. This directly tests whether two prediction paths are still necessary after experiment 67, rather than assuming the mixture is best. A near-equal result would offer a large reduction in trees, runtime, artifact size, and code.

Result: `298d665`, Eval AUC **0.7616**, keep. AUC +0.0007 to 0.7616, training only 18.8s and artifact 48.9MB. Remove the weaker ensemble member and sklearn voting/clone imports: a clear accuracy and simplicity win.

### 69 — Finer updates for the new single-model winner

Classification: follow-up. Double boosting rounds from 600 to 1,200 and halve eta from 0.05 to 0.025, preserving total shrinkage. Hypothesis: smaller updates improve category partitions in the now-successful 32-leaf tree-sampled model, as they modestly helped an earlier 16-leaf model. The simplification in experiment 68 leaves ample training headroom. Source: XGBoost shrinkage/round-count guidance.

Result: `49e8d6c`, Eval AUC **0.7619**, keep. AUC +0.0003 to 0.7619; training 37.4s, artifact 97.3MB. Keep the standard-parameter improvement with comfortable runtime headroom.

### 70 — More averaging at a fixed total tree budget

Classification: follow-up. Use 600 rounds, eta=0.05, and eight parallel trees instead of 1,200 rounds, eta=0.025, and four trees. Both configurations contain 4,800 trees, nominal total shrinkage 30, and the same per-tree shrinkage. Hypothesis: stronger averaging within each update may beat more frequent gradient updates in the larger-leaf model. This cleanly contrasts update granularity against averaging, rather than simply adding capacity. Source: XGBoost boosted random-forest tutorial.

Result: `4feff08`, Eval AUC **0.7619**, discard. AUC ties 0.7619, training 38.1s versus 37.4s. No simplicity or performance benefit; retain the more frequent four-tree updates.

### Synthesis after 70 experiments

Best: `49e8d6c`, AUC **0.7619**. The decisive recent step was expanding the tree-sampled ensemble member to 32 leaves, then discovering that this member alone beat the ensemble. Removing the weaker member improved both score and simplicity. Finer updates helped again; redistributing the same 4,800 trees into eight-tree updates tied but did not improve. Default numeric bins simplify the model, while row subsampling, category grouping even for carriers, and unconstrained leaf-guided growth remain useful. A saved-artifact check confirmed row-local frozen preparation and unseen-category behavior. The current best uses just the same six time/distance/carrier/airport/date features and one standard XGBoost classifier.

Research refresh: searched [leaf-wise complexity guidance](https://lightgbm.readthedocs.io/en/v4.6.0/Parameters-Tuning.html) and [XGBoost overfitting controls](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html). Adapt only the structural insight: tree size and iteration count jointly control capacity; no new library is introduced. Remaining short-budget tests will balance leaf count against rounds and remove any now-unnecessary regularization.

### 71 — Larger trees at a similar total leaf budget

Classification: follow-up. Use 64 leaves with 600 rounds at eta=0.05, compared with 32 leaves and 1,200 rounds at eta=0.025. Keep four parallel trees. Nominal cumulative shrinkage and maximum total leaf count are preserved. Hypothesis: deeper within-tree interactions can extend the successful 32-leaf direction without doubling the training budget. This is a capacity-allocation comparison, not an unrestricted increase in tree count.

Result: `60d82da`, Eval AUC **0.7621**, keep. AUC +0.0002 to 0.7621, with training reduced to 27.3s and a 95.2MB artifact. Keep the more efficient capacity allocation.

### 72 — Remove L1 from the new larger-tree winner

Classification: ablation/simplification. Delete reg_alpha=1 while retaining the newly successful 64-leaf configuration. Hypothesis: larger tree-sampled structures may account for the latest gains without the previously added category regularizer; if accuracy holds, remove another setting. If it drops, this establishes that mild categorical regularization remains useful at the new capacity.

Result: `306c158`, Eval AUC **0.7606**, discard. AUC -0.0015 to 0.7606. Mild categorical regularization remains important in the larger-tree winner.

### 73 — Hessian-weighted adaptive numeric sketches

Classification: exploration. Set tree_method=approx with all other winning settings fixed. Hypothesis: rebuilding numeric cut proposals using current Hessian weights allocates split resolution to uncertain departure-time regions, potentially improving over fixed hist bins. Source: [XGBoost tree methods](https://xgboost.readthedocs.io/en/stable/treemethod.html), researched earlier; the documentation explicitly notes possible gains for objectives with non-constant Hessians and higher computation cost. The winner's 27s training leaves room for this algorithmic comparison.

Result: `9295421`, Eval AUC **0.0000**, crash. Training exceeded the 60s limit before producing an artifact or AUC. The fixed winning configuration is too expensive with this algorithm; revert. Current best 60d82da passed saved/source preparation equality, row independence, unseen categories, finite normalized probabilities, and final save_and_evaluate-call checks.

### 74 — Fewer boosting rounds in the larger-tree model

Classification: ablation/simplification. Reduce n_estimators from 600 to 400 with eta=0.05 and 64 leaves unchanged. Hypothesis: the more expressive trees may reach their best generalization earlier, allowing a one-third reduction in trees and artifact size. This deliberately changes total fitting strength rather than preserving it, unlike experiments 69–71. A close result could justify the materially smaller model.

Result: `8096331`, Eval AUC **0.7633**, keep. AUC +0.0012 to 0.7633, training 17.6s, evaluation 9.3s, artifact 63.6MB. The larger trees needed less cumulative boosting; reducing one-third of the rounds improves both accuracy and efficiency. This is the final candidate within the two-hour start budget.


## Final summary

Completed **74 experiments** on branch **oct2**: 24 kept decisions, 48 discards, and 2 failed runs. The two-hour clock was exhausted after the final experiment; no new experiment was launched after TIME IS UP.

- Baseline: `92e43e6`, Eval AUC **0.7203**.
- Best and final commit: `809633166898f4e2a1d6fd5cbf3b7b2f640c5cdb`, Eval AUC **0.7633** — an absolute gain of **0.0430**.
- Final measured fit: **17.6s**; evaluation: **9.3s**; artifact: **63.6MB** at `artifacts/809633166898f4e2a1d6fd5cbf3b7b2f640c5cdb.pkl`.
- Final model: one standard XGBoost classifier, 400 rounds at eta=0.05, four parallel trees per round, 64 loss-guided leaves, min_child_weight=20, reg_alpha=1, max_cat_threshold=256, subsample=0.8, and colsample_bytree=0.8. Numeric histogram bins use the default. Inputs are CRSDepTime, Distance, UniqueCarrier, Origin, Dest, and the combined Month-DayofMonth Date category.

What worked: the combined date category, broad native category partitions, calibrated structural capacity, row/feature diversity, and mild L1 at the category-statistic scale. Ensemble experiments exposed a stronger tree-sampled member; removing the weaker member then improved both AUC and simplicity. The final larger trees needed fewer boosting rounds, producing the best score with substantially less computation. Frozen categorical index lookups also made row-wise preparation much faster than the baseline.

What did not: sparse category crosses, route/spatial extra features, disjoint target-encoding partitions, monotonic time constraints, cyclic clock expansion, ranking/dropout alternatives, stronger generic penalties, and custom-loss or leaf-refresh complexity. Approximate Hessian-weighted sketching exceeded the training limit. An earlier generic target-encoder preparation was stopped for excessive per-row cost; its fixed-lookup replacement ran successfully but did not improve AUC.

Final verification: loaded the winning saved artifact and confirmed exact source/artifact preparation agreement, batch/single-row feature equality, unknown-category handling, no data-file reads during preparation, finite normalized probabilities, matching feature names, 400 stored boosting rounds, and the required final save_and_evaluate call. All 74 TSV records were validated. The branch is at the winning commit, train.py is clean, and it is the only tracked file changed from the baseline. Results, research notes, timing files, and harness artifacts remain in place and uncommitted as required.

Next research directions: controlled comparisons of tree size and total boosting strength around the final 64-leaf solution, stronger row sampling with the larger trees, and category-specific regularization that separates split ordering from leaf penalties. These were not added after the clock expired.
