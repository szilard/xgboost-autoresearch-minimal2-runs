# Experiment: oct2

## Setup — 2026-10-02

- Created branch `oct2` from the existing HEAD, `92e43e6`.
- Read `program.md`, `README-autoresearch.md`, `train.py`, and `harness.py`.
- Verified that `data/train.csv` and `data/eval.csv` exist. Inspected only the training data: 200,000 rows, all required columns present, Y/N target, and no missing values in the required columns.
- Verified installed dependencies: Python 3.14.4, pandas 3.0.6, XGBoost 3.4.1, scikit-learn 1.9.1, cloudpickle 3.1.2, and NumPy 2.5.3.
- Initialized `results.tsv` with its header only. No model has been trained or evaluated during setup; the experiment clock has not started.
- Confirmed `train.py` is syntactically valid and ends with `save_and_evaluate(model, prepare)`; its baseline code is unchanged.

Setup incident: the initial inspection inadvertently read the human-only `prepare.py` before the restriction in `program.md` was seen. It was neither executed nor changed. No evaluation or held-out data contents were inspected. The incident was disclosed to the user; subsequent work follows the access restrictions, and experiment design will not rely on that file's contents.

Next step, after the user's confirmation: run `python3 harness.py start` as the first action, then establish the baseline with the unchanged training script via the harness. Research external sources before the first non-baseline experiment.

## Experiment 1 — baseline — 92e43e6

Unchanged starter: 30 trees, depth 6, learning rate 0.1, native categorical inputs. Eval AUC **0.7203**; training 1.1 s including startup, evaluation 30.5 s. Kept as baseline.

## Initial research

Read the [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html), [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html), and [categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html). The relevant tradeoff is boosting capacity versus regularization: assess additional rounds before increasing interaction depth; later compare learning rates, minimum leaf weight, and row sampling. Categorical partition splits can group levels with similar responses. Candidate ranges are deliberate coarse probes (100–1000 rounds, depth 4–10, learning rate 0.03–0.15), not claimed universal optima. Also searched for tabular/airline temporal feature engineering; will read more before adding features.

## Experiment 2 — exploration: boosting capacity

Hypothesis: the starter's 30 trees underfit, so 300 trees with the same depth and learning rate should learn additional useful effects. Change only n_estimators from 30 to 300. Source: XGBoost tuning guide above.

Result: commit `4e15148`, Eval AUC **0.7342** (+0.0139), training 2.5 s, evaluation 31.1 s. Keep. More boosting helps substantially without approaching the training limit.

## Experiment 3 — follow-up: remaining boosting headroom

Hypothesis: extending 300 to 800 rounds will show whether the improvement is still limited by the boosting horizon. Preserve all other settings to isolate this effect; based on experiment 2 and the initial XGBoost tuning research.

Result: `619950d`, Eval AUC **0.7273** (-0.0069 versus kept), training 5.3 s, evaluation 31.0 s. Discard. Extra rounds at depth 6 hurt generalization.

## Experiment 4 — ablation/simplification: shallower trees

Hypothesis: the overfitting observed in experiment 3 suggests reducing per-tree complexity. Starting from kept experiment 2, test depth 4 instead of 6 at 300 rounds. Source: XGBoost's bias/variance and depth guidance, linked above.

Result: `08ba18e`, Eval AUC **0.7343**, training 1.9 s, evaluation 31.0 s. Keep: slightly higher AUC with artifact size reduced from 7.5 MB to 2.1 MB. Gain importance in the prior model showed scheduled departure time dominating, with calendar/carrier/airport effects also used; this is descriptive model structure, not another evaluation metric.

## Experiment 5 — exploration: ordered calendar feature

Hypothesis: combining month and day into ordinal day-of-year makes contiguous seasonal effects easier to split than two unordered categorical columns. Keep the original features and add one row-local numeric feature for a non-leap year. Source: [scikit-learn time feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html), which discusses complementary calendar representations. This is an adaptation to the available airline columns, not a claimed result from that example.

Result: `3e548cc`, Eval AUC **0.7382** (+0.0039), training 1.9 s, evaluation 34.8 s. Keep. Batch versus single-row features matched exactly on 20 sampled training rows.

## Experiment 6 — follow-up: categorical date effects

Hypothesis: daily operational conditions can differ sharply between neighboring dates. Add a categorical day-of-year alongside its numeric version, allowing XGBoost's partition splits to pool dates with similar residuals. Source: [XGBoost categorical partitioning](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html). Fixed categories 1–365 keep row preparation consistent.

Result: `7fecc6a`, Eval AUC **0.7521**, keep. Run time: 39.3s (training 2.0s, eval 37.3s, ok)

AUC improves by 0.0139. Daily effects are more useful when partitionable, motivating interaction-capacity tests.

## Experiment 7 — follow-up: Test depth six with explicit date features

Categorical date produced the largest feature gain so far. Increase depth 4 to 6 at 300 rounds to expose date-by-airport/carrier effects. This differs from the earlier depth comparison because date now enters each tree as a single feature. Source: initial XGBoost depth and categorical-partitioning documentation.

Result: `95d3f4e`, Eval AUC **0.7500**, discard. Run time: 39.8s (training 2.7s, eval 37.1s, ok)

AUC decreases by 0.0021 despite richer date features. Retain depth 4.

## Experiment 8 — ablation/simplification: Remove redundant categorical membership masking

pd.Categorical with fixed categories already maps unseen values to missing. Remove the preceding isin/where pass without changing features, reducing per-row preparation work. Source: https://pandas.pydata.org/docs/reference/api/pandas.Categorical.html . This is a simplicity/performance experiment; retain only if the harness AUC is unchanged.

Result: `fb947a7`, Eval AUC **0.7521**, keep. Run time: 30.2s (training 2.0s, eval 28.3s, ok)

Exact old/new feature equality passed, including an unseen airport; batch/single-row equality and independence from input target also passed. Evaluation fell from 37.3 s to 28.3 s. The installed pandas emits a future-version deprecation warning for unknown categories, but behavior remains correct in this environment.

## Experiment 9 — follow-up: Use smaller boosting steps for date features

Test learning_rate 0.05 with 600 rounds instead of 0.1 with 300. Preserve approximate total shrinkage while letting later categorical partitions adapt in smaller steps; distinct from simply adding rounds in experiment 3. Source: XGBoost tuning guide recommends coupling reduced eta with increased rounds.

Result: `fe7ff17`, Eval AUC **0.7530**, keep. Run time: 31.7s (training 3.8s, eval 27.9s, ok)

AUC improves by 0.0009 with only a parameter change; keep despite the additional trees.

## Experiment 10 — exploration: Expose scheduled departure hour and minute

Split scheduled HHMM into a categorical hour (for non-monotonic time-of-day effects) and numeric minute (for recurring schedule banks). Keep original CRSDepTime, so this adds accessible structure instead of losing fine timing. Source: the scikit-learn time feature example cited in experiment 5. Airport-context relevance is also motivated by Shao et al., https://arxiv.org/abs/1911.01605 ; its traffic/weather inputs are unavailable here, so no such external data is used.

Result: `1f49f4f`, Eval AUC **0.7534**, keep. Run time: 36.0s (training 3.2s, eval 32.9s, ok)

AUC improves by 0.0004 with two simple row-local features. Batch/single-row and target-independence checks pass.

## Synthesis after 10 experiments

Best: **0.7534** at `1f49f4f`, versus baseline 0.7203 (+0.0331). Additional boosting helps only until variance dominates. Depth 4 outperforms or matches depth 6; categorical day-of-year contributes the strongest feature gain. Smaller updates help modestly, and hour/minute decomposition has a small benefit. Simpler categorical preparation preserves AUC and saves about nine evaluation seconds. Current theory: shared daily conditions plus departure schedule explain substantial signal, while unconstrained higher-order interactions fit noise.

New research: searched categorical regularization, feature interactions, and boosted random forests. Read [XGBoost forest/boosting documentation](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) and the abstract of [Goyal et al., Feature Interactions in XGBoost](https://arxiv.org/abs/2007.05758). Candidate directions: explicit route/carrier-airport categories, carefully regularized deeper trees, row/feature subsampling, and eventually multiple trees per boosting round. The interaction paper motivates structured interactions generally; the proposed airline combinations are our own hypothesis. No cross-validation or alternative scoring is introduced.

## Experiment 11 — exploration: Add origin-destination route category

Route-specific operating patterns may be easier to capture through a single categorical split than repeated origin/destination splits. Fit the route vocabulary on train and construct each row's key independently. This uses the native categorical partitioning already researched; the airline pairing is a domain hypothesis following the ten-experiment synthesis.

Result: `97f6dd3`, Eval AUC **0.7351**, discard. Run time: 50.3s (training 4.6s, eval 45.7s, ok)

AUC falls by 0.0183 and artifact size grows to 36.2 MB. Explicit sparse route grouping is strongly counterproductive despite passing row-local feature checks.

## Experiment 12 — exploration: Regularize small leaves and leaf weights

High-cardinality route partitions failed badly and deeper unregularized trees also hurt. On the kept date model, raise min_child_weight to 20 and reg_lambda to 10 to suppress small, unstable leaves and shrink their scores. Source: XGBoost parameter reference and tuning guide; these regulate leaf structure and leaf weights respectively.

Result: `3c912ac`, Eval AUC **0.7552**, keep. Run time: 35.7s (training 3.1s, eval 32.6s, ok)

AUC improves by 0.0018 with two parameter changes; the variance-control hypothesis is supported.

## Experiment 13 — follow-up: Test deeper interactions with leaf regularization

Experiment 12 reduced variance at depth 4. Test depth 6 while retaining min_child_weight 20 and reg_lambda 10. This revisits the earlier depth failure under materially stronger regularization and smaller boosting steps, to determine whether useful higher-order interactions were obscured by noisy leaves.

Result: `fa064ca`, Eval AUC **0.7548**, discard. Run time: 37.6s (training 5.0s, eval 32.7s, ok)

AUC is 0.0004 lower and the model is substantially larger; retain the simpler depth-4 model.

## Experiment 14 — exploration: Test stochastic row and feature sampling

The shallower model remains strongest. Set subsample=0.8 and colsample_bytree=0.8 to reduce dependence on individual observations and dominant feature splits while averaging 600 trees. Source: XGBoost parameter-tuning guide's stochastic regularization and the forest documentation reviewed at the first synthesis.

Result: `06ab417`, Eval AUC **0.7497**, discard. Run time: 36.1s (training 3.5s, eval 32.6s, ok)

AUC falls by 0.0055. The categorical date/airport learner appears sensitive to reduced data or excluded predictors; combined sampling is not useful at this stage.

## Experiment 15 — exploration: Select boosting horizon with training-only early stopping

A fixed 600-round horizon may be suboptimal. Reserve a stratified 10% of train.csv for early stopping, cap training at 1500 rounds with patience 60 and AUC monitoring, and save that single model without retraining. No cross-validation or alternative experiment metric is added. Source: https://xgboost.readthedocs.io/en/stable/python/sklearn_estimator.html .

Result: `fd91846`, Eval AUC **0.7522**, discard. Run time: 36.2s (training 3.9s, eval 32.3s, ok)

AUC falls by 0.0030. Early stopping on a 10% training split does not offset the reduction in fitting data. Return to the single model fitted on all training rows.

## Experiment 16 — exploration: Learn airport geography proxies from route distances

After three unhelpful regularization/horizon variants, investigate structure rather than more nearby parameter tweaks. Fit a two-dimensional classical scaling embedding of undirected shortest-path route distances using only train.csv. Airport coordinates may share regional seasonal effects across airports without sparse route categories. No targets, traffic counts, or external airport data enter the lookup. Sources: https://scikit-learn.org/1.9/modules/manifold.html (Isomap/shortest-path embedding) and https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.shortest_path.html . Geographic usefulness here is an experimental hypothesis.

Result: `bdb5f31`, Eval AUC **0.7546**, discard. Run time: 43.3s (training 3.4s, eval 39.9s, ok)

AUC falls by 0.0006, and preparation is slower. The connected 284-airport graph and feature checks were valid, but this geographic proxy does not justify 24 added lines.

## Experiment 17 — ablation/simplification: Remove redundant day-of-month category

Date and DayOfYear already identify the calendar day. The separate DayofMonth category may encourage spurious pooling of the same numbered day across unrelated months. Remove only that input, retaining its raw value solely to construct the date features. Motivated by the strong date result and repeated complexity failures.

Result: `bd8578f`, Eval AUC **0.7550**, discard. Run time: 33.0s (training 3.0s, eval 30.0s, ok)

AUC falls by 0.0002. Removing one feature saves about three evaluation seconds but is not a large enough simplification to favor it over the kept model.

## Experiment 18 — exploration: Restrict categorical partition candidates

Native categorical partitioning is central to the date gain but high-cardinality grouping overfits. Set max_cat_threshold=16 versus the observed default 64, retaining all rows/features and existing leaf regularization. This specifically limits categorical split search rather than general depth or stochastic sampling. Source: XGBoost categorical parameter documentation reviewed above.

Result: `7720389`, Eval AUC **0.7489**, discard. Run time: 35.8s (training 2.9s, eval 32.9s, ok)

AUC falls by 0.0063. Restricting categorical split candidates is substantially worse; the model benefits from broader category grouping.

## Experiment 19 — follow-up: Allow broader categorical partition search

The restrictive threshold failed sharply. Increase max_cat_threshold from default 64 to 256, allowing a much broader search for group partitions across 365 dates and roughly 283 airports. This is a directional test supported by experiment 18, not a cosmetic neighboring value. Retain the successful leaf regularization.

Result: `6b49aa3`, Eval AUC **0.7557**, keep. Run time: 35.7s (training 3.3s, eval 32.4s, ok)

AUC improves by 0.0005 with one parameter; retain broader partitions. The attempted source-code search returned no results, so no finer implementation claim is assumed.

## Experiment 20 — exploration: Use one-hot splits for small categorical fields

Set max_cat_to_onehot=32 so month, day-of-month, weekday, carrier, and departure hour use single-category splits, while airports and date retain broad partition splits. This isolates how small categorical fields are handled, rather than reducing the partition-search limit that just helped. Source: XGBoost categorical tutorial and parameter reference.

Result: `e27f90a`, Eval AUC **0.7491**, discard. Run time: 35.8s (training 3.2s, eval 32.6s, ok)

AUC falls by 0.0066. Native partition splits are useful for both small and large categorical fields.

## Synthesis after 20 experiments

Best: **0.7557** at `6b49aa3` (+0.0354 over baseline). Leaf regularization improved the calendar model; broader categorical partition search helped slightly. Sparse route categories severely overfit. More depth, combined row/column sampling, an early-stopping data reservation, a geographic embedding, and one-hot categorical splits all failed. Removing day-of-month did not clearly simplify enough to justify its small loss. Current theory: broad shared date/airport patterns matter, with regularized leaves; useful fine-grained daily conditions may need a different representation.

Research refresh: revisited categorical regularization and growth policy in the [XGBoost reference](https://xgboost.readthedocs.io/en/stable/parameter.html), and searched/read [scikit-learn target encoding guidance](https://scikit-learn.org/stable/modules/preprocessing.html#target-encoder) plus the [CatBoost paper abstract](https://arxiv.org/abs/1706.09516). Target leakage is a concern when a row contributes its own label to a supervised encoding. We will not add cross-validation: a single disjoint training-data reservation can fit fixed lookup tables while the remaining rows train the model. These lookups must be frozen, row-local at inference, and use no evaluation labels. Counts will only enter the smoothing formula, never the feature matrix.

## Experiment 21 — exploration: Add independent airport-date delay lookups

Local daily disruption may be too fine-grained for the current shallow trees. Reserve 25% of train.csv solely to fit smoothed Origin-date and Dest-date target means (prior weight 10), then fit XGBoost on the disjoint 75%. Fixed tables are used identically for training rows and one-row inference. Only means become features; no counts, evaluation labels, cross-validation, or full-data retraining. This adapts the target-leakage precautions researched at the second synthesis.

Result: `05cabb5`, Eval AUC **0.7516**, discard. Run time: 42.8s (training 3.2s, eval 39.6s, ok)

AUC falls by 0.0041. The model uses both delay lookups strongly, but the complete pipeline is worse. Disjoint 50,000 lookup / 150,000 model rows, fixed-table row consistency, and input-target independence were verified. No unsafe full-training target encoding is substituted.

## Experiment 22 — exploration: Add departure time relative to route schedule

Sparse route categories failed, but a label-free route median may expose whether a flight is unusually early or late for its route without assigning a separate category. Fit median scheduled departure minutes from all train rows, then subtract it per input row. This is directly aligned with the permitted train-fitted lookup example in program.md and with the time/context research already read.

Result: `661efd7`, Eval AUC **0.7543**, discard. Run time: 41.3s (training 3.4s, eval 37.8s, ok)

AUC falls by 0.0014. The label-free lookup passes row/batch consistency checks but adds evaluation cost without improving ranking.

## Experiment 23 — exploration: Add coarse weekly calendar groups

Date categories captured daily effects strongly, but a coarse seven-day block could share persistent seasonal or operational effects more efficiently than independent daily groups. Add one categorical WeekOfYear derived from DayOfYear, retaining the original date inputs. This follows the temporal-representation research, with the grouping choice an experimental hypothesis.

Result: `a3b5637`, Eval AUC **0.7557**, discard. Run time: 39.3s (training 3.4s, eval 35.9s, ok)

Rounded AUC is unchanged at 0.7557, with more preparation work. Retain the simpler feature set.

## Experiment 24 — follow-up: Test longer horizon with regularized date model

Double 600 to 1200 rounds at learning_rate 0.05 with depth 4, leaf weight 20, L2 10, and broad categorical partitions. The prior long-horizon failure used depth 6, rate 0.1, no date features, and weak regularization; this tests whether the materially improved model still has boosting headroom.

Result: `2e4b2a6`, Eval AUC **0.7549**, discard. Run time: 38.3s (training 5.7s, eval 32.6s, ok)

AUC falls by 0.0008 and model size doubles. The current regularized model does not need a longer horizon at this learning rate.

## Experiment 25 — exploration: Optimize pairwise ordering with XGBoost rank loss

Recent feature additions have not improved ranking. Try rank:pairwise, the pairwise logistic loss documented at https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html . Shuffle training rows into random groups of 256 and sample four pairs per row to approximate population-wide positive/negative ordering with parallel training. No ranking metric or custom evaluation is introduced: a sigmoid wrapper exposes predict_proba and the unchanged harness computes the same AUC. The randomized groups are a computational approximation, not real airline query groups.

Result: `5a4b85c`, Eval AUC **0.7347**, discard. Run time: 38.7s (training 6.1s, eval 32.6s, ok)

AUC falls by 0.0210. The randomized-group pairwise approximation adds complexity and does not suit this configuration; return to binary classification.

## Experiment 26 — exploration: Average three randomized trees per boosting round

Use num_parallel_tree=3, subsample=0.8, and colsample_bynode=0.9. Averaging multiple randomized trees may stabilize noisy categorical partitions. Per-node feature sampling differs from the failed per-tree sampling: important features can become available deeper in each tree. Keep 600 boosting rounds and learning_rate 0.05. Source: https://xgboost.readthedocs.io/en/stable/tutorials/rf.html .

Result: `de8067c`, Eval AUC **0.7557**, discard. Run time: 45.5s (training 12.5s, eval 33.0s, ok)

Rounded AUC is unchanged at 0.7557, while training rises to 12.5 s and model size triples. Keep the simpler single-tree updates.

## Experiment 27 — ablation/simplification: Distribute capacity across shallower trees

Depth 4 consistently beats depth 6. Test depth 3 with 1200 rounds at learning_rate 0.05, roughly preserving a comparable maximum leaf budget while shifting capacity toward lower-order interactions. This is a structural simplicity hypothesis, not another longer-horizon trial at the same depth.

Result: `b6b8d4f`, Eval AUC **0.7529**, discard. Run time: 36.9s (training 4.4s, eval 32.5s, ok)

AUC falls by 0.0028. Depth 4 is the best tested tradeoff between useful interactions and noise.

## Experiment 28 — exploration: Fit regularized airport-date residual corrections

The disjoint target-feature experiment lost fitting data. Instead, keep the XGBoost learner fitted on all rows with unchanged features, then fit two additive model stages: one regularized Newton score per Origin-date and Dest-date, using residual gradients and Hessians. Shrink each score by 0.5 with L2=10. The input keys are constructed only in prepare; correction tables are fitted model parameters and never become target-derived training features. No extra evaluation metric or retraining is added. Source: the additive objective and optimal leaf-weight derivation at https://xgboost.readthedocs.io/en/stable/tutorials/model.html .

Result: `231b407`, Eval AUC **0.7575**, keep. Run time: 42.9s (training 4.1s, eval 38.8s, ok)

AUC improves by 0.0018, ending the plateau. The extra model stage is principled and uses fixed, regularized parameters rather than target-derived inputs to the trees. Row/batch consistency, input-target independence, artifact reload, and finite normalized probabilities passed. Corrections remain small (roughly -0.20 to +0.28 logits).

## Experiment 29 — follow-up: Use full regularized airport-date correction steps

The conservative half-step corrections helped and remain small. Increase their step multiplier from 0.5 to 1.0 while keeping L2=10, to test whether local daily residuals remain underfit. This changes model-stage strength only; the XGBoost model and input features are unchanged.

Result: `eb48336`, Eval AUC **0.7583**, keep. Run time: 42.4s (training 4.0s, eval 38.4s, ok)

AUC improves by 0.0008 with no added code complexity; the initial half-step was conservative.

## Experiment 30 — follow-up: Relax shrinkage on airport-date residual scores

The full correction step improved AUC. Reduce the additive-stage L2 penalty from 10 to 3, a coarse test of whether local daily deviations remain overshrunk. This changes only the fitted group scores; the trees retain reg_lambda=10 and all other settings. Source: the regularized leaf-weight formula from the XGBoost model tutorial.

Result: `47e2903`, Eval AUC **0.7560**, discard. Run time: 42.7s (training 4.2s, eval 38.5s, ok)

AUC falls by 0.0023 from the full-step L2=10 model. Small local groups need substantial shrinkage.

## Synthesis after 30 experiments

Best: **0.7583** at `eb48336` (+0.0380 over baseline). Additional raw calendar/route features, a longer horizon, shallower trees, and pairwise ranking did not help. A three-tree boosted forest tied the former best but was larger. The productive new approach is a fixed XGBoost base plus two regularized additive airport-date model stages: half steps scored 0.7575, full steps 0.7583. Reducing the stage penalty from 10 to 3 dropped AUC to 0.7560, so the local effects must remain strongly shrunk.

Research refresh: read the [XGBoost additive training and optimal leaf-weight derivation](https://xgboost.readthedocs.io/en/stable/tutorials/model.html), [ranking tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html), and searched [regularized logistic regression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html), [generalized additive models](https://www.statsmodels.org/stable/gam.html), and [feature interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html). Next directions: carrier-date residual effects, removal of redundant correction stages, and joint regularized fitting of the additive scores. These are fitted model parameters; target-derived lookup values never enter the XGBoost training feature matrix.

## Experiment 31 — follow-up: Add carrier-date residual effects

Airline-wide daily disruptions may remain after origin-date and destination-date corrections. Add one CarrierDate key and one L2=10 Newton correction stage, fitted after the existing airport stages. Generalize the key declaration to keep prepare and model column selection aligned. Motivation: the successful additive local-effects model and the third synthesis; this is a domain-specific hypothesis.

Result: `6b4171b`, Eval AUC **0.7588**, keep. Run time: 48.1s (training 4.2s, eval 43.9s, ok)

AUC improves by 0.0005 within the existing correction model. Row/batch and target-independence checks pass, and base XGBoost predictions exactly match the prior base on sampled training inputs.

## Experiment 32 — ablation/simplification: Ablate destination-date correction stage

Departure delay is primarily an origin event, and carrier-date effects may already capture part of the destination contribution. Remove DestDate from the shared correction-key declaration, eliminating its input construction and fitted stage. Keep if performance is effectively preserved with this simpler model.

Result: `7cb0ec1`, Eval AUC **0.7580**, discard. Run time: 44.3s (training 4.1s, eval 40.3s, ok)

Removing the destination correction reduces AUC by 0.0008. It contributes complementary information after origin-date and carrier-date effects.

## Experiment 33 — follow-up: Jointly refine regularized additive correction scores

One sequential pass can leave correlated origin, destination, and carrier effects dependent on fit order. Perform three coordinate Newton passes on the same penalized logistic model. Each update includes the existing coefficient penalty (G - lambda*w)/(H + lambda), so repeated passes optimize one L2-regularized model rather than repeatedly adding unpenalized residual stages. The derivation follows the XGBoost quadratic objective; the multi-pass adaptation is our implementation.

Result: `21e0736`, Eval AUC **0.7588**, discard. Run time: 48.5s (training 4.4s, eval 44.1s, ok)

AUC remains 0.7588. The more elaborate fitting loop offers no measured advantage; preserve the one-pass procedure.

## Experiment 34 — exploration: Add a regularized route residual stage

The raw route category overfit inside the trees, but a single shrunk route-specific logit may capture persistent route effects without label-dependent category partition search. Add Route=(Origin,Dest) as a correction-stage key only, with the same L2=10 penalty and fixed base tree inputs. This explores representation and model structure, not a repeat of experiment 11.

Result: `f05201f`, Eval AUC **0.7583**, discard. Run time: 50.2s (training 4.2s, eval 46.0s, ok)

AUC falls by 0.0005 and preparation becomes slower. Persistent route effects do not improve the current model.

## Experiment 35 — ablation/simplification: Remove calendar columns unused by the base trees

Inspection of the kept base booster shows zero splits on Month, DayofMonth, DayOfWeek, and numeric DayOfYear after broad categorical date partitions were enabled. Remove these four inputs while continuing to derive the categorical date and correction keys from raw month/day values. Unlike experiment 17, the currently kept broader-partition model demonstrably does not use any of these columns.

Result: `d534fa8`, Eval AUC **0.7588**, keep. Run time: 39.8s (training 3.9s, eval 35.9s, ok)

AUC remains 0.7588, remaining features and sampled predictions are exactly identical, and evaluation drops from 43.9 s to 35.9 s. Keep the simpler representation.

## Experiment 36 — exploration: Add date-by-time-block residual effects

Shared conditions can change within a day. Add a DateTimeBlock residual key using date and scheduled six-hour departure block, with the established L2=10 correction. It is fitted after airport/date and carrier/date stages. The block is computed from each row's scheduled time inside prepare; no traffic counts or future information are used. Motivation: prior time-feature research and the successful local daily correction model.

Result: `4f6ca29`, Eval AUC **0.7585**, discard. Run time: 43.2s (training 4.0s, eval 39.1s, ok)

AUC falls by 0.0003 and preparation is slower. Global within-day grouping is not useful beyond the current model.

## Experiment 37 — exploration: Add carrier-origin residual effects

Airlines may have persistent operating differences at specific origin airports. Add one CarrierOrigin correction key, fitted after the daily stages with L2=10. This moderate-cardinality additive effect is distinct from route grouping and does not alter the tree feature matrix.

Result: `0e7623a`, Eval AUC **0.7588**, discard. Run time: 41.9s (training 3.9s, eval 38.0s, ok)

AUC remains 0.7588 with added input preparation and a model stage. Keep the simpler three-stage correction model.

## Experiment 38 — exploration: Separate global date effects from tree interactions

Test a decomposition in which XGBoost learns an additive global date component and schedule/airport/carrier interactions separately, while existing shrunk correction stages learn local daily deviations. Use disjoint interaction groups: [Date] and all other base features. The source warns that overlapping groups can expand allowed interactions, so these groups deliberately do not overlap. Source: https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html .

Result: `55ad229`, Eval AUC **0.7561**, discard. Run time: 39.3s (training 3.9s, eval 35.4s, ok)

AUC falls by 0.0027. The regularized additive stages do not replace all useful date interactions inside the base trees.

## Experiment 39 — exploration: Use loss-guided trees with a fixed leaf budget

Depthwise trees allocate capacity uniformly by level. Test grow_policy=lossguide, max_depth=0, max_leaves=16, retaining the maximum leaf count of depth 4 while allowing asymmetric paths where loss reduction is strongest. Existing minimum child weight and L2 regularization guard small leaves. Source: grow_policy and max_leaves in the XGBoost parameter reference.

Result: `27e2063`, Eval AUC **0.7590**, keep. Run time: 40.0s (training 4.3s, eval 35.7s, ok)

AUC improves by 0.0002 with standard model parameters and nearly unchanged runtime/size. This is a small gain, not evidence of a large generalization difference.

## Experiment 40 — follow-up: Expand loss-guided trees to 32 leaves

The loss-guided 16-leaf model modestly improves on depthwise growth. Double the leaf budget to 32 while retaining leaf regularization, testing whether selective asymmetric growth supports useful additional capacity. This differs from earlier depth-6 trials because the tree has a hard leaf budget and chooses expansion by loss reduction.

Result: `97b305f`, Eval AUC **0.7573**, discard. Run time: 40.8s (training 5.8s, eval 35.0s, ok)

AUC falls by 0.0017 and artifact size grows substantially. Keep the 16-leaf budget.

## Synthesis after 40 experiments — about one hour elapsed

Best: **0.7590** at `27e2063` (+0.0387 over baseline). Carrier-date corrections add a small gain; destination-date corrections remain useful. Repeated joint fitting, route or carrier-origin corrections, and global date/time-block corrections do not improve the model. Removing four calendar inputs unused by the base trees preserves exact sampled predictions and saves about eight evaluation seconds. Separating date from tree interactions hurts. Loss-guided growth with 16 leaves gives a small gain, but 32 leaves overfits.

Research refresh: read [XGBoost interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html), including the implications of overlapping groups, and searched [ensemble averaging](https://scikit-learn.org/1.5/modules/ensemble.html) and [DART dropout](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html). Next directions: isolate row sampling from feature sampling, test independently randomized model averaging if warranted, refine regularization under the new tree growth policy, and consider dropout within the fixed training limit. Every keep/discard decision still uses only the original harness AUC.

## Experiment 41 — follow-up: Isolate row sampling with all features available

Experiment 14 combined row and per-tree feature sampling, so its failure did not identify the harmful component. On the current improved model, set only subsample=0.8 and keep all features available at every split. This checks whether stochastic training can reduce variance without removing the dominant date/time predictors; source: XGBoost stochastic regularization guidance.

Result: `626648f`, Eval AUC **0.7555**, discard. Run time: 39.8s (training 5.0s, eval 34.7s, ok)

AUC falls by 0.0035 even when all features remain available. Do not build an ensemble solely from this weaker stochastic configuration.

## Experiment 42 — follow-up: Refine boosting with smaller deterministic steps

Reducing eta from 0.1 to 0.05 helped earlier, and stochastic sampling consistently hurts. Test eta=0.02 with 1500 rounds versus 0.05 with 600, holding their product at 30 under the current loss-guided and residual-correction model. This tests a more gradual deterministic fitting path rather than increasing the effective boosting horizon.

Result: `2427b05`, Eval AUC **0.7589**, discard. Run time: 46.2s (training 10.4s, eval 35.8s, ok)

AUC is 0.0001 lower while training and model size increase substantially; keep 600 rounds at 0.05.

## Experiment 43 — follow-up: Increase minimum leaf weight for asymmetric trees

Loss-guided growth permits deeper selective paths. Raise min_child_weight from 20 to 100 to prevent these paths from fitting small groups, while keeping the leaf budget and L2 penalty fixed. The original paired regularization change helped, but this isolates stronger structural leaf regularization under the new grow policy.

Result: `1ae2ff2`, Eval AUC **0.7582**, discard. Run time: 40.2s (training 4.5s, eval 35.7s, ok)

AUC falls by 0.0008. The existing minimum leaf weight of 20 is preferable.

## Experiment 44 — exploration: Increase numeric histogram resolution

Scheduled departure time and distance have more than 1000 distinct training values, while the default histogram uses 256 bins. Test max_bin=1024 to allow finer numeric split locations without changing categorical representations or tree capacity. Source: max_bin in the XGBoost parameter reference; any benefit here is empirical, not assumed.

Result: `dc133d4`, Eval AUC **0.7588**, discard. Run time: 39.8s (training 4.4s, eval 35.4s, ok)

AUC falls by 0.0002. Three consecutive near-miss discards triggered a fresh research pause before the next trial.

## Experiment 45 — exploration: Test mild tree dropout with DART

Fresh plateau research: read the abstract/introduction of Rashmi and Gilad-Bachrach, DART (https://proceedings.mlr.press/v38/korlakaivinayak15.pdf), and XGBoost's DART tutorial. Tree dropout targets over-specialization without dropping input features or rows. Test booster=dart, rate_drop=0.01, skip_drop=0.5. Use 300 rounds at eta=0.1 to accommodate the documented loss of prediction-buffer reuse under the one-minute training limit. This is a complete candidate comparison, not an isolated estimate of the dropout parameter's effect.

Result: `329a415`, Eval AUC **0.7577**, discard. Run time: 83.4s (training 48.2s, eval 35.2s, ok)

AUC is 0.7577 and total training takes 48.2 s, near the one-minute limit. Ordinary boosting is both stronger and faster. The legacy dart name also emits a deprecation warning in this installed version.

## Experiment 46 — exploration: Average depthwise and loss-guided model margins

The two strongest tree structures have similar AUC but may make different ranking errors. Fit both full-data models with fixed equal weight, average their raw logits, then fit the existing regularized daily corrections against that averaged base. No individual-model evaluation, validation-fitted weights, cross-validation, or extra data is used. Motivation: ensemble variance reduction reviewed in the fourth synthesis; logit averaging is our additive-model implementation choice.

Result: `6c176a1`, Eval AUC **0.7602**, keep. Run time: 42.3s (training 7.1s, eval 35.2s, ok)

AUC improves by 0.0012, a useful gain for the straightforward two-model average. Training remains only 7.1 s and evaluation is unchanged. Weights are fixed, not fitted to evaluation data.

## Experiment 47 — follow-up: Prune weak splits in the averaged base models

The complementary tree structures improve ranking through averaging. Add gamma=2 to both base models to require a minimum loss reduction for new splits, targeting weak late-stage branches without removing predictors or samples. Source: gamma/min_split_loss in the XGBoost parameter reference.

Result: `e34336d`, Eval AUC **0.7601**, discard. Run time: 41.4s (training 5.9s, eval 35.5s, ok)

AUC is 0.7601 versus 0.7602. The size reduction is modest and the code adds a control, so retain the best scoring ensemble. Saved-ensemble row consistency and probability checks passed.

## Experiment 48 — exploration: Strengthen L2 shrinkage in both base learners

Larger minimum leaves removed useful structure, while split pruning nearly preserved AUC. Test reg_lambda=100 versus 10 in both base learners to retain candidate splits but shrink uncertain leaf scores more strongly. The separate additive-correction penalty remains 10. This isolates leaf-value shrinkage from structural pruning.

Result: `c203fa3`, Eval AUC **0.7597**, discard. Run time: 42.3s (training 7.1s, eval 35.2s, ok)

AUC falls by 0.0005. Retain reg_lambda=10 in the two base learners.

## Experiment 49 — ablation/simplification: Sparsify additive daily corrections with L1

Weak daily correction groups may add noise and storage. Apply L1=1 soft-thresholding to each group's residual gradient before the existing L2=10 division, and store only nonzero scores. This matches the regularized leaf-score form in XGBoost's primary implementation: https://raw.githubusercontent.com/dmlc/xgboost/master/src/tree/param.h (ThresholdL1 and CalcWeight). Training and inference map omitted coefficients to zero; counts are not input features.

Result: `7dfbf0e`, Eval AUC **0.7601**, discard. Run time: 42.8s (training 7.5s, eval 35.3s, ok)

AUC is 0.7601 versus 0.7602. Stored corrections fall from 94,470 to 16,247 (about 83% fewer), making this a promising simplification direction; test a weaker threshold rather than accepting lost accuracy immediately.

## Experiment 50 — follow-up: Use a gentler sparse daily-correction penalty

L1=1 removed most correction coefficients but lost 0.0001 AUC. Test L1=0.5 to restore moderate residual effects while still suppressing weak coefficients. This is a targeted simplicity/accuracy tradeoff following the measured sparsity change, not a seed or cosmetic repeat.

Result: `7dddf5a`, Eval AUC **0.7604**, keep. Run time: 43.0s (training 7.3s, eval 35.7s, ok)

AUC improves by 0.0002 and artifact size falls from 15.4 MB to 13.8 MB. Keep this useful accuracy/simplicity improvement.

## Synthesis after 50 experiments

Best: **0.7604** at `7dddf5a` (+0.0401 over baseline). Row sampling, more gradual boosting, heavier base-model penalties, finer histograms, and DART do not improve the kept model. DART fits within the training limit only with a shorter horizon and is much slower. Equal averaging of the strong depthwise and loss-guided models improves AUC to 0.7602. Sparse daily corrections improve this to 0.7604 while reducing storage: L1=1 was slightly too aggressive, while L1=0.5 preserves useful moderate effects.

Research refresh: read the [DART paper](https://proceedings.mlr.press/v38/korlakaivinayak15.pdf), XGBoost's [L1 leaf-weight implementation](https://raw.githubusercontent.com/dmlc/xgboost/master/src/tree/param.h), and searched [soft voting](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html), [Eilers's penalized smoother](https://pubmed.ncbi.nlm.nih.gov/14570219/), and [SciPy banded linear solvers](https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.solve_banded.html). Candidate directions are localized time-of-day corrections, temporally smoothed daily effects, and comparison of probability versus logit averaging. These are hypotheses; no external data or new packages will be used.

## Experiment 51 — exploration: Add sparse origin-date time-block effects

Global date/time blocks failed, but local disruptions may affect one airport during only part of a day. Add OriginDateBlock from origin, date, and six-hour scheduled departure block, after the existing coarser daily stages. Keep L1=0.5 and L2=10 to suppress weak fine-grained effects. The block is aligned with the departure airport's scheduled local time and is computed row by row in prepare.

Result: `2fed12e`, Eval AUC **0.7608**, keep. Run time: 48.7s (training 8.1s, eval 40.5s, ok)

AUC improves by 0.0004 with a small extension to the existing key declaration. Row/batch and target-independence checks pass; evaluation remains well below the limit.

## Experiment 52 — exploration: Compare probability averaging with logit averaging

Equal averaging of logits improved the model, but it can give more influence to extreme confidence. Compare standard soft voting: average the two base probabilities, convert that mean back to a logit for the existing correction stages, and keep fixed equal weights. Source: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html .

Result: `f13b07e`, Eval AUC **0.7608**, discard. Run time: 47.7s (training 7.4s, eval 40.3s, ok)

The displayed AUC is unchanged at 0.7608, with an extra probability-to-logit transformation. Keep the simpler existing logit average.

## Experiment 53 — ablation/simplification: Encode correction groups with fixed numeric identifiers

String correction keys repeatedly concatenate airport, month, day, and time-block strings. Replace them with injective integer identifiers built from fixed training category codes, day-of-year, and block. This preserves group membership exactly, reduces per-row preparation work and table storage, and gives unknown entities a negative unmatched key. Check row consistency and equivalence to the saved kept artifact.

Result: `4d3ca2f`, Eval AUC **0.7608**, keep. Run time: 36.6s (training 6.9s, eval 29.7s, ok)

AUC remains 0.7608; 512 sampled training-row predictions are bit-for-bit identical to the previous saved artifact. Evaluation falls from about 40s to 29.4s, with three fewer lines and a smaller artifact. Row/batch and target-independence checks pass.

## Experiment 54 — follow-up: Resolve origin-date disruption effects into three-hour blocks

Six-hour origin-date effects helped in experiment 51. Three-hour blocks may better isolate short-lived airport disruptions; retain the same sparse regularization so unsupported fine groups shrink to zero. Also make the daily-key expression explicitly independent of hour even for an out-of-range hour 24; training times span 00:05–23:59, so that guard does not change the measured daily grouping.

Result: `a60dd4a`, Eval AUC **0.7607**, discard. Run time: 36.0s (training 6.8s, eval 29.2s, ok)

AUC decreases from 0.7608 to 0.7607 while the finer table grows. Restore six-hour blocks; the extra temporal resolution is not justified.

## Experiment 55 — exploration: Smooth daily correction coefficients across adjacent dates

Airport disruptions and carrier effects may persist across neighboring days. Adapt the first-difference penalty in https://pybaselines.readthedocs.io/en/latest/algorithms/whittaker.html to the quadratic Newton correction objective: retain L1=0.5 and L2=10 and add coupling strength 5 between adjacent daily coefficients. Use 20 diagonally dominant Jacobi soft-threshold updates; daily endpoints do not wrap and airport/carrier groups remain separate. Fit all tables only on train. Six-hour local effects remain unsmoothed. The explicit hour-independent daily key guard is retained for out-of-range times.

Result: `6b3e0cb`, Eval AUC **0.7608**, discard. Run time: 36.5s (training 7.6s, eval 28.8s, ok)

AUC remains 0.7608 with 16 extra fitting lines. The penalized optimizer satisfies its coordinate optimality conditions to 1.5e-7 and preparation checks pass, but no score gain justifies smoothing. Retain independent daily effects.

## Experiment 56 — follow-up: Add carrier-date six-hour residual effects

Local origin/date blocks improved the daily model; carrier operations can also experience disruptions confined to part of the day across multiple airports. Add a carrier/date/six-hour residual stage, using the same L1=0.5 and L2=10 penalties. This tests network-wide within-day structure rather than making existing airport groups finer. Apply the daily key boundary guard without changing any training-row keys.

Result: `06812b3`, Eval AUC **0.7610**, keep. Run time: 37.8s (training 7.1s, eval 30.7s, ok)

AUC improves from 0.7608 to 0.7610 for one extra correction-stage declaration. Evaluation remains around 30s. The daily-key guard is now explicit.

## Experiment 57 — follow-up: Add a deeper member to the structural ensemble

Averaging depthwise and loss-guided models was one of the largest recent gains. A depth-six model was weaker alone, but may contribute complementary interactions to this ensemble. Add it at an equal fixed weight, retain all regularization, and refit the existing residual stages after the average. This tests ensemble diversity rather than replacing the best base learner. Sources: https://scikit-learn.org/1.5/modules/ensemble.html and https://xgboost.readthedocs.io/en/stable/parameter.html .

Result: `c9f7693`, Eval AUC **0.7613**, keep. Run time: 43.2s (training 11.6s, eval 31.6s, ok)

The deeper member improves ensemble AUC by 0.0003 despite its weaker standalone result earlier. It adds two fitting lines and stays comfortably within the 60s training limit (11.6s), though the artifact grows to 38.7MB. Keep the score gain; seek feature and ensemble simplifications next.

## Experiment 58 — ablation/simplification: Remove the rarely used departure-minute feature

In the two-member model, DepMinute appeared in only 28 and 44 splits, while raw scheduled departure time already contains minutes. Test removing this derived feature from the new three-member ensemble. A tie would justify one fewer transformation and base feature; a drop would establish that the explicit minute representation remains useful.

Result: `387f653`, Eval AUC **0.7617**, keep. Run time: 41.2s (training 11.9s, eval 29.3s, ok)

Removing DepMinute improves AUC from 0.7613 to 0.7617, reduces a per-row transformation, and slightly speeds evaluation. Retain this simplification.

## Experiment 59 — ablation/simplification: Test whether the original loss-guided member remains necessary

The depth-six member improved the ensemble, and dropping a weak feature improved it again. Check whether the ensemble can now be reduced to the two depthwise models: omit fitting and averaging the original loss-guided member while retaining its parameter object as the shared configuration source. This is a direct ablation of ensemble redundancy, with all correction stages refitted.

Result: `c3138a2`, Eval AUC **0.7604**, discard. Run time: 37.0s (training 8.3s, eval 28.7s, ok)

AUC falls from 0.7617 to 0.7604 when averaging only the depth-four and depth-six members. The loss-guided model supplies useful complementary information, so all three are retained.

## Experiment 60 — exploration: Fit a low-rank airport-date residual stage

Correlated disruptions across airports may have a low-dimensional structure that independent daily effects cannot share. Adapt weighted alternating least squares from https://developers.google.com/machine-learning/recommendation/collaborative/matrix to the grouped Newton objective. Before the independent OriginDate stage, fit a rank-eight airport-by-day matrix to residual gradients with hessian+10 weights and factor ridge penalty 1. SVD initialization and ten alternating linear solves are deterministic. Missing cells have zero gradient and the same zero-centered prior. This is a fitted additive model component, not a target-encoded feature for the trees.

Result: `4300681`, Eval AUC **0.7618**, discard. Run time: 42.4s (training 11.6s, eval 30.8s, ok)

AUC reaches 0.7618, only 0.0001 above the simpler kept model. Sixteen added fitting lines and another model family are not justified by that gain. Discard under the simplicity criterion, then test whether a much simpler low-rank projection preserves the signal.

## Synthesis after 60 experiments

Best kept: **0.7617** at `387f653` (+0.0414 over baseline). The highest displayed score, 0.7618, came from a weighted low-rank stage whose tiny improvement did not justify its complexity. Fixed numeric correction keys preserved predictions exactly and reduced evaluation time by about a quarter. Carrier/date/time-block effects and a third, deeper ensemble member helped; dropping the departure-minute feature helped again. The loss-guided member is still essential. Probability averaging, finer airport blocks, and adjacent-day smoothing did not improve the kept model.

Research refresh: read [weighted matrix factorization and alternating solves](https://developers.google.com/machine-learning/recommendation/collaborative/matrix), [difference-penalty smoothing](https://pybaselines.readthedocs.io/en/latest/algorithms/whittaker.html), and searched pandas categorical construction and XGBoost monotonic constraints. The next tests emphasize whether the low-rank idea survives aggressive simplification, cheaper row preparation, and remaining redundant correction stages. No source suggests a defensible monotonic direction for distance or scheduled time across the whole day, so monotonic constraints will not be imposed arbitrarily.

## Experiment 61 — ablation/simplification: Replace alternating factor fitting with a direct low-rank projection

Experiment 60 found a tiny gain from shared airport-date patterns but was too complex. Use only a rank-eight SVD projection of the regularized airport/date residual matrix, eliminating alternating solves and separate factor penalties. Independent sparse corrections still follow it. The matrix-factorization source above gives the direct low-rank approximation objective; this trial tests whether a simpler approximate stage can capture the same useful structure.

Result: `03f73ab`, Eval AUC **0.7618**, keep. Run time: 42.9s (training 12.1s, eval 30.8s, ok)

The direct SVD projection matches the weighted solver's 0.7618 AUC using six straightforward lines instead of sixteen, without a custom optimizer or additional dependencies. Keep this compact form of the shared airport/date effect; training remains 12.1s.

## Experiment 62 — ablation/simplification: Build prepared features once from fixed category codes

Preparation runs on one row at a time and still dominates runtime. Build columns in a dictionary and construct one DataFrame at the end, instead of repeated DataFrame column assignment. Store training category vocabularies as pandas indexes and use get_indexer plus Categorical.from_codes, which explicitly maps unknown values to missing (-1). Preserve column order, dtypes, and all feature values. Sources: https://pandas.pydata.org/docs/reference/api/pandas.Categorical.from_codes.html and https://pandas.pydata.org/docs/reference/api/pandas.Index.get_indexer.html .

Result: `5196f07`, Eval AUC **0.7618**, keep. Run time: 26.3s (training 11.8s, eval 14.5s, ok)

AUC remains 0.7618 while evaluation drops from 30.4s to 14.1s. Feature equality, row/batch consistency, input-target independence, and unseen-category finite prediction checks pass. Keep the faster and explicit category-code preparation.

## Experiment 63 — ablation/simplification: Cap the deepest ensemble member at 32 leaves

The third member averages 60.1 leaves per tree and accounts for most artifact size; the first two average 16.0 and 15.6. Keep max_depth=6 but cap its leaf count at 32, allowing selectively deeper branches while reducing complexity. A tie or gain would justify a much smaller ensemble; a decline would show the breadth of the deeper learner is useful. XGBoost max_leaves and grow_policy semantics: https://xgboost.readthedocs.io/en/stable/parameter.html .

Result: `b16864b`, Eval AUC **0.7616**, discard. Run time: 25.8s (training 11.3s, eval 14.5s, ok)

The artifact shrinks from 40.8MB to 29.7MB, but AUC falls from 0.7618 to 0.7616. Training is already well within budget, so retain the fuller deeper member.

## Experiment 64 — ablation/simplification: Remove the coarse carrier-date correction stage

The carrier/date/six-hour correction added a gain after the coarse carrier/date stage. Test whether the fine-grained stage can absorb the coarser effect without a separate table. This removes a prepared column, fitting pass, and prediction lookup if AUC is preserved; a drop would support the hierarchical shrinkage structure.

Result: `35fc52d`, Eval AUC **0.7617**, discard. Run time: 25.8s (training 11.3s, eval 14.4s, ok)

AUC falls from 0.7618 to 0.7617 without the coarse carrier/date stage. Its overhead is small and the hierarchical coarse-plus-fine structure remains useful.

## Experiment 65 — exploration: Initialize the boosted ensemble with fitted daily intercepts

Date dominates the base trees' split counts. Fit a regularized per-date logistic intercept first, then train each XGBoost member on deviations using base_margin. This is sequential additive model fitting on all train rows, not a target feature or extra evaluation split. Use a ten-observation global-mean prior for the daily intercepts; supply the same fitted margins at prediction. The remaining residual stages stay unchanged. Source: https://xgboost.readthedocs.io/en/stable/tutorials/intercept.html .

Result: `0f57f57`, Eval AUC **0.7616**, discard. Run time: 25.8s (training 11.4s, eval 14.5s, ok)

Daily intercept initialization scores 0.7616 versus 0.7618, while adding offset handling. Restore the original learned tree intercepts. After three close discards, refreshed the official XGBoost regularization documentation before choosing the next trial.

## Experiment 66 — exploration: Apply sparse leaf regularization to the deepest member

A hard leaf cap weakened the ensemble, but the deepest member still has many more leaves than the others. Instead of removing branches, apply reg_alpha=5 only to this member to shrink weak leaf updates toward zero. Keep the proven shallow models unchanged. L1 leaf-weight regularization is distinct from the earlier L2 and global gamma trials, and follows https://xgboost.readthedocs.io/en/stable/parameter.html .

Result: `7ff912e`, Eval AUC **0.7645**, keep. Run time: 25.1s (training 10.5s, eval 14.5s, ok)

AUC improves substantially from 0.7618 to 0.7645 while the artifact shrinks from 40.8MB to 32.4MB and training gets faster. Sparse leaf regularization preserves useful structure more effectively than the earlier hard leaf cap.

## Experiment 67 — follow-up: Extend successful L1 regularization to all ensemble members

Applying reg_alpha=5 to the deepest member improved AUC by 0.0027 and reduced artifact size. Test the same sparse leaf penalty in the two shallower models as well, using one shared reg_alpha=5 setting. This isolates whether the benefit is specific to deep interactions or also stabilizes the broad categorical partitions in every member. Source: the official XGBoost L1 documentation reviewed before experiment 66.

Result: `a194ace`, Eval AUC **0.7657**, keep. Run time: 24.8s (training 10.3s, eval 14.5s, ok)

Extending reg_alpha=5 to the two shallow members improves AUC by a further 0.0012, with a slightly smaller artifact (31.2MB). Keep one shared L1 setting.

## Experiment 68 — follow-up: Extend the strongly regularized ensemble to 1200 rounds

Extra rounds previously hurt the unpenalized categorical model. L1=5 now suppresses weak leaf updates and has improved AUC by 0.0039 across experiments 66–67. Double the boosting horizon at the same learning rate to test whether the conservative ensemble can learn additional stable interactions without the earlier overfitting. Expected training remains below 60s based on the current 10.3s run.

Result: `da6498a`, Eval AUC **0.7661**, keep. Run time: 34.3s (training 18.7s, eval 15.5s, ok)

The longer strongly regularized ensemble reaches 0.7661 (+0.0004). Training remains safely within budget at 18.7s; the artifact grows to 54.1MB. Unlike the earlier unpenalized model, this one benefits from additional rounds.

## Experiment 69 — ablation/simplification: Ablate the low-rank stage after strengthening the trees

The direct low-rank correction added only 0.0001 before L1 regularization and longer boosting substantially improved the base ensemble. Remove it now to test whether the better trees already explain the shared airport-date structure. An equal score would remove SVD fitting, a prepared key, and a prediction table.

Result: `f06ab47`, Eval AUC **0.7662**, keep. Run time: 35.1s (training 19.8s, eval 15.3s, ok)

AUC improves from 0.7661 to 0.7662 while removing six lines, a prepared column, and the SVD/correction table. The stronger tree ensemble makes the earlier low-rank stage unnecessary.

## Experiment 70 — follow-up: Increase interaction depth under strong L1 regularization

The depth-six member became much more useful after L1 regularization. Test depth eight for that member alone, preserving the two complementary shallow members and all penalties. This explores richer interactions under the newly successful sparse-leaf regime, rather than repeating the earlier unregularized depth increases. Training should remain within 60s given the current 19.8s total.

Result: `b1fc100`, Eval AUC **0.7673**, keep. Run time: 37.5s (training 22.0s, eval 15.6s, ok)

Depth eight improves AUC from 0.7662 to 0.7673, with training still only 22.0s. The artifact grows to 82.4MB, but the clear gain and unchanged implementation complexity justify keeping it.

## Synthesis after 70 experiments

Best kept: **0.7673** at `b1fc100` (+0.0470 over baseline). The most important new result is L1 regularization of native-categorical tree leaves: first on the deep member, then across the ensemble. This unlocked a useful longer boosting horizon and depth-eight interactions. A hard leaf-count cap and daily intercept initialization did not help. Removing the now-redundant low-rank stage improved AUC and removed six lines. Prepared features are now built once from fixed categorical codes, reducing evaluation to about 15s.

Research refresh: revisited [XGBoost regularization and logistic objectives](https://xgboost.readthedocs.io/en/stable/parameter.html), read [label smoothing research](https://arxiv.org/abs/1906.02629) and [custom-objective documentation](https://xgboost.readthedocs.io/en/stable/tutorials/custom_metric_obj.html), and searched for smoothing in boosted classifiers. Label smoothing evidence is mainly from neural networks, so any use here is an explicit transfer hypothesis, not an established result for this dataset. Next: test whether a stronger sparse-leaf penalty is useful at depth eight, then compare modest target smoothing and remaining simple ensemble changes within the clock.

## Experiment 71 — follow-up: Test stronger L1 shrinkage in the larger ensemble

L1=5 enabled deeper interactions and longer boosting. Now test L1=20 across the depth-eight ensemble to determine whether additional suppression of weak categorical leaf updates further improves generalization or begins to underfit. The fourfold step tests a materially stronger regularization regime rather than a fine parameter sweep.

Result: `0f89c59`, Eval AUC **0.7656**, discard. Run time: 38.2s (training 22.4s, eval 15.7s, ok)

AUC drops from 0.7673 to 0.7656, despite a smaller artifact. The stronger penalty suppresses useful signal; restore L1=5.

## Experiment 72 — exploration: Test modest label smoothing in the base ensemble

Research on label smoothing suggests that soft targets can discourage excessive confidence; applying it to boosted trees is an explicit transfer hypothesis. Fit the base models to 0.05/0.95 targets using XGBRegressor with the native logistic objective, then fit the existing residual stages on the original binary labels. Prepared labels and harness evaluation remain unchanged. Native logistic margins preserve the ensemble's prediction interface. Sources: https://arxiv.org/abs/1906.02629 and https://xgboost.readthedocs.io/en/stable/parameter.html .

Result: `3651943`, Eval AUC **0.7674**, keep. Run time: 37.9s (training 22.5s, eval 15.3s, ok)

Native logistic fitting to 0.05/0.95 targets yields 0.7674, a small gain with only two additional lines and no custom gradient code. The correction stages and evaluation still use original binary targets.

## Experiment 73 — ablation/simplification: Test the regularized deep model without shallow ensemble members

L1 regularization and depth eight changed the strongest model substantially. Test a single depth-eight model with the same smoothing, rounds, and residual corrections, removing the two shallow members and the averaging wrapper. This checks whether ensemble diversity is still necessary and offers a substantial code/runtime reduction if AUC holds.

Result: `5b9d62b`, Eval AUC **0.7671**, discard. Run time: 26.3s (training 11.6s, eval 14.7s, ok)

The single depth-eight model reaches 0.7671 and is faster, but loses 0.0003 versus the three-member ensemble. Retain the complementary shallow models.

## Experiment 74 — follow-up: Add an intermediate-depth member to the regularized ensemble

The single deep model is close to the best ensemble, but shallow structural diversity still adds value. Add a regularized depth-six member at the same fixed equal weight, balancing the ensemble between shallow and deeper interactions. This tests an intermediate model family rather than fitting evaluation-dependent weights. Expected total training remains under 60s.

Result: `d83d73d`, Eval AUC **0.7673**, discard. Run time: 45.1s (training 29.2s, eval 15.9s, ok)

AUC falls slightly from 0.7674 to 0.7673 while training rises to 29.2s and the artifact grows to 109.3MB. Retain the three-member ensemble.

## Experiment 75 — ablation/simplification: Test hour-only scheduled-time representation

Removing the explicit departure-minute feature helped earlier, but raw CRSDepTime still exposes minute-level schedule details. Remove that numeric column from the tree inputs while retaining categorical hour and all six-hour correction keys. This tests whether the stronger deep trees benefit from coarser, less noisy schedule representation. The original row field remains available only for deriving these features.

Result: `d739e8e`, Eval AUC **0.7668**, discard. Run time: 37.9s (training 22.6s, eval 15.3s, ok)

AUC falls from 0.7674 to 0.7668 without raw CRSDepTime. Precise scheduled time remains useful to the stronger regularized models.

## Experiment 76 — ablation/simplification: Measure whether residual corrections remain necessary

The base ensemble is now substantially stronger than when the correction tables were introduced. Remove all five residual correction stages, their prepared keys, and the correction wrapper, retaining the exact three base models and fixed average. This large simplification tests whether the improved trees alone now suffice.

Result: `9280c50`, Eval AUC **0.7664**, discard. Run time: 32.1s (training 17.7s, eval 14.4s, ok)

The base ensemble alone scores 0.7664 versus 0.7674 with corrections. The grouped residual stages still provide useful information, so restore the best saved model.

## Experiment 77 — reproducibility check of the retained model

The retained label-smoothing gain is only 0.0001 over its predecessor. Re-run the existing committed train.py unchanged to confirm that the final reported result is reproducible after the ablation resets. This is a confirmation run, not a new parameter candidate; it uses the same commit and unchanged harness.

Result: `3651943`, Eval AUC **0.7674**, keep. Run time: 40.8s (training 24.5s, eval 16.3s, ok)

The retained commit reproduces 0.7674 exactly at the displayed precision. Final artifact reload checks pass for row/batch feature and prediction equivalence, target independence, probability bounds/normalization, and unknown categories. Harness status reports TIME IS UP; no further experiments are started.

## Final summary

The two-hour experiment budget is exhausted. Branch **oct2** is left at best kept commit **3651943**.

- Baseline Eval AUC: **0.7203** (`92e43e6`).
- Best kept Eval AUC: **0.7674** (`3651943`), an absolute improvement of **0.0471**.
- **77 completed evaluations**: 76 candidate runs including baseline, followed by one unchanged confirmation of the best commit. No crashes or timeouts.
- Confirmation timing: **24.5s training**, **16.3s evaluation**, **40.8s total**, within both harness limits. Saved artifact: **81.8MB**.
- Confirmation reproduced the displayed AUC exactly. The artifact passed feature and prediction consistency between individual rows and batches, target-independence checks, probability bounds/normalization, and unseen-category handling.
- Only `train.py` differs from the starting tracked commit. The tracked tree is clean; the final call remains `save_and_evaluate(model, prepare)`. Results, research notes, and timing remain uncommitted as instructed.

### What worked

Categorical specific-date features were much more effective than the original coarse calendar representation. Native categorical carrier and airport features, scheduled time, distance, and categorical departure hour form the final base inputs. Fixed category indexes and one DataFrame construction make row-by-row preparation much faster.

The final model averages raw margins from three XGBoost logistic models: a 16-leaf loss-guided model, a depth-four model, and a depth-eight model. All use 1200 rounds, learning rate 0.05, min_child_weight 20, L2 10, and L1 5. L1 regularization was the strongest late improvement and made the longer horizon and deeper interactions worthwhile. Modest target smoothing (0.05/0.95) added a small reproducible improvement.

Five sparse additive Newton correction stages remain useful: origin/date, destination/date, carrier/date, origin/date/six-hour block, and carrier/date/six-hour block. They use original binary labels, L1 0.5, and L2 10. Removing them lowered AUC by 0.0010. All preparation remains row-local; fitted correction coefficients are model parameters, not input-target features.

### What did not work

High-cardinality route categories, generic sampling, stronger L2, pairwise ranking, DART, geographic embeddings, several extra interactions, probability averaging, adjacent-date smoothing, and daily initial margins did not improve the kept model. Low-rank airport/date corrections briefly helped, but the stronger regularized trees made them redundant; removing them then improved AUC and simplified the code. L1 20 over-regularized the final ensemble. A fourth member, a single deep model, and hour-only scheduled-time features all fell short.

### Next experiments

In a new authorized run, investigate whether correction families benefit from different shrinkage strengths, whether a compact ensemble can retain the current score, and how much the strongly regularized model benefits from a different boosting horizon. Preserve the unchanged harness and use the final model here as the new baseline.

### Protocol note

The accidental setup-time read of `prepare.py`, before its restriction was seen, was disclosed and documented earlier in this log. It was not executed or accessed again. No held-out data, human-only evaluation outputs, or archived earlier results were accessed during this research loop.
