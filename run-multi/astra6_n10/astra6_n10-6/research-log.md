# Research log: oct2

## Setup — 2026-10-02

- Created branch `oct2` directly from the current HEAD, `92e43e6`.
- Read `program.md`, `README-autoresearch.md`, `train.py`, and `harness.py`.
- Verified that `data/train.csv` and `data/eval.csv` exist, are nonempty, and are readable; their contents were not inspected during setup.
- Verified imports: Python 3.14.4, pandas 3.0.6, NumPy 2.5.3, XGBoost 3.4.1, scikit-learn 1.9.1, and cloudpickle 3.1.2. The environment reports 8 CPUs.
- Initialized `results.tsv` with only the required tab-separated header. Both logs remain uncommitted.
- Left the starter `train.py` unchanged. No experiments have run and no AUC has been measured.
- Confirmed the experiment clock has not started. Awaiting confirmation to begin the two-hour experiment.

## Start sequence

1. After confirmation, run `python3 harness.py start` as the first action.
2. Run the unchanged starter through `python3 harness.py run > run.log 2>&1` and record the baseline against commit `92e43e6`.
3. Research relevant primary sources before the first non-baseline experiment, then follow the experiment and logging rules in `program.md`.

## Experiment started

The user confirmed go. The first action was `python3 harness.py start`; all experiments use the harness and its original evaluation.

### 001 — Baseline — `92e43e6`

Unchanged starter, 30 trees, depth 6, learning rate 0.1. Eval AUC **0.7203**; training phase 1.1s, evaluation 31.2s. **Keep** as baseline.

### Initial research

Read the official [parameter tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html), [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html), and [categorical data tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html). Capacity, regularization, shrinkage, and categorical split behavior are the initial research directions. Start with moderate depth (4–8), learning rates 0.03–0.1, and enough boosting rounds to expose underfitting; these are experimental choices rather than claimed universal optima.

Inspected only train.csv: 200,000 rows, balanced binary labels, no missing values, eight predictors; month/day/week use c-N strings, airport columns each have 283 categories. No row-count features will be used. The first feature directions to investigate are schedule/calendar representations and categorical interactions fitted only on training data.

### 002 — More boosting rounds

**Class:** follow-up to baseline. **Hypothesis:** 30 trees underfit schedule and airport interactions. Increase only n_estimators from 30 to 300 at learning rate 0.1 to test capacity before feature changes. Motivated by the official tuning guide's bias/variance discussion. Parent: `92e43e6`.

**002 outcome:** `9570071`, Eval AUC **0.7342**, training 2.6s, evaluation 30.7s. **Keep**, +0.0139 over baseline. Extra boosting addresses substantial underfitting.

### 003 — Remove redundant category masking

**Class:** ablation/simplification of 002. **Hypothesis:** direct `pd.Categorical(values, categories=fixed_levels)` preserves the exact known/unknown mapping, while removing six repeated `isin`/`where` operations per evaluation row. Expected unchanged AUC with simpler, faster code. [Pandas Categorical documentation](https://pandas.pydata.org/docs/reference/api/pandas.Categorical.html) specifies unknown values map to NaN. Parent: `9570071`.

**003 outcome:** `ad16273`, Eval AUC **0.7342**, training 2.5s, evaluation 21.1s. **Keep** as a simplification win; evaluation is about 9.6s faster. Pandas emits a future-version deprecation warning for unseen categories but current behavior is correct; a later category implementation can avoid that dependency.

### 004 — Explicit calendar-date category

**Class:** exploration, first feature engineering. **Hypothesis:** a Month × DayofMonth category allows single splits on days with shared disruption patterns, which otherwise require interacting separate calendar fields. Derived solely from each row with categorical levels fitted on train. The [scikit-learn time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) motivates explicit time representations; the specific daily interaction is our hypothesis, not a claim from that example. Parent: `ad16273`.

**004 outcome:** `06b6661`, Eval AUC **0.7500**, training 3.7s, evaluation 26.2s. **Keep**, +0.0158. Batch/single-row feature equality passed on training examples. Daily effects appear much easier to learn through one explicit category.

### 005 — Regularize date and airport partitions

**Class:** follow-up to 004. **Hypothesis:** categorical date/airport splits can fit noisy small groups; min_child_weight=20 and reg_lambda=10 should reduce their variance while retaining daily effects. All other settings fixed. These parameters' roles are documented in the official XGBoost parameter reference linked above. Parent: `06b6661`.

**005 outcome:** `f2ac5a7`, Eval AUC **0.7526**, training 2.7s, evaluation 26.3s. **Keep**, +0.0026. Regularization helps despite using all 200,000 training rows.

### 006 — Restrict categorical split search

**Class:** follow-up to 005. **Hypothesis:** `max_cat_threshold=16` (instead of the default 64) will limit overly specific categorical partitions, especially on the 365-level date and airport fields. This isolates category-specific regularization after broader leaf regularization helped. Source: official XGBoost categorical parameter reference. Parent: `f2ac5a7`.

**006 outcome:** `7ed68ce`, Eval AUC **0.7552**, training 2.5s, evaluation 26.6s. **Keep**, +0.0026; serialized model also shrank from 11.4 MB to 6.5 MB.

### 007 — Deeper trees after regularization

**Class:** follow-up to 006. **Hypothesis:** with smaller categorical partitions and supported leaves, depth 8 can capture date × airport × departure-time interactions that depth 6 misses. Change only max_depth from 6 to 8. Parent: `7ed68ce`.

**007 outcome:** `af4ce47`, Eval AUC **0.7571**, training 2.9s, evaluation 26.7s. **Keep**, +0.0019. Training split gain in parent 006 ranked CRSDepTime and FlightDate highest; this is descriptive training information, not an additional evaluation metric.

### 008 — Smaller boosting steps

**Class:** follow-up to 007. **Hypothesis:** 600 trees at learning_rate=0.05 retain roughly the same total boosting path length as 300 at 0.1, but finer updates reduce overshoot and categorical split noise. Motivated by the official tuning guide's shrinkage advice. Parent: `af4ce47`.

**008 outcome:** `67dc356`, Eval AUC **0.7590**, training 4.8s, evaluation 26.8s. **Keep**, +0.0019. Smaller updates helped with only a modest training-time cost.

### 009 — Route category

**Class:** exploration of route-level interactions. **Hypothesis:** an Origin × Dest category can represent route-specific schedule and operational effects more economically than two separate airport splits. Keep the well-regularized model and add only this feature with training-fitted levels. Native partitioning is supported by the official categorical tutorial read during initial research. Parent: `67dc356`.

**009 outcome:** `bb545f9`, Eval AUC **0.7460**, training 7.5s, evaluation 39.4s. **Discard**, -0.0130. The high-cardinality route category hurt generalization and cost more evaluation time. Return to `67dc356`.

### 010 — Departure hour and minute

**Class:** exploration of scheduled-time representation. **Hypothesis:** explicit hour and minute-of-hour complement ordered HHMM values, particularly for rounded scheduling patterns and repeated time-of-hour effects. Add two numeric row-local features while retaining CRSDepTime. Source: scikit-learn time-related feature engineering example read before feature work. Parent: `67dc356`.

**010 outcome:** `7925b46`, Eval AUC **0.7577**, training 4.9s, evaluation 29.9s. **Discard**, -0.0013. The raw HHMM value seems sufficient under current tree settings.

## Synthesis after 10 experiments

Best: **0.7590**, `67dc356`, versus baseline 0.7203 (+0.0387). The important gains came from more boosting, explicit calendar date, and regularizing categorical splits before adding depth. Smaller boosting steps helped further. Route categories were strongly harmful; extra departure-hour/minute features did not help. Preparation simplification saved about one third of evaluation time without changing AUC.

Current theory: daily disruptions interact with airports and scheduled departure time, but high-cardinality partitions need careful regularization. Next explore smooth chronological and geographic representations that let nearby dates/airports share evidence; also investigate categorical one-hot splits and leaf-wise growth as alternative inductive biases.

Research refresh: searched official XGBoost docs on category partitioning and leaf-wise growth, and scikit-learn [Isomap](https://scikit-learn.org/stable/modules/generated/sklearn.manifold.Isomap.html) / [manifold learning](https://scikit-learn.org/stable/modules/manifold.html). Idea for later: embed an airport graph weighted by training route distances; use only distance values, never traffic counts. This is an experimental adaptation of shortest-path/MDS geometry.

### 011 — Numeric day of year

**Class:** follow-up to the explicit-date gain. **Hypothesis:** add an ordered day-of-year feature alongside the date category so adjacent days can share splits for seasonal and multi-day patterns. Use fixed non-leap calendar offsets, appropriate to the repository's stated year 2005. All operations are row-local. Parent: `67dc356`.

**011 outcome:** `0b8cb6c`, Eval AUC **0.7586**, training 4.8s, evaluation 30.9s. **Discard**, -0.0004; no benefit justifies retaining the extra feature.

### 012 — Airport geometry from training distances

**Class:** exploration, unsupervised feature family. **Hypothesis:** approximate airport coordinates permit regional daily patterns to generalize across different airports without an enormous route category. Build an undirected graph using median route Distance from train, fill missing pair distances with shortest paths, and use the leading three classical-MDS coordinates as origin and destination features. The training graph has 284 vertices and one connected component; no target values or traffic counts enter it. Fitting stays at module level and prepare only looks up coordinates.

Sources read: [scikit-learn manifold learning](https://scikit-learn.org/stable/modules/manifold.html) on graph distances and spectral embedding; [SciPy shortest_path](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.shortest_path.html). The regional-delay benefit is our hypothesis. Parent: `67dc356`.

**012 outcome:** `b7eda79`, Eval AUC **0.7590**, training 5.4s, evaluation 33.4s. **Discard** on the simplicity criterion: no measured gain justifies 25 extra lines and slower preparation. Batch/single-row consistency passed.

### Plateau research and 013 — One-hot categorical splits

Four feature explorations have failed to advance the best score. Revisited the official categorical tutorial and searched current primary documentation for alternative categorical splitting. The parameter max_cat_to_onehot can force one-category-versus-rest splits instead of learned category groups. Latest development docs mention a changed default; explicitly configure the installed version rather than relying on that default.

**Class:** exploration of categorical handling. **Hypothesis:** forcing one-hot splits (max_cat_to_onehot=512, above every retained feature cardinality) may avoid noisy multi-category groupings at the cost of needing more splits. Keep the same 600 rounds first to isolate split strategy. Parent: `67dc356`.

**013 outcome:** `85b73d3`, Eval AUC **0.7395**, training 4.5s, evaluation 26.2s. **Discard**, -0.0195. Grouped categorical splits carry useful signal; a tiny one-hot model underfits at the same boosting budget.

### 014 — Extend the regularized boosting path

**Class:** follow-up to 008. **Hypothesis:** the successful small-step model may still underfit; double rounds from 600 to 1200 at fixed learning rate 0.05 to test longer optimization separately from step size. Existing categorical and leaf regularization remain in place. Parent: `67dc356`.

**014 outcome:** `effe647`, Eval AUC **0.7569**, training 8.7s, evaluation 27.1s. **Discard**, -0.0021. More rounds at the same shrinkage now overfit; the prior gain from 600 smaller-step rounds was not just a need for an indefinitely longer path.

Additional research: read scikit-learn target-encoding guidance and the [CatBoost paper](https://proceedings.neurips.cc/paper/2018/hash/14491b756b3a51daac41c24863285549-Abstract.html). Target statistics can represent interactions but using an example's own label in its feature invites leakage. If explored later, use a disjoint training-only lookup subset; do not add cross-validation or change the evaluation metric.

### 015 — Smaller categorical partitions without forcing one-hot

**Class:** follow-up to 006. **Hypothesis:** max_cat_threshold=4 further regularizes high-cardinality groups while preserving multi-category grouping, unlike the poor one-hot experiment. This probes the useful region between unrestricted grouping and one-category splits. Parent: `67dc356`.

**015 outcome:** `cf762ee`, Eval AUC **0.7511**, Run time: 30.2s (training 4.1s, eval 26.1s, ok). **Discard**. AUC fell by 0.0079. Limiting groups this strongly underfits; restore the 16-category search cap.

### 016 — Stochastic row sampling

**Class:** exploration of stochastic boosting. **Hypothesis:** sampling 80% of training rows independently for each tree can reduce correlation and variance in the fitted category groups without forcing smaller partitions. Keep all columns and existing complexity controls. Research refresh: Friedman's Stochastic Gradient Boosting paper and the official XGBoost subsample documentation motivate row sampling. Parent: `67dc356`.

**016 outcome:** `4bc29e4`, Eval AUC **0.7540**, Run time: 31.6s (training 5.0s, eval 26.6s, ok). **Discard**. Sampling rows reduced AUC by 0.0050. Full-data category gradient estimates seem valuable here.

Stochastic boosting source: [Friedman, 2002](https://www.sciencedirect.com/science/article/pii/S0167947301000652).

### 017 — Leaf-wise tree growth

**Class:** exploration of tree structure. **Hypothesis:** lossguide growth with 128 leaves and no fixed depth cap can allocate capacity to difficult date/airport interactions more efficiently than uniformly limiting depth to 8. Keep shrinkage, categorical cap, and leaf support fixed. Source: official XGBoost grow_policy/max_leaves documentation. Parent: `67dc356`.

**017 outcome:** `7c6f0ae`, Eval AUC **0.7582**, Run time: 38.4s (training 11.4s, eval 27.1s, ok). **Discard**. AUC was 0.0008 lower, with longer training and a larger artifact. Keep depth-wise growth.

### 018 — Training-only early stopping

**Class:** exploration of training duration selection. **Hypothesis:** a 10% stratified split from train.csv can choose an appropriate boosting length instead of a fixed count; cap at 2000 rounds and stop after 75 rounds without internal AUC improvement. Fit once on the remaining 90%; do not retrain. Only harness Eval AUC determines keep/discard. Source: [XGBoost sklearn early-stopping guide](https://xgboost.readthedocs.io/en/stable/python/sklearn_estimator.html). Parent: `67dc356`.

**018 outcome:** `41b7f0c`, Eval AUC **0.7568**, Run time: 33.0s (training 6.4s, eval 26.6s, ok). **Discard**. AUC fell by 0.0022. The selected 597 rounds supports the existing 600-round choice, while fitting on fewer rows reduced accuracy.

### 019 — Honest airport-date target statistics

**Class:** exploration of supervised interaction features. **Hypothesis:** airport-by-date delay rates can capture local daily disruption patterns more directly than repeated categorical splits. Reserve a fixed random 25% of train.csv solely for fitting two smoothed delay-rate lookups; fit the XGBoost model once on the remaining 75%. Use five prior pseudo-observations at the lookup subset's global rate. This is one disjoint training split, not cross-validation, and there is no retraining or alternative scoring metric. Group sizes only regularize the target mean and are never emitted as features.

The [scikit-learn target encoding guide](https://scikit-learn.org/stable/modules/preprocessing.html#target-encoder) and CatBoost paper read earlier motivate separating target-statistic fitting from model fitting. Row features use fixed lookups and never consult the row's label. Parent: `67dc356`.

**019 outcome:** `03b87d8`, Eval AUC **0.7556**, Run time: 38.1s (training 4.6s, eval 33.5s, ok). **Discard**. AUC fell by 0.0034. The honest lookup features did not offset the loss of model-fitting rows. Disjointness, row consistency, and label independence were verified.

### 020 — Prepare categories from fitted indexes

**Class:** ablation/simplification of preparation. **Hypothesis:** fixed indexes can map each category directly to its code, with unseen values represented by -1, while constructing the DataFrame once avoids repeated column mutation. This removes implicit per-call category inference/validation and the deprecated unknown-value conversion. Expected identical features/AUC and reduced evaluation cost. No model changes. Parent: `67dc356`.

**020 outcome:** `c4f89d4`, Eval AUC **0.7590**, Run time: 16.1s (training 4.7s, eval 11.4s, ok). **Keep**. Feature equality to the saved best model passed, including unseen categories and single-row preparation. Evaluation dropped from about 26s to 11s and no deprecation warnings remain.

## Synthesis after 20 experiments

Best AUC remains **0.7590**; best implementation is now `c4f89d4` with substantially faster preparation. One-hot splits, tiny category groups, row subsampling, and longer boosting all hurt. Leaf-wise growth was a near miss. Early stopping selected 597 rounds, supporting the chosen 600. Honest target statistics did not compensate for reserving a quarter of training rows for lookup fitting. Airport geometry matched the best but was discarded because it added complexity without gain.

Current theory: accurate category gradient estimates from the full training set matter more than the tested extra features. The model already has enough boosting length; further gains may require better interaction structure or a different loss/ensemble rather than more rounds. Next explore additional depth, dropout, pairwise ranking, and controlled ensembles. All candidate metrics remain the original harness Eval AUC.

Research refresh at 20: official [DART tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) explains tree dropout and its extra training cost; official [learning-to-rank tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html) motivates pairwise loss for ordering. These are candidate directions, not assertions of improvement on these data.

### 021 — Depth 10 under existing regularization

**Class:** follow-up to 007. **Hypothesis:** the earlier gain from depth 6 to 8 may extend to depth 10, allowing more date/airport/time interactions. Unlike the leaf-wise experiment, preserve depth-wise growth and change only the cap. Keep 600 rounds to avoid the demonstrated long-path overfitting. Parent: `c4f89d4`.

**021 outcome:** `11e0d0d`, Eval AUC **0.7588**, Run time: 17.8s (training 6.2s, eval 11.7s, ok). **Discard**. AUC was 0.0002 below the best, with a larger model. Depth 8 remains the preferred capacity.

### 022 — Pairwise ranking loss

**Class:** exploration of training objective. **Hypothesis:** a pairwise ordering loss may align better with AUC than pointwise logistic loss. Train XGBRanker on one global training group, sampling two pairs per row with the mean pair strategy. Disable score-difference normalization to keep the plain pairwise loss; mean-pair normalization remains enabled. Keep features and tree settings fixed. A small wrapper sigmoid-transforms scores into two-column outputs for the unchanged save_and_evaluate call; this preserves their ordering and is not a calibration claim.

Read the official learning-to-rank tutorial and parameter details, including the mean-pair normalization behavior in installed XGBoost 3.x. Only the training objective changes; no ranking-based evaluation is added. Parent: `c4f89d4`.

**022 outcome:** `3b844c9`, Eval AUC **0.7511**, Run time: 45.5s (training 33.8s, eval 11.6s, ok). **Discard**. AUC fell by 0.0079 and training took 33.8s. Logistic loss remains preferable under these settings.

### 023 — Ordered airport-date target statistics

**Class:** exploration, informed by the failed disjoint-subset encoder. **Hypothesis:** ordered target statistics can retain all model-fitting rows while avoiding each row's own target. Read Section 3.2 of the CatBoost paper: simple leave-one-out can still expose an inverse label signal, so that idea was rejected before implementation.

Adapt the paper's ordering principle to the row-wise harness: use a deterministic hash of the eight input features (never label or DataFrame index) as a random order. Fit sorted hash/prefix-label-sum tables for each airport-date group. Every training or evaluation row uses only training hashes strictly smaller than its own; identical feature rows are excluded together. The same fixed lookup rule applies to individual rows and batches. Smooth with 20 prior observations at fixed probability 0.5. No cross-validation, auxiliary evaluation metric, or train/test-specific transform is used. Group support is only a denominator for the smoothed rate, never a count feature. Parent: `c4f89d4`.

**023 outcome:** `2d53ef5`, Eval AUC **0.7562**, Run time: 26.9s (training 6.9s, eval 20.0s, ok). **Discard**. AUC fell by 0.0028 despite full model-fitting data. The encoder passed batch/single-row equality and a refit-after-own-label-flip check, but adds noise and complexity without a gain.

### 024 — Boosted random forests

**Class:** exploration of ensemble structure, informed by 016. **Hypothesis:** average four independent 80%-row trees per boosting step; the group can recover information lost by a single sampled tree while reducing variance in category partitions. Keep 600 boosting steps and learning rate 0.05. This is one XGBoost model using num_parallel_tree=4, not additional evaluation or retraining. Source: official num_parallel_tree/subsample parameters. Parent: `c4f89d4`.

**024 outcome:** `7cfae02`, Eval AUC **0.7566**, Run time: 33.1s (training 20.3s, eval 12.8s, ok). **Discard**. AUC was 0.0024 below the full-row single-tree model. The 95 MB artifact and added training cost are not justified.

### 025 — Remove redundant day-of-month feature

**Class:** ablation/simplification of the date model. **Hypothesis:** once FlightDate is explicit, a standalone DayofMonth creates noisy cross-month groupings and unnecessary split competition. Remove it from the modeled columns while still using the raw field to form FlightDate. Month and weekday stay available for shared seasonal/weekly effects. Parent: `c4f89d4`.

**025 outcome:** `c7a4611`, Eval AUC **0.7598**, Run time: 15.4s (training 4.6s, eval 10.8s, ok). **Keep**. AUC improved by 0.0008 while removing a redundant feature. This is a straightforward simplification win.

### 026 — Remove standalone weekday

**Class:** ablation/simplification following 025. **Hypothesis:** in this single-year dataset, FlightDate also determines weekday, and removing the standalone field may reduce redundant split competition. This may instead hurt shared weekly patterns; the experiment tests that tradeoff directly. Parent: `c7a4611`.

Read official feature interaction constraints documentation while considering structural alternatives; overlapping constraint groups can have subtle expansion behavior, so no unverified claim of completely blocking route interactions is used.

**026 outcome:** `b31b9d4`, Eval AUC **0.7601**, Run time: 14.7s (training 4.5s, eval 10.2s, ok). **Keep**. AUC improved by 0.0003 with another feature removed. Calendar-date representation is sufficient for the retained weekly signal in this run.

### 027 — Remove standalone month

**Class:** ablation/simplification following 025–026. **Hypothesis:** FlightDate may also make Month redundant after enough boosting; removing the final separate calendar field tests whether direct seasonal pooling remains useful. Change only the modeled categorical column list. Parent: `b31b9d4`.

**027 outcome:** `43388fb`, Eval AUC **0.7589**, Run time: 13.7s (training 4.4s, eval 9.3s, ok). **Discard**. AUC fell by 0.0012. Month still provides useful seasonal pooling even though date contains the same raw information.

### 028 — Finer shrinkage after calendar simplification

**Class:** follow-up to 008 and 025–026. **Hypothesis:** lower learning_rate from 0.05 to 0.02 and raise rounds from 600 to 1500, preserving total step length. Smaller updates helped earlier; this tests whether that benefit continues with the simpler feature set. Unlike 014, this does not lengthen the nominal boosting path. Parent: `b31b9d4`.

**028 outcome:** `efd73ae`, Eval AUC **0.7600**, Run time: 20.9s (training 10.2s, eval 10.7s, ok). **Discard**. AUC was 0.0001 below the best, effectively tied, but the model is much larger and slower. Prefer 600 trees.

### 029 — Sample columns, retain all rows

**Class:** exploration of stochastic feature selection. **Hypothesis:** colsample_bytree=0.9 occasionally removes the dominant departure-time feature and encourages complementary date/airport splits, while every available category gradient still uses the full training sample. This differs materially from the failed row-sampling experiments. Parent: `b31b9d4`.

**029 outcome:** `781a911`, Eval AUC **0.7597**, Run time: 14.5s (training 4.4s, eval 10.1s, ok). **Discard**. AUC was 0.0004 below the best. Column sampling is a close alternative, but adds a parameter without measured benefit.

### 030 — Departure time relative to route schedule

**Class:** exploration of unsupervised schedule context. **Hypothesis:** the same departure clock time can mean early or late relative to a route's normal schedule; subtracting the training route median in true minutes provides that interaction without high-cardinality route categories. Fit only the route-median lookup on train; prepare performs row-local arithmetic and lookup. This adapts the permitted group-statistic example in program.md, using minutes rather than HHMM subtraction. Parent: `b31b9d4`.

**030 outcome:** `2f840a0`, Eval AUC **0.7592**, Run time: 18.6s (training 4.8s, eval 13.8s, ok). **Discard**. AUC fell by 0.0009 and preparation became slower. The context feature did not improve on raw departure time and airports.

## Synthesis after 30 experiments

Best: **0.7601**, `b31b9d4`, +0.0398 over baseline. Removing standalone day-of-month and weekday produced the recent gains; month still helps seasonal pooling. Pairwise ranking, ordered target statistics, boosted random forests, finer learning-rate steps, column sampling, and route-relative schedule time did not improve the score. Target-encoding consistency checks passed; those experiments were discarded for predictive performance, not implementation failures.

Current theory: a compact feature representation with native date/airport categories and full training data is strong. The remaining opportunity may be in how numeric split candidates and weak leaves are regularized, or in blending complementary models. Research refresh: reread official tree-method and DART tutorials. The tree-method guide explains global hist sketches versus per-tree Hessian-weighted approx sketches and suggests higher hist max_bin as a useful accuracy alternative. Plan to test numeric resolution, sparse leaf weights, and dropout before revisiting feature interactions.

### 031 — Finer numeric histogram bins

**Class:** exploration of split precision. **Hypothesis:** max_bin=1024, versus the default 256, may preserve useful distinctions among the roughly 1,200 unique departure-time and distance values without new features. Keep all other settings fixed. Source: [XGBoost tree methods](https://xgboost.readthedocs.io/en/stable/treemethod.html). Parent: `b31b9d4`.

**031 outcome:** `ed3d8bc`, Eval AUC **0.7594**, Run time: 14.6s (training 4.6s, eval 10.0s, ok). **Discard**. AUC was 0.0007 below the best. Finer numeric resolution did not help; retain the default 256 bins.

### 032 — Sparse leaf-weight regularization

**Class:** exploration of regularization. **Hypothesis:** reg_alpha=5 suppresses weak leaf updates driven by noisy categorical partitions while leaving stronger effects active. This changes leaf-weight shrinkage rather than group size, row support, or tree depth, all of which were already explored. Keep L2=10. Source: official XGBoost regularization parameters and its boosted-tree objective. Parent: `b31b9d4`.

**032 outcome:** `1644697`, Eval AUC **0.7673**, Run time: 14.4s (training 4.6s, eval 9.9s, ok). **Keep**. AUC improved by 0.0072, the largest gain since adding calendar date. The artifact also shrank from roughly 27 MB to 19.7 MB, consistent with suppressing weak category-driven updates.

### 033 — Stronger L1 shrinkage

**Class:** follow-up to 032. **Hypothesis:** the large gain from alpha=5 indicates weak gradient groups were overfitting; alpha=20 will test whether stronger sparsity continues to help or begins to underfit. All features, rounds, and other regularizers stay fixed, providing a coarse upper bracket rather than a small arbitrary tweak. Parent: `1644697`.

**033 outcome:** `0b45af6`, Eval AUC **0.7492**, Run time: 14.2s (training 4.3s, eval 9.9s, ok). **Discard**. AUC fell sharply to 0.7492. Strong L1 regularization removes useful signal; the useful regime is much lighter than 20.

### 034 — Lower L1 bracket

**Class:** ablation/follow-up to 032–033. **Hypothesis:** alpha=2 may retain more weak genuine daily effects while still addressing the noise seen with alpha=0. Together with the tested values 0, 5, and 20, this is a coarse bracket of the sparsity tradeoff; avoid an indiscriminate fine grid. Parent: `1644697`.

**034 outcome:** `6f06464`, Eval AUC **0.7644**, Run time: 14.6s (training 4.7s, eval 9.9s, ok). **Discard**. AUC 0.7644 improves on no L1 but remains below alpha=5. Keep the intermediate strength, with a clear coarse bracket established.

### 035 — Remove the extra leaf-support constraint

**Class:** ablation/simplification of 032. **Hypothesis:** with L1 shrinkage suppressing weak gradients, min_child_weight=20 may unnecessarily exclude small but strong local effects. Remove the explicit setting (return to XGBoost default 1) while retaining alpha=5 and lambda=10. This also isolates a component of the originally combined regularization change in 005. Parent: `1644697`.

**035 outcome:** `9f7c2be`, Eval AUC **0.7671**, Run time: 14.9s (training 4.9s, eval 9.9s, ok). **Discard**. AUC 0.7671 is nearly tied, but the artifact grew to 24.8 MB from 19.7 MB. Retain the support constraint for the smaller, slightly better model.

### 036 — Remove the extra L2 shrinkage

**Class:** ablation/simplification of 032. **Hypothesis:** L1 may now supply the necessary regularization, allowing reg_lambda to return from 10 to its default 1 and preserving stronger useful leaf effects. Keep min_child_weight=20 after the preceding ablation. This isolates the other part of experiment 005. Parent: `1644697`.

**036 outcome:** `cfa04e7`, Eval AUC **0.7669**, Run time: 14.4s (training 4.6s, eval 9.8s, ok). **Discard**. AUC fell by 0.0004 and the artifact was slightly larger. L2=10 remains useful alongside L1=5.

Training-model diagnostics (no alternative evaluation): the pre-L1 model had 44,303 leaves with one zero-valued leaf; alpha=5 had 55,400 leaves with 13,921 zero-valued leaves. L1 changes the fitted structure substantially and nulls many updates; artifact size alone is not a leaf-count measure.

### 037 — Penalize weak splits

**Class:** follow-up to 032. **Hypothesis:** gamma=2 may prune low-gain subdivisions left after L1 suppresses weak leaf weights. This regularizes the number of splits rather than coefficient magnitudes. Keep all prior regularization and compare both AUC and model size. Parent: `1644697`.

**037 outcome:** `1b1408a`, Eval AUC **0.7576**, Run time: 12.3s (training 2.6s, eval 9.7s, ok). **Discard**. AUC fell by 0.0097; hard split pruning removes useful small gains, unlike shrinking weak leaf weights. Restore gamma=0.

### 038 — Longer boosting with successful L1 regularization

**Class:** follow-up to 032. **Hypothesis:** alpha=5 changes the overfitting regime, so 1200 rounds at 0.05 may now capture useful residual effects where the unregularized longer run 014 failed. This is a deliberate retest under a materially changed regularizer, not a duplicate of 014. Parent: `1644697`.

**038 outcome:** `ac149df`, Eval AUC **0.7686**, Run time: 18.4s (training 8.1s, eval 10.3s, ok). **Keep**. AUC improved by 0.0013. L1 makes a longer boosting path useful, unlike experiment 014 without L1.

Research refresh: read the original [DART paper](https://proceedings.mlr.press/v38/korlakaivinayak15.pdf). It motivates reducing late-tree specialization; a dropout test remains a candidate, subject to the one-minute training cap.

### 039 — Deeper interactions with L1 and longer boosting

**Class:** follow-up to 038. **Hypothesis:** depth 10 can now capture additional supported interactions because alpha=5 filters weak leaf gradients. This revisits depth under materially stronger regularization and a validated longer path, rather than repeating 021. Parent: `ac149df`.

**039 outcome:** `c22e27f`, Eval AUC **0.7687**, Run time: 20.8s (training 10.2s, eval 10.6s, ok). **Keep**. AUC improved marginally by 0.0001. Keep as a simple parameter change, while noting that the gain is small and the model is larger.

### 040 — Calendar-date by departure-block category

**Class:** exploration of a targeted feature interaction under improved regularization. **Hypothesis:** a date × six-hour departure block category can distinguish days with afternoon/evening disruption from all-day effects more directly than separate splits. Its roughly 1,400 possible categories are far fewer than airport-date groups. Keep FlightDate and raw departure time, and fit composite levels only on train. Motivated by explicit time representations and the CatBoost paper's discussion of categorical feature combinations, adapted to this domain. Parent: `c22e27f`.

**040 outcome:** `ecc3312`, Eval AUC **0.7679**, Run time: 27.4s (training 13.5s, eval 13.9s, ok). **Discard**. AUC fell by 0.0008 and both training and preparation slowed. Keep the separate date and time inputs.

## Synthesis after 40 experiments

Best: **0.7687**, `c22e27f`, +0.0484 over baseline. The decisive discovery was L1=5, which improved 0.7601 to 0.7673. Alpha=2 was weaker and alpha=20 strongly underfit. Hard split pruning gamma=2 also underfit. Existing min-child support and L2 remain useful. With L1, extending to 1200 trees helped and depth 10 added a small further gain. An explicit date/time-block category did not help.

Theory update: useful signals include many weak splits, so hard pruning is harmful, while sparse leaf-weight shrinkage removes noisy updates. Additional boosting is useful once that shrinkage is present. Next test operational categorical combinations and dropout, then revisit ensemble averaging and adaptive learning rates under the successful regularization regime.

Research refresh at 40: searched the XGBoost implementation/documentation for ThresholdL1 and weight calculation, and primary papers on categorical combinations and regularized gradient boosting. The [XGBoost parameter source](https://github.com/dmlc/xgboost/blob/master/doc/parameter.rst) and CatBoost feature-combination discussion guide these follow-ups. Disk space check showed ample capacity; saved artifacts remain untouched.

### 041 — Carrier by origin airport category

**Class:** exploration of operational interactions. **Hypothesis:** carrier-specific operations at an origin airport may be easier to learn through one categorical combination. This has a different meaning and lower cardinality than the failed origin-destination route feature, and now benefits from L1 shrinkage. Fit levels on train only and apply the same row-local combination everywhere. Parent: `c22e27f`.

**041 outcome:** `3ecb385`, Eval AUC **0.7676**, Run time: 26.2s (training 13.1s, eval 13.0s, ok). **Discard**. AUC fell by 0.0011. Explicit operational categories were not better than the separate inputs under this model.

### 042 — Budget-aware DART dropout

**Class:** exploration of booster architecture. **Hypothesis:** occasional dropout (rate_drop=0.02, skip_drop=0.8) can reduce specialization of later trees. Because DART may replay tree predictions during training, use 300 rounds at learning_rate=0.2 rather than 1200 at 0.05; the nominal step sum is matched, though dropout changes the effective path. Keep depth and regularizers unchanged. This is a compute-constrained architecture trial, not a pure single-parameter comparison. Sources: original DART paper and official tutorial already read. Parent: `c22e27f`.

**042 outcome:** `392a968`, **crash / timeout-training** at 60.0s, no Eval AUC. Logged 0.0000 per protocol and discard the candidate. The installed library also recommends using dropout parameters directly on gbtree rather than the legacy dart booster name.

### 043 — Fit dropout within the time cap

**Class:** follow-up/fix to 042. **Hypothesis:** reducing dropout training to 160 rounds at 0.2 should cut its roughly quadratic prediction work substantially, while retaining a nominal path length comparable to the successful 600-round 0.05 model. Use the current gbtree dropout interface and the same rate/skip probabilities. This deliberately trades capacity for feasibility under the fixed one-minute limit. Parent: `c22e27f`.

**043 outcome:** `b4c1d4e`, Eval AUC **0.7656**, Run time: 43.0s (training 33.2s, eval 9.7s, ok). **Discard**. Training completed in 33.2s and AUC was 0.7656, below the best. The model is substantially smaller and may be a complementary ensemble component, but is not kept alone.

### 044 — Blend standard boosting with dropout

**Class:** follow-up to the feasible dropout trial. **Hypothesis:** dropout may make complementary errors despite lower standalone AUC. Fit the current best booster and the 160-round dropout model, then use a preselected 3:1 probability average favoring the stronger model. Expected combined training time is roughly 43s, within the cap. Both models fit the same train.csv rows; there is no extra evaluation or retraining on additional data. Use the installed sklearn VotingClassifier rather than a custom scoring implementation. Source: [VotingClassifier documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html). Parent: `c22e27f`.

**044 outcome:** `d2e10fe`, Eval AUC **0.7698**, Run time: 52.6s (training 41.7s, eval 10.9s, ok). **Keep**. AUC improved by 0.0011 over the strongest single model. Combined training took 41.7s, comfortably within the one-minute cap; artifact size is 55.2 MB.

### 045 — Equal-weight ensemble ablation

**Class:** ablation/follow-up to 044. **Hypothesis:** the clear gain from adding dropout suggests complementary errors; an equal-weight average tests whether its contribution should be larger while removing the explicit weight setting. This is one coarse comparison, not a fine weight search. Both constituent models are unchanged. Parent: `d2e10fe`.

**045 outcome:** `87b5d18`, Eval AUC **0.7696**, Run time: 53.1s (training 42.3s, eval 10.8s, ok). **Discard**. AUC was 0.0002 below the 3:1 blend. Removing one weight setting does not reduce model size or training cost, so retain the higher-scoring weighting.

### 046 — Hessian-adaptive numeric split candidates

**Class:** exploration of tree construction. **Hypothesis:** tree_method=approx can adapt numeric cut points as the logistic Hessian changes, unlike hist's single initial sketch. Test it as a single-model candidate with the strongest single-model settings; remove the voting wrapper for this trial. A competitive result could also inform a later blend. This is distinct from increasing static max_bin in 031. Source: official tree-method guide read at experiment 30. Parent: `d2e10fe`.

**046 outcome:** `d621679`, Eval AUC **0.7684**, Run time: 40.8s (training 30.1s, eval 10.7s, ok). **Discard**. AUC 0.7684 is close to the best single-model 0.7687 but below the kept ensemble. Training took 30.1s; it remains feasible as a complementary component.

### 047 — Blend global and adaptive histogram models

**Class:** follow-up to 046. **Hypothesis:** hist and approx have similar standalone AUC but different cut points and tree paths, so an equal probability average may improve ranking through complementary errors. Replace the dropout member with the approx model and remove explicit weights because component quality is nearly equal. Expected fit cost is around 40s. Parent: `d2e10fe`.

**047 outcome:** `d01ca36`, Eval AUC **0.7694**, Run time: 52.1s (training 40.3s, eval 11.8s, ok). **Discard**. AUC 0.7694 improved over either member but remained below the dropout blend, with a larger 94.3 MB artifact.

### 048 — Extend the main ensemble member

**Class:** follow-up to 038 and 044. **Hypothesis:** because L1 made 600→1200 rounds useful, 2400 rounds may capture additional residual signal in the main booster. Keep the dropout member explicitly at 160 rounds and preserve 3:1 weights. Estimated total training cost is about 50–55s, leaving a small but usable margin under the harness cap. Parent: `d2e10fe`.

**048 outcome:** `a6167e7`, Eval AUC **0.7678**, Run time: 62.8s (training 50.9s, eval 11.8s, ok). **Discard**. AUC fell to 0.7678 despite fitting within 50.9s. The main member now overfits; restore 1200 rounds.

### 049 — Blend two supported interaction depths

**Class:** exploration/simplification of ensemble composition. **Hypothesis:** depth-8 and depth-10 L1 models had nearly identical standalone AUC (0.7686 and 0.7687) but different tree paths. Average them equally to test useful diversity without expensive dropout. Both use 1200 rounds at 0.05. This should train much faster than the kept ensemble if it matches performance. Parent: `d2e10fe`.

**049 outcome:** `54bc4f9`, Eval AUC **0.7697**, Run time: 28.6s (training 17.3s, eval 11.3s, ok). **Keep**. Keep on the simplicity criterion: AUC 0.7697 is within 0.0001 of the 0.7698 peak, training drops from 41.7s to 17.3s, and dropout plus explicit blend weights are removed. Artifact grows to 80.4 MB, a noted tradeoff.

### 050 — Native averaged tree groups with all rows

**Class:** exploration/simplification of ensemble structure. **Hypothesis:** three feature-sampled trees per boosting step (num_parallel_tree=3, colsample_bynode=0.9) can reduce correlation while every tree still uses all training rows. Keep successful L1 and other regularizers. This differs from 024, which sampled rows and lacked L1. Remove the external voting wrapper for one native XGBoost model. Source: [Breiman's Random Forests paper](https://www.stat.berkeley.edu/users/breiman/randomforest2001.pdf) on tree strength/correlation and random split features, adapted here to boosted tree groups; no out-of-bag or other auxiliary evaluation is used. Parent: `54bc4f9`.

**050 outcome:** `8ba4da2`, Eval AUC **0.7686**, Run time: 49.2s (training 36.4s, eval 12.8s, ok). **Discard**. AUC 0.7686 trails the preferred 0.7697 blend while training and artifact size both increase.

## Synthesis after 50 experiments

Highest measured AUC is **0.7698** at `d2e10fe`; preferred simpler candidate is **0.7697** at `54bc4f9`, +0.0494 over baseline. Averaging complementary models consistently improves their standalone ranking: standard/dropout, hist/approx, and depth-8/depth-10 all helped relative to their components. The depth blend gives nearly the peak AUC at 17.3s training versus 41.7s. Doubling rounds to 2400 overfit; native feature-sampled groups did not outperform the external depth blend. New calendar/operational category combinations still failed under L1.

Theory: supported date, airport, carrier and departure-time interactions matter, while L1 filters noisy leaf updates. Averaging genuinely different tree paths adds modest value. Next combine the two demonstrated kinds of diversity, then test feature ablations and a learning-rate schedule. Research refresh: searched primary sources on shrinkage schedules and airline feature engineering; read the [XGBoost LearningRateScheduler API](https://xgboost.readthedocs.io/en/stable/python/python_api.html#xgboost.callback.LearningRateScheduler). It supports per-iteration schedules and requires fresh/deep-copied callbacks for each fit. Papers that use actual delay or unavailable operational/weather variables are not applicable to this task's inputs.

### 051 — Combine depth diversity with dropout diversity

**Class:** follow-up to 044 and 049. **Hypothesis:** a 25% contribution from the feasible dropout model can complement the equal depth-8/depth-10 mixture just as it complemented depth 10 alone in 044. Use fixed weights 3:3:2, preserving 25% dropout and equal ordinary members. Prior measured total training is about 50s, within the cap. All three members train on the same original train rows. Parent: `54bc4f9`. Sources: DART paper and VotingClassifier documentation cited above.

**051 outcome:** `fcfa068`, Eval AUC **0.7703**, Run time: 61.6s (training 50.0s, eval 11.6s, ok). **Keep**. AUC rose to 0.7703, exceeding both the preferred 0.7697 and prior peak 0.7698. The compact three-member specification fits in 50.0s including startup.

### 052 — Remove distance from the feature set

**Class:** ablation/simplification of 051. **Hypothesis:** origin and destination already identify geography, so raw distance may offer noisy extra splits rather than useful new information. Removing redundant calendar columns helped in 025–026; this tests a different redundancy. Keep all ensemble members and weights fixed. Parent: `fcfa068`.

**052 outcome:** `8a68d69`, Eval AUC **0.7694**, Run time: 62.9s (training 51.4s, eval 11.5s, ok). **Discard**. AUC declined from 0.7703 to 0.7694. Distance retains useful information even with both airport categories.

### 053 — Decay the ordinary boosters' learning rate

**Class:** exploration of optimization schedule, informed by 048. **Hypothesis:** larger early updates and smaller late updates can capture broad effects before refining residuals, without the overfitting observed from doubling constant-rate rounds. On each ordinary booster use an exponential schedule from 0.1 to 0.02 over 1200 rounds; its cumulative step size is about 59.7, close to the current 60. Keep dropout fixed. Instantiate a fresh callback for each member; VotingClassifier also clones members. Installed callback source confirms scheduling occurs after each iteration, so use epoch+1 for the next tree. Sources: [official callback API](https://xgboost.readthedocs.io/en/stable/python/python_api.html#xgboost.callback.LearningRateScheduler) and [Margins, Shrinkage, and Boosting](https://proceedings.mlr.press/v28/telgarsky13.html), which motivates shrinkage generally rather than this particular schedule. Parent: `fcfa068`.

**053 outcome:** `ad1bc55`, Eval AUC **0.7700**, Run time: 62.6s (training 51.2s, eval 11.4s, ok). **Discard**. AUC 0.7700 did not beat 0.7703 and the schedule adds callback complexity. Restore constant 0.05.

Read-only diagnostics of this run's `fcfa068` artifact: total training split gain assigns 36–38% to FlightDate and 21–22% to departure time across the three members. Distance receives 3–5%, yet its ablation hurt AUC; split importance is descriptive, not a replacement metric. No data was scored for these diagnostics.

### 054 — Ordered numeric month instead of a category

**Class:** exploration of calendar representation. **Hypothesis:** adjacent months can share seasonal effects more efficiently through ordered thresholds than free categorical partitions. Replace the Month category with its numeric 1–12 value, retaining FlightDate and every other feature. Unlike removing Month in 027, this preserves its seasonal information while changing the inductive bias. Month extraction is row-local. The official sklearn time-feature example previously read motivates testing encodings based on estimator behavior, not assuming one representation wins. Parent: `fcfa068`.

**054 outcome:** `7598565`, Eval AUC **0.7699**, Run time: 60.7s (training 48.7s, eval 12.0s, ok). **Discard**. AUC 0.7699 trails 0.7703, so flexible categorical month groups remain preferable.

Plateau refresh after three small discards: searched and read the official custom-objective guide and [When does label smoothing help?](https://proceedings.neurips.cc/paper/2019/hash/f1748d6b0fd9d439f71450117eba2725-Abstract.html). The latter studies neural networks; applying its confidence regularization to boosted logistic models would be an explicit hypothesis, not an established result for this dataset. Custom logistic derivatives and prediction-link handling need verification before that trial.

### 055 — Broader categorical partitions under L1

**Class:** follow-up to 006 and 032. **Hypothesis:** max_cat_threshold=32 can capture larger groups of dates or airports now that alpha=5 regularizes leaf updates. The 16-category threshold was selected on shallow unregularized 300-round models, so the regularization regime is materially different. Keep all other settings fixed across the three members. Source: [XGBoost categorical parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-categorical-feature). Parent: `fcfa068`.

**055 outcome:** `a1af349`, Eval AUC **0.7690**, Run time: 64.0s (training 52.3s, eval 11.6s, ok). **Discard**. AUC dropped to 0.7690. Broader categorical partitions still overfit despite L1; retain threshold 16.

### 056 — Mild label smoothing on the deepest ordinary member

**Class:** exploration of objective regularization. **Hypothesis:** mixing targets with 4% uniform label mass (0→0.02, 1→0.98) can temper confidence in the depth-10 member and provide useful ensemble diversity. Keep the depth-8 and dropout objectives unchanged to isolate the change and preserve the training-time margin. Implement logistic gradient p−soft_target and Hessian p(1−p); training/evaluation labels remain the original binary labels. Sources: [label-smoothing paper](https://proceedings.neurips.cc/paper/2019/hash/f1748d6b0fd9d439f71450117eba2725-Abstract.html) and [official custom-objective tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/custom_metric_obj.html). This adapts a neural-network regularizer to trees experimentally. Installed XGBClassifier source confirms callable objectives retain binary:logistic as the prediction link. Parent: `fcfa068`.

056 validation before fitting: analytic gradient and Hessian match centered finite differences on five synthetic margins and both labels, rtol=1e-6. No dataset metric was computed.

**056 outcome:** `e949585`, Eval AUC **0.7699**, Run time: 63.3s (training 51.6s, eval 11.7s, ok). **Discard**. AUC 0.7699 is lower than the kept 0.7703 and the custom objective adds code. Restore the built-in logistic objective.

Research refresh: revisited the official [DART tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) and original paper for dropout versus shrinkage. This suggests a missing causal ablation: the helpful third member differs in both dropout and its shorter, higher-rate boosting path.

### 057 — Remove dropout from the fast-learning member

**Class:** ablation/simplification of 051. **Hypothesis:** the third member's useful diversity may come mainly from its 160-round, 0.2-rate training path rather than dropout itself. Remove rate_drop and skip_drop while retaining its other settings and the 3:3:2 weights. This isolates the mechanism and should substantially reduce training time if performance holds. Rename that member to fast for clarity. Parent: `fcfa068`.

**057 outcome:** `54866e8`, Eval AUC **0.7701**, Run time: 30.4s (training 18.8s, eval 11.7s, ok). **Keep**. Keep as a simplification: AUC 0.7701 is within 0.0002 of peak 0.7703, training falls from 50.0s to 18.8s, and both dropout parameters plus its training mechanism are removed. Highest measured AUC remains fcfa068 at 0.7703.

### 058 — Leafwise growth for the main ensemble member

**Class:** exploration/follow-up under the improved regularization regime. **Hypothesis:** loss-guided growth with at most 128 leaves can devote depth to supported residual interactions without requiring every branch to share a depth ceiling. Change only the main ordinary member to grow_policy=lossguide, max_depth=0, max_leaves=128 after cloning the other two. Unlike 017, this retains alpha=5, uses the validated longer path, and tests contribution within a diverse ensemble. Sources: official tree-method and parameter documentation cited above. Parent: `54866e8`.

**058 outcome:** `5e5bb77`, Eval AUC **0.7698**, Run time: 39.4s (training 27.5s, eval 11.9s, ok). **Discard**. AUC 0.7698 trails the simpler 0.7701 depth-based ensemble, and training increases from 18.8s to 27.5s.

### 059 — Equal votes for the three ordinary boosters

**Class:** ablation/simplification of 057. **Hypothesis:** equal probability averaging may retain useful diversity while removing the remaining fixed weighting. The fast member now receives one third rather than one quarter; unlike 045, this is a three-member ordinary-boosting mixture rather than a two-member mixture with 50% dropout. Keep every fitted constituent unchanged. This is a single coarse simplicity test, not a fine search over weights. Parent: `54866e8`.

**059 outcome:** `aca8c2a`, Eval AUC **0.7700**, Run time: 31.2s (training 19.9s, eval 11.4s, ok). **Discard**. AUC was 0.7700 versus 0.7701. Removing one weight argument leaves model architecture and compute unchanged, so prefer the measured higher score.

### 060 — Logarithmic probability pooling

**Class:** exploration of ensemble aggregation. **Hypothesis:** averaging raw logistic margins can preserve confident complementary evidence that arithmetic probability averaging compresses. Keep the same three fitted models and 3:3:2 weights; apply sigmoid only after the weighted margin average. This is row-local and uses no batch ranks, calibration data or new selection metric. Source: [Heskes, Selecting Weighting Factors in Logarithmic Opinion Pools](https://proceedings.neurips.cc/paper_files/paper/1997/hash/59f51fd6937412b7e56ded1ea2470c25-Abstract.html). We use fixed existing weights, not the paper's weight-fitting procedures, and make no claim that its log-loss arguments guarantee higher AUC. Parent: `54866e8`.

060 validation: weighted margin pooling matches an independently computed normalized geometric pool on three synthetic examples; probability rows sum to one.

**060 outcome:** `55fc779`, Eval AUC **0.7701**, Run time: 30.5s (training 18.8s, eval 11.7s, ok). **Discard**. AUC tied 0.7701 to reported precision and training/evaluation costs were similar, so the additional custom class and imports are not justified.

## Synthesis after 60 experiments

Highest measured AUC remains **0.7703** at `fcfa068`; preferred simpler code is **0.7701** at `54866e8`, +0.0498 over baseline. The third member's short, high-rate boosting path provides most of the diversity previously attributed to dropout: removing dropout cuts training from 50.0s to 18.8s for only 0.0002 AUC. Distance remains useful. Numeric month, learning-rate decay, broader categorical partitions, label smoothing and leafwise main-model growth did not help. Logarithmic pooling tied ordinary probability voting while requiring extra code. The 3:3:2 blend slightly exceeded equal votes.

Theory update: the dominant practical gains come from date identity, restrained native categorical partitions, L1 regularization and averaging distinct boosting paths. More elaborate objectives and aggregation have not earned their complexity. Next try compact calendar pooling and a few genuinely different component capacities, with no fine-grained weight search. Research refresh: searched the official sklearn cyclical-feature example and primary flight-delay studies for supported calendar representations. Existing seven-category DayOfWeek was unhelpful before L1, but a pooled weekend indicator remains untested.

### 061 — Add a pooled weekend indicator

**Class:** exploration of a compact calendar feature. **Hypothesis:** a single Saturday/Sunday indicator shares broad schedule/congestion effects across dates with fewer degrees of freedom than the discarded seven-category DayOfWeek. Keep FlightDate and Month unchanged and derive the Boolean directly from each row's original DayOfWeek. This explicitly pools categories rather than restoring the removed feature unchanged. Source: [sklearn time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html), adapted to the existing weekday input. Parent: `54866e8`.

**061 outcome:** `77297f0`, Eval AUC **0.7704**, Run time: 31.9s (training 19.4s, eval 12.4s, ok). **Keep**. AUC improved from 0.7701 to 0.7704, also exceeding the prior overall peak 0.7703. The change is one feature line with essentially unchanged training cost.

061 validation: loaded only this run's saved artifact and verified exact batch/single-row feature and target equality on 12 training rows, including an artificial unseen origin. The unknown origin maps to categorical missing. No auxiliary metric was evaluated.

### 062 — Restore the weekday category alongside the pooled flag

**Class:** follow-up to 061. **Hypothesis:** the new weekend gain establishes useful weekday structure, and the stronger L1 regime may now support distinctions among weekdays beyond the pooled flag. Add native categorical DayOfWeek while retaining IsWeekend. Unlike 026, the model uses L1, longer boosting and the three-member average; this tests whether the earlier ablation result persists after those material changes. Parent: `77297f0`.

**062 outcome:** `f4305aa`, Eval AUC **0.7702**, Run time: 33.3s (training 20.3s, eval 13.0s, ok). **Discard**. AUC 0.7702 is below the simpler weekend-only 0.7704, and per-row preparation is slower.

### 063 — Coarser numeric histogram splits

**Class:** exploration of split-resolution regularization. **Hypothesis:** max_bin=64 can pool small departure-time/distance differences, reducing sensitivity to noisy fine cut points while leaving native categorical inputs available. The opposite move to 1024 bins failed in 031; coarsening has not been tested. Apply the setting consistently to all members. Source: [XGBoost tree-method guide](https://xgboost.readthedocs.io/en/stable/treemethod.html) on histogram cut construction. Parent: `77297f0`.

**063 outcome:** `c0c117c`, Eval AUC **0.7698**, Run time: 31.6s (training 19.3s, eval 12.3s, ok). **Discard**. AUC fell to 0.7698, showing useful fine numeric split information remains at the default resolution.

### 064 — Intermediate seven-day calendar blocks

**Class:** exploration of pooled calendar structure after 061. **Hypothesis:** a categorical seven-day block can share multi-day conditions more directly than separate dates, while retaining the precise FlightDate category for isolated events. Derive day-of-year from fixed non-leap-month offsets and the row's day, then block=(day_of_year−1)//7 with 53 fixed levels. These are January-1-aligned blocks, not ISO week numbers. Unlike 011, the new feature pools neighboring dates categorically and is tested under L1 and the ensemble. Source: official sklearn time-feature engineering example already researched. Parent: `77297f0`.

**064 outcome:** `96d190a`, Eval AUC **0.7693**, Run time: 36.8s (training 21.1s, eval 15.8s, ok). **Discard**. AUC 0.7693 is lower than 0.7704 and preprocessing is slower. Keep exact dates, month and the compact weekend indicator.

Research refresh after the feature plateau: revisited official XGBoost documentation on max_delta_step and disjoint feature-interaction constraints. Read-only inspection of this run's preferred saved models found maximum absolute unshrunk leaf updates of about 1.58. Only 0.17%, 0.22%, and 0.34% of leaf updates exceed 1 in the depth-10, depth-8, and fast members respectively; this makes a cap at 1 a targeted extreme-update test rather than broad shrinkage.

### 065 — Limit rare extreme leaf updates

**Class:** exploration of local update regularization. **Hypothesis:** max_delta_step=1 may stabilize the small number of unusually large leaf updates while leaving most steps unconstrained. Apply it to all members, retaining L1 and the existing learning rates. The training labels are balanced; the hypothesis concerns rare conditional leaves, not global class imbalance. Source: [XGBoost max_delta_step documentation](https://xgboost.readthedocs.io/en/stable/parameter.html). Parent: `77297f0`.

**065 outcome:** `c8d7879`, Eval AUC **0.7698**, Run time: 32.0s (training 19.7s, eval 12.3s, ok). **Discard**. AUC 0.7698 is lower than 0.7704; clipping even the rare largest leaf updates did not help.

### 066 — Finer steps for the short-path ensemble member

**Class:** follow-up to 057. **Hypothesis:** the third member's useful shorter boosting path can be retained while making its discretization less coarse: change 160 rounds × 0.2 to 320 rounds × 0.1, keeping the nominal step sum at 32. The two long-path members remain fixed. Those original third-member settings were chosen under dropout's training limit; ordinary boosting now permits this refinement cheaply. This distinguishes step size from path length rather than simply adding trees. Sources: XGBoost shrinkage guidance and the shrinkage paper already cited. Parent: `77297f0`.

**066 outcome:** `c66730c`, Eval AUC **0.7707**, Run time: 33.2s (training 20.8s, eval 12.4s, ok). **Keep**. AUC improved to 0.7707. Finer steps preserve the useful shorter path and cost only about 1.4s extra training.

### 067 — Finer steps on both long boosting paths

**Class:** follow-up to 066. **Hypothesis:** the same discretization refinement may improve the two long-path members: use 2400 rounds at 0.025 instead of 1200 at 0.05, preserving a cumulative step size of 60. Keep the short member explicitly at 320×0.1. Unlike 048, this does not double the path length; unlike 028, it uses the successful L1 regime and is motivated by a current positive result. Expected training is about 40s, within the cap. Parent: `c66730c`.

**067 outcome:** `5063e2a`, Eval AUC **0.7703**, Run time: 52.8s (training 38.6s, eval 14.2s, ok). **Discard**. AUC fell to 0.7703 while training nearly doubled and artifact size grew to 175 MB. Finer steps helped the short member but not the long members.

### 068 — Require more support for each leaf

**Class:** follow-up to 005 and 035. **Hypothesis:** min_child_weight=50 can suppress weakly supported residual partitions under the longer, L1-regularized boosting regime. The original value 20 was selected before L1, and removing that support requirement hurt in 035; raising it has not been tested. Keep the validated learning rates and path lengths fixed. This controls which leaves can form, distinct from clipping their output in 065. Source: official XGBoost parameter-tuning guide. Parent: `c66730c`.

**068 outcome:** `cb467a9`, Eval AUC **0.7697**, Run time: 32.3s (training 19.8s, eval 12.5s, ok). **Discard**. AUC fell to 0.7697. Stronger structural support reduced model size but suppressed useful interactions.

### 069 — Structured additive short-path member

**Class:** exploration of interaction constraints. **Hypothesis:** a more constrained short-path member may contribute less-correlated errors by separating calendar/airport interactions from time/carrier/distance/weekend interactions. Apply two disjoint feature groups only to the short-path model; the long-path models remain unrestricted. Use named features and cover all eight inputs. Disjoint groups are deliberate: the official guide shows overlapping groups can admit additional interactions, so no stronger exclusion claim is made for overlaps. Source: freshly reread [XGBoost interaction-constraint guide](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html). Parent: `c66730c`.

**069 outcome:** `22dfab8`, Eval AUC **0.7712**, Run time: 33.1s (training 20.4s, eval 12.7s, ok). **Keep**. AUC improved to 0.7712 with essentially unchanged training time. A constrained component complements the two unrestricted members.

### 070 — Apply the successful interaction prior to every member

**Class:** follow-up/ablation to 069. **Hypothesis:** the disjoint grouping may be a generally better inductive bias rather than only useful diversity. Move the same groups into the base classifier so both long members inherit them, and remove the short-member-only override. Features, rounds, weights and group definitions remain fixed. This directly distinguishes a universally useful constraint from a useful mixture of model biases. Parent: `22dfab8`.

**070 outcome:** `b14f550`, Eval AUC **0.7578**, Run time: 31.3s (training 19.2s, eval 12.1s, ok). **Discard**. AUC fell sharply to 0.7578. Cross-group interactions are essential in the main models; the constrained member helps through complementary bias, not as a universal replacement.

## Synthesis after 70 experiments

Best is now **0.7712** at `22dfab8`, +0.0509 over baseline, with 20.4s training and 12.7s evaluation. A pooled weekend flag helped, while restoring full weekday detail or adding calendar-week blocks did not. Finer steps improved the short member (320×0.1) but not the long members (2400×0.025). More leaf support and output clipping both hurt. The important late result is that disjoint interaction groups help only in the short member: constraining all three models collapses AUC to 0.7578. Useful cross-group interactions therefore remain essential, and the restricted component provides complementary regularization.

Research refresh at 70: searched primary sources on additive models and controlled interactions, including [Accurate Intelligible Models with Pairwise Interactions](https://www.microsoft.com/en-us/research/wp-content/uploads/2017/06/kdd13.pdf) and [Incorporating Grouping Information into Bayesian Decision Tree Ensembles](https://proceedings.mlr.press/v97/du19d.html). These support considering structured interaction priors but use different algorithms; our empirical mixture result is the justification for follow-ups here. In the remaining time, test the constrained component's path length and one deeper complementary member, then complete final artifact and scope checks.

### 071 — Extend the constrained member's boosting path

**Class:** follow-up to 069. **Hypothesis:** with far fewer allowed interactions, the constrained member may tolerate a longer path and capture more supported additive signal. Increase only its rounds from 320 to 640 at rate 0.1; retain its groups and 25% ensemble weight. The long unrestricted members remain at 1200×0.05. This tests path length after 066 separated the effect of step discretization. Parent: `22dfab8`.

**071 outcome:** `e13bf42`, Eval AUC **0.7711**, Run time: 36.6s (training 23.6s, eval 13.0s, ok). **Discard**. AUC 0.7711 is slightly below 0.7712 and training/artifact size increase. Retain the shorter constrained path.

### 072 — Add a modest deeper component

**Class:** exploration/follow-up to depth diversity in 049. **Hypothesis:** an unrestricted depth-12, 1200×0.05 member can contribute supported higher-order detail beyond depths 8 and 10, while the constrained component retains its complementary bias. Add it with preselected weight 2, giving 20% of the resulting 3:3:2:2 mixture and preserving the existing members' relative weights. No member is refit on additional data and no blend weights are optimized. Estimated total training remains below 40s. Parent: `22dfab8`.

**072 outcome:** `fd98cd0`, Eval AUC **0.7713**, Run time: 48.2s (training 33.9s, eval 14.2s, ok). **Discard**. AUC rose only 0.0001 to 0.7713, while training grew from 20.4s to 33.9s and artifact size from 92.8 to 154.4 MB. Keep the substantially cheaper three-member 0.7712 model under the simplicity criterion; record 0.7713 as the highest observed score.

### 073 — Use depth 12 instead of depth 10 for the main member

**Class:** follow-up/simplification of 072. **Hypothesis:** replacing the main long-path member with depth 12 can retain useful deeper detail without paying for a fourth model. Keep the depth-8 long member and explicitly preserve depth 10 for the constrained short member. All rounds and 3:3:2 weights remain fixed. This tests a wider two-depth spread rather than simply growing the ensemble. Parent: `22dfab8`.

**073 outcome:** `f537619`, Eval AUC **0.7710**, Run time: 37.1s (training 24.4s, eval 12.7s, ok). **Discard**. AUC 0.7710 trails 0.7712 and the replacement is slower and larger. Retain the depth-8/depth-10 unrestricted pair.

Research refresh after three small depth/path discards: searched the official categorical guide for selective one-hot versus partition splits. The early forced-one-hot trial affected every large categorical feature and failed badly; using the threshold only for low-cardinality Month has not been tested.

### 074 — Selective one-hot splitting for Month

**Class:** exploration of categorical handling. **Hypothesis:** max_cat_to_onehot=16 can regularize Month by isolating months instead of searching grouped month partitions, while leaving carrier (20), airports (~283) and dates (365) on native partition splits. Unlike 013's threshold 512, high-cardinality categorical handling remains intact. Weekend remains numeric. Source: [official categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html). Parent: `22dfab8`.

**074 outcome:** `44cf647`, Eval AUC **0.7705**, Run time: 32.6s (training 20.1s, eval 12.5s, ok). **Discard**. AUC 0.7705 is below 0.7712. Retain native partitioning for Month as well as the higher-cardinality features.

### 075 — Remove the shallower unrestricted member

**Class:** final ablation/simplification of 069. **Hypothesis:** the constrained member may now provide enough diversity to make the depth-8 member redundant. Remove depth 8 and allocate the original total unrestricted weight to depth 10, using a 3:1 blend so the constrained contribution remains 25%. This preserves the regularization mixture while reducing the model count and training cost. Parent: `22dfab8`.

**075 outcome:** `1b3dd0c`, Eval AUC **0.7707**, Run time: 25.4s (training 13.6s, eval 11.8s, ok). **Discard**. AUC fell from 0.7712 to 0.7707. The depth-8 member still provides useful diversity despite the constrained component; restore the three-member model.

Final verification before clock expiry: all 75 experiments have unique TSV entries; HEAD matches the latest kept commit `22dfab8`; only train.py differs among tracked files from the starting commit, and it has no uncommitted changes or whitespace errors. The last statement remains save_and_evaluate(model, prepare). Reloaded the final artifact and verified exact single-row/batch feature equality, matching predictions within 1e-6, finite normalized probabilities, unknown-airport handling, and the expected three-member 3:3:2 mixture on 16 training rows. No auxiliary performance metric was computed. Results and research logs remain uncommitted.

## Final summary — two-hour run complete

Branch: **oct2**. Completed **75 experiments**: 21 kept, 53 discarded, 1 training-timeout failure. The starting baseline was **0.7203**. The final preferred model is **0.7712** at **`22dfab8`**, a gain of **0.0509 AUC**. Its measured training time was **20.4s**, evaluation **12.7s**, and saved artifact **92.8 MB**.

The highest observed Eval AUC was **0.7713** at `fd98cd0`, but that four-member ensemble took 33.9s to train and occupied 154.4 MB. The extra 0.0001 was not worth the additional model; the branch is restored to the three-member candidate under the stated simplicity criterion.

What worked: exact FlightDate categories, stronger minimum-child/L2 settings, a restrained categorical partition threshold, especially L1=5, and a longer boosting path after L1. Removing redundant calendar categories and speeding up stable category encoding helped simplicity and evaluation cost. Late gains came from the pooled weekend flag, refining the short member's step size, and mixing two unrestricted models with one model using disjoint interaction groups.

Final model: two unrestricted classifiers of depths 10 and 8, each 1200 rounds at 0.05, plus a depth-10 constrained classifier with 320 rounds at 0.1. All share min_child_weight=20, reg_lambda=10, reg_alpha=5, max_cat_threshold=16. Soft votes use weights 3:3:2. The constrained groups are {FlightDate, Month, Origin, Dest} and {CRSDepTime, Distance, IsWeekend, UniqueCarrier}. Every member fits the original training rows.

What did not earn its cost: high-cardinality route/operational combinations, target-statistic variants, airport geometry, row sampling, forcing one-hot splits for large categories, ranking loss, broader partitions, custom label smoothing, learning-rate decay, output clipping, and several stricter structural regularizers. Dropout helped initially but ordinary short-path boosting captured most of its value far faster. Applying the interaction constraints to every model removed essential interactions and hurt strongly. Adding a fourth model produced only a negligible gain; removing the depth-8 member lost useful diversity.

Validation: every successful candidate was committed before the harness saved and evaluated it. Final artifact reload, batch/single-row equivalence, unknown-category handling, finite normalized probabilities, and code-scope checks passed. Only train.py has tracked changes; research-log.md, results.tsv, and harness timing remain uncommitted. The final model is left at the selected kept commit.

Next research directions: test a small number of domain-motivated disjoint groupings for the constrained component, or structured low-order components that retain selected time/airport interactions. Any follow-up should preserve the same data boundaries and use the harness metric; the tiny late AUC differences should not be treated as proof of generalization beyond this evaluation sample.
