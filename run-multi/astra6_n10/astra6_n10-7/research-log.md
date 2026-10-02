# Research log: oct2

## Setup — 2026-10-02

- Created branch `oct2` directly from the current HEAD, `92e43e6`.
- Read `program.md`, `README-autoresearch.md`, `train.py`, and `harness.py`.
- Verified that `data/train.csv` and `data/eval.csv` exist and are nonempty; checked only the training CSV header for the required columns.
- Verified imports: Python 3.14.4, pandas 3.0.6, NumPy 2.5.3, XGBoost 3.4.1, scikit-learn 1.9.1, cloudpickle 3.1.2. Eight CPU cores are visible.
- Initialized `results.tsv` with the required tab-separated header. Logs remain uncommitted.
- Training code is unchanged; no training or evaluation has run. The experiment clock has not started.

## Next steps after confirmation

1. Start the two-hour clock with `python3 harness.py start` as the first action.
2. Run the unchanged baseline via `python3 harness.py run > run.log 2>&1`, then record its commit and Eval AUC.
3. Research relevant external sources before the first non-baseline experiment, and document sources, hypotheses, results, and keep/discard decisions here.

Training is limited to 60 seconds and evaluation to 300 seconds per run. Only `train.py` may be edited as code; data access and evaluation follow `program.md`.

## Initial research and training-data inspection

The training set has 200,000 rows, eight predictors, no missing entries, and a 50% positive class rate. Calendar categories use `c-N` strings; there are 283 origins, 283 destinations, and 20 carriers. Departure time is HHMM, and distance ranges from 31 to 4,962. No class reweighting is needed for the balanced objective.

Sources read before the first non-baseline experiment:
- [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html): consider capacity, shrinkage, and regularization together.
- [XGBoost parameters, stable 3.4 documentation](https://xgboost.readthedocs.io/en/stable/parameter.html): relevant controls include depth, child weight, row/column subsampling, and categorical split thresholds. Initial candidates are depths 4–8, learning rates 0.03–0.1, child weights 1–50, and subsampling 0.7–1.0; these are hypotheses for this dataset, not universal optima.
- [Native categorical support](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html): compare partitioning with one-category splits if overfitting emerges. The latest page documents future 3.5 defaults, so explicitly configure any comparison rather than assuming its defaults match installed 3.4.1.
- [Time-related feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html): investigate hour/minute and ordered calendar representations; trees may already capture many periodic effects without sine/cosine features.

## Experiment 1 — baseline — 92e43e6

Unchanged starter: 30 trees, depth 6, learning rate 0.1. Eval AUC **0.7203**; training phase 1.1s, evaluation 30.9s. **Keep** as the baseline. Plenty of training-time headroom.

## Experiment 2 — exploration: boosting capacity

Hypothesis: 30 boosting rounds underfit the airline interactions. Increase only the number of trees to 300, retaining depth 6 and learning rate 0.1. Motivated by the baseline's short training time and the tuning notes above.

Outcome: **86f06f2**, Eval AUC **0.7342**, training 2.5s, evaluation 31.0s. **Keep** (+0.0139). More capacity clearly helps.

## Experiment 3 — follow-up: smaller boosting steps

Hypothesis: 600 rounds at learning rate 0.05, keeping depth 6, may learn smoother interactions than 300 rounds at 0.1 with similar total boosting strength. This follows the shrinkage guidance in the initial XGBoost tuning source.

Outcome: **9a08261**, Eval AUC **0.7359**, training 4.5s, evaluation 31.6s. **Keep** (+0.0017). Smaller updates help at equal total shrinkage.

## Experiment 4 — exploration: calendar-date interaction

Hypothesis: a combined month/day categorical feature can capture date-specific conditions shared across flights, which separate month and day categories make harder to learn. Add only this feature, keeping the 600-tree model fixed. [Airport delay research](https://arxiv.org/abs/2601.00875) identifies weather and operational context as relevant; using date as a proxy is our inference, not a claim demonstrated by that paper. No external flight or weather data is used. Levels are fitted on train, and features depend on each row alone.

Outcome: **0610ff7**, Eval AUC **0.7525**, **keep** (delta +0.0166). Run time: 40.4s (training 4.4s, eval 36.0s, ok) The combined date representation adds substantial predictive information.

## Experiment 5 — follow-up: regularize small leaves

Hypothesis: date-aware categorical trees can overfit small subgroups. Raise min_child_weight from 1 to 20 while keeping 600 rounds, eta 0.05, and depth 6 fixed. Larger leaves should reduce noisy interactions; see the initial XGBoost parameter research.

Outcome: **da019c7**, Eval AUC **0.7525**, **discard** (delta +0.0000). Run time: 40.2s (training 4.3s, eval 35.9s, ok) Equal reported AUC with an extra setting; revert under the keep/discard rule.

## Experiment 6 — follow-up: deeper regularized interactions

Hypothesis: depth 6 limits date/airport/time interactions. Test depth 8 with min_child_weight 20 to control the additional small-leaf variance. Experiment 5 showed that this leaf threshold did not hurt depth-6 AUC, making it a reasonable guard for the deeper model. The standalone threshold change was discarded; this trial tests a distinct capacity regime.

Outcome: **aefd472**, Eval AUC **0.7495**, **discard** (delta -0.0030). Run time: 43.1s (training 6.6s, eval 36.5s, ok) The extra interaction capacity reduced generalization; retain the depth-6 model.

## Experiment 7 — simplification: categorical preprocessing

Hypothesis: removing redundant isin/where checks preserves all features and makes row-wise evaluation faster. [pandas.Categorical documentation](https://pandas.pydata.org/docs/reference/api/pandas.Categorical.html) confirms that unknown levels become missing automatically. Compare old/new features, including an unseen origin, before the official run.

Outcome: **4e7c32a**, Eval AUC **0.7525**, **keep** (delta +0.0000). Run time: 31.0s (training 4.4s, eval 26.6s, ok) Exact AUC preserved while evaluation dropped from 36.0s to 26.3s; keep for simpler and faster code. Installed pandas emits a future-version warning for unseen categories but current behavior is verified.

## Experiment 8 — follow-up: ordered calendar representation

Hypothesis: numeric day-of-year lets trees express contiguous seasonal/event intervals, complementing the date category. Keep existing features and model settings fixed. Inspired by the initial time-feature engineering source; all date values are calculated from each row with a calendar lookup built from training levels.

Outcome: **a84fa01**, Eval AUC **0.7527**, **keep** (delta +0.0002). Run time: 33.9s (training 4.5s, eval 29.5s, ok) Small gain from a straightforward calendar feature; retain for subsequent interaction tests.

## Experiment 9 — exploration: one-category splits

Hypothesis: one-category splits may generalize better than gradient-sorted category groups for the date/airport effects. Set max_cat_to_onehot=512, above all current cardinalities, keeping all other settings fixed. Numeric day-of-year still permits contiguous date splits. Source: the native categorical XGBoost documentation linked in initial research; the saved baseline config confirmed installed default max_cat_to_onehot=4.

Outcome: **33f2906**, Eval AUC **0.7427**, **discard** (delta -0.0100). Run time: 32.4s (training 3.1s, eval 29.3s, ok) Substantial AUC loss; grouped categories are beneficial on this dataset.

## Experiment 10 — follow-up: conservative categorical partitions

Hypothesis: Grouped categories outperformed one-category splits by 0.0100 AUC. Restrict max_cat_threshold from 64 to 16 while retaining partitioning, testing whether smaller candidate category groups reduce overfitting. Source: initial XGBoost parameter documentation.

Outcome: **122407c**, Eval AUC **0.7513**, **discard** (delta -0.0014). Run time: 33.2s (training 3.8s, eval 29.4s, ok) Restricting category groups lost 0.0014 AUC; retain the default threshold 64.

## Synthesis after 10 experiments

Best: **a84fa01, 0.7527 AUC**, versus baseline 0.7203. More rounds and smaller updates helped, but the largest feature gain came from a joint date category. Day-of-year added only 0.0002 and remains an ablation candidate. Depth 8 lost accuracy even with larger leaves; child weight alone was neutral. Grouped categorical splits were substantially better than one-category splits, and reducing the categorical threshold also hurt. Simplifying preprocessing preserved predictions and saved about 10 seconds per evaluation.

Current theory: shared calendar conditions and smooth time-of-day effects dominate, while excessive interaction capacity overfits. Next test explicit route and carrier-airport context, departure-time decomposition, and stronger shrinkage/regularization.

Research refresh: searched flight-delay feature engineering and read [XGBoost early-stopping documentation](https://xgboost.readthedocs.io/en/stable/python/sklearn_estimator.html). A later trial can reserve part of train.csv for stopping and score only via the official harness; no cross-validation or retraining will be added. [Spatio-Temporal Data Mining for Aviation Delay Prediction](https://arxiv.org/abs/2103.11221) motivates examining route/time context; our categorical route feature is a simpler hypothesis using only the available columns.

## Experiment 11 — exploration: explicit route identity

Hypothesis: A train-fitted origin-destination category may expose route-specific operational patterns without requiring deeper trees. Retain all other features and hyperparameters. Route/time context was suggested by the refreshed aviation research; unseen routes map to missing.

Outcome: **0e413ca**, Eval AUC **0.7322**, **discard** (delta -0.0205). Run time: 40.0s (training 6.9s, eval 33.1s, ok) The high-cardinality route category sharply reduced AUC; do not retain raw route identity.

## Experiment 12 — exploration: departure-time decomposition

Hypothesis: Separate hour and minute-of-hour features expose repeated scheduling patterns without high-cardinality categorical interactions. Retain raw HHMM and all calendar features. Source: the initial scikit-learn time-related feature engineering example.

Outcome: **6fe547a**, Eval AUC **0.7518**, **discard** (delta -0.0009). Run time: 37.0s (training 4.5s, eval 32.5s, ok) Extra schedule columns reduced AUC by 0.0009 and added evaluation overhead.

## Experiment 13 — follow-up: shallower ensemble

Hypothesis: Depth 8 hurt, suggesting interaction variance is a problem. Test depth 4 with 1200 rounds at eta 0.05: fewer leaves per tree, with more boosting steps to recover main effects. Keep the best feature representation fixed. Source: initial XGBoost bias-variance tuning notes.

Outcome: **1f91ad2**, Eval AUC **0.7535**, **keep** (delta +0.0008). Run time: 34.4s (training 4.9s, eval 29.5s, ok) Shallower trees improved AUC with a smaller artifact, supporting the variance-control hypothesis.

## Experiment 14 — follow-up: L2 leaf regularization

Hypothesis: The shallow-tree gain suggests reducing variance. Increase reg_lambda from 1 to 20 to shrink noisy leaf estimates, retaining depth 4, 1200 rounds, and eta 0.05. Source: XGBoost parameter documentation.

Outcome: **4b6e930**, Eval AUC **0.7561**, **keep** (delta +0.0026). Run time: 34.1s (training 5.0s, eval 29.1s, ok) L2 regularization improved AUC by 0.0026, the strongest recent parameter gain.

## Experiment 15 — follow-up: interaction capacity after regularization

Hypothesis: L2=20 improved the shallow ensemble. With this stronger regularizer, depth 6 may now recover useful date-airport interactions that previously overfit. Change only depth from 4 to 6, retaining 1200 rounds at eta 0.05.

Outcome: **b40ab90**, Eval AUC **0.7507**, **discard** (delta -0.0054). Run time: 38.0s (training 8.2s, eval 29.8s, ok) Additional depth still hurts after L2 regularization; restore the shallow best model.

## Experiment 16 — ablation/simplification: remove redundant calendar categories

Hypothesis: Month, day-of-month, and weekday have low gain importance once the full date is included. Remove these three model inputs while retaining Date and DayOfYear, testing simpler preprocessing and less noisy split choice. Their raw columns remain available solely to derive the date.

Outcome: **a33523a**, Eval AUC **0.7562**, **keep** (delta +0.0001). Run time: 27.4s (training 4.7s, eval 22.6s, ok) Simpler six-plus-one-feature representation slightly improved AUC and saved about seven evaluation seconds.

## Experiment 17 — ablation/simplification: remove numeric day-of-year

Hypothesis: The date category appears to subsume most calendar effects. DayOfYear had very low gain importance and added only 0.0002 before regularization; remove it and its lookup/import to test a six-feature model.

Outcome: **0cee784**, Eval AUC **0.7567**, **keep** (delta +0.0005). Run time: 25.0s (training 5.6s, eval 19.4s, ok) Removing the weak numeric calendar feature improved AUC and shortened preprocessing.

## Experiment 18 — exploration: stochastic row sampling

Hypothesis: Sample 80% of rows for each tree to reduce correlated fitting errors in the shallow regularized ensemble. Keep all six features available at each split and all other settings fixed. Source: XGBoost tuning notes on randomness.

Outcome: **d0474bb**, Eval AUC **0.7500**, **discard** (delta -0.0067). Run time: 25.6s (training 6.2s, eval 19.4s, ok) Sampling alone hurt substantially, likely making categorical estimates less stable.

## Experiment 19 — exploration: boosted forest

Hypothesis: Single sampled trees were unstable. Average four randomized trees per boosting step, with row and per-node feature sampling at 0.8, to reduce that variance while retaining the shallow model. This is a different ensemble architecture, not a repeat of row sampling alone. Source: https://xgboost.readthedocs.io/en/stable/tutorials/rf.html.

Outcome: **6ac8e4a**, Eval AUC **0.7537**, **discard** (delta -0.0030). Run time: 44.7s (training 24.2s, eval 20.5s, ok) Averaging helps relative to single sampled trees but remains worse than full-data boosting and costs more training time.

## Experiment 20 — exploration: training-only early stopping

Hypothesis: Let 5% of train.csv determine a suitable number of smaller boosting steps, using up to 4000 rounds at eta 0.03 and patience 100. Fit once on the other 95%, without cross-validation or a full-data refit. Only harness Eval AUC determines keep/discard. Source: https://xgboost.readthedocs.io/en/stable/python/sklearn_estimator.html.

Outcome: **3670bc6**, Eval AUC **0.7549**, **discard** (delta -0.0018). Run time: 26.1s (training 6.0s, eval 20.0s, ok) Validation-guided stopping did not beat full-data training; discard without retraining.

## Synthesis after 20 experiments

Best: **0cee784, 0.7567 AUC**. Shallow depth-4 trees and L2=20 outperform deeper models. Removing separate calendar categories and numeric day-of-year improved AUC and cut evaluation to about 19 seconds. Raw route identity and departure hour/minute additions hurt. Row sampling is particularly harmful; four-tree boosted forests recover some loss but remain below full-data boosting. A 95/5 training-only early-stopping split selected 1422 rounds at eta 0.03 but scored 0.7549.

The strongest current theory is that low-variance categorical estimates matter more than extra interaction capacity. Next test interaction constraints, modest-cardinality carrier/calendar combinations, and a smoother boosting schedule.

Research refresh: read [boosted forests](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html), [interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html), and [target-encoding leakage examples](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html). The last source reinforces caution with high-cardinality supervised lookups; if tested, use disjoint reference rows rather than encoding a training row with its own outcome. No cross-validation evaluation is introduced.

## Experiment 21 — exploration: separate origin and destination interactions

Hypothesis: Prevent Origin and Dest from appearing together on a tree path while allowing each to interact with time, carrier, distance, and date. The raw route-category failure suggests detailed route effects may overfit. This is an inferred regularization hypothesis, supported mechanistically by the XGBoost interaction-constraint documentation.

Outcome: **439ab7a**, Eval AUC **0.7559**, **discard** (delta -0.0008). Run time: 24.1s (training 4.6s, eval 19.5s, ok) Verified zero joint airport paths versus 9461 in the unconstrained model, but AUC decreased; the restriction removes useful signal.

## Experiment 22 — exploration: carrier-specific seasonal effects

Hypothesis: A carrier-month category has at most 240 levels and may capture stable airline-specific seasonal effects without the thousands of sparse route identities that failed earlier. All levels are fitted on train; no target statistics are used. Inference motivated by airline/calendar factors in the aviation research refresh.

Outcome: **a45d447**, Eval AUC **0.7565**, **discard** (delta -0.0002). Run time: 27.7s (training 4.8s, eval 22.8s, ok) Nearly matched the best score but added feature complexity and evaluation cost without an improvement.

## Experiment 23 — follow-up: stronger L2 bound

Hypothesis: L2=20 produced a meaningful gain. Test L2=100 to bracket whether additional shrinkage improves the stable six-feature, depth-4 model or introduces underfitting. Change only this parameter.

Outcome: **b7b50f7**, Eval AUC **0.7578**, **keep** (delta +0.0011). Run time: 24.4s (training 4.7s, eval 19.7s, ok) Further shrinkage improved AUC by 0.0011, confirming that the model benefits from stronger regularization.

## Experiment 24 — follow-up: smaller steps for the regularized model

Hypothesis: Halve eta to 0.025 and double rounds to 2400, holding total boosting strength at 60. Smaller steps helped in the initial model; this tests whether that benefit persists after substantial regularization and feature simplification.

Outcome: **5f1fa86**, Eval AUC **0.7587**, **keep** (delta +0.0009). Run time: 28.1s (training 8.3s, eval 19.8s, ok) Smaller steps improved AUC by 0.0009 with unchanged feature complexity.

## Experiment 25 — exploration: route-relative departure time

Hypothesis: A numeric deviation from the training route median may express schedule position with less variance than a raw route category. Fit medians only on train, then apply fixed lookups per row; unseen routes yield missing values. No counts or target means are features. Source: the program.md lookup example and https://scikit-learn.org/stable/common_pitfalls.html on consistent train-fitted preprocessing.

Outcome: **9e72671**, Eval AUC **0.7576**, **discard** (delta -0.0011). Run time: 34.0s (training 9.7s, eval 24.3s, ok) Train-only numeric route context did not improve AUC and added preprocessing cost.

## Experiment 26 — exploration: pairwise ranking objective

Hypothesis: Pairwise logistic loss may improve ordering directly relative to pointwise classification loss. Treat all training examples as one ranking group, sample one pair per row, and use 1200 depth-4 rounds at eta 0.05 with L2=100. A small subclass exposes sigmoid-transformed ranking scores through predict_proba; this is a monotonic score transform and the unchanged harness computes the sole comparison metric. Source: https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html.

Outcome: **b955514**, Eval AUC **0.7507**, **discard** (delta -0.0080). Run time: 69.7s (training 49.9s, eval 19.7s, ok) Training took 49.9s and AUC was 0.7507, well below logistic boosting; discard the extra model wrapper.

## Experiment 27 — exploration: coarser numeric histograms

Hypothesis: Reduce max_bin from 256 to 64 to smooth split candidates for the two numerical features (HHMM departure time and distance). Categorical resolution remains unchanged. This tests numeric granularity as a regularizer after the consistent gains from simpler models. Source: initial XGBoost max_bin parameter documentation.

Outcome: **7cf8d45**, Eval AUC **0.7579**, **discard** (delta -0.0008). Run time: 28.4s (training 8.5s, eval 19.9s, ok) Coarser numeric split candidates slightly hurt; restore 256 bins.

## Experiment 28 — exploration: disjoint-reference airport-date rates

Hypothesis: Airport-specific daily conditions may be missing from the six-feature model. Reserve a deterministic 25% of train.csv solely to fit origin/date and destination/date mean delay lookups; fit XGBoost once on the disjoint 75%. Each model-training row therefore has no own-label contribution to its features. No cross-validation, refit, frequency/count feature, or extra evaluation is used. Unknown keys map to missing. Source: https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html, adapted with one separate reference split rather than cross-fitting.

Outcome: **1786ca1**, Eval AUC **0.7518**, **discard** (delta -0.0069). Run time: 32.6s (training 10.2s, eval 22.5s, ok) The reference-split model underperformed; a matched control is needed to separate the loss of fit rows from the new features.

## Experiment 29 — ablation/simplification: reference-split control

Hypothesis: Use exactly the same 75% model-training rows as experiment 28, but remove both airport-date rate features. Comparing the two official Eval AUCs isolates whether those features helped enough to offset reserving reference rows. This control informs whether to continue that category of research.

Outcome: **50c58d5**, Eval AUC **0.7507**, **discard** (delta -0.0080). Run time: 26.6s (training 6.9s, eval 19.8s, ok) Control AUC 0.7507 versus 0.7518 with rates: the rates add 0.0011 but cannot offset the loss of model-training data.

## Experiment 30 — exploration: distance-derived airport geometry

Hypothesis: Approximate regional structure may let shallow trees pool nearby airports with shared conditions. Build an undirected graph of training route distances, complete it with shortest paths, then fit a two-dimensional classical scaling embedding. Add the two coordinates for each endpoint via fixed lookups. No external geographic dataset, labels, or frequency/count features are used. Source: https://scikit-learn.org/stable/modules/generated/sklearn.manifold.Isomap.html.

Outcome: **32f0067**, Eval AUC **0.7585**, **discard** (delta -0.0002). Run time: 33.3s (training 9.4s, eval 23.9s, ok) The connected-graph embedding was valid and row-invariant, but AUC did not improve; discard 24 added lines and four extra features.

## Synthesis after 30 experiments

Best: **5f1fa86, 0.7587 AUC** (six features, depth 4, 2400 rounds, eta 0.025, L2=100). Stronger L2 and smaller updates delivered the gains in this group. Interaction restrictions, carrier-month identity, coarser bins, route-relative time, and a distance-derived airport embedding failed to improve the best score. Pairwise ranking fit within 60s but was much slower and substantially worse.

A deliberately disjoint-reference target-encoding experiment scored 0.7518; its matched reduced-data control scored 0.7507. The two airport/date rates carry some information, but reserving 25% of training data loses more than they recover. No own-row target leakage, cross-validation metric, or count features were used. Full-data training remains valuable.

Research refresh: studied [Isomap](https://scikit-learn.org/stable/modules/generated/sklearn.manifold.Isomap.html), [categorical threshold semantics](https://github.com/dmlc/xgboost/issues/10844), and [honest categorical splitting discussion](https://github.com/dmlc/xgboost/issues/12130), along with lossguide/max_leaves in the official parameters. Next examine wider categorical partition search and leaf-wise capacity, then L1/split regularization. The discussion of categorical overfitting is consistent with our poor high-cardinality route result; it does not imply that an unimplemented RFC parameter is available.

## Experiment 31 — follow-up: wider categorical partition search

Hypothesis: The threshold-16 trial hurt, and date/airport cardinalities exceed the default 64. Increase max_cat_threshold to 256 to allow a wider set of grouped categorical splits, while retaining the stronger L2=100 regularizer. Source: https://github.com/dmlc/xgboost/issues/10844 and the XGBoost categorical parameters.

Outcome: **4195995**, Eval AUC **0.7566**, **discard** (delta -0.0021). Run time: 29.9s (training 10.1s, eval 19.8s, ok) Wider categorical search overfits relative to the default 64 under this configuration; revert.

## Experiment 32 — exploration: leaf-wise growth with a fixed leaf budget

Hypothesis: Use lossguide growth, max_leaves=16, and no depth cap. This retains the nominal leaf budget of a depth-4 tree but allows asymmetric allocation to harder subproblems. It tests tree shape, not unrestricted added capacity. Source: the refreshed XGBoost grow_policy/max_leaves documentation.

Outcome: **f24ef3b**, Eval AUC **0.7566**, **discard** (delta -0.0021). Run time: 29.4s (training 9.4s, eval 20.0s, ok) Asymmetric leaf allocation did not beat depth-wise growth at the same nominal leaf budget.

## Experiment 33 — follow-up: L1 regularization of weak leaves

Hypothesis: Add reg_alpha=10 alongside L2=100 to suppress weak leaf effects, testing a different regularization mechanism from uniformly shrinking every leaf. Keep depth, rounds, features, and learning rate fixed. Source: the XGBoost regularized tree objective and parameter documentation.

Outcome: **c8954f4**, Eval AUC **0.7547**, **discard** (delta -0.0040). Run time: 27.1s (training 7.4s, eval 19.7s, ok) L1 suppression removed useful weak effects and reduced AUC by 0.0040.

## Experiment 34 — ablation/simplification: shorter boosting horizon

Hypothesis: Halve boosting rounds from 2400 to 1200 while retaining eta 0.025, depth 4, and L2=100. This tests whether late rounds overfit and whether the current model can be simplified; unlike prior learning-rate trials it halves total boosting strength.

Outcome: **2e934ca**, Eval AUC **0.7559**, **discard** (delta -0.0028). Run time: 24.2s (training 4.6s, eval 19.6s, ok) Removing late rounds lost 0.0028 AUC; the best model has not simply overtrained past 1200 rounds.

## Experiment 35 — follow-up: longer boosting horizon

Hypothesis: Since 1200 rounds underfit relative to 2400, test 4800 rounds at the same eta 0.025 to bracket the useful training horizon. Keep all regularization and features fixed; this is the upper side of the deliberate horizon comparison.

Outcome: **c63c034**, Eval AUC **0.7533**, **discard** (delta -0.0054). Run time: 36.5s (training 16.0s, eval 20.5s, ok) The upper horizon clearly overfits. Together with the 1200-round ablation this brackets the useful horizon around the kept 2400-round model.

## Experiment 36 — exploration: deterministic histogram ensemble

Hypothesis: Average the best 256-bin model with a 64-bin model. The coarser individual model was only 0.0008 behind; different numerical split candidates may yield complementary categorical partitions. Both train on all rows using the same six features. Soft voting changes only the trained model; the harness is unchanged. Source: scikit-learn VotingClassifier documentation.

Outcome: **33a6f00**, Eval AUC **0.7596**, **keep** (delta +0.0009). Run time: 36.6s (training 16.0s, eval 20.6s, ok) Averaging improved AUC by 0.0009 with a small standard-library composition; retain. Source: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html.

## Experiment 37 — follow-up: finer-resolution ensemble member

Hypothesis: The coarse/standard ensemble improved ranking, suggesting complementary partition errors. Add an equally weighted 1024-bin model to cover a distinctly finer numerical resolution while keeping all training rows, six features, and other hyperparameters identical.

Outcome: **057723a**, Eval AUC **0.7599**, **keep** (delta +0.0003). Run time: 47.2s (training 26.2s, eval 21.0s, ok) The finer-resolution member added 0.0003 AUC and total training remained at 26.2 seconds.

## Experiment 38 — follow-up: interaction-depth ensemble diversity

Hypothesis: Add a depth-5, 1200-round member to the three-resolution ensemble. It has roughly the same maximum total leaf count as a depth-4, 2400-round member but allocates capacity to deeper interactions. Averaging may retain useful deeper effects while controlling their standalone variance.

Outcome: **eaf5184**, Eval AUC **0.7602**, **keep** (delta +0.0003). Run time: 49.9s (training 28.4s, eval 21.4s, ok) Depth diversity added 0.0003 AUC while the whole ensemble trained in 28.4 seconds.

## Experiment 39 — follow-up: shallow ensemble complement

Hypothesis: The deeper member improved the ensemble. Add a depth-3, 3600-round member to supply smoother low-order effects from the other side of the capacity range. All models retain full training data and L2=100, and fit sequentially within the same harness run.

Outcome: **07d68f9**, Eval AUC **0.7604**, **keep** (delta +0.0002). Run time: 59.9s (training 37.9s, eval 22.0s, ok) A smoother member added 0.0002 AUC; five models still fit in 37.9 seconds.

## Experiment 40 — ablation/simplification: remove the finest-bin ensemble member

Hypothesis: After adding both shallower and deeper models, the 1024-bin member may be redundant. Remove it to test whether depth diversity preserves accuracy with one fewer fitted model and roughly ten seconds less training.

Outcome: **f339c7a**, Eval AUC **0.7604**, **keep** (delta +0.0000). Run time: 51.1s (training 29.5s, eval 21.6s, ok) AUC stayed at 0.7604 while training fell from 37.9s to 29.5s; retain the simpler four-model ensemble.

## Synthesis after 40 experiments

Best: **f339c7a, 0.7604 AUC**, now a four-model soft-voting ensemble on the same six features. Wider categorical partitions, leaf-wise growth, and L1 regularization failed. The 1200/2400/4800-round bracket favored 2400 for the depth-4 base model. Deterministic diversity across histogram resolution and depths 3–5 improved the ensemble. After depth diversity was added, removing the expensive 1024-bin member preserved AUC and saved about nine training seconds.

The useful distinction is between adding complexity to one learner (often harmful) and averaging complementary regularized learners (helpful). Next test feature sampling with full row data and revisit regularization in the ensemble.

Research refresh: [feature-weight sampling example](https://xgboost.readthedocs.io/en/stable/python/examples/feature_weights.html), [custom-objective documentation](https://xgboost.readthedocs.io/en/stable/tutorials/custom_metric_obj.html), and [soft voting](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html). Feature weights affect selection probabilities when column sampling is enabled; a trial can favor time/date without dropping training rows. Any custom-loss trial would preserve the official evaluation metric and its final save call.

## Experiment 41 — exploration: weighted per-node feature sampling

Hypothesis: Keep all training rows but sample 80% of columns per node, with weights [2,1,1,1,1,2] in feature order (departure time, distance, carrier, origin, destination, date). Favoring the strong time/date signals may avoid unstable categorical competition while allowing ensemble diversity. This differs from the failed row-sampling trial. Source: XGBoost feature_weights example.

Outcome: **a700dab**, Eval AUC **0.7614**, **keep** (delta +0.0010). Run time: 52.1s (training 30.6s, eval 21.4s, ok) Feature sampling improved AUC by 0.0010 while preserving stable full-data category estimates; keep.

## Experiment 42 — follow-up: one-category carrier splits only

Hypothesis: Set max_cat_to_onehot=32. With the current six features, only the 20-level carrier becomes one-category splitting; 283-level airports and the 365-level date remain partitioned. This isolates a lower-cardinality alternative from experiment 9, which changed all categories at once. Source: native categorical split documentation.

Outcome: **8010ef6**, Eval AUC **0.7562**, **discard** (delta -0.0052). Run time: 50.7s (training 28.9s, eval 21.8s, ok) Carrier-only one-category splits reduced AUC by 0.0052; grouped carrier splits remain preferable.

## Experiment 43 — follow-up: weaker L2 in the sampled ensemble

Hypothesis: Reduce reg_lambda from 100 to 20 for all four full-data ensemble members. Earlier single-model results favored 100, but soft averaging and feature sampling now reduce variance and may permit less biased leaves. This specifically tests whether the earlier regularization choice transfers to the ensemble. Source: https://xgboost.readthedocs.io/en/stable/parameter.html.

Outcome: **5af517c**, Eval AUC **0.7602**, **discard** (delta -0.0012). Run time: 52.9s (training 30.7s, eval 22.3s, ok) Averaging and feature sampling did not remove the need for strong leaf shrinkage; revert weaker L2.

## Experiment 44 — follow-up: stronger L2 bracket for the ensemble

Hypothesis: Increase reg_lambda from 100 to 300 for all four members. The weaker-L2 ensemble lost 0.0012 AUC; testing the other side of the current value distinguishes a shrinkage-limited ensemble from one already near its useful regularization level. Source: https://xgboost.readthedocs.io/en/stable/parameter.html.

Outcome: **31cee35**, Eval AUC **0.7611**, **discard** (delta -0.0003). Run time: 52.5s (training 30.5s, eval 22.0s, ok) Stronger L2 was closer than weaker L2 but still lost 0.0003 AUC. Keep reg_lambda=100.

## Experiment 45 — ablation/simplification: remove the weak distance feature

Hypothesis: Remove Distance, leaving five predictors, and remove its feature-sampling weight. The saved best model's training split-gain shares assign Distance only 0.3%-0.4% for each member, whereas origin and destination already identify the route endpoints. Gain is not a generalization metric; this controlled harness ablation tests whether the weak feature is redundant or harmful.

Outcome: **029d654**, Eval AUC **0.7608**, **discard** (delta -0.0006). Run time: 54.0s (training 32.9s, eval 21.1s, ok) Despite little training split gain, dropping Distance lost 0.0006 AUC. Retain it. A training-only diagnostic also confirmed each of the 365 dates has exactly one weekday, supporting the previous removal of redundant calendar columns.

## Experiment 46 — exploration: label-smoothed logistic objective

Hypothesis: Use 5% uniform label smoothing: logistic targets become 0.025 and 0.975. The gradient is sigmoid(margin)-target and the nonnegative Hessian is p*(1-p). This preserves ordering of the ideal conditional probabilities while discouraging extreme margins. Adapted from https://arxiv.org/abs/1906.02629 (neural-network evidence, not established XGBoost evidence). API source: https://xgboost.readthedocs.io/en/stable/tutorials/custom_metric_obj.html; installed sklearn wrapper confirms binary:logistic remains the prediction link. Evaluation is unchanged.

Outcome: **db29fc0**, Eval AUC **0.7611**, **discard** (delta -0.0003). Run time: 67.7s (training 45.8s, eval 22.0s, ok) Gradient, Hessian, and binary shape checks passed, and training stayed within 60 seconds. AUC fell 0.0003 with about 15 seconds of extra training, so discard the custom objective.

### Plateau review after experiment 46

The last three discards moved AUC by only 0.0003–0.0006. Research refresh: [XGBoost column sampling](https://xgboost.readthedocs.io/en/stable/parameter.html) distinguishes node/tree sampling and weighted selection; [scikit-learn gradient boosting](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.GradientBoostingClassifier.html) documents the variance/bias tradeoff of restricting candidate features. The experiment-41 gain combined sampling with unequal weights. Before increasing sampling strength, ablate the unequal weights to identify their contribution.

## Experiment 47 — ablation/simplification: uniform feature sampling

Hypothesis: Remove feature_weights while retaining colsample_bynode=0.8. Experiment 41 combined these changes; this ablation separates the benefit of sampling from favoring departure time/date. Equal or better AUC would remove a hand-chosen vector. Sources: XGBoost column-sampling documentation and the plateau review.

Outcome: **7bef006**, Eval AUC **0.7610**, **discard** (delta -0.0004). Run time: 51.1s (training 29.3s, eval 21.8s, ok) Uniform sampling lost 0.0004 AUC. The unequal weights contribute part of the improvement from experiment 41; retain them.

## Experiment 48 — follow-up: stronger node-level column sampling

Hypothesis: Reduce colsample_bynode from 0.8 to 0.5 while retaining the now-supported time/date weights and all training rows. With six features this reduces candidate columns per node from four to three, testing a stronger variance-reduction mechanism rather than changing sample weights or rows. Source: https://xgboost.readthedocs.io/en/stable/parameter.html.

Outcome: **c839b06**, Eval AUC **0.7620**, **keep** (delta +0.0006). Run time: 52.0s (training 30.5s, eval 21.6s, ok) Reducing the candidate set from four to three raised AUC by 0.0006 without added code or material runtime cost. Keep stronger node-level sampling.

## Experiment 49 — follow-up: tree-level versus node-level feature sampling

Hypothesis: Move the same 0.5 weighted column sampling from each node to each entire tree. The candidate count remains three, but each tree now learns interactions only within its sampled features, potentially reducing fragile high-order interactions. Node sampling allowed different feature sets at different nodes. Source: https://xgboost.readthedocs.io/en/stable/parameter.html.

Outcome: **b1de4b3**, Eval AUC **0.7604**, **discard** (delta -0.0016). Run time: 50.4s (training 28.9s, eval 21.5s, ok) Tree-level sampling reduced AUC by 0.0016. Allowing different features at different nodes is valuable; retain node-level sampling.

## Experiment 50 — exploration: one DART member within the training budget

Hypothesis: Replace the standard histogram ensemble member with a 256-round, learning-rate-0.2 DART member (rate_drop=0.1, skip_drop=0.9), leaving the other three members fixed. The smaller tree count budgets for DART recomputing predictions; its nominal boosting horizon is close to the 2400*0.025 baseline. Tree dropout may address late-tree over-specialization differently from column sampling. This is a compute-constrained architecture comparison, not an isolated drop-rate effect. Sources: https://xgboost.readthedocs.io/en/stable/tutorials/dart.html and https://arxiv.org/abs/1505.01866.

Outcome: **c0da13c**, Eval AUC **0.7619**, **discard** (delta -0.0001). Run time: 72.4s (training 51.3s, eval 21.1s, ok) DART stayed within the training limit but achieved 0.7619, just below the best, while adding roughly 21 training seconds. Retain ordinary boosted trees.

## Synthesis after 50 experiments

Best: **c839b06, 0.7620 AUC**. Weighted node-level feature sampling improved the four-model ensemble from 0.7604 to 0.7620. Favoring departure time/date helped relative to uniform sampling, and three candidates per split beat four. Sampling once per tree hurt, suggesting useful interactions need different feature choices along paths. Both weaker and stronger L2 lost; the current 100 remains preferable. Removing Distance hurt despite its low training gain, so training importance alone is an inadequate deletion rule. Label smoothing and a budget-limited DART member came close but added runtime without improving AUC.

Research refresh: [DART](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) and its [original paper](https://arxiv.org/abs/1505.01866) motivated trial 50. [Generalized ensemble means](https://proceedings.mlr.press/v337/razafindralambo26a.html) distinguishes probability averaging from logit averaging; its analysis concerns likelihood rather than guaranteeing AUC gains. Test logit aggregation with unchanged learners, then use a matched ordinary-boosting control for the fast-learning DART member to distinguish dropout from learning-rate diversity. Continue controlled simplifications and investigate supported carrier/airport interactions.

## Experiment 51 — exploration: average logits instead of probabilities

Hypothesis: Keep all four fitted learners unchanged but average their raw binary margins, then apply sigmoid. This geometric pooling may preserve ranking information that averaging saturated probabilities compresses. No weight fitting or extra evaluation is introduced. Source: https://proceedings.mlr.press/v337/razafindralambo26a.html; this is an AUC hypothesis, not a claimed consequence of its likelihood results.

Outcome: **635acd6**, Eval AUC **0.7620**, **discard** (delta +0.0000). Run time: 52.6s (training 30.7s, eval 21.8s, ok) Analytic aggregation and extreme-margin checks passed. Logit pooling tied AUC at 0.7620 but added a custom subclass and imports, so retain simpler built-in soft voting.

## Experiment 52 — follow-up: matched ordinary-boosting control for DART

Hypothesis: Replace the standard member with a 256-round, learning-rate-0.2 ordinary boosted model. This matches experiment 50 except for dropout and tests whether its near-tie came from a faster-learning, structurally different member. All other parameters and the other three members are unchanged.

Outcome: **da2bdaf**, Eval AUC **0.7621**, **keep** (delta +0.0001). Run time: 45.3s (training 24.0s, eval 21.3s, ok) Ordinary boosting slightly improved AUC to 0.7621 and cut training by about seven seconds versus the previous best, and by 27 seconds versus DART. Keep the simpler, faster member; learning-rate diversity was more useful than dropout.

## Experiment 53 — exploration: explicit carrier-origin interaction

Hypothesis: Append a native categorical carrier-origin key (1551 training levels), preserving the individual columns and giving the new feature sampling weight 1. Carrier-specific operations at an airport may be captured more directly than by successive splits, especially in shallow sampled trees. This is a proxy inferred from https://www.eurocontrol.int/publication/propagation-air-transport-delays-europe, not a measurement of hub status or prior-flight delay. All levels are fixed from train; no counts or external data become features.

Outcome: **d53b484**, Eval AUC **0.7592**, **discard** (delta -0.0029). Run time: 53.4s (training 24.9s, eval 28.5s, ok) Batch/single-row and unseen-key checks passed. AUC dropped 0.0029 and preparation added several evaluation seconds; the explicit 1551-level interaction overcomplicates the model. Revert.

## Experiment 54 — follow-up: minimum split-gain regularization

Hypothesis: Add gamma=5 to all members to reject low-gain splits. Training-only inspection of the best artifact's final quarter of trees found split-gain medians near 15-18 and 10th percentiles 0.2-2, so 5 targets the lower-gain tail without suppressing most typical splits. This acts on tree structure rather than leaf shrinkage. Source: https://xgboost.readthedocs.io/en/stable/parameter.html.

Outcome: **2680143**, Eval AUC **0.7477**, **discard** (delta -0.0144). Run time: 32.1s (training 12.3s, eval 19.9s, ok) AUC fell sharply to 0.7477. Inspection of the saved coarse member found 1933/2400 unsplit trees versus zero in the prior best. Its best-model final-quarter root gain median was only 0.222 (all-node median was 17), explaining why a threshold chosen from all-node gains prevented useful deeper interactions. Revert.

## Experiment 55 — follow-up: root-aware light split pruning

Hypothesis: Set gamma=0.1, below the final-quarter root-gain 10th percentile of 0.196 in the best coarse member. Experiment 54 revealed that low-gain roots can open valuable deeper interactions; this much lighter threshold tests whether near-zero splits can be removed without shutting down boosting. Source: https://xgboost.readthedocs.io/en/stable/parameter.html.

Outcome: **77c7dda**, Eval AUC **0.7621**, **discard** (delta +0.0000). Run time: 44.7s (training 23.7s, eval 21.0s, ok) Light pruning restored normal training but tied AUC at 0.7621 and offered no material simplification or speed benefit. Keep default gamma=0.

## Experiment 56 — follow-up: minimum leaf support in the ensemble

Hypothesis: Set min_child_weight=100 across the ensemble. The best model's late-tree leaf-cover 10th percentile is about 100 for depth-4 members but only 15 for depth 5. A minimum Hessian mass of 100 should mainly prevent small, unstable leaves while preserving low-gain roots that gamma pruning incorrectly removed. This is stronger than the early min_child_weight=20 trial and is tested under the now very different sampled ensemble. Source: https://xgboost.readthedocs.io/en/stable/parameter.html.

Outcome: **3da5e30**, Eval AUC **0.7622**, **keep** (delta +0.0001). Run time: 44.0s (training 22.8s, eval 21.2s, ok) AUC increased slightly to 0.7622 and training became about one second faster. A single regularization parameter restricts small leaves without blocking useful low-gain roots; keep.

## Experiment 57 — follow-up: two candidate features per split

Hypothesis: Reduce colsample_bynode from 0.5 to 0.34, which selects two of six features instead of three. Four-to-three helped, and this final lower bracket tests whether stronger diversity still outweighs bias after minimum leaf support was added. Keep time/date weights and full training data unchanged. Source: https://xgboost.readthedocs.io/en/stable/parameter.html.

Outcome: **fe49e99**, Eval AUC **0.7629**, **keep** (delta +0.0007). Run time: 44.5s (training 23.6s, eval 20.8s, ok) Two candidates per node improved AUC by 0.0007 without extra code or runtime. Keep stronger sampling.

## Experiment 58 — follow-up: one candidate feature per split

Hypothesis: Set colsample_bynode=0.2, selecting one of six columns per node while retaining weighted selection and all rows. Four-to-three and three-to-two candidate reductions both helped. This endpoint tests whether eliminating competition among features further suppresses unstable split selection or instead adds too much bias. It is the final possible candidate-count reduction. Source: https://xgboost.readthedocs.io/en/stable/parameter.html.

Outcome: **40ea133**, Eval AUC **0.7578**, **discard** (delta -0.0051). Run time: 41.9s (training 21.2s, eval 20.7s, ok) The single-feature endpoint lost 0.0051 AUC. The candidate-count bracket now favors two; further randomization introduces too much bias. Revert.

## Experiment 59 — ablation/simplification: remove the shallowest ensemble member

Hypothesis: Remove the depth-3, 3600-round member. After stronger node sampling, this already shallow learner may add bias more than useful diversity. Removing it would simplify the ensemble and save substantial training time if AUC is preserved. The other three members stay fixed.

Outcome: **2cbf05f**, Eval AUC **0.7631**, **keep** (delta +0.0002). Run time: 34.8s (training 14.3s, eval 20.5s, ok) Simplification win: AUC increased to 0.7631 and training dropped from about 24 to 14 seconds. Retain the three-member ensemble.

## Experiment 60 — ablation/simplification: remove the fast-learning ensemble member

Hypothesis: Remove the 256-round, learning-rate-0.2 member, retaining the coarse depth-4 and standard depth-5 learners. The shallow-member ablation helped, and the fast member has greater per-tree updates than the remaining learners. This checks whether its diversity still compensates for that extra variance in the now smaller ensemble.

Outcome: **a31ccbd**, Eval AUC **0.7631**, **keep** (delta +0.0000). Run time: 34.5s (training 14.3s, eval 20.2s, ok) AUC tied at 0.7631 with only two learners. Remove the unnecessary fast member; this is an exact-score simplification win.

## Synthesis after 60 experiments

Best: **a31ccbd, 0.7631 AUC**, with two learners: coarse depth 4 and standard depth 5. The three/four/two/one candidate-feature comparisons show two is best; one causes underfitting. A minimum child Hessian mass of 100 gave a small gain. Removing shallow and fast-learning ensemble members improved or preserved AUC, reducing complexity and training time. Logit pooling tied ordinary soft voting, so the custom class was discarded. Carrier-origin categories hurt. Strong split-gain pruning failed because root gains can be tiny even when their descendants are useful: 1933 of 2400 coarse-model trees became unsplit. Light pruning tied but was unnecessary.

Research refresh: [XGBoost tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) discusses direct complexity control versus stochastic regularization; [ensemble quality/diversity research](https://proceedings.mlr.press/v224/purucker23b.html) reinforces that diversity alone is not sufficient and selection can overfit. We do not implement post-hoc selection or additional evaluations. Next test a depth-6 member under existing leaf support, then remaining targeted checks on categorical partition size and sampling weights. Keep using the harness as the sole performance metric.

## Experiment 61 — follow-up: deeper interaction member with fixed leaf support

Hypothesis: Add a depth-6, 600-round member with the same learning rate, minimum child support, and two-column node sampling. Removing shallow models helped, suggesting remaining bias may be in higher-order interactions. This member has the same nominal full-tree leaf budget as depth 5 at 1200 rounds, and the current training time leaves ample room. This is a controlled structural-diversity test, not a claim that more models always help.

Outcome: **24d9b80**, Eval AUC **0.7625**, **discard** (delta -0.0006). Run time: 37.1s (training 16.5s, eval 20.6s, ok) The additional deeper member lost 0.0006 AUC. Retain the simpler two-model ensemble.

## Experiment 62 — follow-up: restrict categorical partition search in the regularized ensemble

Hypothesis: Set max_cat_threshold=16. The early trial of 16 used a deeper, weakly regularized single model; the current two-member ensemble has L2=100, minimum child mass=100, and two feature candidates per node. Restricting category subsets may now suppress residual adaptive split noise. The prior widening to 256 hurt. Source: https://xgboost.readthedocs.io/en/stable/parameter.html.

Outcome: **72cda73**, Eval AUC **0.7500**, **discard** (delta -0.0131). Run time: 31.3s (training 11.2s, eval 20.1s, ok) AUC dropped sharply to 0.7500. The current model needs broader category partitions; retain the default threshold of 64.

## Experiment 63 — follow-up: finer boosting steps within the freed training budget

Hypothesis: Halve learning_rate from 0.025 to 0.0125 and double rounds for both members (4800 depth-4, 2400 depth-5). The nominal boosting horizon stays fixed. Earlier smaller steps helped the single model; the simplified ensemble now has enough training headroom to test this under two-feature sampling. Source: https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html.

Outcome: **1700078**, Eval AUC **0.7625**, **discard** (delta -0.0006). Run time: 46.8s (training 25.3s, eval 21.5s, ok) Finer steps lost 0.0006 AUC and nearly doubled training time. Retain learning_rate=0.025 and the shorter learners.

## Experiment 64 — follow-up: stronger preference for time and date in feature sampling

Hypothesis: Raise the sampling weights of departure time and date from 2 to 4, leaving the other four weights at 1. With only two candidate columns, this reduces how often both dominant signals are absent. Uniform weights previously hurt; this tests whether the stronger candidate restriction now needs a stronger preference for these signals.

Outcome: **450bfc4**, Eval AUC **0.7615**, **discard** (delta -0.0016). Run time: 34.2s (training 13.9s, eval 20.3s, ok) Stronger preference lost 0.0016 AUC. The milder 2:1 weights balance dominant signals and airport interactions better; revert.

## Experiment 65 — ablation/simplification: single depth-5 model

Hypothesis: Remove the coarse depth-4 member and the voting wrapper, retaining the depth-5 learner unchanged. Two earlier ensemble members proved unnecessary after stronger sampling. This tests whether the final averaging step is still worth its code and runtime.

Outcome: **96e3b8c**, Eval AUC **0.7618**, **discard** (delta -0.0013). Run time: 26.2s (training 6.6s, eval 19.6s, ok) The single learner scored 0.7618, losing 0.0013 AUC. The final ensemble still adds useful performance; revert.

## Experiment 66 — ablation/simplification: single coarse depth-4 model

Hypothesis: Retain only the coarse depth-4 learner, unchanged, and remove the voting wrapper. The depth-5-only trial underperformed; this complementary ablation checks whether the other remaining learner is already sufficient.

Outcome: **dfd8b70**, Eval AUC **0.7624**, **discard** (delta -0.0007). Run time: 28.6s (training 8.6s, eval 20.0s, ok) The coarse learner scored 0.7624, below the two-model 0.7631. Both constituent ablations underperform, supporting the final pair.

## Experiment 67 — follow-up: stronger minimum leaf support

Hypothesis: Increase min_child_weight from 100 to 500. The first increase helped slightly, and stronger support may reduce noisy categorical subsets remaining under two-feature sampling. This upper bracket should reveal whether the current value is under-regularized or whether useful smaller interactions would be lost. Source: https://xgboost.readthedocs.io/en/stable/parameter.html.

Outcome: **ca6101c**, Eval AUC **0.7630**, **discard** (delta -0.0001). Run time: 33.6s (training 13.3s, eval 20.4s, ok) Stronger leaf support reached 0.7630, slightly below 0.7631. Retain the lighter minimum of 100.

## Experiment 68 — follow-up: coarser numeric histogram in one ensemble member

Hypothesis: Reduce max_bin from 64 to 16 only in the depth-4 member. Date and airport handling stay unchanged; coarser departure-time/distance boundaries may provide stronger smoothing alongside the depth-5 member's default 256-bin resolution. Earlier histogram diversity helped. Source: https://xgboost.readthedocs.io/en/stable/parameter.html; any regularization benefit is an empirical hypothesis.

Outcome: **91d250d**, Eval AUC **0.7632**, **keep** (delta +0.0001). Run time: 33.8s (training 13.5s, eval 20.3s, ok) AUC increased slightly to 0.7632 at the same runtime and code complexity. Retain the more strongly smoothed numeric member.

## Experiment 69 — follow-up: upper bracket for numeric smoothing

Hypothesis: Reduce only the coarse member's max_bin from 16 to 4, another fourfold coarsening. The 64-to-16 change helped; this endpoint tests whether very broad numeric bands remain complementary to the depth-5 member or discard useful timing detail.

Outcome: **dabd8f4**, Eval AUC **0.7632**, **keep** (delta +0.0000). Run time: 33.7s (training 13.5s, eval 20.2s, ok) AUC tied at 0.7632 with fewer available numeric cut points and unchanged runtime. Keep the simpler numeric representation in the coarse learner.

## Experiment 70 — follow-up: additional fine-resolution depth-4 member

Hypothesis: Add a standard 256-bin depth-4 learner alongside the four-bin depth-4 and standard depth-5 pair. Earlier histogram diversity helped; this tests whether fine numeric resolution at the same depth adds useful information beyond changing depth alone. Retain only an improvement that justifies the extra member.

Outcome: **99da25c**, Eval AUC **0.7638**, **keep** (delta +0.0006). Run time: 42.4s (training 21.1s, eval 21.3s, ok) The additional fine-resolution learner improved AUC by 0.0006 to 0.7638 with training still about 21 seconds. Keep the three-model ensemble.

## Synthesis after 70 experiments

Best: **99da25c, 0.7638 AUC**. Both single-model ablations lost AUC, confirming useful averaging. A depth-6 member hurt; a fine-resolution depth-4 member helped. The coarse numeric member tolerated reduction from 64 to 16 and then four bins; stronger time/date sampling weights and restrictive categorical partitions hurt. Doubling rounds while halving the learning rate also lost, as did stronger minimum leaf support. The useful combination is shallow regularized learners, broad categorical partitions, strong but not extreme feature sampling, and contrasting numeric resolution.

Research refresh: [LearningRateScheduler API](https://xgboost.readthedocs.io/en/stable/python/python_api.html#xgboost.callback.LearningRateScheduler) supports a possible future decaying-step experiment. For the remaining time, test a longer horizon at the current fixed rate; this differs from the failed finer-step trial, which preserved the horizon.

## Experiment 71 — follow-up: longer horizon under strong feature sampling

Hypothesis: Increase both depth-4 learners from 2400 to 3600 rounds and the depth-5 learner from 1200 to 1800, keeping learning_rate=0.025. Two-column sampling may need a longer fit than the earlier unsampled single model. Unlike experiment 63, this increases total boosting strength rather than only refining step size. All members remain within the observed runtime headroom.

Outcome: **10d2bfa**, Eval AUC **0.7644**, **keep** (delta +0.0006). Run time: 56.0s (training 34.0s, eval 22.0s, ok) The longer fit improved AUC by 0.0006 to 0.7644, with training safely within the 60-second limit at 34.0 seconds. Keep this final model.

## Final summary

The two-hour experiment is complete on branch **oct2**. Ran **71** experiments: 28 kept, 43 discarded, and 0 crashes. Baseline Eval AUC was **0.7203**; best kept Eval AUC is **0.7644** (**+0.0441**), at commit **10d2bfa**.

The final model averages three XGBoost classifiers: standard: depth 4, 3600 rounds, max_bin 256; coarse: depth 4, 3600 rounds, max_bin 4; deeper: depth 5, 1800 rounds, max_bin 256. It uses six features: scheduled departure time, distance, carrier, origin, destination, and the month/day categorical date. Shared regularization includes L2=100, minimum child Hessian mass=100, and weighted sampling of two feature candidates per node, favoring time/date. All training rows are retained.

What worked: the full date feature, shallow regularized trees, removing redundant calendar columns, full-data column sampling, complementary histogram/depth models, and pruning unnecessary ensemble members. What did not: row subsampling, raw route/carrier-origin combinations, disjoint-reference target rates, graph-derived coordinates, ranking loss, label smoothing, strong split-gain pruning, restrictive categorical partitions, excessive feature randomness, and the compute-limited DART alternative. Both remaining model families benefited from averaging; individual-model ablations were worse.

The final audit verified clean committed train.py, that no other tracked file changed, one valid results row per trial, artifacts for every successful run, equality of saved/current preparation, batch-versus-single-row feature parity, and finite normalized saved-model predictions. All measured AUC values came from the unmodified harness. The final save_and_evaluate call remains last.

Next: test a decaying learning-rate schedule within the same training limit and investigate more robust categorical split regularization without sacrificing training rows. The LearningRateScheduler source is linked in the experiment-70 synthesis. Preserve the current simple feature set unless a new interaction passes a controlled ablation. Further performance claims require the separate human-run held-out evaluation; no held-out data was inspected in this experiment.

results.tsv, research-log.md, and timing/ are intentionally uncommitted. Saved artifacts and timing records were preserved.
