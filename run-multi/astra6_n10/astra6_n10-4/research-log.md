# XGBoost experiment: oct2

## Setup — 2026-10-02

- Created branch `oct2` directly from the starting HEAD, `92e43e6`.
- Read `program.md`, `README-autoresearch.md`, `train.py`, and `harness.py`.
- Confirmed `data/train.csv` and `data/eval.csv` exist. Inspected only the training data: 200,000 rows, all expected columns present, no missing values, and 100,000 examples of each target class.
- Confirmed required packages import: pandas 3.0.6, NumPy 2.5.3, XGBoost 3.4.1, scikit-learn 1.9.1, and cloudpickle 3.1.2. Python is 3.14.4; 8 logical CPUs are available.
- Confirmed `train.py` and `harness.py` compile successfully without executing training or evaluation.
- Initialized `results.tsv` with its header only. No baseline has been run.
- Left the starter training code unchanged: 30 trees, depth 6, learning rate 0.1, native categorical handling, and random seed 42.
- The experiment clock has not started. On the user's go-ahead, the first action must be `python3 harness.py start`, followed by the unchanged baseline through `python3 harness.py run`.
- Before the first non-baseline experiment, research relevant primary sources and record citations, hypotheses, and results here. Run one experiment at a time within the two-hour budget.

### Setup incident

`prepare.py` was inadvertently included in the initial batched file read before the restrictions in `program.md` had been read. This was disclosed to the user. The script was not executed, and no evaluation data, held-out data, or archived results were inspected. Its contents are excluded from experiment design.

## Experiment 01 — baseline — 92e43e6

- Eval AUC: **0.7203**; training 1.1 s including startup, evaluation 30.9 s. Kept.
- Unchanged starter establishes the reference point.

## Initial research

- [XGBoost parameter tuning](https://xgboost.readthedocs.io/en/release_3.3.0/tutorials/param_tuning.html): tree complexity, shrinkage, and sampling are complementary ways to control fit. Start by testing whether the 30-tree starter underfits.
- [XGBoost parameters](https://xgboost.readthedocs.io/en/release_3.3.0/parameter.html): depth, child weight, regularization, and categorical partition thresholds give distinct controls. Candidate ranges for this run: 100–1500 trees, eta 0.03–0.15, depth 4–10, child weight 1–50, and subsample 0.7–1.0; these are hypotheses, not guarantees.
- [Scikit-learn time feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html): explicit calendar components and interactions can expose structure; trees can already learn nonlinear effects of ordered time variables. Consider scheduled minute/hour, day of year, and date interactions, computed row by row.
- Latest development XGBoost docs describe a future change to categorical defaults; use explicit settings when experimenting with category splits and compare to installed 3.4.1 behavior.

## Experiment 02 — more boosting rounds

- Classification: follow-up to the baseline.
- Hypothesis: 30 trees underfit; 300 trees at the same depth and learning rate should capture more interactions without changing the representation.
- Change: n_estimators 30 → 300. Source: XGBoost tuning guide above.

- Result: commit `ecfd411`, Eval AUC **0.7342**, training 2.5 s / evaluation 30.7 s. Keep (+0.0139).

## Experiment 03 — boosting capacity boundary

- Classification: follow-up to experiment 02.
- Hypothesis: the gain from 30 to 300 rounds may extend to 900 rounds; this tests the capacity boundary before feature engineering.
- Change: n_estimators 300 → 900, all else fixed.

- Result: commit `b04619f`, Eval AUC **0.7264**, training 5.8 s / evaluation 31.2 s. Discard (−0.0078); return to `ecfd411`.
- The 300-round artifact assigns its largest average split gain to scheduled departure time. This is a model diagnostic, not a separate evaluation metric.
- Installed categorical defaults confirmed from the current run's saved model: one-hot threshold 4, partition threshold 64.

## Experiment 04 — explicit calendar date

- Classification: exploration of feature engineering.
- Hypothesis: combining month and day exposes date-specific disruption patterns that require multiple splits with separate calendar columns.
- Change: add one native categorical Date feature, with levels fitted on train. Retain the 300-tree model.
- Sources: scikit-learn time-feature example above; [XGBoost categorical handling](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html).
- Inference constraint: compute each date from its own row; no label or batch statistics enter the feature.

- Result: commit `ae7eba3`, Eval AUC **0.7503**, training 2.7 s / evaluation 36.1 s. Keep (+0.0161).
- Explicit date interactions produced a larger gain than increasing rounds from 30 to 300.

## Experiment 05 — simplify category conversion

- Classification: ablation/simplification of experiment 04.
- Hypothesis: the explicit membership mask is redundant because pandas.Categorical already maps values outside fixed categories to missing; removing it should preserve AUC and speed up row preparation.
- Change: remove six repeated isin/where operations per row, retaining fixed category levels.
- Source: [pandas.Categorical reference](https://pandas.pydata.org/docs/reference/api/pandas.Categorical.html).

- Result: commit `4fada7c`, Eval AUC **0.7503**, keep. Run time: 29.1s (training 2.6s, eval 26.5s, ok)
- Decision: Identical AUC with simpler code and faster evaluation. Known/unknown/missing category conversion and row invariance checks passed.

## Experiment 06 — regularize leaf size

- Classification: follow-up to the overfitting observed in experiment 03 and the date feature gain.
- Hypothesis: min_child_weight=20 will prevent sparse category partitions from fitting noise while retaining the useful date effect.
- Change: raise min_child_weight from default 1 to 20; keep 300 trees and depth 6.
- Source: XGBoost parameter reference in initial research.

- Result: commit `c61d10f`, Eval AUC **0.7507**, keep. Run time: 29.5s (training 2.8s, eval 26.7s, ok)
- Decision: AUC improved by 0.0004 with one regularization parameter and no extra feature complexity.

## Experiment 07 — restrict categorical partition size

- Classification: follow-up to experiment 06.
- Hypothesis: leaf-size regularization helped slightly; limiting max_cat_threshold to 16 may further curb noisy groupings of sparse airports and dates.
- Change: max_cat_threshold 64 (default) → 16, keeping min_child_weight=20.
- Source: XGBoost categorical parameter reference.

- Result: commit `8c82606`, Eval AUC **0.7524**, keep. Run time: 28.5s (training 2.3s, eval 26.2s, ok)
- Decision: AUC improved by 0.0017; keep the simpler categorical partitions.

## Experiment 08 — shallower interactions

- Classification: ablation/simplification of the regularized date model.
- Hypothesis: depth 4 may generalize better than depth 6 now that date is explicit, reducing high-order interactions that are poorly supported.
- Change: max_depth 6 → 4; all other settings unchanged.

- Result: commit `a6858b3`, Eval AUC **0.7471**, discard. Run time: 27.9s (training 1.8s, eval 26.1s, ok)
- Decision: AUC fell by 0.0053; explicit date still needs richer interactions.

## Experiment 09 — deeper regularized interactions

- Classification: follow-up to experiment 08's loss from shallower trees.
- Hypothesis: depth 8 can represent airport/date/time interactions better than depth 6; min_child_weight=20 and max_cat_threshold=16 should moderate sparse splits.
- Change: max_depth 6 → 8. This brackets depth in the opposite direction after depth 4 failed.

- Result: commit `6489270`, Eval AUC **0.7522**, discard. Run time: 30.0s (training 3.7s, eval 26.3s, ok)
- Decision: AUC fell by 0.0002 and training became slower; depth 6 remains best.

## Experiment 10 — ordered day of year

- Classification: exploration of temporal representation.
- Hypothesis: categorical Date captures shared disruptions, while an additional ordered day-of-year coordinate may let trees group nearby dates and seasonal intervals efficiently.
- Change: add numeric DayOfYear using the fixed non-leap-year month offsets for this 2005 dataset. Keep the winning depth-6 settings.
- Source: scikit-learn time-feature example from initial research. This is an inferred adaptation to the current data.

- Result: commit `4127a7d`, Eval AUC **0.7511**, discard. Run time: 30.0s (training 2.4s, eval 27.6s, ok)
- Decision: AUC fell by 0.0013; the added temporal coordinate did not justify its feature complexity.

## Synthesis after 10 experiments

- Best: `8c82606`, Eval AUC 0.7524, versus baseline 0.7203 (+0.0321).
- Useful changes: 300 rounds, explicit categorical Date, min_child_weight=20, max_cat_threshold=16. Removing redundant category masks preserved predictions and reduced evaluation cost.
- Unhelpful: 900 unregularized rounds, depth 4 or 8, and ordered day of year. Depth 6 appears to balance interaction capacity and noise in this representation.
- Current theory: specific-date effects and their interactions with time and airport matter; unrestricted categorical partitions overfit. Seek more stable fitting and explicit operational interactions next.

### Research refresh

- [XGBoost original paper](https://arxiv.org/abs/1603.02754): shrinkage and feature subsampling provide regularization beyond leaf constraints. Test a slower boosting path before adding many more features.
- [CatBoost paper](https://arxiv.org/abs/1706.09516) and [TargetEncoder documentation](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html): target-derived categorical encodings can create training/inference shift. Avoid naive target-mean features and do not introduce cross-validation into this experiment.
- [FlightSense paper](https://arxiv.org/abs/2605.07364): schedule features are a meaningful baseline; its larger gains use aircraft-rotation and weather inputs unavailable here. Adapt only schedule interactions available in train.csv.

## Experiment 11 — slower boosting path

- Classification: follow-up to regularized categorical model.
- Hypothesis: 600 rounds at learning_rate=0.05 will make smaller fitting steps than 300 at 0.1, improving generalization at comparable total shrinkage.
- Change: n_estimators=600, learning_rate=0.05; all feature and regularization settings retained.

- Result: commit `74f90b0`, Eval AUC **0.7537**, keep. Run time: 29.9s (training 3.6s, eval 26.3s, ok)
- Decision: AUC improved by 0.0013 with the same feature set and modest training cost.

## Experiment 12 — stochastic row sampling

- Classification: follow-up to the slower boosting gain.
- Hypothesis: sampling 80% of training rows independently for each tree will regularize repeated fitting to noisy category signals.
- Change: subsample=0.8; retain all features in every tree.
- Source: original XGBoost paper and tuning guide.

- Result: commit `1c2a071`, Eval AUC **0.7436**, discard. Run time: 30.2s (training 3.8s, eval 26.4s, ok)
- Decision: AUC fell by 0.0101; reducing per-tree observations destabilizes this categorical model.

## Experiment 13 — explicit route category

- Classification: exploration of operational feature interactions.
- Hypothesis: an Origin–Dest category can capture route-level behavior in fewer splits than separate endpoint features.
- Change: add Route with levels learned from train, use all training rows per tree.
- Sources: XGBoost categorical tutorial and schedule-based airline research noted above. Route benefit is a hypothesis for this dataset.

- Result: commit `3d78f98`, Eval AUC **0.7457**, discard. Run time: 45.2s (training 6.0s, eval 39.2s, ok)
- Decision: AUC fell by 0.0080 and evaluation slowed; route categories overfit at these settings.

## Experiment 14 — one-hot categorical splits

- Classification: exploration of a different categorical splitting strategy.
- Hypothesis: selecting one category per split, rather than label-guided groups, may generalize better given the failure of sparse route groupings and row sampling.
- Change: max_cat_to_onehot=512, enough to use one-hot splits for all current categorical columns; return to the representation without Route.
- Source: XGBoost categorical tutorial, contrasting equality tests with category-set membership splits.

- Result: commit `0a1ba39`, Eval AUC **0.7356**, discard. Run time: 29.3s (training 2.9s, eval 26.4s, ok)
- Decision: AUC fell by 0.0181. Equality splits may need many more rounds than category-set splits; test that specific capacity hypothesis separately.

## Research check after categorical-strategy failures

- Revisited [XGBoost's categorical versus one-hot example](https://xgboost.readthedocs.io/en/stable/python/examples/cat_in_the_dat.html) and categorical split definitions. A category equality split isolates one value while a partition can group many; the same tree count does not imply comparable category-fitting capacity.
- Next test expands one-hot capacity substantially, then returns to partitioning if that does not beat the retained model.

## Experiment 15 — adequate capacity for one-hot splits

- Classification: follow-up to experiment 14, testing a specific underfitting explanation.
- Hypothesis: 3,000 one-hot trees may close the gap left by 600 because each equality split represents only one category.
- Change from retained best: max_cat_to_onehot=512 and n_estimators=3000, learning_rate remains 0.05. Expected training cost is comfortably below 60 seconds based on experiment 14.

- Result: commit `4403174`, Eval AUC **0.7461**, discard. Run time: 37.4s (training 10.3s, eval 27.2s, ok)
- Decision: Extra capacity helped one-hot splitting, but 0.7461 remains 0.0076 below the simpler retained partition model.

## Experiment 16 — cache category types and construct features once

- Classification: ablation/simplification of the best model's preparation.
- Hypothesis: constructing category metadata once and assembling a single DataFrame from prepared columns can preserve the feature matrix exactly while avoiding repeated dtype construction and frame mutation per row.
- Change: cache pandas.CategoricalDtype objects fitted on train; build Date keys row by row; retain the identical feature order and winning model.
- Source: pandas.Categorical API's dtype parameter. Validate equivalence and single-row behavior against the previous saved artifact.

- Result: commit `0172af5`, Eval AUC **0.7537**, keep. Run time: 16.1s (training 3.7s, eval 12.4s, ok)
- Decision: Identical AUC and exact feature equivalence on 25 training rows; evaluation fell from 26.3 s to 12.4 s. Single-row invariance also passed.

## Experiment 17 — smoothed airport/date delay rates

- Classification: exploration of supervised lookup features.
- Hypothesis: airport-specific daily disruption rates contain information that a global Date category and tree interactions estimate inefficiently.
- Add OriginDateRate and DestDateRate with a fixed 0.5 prior and smoothing strength 10. Fit aggregate statistics on train only; expose rates, never counts, to the model.
- Adapt [leave-one-out encoding](https://contrib.scikit-learn.org/category_encoders/leaveoneout.html) to the required identical per-row transform: subtract all training records having the row's exact predictor tuple from each airport/date aggregate. This excludes a training example's own target without consulting the target passed to prepare, using row indices, or branching on training versus evaluation.
- Duplicate predictor tuples are excluded together. An unseen tuple contributes nothing to the exclusion. Both rules apply identically to any input row.
- All lookup fitting stays at module level; all transformations stay inside prepare. No additional metric, cross-validation, external dataset, or package is introduced.
- Functional checks will cover batch invariance, label independence, and equality to direct training-data means with matching predictor tuples removed.

- Result: commit `306b089`, Eval AUC **0.7458**, discard. Run time: 19.0s (training 4.3s, eval 14.7s, ok)
- Decision: AUC fell by 0.0079 despite passing direct exclusion-mean, input-label independence, and batch-invariance tests. Sparse rate granularity may still be overfit; test documented noise regularization once.

## Experiment 18 — regularize airport/date rate granularity

- Classification: follow-up to experiment 17.
- Hypothesis: small deterministic jitter will prevent trees from exploiting fine discrete patterns in leave-out rate estimates while preserving broad airport/day risk information.
- Source: Category Encoders leave-one-out documentation recommends noise for regularization. Adaptation here applies the same predictor-derived jitter to every row in both training and inference, preserving required row invariance.
- Change: restore experiment 17's feature idea and add uniform jitter in [-0.06, 0.06], keyed only by the row's predictor values. No hash or sample count is exposed as a feature.

- Result: commit `9e36cc6`, Eval AUC **0.7546**, discard. Run time: 28.8s (training 4.4s, eval 24.4s, ok)
- Decision: Numerical gain of 0.0009 over best is too small for 28 additional lines, a larger artifact, and slower evaluation. Retain simpler model; test a lower-capacity follow-up before abandoning rates.

## Experiment 19 — fewer trees with rate features

- Classification: follow-up and simplification of experiment 18.
- Hypothesis: the rate features already summarize local risk; 600 boosting rounds may overfit their residual noise. Reducing to 200 may reveal a worthwhile gain while simplifying the fitted model.
- Change: restore the jittered rate features, with n_estimators=200 instead of 600. Retain depth 6 and learning_rate=0.05.
- Best retained model remains the simpler 0.7537 model because the prior 0.0009 improvement did not justify feature complexity.

- Result: commit `f18c0f9`, Eval AUC **0.7547**, discard. Run time: 26.4s (training 2.7s, eval 23.7s, ok)
- Decision: AUC 0.7547 is only 0.0010 above the simpler retained model; the lookup, exclusion, and jitter complexity is not justified. Row invariance passed. Conclude this feature family for now.

## Experiment 20 — scheduled hour and minute

- Classification: exploration of simple schedule decomposition.
- Hypothesis: explicit departure hour and minute make scheduling-bank and within-hour effects easier to represent than the HHMM integer alone.
- Change: add DepHour=CRSDepTime//100 and DepMinute=CRSDepTime%100 to the retained model without target-rate lookups.
- Source: scikit-learn time-feature engineering example; the proposed benefit is specific to this dataset and will be tested.

- Result: commit `aefbef7`, Eval AUC **0.7527**, discard. Run time: 16.3s (training 3.7s, eval 12.5s, ok)
- Decision: AUC fell by 0.0010, so keep the original HHMM feature alone.

## Synthesis after 20 experiments

- Best retained: `0172af5`, Eval AUC 0.7537 (+0.0334 versus baseline). Highest observed was 0.7547 with complex target-rate machinery; discarded under the simplicity criterion.
- Smaller boosting steps helped. One-hot category splits, even with 3,000 trees, were inferior to partitioning. Row subsampling and high-cardinality Route features hurt substantially.
- Target-rate lookups were carefully validated for label exclusion and one-row invariance. Jitter reduced their overfitting, but gains remained too small for the extra state, code, and inference time. Hour/minute decomposition did not help.
- Preparation simplification was a clear win: 12-second evaluation while preserving feature values exactly.
- Current theory: improve fitting of the compact Date/time/airport representation before introducing further complicated features. Prioritize leaf-weight regularization, split pruning, leaf-wise growth, and a different boosting objective.

### Research refresh

- [XGBoost tree methods](https://xgboost.readthedocs.io/en/stable/treemethod.html) and the parameter reference support separating split search, leaf growth, and regularization decisions.
- [DART paper](https://arxiv.org/abs/1505.01866) proposes dropping existing trees during training to counter late-tree over-specialization. This is a later candidate under the training limit.
- [XGBoost learning to rank](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html) describes rank:pairwise and sampled pair construction. A global binary ranking objective is a possible later exploration; the harness AUC remains the sole selection metric.

## Experiment 21 — stronger L2 leaf penalty

- Classification: follow-up to the compact regularized model.
- Hypothesis: reg_lambda=20 will shrink low-support leaf updates more than the default 1, reducing residual categorical overfitting without removing interactions.
- Change: reg_lambda=20; all other winning settings retained.

- Result: commit `ca4ff3e`, Eval AUC **0.7564**, keep. Run time: 15.9s (training 3.6s, eval 12.3s, ok)
- Decision: AUC improved by 0.0027 using one regularization parameter; this also beats the discarded complex rate models.

## Experiment 22 — prune weak splits

- Classification: follow-up to the L2 regularization gain.
- Hypothesis: gamma=2 will remove low-benefit splits that can fit noise after the strongest effects have been learned.
- Change: gamma=2, retaining reg_lambda=20 and the compact feature set.
- Source: XGBoost parameter reference, minimum loss reduction required for a split.

- Result: commit `27c64b2`, Eval AUC **0.7503**, discard. Run time: 15.0s (training 2.6s, eval 12.3s, ok)
- Decision: AUC fell by 0.0061; pruning weak individual splits removes useful cumulative structure.

## Experiment 23 — tighter categorical groups

- Classification: follow-up to the earlier gain from reducing max_cat_threshold 64 to 16.
- Hypothesis: max_cat_threshold=4 may further suppress noisy grouped categories while retaining more flexibility than the unsuccessful one-hot strategy.
- Change: max_cat_threshold 16 → 4; gamma returns to default 0, retain reg_lambda=20.

- Result: commit `93835a7`, Eval AUC **0.7451**, discard. Run time: 15.7s (training 3.4s, eval 12.4s, ok)
- Decision: AUC fell by 0.0113; category groups need more flexibility than threshold 4 or one-hot splitting allows.

## Experiment 24 — adaptive leaf-wise tree growth

- Classification: exploration of tree architecture.
- Hypothesis: lossguide growth can allocate deeper interactions to well-supported branches without increasing the 64-leaf capacity of a depth-6 tree.
- Change: grow_policy=lossguide, max_depth=0, max_leaves=64. Restore max_cat_threshold=16 and retain reg_lambda=20.
- Source: XGBoost parameter reference for grow_policy and max_leaves.

- Result: commit `02f2961`, Eval AUC **0.7601**, keep. Run time: 19.2s (training 6.7s, eval 12.5s, ok)
- Decision: AUC improved by 0.0037. Adaptive allocation of splits helps more than simply raising fixed depth.

## Experiment 25 — leaf capacity in adaptive trees

- Classification: follow-up to experiment 24.
- Hypothesis: the substantial gain from adaptive growth may extend to 128 leaves, capturing additional supported date/airport/time interactions.
- Change: max_leaves 64 → 128, retaining lossguide growth and regularization. This tests capacity in the newly successful architecture, not the discarded fixed-depth strategy.

- Result: commit `9436b21`, Eval AUC **0.7598**, discard. Run time: 23.8s (training 11.0s, eval 12.8s, ok)
- Decision: AUC 0.7598 is 0.0003 below 64 leaves, with almost double the training time; retain smaller trees.

## Experiment 26 — simplify calendar inputs

- Classification: ablation/simplification of the adaptive model.
- Diagnostics: the 64-leaf artifact has median maximum tree depth 17 (maximum 31). Date and airports dominate split counts; DayOfWeek is rarely used. These are model diagnostics, not additional performance metrics.
- Hypothesis: the combined Date category may make separate Month, DayofMonth, and DayOfWeek redundant. Removing them may reduce noisy choices and preparation cost.
- Change: retain only UniqueCarrier, Origin, Dest as base categorical columns, plus the engineered Date and original numeric columns.

- Result: commit `57101d3`, Eval AUC **0.7593**, discard. Run time: 15.2s (training 5.9s, eval 9.3s, ok)
- Decision: AUC fell by 0.0008. Although evaluation became 3 seconds faster, the implementation was not materially simpler; restore the pooled calendar inputs.

## Experiment 27 — bracket L2 strength in adaptive trees

- Classification: follow-up to experiment 21 and the adaptive-growth gain.
- Hypothesis: deeper adaptive branches may benefit from a stronger leaf-weight penalty than reg_lambda=20; the earlier increase from 1 to 20 was clearly beneficial.
- Change: reg_lambda 20 → 100. Restore all original calendar inputs and keep 64 leaves.

- Result: commit `f805877`, Eval AUC **0.7627**, keep. Run time: 19.6s (training 7.2s, eval 12.5s, ok)
- Decision: AUC improved by 0.0026, supporting stronger shrinkage of the adaptive model.

## Experiment 28 — L1 suppression of tiny leaf updates

- Classification: follow-up to stronger leaf-weight regularization.
- Hypothesis: reg_alpha=5 can suppress weak leaf updates while preserving the deeper branches that hard split pruning removed too aggressively.
- Change: add reg_alpha=5 to the 64-leaf model with reg_lambda=100.
- Source: XGBoost parameter reference on L1 versus L2 weight regularization.

- Result: commit `3102d59`, Eval AUC **0.7668**, keep. Run time: 21.4s (training 8.4s, eval 13.0s, ok)
- Decision: AUC improved by 0.0041 using one additional regularization parameter.

## Experiment 29 — boosting length under stronger regularization

- Classification: follow-up to experiments 27–28.
- Hypothesis: strong L1/L2 regularization shrinks or suppresses updates, so the new adaptive model may need more than 600 rounds to fit useful signals fully.
- Change: n_estimators 600 → 1200, learning_rate remains 0.05.
- Distinction from experiment 03: that model used depth-limited trees, default penalties, and no Date feature. This specifically tests capacity after a major change in regularization and tree structure.

- Result: commit `0a03db6`, Eval AUC **0.7668**, discard. Run time: 28.2s (training 15.0s, eval 13.2s, ok)
- Decision: AUC tied 0.7668 at four decimal places with twice as many trees. Retain the smaller 600-round model.

## Experiment 30 — carrier at departure airport

- Classification: exploration of a supported operational interaction.
- Hypothesis: a CarrierOrigin category will capture airline-specific departure-airport effects directly. Unlike the discarded Route feature, this grouping pools across destinations and should have more support per category.
- Change: add one native categorical UniqueCarrier–Origin interaction with train-fitted, cached category metadata; retain 600 rounds.
- Sources: categorical interaction handling in XGBoost and schedule-based flight-delay research already reviewed.

- Result: commit `9f27e06`, Eval AUC **0.7668**, discard. Run time: 24.5s (training 10.6s, eval 13.9s, ok)
- Decision: AUC tied 0.7668 with extra feature code and slower preparation. Retain the simpler model.

## Synthesis after 30 experiments

- Best retained: `3102d59`, Eval AUC 0.7668 (+0.0465 versus baseline).
- The key gains came from lossguide growth with 64 leaves, reg_lambda=100, and reg_alpha=5. Simply increasing depth, leaf count, or rounds did not produce the same benefit.
- Adaptive trees have long selective paths (median maximum depth 17 before the latest penalties), explaining why a uniform depth cap was restrictive. The retained 600-tree model still uses full trees at late rounds; its plateau is not caused by empty stumps.
- Hard split pruning hurt, while soft leaf penalties helped. Separate calendar components still provide useful inductive bias alongside Date. CarrierOrigin added no measurable gain.
- Next directions: pairwise ranking, early stopping from a training-only split, tree dropout, and constrained interactions. Keep the compact representation as the reference.

### Research refresh

- [XGBoost learning-to-rank guide](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html): rank:pairwise uses pairwise logistic loss without NDCG/MAP weighting; mean pair construction samples throughout a query. Test all training rows as one ranking group to target global binary ordering.
- [Estimator interface and early stopping](https://xgboost.readthedocs.io/en/stable/python/sklearn_estimator.html): a training-only validation split can choose the prediction tree range. Adapt only the single-split early-stopping method, without cross-validation or retraining.
- [Feature interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html): constrain which features share a path to test structured regularization if unconstrained adaptive trees plateau.

## Experiment 31 — pairwise logistic ranking

- Classification: exploration of a different training objective.
- Hypothesis: pairwise logistic loss may improve the global positive-versus-negative ordering measured by AUC.
- Change: fit XGBRanker with rank:pairwise, one global group, mean pair sampling at one pair per sample, and no score/lambda normalization. Keep 600 rounds and the retained structural penalties.
- Wrap ranking scores in a monotone logistic mapping solely to provide the harness's predict_proba interface. The harness evaluation and final save_and_evaluate call remain unchanged.

- Result: commit `5c247bb`, Eval AUC **0.7623**, discard. Run time: 43.3s (training 30.5s, eval 12.8s, ok)
- Decision: AUC fell by 0.0045 and training increased to 30.5 seconds; the wrapper and ranking objective did not justify their complexity.

## Experiment 32 — DART tree dropout

- Classification: exploration of a different boosting algorithm.
- Hypothesis: occasional tree dropout can reduce reliance on early trees and improve generalization beyond leaf penalties alone.
- Change: booster=dart, 250 rounds, learning_rate=0.1, rate_drop=0.05, skip_drop=0.5, normalize_type=forest. Preserve the adaptive 64-leaf architecture and penalties.
- Runtime rationale: DART repeatedly predicts with prior trees during fitting; cap rounds at 250 to stay below the 60-second training limit.
- Source: [DART paper](https://arxiv.org/abs/1505.01866) and XGBoost DART parameter definitions.

- Result: commit `566bfbd`, Eval AUC **0.0000**, crash. Run time: 60.0s (training 60.0s, eval 0.0s, timeout-training)
- Decision: Harness killed training at 60 seconds. No model score was produced. The installed library also recommends dropout parameters on the tree booster instead of the deprecated dart name.

## Experiment 33 — smaller dropout ensemble

- Classification: follow-up to experiment 32's runtime failure.
- Hypothesis: 120 trees with learning_rate=0.2 can test tree dropout within the runtime budget while retaining a substantial total update scale.
- Change: rate_drop=0.05, skip_drop=0.5, normalize_type=forest on the default tree booster, 120 rounds at eta=0.2. Use the current library's recommended interface as reported by the prior warning.
- If this controlled smaller version is not competitive, move on from dropout rather than repeatedly exceeding the limit.

- Result: commit `13ff9b0`, Eval AUC **0.7611**, discard. Run time: 38.4s (training 26.1s, eval 12.3s, ok)
- Decision: AUC 0.7611 is below 0.7668 and training is slower than the standard booster. Conclude the dropout exploration.

## Experiment 34 — training-only early stopping

- Classification: exploration of adaptive stopping.
- Hypothesis: a stratified 10% validation split from train.csv can identify a more suitable stopping point than a fixed 600 rounds, despite fitting on fewer rows.
- Change: split the training feature matrix once (random_state=42), allow up to 2500 rounds, and use an AUC EarlyStopping callback with patience 80 and save_best=True. Fit only the remaining 90%; do not retrain on additional rows.
- Source: XGBoost estimator interface and early-stopping documentation. Internal validation is used only by the training procedure; the harness Eval AUC remains the only experiment-selection metric.

- Result: commit `4c5648e`, Eval AUC **0.7650**, discard. Run time: 22.9s (training 10.2s, eval 12.6s, ok)
- Decision: AUC fell to 0.7650. Selected length was close to the retained 600 rounds, while withholding fitting rows reduced performance. No retraining was performed within this experiment.

## Experiment 35 — structured airport interactions

- Classification: exploration of interaction regularization.
- Hypothesis: separate origin- and destination-centered interaction groups can reduce noisy route-specific fitting while retaining each endpoint's calendar, carrier, and time effects.
- Change: specify two overlapping interaction-constraint groups, one excluding Dest and the other excluding Origin. Return to the retained full-training-data model and fixed 600 rounds.
- Source: XGBoost feature-interaction constraint documentation. Route-feature failure and adaptive trees' long paths motivate the restriction.

- Result: commit `6a6bb48`, Eval AUC **0.7657**, discard. Run time: 20.4s (training 7.7s, eval 12.7s, ok)
- Decision: AUC fell by 0.0011; unrestricted endpoint interactions remain useful under strong regularization.

## Experiment 36 — sample candidate features at each node

- Classification: exploration of stochastic feature selection.
- Hypothesis: colsample_bynode=0.8 will diversify greedy split choices without reducing the observations used to estimate category effects, unlike the failed row-sampling experiment.
- Change: add colsample_bynode=0.8 to the retained model. Keep all rows in every tree.
- Sources: XGBoost column-sampling parameters and [boosted-forest documentation](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html), read as preparation for possible multi-tree or averaging follow-ups.

- Result: commit `5f8497d`, Eval AUC **0.7672**, keep. Run time: 20.7s (training 7.8s, eval 12.9s, ok)
- Decision: AUC improved by 0.0004 with one parameter and slightly faster fitting; retain stochastic split candidates.

## Experiment 37 — boosted ensembles of randomized trees

- Classification: follow-up to experiment 36.
- Hypothesis: averaging three randomized trees at each boosting step will reduce variance from feature sampling and improve generalization.
- Change: num_parallel_tree=3, retain 600 boosting rounds and colsample_bynode=0.8. This fits 1800 total trees within one XGBoost model.
- Source: XGBoost random-forest documentation explicitly supports combining multiple trees per round with multiple boosting rounds. All rows remain available for each tree because row subsampling performed poorly.

- Result: commit `1c25951`, Eval AUC **0.7675**, keep. Run time: 37.7s (training 23.8s, eval 13.9s, ok)
- Decision: AUC improved by 0.0003 with one standard XGBoost parameter. Training remains below the limit and evaluation overhead is small.

## Experiment 38 — finer numeric split resolution

- Classification: exploration of histogram resolution.
- Hypothesis: max_bin=1024 will preserve finer distinctions in scheduled departure time and distance than the default 256 bins, with strong regularization limiting spurious splits.
- Change: max_bin 256 → 1024; retain the three-tree-per-round model.
- Source: XGBoost tree-method and histogram parameter documentation. Unlike the discarded hour/minute columns, this changes split resolution without adding features.

- Result: commit `1b17c27`, Eval AUC **0.7677**, keep. Run time: 38.3s (training 24.4s, eval 13.9s, ok)
- Decision: AUC improved by 0.0002 at nearly unchanged runtime, with no additional features.

## Experiment 39 — bracket L1 regularization

- Classification: follow-up to experiment 28's substantial gain from reg_alpha=5.
- Hypothesis: a stronger L1 threshold may further reduce residual noise in the randomized adaptive trees.
- Change: reg_alpha 5 → 20, keeping the now-retained histogram and multi-tree settings. This brackets regularization strength rather than making a cosmetic adjustment.

- Result: commit `7dadc44`, Eval AUC **0.7560**, discard. Run time: 35.1s (training 21.7s, eval 13.4s, ok)
- Decision: AUC fell by 0.0117; the stronger L1 threshold removes useful effects. Retain reg_alpha=5.

## Experiment 40 — departure time relative to route schedule

- Classification: exploration of non-target lookup features.
- Hypothesis: the deviation from a route's typical scheduled departure time captures relative schedule position more compactly than a high-cardinality route category.
- Change: fit each Origin–Dest route's median scheduled minutes on train, then add current scheduled minutes minus that fixed median inside prepare. Unknown routes map to NaN.
- Sources: the permitted fitted-lookup design in program.md and [pandas group-median API](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.api.typing.DataFrameGroupBy.median.html). Predictive value is a hypothesis, not an assertion from the API documentation.
- No counts or labels are used as features; no input-batch statistics are computed.

- Result: commit `e091077`, Eval AUC **0.7672**, discard. Run time: 39.5s (training 24.8s, eval 14.7s, ok)
- Decision: AUC fell by 0.0005 with additional feature code and lookup state; retain the compact representation.

## Synthesis after 40 experiments

- Best retained: `1b17c27`, Eval AUC 0.7677 (+0.0474 versus baseline).
- Node-level feature sampling, three trees per boosting round, and finer numeric bins provided small cumulative improvements. The compact model remains preferable to extra carrier/route/rate features.
- Pairwise ranking and dropout did not beat logistic boosting; the first dropout configuration exceeded the training limit. Training-only early stopping selected 602 rounds, corroborating the current scale but scoring lower because fitting used fewer rows.
- Hard interaction restrictions and excessive L1 regularization hurt. Reg_alpha=5 is useful, while 20 clearly underfits. The route-relative median feature did not improve AUC.
- Next theory: improve generalization across airports with a non-target geometric representation, then test simpler ensembles and intermediate regularization rather than repeating failed high-cardinality categories.

### Research refresh

- [Classical multidimensional scaling](https://web.mit.edu/r/current/arch/i386_linux26/lib/R/library/stats/html/cmdscale.html) describes recovering low-dimensional coordinates from pairwise dissimilarities.
- [SciPy shortest_path](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.shortest_path.html) supports weighted route-graph distances. The Isomap literature motivates shortest-path distances followed by classical scaling; the adaptation here uses observed flight-route distances and makes no claim of recovering exact latitude/longitude.
- [XGBoost boosted forests](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) informed the successful multi-tree-per-round experiment.

## Experiment 41 — airport route-distance geometry

- Classification: exploration of unsupervised geometric lookup features.
- Hypothesis: a two-dimensional layout learned from training-route distances can pool regional behavior across airports that categorical splits otherwise treat independently.
- Change: build an undirected graph from train-only median route distances, fill missing distances by shortest paths, and fit a classical two-dimensional scaling lookup. Add two coordinates each for Origin and Dest inside prepare.
- Only train.csv is used. No target, row count, external airport table, or evaluation data enters the layout. All coordinates are fitted once at module level and looked up independently per row.

- Result: commit `8852ad9`, Eval AUC **0.7679**, discard. Run time: 41.4s (training 26.9s, eval 14.5s, ok)
- Decision: AUC gain of 0.0002 is too small for 22 additional lines and the geometric fitting machinery. Keep the compact model; test a coarser regional representation once.

## Experiment 42 — airport regions from route-distance geometry

- Classification: follow-up and representation simplification of experiment 41.
- Hypothesis: coarse geometric regions may share calendar-related effects across airports more directly than four continuous coordinates.
- Change: cluster the train-only two-dimensional airport layout into 12 regions with KMeans (n_init=10, random_state=42); add OriginRegion and DestRegion as fixed-level categoricals instead of coordinate columns.
- Sources: classical scaling references above and [scikit-learn KMeans](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html).
- No target or frequency feature enters the clustering; evaluation rows only use saved airport-to-region lookups.

- Result: commit `10e2531`, Eval AUC **0.7677**, discard. Run time: 40.2s (training 24.5s, eval 15.7s, ok)
- Decision: AUC tied 0.7677 with 25 added lines and slower preparation. Single-row invariance passed; retain the compact model without geometry.

## Experiment 43 — independently trained soft-voting boosters

- Classification: follow-up to successful randomized-tree averaging.
- Hypothesis: averaging three independently optimized boosting trajectories may reduce variance more effectively than averaging three trees within each shared trajectory.
- Change: use a standard VotingClassifier with three XGBClassifier members (seeds 42, 137, 2026), each 600 rounds and one tree per round. Keep the same feature sampling, penalties, and numeric bins. Fit members sequentially on the same train.csv rows.
- Total tree count remains 1800, comparable to the retained model. The harness sees the standard predict_proba interface.
- Source: scikit-learn VotingClassifier documentation on soft voting.

- Result: commit `1ec94ff`, Eval AUC **0.7677**, discard. Run time: 36.1s (training 22.3s, eval 13.8s, ok)
- Decision: AUC tied 0.7677 at comparable tree count and runtime; the native multi-tree model requires less orchestration code.

## Plateau research after experiments 40–43

- Route medians, geometric coordinates/regions, and independent voting all produced changes within 0.001 of the retained model without a worthwhile simplification.
- Read [XGBoost LearningRateScheduler](https://xgboost.readthedocs.io/en/stable/python/python_api.html#xgboost.callback.LearningRateScheduler) to test a changing optimization path rather than another redundant representation.

## Experiment 44 — decaying learning rate

- Classification: exploration of boosting-step scheduling.
- Hypothesis: larger early updates and smaller late updates can fit broad patterns efficiently while reducing late-stage noise.
- Change: exponentially decay eta from 0.1 to 0.02 across 600 rounds. Its average is about 0.05, making total shrinkage comparable to the constant-rate baseline.
- Keep the same tree count, feature set, regularization, and three trees per round.

- Result: commit `6369ae2`, Eval AUC **0.7671**, discard. Run time: 38.4s (training 24.1s, eval 14.2s, ok)
- Decision: AUC fell by 0.0006; the constant 0.05 path remains better and simpler.

## Experiment 45 — stronger L2 shrinkage boundary

- Classification: follow-up to the gains from reg_lambda 1 → 20 → 100.
- Hypothesis: reg_lambda=300 may further improve generalization of the randomized adaptive model, or identify the point where shrinkage becomes excessive.
- Change: reg_lambda 100 → 300, retaining reg_alpha=5 and the constant learning rate.

- Result: commit `bdd8c2c`, Eval AUC **0.7663**, discard. Run time: 39.7s (training 25.4s, eval 14.3s, ok)
- Decision: AUC fell by 0.0014, identifying an upper shrinkage boundary; retain reg_lambda=100.

## Experiment 46 — label-smoothed logistic training

- Classification: exploration of loss regularization.
- Hypothesis: replacing hard training targets with 0.05 and 0.95 inside the logistic objective may reduce overconfident fitting and improve ranking under finite model capacity.
- Sources: [When Does Label Smoothing Help?](https://arxiv.org/abs/1906.02629) studies neural networks; adapting the idea to boosted trees is an explicit experimental inference, not a claimed result from that paper. [XGBoost custom objectives](https://xgboost.readthedocs.io/en/stable/tutorials/custom_metric_obj.html) provides the supported gradient/Hessian interface.
- Change: use gradient sigmoid(margin) − (0.05 + 0.9*y) and ordinary logistic Hessian. Keep actual y returned by prepare and the harness evaluation unchanged.
- Verify the custom derivatives by finite differences before the timed run. No custom evaluation metric is added.

- Result: commit `edd1d0f`, Eval AUC **0.7676**, discard. Run time: 39.6s (training 25.4s, eval 14.1s, ok)
- Decision: AUC was 0.0001 lower than the built-in objective. Derivative checks passed, but the custom loss adds complexity without benefit.

## Experiment 47 — intermediate calendar timescale

- Classification: exploration of temporal pooling.
- Hypothesis: a calendar-week category can represent multi-day seasonal/disruption patterns more efficiently than separate dates or months.
- Change: add a Monday-aligned week block derived deterministically from month/day in the known 2005 calendar. Keep Date and the original calendar columns.
- Source: scikit-learn time-feature engineering reference. Unlike experiment 10's numeric DayOfYear, this adds a coarse categorical timescale to the much more regularized adaptive model.

- Result: commit `b82421b`, Eval AUC **0.7682**, keep. Run time: 40.6s (training 25.4s, eval 15.2s, ok)
- Decision: AUC improved by 0.0005 with a small, interpretable calendar feature and modest evaluation overhead. Test whether the candidate-feature count explains the gain.

## Experiment 48 — control for candidate-feature count

- Classification: ablation/simplification of experiment 47.
- Hypothesis: adding WeekBlock increased the number of split candidates at colsample_bynode=0.8 (ten features instead of nine); part of its gain may reflect sampling rather than calendar information.
- Change: remove WeekBlock and its constants, set colsample_bynode=0.9 so the nine-feature model considers approximately the same number of candidates. A tie would favor this simpler version.

- Result: commit `ab12ee0`, Eval AUC **0.7675**, discard. Run time: 39.4s (training 24.9s, eval 14.5s, ok)
- Decision: AUC fell by 0.0007; the week feature's gain is not recovered by simply increasing candidate-feature count. Week feature row-invariance check passed.

## Experiment 49 — categorical flexibility under strong penalties

- Classification: follow-up to the successful adaptive, strongly regularized model.
- Hypothesis: max_cat_threshold=64 may now support useful broader date/week/airport groups without the overfitting seen under the much weaker early model.
- Change: max_cat_threshold 16 → 64, restoring WeekBlock and colsample_bynode=0.8.
- Distinction from early categorical tests: the current model has L1=5, L2=100, adaptive growth, tree averaging, and a weekly feature; the trade-off between partition size and shrinkage may have shifted.

- Result: commit `71cf02a`, Eval AUC **0.7670**, discard. Run time: 39.3s (training 24.3s, eval 15.0s, ok)
- Decision: AUC fell by 0.0012; even with strong leaf penalties, tighter categorical groups remain useful.

## Experiment 50 — smaller adaptive trees

- Classification: ablation/simplification of the best model.
- Hypothesis: 32 leaves may retain the useful adaptive paths while reducing tree size, noise, and fitting cost; three-tree averaging and stronger penalties have changed the capacity trade-off since early depth tests.
- Change: max_leaves 64 → 32, restore max_cat_threshold=16. A near-equal score with substantially smaller trees would be a simplification win.

- Result: commit `b576710`, Eval AUC **0.7628**, discard. Run time: 30.5s (training 16.3s, eval 14.2s, ok)
- Decision: AUC fell by 0.0054; halving tree size loses too much useful interaction capacity.

## Synthesis after 50 experiments

- Best retained: `b82421b`, Eval AUC 0.7682 (+0.0479 versus baseline).
- WeekBlock provided a small gain. A control with fewer features and a higher sampling fraction did not recover it, supporting an intermediate calendar timescale. Its preparation is exactly invariant between batch and single-row calls.
- Independent soft voting, label smoothing, airport geometry/regions, route medians, and learning-rate decay did not justify replacing the compact built-in model.
- Reg_lambda=300 and reg_alpha=20 were excessive. Broad categorical partitions and 32-leaf trees also hurt. The model benefits from flexible selective paths paired with soft weight penalties.
- Next priorities: remove any now-redundant hard constraints, compare numeric split algorithms, and test complementary simple temporal encodings.

### Research refresh

- [Tree-method comparison](https://xgboost.readthedocs.io/en/stable/treemethod.html): approx refreshes Hessian-weighted quantile sketches during fitting, while hist uses a fixed sketch; this suggests a distinct later experiment under the runtime cap.
- Revisited the [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) to distinguish minimum child Hessian (a hard constraint) from L1/L2 leaf penalties.

## Experiment 51 — ablate explicit minimum child weight

- Classification: ablation/simplification.
- Hypothesis: the strong L1/L2 penalties may now suppress noisy small leaves sufficiently, making min_child_weight=20 redundant or unnecessarily restrictive.
- Change: remove min_child_weight, returning to default 1. Retain the 64-leaf architecture and all other winning settings.

- Result: commit `0471adc`, Eval AUC **0.7677**, discard. Run time: 39.3s (training 24.5s, eval 14.8s, ok)
- Decision: AUC fell by 0.0005. The explicit minimum child weight still contributes useful regularization.

## Experiment 52 — Hessian-adaptive numeric split search

- Classification: exploration of a different tree-building method.
- Hypothesis: approx's refreshed Hessian-weighted quantile sketches may locate more useful numeric thresholds than the fixed hist sketch.
- Change: tree_method=approx, all other retained settings unchanged. This is a direct algorithm comparison; the harness will enforce the 60-second training limit.
- Source: XGBoost tree-method comparison reviewed in the latest synthesis.

- Result: commit `7702866`, Eval AUC **0.0000**, crash. Run time: 60.0s (training 60.0s, eval 0.0s, timeout-training)
- Decision: Hessian-adaptive split search exceeded the 60-second training limit; no evaluation score was produced.

## Experiment 53 — approximate split search within the runtime budget

- Classification: follow-up to experiment 52's runtime failure.
- Hypothesis: a smaller approx model may retain useful adaptive numeric thresholds while satisfying the training cap.
- Change: tree_method=approx, 300 rounds at eta=0.1, one tree per round. Preserve feature and leaf-regularization settings. The total nominal shrinkage remains about 30.
- This is the bounded feasibility test for approx; if uncompetitive, return to hist.

- Result: commit `3470a0e`, Eval AUC **0.7664**, discard. Run time: 25.6s (training 12.0s, eval 13.5s, ok)
- Decision: AUC 0.7664 is below the retained 0.7682. Approximate Hessian-weighted split search adds cost at full capacity and does not improve this smaller comparison; return to histogram trees.

## Experiment 54 — Intermediate L1 regularization

- Classification: hyperparameter refinement with a specific bracket from previous outcomes.
- Review: L1=5 improved the adaptive-tree model substantially; L1=20 hurt (0.7560). The current weekly feature and randomized 3-tree rounds were added since that strong-penalty comparison.
- Hypothesis: L1=10 may suppress marginal leaf updates without the underfitting observed at 20. Change only `reg_alpha`, from 5 to 10; retain the current best hist model otherwise.

- Result: commit `3075326`, Eval AUC **0.7654**, discard. Run time: 38.6s (training 23.7s, eval 14.9s, ok)
- Decision: Intermediate L1 also underfits relative to the retained penalty: 0.7654 versus 0.7682. Keep reg_alpha=5; stronger L1 is not promising.

## Experiment 55 — Cyclic departure time

- Classification: exploration of a different representation of scheduled time.
- Research: [scikit-learn time-related feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) describes sine/cosine transforms to remove a periodic boundary. Trees can already fit nonlinear time effects, so this is a hypothesis about more efficient split geometry, not a guaranteed advantage. Reviewed XGBoost class-weight guidance too; balanced training labels provide no imbalance-based reason to change class weights.
- Prior context: numeric hour/minute decomposition (experiment 20) failed; cyclic functions differ because a single threshold can pool times that straddle midnight or a daily peak.
- Hypothesis: append sin/cos of scheduled minutes/1440, retaining raw HHMM. This may share signal across the day boundary without a deeper interaction. Fixed transforms are row-wise; no fitted statistics or count features.

- Result: commit `7a9594c`, Eval AUC **0.7676**, discard. Run time: 42.3s (training 27.0s, eval 15.3s, ok)
- Decision: Cyclic transforms scored 0.7676 versus 0.7682, adding features and per-row work without benefit. Batch and singleton features matched exactly on 25 training rows.

## Experiment 56 — Airport-by-month categories

- Classification: exploration of spatial-seasonal categorical interactions.
- Research: [Airport time profile construction driven by flight delay prediction](https://pmc.ncbi.nlm.nih.gov/articles/PMC11319447/) studies airport schedules with weather and seasonal scheduling. It motivates location/time context broadly; the specific month-cross idea below is our inference, not a method established by that paper. We have no weather inputs and will not add external data. [XGBoost categorical documentation](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) provides the partition-based categorical split mechanism already used here.
- Hypothesis: explicit Origin-Month and Dest-Month categories let a split pool airport-season combinations across different airports, which otherwise requires several tree levels. This differs from the failed route/carrier crosses and from train-target date-rate lookups: these are coarse unlabeled season/location crosses with much lower cardinality than airport-date.
- Dtypes are fitted on training predictors; preparation only concatenates each row's airport and month, with unseen pairs handled as missing. No counts or target statistics.

- Result: commit `4dbc523`, Eval AUC **0.7653**, discard. Run time: 69.2s (training 50.8s, eval 18.4s, ok)
- Decision: AUC fell to 0.7653 and training rose to 50.8s including startup. Features are row-invariant but not worthwhile; discard the coarse spatial-seasonal cross direction.

## Experiment 57 — Smaller boosting steps at matched nominal total

- Classification: follow-up to regularized randomized trees.
- Research: [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/release_3.3.0/tutorials/param_tuning.html) treats learning rate and boosting length together. Reducing step size can change the optimization trajectory while preserving useful capacity with more rounds.
- Hypothesis: 1200 rounds at learning_rate=0.025 may improve ranking relative to 600 at 0.05; both have nominal total shrinkage 30. Experiment 29 merely doubled rounds at unchanged eta and plateaued, so this tests discretization rather than adding unchecked boosting length. Current 3-tree rounds and weekly feature remain in place.
- Runtime estimate: roughly 48s training based on the best model's 24.5s, leaving limited but plausible room under 60s. Timeout counts as failure.

- Result: commit `8c51f25`, Eval AUC **0.7680**, discard. Run time: 65.9s (training 48.9s, eval 16.9s, ok)
- Decision: AUC 0.7680 is essentially flat but slightly lower while training doubles to 48.9s and the ensemble doubles in size. Retain the smaller 600-round model.

## Experiment 58 — Remove raw month and day-of-month columns

- Classification: ablation/simplification of the date/week feature result.
- Review: removing all three raw calendar columns earlier cost 0.0008 AUC (experiment 26), before WeekBlock existed. The retained model's training split-gain diagnostic assigns about 32% to Date and 14% to WeekBlock, versus 4.1% to DayofMonth and 0.7% to Month. These are descriptive fitted-model diagnostics, not a new validation metric and not proof of irrelevance.
- Hypothesis: Date supplies exact day identity and WeekBlock now supplies coarse seasonal pooling, allowing Month and DayofMonth to be removed as model inputs. Keep DayOfWeek for cross-date weekly pooling. The row values remain available inside prepare to derive Date/WeekBlock. This tests whether the newer weekly representation makes the earlier broad calendar ablation viable in a narrower form.
- Prefer the reduced feature set if AUC is equal to reported precision or improves; otherwise retain the full model.

- Result: commit `3cc2c3c`, Eval AUC **0.7683**, keep. Run time: 37.1s (training 24.0s, eval 13.1s, ok)
- Decision: AUC rises from 0.7682 to 0.7683 with two fewer model inputs; evaluation drops to 13.1s. A clear simplification win even though the score change is small.

## Experiment 59 — One tree per boosting round

- Classification: ablation/simplification of the native three-tree ensemble after calendar feature reduction.
- Prior context: three parallel trees gained 0.0003 before the later histogram and week changes (experiment 37). Removing redundant calendar columns just changed the split candidate set from 10 features to 8 and may reduce the need to average random subsets.
- Hypothesis: one tree per round may preserve AUC while cutting the model to one-third of its trees and reducing training time substantially. Remove only `num_parallel_tree=3`; keep 600 rounds and eta=0.05.
- AUC equal to reported precision is an automatic simplification keep; a decrease up to 0.0001 may be acceptable only if the expected large runtime/size reduction occurs. Larger decreases retain three trees.

- Result: commit `8eaa05f`, Eval AUC **0.7675**, discard. Run time: 19.7s (training 7.8s, eval 11.9s, ok)
- Decision: Training falls from 24.0s to 7.8s, but AUC falls by 0.0008 to 0.7675, exceeding the stated simplicity tolerance. Three-tree averaging still contributes on the reduced feature set.

## Experiment 60 — Remove the remaining raw calendar category

- Classification: follow-up ablation/simplification to experiment 58.
- Review: removing Month and DayofMonth improved AUC and speed; DayOfWeek is the only remaining original calendar column. The current fixed year means Date already identifies the weekday, though DayOfWeek can provide a useful pooling bias across dates.
- Hypothesis: remove DayOfWeek to test whether Date and WeekBlock alone provide adequate calendar pooling. This directly extends the successful narrower removal rather than changing unrelated tree parameters. Keep all three trees per round after experiment 59 showed a measurable benefit.

- Result: commit `f8c9bde`, Eval AUC **0.7683**, keep. Run time: 36.2s (training 24.4s, eval 11.8s, ok)
- Decision: AUC remains 0.7683 with one fewer feature and evaluation improves to 11.8s. Retain the simpler model.

## Synthesis after 60 experiments

- Current best retained: `f8c9bde`, Eval AUC **0.7683**, versus baseline 0.7203. Date and WeekBlock now replace all three raw calendar columns; the model has seven inputs.
- Experiments 51–60: min_child_weight=1 lost a little, approx split search timed out at full size and lost at smaller size, L1=10 underfit, cyclic clock features and airport-month crosses lost, half learning rate with twice the rounds was flat but slower. Three-tree rounds still improve AUC enough to retain. The two calendar ablations kept the score while reducing feature count/eval time.
- Current theory: the date and week grouping, regularized adaptive trees, and randomized averaging carry the signal. Most added representations duplicate what the trees can learn; removing redundant calendar inputs is more productive. Training diagnostics are descriptive only; harness Eval AUC remains the sole selection metric.
- Research refresh: reviewed [GradientBoostingClassifier loss options](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.GradientBoostingClassifier.html), [Friedman/Hastie/Tibshirani's boosting report](https://statistics.stanford.edu/technical-reports/additive-logistic-regression-statistical-view-boosting), and [Wyner's examination of exponential loss](https://proceedings.mlr.press/r4/wyner03a.html). Exponential loss is a classic alternative with different emphasis on margins; Wyner cautions against equating minimizing that criterion with explaining generalization. No claim that it guarantees better AUC. Next test a small convex custom-loss implementation, then alternative randomization granularity and structural simplification if it fails.
- Clarification: experiment 54's 'hyperparameter refinement' classification was a follow-up to the earlier L1 bracket.

## Experiment 61 — Exponential margin loss

- Classification: exploration of a meaningfully different training objective.
- Hypothesis: exponential loss may rank difficult positive/negative pairs differently from logistic loss, which can matter to AUC even with unchanged features. This differs from label smoothing (46), which compressed targets but retained the logistic curvature, and pairwise ranking (31), which sampled pairs.
- Implementation: use L=exp(-(2*y-1)*margin/2), gradient=-0.5*(2*y-1)*L, Hessian=0.25*L. At zero margin the derivatives match logistic loss, preserving the starting regularization scale. Its population optimum is the log odds, so the standard logistic prediction link remains appropriate. Set base_score=0.5 explicitly; no feature changes or alternate scoring metric.
- Validate the analytic derivatives with finite differences before the harness run. A marginal improvement would need to justify the added custom objective.

- Result: commit `b80ecce`, Eval AUC **0.7676**, discard. Run time: 36.9s (training 25.3s, eval 11.6s, ok)
- Decision: Finite-difference derivatives passed, training/evaluation succeeded, but AUC 0.7676 is below 0.7683 and adds custom code. Keep native logistic loss.

## Experiment 62 — Tree-level feature randomization

- Classification: exploration of a distinct ensemble randomization scheme.
- Research: [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) distinguishes column sampling per tree, per depth level, and per node. These are structural choices, not interchangeable aliases.
- Hypothesis: setting colsample_bytree=0.8 instead of colsample_bynode=0.8 holds each tree's feature subset fixed, creating more distinct component trees. The fraction and native three-tree rounds stay unchanged. This could reduce correlation more than refreshing subsets at each node; it could also underfit when a key calendar feature is absent for a whole tree, which this run will test.

- Result: commit `6e0aed7`, Eval AUC **0.7684**, keep. Run time: 34.1s (training 22.4s, eval 11.8s, ok)
- Decision: AUC improves to 0.7684 with unchanged code complexity and training drops from 24.4s to 22.4s. Keep tree-level feature subsets.

## Experiment 63 — Gradient-based row sampling on CPU

- Classification: exploration of adaptive sampling, distinct from earlier uniform row removal.
- Research: the [stable XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) states that CPU gradient-based sampling has been supported since 3.2.0. Our installed 3.4.1 is eligible. Selection depends on gradient/Hessian magnitude and is supported by hist; this differs from uniformly dropping rows. Older advice restricting it to GPUs is not applicable here.
- Hypothesis: subsample=0.5 with sampling_method='gradient_based' may retain informative gradients while reducing redundant easy-row contributions and diversifying the native tree ensemble. Earlier uniform subsample=0.8 hurt a much less regularized architecture (experiment 12); this is a distinct sampling rule and later model. Keep new tree-level column sampling and all other settings.

- Result: commit `968af2b`, Eval AUC **0.7662**, discard. Run time: 42.2s (training 30.3s, eval 11.9s, ok)
- Decision: Supported and completed, but AUC fell to 0.7662 and training rose to 30.3s. Importance-weighted row selection did not help this configuration; retain all training rows.

## Experiment 64 — Prefer calendar features in random subsets

- Classification: follow-up to successful tree-level feature randomization (62).
- Research: [XGBoost's feature_weights parameter](https://xgboost.readthedocs.io/en/stable/python/python_api.html?highlight=XGBRegressor) assigns positive column-sampling weights; the installed interface accepts it in the estimator constructor. It changes inclusion probabilities, not feature values or prediction scaling. Also reviewed [Minimal Variance Sampling](https://arxiv.org/abs/1910.13204) for context on experiment 63; its general motivation did not translate to a gain here.
- Hypothesis: Date and WeekBlock are key pooling features, and dropping both from a whole tree may be too restrictive. Give each weight 2 versus 1 for other features, maintaining colsample_bytree=0.8 and the same feature count per tree. The mapping uses feature names to remain correct if feature order changes. This is a specific bias toward calendar coverage, not random seed selection.

- Result: commit `73180cc`, Eval AUC **0.7679**, discard. Run time: 35.3s (training 23.5s, eval 11.9s, ok)
- Decision: AUC 0.7679 is below 0.7684 and adds a special-case weight mapping. Uniform feature probabilities remain preferable.

## Experiment 65 — Cap long adaptive-tree paths

- Classification: ablation/simplification of unrestricted tree depth.
- Research: [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) distinguishes maximum depth from maximum leaves; the former limits interaction paths even with lossguide growth.
- Diagnostic: retained `6e0aed7` has per-tree maximum depth min=9, median=18, 90th percentile=24, max=29, from its saved tree structures only. No extra evaluation was performed.
- Hypothesis: cap max_depth at 16 while retaining 64 leaves. This removes the longest conditional paths that may isolate noisy category combinations, while allowing much deeper trees than the early depth-4/8 runs. It is a structural constraint on the later adaptive trees, not a repeat of depthwise growth comparisons.

- Result: commit `a43b44b`, Eval AUC **0.7684**, keep. Run time: 33.4s (training 21.8s, eval 11.6s, ok)
- Decision: AUC remains 0.7684 while restricting long conditional paths; training is 21.8s and evaluation 11.6s. Keep the shallower model as a structural simplification.

## Experiment 66 — Increase native averaging under tree-level sampling

- Classification: follow-up to successful tree-level randomization (62) and the benefit of three trees versus one (59).
- Research: [XGBoost random forests tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) explains num_parallel_tree within boosted forests. Each iteration averages multiple component trees.
- Hypothesis: six trees per boosting round may reduce variation from the fixed per-tree feature subsets more effectively than three. This is materially different from the earlier independent-seed ensemble (43), and is motivated by the later shift from per-node to per-tree randomization. Boosting rounds, eta, and feature fraction remain fixed.
- Runtime estimate: about 42s training from the retained depth-16 model's 21.8s. The model doubles in tree count; retain only if AUC improves, not for an equal score.

- Result: commit `45036eb`, Eval AUC **0.7683**, discard. Run time: 56.8s (training 43.4s, eval 13.4s, ok)
- Decision: AUC is slightly lower at 0.7683 and training doubles to 43.4s. Three trees remain sufficient; extra averaging does not justify the larger model.

## Experiment 67 — Share a compact calendar calculation

- Classification: ablation/simplification of feature preparation.
- Hypothesis: compute the known non-leap year's day number once, use it as an unordered categorical Date, and derive WeekBlock from the same values. This removes the fitted string-date category list and separate string concatenation. It is not the failed numeric DayOfYear feature (11): Date remains categorical, representing the same 365 day identities.
- Source for numeric category labels: [pandas.Categorical](https://pandas.pydata.org/docs/reference/api/pandas.Categorical.html); categorical labels need not be strings. No extra data is needed; the existing weekly encoding already assumes this non-leap year.
- The category code order changes, which can change tie resolution during training, so score it through the harness rather than assuming identical predictions. Check that WeekBlock stays identical and that new Date is a one-to-one recoding of old Date, plus singleton invariance. Keep if AUC is equal or better with simpler preparation.

- Result: commit `6626ada`, Eval AUC **0.7681**, discard. Run time: 34.3s (training 23.1s, eval 11.1s, ok)
- Decision: Calendar recoding passed a bijection check on all 365 training dates, non-Date features stayed identical, and singleton invariance passed. AUC decreased to 0.7681, so retain the existing date encoding despite the modest preparation saving.

## Experiment 68 — Categorical departure-time blocks

- Classification: exploration of coarse categorical time pooling.
- Research: [scikit-learn time-feature examples](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) distinguish numeric, one-hot and periodic representations. Combined with [XGBoost category partitions](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html), this suggests testing groups of time blocks rather than only ordered thresholds. The extension to a native categorical split here is our inference.
- Hypothesis: add a fixed 3-hour departure block (HHMM // 300, categories 0..7), keeping raw departure time. Native partitions may pool disjoint parts of the day with similar delay behavior without several numeric thresholds. This differs from numeric hour/minute decomposition and continuous sin/cos transforms, both of which failed earlier.
- Fixed bins and dtype are independent of batch composition, and there are no aggregate/count features.

- Result: commit `20051b2`, Eval AUC **0.7684**, discard. Run time: 35.6s (training 23.1s, eval 12.5s, ok)
- Decision: AUC is unchanged at 0.7684, with extra features/code and slower evaluation. Singleton invariance passed; discard the representation because it does not improve the retained simpler model.

## Plateau research refresh after experiment 68

- Three near-flat discards (66–68) prompted a research pause. Reviewed [scikit-learn's gradient boosting regularization example](https://scikit-learn.org/stable/auto_examples/ensemble/plot_gradient_boosting_regularization.html), which illustrates interactions between shrinkage and ensemble size/sampling. The practical next question is whether this strongly regularized model can reach the same result in fewer boosting steps.
- A domain search found [NASA's 2019 flight-delay propagation slides](https://ntrs.nasa.gov/api/citations/20190028340/downloads/20190028340.pdf). The search excerpt describes propagation from inbound to outbound flights during turnaround. Direct page/PDF retrieval failed, so this source was not read in full and no further claims about its contents are used. We lack aircraft identities/rotation history, so will not invent propagation inputs from the sampled row counts.

## Experiment 69 — Compress the boosting trajectory

- Classification: ablation/simplification of the current 600-round ensemble.
- Hypothesis: 300 rounds at eta=0.1 may match 600 at eta=0.05 with half the stored trees and substantially faster training. Strong regularization, calendar simplification, and tree-level averaging distinguish this model from the early learning-rate comparison (11). The approx 300-round run (53) changed the tree method and cannot answer this question for hist.
- Keep all other hyperparameters, including three trees per round and max_depth=16. Experiment 57's smaller steps did not help, so this explores the opposite, computationally cheaper direction at the same nominal total shrinkage.

- Result: commit `8aba144`, Eval AUC **0.7679**, discard. Run time: 22.2s (training 11.4s, eval 10.8s, ok)
- Decision: Training roughly halves, but AUC falls by 0.0005 to 0.7679. Preserve the more accurate 600-round trajectory.

## Experiment 70 — Further shorten conditional paths

- Classification: follow-up ablation/simplification to the successful depth cap (65).
- Hypothesis: max_depth=12 may preserve accuracy while eliminating still more long category-conditioned paths. Depth 16 already matched the unrestricted score, so this is a deliberate continuation of an effective structural simplification. Leave 64-leaf budget, three-tree rounds, and 600 boosting stages unchanged.
- This is the final planned depth compression comparison; if it loses meaningful AUC, retain 16 rather than searching individual depth values.

- Result: commit `2216704`, Eval AUC **0.7681**, discard. Run time: 32.4s (training 20.8s, eval 11.7s, ok)
- Decision: AUC falls to 0.7681, so depth 16 is the retained compression boundary. No per-integer depth search is justified.

## Synthesis after 70 experiments

- Retained best: `a43b44b`, Eval AUC **0.7684** (+0.0481 over baseline), 21.8s training including startup and 11.6s evaluation.
- Experiments 61–70: native logistic loss beat exponential loss; tree-level feature sampling slightly improved the score; gradient-based row sampling and manually weighted calendar sampling hurt. A depth cap of 16 preserved score, but 12 lost a little. Six trees per round, numeric recoding of Date, extra departure blocks, and halving the boosting stages did not justify replacement.
- Current theory: category pooling and regularized adaptive trees are stable; variety across trees helps more than more elaborate predictors. Seven inputs remain sufficient. Small AUC differences here are selection observations on the harness evaluation, not claims about unseen performance.
- Research refresh: [XGBoost's update/prune example](https://xgboost.readthedocs.io/en/stable/python/examples/update_process.html) demonstrates modifying existing trees; docs explicitly characterize this as less established. Unlike growing with gamma, pruning afterward preserves the original growth trajectory before deleting weak branches. This is a new compression mechanism worth one controlled trial. Other remaining directions are mixed categorical split types and continuous histogram resolution.

## Experiment 71 — Prune weak branches after fitting

- Classification: exploration of post-training structural simplification.
- Hypothesis: fit the current model normally, then prune existing branches with gamma=1 using process_type='update', updater='prune'. Saved-tree diagnostics show only 3.38% of split gains below 1, so this is a mild targeted removal, not the earlier gamma=2 growth restriction (22).
- The second fit updates the in-memory model on exactly the same training rows, adds no new data or trees, and performs no separate scoring. Both passes occur inside the harness training budget. Same features and final harness evaluation apply.
- Compare stored tree counts/leaves after scoring to confirm pruning actually occurred. Retain only for improved AUC or a material model simplification at equal AUC that warrants the extra update pass.

- Result: commit `e380802`, Eval AUC **0.0000**, crash. Run time: 23.2s (training 23.2s, eval 0.0s, crash)
- Decision: XGBoost reported no trees left for updating (0 vs 0). Setting update parameters on the already fitted estimator mutated the source booster before transfer. Retry using a fresh estimator and the untouched fitted booster.

## Experiment 72 — Correct the pruning handoff

- Classification: follow-up implementation repair to experiment 71.
- Hypothesis is unchanged. Construct an unfitted XGBClassifier with the original parameters plus the pruning configuration, then pass the original fitted booster to its fit call. Do not set update mode on the source model before copying it.
- This matches the separate output-booster pattern in the [official update/prune demo](https://xgboost.readthedocs.io/en/stable/python/examples/update_process.html). All work still uses the same train.csv rows and stays within one harness run.

- Result: commit `20a3b8c`, Eval AUC **0.0000**, crash. Run time: 22.2s (training 22.2s, eval 0.0s, crash)
- Decision: The source-booster handoff is fixed, but the sklearn wrapper selected QuantileDMatrix, which the prune updater does not implement. One final repair will use the native DMatrix/train pattern from the official example and load the resulting booster in memory.

## Experiment 73 — Native DMatrix pruning path

- Classification: follow-up implementation repair; final attempt for this direction.
- Use xgb.train with an explicit ordinary DMatrix and the fitted booster as xgb_model. Transfer the resulting model back through the public load_model(bytearray) method. This avoids both mutation of the source estimator and the sklearn wrapper's automatic QuantileDMatrix choice.
- Source: [official update/prune demo](https://xgboost.readthedocs.io/en/stable/python/examples/update_process.html). The gamma=1 hypothesis and same-row/no-extra-scoring constraints are unchanged. All in-memory booster updates happen before the final save_and_evaluate call.

- Result: commit `21adecb`, Eval AUC **0.0000**, crash. Run time: 60.0s (training 60.0s, eval 0.0s, timeout-training)
- Decision: The corrected native update path exceeded 60 seconds. Three attempts covered two API issues and the runtime constraint; close the pruning direction and retain the simple single-pass model.

## Experiment 74 — Mixed categorical split strategies

- Classification: exploration of selective one-hot splitting for the low-cardinality carrier feature.
- Research: [XGBoost categorical parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) use max_cat_to_onehot as a cardinality threshold. Set it to 32: only UniqueCarrier (20 levels) qualifies among the five retained categorical inputs; WeekBlock, Date, Origin and Dest keep partition-based splits.
- Hypothesis: individual-carrier splits may regularize arbitrary carrier groupings while retaining the date/airport pooling that made native categorical handling strong. This specifically differs from the all-one-hot trials (14–15), which removed beneficial partitions for all high-cardinality columns.

- Result: commit `0300b31`, Eval AUC **0.7664**, discard. Run time: 33.9s (training 22.0s, eval 12.0s, ok)
- Decision: AUC falls to 0.7664. Even the low-cardinality carrier benefits from partition-based splits in this model.

## Experiment 75 — Near-exhaustive numeric histogram resolution

- Classification: follow-up to the small gain from increasing max_bin to 1024 (38).
- Research: [XGBoost tree methods](https://xgboost.readthedocs.io/en/stable/treemethod.html) explains the hist/approx tradeoff and notes that a higher bin count can improve hist split quality. Approx was already slower and worse here.
- Hypothesis: max_bin=4096 approaches the full observed numeric resolution of HHMM departure time and flight distance. It may recover useful thresholds lost at 1024 while preserving all categorical partitions and the retained ensemble. This is a bounded resolution comparison, not a seed or category-order change.
- Keep only if AUC improves enough to warrant any runtime increase; no further bin sweep is planned.

- Result: commit `221e410`, Eval AUC **0.7684**, discard. Run time: 34.8s (training 23.1s, eval 11.7s, ok)
- Decision: AUC stays 0.7684 while training rises slightly. The 1024-bin setting is sufficient and cheaper; retain it.

## Experiment 76 — Remove distance

- Classification: ablation/simplification of a weak, partly redundant predictor.
- Hypothesis: Origin/Dest already identify the route and therefore much of its distance information. Earlier fitted-model diagnostics assigned Distance under 1% of total split gain, though that alone does not prove it is unnecessary. Remove only Distance from num_cols and score the resulting six-feature model.
- This is a direct feature ablation, not a transformation or a train-derived geometry replacement. Keep if AUC matches or improves; otherwise retain Distance as a useful low-cost grouping feature.

- Result: commit `fb936e0`, Eval AUC **0.7681**, discard. Run time: 31.9s (training 20.5s, eval 11.4s, ok)
- Decision: AUC falls to 0.7681. Despite low aggregate split gain, distance supplies useful grouping information beyond airport identities, so retain it.

## Experiment 77 — Mild uniform row sampling with matched penalty scale

- Classification: exploration of stochastic regularization with controlled expected penalty strength.
- Research: [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) defines row sampling and L1/L2/Hessian constraints; [gradient boosting regularization examples](https://scikit-learn.org/stable/auto_examples/ensemble/plot_gradient_boosting_regularization.html) motivate interactions between shrinkage and sampling.
- Hypothesis: uniform subsample=0.9 may add useful variation with less information loss than the earlier 0.8 uniform or 0.5 gradient-based trials. Scale reg_lambda from 100 to 90, reg_alpha from 5 to 4.5, and min_child_weight from 20 to 18 to approximately match their strength relative to the expected 90% gradient/Hessian mass.
- For a fixed partition, expected sampled gradients and Hessians scale by 0.9; scaling penalties similarly preserves its expected leaf update. Finite samples and split choices still vary. This makes the test about stochasticity with approximately controlled regularization, not an arbitrary multi-parameter tweak.

- Result: commit `4a14c82`, Eval AUC **0.7679**, discard. Run time: 34.8s (training 22.9s, eval 12.0s, ok)
- Decision: AUC is 0.7679 despite controlling expected penalty strength. Full-row training remains preferable; this closes the mild stochastic-row-sampling comparison.

## Experiment 78 — Require more support per leaf

- Classification: follow-up to the gain from min_child_weight=20 (6) and the loss when removing it (51).
- Plateau refresh: revisited the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) and [Python API](https://xgboost.readthedocs.io/en/stable/python/python_api.html?highlight=XGBRegressor) on minimum child Hessian. Unlike L1/L2, this prevents weakly supported partitions rather than shrinking their fitted values.
- Hypothesis: min_child_weight=50 may reduce noisy rare-category interactions while retaining the current leaf count/depth budget. This is the first comparison above 20, after ablation to 1 showed the constraint still helped. It is a single targeted support-strength test, not a broad parameter sweep.
- The clock has roughly one run left; score through the harness, then retain the best eligible model and verify its saved artifact without new evaluation metrics.

- Result: commit `4bbaadb`, Eval AUC **0.7682**, discard. Run time: 34.6s (training 23.0s, eval 11.6s, ok)
- Decision: AUC decreases to 0.7682, so retain the existing minimum-support setting and best commit a43b44b. This was launched before the deadline and completed after it; no new experiments will be started.

## Final summary — two-hour experiment complete

- Completed **78 experiments**: {'keep': 20, 'discard': 53, 'crash': 5}. Best retained Eval AUC **0.7684**, commit `a43b44b` on branch `oct2`, versus baseline **0.7203**; absolute gain **0.0481**.
- Final model: native categorical XGBoost, 600 rounds, three trees per round, lossguide with 64 leaves and depth cap 16, eta 0.05, minimum child Hessian 20, L2=100, L1=5, categorical threshold 16, 1024 numeric bins, and 80% feature sampling per tree. All training rows are used. Its scored run took 21.8s training including startup and 11.6s evaluation.
- Features: raw scheduled departure time, distance, carrier, origin and destination, plus categorical date and calendar week. Separate raw month/day/weekday inputs were removed without losing AUC. Cached category dtypes and single-frame construction make singleton preparation faster.
- What worked: sufficient boosting, date identity, calendar-week pooling, adaptive leaf growth, L1/L2 regularization, native category partitions, and randomized three-tree averaging. Later simplifications reduced calendar input redundancy and capped unnecessary depth.
- What did not justify retention: more elaborate route/airport/date target-rate or geographic features; cyclic/coarse clock transforms; alternative losses and ranking; dropout; early stopping on a reduced training split; heavier penalties; larger ensembles; finer numeric bins; row sampling; and aggressive model compression. Post-training pruning hit two interface issues, then exceeded the training limit on the corrected native path. All failures are logged.
- Final eight trials (71–78): pruning failed within the constraints; carrier-only one-hot splitting hurt; 4096 bins tied without benefit; removing distance hurt; mild row sampling with scaled penalties hurt; increasing child support to 50 hurt. The final run began with 20s left, completed under its per-run limits after the overall deadline, and was discarded. No experiment was started after the deadline.
- Validation: results.tsv contains one unique row for each of 78 commits; branch HEAD matches the final retained commit; only train.py differs from the starting commit; tracked working/staged trees are clean. The best artifact loads, produces valid two-column probabilities, and prepares 32 sampled training rows identically in batch and individually. This is a functional check only, not another selection metric.
- Scope note: the setup-time accidental read of the human-only preparation script was disclosed and documented earlier. It was not executed or used to guide these experiments. No eval/holdout/source/archived results were inspected; harness Eval AUC was the sole experiment selection metric.
- Next: under the same constraints, a deliberately heterogeneous shallow/deep ensemble at matched total runtime could be tested, or training-side smoothing that reduces variance without hand-written target-rate machinery. A separate future project with newly authorized aircraft/weather data could investigate real propagation signals. The current small late-stage score differences should not be treated as evidence of unseen-data gains without the human-controlled assessment.
- Results, research notes, and harness timing files remain uncommitted in place. The harness clock will be stopped as the final action.
