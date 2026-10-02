# XGBoost research run: oct1

Date: 2026-10-01. Starting commit: `92e43e6`. Branch created from the existing HEAD.
The two-hour clock started on the user's `go`; all experiments use the unchanged harness.
Only `data/train.csv` is inspected for modeling. The harness alone scores evaluation data.

## Initial observations

Training has 200,000 rows, eight predictors, balanced binary labels, and no missing values.
Calendar categories use `c-` prefixes; there are 283 origin and destination airports and 20 carriers.
The starter uses 30 depth-6 trees at learning rate 0.1 with native categorical inputs.
All feature transformations will stay in `prepare`, with row-independent outputs and train-fitted lookups only.
No row-count or frequency features, extra dependencies, alternative evaluation metrics, or held-out data access.

## Research before the first change

- [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html): more boosting rounds can address underfitting; depth, child weight and regularization control variance.
- [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html): inspect learning rate, tree size, sampling and categorical split controls. Start with 300 rounds, then test depth and regularization deliberately.
- [Categorical feature tutorial](https://xgboost.readthedocs.io/en/release_3.2.0/tutorials/categorical.html): stable train-fitted category levels and partition-based splits support interaction categories without dense one-hot expansion.
- [Scikit-learn time feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html): calendar and time representations can expose seasonal structure; adapt to scheduled departure time and flight date.
- Use stable XGBoost docs: the development docs describe a changed categorical default in 3.5, while the installed version is 3.4.1.

## E000 — unchanged baseline

Commit: `92e43e6`. Classification: baseline.
Hypothesis: measure the provided model before changing any code.
Result: **0.7203 AUC**, kept. Training 1.1s, evaluation 30.7s, total 31.8s.

## E001 — increase boosting rounds from 30 to 300

Commit: 550ea08. Parent: 92e43e6. Classification: follow-up.
Hypothesis: The 30-tree baseline underfits; increase rounds tenfold with unchanged features and tree settings.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html.
Result: **0.7342 AUC**, keep; previous best 0.7203. Run time: 33.4s (training 2.5s, eval 30.9s, ok)

## E002 — cache categorical dtypes and remove redundant membership filtering

Commit: 6132d72. Parent: 550ea08. Classification: ablation/simplification.
Hypothesis: A fixed CategoricalDtype already maps unknown labels to missing, so reusing it should preserve AUC and reduce per-row preprocessing overhead.
Source: https://pandas.pydata.org/docs/user_guide/categorical.html.
Result: **0.7342 AUC**, keep; previous best 0.7342. Run time: 16.3s (training 2.5s, eval 13.7s, ok)
AUC is unchanged while evaluation fell from 30.9s to 13.7s. Batch/single-row equality and unknown-category behavior were checked on training rows; fewer code lines justify keeping.

## E003 — add exact flight-date categorical feature

Commit: acc22f7. Parent: 6132d72. Classification: exploration.
Hypothesis: Month-day conjunctions expose specific-day delay conditions that separate month and day features require several splits to isolate.
Source: https://proceedings.mlr.press/v82/vandal18a.html; https://xgboost.readthedocs.io/en/release_3.2.0/tutorials/categorical.html.
Result: **0.7500 AUC**, keep; previous best 0.7342. Run time: 19.9s (training 2.7s, eval 17.2s, ok)
The date conjunction adds 0.0158 AUC. This supports modeling daily conditions explicitly, rather than treating month and day only as separate categories.

## E004 — deepen trees from 6 to 8 with exact-date features

Commit: 00362a0. Parent: acc22f7. Classification: follow-up.
Hypothesis: The strong gain from exact dates suggests useful date-airport-carrier interactions; depth 8 may learn these with fewer boosting steps.
Source: E003; https://xgboost.readthedocs.io/en/stable/parameter.html.
Result: **0.7454 AUC**, discard; previous best 0.7500. Run time: 22.1s (training 4.7s, eval 17.5s, ok)
Depth 8 reduced AUC by 0.0046, so the commit was discarded. Stronger interaction capacity appears to overfit at the current regularization level. Saved date preparation passed batch/single-row equality on 32 training rows.

## E005 — regularize date interactions with min_child_weight 20

Commit: 628bb1a. Parent: acc22f7. Classification: follow-up.
Hypothesis: Depth-8 overfitting suggests fragile leaf estimates. Raising minimum child Hessian from 1 to 20 should improve stability while retaining depth-6 interaction capacity.
Source: E004; https://xgboost.readthedocs.io/en/stable/parameter.html.
Result: **0.7517 AUC**, keep; previous best 0.7500. Run time: 19.8s (training 2.6s, eval 17.1s, ok)
Minimum child weight 20 improves AUC by 0.0017 with no meaningful runtime cost; kept.

## E006 — add ordered month-day calendar coordinate

Commit: 1770616. Parent: 628bb1a. Classification: follow-up.
Hypothesis: An ordered calendar coordinate complements exact-date categories by allowing contiguous seasonal and multi-day periods to share tree splits.
Source: E003; https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html.
Result: **0.7499 AUC**, discard; previous best 0.7517. Run time: 24.0s (training 2.8s, eval 21.3s, ok)
Ordered dates reduced AUC by 0.0018 and added preprocessing time; discarded. Exact-date categories already carry the useful calendar signal at this model capacity.

## E007 — add carrier-origin and carrier-destination categories

Commit: 1c6a72d. Parent: 628bb1a. Classification: exploration.
Hypothesis: Airline behavior can differ by airport; explicit carrier-airport categories may capture stable operating patterns more economically than deeper trees.
Source: https://arxiv.org/abs/1911.01605; https://xgboost.readthedocs.io/en/release_3.2.0/tutorials/categorical.html.
Result: **0.7336 AUC**, discard; previous best 0.7517. Run time: 27.0s (training 3.3s, eval 23.6s, ok)
Carrier-airport categories sharply worsened AUC (−0.0181), so they were discarded. High-cardinality partitioning may be overfitting; test categorical split regularization before adding further sparse conjunctions.

## E008 — limit categorical partition threshold to 16

Commit: 917dd98. Parent: 628bb1a. Classification: follow-up.
Hypothesis: The carrier-airport failure suggests overly flexible category groupings. A smaller categorical split threshold should regularize even the kept airport/date categories.
Source: E007; https://xgboost.readthedocs.io/en/stable/parameter.html.
Result: **0.7510 AUC**, discard; previous best 0.7517. Run time: 19.5s (training 2.3s, eval 17.2s, ok)
Reducing max_cat_threshold from 64 to 16 gives 0.7510, slightly below the best. Discarded. Three consecutive feature/regularization changes have failed, so refresh research before switching categorical split strategy.

## E009 — use one-category splits for all categorical features

Commit: 1b88103. Parent: 628bb1a. Classification: exploration.
Hypothesis: Single-category splits avoid fitting flexible groups of sparse levels, providing a distinct bias-variance tradeoff after native partition regularization failed.
Source: https://github.com/dmlc/xgboost/blob/master/doc/parameter.rst; https://lightgbm.readthedocs.io/en/stable/Advanced-Topics.html#categorical-feature-support.
Result: **0.7352 AUC**, discard; previous best 0.7517. Run time: 19.2s (training 2.0s, eval 17.2s, ok)
At 300 trees, single-category splits reach only 0.7352 AUC. This strategy may need many more trees to fit hundreds of separate date and airport effects. Discarded; test that capacity explanation explicitly.

## E010 — give single-category splits 1500 boosting rounds

Commit: eb81d79. Parent: 628bb1a. Classification: follow-up.
Hypothesis: The 300-round one-category model may underfit hundreds of date and airport effects; 1500 rounds test this capacity explanation without changing its tree depth or learning rate.
Source: E009; https://xgboost.readthedocs.io/en/release_3.2.0/tutorials/categorical.html.
Result: **0.7466 AUC**, discard; previous best 0.7517. Run time: 23.3s (training 5.7s, eval 17.6s, ok)
More one-category boosting rounds recover some performance (0.7466 versus 0.7352), but remain below native grouped splits. Discarded; return to grouped categories and test stronger shrinkage and early stopping.

## Synthesis after E010

Best: **0.7517**, commit `628bb1a`, versus baseline 0.7203 (+0.0314).
What helped: 300 boosting rounds, explicit flight-date categories, and minimum child weight 20.
A useful simplification halved evaluation time with identical predictions/AUC.
What failed: depth 8, ordered date coordinates, carrier-airport conjunctions, a smaller partition threshold, and one-category splits at both 300 and 1500 rounds.
Current theory: calendar-specific conditions matter, but sparse categorical interactions are easy to overfit. Preserve the simple date feature and stabilize leaf estimates before revisiting feature growth.
Training-only EDA also shows a strong time-of-day pattern, rising from morning to evening and declining late at night; a global monotonic time constraint is therefore unsuitable.
Research refresh: [LightGBM categorical guidance](https://lightgbm.readthedocs.io/en/stable/Advanced-Topics.html#categorical-feature-support) emphasizes regularization/low-dimensional representations for many categories. [XGBoost estimator documentation](https://xgboost.readthedocs.io/en/stable/python/sklearn_estimator.html) describes a train-only validation split and early stopping. We will use no cross-validation or refit, and the harness AUC remains the selection metric.
Next directions: L2 shrinkage; slower boosting with a larger tree budget; train-only early stopping; low-cardinality schedule components and train-fitted schedule medians.

## E011 — increase leaf L2 regularization to 20

Commit: 744054d. Parent: 628bb1a. Classification: follow-up.
Hypothesis: Depth and sparse-category experiments indicate overfitting; stronger L2 shrinkage should stabilize leaf outputs without suppressing useful date interactions.
Source: E004–E010; https://xgboost.readthedocs.io/en/stable/python/python_api.html.
Result: **0.7539 AUC**, keep; previous best 0.7517. Run time: 20.1s (training 2.7s, eval 17.4s, ok)

## E012 — use 1000 rounds at learning rate 0.03

Commit: d22c516. Parent: 744054d. Classification: follow-up.
Hypothesis: Smaller boosting steps may learn more stable categorical interactions. Match approximately the current total shrinkage (300×0.1 versus 1000×0.03) to isolate step granularity.
Source: E011; https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html.
Result: **0.7565 AUC**, keep; previous best 0.7539. Run time: 24.5s (training 6.8s, eval 17.8s, ok)

## E013 — train-only early stopping with up to 4000 rounds

Commit: de0a1e3. Parent: d22c516. Classification: exploration.
Hypothesis: A 10% training-only stopping split can identify a better boosting length than the fixed 1000 rounds, while preventing late-round overfitting. The fitted model uses the other 90%; there is no refit or cross-validation.
Source: https://xgboost.readthedocs.io/en/stable/python/sklearn_estimator.html; https://xgboost.readthedocs.io/en/stable/prediction.html.
Result: **0.7542 AUC**, discard; previous best 0.7565. Run time: 23.5s (training 5.9s, eval 17.5s, ok)
Stopping selected iteration 618, but harness AUC was 0.7542 versus 0.7565 for the full-training-data model. Discarded; the stopping split's reduced fitting sample did not improve the final metric.

## E014 — add departure time relative to the route median

Commit: 4c93b72. Parent: d22c516. Classification: exploration.
Hypothesis: A route's usual departure schedule can contextualize clock time. Fit route median departure minutes once on train and subtract it row by row; use no labels, frequencies, or counts.
Source: program.md feature-engineering example; https://pandas.pydata.org/pandas-docs/version/2.1/reference/api/pandas.core.groupby.SeriesGroupBy.median.html; https://pandas.pydata.org/docs/reference/api/pandas.Series.map.html.
Result: **0.7555 AUC**, discard; previous best 0.7565. Run time: 29.4s (training 6.8s, eval 22.6s, ok)
Route-relative departure time scored 0.7555 and added five seconds of evaluation cost, so it was discarded. Its train-fitted lookup passed the required batch/single-row invariance check.

## E015 — add scheduled minute within the hour

Commit: ab90cc1. Parent: d22c516. Classification: exploration.
Hypothesis: Minute-of-hour exposes recurring scheduling patterns that are non-monotonic in HHMM time, adding an inexpensive row-local feature.
Source: https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html; training time-of-day EDA.
Result: **0.7557 AUC**, discard; previous best 0.7565. Run time: 25.9s (training 6.8s, eval 19.1s, ok)

## E016 — derive two-dimensional airport positions from training route distances

Commit: d2dc81c. Parent: d22c516. Classification: exploration.
Hypothesis: A distance-based airport embedding can expose regional similarity and let date effects transfer among nearby airports. Fit the graph and MDS coordinates only on training predictors; map the four origin/destination coordinates per row.
Source: https://scikit-learn.org/stable/modules/manifold.html; https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.shortest_path.html.
Result: **0.7568 AUC**, discard; previous best 0.7565. Run time: 32.1s (training 7.3s, eval 24.8s, ok)
AUC rose by only 0.0003 for 18 added lines and roughly seven extra evaluation seconds. Discarded under the simplicity criterion (required >0.001 gain for this larger feature block). The geometry hypothesis remains worth one targeted date-region follow-up.

## E017 — add date-by-geographic-region categories from distance-derived clusters

Commit: a836fa7. Parent: d22c516. Classification: follow-up.
Hypothesis: Grouping distance-derived airport positions into eight regions may expose daily regional conditions at a less sparse scale than airport-by-date interactions. Fit geography and category levels on train predictors only.
Source: E016; https://scikit-learn.org/stable/modules/manifold.html; https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html; https://proceedings.mlr.press/v82/vandal18a.html.
Result: **0.7456 AUC**, discard; previous best 0.7565. Run time: 37.3s (training 11.4s, eval 25.9s, ok)
Date-region categories scored 0.7456, a clear regression. Discarded; geographic feature engineering has not justified its complexity. Return to the compact model and test whether reducing tree interactions improves generalization.

## E018 — reduce tree depth from 6 to 4

Commit: 82b7098. Parent: d22c516. Classification: ablation/simplification.
Hypothesis: The repeated failure of extra sparse interactions suggests variance remains limiting. Shallower trees may retain the useful calendar effects while learning fewer fragile high-order interactions.
Source: E004, E007, E017; current-run regularization evidence.
Result: **0.7549 AUC**, discard; previous best 0.7565. Run time: 21.8s (training 4.3s, eval 17.5s, ok)

## E019 — increase L2 regularization from 20 to 100

Commit: c8663d8. Parent: d22c516. Classification: follow-up.
Hypothesis: The earlier L2 increase improved AUC, whereas removing interaction capacity did not. A fivefold stronger leaf penalty tests whether more shrinkage can stabilize the existing depth-6 model.
Source: E011 and E018; https://jerryfriedman.su.domains/ftp/machine.pdf.
Result: **0.7583 AUC**, keep; previous best 0.7565. Run time: 24.2s (training 6.5s, eval 17.6s, ok)

## E020 — sample 80 percent of rows per boosting step

Commit: de3e90c. Parent: c8663d8. Classification: exploration.
Hypothesis: Stochastic row sampling may reduce reliance on particular training examples and stabilize the strongly regularized categorical model.
Source: https://jerryfriedman.su.domains/ftp/machine.pdf; https://xgboost.readthedocs.io/en/stable/tutorials/rf.html.
Result: **0.7558 AUC**, discard; previous best 0.7583. Run time: 25.1s (training 7.2s, eval 17.9s, ok)

## Synthesis after E020

Best retained: **0.7583**, commit `c8663d8` (+0.0380 over baseline).
This block's gains came from L2 penalties (20 then 100) and smaller boosting steps (1000 rounds at 0.03).
Train-only early stopping, route-relative time, within-hour minutes, shallower trees, and 80% row sampling did not improve the harness metric.
Distance-derived airport coordinates reached 0.7568 when the incumbent was 0.7565, but the 0.0003 gain did not justify 18 extra lines and evaluation overhead. Daily geographic-region categories were worse and were also discarded.
Current theory: the simple feature set has sufficient signal; controlling noisy categorical interactions matters more than adding sparse features. Preserve exact dates, depth 6, full-data fitting, and strong shrinkage.
Research refresh: [XGBoost forest tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) explains per-node feature sampling and boosted forests. [Tree growth options](https://xgboost.readthedocs.io/en/latest/parameter.html) suggest a leaf-budget approach as a distinct alternative to fixed depth. No external example's cross-validation code is adopted.
Next: column sampling, a small boosted forest, larger shrinkage/leaf-support tests, and loss-guided growth. Revisit an earlier categorical near-miss only if a substantive change in regularization makes the hypothesis different.

## E021 — sample 80 percent of features at each split

Commit: 265d4a7. Parent: c8663d8. Classification: exploration.
Hypothesis: Per-node feature sampling may prevent clock time and exact date from monopolizing splits, allowing useful airport/carrier effects to emerge while preserving every training row.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/rf.html.
Result: **0.7594 AUC**, keep; previous best 0.7583. Run time: 24.2s (training 6.6s, eval 17.6s, ok)

## E022 — average four feature-randomized trees per boosting round

Commit: 3e8815e. Parent: 265d4a7. Classification: follow-up.
Hypothesis: Per-node feature sampling helped. Averaging four trees at each step may retain its useful diversity while reducing the variance of each gradient update; preserve all training rows.
Source: E021; https://xgboost.readthedocs.io/en/stable/tutorials/rf.html.
Result: **0.7602 AUC**, keep; previous best 0.7594. Run time: 48.4s (training 29.0s, eval 19.3s, ok)
Four trees per boosting round improve AUC by 0.0008 with one additional parameter. Training rises to 29.0s, still below the one-minute limit; keep and track runtime headroom.

## E023 — increase histogram resolution to 1024 bins

Commit: 09ccc6c. Parent: 3e8815e. Classification: exploration.
Hypothesis: Training has over 1100 distinct departure times and 1200 distances. Finer numeric histograms may preserve useful schedule/route distinctions currently merged into 256 bins.
Source: https://xgboost.readthedocs.io/en/stable/treemethod.html; initial training-data inspection.
Result: **0.7598 AUC**, discard; previous best 0.7602. Run time: 49.0s (training 29.9s, eval 19.1s, ok)
1024 bins scored 0.7598, slightly below the retained 0.7602. Discarded; numeric split resolution is not the current bottleneck.

## E024 — remove separate month and day-of-month predictors

Commit: b25bad5. Parent: 3e8815e. Classification: ablation/simplification.
Hypothesis: Exact flight date already determines month and day. Removing those weak-gain redundant predictors may simplify the model and avoid spending sampled feature slots on them.
Source: E003 model feature gains; current-run evidence.
Result: **0.7603 AUC**, keep; previous best 0.7602. Run time: 44.9s (training 28.1s, eval 16.7s, ok)

## E025 — grow loss-guided trees with a 32-leaf budget

Commit: 6c0f1a6. Parent: b25bad5. Classification: exploration.
Hypothesis: A fixed leaf budget can allocate extra depth to useful date/airport conditions without expanding every branch to the same depth. Test 32 leaves with loss-guided growth and no depth cap.
Source: https://xgboost.readthedocs.io/en/stable/treemethod.html; https://xgboost.readthedocs.io/en/latest/parameter.html.
Result: **0.7594 AUC**, discard; previous best 0.7603. Run time: 47.7s (training 31.1s, eval 16.6s, ok)

## E026 — increase L2 penalty from 100 to 500

Commit: 1e6349f. Parent: b25bad5. Classification: follow-up.
Hypothesis: L2 improvements from 20 to 100 motivate a coarse fivefold test of the remaining shrinkage tradeoff under the averaged-tree model, rather than small arbitrary parameter increments.
Source: E011, E019, E022.
Result: **0.7604 AUC**, keep; previous best 0.7603. Run time: 44.3s (training 27.2s, eval 17.0s, ok)

## E027 — extend the strongly regularized forest to 2000 rounds

Commit: bf4bb1e. Parent: 1e6349f. Classification: follow-up.
Hypothesis: L2=500 sharply shrinks small-leaf updates. Doubling rounds tests whether the 1000-round model is now underfitting despite its stronger variance control; estimated training time is about 54 seconds.
Source: E026 training time and shrinkage result.
Result: **0.7602 AUC**, discard; previous best 0.7604. Run time: 72.5s (training 53.5s, eval 19.0s, ok)

## E028 — train a pairwise-ranking XGBoost model on all training labels

Commit: 9e25343. Parent: 1e6349f. Classification: exploration.
Hypothesis: AUC measures positive/negative ordering. RankNet's pairwise logistic surrogate may improve that ordering. Use one training group, uniform pair sampling, disabled ranking normalization, and two parallel trees to leave time for pair construction. The unchanged harness still selects by Eval AUC.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html; https://www.microsoft.com/en-us/research/publication/learning-to-rank-using-gradient-descent/.
Result: **0.7567 AUC**, discard; previous best 0.7604. Run time: 67.4s (training 51.3s, eval 16.1s, ok)
The ranking objective completed within the training limit (51.3s) but scored 0.7567. Discarded; the current binary-logistic model remains stronger and simpler for this data.

## E029 — raise minimum child weight from 20 to 100

Commit: c8f8f83. Parent: 1e6349f. Classification: follow-up.
Hypothesis: Stronger minimum leaf support may eliminate fragile conditional splits that L2 only shrinks. Test a fivefold support threshold while retaining the successful averaged-tree architecture.
Source: E005, E026; current-run categorical-overfitting evidence.
Result: **0.7612 AUC**, keep; previous best 0.7604. Run time: 44.7s (training 28.1s, eval 16.6s, ok)

## E030 — construct categoricals from fitted category codes

Commit: 4929993. Parent: c8f8f83. Classification: ablation/simplification.
Hypothesis: Using the fitted category index directly preserves every category code and maps unknowns to -1, while avoiding deprecated constructor behavior and potentially reducing row-preparation overhead.
Source: https://pandas.pydata.org/docs/user_guide/categorical.html; explicit unknown-category check.
Result: **0.7612 AUC**, keep; previous best 0.7612. Run time: 40.8s (training 27.7s, eval 13.1s, ok)
AUC is exactly preserved at 0.7612. Evaluation fell from 16.6s to 13.1s including artifact overhead, and the observed unknown-category deprecation warning disappeared. Kept.

## Synthesis after E030

Best retained: **0.7612**, commit `4929993` (+0.0409 over baseline).
Feature sampling and four trees per boosting round helped. Removing redundant month/day predictors preserved accuracy and reduced evaluation cost. Stronger minimum leaf support added another 0.0008.
Finer numeric bins, loss-guided trees, twice as many boosting rounds, and a pairwise-ranking objective did not beat the incumbent. The latter needed 51.3s of training without improving AUC, so binary logistic remains preferable here.
The categorical-code cleanup keeps the same feature values, handles unseen labels explicitly, removes a pandas warning observed during evaluation, and reduces runtime.
Research refresh: [XGBoost interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html) support restricting groups, but overlapping groups can admit additional interactions; enumerating all pairs/triples is not a reliable shortcut to a strict interaction-order limit.
Current theory: explicit dates plus a small original feature set are strong; regularized averaging gives more reliable gains than broad feature expansion. Deeper trees previously failed with weak regularization, but the current L2=500, child weight=100, and tree averaging make one controlled retest meaningful. Next consider disjoint domain-informed interaction groups and selected categorical additions under this stronger regularization.

## E031 — retest depth 8 with strong regularization and averaged trees

Commit: ddd32c1. Parent: 4929993. Classification: follow-up.
Hypothesis: Unlike E004's weakly regularized model, the current model has L2=500, minimum child weight=100, smaller steps, feature sampling and four-tree averaging. This may make higher-order date-airport interactions useful without the previous variance penalty.
Source: E004 versus E019–E030.
Result: **0.7613 AUC**, keep; previous best 0.7612. Run time: 52.5s (training 38.4s, eval 14.0s, ok)

## E032 — remove day-of-week as a redundant date predictor

Commit: f181a60. Parent: ddd32c1. Classification: ablation/simplification.
Hypothesis: The exact date determines weekday, and weekday has the lowest mean split gain in the retained model. Removing it may reduce redundant splits and preparation work while preserving AUC.
Source: Retained-model training feature gains; E024.
Result: **0.7617 AUC**, keep; previous best 0.7613. Run time: 49.5s (training 36.1s, eval 13.4s, ok)

## E033 — restrict interactions to disjoint daily-context and carrier-distance groups

Commit: a3f24ae. Parent: f181a60. Classification: exploration.
Hypothesis: An additive separation between daily airport/schedule context and carrier-distance effects may suppress spurious cross-group interactions. Use disjoint groups so the documented overlap behavior cannot weaken the intended restriction.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html.
Result: **0.7550 AUC**, discard; previous best 0.7617. Run time: 43.0s (training 30.3s, eval 12.7s, ok)
The disjoint interaction groups fell to 0.7550, showing that cross-group effects carry useful signal. Discarded. A focused carrier-origin feature is worth revisiting under the much stronger current regularization.

## E034 — revisit a carrier-origin category under strong regularization

Commit: 991bea3. Parent: f181a60. Classification: follow-up.
Hypothesis: The interaction-constraint failure shows cross-group signal. Unlike E007, add only the departure-side carrier interaction, using L2=500, child weight=100, small steps and averaged trees to control sparse-category noise.
Source: E007 and E033; https://arxiv.org/abs/1911.01605.
Result: **0.7584 AUC**, discard; previous best 0.7617. Run time: 56.6s (training 39.4s, eval 17.2s, ok)

## E035 — add sine and cosine calendar-season features

Commit: f6f8252. Parent: f181a60. Classification: exploration.
Hypothesis: Smooth annual phase can share seasonal effects across adjacent dates and across year-end, complementing discrete flight dates. Fit two date-to-phase lookups from training category levels; apply fixed row-local maps.
Source: https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html.
Result: **0.7611 AUC**, discard; previous best 0.7617. Run time: 55.3s (training 38.0s, eval 17.3s, ok)
Seasonal sine/cosine features pass row-invariance checks but score 0.7611, below the simpler 0.7617 model. Discarded. Refresh research after three consecutive unsuccessful changes.

## E036 — sample half of the predictors at each split

Commit: 20a93eb. Parent: f181a60. Classification: follow-up.
Hypothesis: Feature sampling was one of the successful variance controls. With six retained predictors, 0.5 selects three instead of four candidates per split, testing meaningfully stronger tree diversity without adding features.
Source: E021–E022; https://xgboost.readthedocs.io/en/stable/tutorials/rf.html; plateau research on https://xgboost.readthedocs.io/en/stable/tutorials/dart.html.
Result: **0.7631 AUC**, keep; previous best 0.7617. Run time: 47.9s (training 34.7s, eval 13.2s, ok)

## E037 — halve the trees per boosting round from four to two

Commit: ebdb707. Parent: 20a93eb. Classification: ablation/simplification.
Hypothesis: After stronger leaf support and feature sampling, four parallel trees may be redundant. Two trees would halve model size and leave more training-budget headroom if AUC is preserved.
Source: E022 and E036.
Result: **0.7632 AUC**, keep; previous best 0.7631. Run time: 29.5s (training 17.6s, eval 11.9s, ok)

## E038 — sample features per tree instead of per node

Commit: a6f92e1. Parent: ebdb707. Classification: exploration.
Hypothesis: A fixed three-feature subset per tree creates additive low-order models across the ensemble, while sampling at each node permits broader interactions. Compare these distinct diversity mechanisms at the same sampling fraction.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/rf.html; XGBoost column-sampling parameter definitions.
Result: **0.7618 AUC**, discard; previous best 0.7632. Run time: 28.3s (training 16.4s, eval 11.9s, ok)

## E039 — average two independent boosting trajectories at the same total tree count

Commit: 048604a. Parent: ebdb707. Classification: exploration.
Hypothesis: Two independent one-tree-per-step boosters can diversify the full residual-learning trajectory, unlike two trees sharing each update. Average fixed seeds 42 and 2026 with the same total 2000 trees; no seed selection or extra evaluation.
Source: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html; E022 and E037.
Result: **0.7631 AUC**, discard; previous best 0.7632. Run time: 27.1s (training 14.8s, eval 12.3s, ok)

## E040 — test occasional tree dropout with 300 larger boosting steps

Commit: aada6e3. Parent: ebdb707. Classification: exploration.
Hypothesis: DART-style dropout can reduce dependence on early trees and late-round overspecialization. Use rate_drop=0.1, skip_drop=0.9, forest normalization, and 300 rounds at 0.1 to keep its expensive prediction recomputation within the training limit.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/dart.html; https://proceedings.mlr.press/v38/korlakaivinayak15.html.
Result: **0.0000 AUC**, crash; previous best 0.7632. Run time: 60.0s (training 60.0s, eval 0.0s, timeout-training)
DART's prediction-buffer cost exceeded the training limit even at 300 rounds; classify the timeout as a crash and discard. Prefer split penalties and native boosting within this budget.

## Synthesis after E040

Best retained: **0.7632**, commit `ebdb707` (+0.0429 over baseline).
The strongest gain in this block came from sampling three of six predictors at each split. Two parallel trees matched/slightly exceeded four while halving training time and model size. Weekday removal was another successful simplification.
Restricting interaction groups, revisiting carrier-origin categories, smooth seasonal features, fixed per-tree feature subsets, and averaging independent trajectories did not improve the retained model. The seasonal features passed batch/single-row invariance checks before being discarded.
DART exceeded the 60s training limit even at 300 rounds; logged as a crash and reverted. Its documented prediction-buffer overhead is material under this budget.
Research refresh: [DART paper](https://proceedings.mlr.press/v38/korlakaivinayak15.html), [DART implementation notes](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html), [soft-voting API](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html), and the [XGBoost paper](https://arxiv.org/abs/1603.02754) on explicit tree-complexity penalties.
Current theory: a compact six-feature model benefits from strong regularization plus per-node feature diversity; frequent shallow changes to its feature set are less effective. Next test weak-split penalties, adaptive quantile sketches, and further controlled capacity/diversity tradeoffs, with enough training headroom to stay below one minute.

## E041 — require split gain of at least one

Commit: c90d69f. Parent: ebdb707. Classification: exploration.
Hypothesis: An explicit gamma=1 complexity cost may suppress low-gain noisy splits that remain after L2 shrinkage and leaf-support constraints, while retaining useful larger interactions.
Source: https://arxiv.org/abs/1603.02754.
Result: **0.7582 AUC**, discard; previous best 0.7632. Run time: 22.3s (training 11.1s, eval 11.1s, ok)

## E042 — use adaptive Hessian-weighted quantile sketches

Commit: 2098c70. Parent: ebdb707. Classification: exploration.
Hypothesis: The approx tree method updates numeric split candidates using current Hessian weights, potentially improving boundaries for ambiguous cases beyond the fixed global histogram. Preserve all other model settings.
Source: https://xgboost.readthedocs.io/en/stable/treemethod.html.
Result: **0.7633 AUC**, discard; previous best 0.7632. Run time: 56.5s (training 44.6s, eval 12.0s, ok)

E042 selection note: the 0.0001 gain is insufficient for training increasing from 17.6s to 44.6s, which removes most tuning headroom. Apply the simplicity/cost criterion and retain the histogram model.

## E043 — restrict each split to two sampled predictors

Commit: 8164256. Parent: ebdb707. Classification: follow-up.
Hypothesis: Moving from four to three feature candidates improved AUC. With six predictors, colsample_bynode=0.4 selects two, bracketing whether still stronger randomization helps or begins to underfit.
Source: E021 and E036.
Result: **0.7645 AUC**, keep; previous best 0.7632. Run time: 29.3s (training 17.5s, eval 11.8s, ok)

## E044 — increase depth to 10 under two-feature split sampling

Commit: 01abec6. Parent: 8164256. Classification: follow-up.
Hypothesis: With only two feature candidates at each split, a longer path can recover useful combinations that randomness postpones. Test depth 10 while retaining the strong leaf support and shrinkage.
Source: E031 and E043.
Result: **0.7645 AUC**, discard; previous best 0.7645. Run time: 30.9s (training 18.8s, eval 12.1s, ok)

## E045 — learn date risk from a separate training-only encoding partition

Commit: dc1b8be. Parent: 8164256. Classification: exploration.
Hypothesis: A fixed numeric date-risk prior may be less noisy within tree nodes than repeatedly reordering date categories. Reserve 20% of train solely for the lookup and fit the trees on the other 80%, eliminating self-label leakage. This is one training partition, not cross-validation; no extra performance metric or refit is used.
Source: https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html.
Result: **0.7590 AUC**, discard; previous best 0.7645. Run time: 27.7s (training 13.8s, eval 13.9s, ok)
The saved preparation was checked on training rows: batching does not change features, and flipping supplied labels changes only y, never X.

## E046 — add an L1 leaf-weight penalty of five

Commit: 291c4a2. Parent: 8164256. Classification: exploration.
Hypothesis: L1 shrinkage can zero weak leaf updates while retaining larger effects, providing a different form of sparsity from L2's continuous shrinkage or gamma's hard split-cost threshold.
Source: https://xgboost.readthedocs.io/en/stable/parameter.html; E041.
Result: **0.7636 AUC**, discard; previous best 0.7645. Run time: 26.9s (training 15.2s, eval 11.7s, ok)

## E047 — sample half the rows using gradient-based probabilities

Commit: d460c6d. Parent: 8164256. Classification: exploration.
Hypothesis: Uniform row sampling lost useful signal in E020. Sampling according to regularized gradient/Hessian magnitude may retain more informative rows at the same reduced sample fraction; use the installed CPU-supported histogram method.
Source: https://arxiv.org/abs/1910.13204; https://xgboost.readthedocs.io/en/release_3.3.0/parameter.html.
Result: **0.7624 AUC**, discard; previous best 0.7645. Run time: 34.2s (training 22.1s, eval 12.1s, ok)

## E048 — reduce L2 to 100 under the stronger feature-sampling regime

Commit: 0cd3daa. Parent: 8164256. Classification: ablation/simplification.
Hypothesis: L2=500 was chosen before two-feature split sampling. Since that sampling now supplies stronger variance control, a lower penalty may recover useful small leaf effects; this tests the interaction between two successful regularizers.
Source: E026 versus E043; current-run regularization evidence.
Result: **0.7639 AUC**, discard; previous best 0.7645. Run time: 29.8s (training 17.7s, eval 12.1s, ok)

## E049 — add a clock-plus-distance proxy for trip completion time

Commit: 6d8ff67. Parent: 8164256. Classification: exploration.
Hypothesis: Destination arrival capacity can delay departures. A row-local departure-minutes + Distance/8 + 30 proxy (wrapped to a day) exposes an oblique time/distance interaction. The 480 mph and 30-minute assumptions are heuristic; it is not a destination-local ETA and uses no external flight data.
Source: https://www.faa.gov/air_traffic/publications/atpubs/foa_html/chap18_section_10.html.
Result: **0.7642 AUC**, discard; previous best 0.7645. Run time: 32.1s (training 16.6s, eval 15.5s, ok)

## E050 — remove route distance from the six-feature model

Commit: b84f389. Parent: 8164256. Classification: ablation/simplification.
Hypothesis: Distance is largely determined by Origin and Dest and has the weakest remaining gain. Removing it may eliminate redundant splits while still sampling two of the five remaining features at each node.
Source: Current-run feature gain inspection and E024/E032 successful feature removals..
Result: **0.7640 AUC**, discard; previous best 0.7645. Run time: 29.7s (training 18.5s, eval 11.2s, ok)

## Synthesis after E050

Best remains 0.7645 at 8164256, versus 0.7203 baseline. Sampling two of six features per split was the only substantial gain in E041–E050. Greater depth tied, while hard split pruning, L1, gradient row sampling, weaker L2, and removing Distance lost AUC. Approximate tree construction gained only 0.0001 at 2.5x training cost and was rejected. Disjoint date target encoding did not justify withholding one fifth of the training data. A rough trip-completion clock did not improve ranking.

Working theory: global date conditions and local schedule/airport interactions require flexible trees, but strong shrinkage and diverse split candidates are essential. Sparse high-cardinality interactions and extra numeric proxies have usually diluted the useful features. Next test objective-level confidence regularization, then categorical partition constraints and the limit of feature randomization.

Fresh research: https://arxiv.org/abs/2409.08647 discusses GBDT sensitivity to label noise, but there is no evidence these flight labels are incorrect; it is motivation for robustness, not grounds to delete or relabel records. https://arxiv.org/abs/1906.02629 motivates soft targets for confidence control in neural networks; transferring this to trees is an exploratory hypothesis. https://xgboost.readthedocs.io/en/stable/tutorials/custom_metric_obj.html documents custom gradients/Hessians. Installed sklearn-wrapper source confirms a callable binary objective retains the binary-logistic prediction link.

## E051 — soften binary targets by ten percent in the training objective

Commit: 6431386. Parent: 8164256. Classification: exploration.
Hypothesis: Replace the cross-entropy target y with 0.9*y+0.05 inside its gradient, preserving the logistic Hessian and prediction link. This may prevent confident fitting of unexplained flight variation. No records or evaluation labels change; the neural-network evidence is an analogy to be tested.
Source: https://arxiv.org/abs/1906.02629; https://xgboost.readthedocs.io/en/stable/tutorials/custom_metric_obj.html.
Result: **0.7641 AUC**, discard; previous best 0.7645. Run time: 33.1s (training 20.9s, eval 12.1s, ok)

## E052 — cap categorical partition search at sixteen categories under strong regularization

Commit: d50f4f6. Parent: 8164256. Classification: follow-up.
Hypothesis: E008 tested this cap before large L2 penalties and split randomization. Current trees repeatedly choose among many date and airport categories; a smaller partition search may reduce noisy category groupings after the larger regularization changes.
Source: https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-categorical-feature.
Result: **0.7549 AUC**, discard; previous best 0.7645. Run time: 25.2s (training 13.6s, eval 11.5s, ok)

## E053 — expand categorical partition search from sixty-four to 256

Commit: f7f6659. Parent: 8164256. Classification: follow-up.
Hypothesis: E052's smaller search lost 0.0096 AUC, suggesting date/airport category grouping is capacity-limited. Expanding the cap to 256 lets high-cardinality features form broader sorted partitions while the existing L2 and leaf-size penalties constrain their fitted effects.
Source: E052; https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-categorical-feature.
Result: **0.7622 AUC**, discard; previous best 0.7645. Run time: 30.0s (training 18.1s, eval 11.9s, ok)

## E054 — offer only one sampled feature at each split

Commit: 010fcbe. Parent: 8164256. Classification: follow-up.
Hypothesis: Reducing split candidates from four to three and then two improved AUC. Test the remaining discrete boundary, one of six features per split, to determine whether still greater tree diversity outweighs the cost of occasionally withholding important predictors.
Source: E036 and E043; https://xgboost.readthedocs.io/en/stable/tutorials/rf.html.
Result: **0.7611 AUC**, discard; previous best 0.7645. Run time: 26.9s (training 15.2s, eval 11.7s, ok)

## E055 — linearly decay the learning rate across one thousand rounds

Commit: 4b54c98. Parent: 8164256. Classification: exploration.
Hypothesis: Use rates from 0.055 to 0.005 across the existing 1000 rounds, preserving total learning-rate sum 30. Larger early steps fit broad patterns; smaller late steps may avoid chasing residual noise. The scheduler updates the next round after each completed iteration.
Source: https://xgboost.readthedocs.io/en/stable/python/python_api.html#xgboost.callback.LearningRateScheduler; https://jerryfriedman.su.domains/ftp/machine.pdf.
Result: **0.7638 AUC**, discard; previous best 0.7645. Run time: 28.4s (training 16.7s, eval 11.7s, ok)

## E056 — require five times more Hessian mass per leaf

Commit: bf78fa5. Parent: 8164256. Classification: follow-up.
Hypothesis: E029 benefited from min_child_weight=100, and feature subsampling now permits many different paths. Requiring 500 Hessian units may suppress weak small-subgroup interactions while retaining the strong date and schedule effects; it tests broader leaves rather than deeper/shallow tree limits.
Source: E029; https://xgboost.readthedocs.io/en/stable/parameter.html.
Result: **0.7634 AUC**, discard; previous best 0.7645. Run time: 26.0s (training 14.4s, eval 11.6s, ok)

## E057 — reduce departure-time sampling weight relative to other features

Commit: 0aba6b1. Parent: 8164256. Classification: exploration.
Hypothesis: CRSDepTime dominates gain, and stronger split randomization previously helped. Keep two candidate features per split but give departure time half the sampling weight of each other feature, testing whether earlier date/airport splits improve complementary interactions.
Source: https://xgboost.readthedocs.io/en/stable/python/examples/feature_weights.html; E036/E043.
Result: **0.7638 AUC**, discard; previous best 0.7645. Run time: 30.4s (training 18.6s, eval 11.8s, ok)

## E058 — add an explicit origin-destination route category

Commit: 14381aa. Parent: 8164256. Classification: exploration.
Hypothesis: A route category exposes corridor-specific congestion and operations that require several separate airport splits. Carrier-airport crosses failed, so this distinct interaction gets one guarded test with the current large leaf and L2 penalties; unknown training routes map to missing.
Source: https://www.faa.gov/air_traffic/publications/atpubs/foa_html/chap18_section_10.html; current-run interaction tests.
Result: **0.7591 AUC**, discard; previous best 0.7645. Run time: 38.1s (training 22.6s, eval 15.5s, ok)

## E059 — simplify to one tree per boosting step

Commit: 4ae4e94. Parent: 8164256. Classification: ablation/simplification.
Hypothesis: E037 halved the per-step forest from four trees to two without hurting AUC. Remove the remaining extra tree to test whether 1000 sequential randomized trees suffice, reducing training and artifact size if quality is retained.
Source: E037; https://xgboost.readthedocs.io/en/stable/tutorials/rf.html.
Result: **0.7643 AUC**, discard; previous best 0.7645. Run time: 18.7s (training 7.3s, eval 11.5s, ok)

## E060 — use sequential trees at matched total tree count and shrinkage

Commit: 7fb921d. Parent: 8164256. Classification: follow-up.
Hypothesis: The single-tree ablation E059 was only 0.0002 behind at half the tree count. Use 2000 rounds at eta=0.015 and no parallel forest, matching 2000 trees and total eta=30 while refreshing residuals between every tree instead of averaging two trees on the same residuals.
Source: E059; https://xgboost.readthedocs.io/en/stable/tutorials/rf.html.
Result: **0.7646 AUC**, keep; previous best 0.7645. Run time: 25.6s (training 13.6s, eval 11.9s, ok)

## Synthesis after E060

Best is now 0.7646 at 7fb921d. E060 replaces two parallel trees per step with one sequential tree, doubles the rounds, and halves eta. It keeps 2000 trees and total shrinkage 30, removes a parameter, and reduced training from about 17.5 to 13.6 seconds. This is a small gain with simpler code and lower cost.

Other recent tests constrain the useful model: one candidate feature per split was too restrictive; two remains best. Categorical search limits both below and above the default hurt, especially the smaller limit. Larger leaves, weighted feature sampling, soft targets, and decaying learning rates did not help. Explicit route categories again showed that sparse crosses generalize worse than separate airport fields.

Next directions: categorical/coarse clock representation, learning dynamics of the simpler sequential model, and possibly mixed-depth ensembles. Fresh research: https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html discusses numeric, categorical, and periodic representations of hour features. Only the representation ideas are relevant; its cross-validation workflow is not used here. The clock's nonmonotonic daily pattern makes grouping hour categories a distinct test from adding minute-of-hour or a trip-duration proxy.

## E061 — replace raw departure time with a categorical departure hour

Commit: a68f940. Parent: 7fb921d. Classification: exploration.
Hypothesis: The daily delay profile is nonmonotonic and minute-of-hour features did not help. Replacing HHMM with 24 hour categories lets native categorical splits group separated hours directly while discarding within-hour schedule detail. This preserves six model inputs.
Source: https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html.
Result: **0.7634 AUC**, discard; previous best 0.7646. Run time: 29.1s (training 15.7s, eval 13.5s, ok)

## E062 — halve the sequential learning rate and double boosting rounds

Commit: 17ba230. Parent: 7fb921d. Classification: follow-up.
Hypothesis: E012 benefited from smaller updates, and E060 now refreshes gradients after every tree. Doubling sequential rounds to 4000 while halving eta to 0.0075 preserves total shrinkage 30 and tests whether finer optimization improves the current strongly regularized model.
Source: E012/E060; https://jerryfriedman.su.domains/ftp/machine.pdf.
Result: **0.7646 AUC**, discard; previous best 0.7646. Run time: 41.0s (training 27.8s, eval 13.2s, ok)

## E063 — train with squared probability error and positive curvature approximation

Commit: 13255a7. Parent: 7fb921d. Classification: exploration.
Hypothesis: Optimize 2*(sigmoid(margin)-y)^2 instead of cross-entropy. Its gradient downweights confident residuals. Use positive Gauss-Newton curvature 4*[p*(1-p)]^2, which matches logistic curvature at p=0.5 and avoids negative Hessians. The logistic prediction link and harness AUC remain unchanged.
Source: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.brier_score_loss.html; https://xgboost.readthedocs.io/en/stable/tutorials/advanced_custom_obj.html.
Result: **0.7642 AUC**, discard; previous best 0.7646. Run time: 29.6s (training 17.7s, eval 11.9s, ok)
On synthetic margins, the analytic gradient matched finite differences within 1e-8; surrogate curvature stayed positive and equaled 0.25 at margin zero. No extra model evaluation metric was computed.

## E064 — average depth-six and depth-ten sequential boosters

Commit: ecdf37f. Parent: 7fb921d. Classification: exploration.
Hypothesis: A shallow model emphasizes broad effects while a deeper model captures local interactions. Average their probabilities equally using 2000 rounds each. Unlike E039's identical architectures with different seeds, this deliberately varies depth. Require a gain above 0.0003 to justify a second full model.
Source: https://www.cs.princeton.edu/courses/archive/spring10/cos424/papers/Dietterich-2000.pdf; https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html.
Result: **0.7643 AUC**, discard; previous best 0.7646. Run time: 39.0s (training 25.8s, eval 13.2s, ok)

## E065 — cap unshrunk leaf updates at 0.2 log-odds units

Commit: 4384dfe. Parent: 7fb921d. Classification: exploration.
Hypothesis: The best model's unshrunk absolute leaf outputs have median 0.069, 90th percentile 0.197, and maximum 1.062. A max_delta_step of 0.2 therefore targets roughly the largest tenth of existing updates, limiting abrupt subgroup corrections without shrinking every update further.
Source: Training-model introspection; https://xgboost.readthedocs.io/en/stable/parameter.html.
Result: **0.7632 AUC**, discard; previous best 0.7646. Run time: 25.1s (training 13.4s, eval 11.7s, ok)
Current best gain inspection shows FlightDate now exceeds CRSDepTime (52.0 vs 39.0), unlike the earlier snapshot that motivated E057. Trees have median 65 leaves, with 90th percentile 78; these are fitted-model statistics, not extra evaluation metrics.

## E066 — revisit distance-derived airport coordinates with the regularized sequential model

Commit: 9a5a69e. Parent: 7fb921d. Classification: follow-up.
Hypothesis: E016 had a small positive signal before strong L2, large leaves, and feature sampling. Fit an unsupervised 2D airport embedding from training-route median distances and shortest paths, then add four coordinate lookups. Sample three of ten columns to keep each column's inclusion probability near the previous two-of-six rate. Require over 0.001 gain for the extra preparation complexity.
Source: E016; https://scikit-learn.org/stable/modules/manifold.html#multidimensional-scaling; https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.shortest_path.html.
Result: **0.7652 AUC**, discard; previous best 0.7646. Run time: 33.9s (training 15.1s, eval 18.8s, ok)

## E067 — use direct training-route distances to LAX and ATL as airport coordinates

Commit: 32c7375. Parent: 7fb921d. Classification: ablation/simplification.
Hypothesis: E066 improved AUC by 0.0006 but its graph and MDS preparation was too complex. Replace that fit with median observed route distances to two fixed reference airports, LAX and ATL. These four row-local lookup features need no extra imports; unsupported airport-reference pairs remain missing. Sampling three of ten columns matches E066.
Source: E066; https://graphics.stanford.edu/courses/cs468-05-winter/Papers/Landmarks/Silva_landmarks5.pdf; analogy to landmark distance representations, not a full LMDS implementation..
Result: **0.7655 AUC**, keep; previous best 0.7646. Run time: 39.6s (training 21.1s, eval 18.5s, ok)

E067 artifact verification: training-row batch features exactly match concatenated single-row features; flipping supplied labels does not affect X. A synthetic unseen origin maps to missing in both its category and landmark distances, and prediction succeeds. No additional evaluation metric was used.

## E068 — simplify landmark geography to ATL alone

Commit: 10f926b. Parent: 32c7375. Classification: ablation/simplification.
Hypothesis: ATL has observed training connections to more airports than LAX. Test whether its distance alone captures the useful regional signal, removing two feature lookups and the sparse second reference. Keep three split candidates by using 0.4 column sampling across eight inputs.
Source: E067 and training-only landmark coverage inspection..
Result: **0.7650 AUC**, discard; previous best 0.7655. Run time: 35.9s (training 20.1s, eval 15.8s, ok)

## E069 — grow best-first trees with a sixty-four-leaf budget

Commit: 1570933. Parent: 32c7375. Classification: follow-up.
Hypothesis: Earlier lossguide testing used only 32 leaves before the later modeling changes. Recent best-model inspection found a median of 65 leaves per depth-limited tree. A 64-leaf best-first budget allocates comparable capacity to the most useful branches and may suit the new geographic interactions.
Source: E025/E065/E067; https://xgboost.readthedocs.io/en/stable/parameter.html.
Result: **0.7656 AUC**, keep; previous best 0.7655. Run time: 47.6s (training 28.9s, eval 18.7s, ok)

## E070 — remove direct route distance after adding landmark geography

Commit: 8b0a75f. Parent: 1570933. Classification: ablation/simplification.
Hypothesis: Unlike E050, the current model has four airport-to-landmark distance features. Direct route distance may now be redundant. Remove it while retaining three split candidates across the nine remaining inputs, using colsample_bynode=0.4.
Source: E050 versus E067/E069..
Result: **0.7649 AUC**, discard; previous best 0.7656. Run time: 46.2s (training 28.2s, eval 18.0s, ok)

## Synthesis after E070

Best is 0.7656 at 1570933. Training-fitted geography finally supplied a useful new signal: the full distance-graph/MDS embedding reached 0.7652 but remained too elaborate; direct median distances to LAX and ATL reached 0.7655 with about half the new code and no added imports. Both reference airports and direct route length survived ablation. Best-first growth with 64 leaves added 0.0001 over depth-eight growth; the gain is small, but only standard tree parameters changed.

Finer optimization at matched total shrinkage tied. Categorical departure hours, squared-probability training loss, mixed-depth averaging, and limiting large leaf updates lost AUC. The saved landmark model passed exact batch/row and label-independence checks and handled an unseen airport correctly.

New theory: broad physical similarity between airports is useful alongside their native categories and exact date, while explicit sparse route IDs overfit. Next inspect numeric split resolution and the balance between geographic inputs and original predictors; any extra geographic machinery still needs a meaningful gain. Fresh research: https://scikit-learn.org/stable/auto_examples/preprocessing/plot_discretization.html cautions that manual binning usually does not help trees. We will not assume it does; a native histogram-resolution test specifically asks whether coarse spatial regions are preferable to fine airport-distance thresholds. https://xgboost.readthedocs.io/en/stable/parameter.html documents max_bin and its split-search tradeoff.

## E071 — reduce numeric histogram resolution to sixty-four bins

Commit: 5851c0c. Parent: 1570933. Classification: exploration.
Hypothesis: The new landmark distances are numeric embeddings with at most 163 observed airports per reference. Coarser histogram cuts may pool nearby airports and suppress fine distance thresholds. Reduce max_bin from 256 to 64 without changing native category handling or introducing manual train/eval binning.
Source: https://xgboost.readthedocs.io/en/stable/parameter.html; https://scikit-learn.org/stable/auto_examples/preprocessing/plot_discretization.html.
Result: **0.7657 AUC**, keep; previous best 0.7656. Run time: 46.9s (training 28.1s, eval 18.8s, ok)

## E072 — use four training threads to reduce small-tree scheduling overhead

Commit: 0ad99f1. Parent: 5851c0c. Classification: ablation/simplification.
Hypothesis: Best-first growth builds many small 64-leaf trees on only ten columns. Four threads may reduce synchronization overhead relative to all eight CPUs, freeing training-budget headroom without changing features or tree hyperparameters. Retain an AUC tie only if training becomes faster.
Source: Current-run training timings and available eight CPUs; execution-efficiency hypothesis..
Result: **0.7657 AUC**, discard; previous best 0.7657. Run time: 48.7s (training 29.6s, eval 19.2s, ok)
Thread ablation: training 29.6s versus previous 28.1s.

## E073 — extend the geographic model to three thousand boosting rounds

Commit: 29d0917. Parent: 5851c0c. Classification: follow-up.
Hypothesis: The latest additions changed the feature space and tree growth rule. Unlike E062, which only refined step size at matched total shrinkage, this increases total shrinkage from 30 to 45 to test whether geographic interactions still have useful residual signal. At the observed 28s per 2000 rounds, 3000 leaves margin below the 60s training limit.
Source: E067/E069/E071; https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html.
Result: **0.7653 AUC**, discard; previous best 0.7657. Run time: 62.4s (training 42.9s, eval 19.4s, ok)

## E074 — remove destination identity while retaining destination geography

Commit: 135fd08. Parent: 5851c0c. Classification: ablation/simplification.
Hypothesis: Two landmark distances now represent destination location. Removing its high-cardinality category tests whether those physical features capture the transferable signal while avoiding airport-specific noise. Keep origin identity and direct route length, and preserve three split candidates across nine inputs.
Source: E067 geographic gain; current-run feature ablation evidence..
Result: **0.7650 AUC**, discard; previous best 0.7657. Run time: 42.9s (training 25.0s, eval 17.9s, ok)

## E075 — constrain daytime departure risk to increase while leaving overnight time flexible

Commit: c9a784e. Parent: 5851c0c. Classification: exploration.
Hypothesis: Training-only hourly delay fractions rise from about 0.19 at 05:00 to 0.65 at 20:00, then fall overnight. Clip the main clock to 05:00–21:00 and constrain it increasing; expose the original clock only outside that interval in an unconstrained NightDeparture feature. This tests a daytime shape prior without imposing global monotonicity on the full daily cycle.
Source: Training-only hourly target profile; https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html.
Result: **0.7620 AUC**, discard; previous best 0.7657. Run time: 53.8s (training 27.5s, eval 26.3s, ok)

## E076 — apply a light split-gain penalty to best-first trees

Commit: 20f1f80. Parent: 5851c0c. Classification: follow-up.
Hypothesis: Gamma=1 overpruned the earlier depth-limited model in E041. The current best-first model can keep adding leaves up to 64 without a depth cap, so a tenfold lighter gamma=0.1 may trim only weak late splits. This revisits split cost in a changed growth regime rather than repeating the earlier strong penalty.
Source: E041/E069; https://arxiv.org/abs/1603.02754; https://xgboost.readthedocs.io/en/stable/parameter.html.
Result: **0.7655 AUC**, discard; previous best 0.7657. Run time: 45.7s (training 26.9s, eval 18.8s, ok)

## E077 — increase L2 leaf shrinkage from 500 to two thousand

Commit: 4994b5d. Parent: 5851c0c. Classification: follow-up.
Hypothesis: L2 increases from 20 to 100 to 500 helped earlier, and reducing it to 100 failed under stronger randomization. With best-first trees and numeric geographic interactions now present, a fourfold larger penalty tests whether remaining subgroup effects need more continuous shrinkage; other complexity limits stay fixed.
Source: E011/E019/E026/E048; https://xgboost.readthedocs.io/en/stable/parameter.html.
Result: **0.7618 AUC**, discard; previous best 0.7657. Run time: 45.3s (training 26.5s, eval 18.8s, ok)

## E078 — reduce aggregate sampling weight of the four geographic lookups

Commit: ee6f84f. Parent: 5851c0c. Classification: follow-up.
Hypothesis: Four added landmark columns give geography four separate chances to enter each split's candidate set, despite being correlated encodings of two airports. Give each landmark column half weight while preserving three candidates, reducing this representation-induced sampling bias. Unlike E057, this reweights the new geographic group rather than departure time.
Source: E067; https://xgboost.readthedocs.io/en/stable/python/examples/feature_weights.html.
Result: **0.7646 AUC**, discard; previous best 0.7657. Run time: 48.8s (training 29.9s, eval 18.9s, ok)

## E079 — fill landmark distances through shortest paths in the training route graph

Commit: 3033612. Parent: 5851c0c. Classification: follow-up.
Hypothesis: Direct landmark lookup leaves many small airports without coordinates. Compute shortest route-distance paths to the same two landmarks using only the training graph, preserving direct distances when those routes exist and supplying geographic proxies elsewhere. Keep the same four features; require over 0.0003 gain for the extra graph construction.
Source: E066/E067; https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.shortest_path.html.
Result: **0.7656 AUC**, discard; previous best 0.7657. Run time: 40.4s (training 21.8s, eval 18.6s, ok)

## E080 — shorten the geographic model to fifteen hundred rounds

Commit: a2000d7. Parent: 5851c0c. Classification: ablation/simplification.
Hypothesis: Extending to 3000 rounds hurt in E073. Test the shorter side at 1500 rounds with eta unchanged, asking whether the current model can retain or improve ranking with one quarter fewer trees and less residual fitting.
Source: E073; https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html.
Result: **0.7643 AUC**, discard; previous best 0.7657. Run time: 40.2s (training 22.0s, eval 18.2s, ok)

## Synthesis after E080

Best remains 0.7657 at 5851c0c. Coarser numeric histograms (64 bins) gave a small gain. Three thousand rounds were worse, and fifteen hundred were also worse, supporting the present 2000-round horizon. L2=2000 was too strong, gamma=0.1 was slightly worse, and the daytime monotonic constraint substantially hurt despite its reasonable aggregate training-data trend. Destination identity remains useful alongside its landmark distances.

Reweighting the geographic features and filling missing landmark distances through the route graph did not improve on the direct two-reference lookups. Four training threads offered no speed benefit. The compact geographic representation, ordinary logistic loss, and moderate leaf regularization remain the strongest combination.

Fresh research: Breiman and Cutler explain that sampling fewer split features lowers both tree correlation and individual tree strength (https://www.stat.berkeley.edu/~breiman/forests/cc_home.htm; https://doi.org/10.1023/A:1010933404324). This is motivation, not a guarantee for boosting. A final sampling check will test two candidates in the expanded ten-feature representation; its current three-candidate choice originally preserved approximate per-column inclusion probability when geography was added.

## E081 — test two split candidates in the ten-feature geographic model

Commit: 68e96db. Parent: 5851c0c. Classification: follow-up.
Hypothesis: Two candidates were best with six original inputs. Adding four correlated geographic inputs led to three candidates to preserve approximate per-column inclusion. Test two again in this expanded representation to see whether lower inter-tree correlation offsets reduced access to date and time; this differs from the prior one-of-six boundary test.
Source: E043/E054/E067; https://www.stat.berkeley.edu/~breiman/forests/cc_home.htm.
Result: **0.7651 AUC**, discard; previous best 0.7657. Run time: 45.7s (training 27.2s, eval 18.5s, ok)
