# Research log: oct2

## Setup — 2026-10-02

- Branch: `oct2`, created directly from the current HEAD, `92e43e6`.
- Reviewed `program.md`, `README-autoresearch.md`, `train.py`, and `harness.py`.
- Verified `data/train.csv` and `data/eval.csv` exist. Only training data was inspected: 200,000 rows, all required columns present, no missing values, and 100,000 rows in each target class.
- Required imports succeeded: pandas 3.0.6, NumPy 2.5.3, XGBoost 3.4.1, scikit-learn 1.9.1, and cloudpickle 3.1.2. Python 3.14.4; 8 available CPUs.
- Initialized `results.tsv` with its header only. Run logs stay uncommitted.
- Baseline `train.py` is unchanged. No training or evaluation has run.
- Confirmed the experiment clock has not started. Setup is complete; launch awaits the user's confirmation, per `program.md`.

## Launch sequence

1. After confirmation, run `python3 harness.py start` as the first action.
2. Establish the unchanged baseline with `python3 harness.py run > run.log 2>&1`, then record its AUC and commit in `results.tsv`.
3. Research XGBoost tuning before the first non-baseline experiment; record sources, hypotheses, results, and keep/discard decisions here.
4. Follow the harness's two-hour budget and per-run limits: 60 seconds for training and 300 seconds for evaluation.

## Experiment 00 — baseline — 92e43e6

Unchanged starter: 30 trees, depth 6, learning rate 0.1, native categorical features. Eval AUC **0.7203**; training phase 1.1 s; evaluation 30.6 s. **Keep** as the initial reference. The experiment clock is now running.

## Initial research

Sources read before the first non-baseline experiment:
- [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html): capacity, regularization, subsampling, and learning-rate/round tradeoffs.
- [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html): depth, child Hessian thresholds, and categorical split controls.
- [Native categorical splits](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html): grouped category splits versus one-hot splits. Use installed-version behavior rather than assuming development-version defaults.
- [Time feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html): alternative time representations and nonlinear interactions.

Training-only inspection found 12 months, 31 days of month, 7 weekdays, 20 carriers, and 283 origins/destinations. Calendar fields have a `c-` prefix; departure time is numeric HHMM. Initial parameter exploration will use 300–1000 trees, depths 4–10, learning rates 0.03–0.1, and child weights 1–30, subject to measured runtime. These are proposed experiment ranges, not claims of universally optimal settings.

## Experiment 01 — exploration — more boosting rounds

Hypothesis: the baseline's 30 trees leave substantial signal unfitted. Increase to 300 trees, holding all other inputs and model parameters fixed. This isolates boosting duration before feature changes.

Result: **0.7342**, +0.0139 over baseline; training phase 2.6 s, evaluation 30.7 s. Commit `99ae626`, **keep**. More boosting clearly helps, with ample training headroom.

## Experiment 02 — follow-up — bracket boosting duration

Hypothesis: increasing from 300 to 900 trees at the same depth and learning rate will reveal whether the current gain continues or has reached an overfitting regime. This is a threefold capacity bracket, not a small round-count tweak. All other settings remain fixed.

Result: commit `d18f731`, AUC **0.7264** (−0.0078); training phase 5.9 s, evaluation 31.0 s. **Discard**. More boosting at this learning rate hurts generalization; retain 300 trees.

## Experiment 03 — ablation/simplification — remove redundant category filtering

Hypothesis: pandas Categorical already represents unseen values as missing when given fixed categories. Removing the preceding `isin`/`where` pass should preserve features exactly, simplify preparation, and reduce the cost repeated over 50,000 evaluation rows. Model parameters remain at the best 300-tree setting.

Result: commit `3e55c5b`, AUC **0.7342** unchanged, evaluation 20.8 s instead of 30.7 s; training phase 2.5 s. **Keep** for simpler code and faster evaluation. Pandas 3.0.6 emitted a deprecation warning for unseen category handling, but scoring succeeded with missing values. A future pandas upgrade would require adjusting this conversion; dependencies remain fixed here. [Pandas Categorical reference](https://pandas.pydata.org/docs/reference/api/pandas.Categorical.html).

## Experiment 04 — follow-up — regularize leaf estimates

Hypothesis: the deterioration with 900 trees suggests sensitivity to small noisy partitions. At 300 trees, set `min_child_weight=20` and `reg_lambda=10` to require more support per leaf and shrink leaf weights. This tests a conservative regularization regime before increasing capacity again. Source: the initial XGBoost parameter documentation.

Result: commit `b97ddae`, AUC **0.7357** (+0.0015), training phase 2.5 s, evaluation 21.0 s. **Keep**. Shrinking small-leaf effects helps.

## Experiment 05 — exploration — expose the calendar date

Hypothesis: month and day separately make individual dates expensive to isolate. Add day-of-year as both a numeric and categorical feature, allowing contiguous seasonal effects and date-specific groups. All flights are from 2005, so use the fixed non-leap-year month offsets; no new data or label-derived features are involved. Keep the regularized 300-tree model.

Research: [flight-delay feature engineering study](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0335141), section 3.4, describes departure-hour and day-of-year features. Only its pre-departure calendar idea is relevant here; its broader feature set and reported accuracy are not comparable to this experiment. The earlier scikit-learn time-feature example supports testing alternate temporal representations.

Result: commit `89bd73c`, AUC **0.7526** (+0.0169), training phase 2.6 s, evaluation 28.2 s. **Keep**. Calendar identity is a major missing representation. A training-only check confirmed exact batch/single-row feature equality on four separated rows; no alternative metric was computed.

## Experiment 06 — follow-up — deeper calendar interactions

Hypothesis: with explicit date features, depth 8 instead of 6 can capture date-by-airport and carrier interactions. Retain 300 trees, learning rate 0.1, child weight 20, and lambda 10; regularization should limit noisy small leaves. Source: XGBoost's capacity/regularization guidance already read.

Result: commit `562008d`, AUC **0.7495** (−0.0031), training phase 3.9 s, evaluation 28.6 s. **Discard**. Greater interaction depth hurts at this regularization level.

Inspection of the current best artifact (no evaluation data read) showed departure time and categorical FlightDate have the largest average training split gains. Numeric DayOfYear and DayOfWeek were unused. The installed categorical defaults are one-hot threshold 4 and category threshold 64.

## Experiment 07 — follow-up — constrain category groups

Hypothesis: native categorical partitions can fit noisy date/airport groupings. Reduce `max_cat_threshold` from 64 to 16 at depth 6, holding the remaining best settings fixed. This targets categorical split regularization rather than overall depth; the official parameter documentation specifically identifies this parameter as an overfitting control.

Result: commit `bee64a1`, AUC **0.7565** (+0.0039), training phase 2.2 s, evaluation 28.5 s. **Keep**. Restricting categorical group complexity helps more than increasing depth.

## Experiment 08 — follow-up — gentler boosting path

Hypothesis: halve the learning rate to 0.05 and double the number of trees to 600, holding the total learning-rate-times-rounds product constant. Smaller updates may select less noisy subsequent categorical splits. Keep depth 6, category threshold 16, child weight 20, and lambda 10. This differs from the discarded 900-tree run, which tripled total boosting strength without shrinkage.

Result: commit `f5ac956`, AUC **0.7568** (+0.0003), training phase 3.5 s, evaluation 28.4 s. **Keep**: small gain from a simple parameter change; runtime remains far below the limit.

## Experiment 09 — exploration — scheduled-hour and minute features

Hypothesis: represent departure hour as a fixed 24-level category and minute-within-hour numerically. This exposes recurring hour groups and schedule rounding without forcing splits on the entire HHMM value. Preserve raw departure time. Motivation: the time-feature examples and flight-delay study already read; no population counts or aggregates are used.

Result: commit `e0fb9cf`, AUC **0.7555** (−0.0013), training phase 3.7 s, evaluation 32.9 s. **Discard**; this representation adds complexity without a gain.

## Synthesis after 10 runs (00–09)

Best: **0.7568** at `f5ac956`, versus baseline 0.7203. More rounds initially helped, but excessive boosting and deeper trees hurt. Explicit calendar date produced the largest gain; restricting categorical groups and regularizing leaves helped further. Separate hour/minute features did not help. Current theory: broad temporal and airport/carrier effects matter, but flexible category groupings need restraint. Next, test meaningful categorical combinations, then ablate redundant features and consider stronger regularization or training-only early stopping.

New research: [CatBoost categorical-feature paper](https://arxiv.org/html/1810.11363), section 2, motivates feature combinations and explains why full-training-set target means can overfit. Its disjoint statistics/training split is a possible later alternative, while ordered training statistics would need careful compatibility with row-wise preparation. [XGBoost early-stopping interface](https://xgboost.readthedocs.io/en/stable/python/sklearn_estimator.html) describes using a validation subset and returning the selected model. Any such subset here must come from train.csv; the harness remains the sole experiment metric.

## Experiment 10 — exploration — route category

Hypothesis: origin–destination combinations can represent route-specific operating patterns directly, reducing the depth otherwise needed to isolate them. Fit route category levels on train and look them up within prepare. Keep the best regularized model and date features; use no target encoding or row counts. Motivation: the categorical-combinations research above.

Result: commit `e4bab9f`, AUC **0.7424** (−0.0144), training phase 6.7 s, evaluation 40.8 s. **Discard**. The high-cardinality route partitions overfit badly; retaining all low-support category combinations is not a promising default.

## Experiment 11 — ablation/simplification — cache categorical dtypes

Hypothesis: fixed pandas CategoricalDtype objects can be fitted once on train and reused with astype. Replace repeated category-list construction and the per-column conversion loop with a dtype mapping, preserving category order and missing-category behavior. Cache the fixed calendar dtype as well. This also avoids the constructor's pandas 4 deprecation path. Keep the best model and feature set unchanged.

Result: commit `a2dbfd9`, AUC **0.7568** unchanged, training phase 3.6 s, evaluation 21.6 s versus 28.4 s. **Keep**: four fewer lines and lower runtime. Batch/single-row equality and a synthetic unseen-origin check passed. Contrary to the hypothesis, astype still emitted the constructor deprecation warning during harness evaluation; the speed/simplicity benefit stands, but future-version compatibility is not resolved.

## Experiment 12 — exploration — individual airport/carrier splits with grouped dates

Hypothesis: set `max_cat_to_onehot=300`. The 283 airports and 20 carriers then use individual-category splits, while 365 date categories retain grouped splits. This removes noisy arbitrary airport groupings without depriving the model of flexible date groupings. Category threshold 16 still regularizes date splits; other best parameters remain fixed. Source: official XGBoost categorical split documentation.

Result: commit `a7becee`, AUC **0.7539** (−0.0029), training phase 3.1 s, evaluation 21.1 s. **Discard**. Airport/carrier category groups remain useful; complete individualization is too restrictive at this model capacity.

## Experiment 13 — exploration — shallow additive interactions

Hypothesis: depth 4 trees can reduce interaction overfitting, with 1000 rounds at learning rate 0.05 allowing their simpler effects to accumulate. This contrasts with both deeper trees and simply lengthening the original depth-6, learning-rate-0.1 model. Keep child weight 20, lambda 10, and category threshold 16.

Result: `0763cc2`, AUC **0.7540**, **discard**. Run time: 25.2s (training 3.8s, eval 21.4s, ok) Simpler trees lose useful interactions despite more rounds.

## Experiment 14 — exploration — Test stochastic row and feature subsampling

Hypothesis: At the best depth-6 model, subsample=0.8 and colsample_bytree=0.8 may make trees less dependent on noisy observations and dominant features. This tests stochastic regularization, motivated by the XGBoost tuning guide, while preserving boosting duration and leaf constraints.

Result: `b14fe4f`, AUC **0.7511**, **discard**. Run time: 25.2s (training 3.8s, eval 21.4s, ok) Stochastic regularization lost useful signal. Plateau research reviewed [interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html), [monotonic constraints](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html), and target-encoding leakage. Training-only hourly target means are nonmonotonic at the day boundaries, so a raw-time monotonic constraint is not justified.

## Experiment 15 — ablation/simplification — Remove redundant calendar features

Hypothesis: FlightDate already identifies month, day, and weekday. Earlier training split gains showed little or no use of these separate columns. Remove Month, DayofMonth, DayOfWeek, and numeric DayOfYear from model inputs, keeping them available in raw data solely to construct FlightDate. This tests a smaller feature set with fewer opportunities for noisy splits.

Result: `53bffff`, AUC **0.7564**, **keep**. Run time: 20.5s (training 3.3s, eval 17.2s, ok) Accepted the 0.0004 tradeoff for four fewer model inputs and evaluation reduced from 21.6 to 17.2 s. Highest observed AUC remains 0.7568 at a2dbfd9; current simpler reference is 0.7564.

## Experiment 16 — exploration — Select boosting duration using training-only early stopping

Hypothesis: Use a stratified 10% subset of train.csv for early stopping, 3000 maximum rounds, and 100-round patience on AUC. Keep the fitted 90%-training model without retraining. This tests whether the fixed 600-round schedule misses the best stopping point. Source: https://xgboost.readthedocs.io/en/stable/python/sklearn_estimator.html . Only harness Eval AUC determines the result.

Result: `8ca3c97`, AUC **0.7565**, **discard**. Run time: 21.8s (training 4.6s, eval 17.1s, ok) A 0.0001 increase does not justify 12 extra lines and withholding 10% of training rows; retain the simpler full-training model.

## Experiment 17 — follow-up — Bracket categorical group size with threshold four

Hypothesis: The move from max_cat_threshold 64 to 16 helped substantially. Test 4 to bracket a much more restrictive regime and determine whether still smaller groups improve generalization or start underfitting. All other best settings stay fixed.

Result: `420593e`, AUC **0.7411**, **discard**. Run time: 20.3s (training 2.9s, eval 17.4s, ok) The large decrease brackets threshold 16 as substantially better than an extremely restrictive grouping regime.

## Experiment 18 — exploration — Fit airport date delay lookups on a disjoint training subset

Hypothesis: Allocate 35% of train.csv exclusively to fit smoothed Origin-Date and Dest-Date delay means, then fit XGBoost on the remaining 65%. Ten pseudo-observations at prior 0.5 regularize each lookup. No counts are model features, no evaluation rows or labels are read, and no training row contributes to its own label-derived features. A single fixed lookup is used for both batch and single-row preparation. This tests localized date effects without the self-label bias discussed in https://arxiv.org/html/1810.11363 .

Result: `4fda463`, AUC **0.7530**, **discard**. Run time: 27.7s (training 3.7s, eval 24.0s, ok) The lookup benefits did not offset withholding 35% from model fitting. Checks confirmed disjoint row indices, exact batch/single-row equality, and feature independence from input labels.

## Experiment 19 — follow-up — Use deterministic ordered airport date target statistics

Hypothesis: Adapt the ordered target-statistics idea from https://arxiv.org/html/1810.11363 to row-wise inference. Hash only the eight original input fields into a stable ordering. For each airport-date key, fit sorted training hashes and cumulative labels; prepare uses only hashes strictly below the current row's hash. Equal-hash duplicates are excluded together. Thus all rows can train the model without self-label leakage; new rows use the identical rule. Smoothed rates use a 0.5 prior with weight 10. No row counts are exposed as features and no cross-validation or additional metric is introduced.

Result: `c44f59c`, AUC **0.7556**, **discard**. Run time: 43.4s (training 9.2s, eval 34.2s, ok) Passed batch/single-row equality, label independence, and strict self-hash exclusion, but adds substantial complexity without an AUC gain.

## Synthesis after 20 runs (00–19)

Current simpler reference: 0.7564 at 53bffff; highest raw AUC: 0.7568 at a2dbfd9. Route groups, deeper/shallower trees, subsampling, and target-statistic variants failed to improve the reference. Early stopping selected 742 rounds but gave only 0.0001 gain with extra machinery. Strong regularization of category groups helps up to a point; threshold 4 underfits badly. Focus next on allocating tree capacity more selectively, stronger leaf shrinkage, and low-cardinality structural features.

Research refresh: official tree-growth parameter documentation and the original [XGBoost paper](https://arxiv.org/abs/1603.02754) motivate a leaf budget and gain-based growth. The [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines lossguide and max_leaves.

## Experiment 20 — exploration — Allocate tree capacity by gain with a fixed leaf budget

Hypothesis: Use grow_policy=lossguide, max_depth=0, and max_leaves=31 to allocate splits to the most useful branches while capping total leaves. This can model uneven airport/date interactions without the broad depth-8 expansion that overfit. Hold rounds and other regularization fixed.

Result: `43ae874`, AUC **0.7547**, **discard**. Run time: 21.9s (training 4.6s, eval 17.2s, ok) Selective leaf allocation did not improve the depthwise reference.

## Experiment 21 — exploration — Derive airport geometry from observed route distances

Hypothesis: Fit a weighted airport graph using only median route Distance from train.csv, complete distances with undirected shortest paths, and derive three classical-MDS coordinates. Add fixed origin and destination coordinate lookups inside prepare. These smooth structural features may support regional date effects without arbitrary high-cardinality route groups. No labels, traffic counts, external airport data, or new dependencies are used. Sources: https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.shortest_path.html and https://scikit-learn.org/1.9/modules/manifold.html .

Result: `ac2f9c5`, AUC **0.7580**, **keep**. Run time: 31.1s (training 3.9s, eval 27.3s, ok) A new highest AUC, +0.0016 over the simpler reference. The fitted structural features improve generalization without using targets or external data.

## Experiment 22 — ablation/simplification — Test two-dimensional airport geometry

Hypothesis: Remove the weakest geometric dimension by fitting two rather than three coordinates, reducing airport-location features from six to four. If the third dimension mainly captures graph-distance distortion, the smaller representation may preserve or improve the gain.

Result: `a253045`, AUC **0.7581**, **keep**. Run time: 28.2s (training 4.3s, eval 23.9s, ok) Two fewer features slightly improve AUC and lower evaluation time. The discarded third coordinates had low training split gains.

## Experiment 23 — follow-up — Expose route direction in learned airport coordinates

Hypothesis: Add destination-minus-origin displacement along the two fitted geometry axes. These row-local differences expose route direction to individual splits instead of requiring multiple splits on separate endpoints. Keep both endpoint coordinates and the original distance.

Result: `de2fb56`, AUC **0.7577**, **discard**. Run time: 30.9s (training 3.9s, eval 27.0s, ok) The small decrease gives no reason to keep two extra features.

## Experiment 24 — follow-up — Strengthen leaf regularization for the geometry model

Hypothesis: Triple min_child_weight from 20 to 60 and reg_lambda from 10 to 30. The new continuous geometry features introduce more candidate splits; stronger support and shrinkage requirements may control that added flexibility while retaining regional effects.

Result: `ef886b6`, AUC **0.7565**, **discard**. Run time: 28.2s (training 3.7s, eval 24.6s, ok) Broadly increasing leaf support and shrinkage removes useful signal.

## Experiment 25 — exploration — Prune weak splits using a minimum gain

Hypothesis: Set gamma=2 while restoring child weight 20 and lambda 10. This targets splits with weak loss improvement rather than shrinking every leaf or requiring larger groups. The geometry model may benefit from selective pruning of noisy late splits.

Result: `88183f2`, AUC **0.7504**, **discard**. Run time: 27.9s (training 3.5s, eval 24.4s, ok) The pruning threshold removes useful weak splits. A new research pass reviewed spatial-temporal delay modeling (https://arxiv.org/abs/2207.06959) and fixed KMeans grouping (https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html). Those works motivate a representation experiment, not a claim that their reported results apply here.

## Experiment 26 — exploration — Add geographic region by date categories

Hypothesis: Fit eight KMeans groups on the training-derived two-dimensional airport coordinates, then add OriginRegion-Date and DestRegion-Date categories. Regional groups pool airports with similar geometry and may express localized date effects with better support than individual airport-date groups. The groups use neither labels nor traffic counts; all category levels and lookups are fixed before prepare.

Result: `dd54658`, AUC **0.7545**, **discard**. Run time: 38.9s (training 6.7s, eval 32.3s, ok) The high-cardinality region-date categories do not improve the continuous geometry representation.

## Experiment 27 — exploration — Average four randomized trees at each boosting round

Hypothesis: Use num_parallel_tree=4, subsample=0.8, and colsample_bynode=0.8 for 600 boosting rounds. This combines boosting with within-round averaging. Unlike the discarded single-model subsampling experiment, averaging offsets sampling variance and node-level feature sampling does not remove departure time from an entire tree. Source: https://xgboost.readthedocs.io/en/stable/tutorials/rf.html .

Result: `c6d93cd`, AUC **0.7517**, **discard**. Run time: 41.7s (training 16.3s, eval 25.4s, ok) Averaging did not recover the signal lost to row/node subsampling; training was also much slower.

## Experiment 28 — exploration — Express departure time relative to the route median

Hypothesis: Fit a median scheduled departure minute for each route on train.csv and add the row's departure time minus that fixed median. This captures whether a flight is early or late within its route's schedule without exposing route identity or traffic counts. The technique is explicitly illustrated in program.md; all per-row transformation remains inside prepare.

Result: `ed46edb`, AUC **0.7576**, **discard**. Run time: 33.1s (training 3.9s, eval 29.2s, ok) The route schedule offset adds runtime and complexity without improving AUC.

## Experiment 29 — exploration — Train XGBoost with a pairwise ranking objective

Hypothesis: Optimize sampled binary-label ordering using XGBRanker rank:pairwise, mean pair sampling, one pair per row, and one query containing all training rows. Start with 400 rounds at learning rate 0.05; ranking gradients differ from classifier gradients. A small wrapper applies a monotonic sigmoid and returns two columns for the unchanged harness interface. No new metric or evaluation data is introduced. Sources: https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html and its ranking-parameter reference.

Result: `0f4ef8f`, AUC **0.7290**, **discard**. Run time: 41.7s (training 17.6s, eval 24.2s, ok) The ranking objective performs poorly with its default score normalization and noisy single-pair updates.

## Synthesis after 30 runs (00–29)

Best: 0.7581 at a253045. Training-derived airport geometry is the only substantive gain in this block, and two dimensions beat three. Direction features, regional date categories, schedule offsets, stronger regularization, and boosted random forests did not help. Preserve the compact geometry model. Ranking is one new objective family under investigation; the first test underfit badly. A targeted follow-up will distinguish gradient normalization/noise from an unsuitable loss, then return to simpler feature and boosting changes.

Research refresh: XGBoost's ranking guide and the original [RankNet paper](https://www.microsoft.com/en-us/research/publication/learning-to-rank-using-gradient-descent/) explain pairwise optimization. The parameter docs identify score normalization as a possible convergence obstacle.

## Experiment 30 — follow-up — Test unnormalized ranking scores with more sampled pairs

Hypothesis: For the same 400-round ranker, disable lambdarank_score_normalization and increase pairs per sample from 1 to 4. These changes directly target two identified weaknesses: score-dependent attenuation and stochastic gradient variance. Mean-method pair-count normalization remains enabled so gradient scale is comparable. This is a bounded follow-up to the failed ranking category, not a change to evaluation.

Result: `fe7ea46`, AUC **0.7456**, **discard**. Run time: 55.9s (training 31.7s, eval 24.2s, ok) Better than the first ranker but still far below logistic loss, with 31.7 s training. Close this objective family rather than adding more complexity.

## Experiment 31 — follow-up — Pair continuous day of year with airport geometry

Hypothesis: Reintroduce numeric DayOfYear alongside categorical FlightDate. It was unused before geometry was added, but geographic coordinates may enable useful contiguous date-by-region partitions and seasonal interactions. This is a one-feature test in the changed representation.

Result: `b3d7cd0`, AUC **0.7577**, **discard**. Run time: 28.8s (training 3.8s, eval 25.0s, ok) Contiguous calendar values did not improve the categorical-date geometry model.

## Experiment 32 — exploration — Learn additive effects before fitting tree interactions

Hypothesis: Fit 800 depth-1 trees at learning rate 0.1 to establish broad additive effects, then continue the same booster with 400 depth-6 trees at 0.05. Both stages use exactly the same train.csv rows; there is no intermediate evaluation or retraining on more data. This may regularize the decomposition of global effects and interactions. Source: XGBoost training-continuation documentation.

Result: `b75f328`, AUC **0.7517**, **discard**. Run time: 28.2s (training 4.1s, eval 24.1s, ok) The staged decomposition fits useful interactions less effectively than ordinary boosting.

## Experiment 33 — follow-up — Test a low learning rate with matched boosting strength

Hypothesis: Use 3000 rounds at learning rate 0.01 instead of 600 at 0.05. The fivefold smaller step tests a meaningfully more gradual optimization path while keeping their product at 30. Geometry and categorical regularization stay fixed; measured training headroom permits this within 60 seconds.

Result: `a334308`, AUC **0.7581**, **discard**. Run time: 39.9s (training 14.6s, eval 25.3s, ok) Equal AUC with five times as many trees and 14.6 s rather than about 4 s training gives no simplification benefit.

## Experiment 34 — follow-up — Revisit depth eight with geometry and restricted category groups

Hypothesis: Test depth 8 in the current geometry model with category threshold 16. The earlier depth-8 failure used threshold 64 and no geometry; both controls have materially changed. More interaction capacity may now capture regional date patterns without the earlier arbitrary category-group overfitting.

Result: `fcddab2`, AUC **0.7601**, **keep**. Run time: 29.4s (training 4.9s, eval 24.5s, ok) New best, +0.0020. Revisiting depth was justified by the changed representation and categorical regularization; the earlier failure did not transfer to this setting.

## Experiment 35 — follow-up — Bracket interaction capacity at depth ten

Hypothesis: Increase depth from 8 to 10 while preserving all other settings. Depth 8 now improves the geometry model; this larger capacity bracket will test whether useful regional-date interactions continue to benefit or whether overfitting returns.

Result: `1eda83d`, AUC **0.7596**, **discard**. Run time: 30.8s (training 6.3s, eval 24.5s, ok) Depth 8 is the better capacity setting; two additional levels slightly reduce AUC.

## Experiment 36 — ablation/simplification — Encode categories explicitly with fixed training indexes

Hypothesis: Use fixed category indexes to obtain codes and construct Categoricals via from_codes. Unseen values receive code -1 explicitly, preserving missing-value handling without pandas' deprecated out-of-category constructor path. Model inputs, category order, and settings remain identical; test AUC and preparation time.

Result: `6828f89`, AUC **0.7601**, **keep**. Run time: 26.2s (training 5.0s, eval 21.2s, ok) Evaluation fell from 24.5 to 21.2 s. Batch/single-row equality and warning-free unseen-category handling passed; harness evaluation emitted no deprecation warning.

## Experiment 37 — exploration — Increase histogram resolution for numerical features

Hypothesis: Raise max_bin from 256 to 1024. Scheduled time and Distance have more than 1000 distinct values, and geometry coordinates have roughly 283. Finer numeric cuts may recover useful boundaries now that deeper trees can exploit them; the tradeoff is additional computation. Source: XGBoost max_bin documentation.

Result: `16b4f35`, AUC **0.7602**, **keep**. Run time: 26.8s (training 5.1s, eval 21.7s, ok) A very small improvement from a single parameter, with essentially unchanged runtime.

## Experiment 38 — ablation/simplification — Test coarse numerical bins as a smoothing constraint

Hypothesis: Compare max_bin=64 with the best 1024-bin model. Coarse cuts pool nearby schedule times and geometry values, potentially reducing variance while the original airport categories retain fine identity information. This brackets the numerical-resolution tradeoff rather than making a cosmetic nearby adjustment.

Result: `7ec80d6`, AUC **0.7591**, **discard**. Run time: 26.7s (training 4.8s, eval 21.9s, ok) Coarser numeric resolution loses about 0.0011 AUC; retain 1024 bins.

## Experiment 39 — follow-up — Restore coarse calendar groups alongside exact date

Hypothesis: Add Month and DayOfWeek as fixed categorical inputs. Unlike numeric DayOfYear, these explicitly pool repeated seasons and weekdays. They were weak before geometry/deeper trees, but may now stabilize broad regional-calendar interactions while FlightDate handles specific dates.

Result: `a87e0d2`, AUC **0.7598**, **discard**. Run time: 28.9s (training 5.2s, eval 23.7s, ok) The extra calendar categories slightly reduce AUC and increase preparation time.

## Synthesis after 40 runs (00–39)

Best: 0.7602 at 16b4f35, versus baseline 0.7203. Depth 8 helped once paired with geometry and restricted category groups; depth 10 did not. Finer numeric bins gave a small gain. Explicit fixed category codes preserved AUC, removed warnings, and sped evaluation. Ranking, additive warm starts, slower learning, and calendar reintroductions did not improve the reference. This block confirms that parameter effects depend on the feature representation.

Research refresh: [Rotation Forest](https://pubmed.ncbi.nlm.nih.gov/16986543/) retains feature information while varying axes to create accurate, diverse tree models. The author's PDF fetch failed, but the indexed author-hosted text and paper abstract were available. Adapt only the axis-orientation/diversity idea to the fitted airport geometry; this is not a full Rotation Forest implementation.

## Experiment 40 — exploration — Rotate airport geometry axes by forty-five degrees

Hypothesis: Apply a fixed orthogonal 45-degree rotation to the two fitted geometry coordinates before constructing airport lookups. Distances and information are preserved, but axis-aligned tree splits gain different regional boundaries. This tests an identifiable representation change and may yield a useful complementary model for averaging.

Result: `cd0cd0c`, AUC **0.7596**, **discard**. Run time: 26.2s (training 5.0s, eval 21.2s, ok) Slightly worse standalone, but a close-performing representation may provide useful diversity in a fixed-weight ensemble.

## Experiment 41 — follow-up — Average original and rotated geometry models

Hypothesis: Fit two XGBoost classifiers on all training rows with identical parameters, one using original geometry axes and one using the 45-degree axes, then average probabilities equally. Prepare emits both fixed coordinate systems; the model only selects its trained columns. This tests rotation-induced diversity without data subsampling, weight tuning, extra validation, or changing the harness metric.

Result: `bf27c54`, AUC **0.7611**, **keep**. Run time: 37.3s (training 9.1s, eval 28.2s, ok) A 0.0009 gain with a standard fixed-weight ensemble, training 9.1 s and evaluation 28.2 s. Keep provisionally while testing whether one model can capture the same gain more simply.

## Experiment 42 — ablation/simplification — Use both geometry orientations in one classifier

Hypothesis: Retain the original and rotated coordinate features but fit one XGBoost classifier to all of them. This removes the two-member wrapper and separate fits. If complementary boundaries explain the ensemble gain, one model may retain it with simpler training and prediction.

Result: `2ce6298`, AUC **0.7599**, **discard**. Run time: 33.3s (training 5.8s, eval 27.5s, ok) Combining features in one model loses the ensemble gain; separate fitted models provide useful diversity.

## Experiment 43 — follow-up — Average four evenly spaced geometry orientations

Hypothesis: Extend the successful two-view ensemble to four orientations: 0, 22.5, 45, and 67.5 degrees (stored as 0,45,22.5,67.5 to preserve the original pair). All models use full training data, identical parameters, and equal weights. This tests whether broader axis diversity reduces variance further without adding a different modeling algorithm.

Result: `66936dd`, AUC **0.7611**, **discard**. Run time: 57.6s (training 17.4s, eval 40.3s, ok) No improvement over two views; training nearly doubled and evaluation rose to 40.3 s. Retain the smaller ensemble.

## Experiment 44 — exploration — Add airline origin operating context

Hypothesis: Add a fixed native categorical Carrier-Origin feature. Airline-specific airport operations may be easier to learn as one category than as repeated two-feature interactions. This has fewer combinations than Origin-Dest routes and a different operational meaning. Include all non-geometry prepared features in both ensemble members; all levels are fitted only on train.

Result: `38e6fc3`, AUC **0.7552**, **discard**. Run time: 40.6s (training 10.1s, eval 30.5s, ok) The additional high-cardinality combination overfits. Plateau research revisited L1 versus L2 leaf regularization in the official parameter reference.

## Experiment 45 — exploration — Apply L1 shrinkage to weak leaf updates

Hypothesis: Set reg_alpha=5 in both ensemble members. L1 shrinkage targets small leaf updates differently from the discarded gamma pruning and increased minimum leaf support. The chosen scale tests a substantive penalty while retaining the successful tree depth, L2 weight, and category threshold. Source: https://xgboost.readthedocs.io/en/stable/parameter.html .

Result: `43a9ff4`, AUC **0.7678**, **keep**. Run time: 37.4s (training 9.4s, eval 28.0s, ok) A substantial +0.0067 improvement. L1 shrinkage works much better here than the previously tested global support increase or gamma pruning.

## Experiment 46 — exploration — Test gradient-aware row sampling on the L1 model

Hypothesis: Set sampling_method=gradient_based and subsample=0.5 with hist trees. Current installed-version documentation supports this on CPU. Importance-aware sampling may retain informative gradients better than the failed uniform-sampling experiments, while L1 continues to suppress weak leaf updates. Preserve all feature columns and ensemble members. Source: https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster .

Result: `2f07758`, AUC **0.7625**, **discard**. Run time: 42.4s (training 14.3s, eval 28.2s, ok) Supported on this CPU build, but lower AUC and slower training than using all rows.

## Experiment 47 — follow-up — Bracket L1 regularization at alpha twenty

Hypothesis: Increase reg_alpha from 5 to 20, holding the successful full-data ensemble fixed. Alpha 5 produced a large gain; a fourfold stronger penalty will distinguish further noise suppression from loss of useful weak effects.

Result: `19903c8`, AUC **0.7511**, **discard**. Run time: 36.6s (training 8.4s, eval 28.2s, ok) A large drop confirms that very strong L1 suppression underfits; retain alpha 5.

## Experiment 48 — ablation/simplification — Test a single geometry model with L1 regularization

Hypothesis: Repeat the single-model, both-orientations simplification with alpha 5. The earlier pooled-feature model failed without L1; the large new regularization gain may now control its extra split choices. If comparable, remove the ensemble wrapper and second fit.

Result: `90f645e`, AUC **0.7675**, **keep**. Run time: 33.2s (training 5.5s, eval 27.8s, ok) Accept a 0.0003 tradeoff for removing 20 lines, one fitted model, and nearly half the training cost. Highest raw AUC remains 0.7678 at 43a9ff4; simpler current reference is 0.7675.

## Experiment 49 — follow-up — Allow smaller supported leaves under L1 shrinkage

Hypothesis: Reduce min_child_weight from 20 to 5 while retaining alpha 5. L1 now suppresses weak gradient updates, so the larger Hessian floor may unnecessarily block localized date-airport effects. This tests finer supported interactions under the newly effective regularization regime.

Result: `992bae4`, AUC **0.7670**, **discard**. Run time: 33.5s (training 5.8s, eval 27.6s, ok) The smaller support floor still adds harmful fine-scale variation.

## Synthesis after 50 runs (00–49)

Highest observed AUC: 0.7678 at 43a9ff4. Current simpler reference: 0.7675 at 90f645e, with one classifier instead of two and 20 fewer lines. L1 alpha 5 was the decisive gain (+0.0067 in the ensemble); alpha 20 underfit. Gradient-aware CPU sampling, carrier-origin combinations, four orientations, and smaller supported leaves did not help. A single model with both geometry views now nearly matches the ensemble, so prefer it while continuing research.

Research refresh: [XGBoost leaf-weight implementation](https://raw.githubusercontent.com/dmlc/xgboost/master/src/tree/param.h) shows L1 thresholding in both weight and gain calculations, while the parameter reference distinguishes category-group limits from leaf penalties. Next test their interaction rather than treating the pre-L1 category limit as fixed.

## Experiment 50 — follow-up — Retest larger category groups with effective L1 regularization

Hypothesis: Increase max_cat_threshold from 16 to 64 in the single alpha-5 model. L1 materially changed the useful model capacity, so larger date/airport partitions may now capture broader effects without their former overfitting. This revisits a control under a substantially changed regularization regime.

Result: `75b94fe`, AUC **0.7667**, **discard**. Run time: 33.9s (training 6.0s, eval 27.9s, ok) L1 reduces the harm of larger groups but threshold 16 remains better. Source inspection also shows L1 can influence categorical weight sorting, giving a plausible mechanism for its large effect.

## Experiment 51 — ablation/simplification — Measure the remaining value of airport geometry under L1

Hypothesis: Remove all graph/MDS geometry and keep the six core inputs: departure time, distance, carrier, origin, destination, and exact date. Preserve the current depth-8, alpha-5, 1024-bin model and explicit category coding. L1 may have reduced the need for structural proxies; a comparable score would justify removing the graph construction and extra dependencies.

Result: `b8c3fd5`, AUC **0.7661**, **discard**. Run time: 19.4s (training 4.5s, eval 14.9s, ok) The 0.0014 loss is enough to retain geometry despite the faster 14.9 s evaluation.

## Experiment 52 — ablation/simplification — Keep only the original airport coordinate axes under L1

Hypothesis: Retain the fitted two-dimensional airport geometry but remove the rotated copies, reducing eight coordinate features to four. Full geometry removal hurt; this narrower ablation measures whether the second orientation still helps in the L1-regularized single model.

Result: `a9cb749`, AUC **0.7673**, **keep**. Run time: 26.4s (training 5.2s, eval 21.3s, ok) Accept a 0.0002 tradeoff for four fewer features and evaluation reduced from 27.8 to 21.3 s. The current model is now one classifier with one coordinate system.

## Experiment 53 — follow-up — Extend boosting duration with L1 control

Hypothesis: Increase rounds from 600 to 1200 at learning rate 0.05. L1 significantly changed the overfitting behavior, so the pre-L1 stopping regime may be too short. This tests a twofold duration increase while keeping the simpler feature set and all regularization fixed.

Result: `abb5dbc`, AUC **0.7697**, **keep**. Run time: 30.5s (training 8.8s, eval 21.7s, ok) New best, +0.0024 over the simpler 600-round model and above all earlier ensembles. L1 permits a longer useful boosting path.

## Experiment 54 — follow-up — Bracket the longer L1 boosting regime at 2400 rounds

Hypothesis: Double rounds again from 1200 to 2400 at the same learning rate and regularization. The first duration increase improved AUC substantially; this wider bracket will locate whether additional residual learning helps or overfits.

Result: `e1bea75`, AUC **0.7688**, **discard**. Run time: 38.6s (training 16.1s, eval 22.5s, ok) Longer boosting has a limit: 1200 rounds outperform 2400.

## Experiment 55 — follow-up — Locate the boosting peak between 1200 and 2400 rounds

Hypothesis: Test 1800 rounds, the midpoint of the bracket established by a strong gain at 1200 and a decline at 2400. This is a deliberate refinement of the duration optimum, not an unmotivated round-count variation.

Result: `2c77ae4`, AUC **0.7694**, **discard**. Run time: 34.3s (training 12.4s, eval 21.9s, ok) The duration bracket favors 1200 rounds; stop refining round count for now.

## Experiment 56 — follow-up — Test depth ten in the effective L1 regime

Hypothesis: Increase depth from 8 to 10 at 1200 rounds and alpha 5. Previous depth-10 testing lacked L1 and used shorter boosting. The changed regularization may allow finer regional-date interactions without its previous overfitting.

Result: `7b9f9f0`, AUC **0.7694**, **discard**. Run time: 33.4s (training 11.5s, eval 21.9s, ok) Depth 8 remains better. Three nearby non-improvements triggered a research pause. The [DART documentation](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) describes randomly omitting trees during boosting to limit overfitting; prediction-buffer loss makes it slower. The original [DART paper](https://proceedings.mlr.press/v38/korlakaivinayak15.pdf) motivates less reliance on earlier trees.

## Experiment 57 — exploration — Test light tree dropout within the training budget

Hypothesis: Use DART with 400 rounds at eta 0.15 (the same nominal total shrinkage as 1200 at 0.05), rate_drop 0.02, skip_drop 0.95, and forest normalization. This is a budget-conscious test of modest tree dropout, not a direct isolation of the dropout parameter: fewer larger steps are needed because DART recomputes predictions. Source: https://xgboost.readthedocs.io/en/stable/tutorials/dart.html .

Result: `af1dfd6`, AUC **0.0000**, **crash**. Run time: 60.0s (training 60.0s, eval 0.0s, timeout-training) As the official tutorial warns, dropout inference recomputation is too costly here. Do not reduce to a clearly underfit token run. The best model's training-only split-gain inspection ranks exact date highest (23.17), then origin (12.88), destination (10.69), and departure time (9.34); this is descriptive training evidence, not an additional performance metric.

## Experiment 58 — exploration — Anneal the learning rate while preserving total shrinkage

Hypothesis: Replace constant eta 0.05 over 1200 rounds by linear decay from 0.08 to 0.02 over the same rounds. Equal total shrinkage separates trajectory from the failed longer-duration tests. Large early steps capture broad effects; smaller late steps may avoid overly specific residual corrections. The [LearningRateScheduler API](https://xgboost.readthedocs.io/en/stable/python/python_api.html#xgboost.callback.LearningRateScheduler) supports this directly. Inspected installed callback code: it runs after each iteration, so epoch+1 selects the next round's rate.

Result: `bdbf3ec`, AUC **0.7692**, **discard**. Run time: 30.9s (training 9.1s, eval 21.8s, ok) Linear annealing did not improve the constant-eta path. Keep the simpler constant schedule.

## Experiment 59 — follow-up — Test weaker L1 shrinkage at the established boosting duration

Hypothesis: Reduce alpha from 5 to 2 at 1200 rounds, leaving all other parameters fixed. Alpha 5 produced the largest recent gain, alpha 20 underfit at the earlier 600-round duration, and zero was much worse. This tests the unmeasured lower half of the bracket under the established longer duration.

Result: `98561d0`, AUC **0.7630**, **discard**. Run time: 31.2s (training 9.5s, eval 21.6s, ok) A substantial 0.0067 drop confirms that alpha 5's gain was not merely incidental to an arbitrary nonzero penalty.

## Synthesis after 60 experiments (00–59)

The current best is `abb5dbc`, AUC 0.7697: one depth-8 classifier with alpha 5, 1200 constant-rate rounds, exact-date categories, and one two-dimensional airport embedding. Removing rotated coordinate copies preserved almost all score and reduced evaluation time. Increasing duration beyond 1200 or depth beyond 8 did not help; DART exceeded training time, linear annealing was weaker, and alpha 2 lost substantial score. The large L1 effect remains the strongest active lead. Next test a stronger L1 penalty with sufficient rounds, then investigate structural regularization if the bracket fails. New research: [interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html) can prevent spurious interactions, but overlapping groups may allow extra features through unions; a meaningful test must use carefully chosen disjoint groups. Installed booster configuration confirms no additional categorical smoothing control is exposed.

## Experiment 60 — follow-up — Test stronger L1 shrinkage with the longer boosting budget

Hypothesis: Increase alpha from 5 to 10 at 1200 rounds. Alpha 2 was materially worse, while alpha 20 was previously tested only at 600 rounds. This brackets the higher side with adequate boosting time before considering more complex feature changes.

Result: `8faa7a9`, AUC **0.7655**, **discard**. Run time: 30.1s (training 8.4s, eval 21.7s, ok) The 0.0042 decline establishes a peak between the tested lower and higher penalties.

## Experiment 61 — follow-up — Resolve the upper half of the L1 bracket

Hypothesis: Test alpha 7.5 between the successful value 5 and the underfitting value 10. This is the final planned L1 bracket refinement; values 2 and 10 both lost substantially, so any remaining useful adjustment should be close to 5.

Result: `fe21070`, AUC **0.7678**, **discard**. Run time: 31.1s (training 9.5s, eval 21.7s, ok) No benefit from the intermediate stronger penalty. Stop refining alpha: 5 is the established setting.

## Experiment 62 — exploration — Separate regional date effects from route and carrier effects

Hypothesis: Use two disjoint interaction groups: date, departure time and airport coordinates for shared regional/time effects; carrier, airport identities and distance for route operations. This tests whether unconstrained deep date-by-airport-ID interactions overfit. Groups are deliberately disjoint to avoid the union behavior documented at https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html . It may underfit genuine airport-specific shocks, which is the hypothesis this experiment will resolve.

Result: `232df74`, AUC **0.7551**, **discard**. Run time: 30.6s (training 8.7s, eval 21.9s, ok) A large loss shows that the current representation needs joint date/time/airport/carrier interactions. Geometry cannot replace airport-specific event interactions under this decomposition. Installed ClassicalMDS source also confirms deterministic full eigendecomposition and sign fixing.

## Experiment 63 — follow-up — Test smaller categorical partitions under effective L1 control

Hypothesis: Reduce max_cat_threshold from 16 to 8 at the established alpha 5 and 1200 rounds. Threshold 64 lost under L1, while threshold 4 was previously tested without L1. Smaller candidate partitions can limit noisy category groups without excluding entire feature interactions, unlike the failed disjoint constraint experiment. Source: XGBoost parameter documentation on max_cat_threshold.

Result: `3fd58d9`, AUC **0.7676**, **discard**. Run time: 30.3s (training 8.4s, eval 21.9s, ok) Threshold 16 remains better; fewer candidate categories underfit useful date/airport groupings.

## Experiment 64 — follow-up — Measure whether L2 shrinkage is redundant after adding L1

Hypothesis: Reduce lambda from 10 to 1 while retaining alpha 5. The current lambda was selected before the large L1 improvement. Since L1 suppresses small-gradient leaves, strong L2 may now unnecessarily shrink useful leaves; varying lambda alone distinguishes this from the earlier joint child-weight/lambda change. Source: https://xgboost.readthedocs.io/en/stable/parameter.html .

Result: `fa6b546`, AUC **0.7694**, **discard**. Run time: 30.9s (training 8.9s, eval 22.0s, ok) L2 shrinkage is still mildly useful alongside L1, so retain lambda 10.

## Experiment 65 — follow-up — Retest coarse calendar structure in the L1 regime

Hypothesis: Restore Month and DayOfWeek as categorical inputs while retaining exact FlightDate. Earlier calendar additions were evaluated without the now-critical L1 penalty. Small-cardinality features can expose month/weekday effects without requiring many date categories in one split; L1 may control the redundant interactions better. This is a changed-regime follow-up to experiments 15 and 39, informed by the scikit-learn cyclical feature engineering example.

Result: `f68f28e`, AUC **0.7706**, **keep**. Run time: 34.0s (training 9.7s, eval 24.3s, ok) New best, +0.0009 for one line and two calendar features. The changed-regime revisit was justified: coarse calendar splits now complement exact date under L1, whereas they did not previously.

## Experiment 66 — ablation/simplification — Measure whether weekday alone explains the calendar improvement

Hypothesis: Remove Month while retaining DayOfWeek and exact FlightDate. This isolates whether weekly grouping explains the gain and tests a simpler feature set before keeping both additions.

Result: `c3c0f26`, AUC **0.7693**, **discard**. Run time: 33.0s (training 10.1s, eval 22.9s, ok) Month matters in the joint calendar representation; weekday alone is insufficient.

## Experiment 67 — ablation/simplification — Measure whether month alone explains the calendar improvement

Hypothesis: Restore Month and remove DayOfWeek, keeping exact date and all other features. This complementary ablation identifies whether weekly grouping adds value after the failed weekday-only experiment.

Result: `01f46a0`, AUC **0.7693**, **discard**. Run time: 32.2s (training 9.4s, eval 22.8s, ok) Both single-feature calendar ablations score 0.7693, below the joint 0.7706. Keep Month and DayOfWeek together.

## Experiment 68 — exploration — Embed airport distances as spherical chords

Hypothesis: Replace the flat two-dimensional embedding by a three-dimensional chord-distance embedding. Convert training-derived graph path lengths d to chord lengths 2R sin(d/(2R)), with fixed Earth radius R=3958.8 miles. Training LAX–JFK distance is 2475, consistent with miles. This approximates Earth's curvature without fetching geographic data. [Universal MDS](https://users.cs.utah.edu/~jeffp/papers/sphericalMDS.pdf) distinguishes geodesic and chordal distances; this is a simple classical-MDS adaptation, not the paper's full iterative spherical algorithm.

Result: `85eb0b5`, AUC **0.7704**, **discard**. Run time: 38.6s (training 11.0s, eval 27.7s, ok) Close to the retained score but slightly worse and two extra features. A dimension ablation will distinguish curvature from the added axis.

## Experiment 69 — ablation/simplification — Remove the extra axis from the spherical geometry

Hypothesis: Keep the chord-distance conversion but return to two MDS components, matching the incumbent's four geographic features. The three-axis result was close; this isolates the new distance representation from the extra feature dimension.

Result: `6ce9e07`, AUC **0.7695**, **discard**. Run time: 33.8s (training 9.5s, eval 24.2s, ok) Neither chordal variant improves the original geometry, so retain the simpler distance representation.

## Synthesis after 70 experiments (00–69)

The best is now `f68f28e`, AUC 0.7706. L1 has a clear useful middle range; alpha 2, 7.5 and 10 all lose to 5. Removing necessary feature interactions causes a large decline. Smaller category groups and weaker L2 do not help. Restoring Month and DayOfWeek together improves the L1 model, while either alone loses the gain. Spherical geometry is competitive but not better. Current theory: broad calendar structure, exact-date shocks and airport/carrier interactions all matter; moderate regularization lets them coexist. Research read during this block: [Universal MDS](https://users.cs.utah.edu/~jeffp/papers/sphericalMDS.pdf) for distance geometry and [CatBoost](https://arxiv.org/html/1810.11363) for ordered categorical combinations. Next investigate carrier-by-date ordered target statistics, a denser combination than the earlier airport-by-date features.

## Experiment 70 — exploration — Add ordered carrier-date delay statistics

Hypothesis: Fit a smoothed carrier-by-exact-date delay rate using only training rows whose stable raw-feature hash strictly precedes the query hash. Exclude every equal hash, including the query itself and duplicate raw rows. Apply the same prefix rule during training and evaluation so single-row inference is unchanged. Unlike earlier airport-date statistics, carrier-date groups pool across the carrier's network and should estimate common disruptions with less variance. Use fixed prior 0.5 and strength 10; emit only a rate, never counts. Source: https://arxiv.org/html/1810.11363 .

Result: `f2db3ff`, AUC **0.7644**, **discard**. Run time: 49.6s (training 11.3s, eval 38.3s, ok) Feature-only checks passed batch/single-row equality, independence from input labels, strict exclusion of the query training label from prefix sums, and unseen-key fallback. The AUC loss and extra inference cost reject this feature.

## Experiment 71 — follow-up — Revisit two-view averaging with the improved base learner

Hypothesis: Average two classifiers trained on the original and 45-degree rotated airport coordinates, now with 1200 rounds and Month/DayOfWeek in each. Two-view averaging helped before the duration and calendar improvements; the stronger base learner may retain useful diversity. Reuse the earlier clean ensemble implementation and current parameters. If this helps, ablate to the rotated member alone before accepting the extra model.

Result: `ca87690`, AUC **0.7712**, **keep**. Run time: 48.9s (training 18.0s, eval 30.9s, ok) New raw best, +0.0006. Temporarily retain the straightforward averaging model while immediately testing whether the rotated member alone can preserve the gain with half the model size and fewer features.

## Experiment 72 — ablation/simplification — Test the rotated member alone

Hypothesis: Use only the classifier with the 45-degree rotated two-dimensional airport coordinates, with the same calendar and regularization settings. The ensemble gain might be mostly attributable to this representation; a near-equal result would justify deleting the ensemble wrapper and second classifier.

Result: `e3a804b`, AUC **0.7698**, **discard**. Run time: 33.9s (training 9.6s, eval 24.4s, ok) The weaker individual rotated member still improves the average. Retain both views: the gain reflects complementary errors rather than a uniformly superior rotation.

## Experiment 73 — exploration — Sample candidate features independently at each tree node

Hypothesis: Set colsample_bynode=0.8 in both geometry members while keeping all rows. Earlier sampling changed rows and whole-tree columns together. Node-level feature sampling allows important calendar/airport features to reappear deeper in each tree and may create useful diversity without wholly omitting them from 20% of trees. The official XGBoost parameter documentation distinguishes the three column-sampling levels.

Result: `0f6bd05`, AUC **0.7713**, **keep**. Run time: 50.0s (training 19.0s, eval 31.0s, ok) A small +0.0001 improvement from one parameter; retain without claiming statistical certainty from the rounded AUC.

## Experiment 74 — exploration — Test row sampling with scale-matched regularization

Hypothesis: Use uniform subsample 0.8 in the two-view ensemble, while scaling alpha 5→4, lambda 10→8 and min_child_weight 20→16. Uniform sampling zeros unselected gradient pairs without inverse-probability rescaling in the [upstream implementation](https://raw.githubusercontent.com/dmlc/xgboost/master/src/tree/hist/sampler.cc). Since expected gradient/Hessian sums scale by 0.8, scaling penalties preserves their approximate strength. This isolates stochastic rows from the unintentional stronger regularization in earlier sampling tests; hold node-level column sampling fixed.

Result: `82728c9`, AUC **0.7674**, **discard**. Run time: 52.6s (training 21.3s, eval 31.2s, ok) Loss of 0.0039 despite matching expected penalty scale. Keep full training rows; stochastic category estimates appear less useful than node-level feature sampling here.

## Experiment 75 — follow-up — Extend the improved calendar ensemble to 1800 rounds

Hypothesis: Increase rounds from 1200 to 1800 in the two-view, node-sampled ensemble. The earlier 1800-round loss was in the single original-view model without Month/DayOfWeek or column sampling. The newer representation and randomized split candidates may need a longer path; test one wider duration before further feature work.

Result: `1dac5a0`, AUC **0.7707**, **discard**. Run time: 58.9s (training 27.2s, eval 31.8s, ok) The earlier duration conclusion survives the calendar and sampling improvements.

## Experiment 76 — ablation/simplification — Replace the two-member average by one model with both views

Hypothesis: Train one classifier on both original and rotated coordinate columns, using the current 1200 rounds, calendar features and colsample_bynode 0.8. An earlier 600-round version nearly matched its ensemble. This tests whether node-level feature sampling makes the enlarged feature set a simpler substitute for two trained members.

Result: `b5bbc29`, AUC **0.7702**, **discard**. Run time: 41.7s (training 11.4s, eval 30.3s, ok) The loss is too large to justify replacing the ensemble, particularly because per-row feature preparation remains similarly expensive.

## Experiment 77 — follow-up — Test day-of-month grouping alongside the successful calendar features

Hypothesis: Add DayofMonth as another native categorical input. Month and weekday helped only jointly under L1; day-of-month can expose repeated within-month schedule effects without enumerating exact dates. This completes the coarse-calendar feature check, with no new fitting or target-derived feature logic.

Result: `ee84567`, AUC **0.7696**, **discard**. Run time: 52.2s (training 19.8s, eval 32.4s, ok) Keep only Month, DayOfWeek and exact date. More calendar categories do not automatically help.

## Experiment 78 — follow-up — Weight the stronger original geometry member more heavily

Hypothesis: Change the equal probability average to fixed weights 0.75 original / 0.25 rotated. The original model was stronger individually, while the rotated member adds diversity. This tests one coarse, evidence-based blend rather than a weight sweep. [Scikit-learn's soft-voting documentation](https://scikit-learn.org/stable/modules/ensemble.html#weighted-average-probabilities-soft-voting) describes the weighted-probability combination.

Result: `354c650`, AUC **0.7709**, **discard**. Run time: 50.3s (training 19.1s, eval 31.1s, ok) Equal weights better exploit complementary errors. Stop tuning mixture weights.

## Experiment 79 — exploration — Add circular departure-time coordinates

Hypothesis: Add sine and cosine of scheduled departure minutes on a 1440-minute cycle, retaining raw CRSDepTime. This gives trees simple splits that join late-night and early-morning departures across midnight. Unlike the earlier hour-category/minute features, it explicitly encodes continuity at the daily boundary. The [scikit-learn time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html#trigonometric-features) motivates the transformation; it need not improve trees, so retain only if the harness supports it.

Result: `cc970a7`, AUC **0.7708**, **discard**. Run time: 56.2s (training 20.0s, eval 36.2s, ok) Discard the extra features and 5-second evaluation overhead.

## Synthesis after 80 experiments (00–79)

Current best is `0f6bd05`, AUC 0.7713, a two-view ensemble with modest node-level column sampling. Ordered carrier-date statistics were valid but harmful. The rotated member alone and a single model containing both views cannot replace averaging. Uniform row sampling remains harmful even after regularization-scale compensation. Longer boosting, extra day-of-month categories, unequal averaging weights and circular departure time do not help. Research during this block included the XGBoost CPU sampler implementation, scikit-learn's soft-voting documentation, and its trigonometric time-feature example. Remaining work: measure whether individual geography/raw-distance inputs can be removed, then test one finer boosting trajectory if time permits. Preserve the full-row, moderately regularized core.

## Experiment 80 — ablation/simplification — Remove destination coordinate features

Hypothesis: Keep both original/rotated origin coordinate views but remove destination coordinates from preparation and both classifiers. Destination identity remains available. This measures whether the lower-gain destination geometry is redundant and can save four feature lookups per row without sacrificing AUC.

Result: `812d7ef`, AUC **0.7711**, **keep**. Run time: 43.0s (training 18.0s, eval 25.0s, ok) Accept a 0.0002 tradeoff under the simplicity criterion: four fewer prepared features and evaluation 25.0 s versus 31.0 s. Peak raw AUC remains 0.7713 at 0f6bd05; retained best is now the simpler 0.7711 model.

## Experiment 81 — ablation/simplification — Remove raw distance from the classifier inputs

Hypothesis: Remove Distance as a direct numeric feature, retaining its use in the training-only airport-geometry fit. Origin/Dest identities and origin coordinates may already account for the useful route information, while raw distance creates additional low-gain interactions.

Result: `f5583b9`, AUC **0.7709**, **discard**. Run time: 41.7s (training 17.2s, eval 24.5s, ok) Unlike the destination-coordinate ablation, this removes no lookup loop or fitting code and saves only about 0.5 s of evaluation. Retain the direct Distance feature.

## Experiment 82 — follow-up — Use a finer constant-rate boosting trajectory

Hypothesis: Use 2400 rounds at eta 0.025 instead of 1200 at 0.05, preserving nominal total shrinkage. The earlier fine-rate experiment predated L1, calendars and the geometry ensemble. A smaller step may stabilize categorical grouping near L1 thresholds while keeping the effective duration fixed. Expected training remains below 60 seconds based on the current two-member fit time.

Result: `e6dcbda`, AUC **0.7712**, **discard**. Run time: 62.3s (training 35.9s, eval 26.4s, ok) A +0.0001 change over the retained 0.7711 is not worth doubling the artifact to 122 MB and training to 35.9 s. Peak remains 0.7713. The saved retained artifact 812d7ef passed batch/single-row equality, input-label independence, unseen-category handling, and finite normalized probabilities on training-only smoke inputs.

## Experiment 83 — ablation/simplification — Test coarser numerical histograms in the final representation

Hypothesis: Reduce max_bin from 1024 to 256 with the retained 1200-round origin-geometry ensemble. This reduces numerical split resolution and histogram work while retaining native categorical handling. Earlier bin tests preceded L1 and the current feature set; coarser thresholds may now remove unnecessary time/distance detail.

Result: `cd88426`, AUC **0.7710**, **discard**. Run time: 43.3s (training 18.5s, eval 24.7s, ok) AUC is slightly lower and training is not faster; artifact size also grows. Retain 1024 bins.

## Experiment 84 — ablation/simplification — Measure whether shallower trees retain the final ensemble performance

Hypothesis: Reduce maximum depth from 8 to 7 with all final features and regularization fixed. Depth 8 was chosen in an earlier single-view regime; the current ensemble may compensate for shallower members, allowing fewer nodes without meaningful AUC loss.

Result: `5c041c4`, AUC **0.7704**, **discard**. Run time: 40.1s (training 15.5s, eval 24.6s, ok) The 0.0007 loss is too large for the moderate size reduction. A plateau research refresh reviewed eta, gamma and depth in the [official parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html). A gain threshold can prune weak splits without imposing a blanket shallow-depth cap.

## Experiment 85 — follow-up — Apply a small minimum split gain to the regularized ensemble

Hypothesis: Set gamma=0.1 while retaining depth 8. The earlier gamma=2 test was before L1 and was much stronger; this twenty-fold smaller threshold may suppress nearly useless residual splits while retaining complex calendar/airport paths. Official docs define gamma as the minimum gain required for a split.

Result: `e368e7e`, AUC **0.7700**, **discard**. Run time: 37.1s (training 12.6s, eval 24.5s, ok) Gamma 0.1 compresses the artifact but loses 0.0011 AUC. Retain unrestricted positive-gain splits under L1.

## Experiment 86 — ablation/simplification — Test a shorter larger-step boosting path

Hypothesis: Use 600 rounds at eta 0.1, preserving nominal total shrinkage while halving the number of trees. The finer path in experiment 82 yielded only a negligible gain, so this final budget-conscious check asks whether the established regularization also tolerates a coarser path with lower model size and training cost.

Result: `35d93ad`, AUC **0.7701**, **discard**. Run time: 34.1s (training 9.7s, eval 24.4s, ok) Halving the model loses 0.0010 AUC. Retain 1200 rounds at eta 0.05.

## Final summary — two-hour budget completed

Completed **87 experiments (00–86)**: 86 scored successfully and one DART attempt hit the training timeout. The harness reported TIME IS UP before wrap-up; no further experiment was started.

Selected retained commit: **`812d7ef`**, Eval AUC **0.7711**, versus baseline **0.7203** (absolute gain **0.0508**). Branch: **`oct2`**. Selected run took 43.0 seconds: 18.0 seconds training and 25.0 seconds evaluation. It uses two depth-8 XGBoost classifiers with 1200 rounds at eta 0.05, alpha 5, lambda 10, child weight 20, 1024 numerical bins, category threshold 16 and node-level column sampling 0.8. The two classifiers use original and rotated origin coordinates and average their probabilities. Calendar inputs include month, weekday and exact flight date; other direct inputs are scheduled departure time, distance, carrier and airport identities.

Peak raw Eval AUC: **0.7713** at **`0f6bd05`**. The selected model trades 0.0002 AUC for four fewer destination-coordinate features and evaluation reduced from 31.0 to 25.0 seconds. Both artifacts remain available. Nearby compact-model checks did not justify further simplification: removing raw distance, coarser bins, shallower trees, positive split-gain thresholds and fewer larger-step rounds all lost score without a sufficient tradeoff. A finer trajectory doubled model size for only 0.0001 over the selected score.

What worked: exact-date categorical structure; moderate L1 regularization; enough boosting rounds; train-fitted airport geometry; month and weekday jointly; complementary geometry views; and modest node-level feature sampling. The strongest gains came from date representation and L1, with later gains from calendar structure and averaging.

What did not work: high-cardinality route combinations; ordered or disjoint target-rate encodings; overly strong regularization; row subsampling; restrictive interaction groups; ranking objectives; longer boosting beyond the useful range; spherical geometry; extra day-of-month or circular departure-time features; and unequal ensemble weights. DART was too slow for the 60-second training limit.

Validation: all 86 successful current-run result rows have corresponding saved artifacts, result commit IDs are unique, and the selected artifact passed batch/single-row feature equality, independence from supplied labels, unseen-category handling, and finite normalized probabilities on training-only smoke inputs. The harness saved and reloaded each successful artifact for evaluation. Only train.py differs from the starting commit, its final save_and_evaluate call is intact, and the code worktree/index are clean. Results, research notes and timing files remain uncommitted as required.

Next ideas for a fresh budget: train-only early stopping in the final L1/calendar regime; a compact ensemble with more diverse categorical representations; and whether useful origin geometry can be distilled into fewer stable features. Keep the prescribed harness metric and per-row feature contract.
