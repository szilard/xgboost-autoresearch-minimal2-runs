# Research log

## Baseline — commit 92e43e6

- **Class:** Baseline, unmodified starter run.
- **Hypothesis:** Establish a repeatable Eval AUC reference before tuning.
- **Setup:** XGBClassifier with 30 trees, depth 6, learning rate 0.1, native categorical handling, and the starter's six categorical plus two numeric features.
- **Result:** Eval AUC 0.7203; run completed successfully. Training took 0.2s and row-wise evaluation took 30.2s.
- **Observation:** Training is far below the 60s limit; evaluation dominates the per-run runtime.

## Research before experiment 1

- The [XGBoost parameter tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends lowering `eta` to make updates more conservative while increasing boosting rounds. Its [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes learning rate as step-size shrinkage and warns that deeper trees increase complexity and overfit risk.
- The flight-delay study [Shao et al. (2019)](https://arxiv.org/abs/1911.01605) reports that airport traffic and standard temporal information matter for departure-delay prediction. Its traffic and weather sources are unavailable among this experiment's permitted columns, so this motivates retaining the available time and airport fields while tuning the current model.

## Experiment 1 — commit 7fc5827

- **Class:** Follow-up to the baseline.
- **Hypothesis:** The baseline may be underfit at 30 trees; more rounds with a lower learning rate may improve ranking quality.
- **Change:** Increased `n_estimators` from 30 to 300 and decreased `learning_rate` from 0.1 to 0.05; all other settings unchanged.
- **Result:** Eval AUC 0.7348, up 0.0145 from baseline 0.7203. Run completed successfully (1.7s training, 30.6s evaluation).
- **Decision:** Keep. The gain is substantial and the code change is two parameter values.

## Experiment 2 — commit ca89138

- **Class:** Follow-up to experiment 1.
- **Hypothesis:** The large gain at 300 trees might leave additional signal for a longer boosting sequence; change only the round count to test that.
- **Change:** Increased `n_estimators` from 300 to 600, holding `learning_rate=0.05` and all other settings fixed.
- **Result:** Eval AUC 0.7359, up 0.0011 from the prior best 0.7348. Run completed successfully (3.3s training, 30.6s evaluation).
- **Decision:** Keep. The extra rounds improved AUC with a small training-time increase.

## Experiment 3 — commit 83878bc

- **Class:** Follow-up to experiment 2.
- **Hypothesis:** The improvement from 300 to 600 trees might continue at 1,200 rounds; change only the round count.
- **Change:** Increased `n_estimators` from 600 to 1,200, holding all other settings fixed.
- **Result:** Eval AUC 0.7324, down 0.0035 from the best 0.7359. Run completed successfully (6.6s training, 30.7s evaluation).
- **Decision:** Discard and reset to commit ca89138. The AUC decline suggests 600 rounds is a better point at this learning rate.

## Experiment 4 — commit e7badc9

- **Class:** Regularization follow-up to the best 600-tree model.
- **Hypothesis:** Reducing depth from 6 to 5 could limit overfitting while preserving the gains from a longer boosting sequence; XGBoost's parameter guide describes depth as a complexity control.
- **Change:** Set `max_depth=5`, holding 600 trees, learning rate 0.05, and the remaining settings fixed.
- **Result:** Eval AUC 0.7362, up 0.0003 from the prior best 0.7359. Run completed successfully (2.6s training, 30.7s evaluation).
- **Decision:** Keep. A small AUC gain came with shorter training time.

## Experiment 5 — commit 26fe527

- **Class:** Regularization follow-up to experiment 4.
- **Hypothesis:** A further reduction in depth from 5 to 4 might improve generalization; only the depth changes.
- **Change:** Set `max_depth=4`, keeping 600 trees and learning rate 0.05.
- **Result:** Eval AUC 0.7350, down 0.0012 from the best 0.7362. Run completed successfully (2.0s training, 30.6s evaluation).
- **Decision:** Discard and reset to commit e7badc9. Depth 5 performed better than both 4 and 6 so far.

## Experiment 6 — commit d239341

- **Class:** Regularization follow-up to the best model.
- **Hypothesis:** Requiring more Hessian weight in child nodes may remove noisy small splits; the XGBoost parameter reference says larger `min_child_weight` is more conservative.
- **Change:** Set `min_child_weight=5` (from the default 1), leaving the best model's 600 trees and depth 5 unchanged.
- **Result:** Eval AUC 0.7359, down 0.0003 from the best 0.7362. Run completed successfully (2.6s training, 30.4s evaluation).
- **Decision:** Discard and reset to commit e7badc9.

## Experiment 7 — commit 5d58e35

- **Class:** Stochastic-regularization exploration.
- **Hypothesis:** Sampling 80% of rows for each tree might reduce overfitting while retaining the best depth and round count.
- **Change:** Added `subsample=0.8`; all other settings matched the 600-tree, depth-5 best.
- **Result:** Eval AUC 0.7249, down 0.0113 from the best 0.7362. Run completed successfully (2.8s training, 30.5s evaluation).
- **Decision:** Discard and reset to commit e7badc9. This sampling level sharply hurt ranking quality.

## Research before experiment 8

- A study of major U.S. airline networks models delays for specific origin-destination pairs ([MIT thesis](https://dspace.mit.edu/entities/publication/ff614a7c-d91e-464d-adeb-c7d0246e3054)), motivating a directional route feature from the available airport codes.
- XGBoost's [categorical data guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) documents native category splits and category partitioning. The route category levels were fitted on `train` and looked up per row, following the repository's feature-preparation rules.

## Experiment 8 — commit 1f6d656

- **Class:** Feature-engineering exploration.
- **Hypothesis:** A directional origin-destination pair could expose route-specific delay patterns beyond separate origin and destination effects.
- **Change:** Added a train-level `route_levels` lookup and a per-row native categorical `Route` feature. No row counts or target-derived aggregates were added.
- **Result:** Eval AUC 0.7079, down 0.0283 from the best 0.7362. Run completed successfully; evaluation took 47.3s versus about 31s without the route feature.
- **Decision:** Discard and reset to commit e7badc9. The high-cardinality route category increased evaluation cost and sharply reduced AUC.

## Experiment 9 — commit b96e35a

- **Class:** Learning-rate/round-count follow-up.
- **Hypothesis:** The 1,200-tree run at 0.05 may have overshot; 1,000 smaller updates at 0.03, with roughly the same trees-times-rate product as the 600-tree best, may fit more smoothly.
- **Change:** Set `n_estimators=1000` and `learning_rate=0.03`, retaining depth 5 and the other settings of the current best.
- **Result:** Eval AUC 0.7366, up 0.0004 from the prior best 0.7362. Run completed successfully (4.2s training, 30.3s evaluation).
- **Decision:** Keep; this is the new best.

## Synthesis after 10 total runs

- **What helped:** Moving from the 30-tree baseline to 300 trees at a lower learning rate gave the largest gain. More rounds to 600 helped again. Depth 5 edged out depths 4 and 6, and the 1,000-tree, 0.03-rate schedule is now the best at Eval AUC 0.7366.
- **What did not:** 1,200 trees at 0.05 reduced AUC; `min_child_weight=5` did not improve the best; `subsample=0.8` and a high-cardinality route category substantially hurt AUC, with the route feature also increasing evaluation time.
- **Current theory:** This dataset benefits from a sufficiently long but not overly aggressive boosting sequence, with moderate tree depth. Stochastic row sampling and a fine-grained route category appear to add noise in the current setup.
- **Next direction:** Continue a small, deliberate search around learning-rate/round-count pairs near the new best, then investigate compact time-of-day features. Research the time feature specifically before changing `prepare()`.

## Experiment 10 — commit 08220e5

- **Class:** Learning-rate/round-count follow-up to experiment 9.
- **Hypothesis:** More, smaller updates at `1,200 × 0.025` might improve on `1,000 × 0.03` while keeping the rough trees-times-rate product constant.
- **Change:** Set `n_estimators=1200` and `learning_rate=0.025`, retaining depth 5.
- **Result:** Eval AUC 0.7366, tied with the prior best at displayed precision. Training took 5.1s versus 4.2s.
- **Decision:** Discard and reset to commit b96e35a. The extra rounds did not improve the metric or simplify the model.

## Experiment 11 — commit a3468a7

- **Class:** Follow-up regularization exploration.
- **Hypothesis:** Mild column sampling might diversify trees while preserving most of the existing signal; XGBoost documents `colsample_bytree` as per-tree column sampling.
- **Change:** Added `colsample_bytree=0.9` to the current best schedule.
- **Result:** Eval AUC 0.7368, up 0.0002 from 0.7366. Run completed successfully (4.3s training, 30.7s evaluation).
- **Decision:** Keep as the new best.

## Experiment 12 — commit d6e16db

- **Class:** Dose follow-up to experiment 11.
- **Hypothesis:** Reducing the per-tree feature fraction from 0.9 to 0.8 could add more diversity; the prior 0.9 result was a small improvement.
- **Change:** Set `colsample_bytree=0.8`, changing no other setting.
- **Result:** Eval AUC 0.7385, up 0.0017 from the previous best 0.7368. Run completed successfully (4.1s training, 30.7s evaluation).
- **Decision:** Keep as the new best.

## Experiment 13 — commit 07abb28

- **Class:** Dose follow-up to experiment 12.
- **Hypothesis:** A further decrease in per-tree feature sampling from 0.8 to 0.7 might continue the improvement; the parameter reference describes `colsample_bytree` as selecting a fraction of features for each tree.
- **Change:** Set `colsample_bytree=0.7`, changing no other setting.
- **Result:** Eval AUC 0.7394, up 0.0009 from the prior best 0.7385. Run completed successfully (4.2s training, 30.5s evaluation).
- **Decision:** Keep as the new best.

## Experiment 14 — commit 9d38cc2

- **Class:** Dose follow-up to experiment 13.
- **Hypothesis:** The AUC gains from 0.9 to 0.7 column sampling might continue at 0.6, while retaining enough features per tree.
- **Change:** Set `colsample_bytree=0.6`, changing no other setting.
- **Result:** Eval AUC 0.7399, up 0.0005 from the prior best 0.7394. Run completed successfully (4.2s training, 30.4s evaluation).
- **Decision:** Keep as the new best.

## Experiment 15 — commit 28370de

- **Class:** Dose follow-up to experiment 14.
- **Hypothesis:** A 0.5 feature fraction might continue the improvements seen at 0.8, 0.7, and 0.6.
- **Change:** Set `colsample_bytree=0.5`, changing no other setting.
- **Result:** Eval AUC 0.7399, tied with the 0.6 result at displayed precision. Runtime was also essentially unchanged (4.1s training, 30.8s evaluation).
- **Decision:** Discard and reset to commit 9d38cc2. This did not improve the metric or simplify the implementation.

## Experiment 16 — commit 382d50c

- **Class:** Follow-up to the best feature-sampled model.
- **Hypothesis:** With only 60% of features considered per tree, additional depth may help capture interactions among the features that are available.
- **Change:** Increased `max_depth` from 5 to 6, holding the 1,000-tree, 0.03-rate schedule and `colsample_bytree=0.6` fixed.
- **Result:** Eval AUC 0.7442, up 0.0043 from the prior best 0.7399. Run completed successfully (5.3s training, 30.9s evaluation).
- **Decision:** Keep as the new best. This is the largest gain since the initial increase in boosting rounds.

## Experiment 17 — commit 85c8758

- **Class:** Follow-up to experiment 16.
- **Hypothesis:** The gain at depth 6 suggests the depth-5 model missed useful interactions; depth 7 may capture more, though increased complexity could overfit.
- **Change:** Increased `max_depth` from 6 to 7, keeping the 1,000-tree, 0.03-rate schedule and `colsample_bytree=0.6` fixed.
- **Result:** Eval AUC 0.7467, up 0.0025 from the prior best 0.7442. Run completed successfully (6.6s training, 31.1s evaluation).
- **Decision:** Keep as the new best.

## Experiment 18 — commit 4b04aa5

- **Class:** Follow-up to experiment 17.
- **Hypothesis:** The improvement from depth 6 to 7 might continue at depth 8, with some risk of overfitting.
- **Change:** Increased `max_depth` from 7 to 8, retaining the 1,000-tree, 0.03-rate schedule and `colsample_bytree=0.6`.
- **Result:** Eval AUC 0.7478, up 0.0011 from the prior best 0.7467. Run completed successfully (8.4s training, 31.2s evaluation); artifact size was 62.7 MB.
- **Decision:** Keep as the new best. The model is larger, but the training and evaluation remain within the harness limits.

## Research before experiment 19

- The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) says `lossguide` grows nodes with the highest loss change, while `depthwise` expands nodes closest to the root; both are supported with `hist`/`approx`, and `max_leaves` can cap tree size.
- A flight-delay feature study extracts the hour from scheduled departure time in HHMM format and tests hour bins ([study](https://www.mdpi.com/2079-9292/13/24/4910)). This motivates a compact, row-local departure-hour feature as a later experiment.

## Experiment 19 — commit 3a90110

- **Class:** Exploration of a different tree-growth strategy.
- **Hypothesis:** The depth-8 model's gains may come from useful interactions. Loss-guided splitting could allocate a similar leaf budget to the most productive parts of each tree rather than expanding level by level.
- **Change:** Switched to `tree_method="hist"`, `grow_policy="lossguide"`, `max_depth=0`, and `max_leaves=255`; kept 1,000 trees, learning rate 0.03, and `colsample_bytree=0.6`.
- **Result:** Eval AUC 0.7507, up 0.0029 from the prior best 0.7478. Run completed successfully (16.9s training, 31.5s evaluation); artifact size was 69.3 MB.
- **Decision:** Keep as the new best.

## Synthesis after 20 total runs

- **What helped:** More boosting rounds at a lower learning rate improved on the 30-tree baseline. Feature subsampling from 0.9 down to 0.6 steadily improved AUC. With that sampling in place, deeper trees improved from depth 5 through depth 8. Switching to loss-guided growth with a 255-leaf cap raised AUC again to 0.7507.
- **What did not:** 1,200 trees at 0.05, depth 4, `min_child_weight=5`, and `subsample=0.8` did not help. The high-cardinality route category sharply hurt AUC and slowed row-wise evaluation. `colsample_bytree=0.5` tied 0.6 without a simplicity gain.
- **Current theory:** The model benefits from interactions among the available schedule, airport, carrier, and distance signals. Selecting fewer columns per tree appears helpful, and loss-guided growth uses those interactions more efficiently than deeper depthwise trees.
- **Next direction:** First explore the loss-guided leaf budget, then try a compact departure-hour category derived from `CRSDepTime`. It must be computed from each row with category levels fitted on `train` only.

## Experiment 20 — commit 7b94d63

- **Class:** Leaf-budget ablation of experiment 19.
- **Hypothesis:** Halving the loss-guided leaf cap from 255 to 127 might remove low-value splits and improve generalization, or retain the AUC with a smaller model.
- **Change:** Set `max_leaves=127`, keeping the loss-guided policy and all other settings fixed.
- **Result:** Eval AUC 0.7495, down 0.0012 from the 255-leaf best. Artifact size fell from 69.3 MB to 38.2 MB, and training time fell from 16.9s to 11.6s.
- **Decision:** Discard and reset to commit 3a90110. The smaller model did not retain the AUC.

## Synthesis after 20 tuning experiments (21 total harness runs)

- **Current best:** commit 3a90110, Eval AUC 0.7507 (up 0.0304 from the baseline).
- **What helped:** 1,000 trees at learning rate 0.03, `colsample_bytree=0.6`, and loss-guided growth with 255 leaves. The 255-leaf model outperformed the 127-leaf version by 0.0012 AUC.
- **Cost tradeoff:** The 127-leaf model was smaller (38.2 MB vs 69.3 MB) and trained faster (11.6s vs 16.9s), but the lost AUC is not a clear simplicity win for the intended AUC goal.
- **Current theory:** The model still benefits from additional useful splits when they are allocated by loss change. The 255-leaf cap may not be the ceiling.
- **Next direction:** Test a 511-leaf cap. After that, add a compact departure-hour category derived row by row from `CRSDepTime`, using levels fitted from `train`.

## Experiment 21 — commit 9ab9ae1

- **Class:** Leaf-budget follow-up to experiment 19.
- **Hypothesis:** A 511-leaf cap might capture additional useful splits beyond the 255-leaf best.
- **Change:** Set `max_leaves=511`, changing no other setting.
- **Result:** Eval AUC 0.7486, down 0.0021 from the best 0.7507. Training took 28.0s, evaluation 31.5s, and the artifact grew to 127.9 MB.
- **Decision:** Discard and reset to commit 3a90110. The larger model cost more time and storage without an AUC gain.

## Experiment 22 — commit a9b7ffb

- **Class:** Feature-engineering exploration based on flight-delay time-feature research.
- **Hypothesis:** A train-fitted categorical departure hour could expose broad hourly patterns alongside raw HHMM time.
- **Change:** Added `DepartureHour = CRSDepTime // 100` as a categorical feature, with levels fitted once from `train` and looked up per row.
- **Result:** Eval AUC 0.7505, down 0.0002 from the 0.7507 best. Run completed successfully (17.7s training, 37.8s evaluation); evaluation was 6.3s slower than without the feature.
- **Decision:** Discard and reset to commit 3a90110. The feature did not improve AUC and increased row-wise preparation cost.

## Experiment 23 — commit 33429f3

- **Class:** Histogram-resolution exploration.
- **Hypothesis:** More bins may offer better split candidates for scheduled time and distance; XGBoost notes that increasing `max_bin` can improve split optimality at added computation cost.
- **Change:** Set `max_bin=512` with the current loss-guided 255-leaf model; all other settings unchanged.
- **Result:** Eval AUC 0.7509, up 0.0002 from the prior best 0.7507. Run completed successfully (16.6s training, 31.0s evaluation); artifact size was 69.5 MB.
- **Decision:** Keep as the new best.

## Experiment 24 — commit 61978f8

- **Class:** Histogram-resolution follow-up to experiment 23.
- **Hypothesis:** Doubling `max_bin` from 512 to 1,024 may provide more useful numeric split candidates.
- **Change:** Set `max_bin=1024`, changing no other setting.
- **Result:** Eval AUC 0.7518, up 0.0009 from the prior best 0.7509. Run completed successfully (17.3s training, 31.1s evaluation); artifact size was 68.8 MB.
- **Decision:** Keep as the new best.

## Experiment 25 — commit ae445b4

- **Class:** Histogram-resolution follow-up to experiment 24.
- **Hypothesis:** Doubling the bin count to 2,048 might expose additional useful splits for the two numeric inputs.
- **Change:** Set `max_bin=2048`, changing no other setting.
- **Result:** Eval AUC 0.7506, down 0.0012 from the 1,024-bin best. Training took 19.0s and evaluation 30.9s; artifact size increased slightly to 69.8 MB.
- **Decision:** Discard and reset to commit 61978f8.

## Experiment 26 — commit d30b0d0

- **Class:** Categorical-regularization exploration.
- **Hypothesis:** Restricting the categories considered for each partition-based split might reduce overfitting in high-cardinality airport categories; XGBoost documents `max_cat_threshold` for this purpose.
- **Change:** Set `max_cat_threshold=32`, changing no other setting.
- **Result:** Eval AUC 0.7492, down 0.0026 from the 1,024-bin best. Run completed successfully (18.0s training, 31.4s evaluation); artifact size increased to 71.9 MB.
- **Decision:** Discard and reset to commit 61978f8.

## Experiment 27 — commit d12ac8a

- **Class:** Local histogram-resolution refinement.
- **Hypothesis:** A 1,536-bin setting between the 1,024-bin best and 2,048-bin decline might preserve finer splits without the larger resolution's loss.
- **Change:** Set `max_bin=1536`, changing no other setting.
- **Result:** Eval AUC 0.7506, down 0.0012 from the 1,024-bin best and tied with the 2,048-bin result at displayed precision. Training took 18.6s; evaluation took 31.3s.
- **Decision:** Discard and reset to commit 61978f8. The best resolution in this local sweep remains 1,024.

## Experiment 28 — commit 9e1f64f

- **Class:** Categorical split-strategy exploration.
- **Hypothesis:** One-hot splits for low-cardinality time categories might work better than partition splits; XGBoost uses `max_cat_to_onehot` to choose between them.
- **Change:** Set `max_cat_to_onehot=16`, so categories with fewer than 16 levels use one-hot splits.
- **Result:** Eval AUC 0.7495, down 0.0023 from the 1,024-bin best. Run completed successfully (17.7s training, 31.0s evaluation); artifact size was 67.9 MB.
- **Decision:** Discard and reset to commit 61978f8.

## Experiment 29 — commit 331e21c

- **Class:** L2-regularization follow-up.
- **Hypothesis:** Doubling `reg_lambda` from its default 1 to 2 might make leaf weights more conservative and improve generalization for the loss-guided model.
- **Change:** Set `reg_lambda=2.0`, changing no other setting.
- **Result:** Eval AUC 0.7504, down 0.0014 from the 1,024-bin best. Run completed successfully (19.0s training, 31.2s evaluation); artifact size was 68.9 MB.
- **Decision:** Discard and reset to commit 61978f8.

## Experiment 30 — commit ef9a0c1

- **Class:** Intermediate leaf-budget follow-up.
- **Hypothesis:** With the improved 1,024-bin histogram, 383 leaves might add useful capacity beyond the 255-leaf best while staying below the 511-leaf model.
- **Change:** Set `max_leaves=383`, changing no other setting.
- **Result:** Eval AUC 0.7500, down 0.0018 from the best 0.7518. Training took 24.9s, evaluation 31.3s, and the artifact grew to 99.3 MB.
- **Decision:** Discard and reset to commit 61978f8.

## Research before experiment 31

- The [XGBoost DART guide](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) describes tree dropout as a way to reduce overfitting. It uses the same tree parameters as `gbtree`, adds a `rate_drop`, and can train more slowly because dropout prevents use of the prediction buffer.
- The [parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) distinguishes per-level and per-node feature sampling. These remain possible follow-ups if DART does not help.

## Synthesis after 30 tuning experiments (31 total runs)

- **Current best:** commit 61978f8, Eval AUC 0.7518, up 0.0315 from the 0.7203 baseline.
- **What helped:** 1,000 trees at learning rate 0.03; `colsample_bytree=0.6`; loss-guided growth capped at 255 leaves; and `max_bin=1024`. The 512-to-1,024-bin increase added 0.0009 AUC.
- **What did not:** Larger leaf budgets (383/511), lower leaf budgets (127), more than 1,024 bins, the departure-hour category, categorical thresholds, one-hot threshold 16, and `reg_lambda=2` all failed to beat the best.
- **Current theory:** This task rewards enough flexible tree capacity, but extra leaves and feature engineering can overfit or add evaluation cost. Per-tree column sampling and a moderate leaf cap remain useful.
- **Next direction:** Compare DART tree dropout with the current loss-guided model; if it fails, try per-level or per-node column sampling, which has not yet been tested.

## Experiment 31 — commit 452ff74

- **Class:** DART architecture exploration.
- **Hypothesis:** Tree dropout might reduce overfitting in the 1,000-tree loss-guided model.
- **Change:** Set `booster="dart"` and `rate_drop=0.1`, retaining the current tree configuration.
- **Result:** Training timed out at the 60s harness limit; no Eval AUC was produced. XGBoost warned that `booster=dart` is deprecated and recommends the tree booster with dropout parameters.
- **Decision:** Record as a crash and revert to commit 61978f8. Retry once using the supported parameter form.

## Experiment 32 — commit 9d5ac9a

- **Class:** Supported-form retry of experiment 31.
- **Hypothesis:** The installed XGBoost warning recommended using the tree booster with dropout parameters rather than the deprecated `booster="dart"` flag.
- **Change:** Removed the explicit booster flag and kept `rate_drop=0.1` on the default tree booster.
- **Result:** Training again timed out at 60s; no Eval AUC was produced. The log contained only the harness training-timeout message.
- **Decision:** Record as a crash and reset to commit 61978f8. DART dropout is not viable within this experiment's training timeout on this machine.

## Experiment 33 — commit 6206d29

- **Class:** Follow-up feature-sampling exploration.
- **Hypothesis:** XGBoost samples columns cumulatively; adding 0.8 per-level sampling on top of the 0.6 per-tree setting might improve diversity across levels.
- **Change:** Added `colsample_bylevel=0.8`, changing no other setting.
- **Result:** Eval AUC 0.7512, down 0.0006 from the 1,024-bin best. Run completed successfully (17.6s training, 31.1s evaluation).
- **Decision:** Discard and reset to commit 61978f8. This added complexity without an AUC improvement.

## Experiment 34 — commit 4adb063

- **Class:** Follow-up feature-sampling exploration.
- **Hypothesis:** Per-node sampling might diversify individual splits without applying the per-level restriction that slightly hurt in experiment 33.
- **Change:** Added `colsample_bynode=0.8`, changing no other setting.
- **Result:** Eval AUC 0.7504, down 0.0014 from the best. Run completed successfully (19.0s training, 31.2s evaluation); artifact size was 69.0 MB.
- **Decision:** Discard and reset to commit 61978f8.

## Experiment 35 — commit c614935

- **Class:** Exploration — supervised categorical statistics.
- **Hypothesis:** Smoothed target rates for carrier, origin, and destination may provide compact numeric signals alongside XGBoost's native categorical splits, especially for airport categories with many levels.
- **Research:** Scikit-learn's TargetEncoder documentation recommends cross-fitting for training data because fitting then transforming the same rows can leak their labels ([TargetEncoder](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html)). The CatBoost paper discusses the same target-statistic leakage issue and motivates computing each training row's statistic from other training examples ([Prokhorenkova et al., NeurIPS 2018](https://papers.neurips.cc/paper/7898-catboost-unbiased-boosting-with-categorical-features.pdf)).
- **Change:** Added five-fold out-of-fold target-rate features for `UniqueCarrier`, `Origin`, and `Dest`, with smoothing strength 20 toward the fold's global target mean. Evaluation rows use mappings fitted on all of `train.csv`; unknown categories fall back to the training prior. Group counts were used only in the smoothing formula, not emitted as feature columns. The original categorical columns and best model settings were retained.
- **Result:** Eval AUC 0.7485 (down 0.0033 from the current best 0.7518). Training took 19.6s and evaluation 40.7s; the run completed within both harness timeouts.
- **Decision:** Discard and reset to 61978f8. This combined rate feature set reduced AUC and added evaluation work, so it does not advance the branch.

## Experiment 36 — commit c4f36fb

- **Class:** Cyclical schedule-feature exploration.
- **Hypothesis:** Circular sine/cosine coordinates for scheduled time, weekday, and month could make adjacent times or calendar values easier to relate while retaining the existing raw and categorical inputs. The scikit-learn [time-related feature guide](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) covers periodic encodings for hour, weekday, and month and notes that sine/cosine coordinates avoid the midnight discontinuity.
- **Change:** Added sine/cosine pairs with periods 1,440 minutes, 7 days, and 12 months.
- **Result:** Crash during `prepare` before training: `Month` values are categorical strings such as `c-11`, so direct numeric conversion failed; no Eval AUC was produced.
- **Decision:** The encoding idea remains viable. The training data's suffixes cover months 1–12 and weekdays 1–7, so parse those suffixes as numeric values and retry.

## Experiment 37 — commit 35c8583

- **Class:** Retry of the cyclical schedule-feature exploration after fixing the numeric conversion.
- **Change:** Parsed the trailing numeric levels from the training data's `c-N` values for month and weekday, then applied periods 12 and 7. Scheduled HHMM time was converted to minutes since midnight and wrapped to a 1,440-minute period. Each periodic value became a sine/cosine pair; original raw and categorical inputs remained.
- **Result:** Eval AUC 0.7533, improving the prior best 0.7518 by 0.0015. Training took 20.3s and evaluation 41.5s; the run completed within the harness timeouts.
- **Decision:** Keep commit 35c8583 as the new best. The cyclic coordinates improved ranking while adding only six row-local numeric features.

## Experiment 38 — commit 6cec1ca

- **Class:** Ablation of the new cyclical feature family.
- **Hypothesis:** The departure-time cycle might account for most of the gain, allowing the month and weekday pairs to be removed for a simpler model.
- **Change:** Kept `DepTimeSin` and `DepTimeCos`; removed the month and weekday sine/cosine pairs.
- **Result:** Eval AUC 0.7502, down 0.0031 from the full cyclical model at 0.7533. Training took 20.3s and evaluation 33.4s, about 8s faster.
- **Decision:** Discard and reset to 35c8583. The speed reduction does not offset the AUC loss; month and weekday cycles contribute to the combined gain.

## Experiment 39 — commit 02a0be8

- **Class:** Ablation of the new cyclical feature family.
- **Hypothesis:** Month and weekday cycles might retain most of the gain without the departure-time pair.
- **Change:** Kept the month and weekday sine/cosine pairs; removed `DepTimeSin` and `DepTimeCos`.
- **Result:** Eval AUC 0.7520, down 0.0013 from the full cyclical model and 0.0002 above the pre-cycle best. Training took 18.4s and evaluation 39.1s.
- **Decision:** Discard and reset to 35c8583. The smaller model is close, but the score loss is material enough to keep the full feature set.

## Experiment 40 — commit 94501ec

- **Class:** Follow-up to the successful departure-time cycle feature.
- **Hypothesis:** A second harmonic could represent two daily peaks more compactly than asking the trees to derive them from the first harmonic.
- **Change:** Added `sin(2θ)` and `cos(2θ)` for scheduled departure time, retaining all six first-harmonic calendar/time features.
- **Result:** Eval AUC 0.7533, tied with the current best. Training took 20.1s and evaluation 42.7s.
- **Decision:** Discard and reset to 35c8583. The added features did not improve AUC, so the simpler first-harmonic model remains best.

## Synthesis after 40 tuning experiments (41 total harness runs)

- **What helped:** Model tuning raised AUC from 0.7203 to 0.7518 using 1,000 trees at learning rate 0.03, loss-guided growth capped at 255 leaves, `colsample_bytree=0.6`, and `max_bin=1024`. Adding first-harmonic sine/cosine encodings for scheduled departure time, weekday, and month improved AUC again to 0.7533. Ablations suggest the three cycle groups work best together.
- **What did not:** Larger histogram bins, alternate categorical thresholds, extra feature-sampling restrictions, dropout, route/hour categories, smoothed category target rates, and a second departure-time harmonic did not beat the best. The target-rate features also slowed row-wise evaluation; the route category caused a larger slowdown.
- **Current theory:** The native categories and raw schedule fields already carry strong signal. Circular coordinates add a small amount of useful structure by representing proximity across time and calendar boundaries, while extra target statistics and isolated categories mostly add noise or redundant detail.
- **Next direction:** Revisit per-tree feature sampling with the expanded 14-feature input. The earlier `colsample_bytree=0.6` result predates six cyclic features; a higher fraction may make it more likely that trees see both members of each sine/cosine pair.

## Experiment 41 — commit 7b67122

- **Class:** Follow-up to the best model after adding six cyclical input columns.
- **Hypothesis:** Raising `colsample_bytree` from 0.6 to 0.8 could make each tree more likely to see both members of the sine/cosine pairs.
- **Change:** Changed only `colsample_bytree` to 0.8.
- **Result:** Eval AUC 0.7462, down 0.0071 from the best. Training took 22.9s and evaluation 41.7s; the run completed successfully.
- **Decision:** Discard and reset to 35c8583. The larger feature fraction substantially hurt ranking and increased artifact size.

## Experiment 42 — commit 9d68f4b

- **Class:** Follow-up to the per-tree sampling experiment.
- **Hypothesis:** The intermediate `colsample_bytree=0.7` setting might preserve the strong 0.6 result while exposing both members of cyclic feature pairs more often.
- **Change:** Changed only `colsample_bytree` to 0.7.
- **Result:** Eval AUC 0.7513, down 0.0020 from the best. Training took 20.5s and evaluation 40.9s.
- **Decision:** Discard and reset to 35c8583. Sampling at 0.6 remains better with the cyclic inputs; 0.7 and 0.8 both reduced AUC.

## Experiment 43 — commit 56af675

- **Class:** Regularization exploration based on the [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html), which defines `gamma` as the minimum loss reduction required for a split and notes that larger values make trees more conservative.
- **Hypothesis:** Requiring a gain of 1.0 might prune weak splits in the 255-leaf model and improve generalization.
- **Change:** Added `gamma=1.0`, retaining all other settings and features.
- **Result:** Eval AUC 0.7513, down 0.0020. Training fell to 8.6s and artifact size to 24.1 MB, indicating substantially smaller trees.
- **Decision:** Discard and reset to 35c8583. This threshold pruned too much useful structure.

## Experiment 44 — commit b38bf3e

- **Class:** Smaller-threshold follow-up to experiment 43.
- **Hypothesis:** A `gamma=0.1` penalty could prune less aggressively than 1.0 while removing only low-gain splits.
- **Change:** Added `gamma=0.1` and kept the remaining configuration unchanged.
- **Result:** Eval AUC 0.7533, tied with the best. Training took 19.1s and artifact size was 62.1 MB, close to the unregularized model.
- **Decision:** Discard and reset to 35c8583. It adds a parameter without an AUC or size benefit.

## Experiment 45 — commit 6fe2669

- **Class:** Follow-up to the loss-guided tree configuration.
- **Hypothesis:** A depth cap of 8 could constrain deep paths while preserving the 255-leaf budget.
- **Change:** Changed `max_depth` from 0 (unlimited) to 8, leaving `grow_policy="lossguide"` and `max_leaves=255` unchanged.
- **Result:** Eval AUC 0.7481, down 0.0052. Training took 14.4s; artifact size fell from 61.7 MB to 53.3 MB.
- **Decision:** Discard and reset to 35c8583. The cap removed useful capacity, so unlimited depth remains preferable.

## Experiment 46 — commit df88b3f

- **Class:** Depth-cap follow-up to experiment 45.
- **Hypothesis:** A cap of 16 could retain more useful paths than depth 8 while preventing the longest branches allowed by unlimited depth.
- **Change:** Set `max_depth=16`, retaining loss-guided growth and the 255-leaf cap.
- **Result:** Eval AUC 0.7535, a new best by 0.0002. Training took 19.4s and artifact size was 62.4 MB, similar to the unrestricted model.
- **Decision:** Keep commit df88b3f. The small AUC gain came with no material time or artifact-size increase.

## Experiment 47 — commit c4b82d2

- **Class:** Depth-cap follow-up to experiment 46.
- **Hypothesis:** Raising the cap from 16 to 24 could recover additional useful paths while still limiting extreme depths.
- **Change:** Set `max_depth=24`; kept the 255-leaf budget, loss-guided policy, and cyclic features.
- **Result:** Eval AUC 0.7538, a new best by 0.0003. Training took 19.8s and artifact size was 62.8 MB.
- **Decision:** Keep commit c4b82d2. The looser cap improved AUC without a material runtime change.

## Experiment 48 — commit 73d7c47

- **Class:** Depth-cap follow-up to experiment 47.
- **Hypothesis:** A cap of 32 could preserve deeper paths than 24 while still limiting the longest branches.
- **Change:** Set `max_depth=32`, retaining the 255-leaf cap.
- **Result:** Eval AUC 0.7533, down 0.0005 from depth 24. Training took 18.7s and artifact size was 62.1 MB.
- **Decision:** Discard and reset to c4b82d2. Depth 24 remains the best tested cap.

## Experiment 49 — commit 214ca16

- **Class:** Learning-rate/round-count follow-up to the current best.
- **Hypothesis:** A smaller step size paired with more rounds could improve ranking while preserving the same approximate total shrinkage.
- **Change:** Used 1,200 trees at learning rate 0.025 instead of 1,000 at 0.03; retained depth 24 and all other best settings.
- **Result:** Eval AUC 0.7530, down 0.0008 from the best. Training took 23.1s and evaluation 41.6s.
- **Decision:** Discard and reset to c4b82d2. The finer boosting schedule did not improve this model.

## Experiment 50 — commit f89749c

- **Class:** Regularization follow-up to the loss-guided depth-cap model.
- **Hypothesis:** `min_child_weight=2` could avoid the smallest, noisiest leaves while being less restrictive than the earlier tested value of 5.
- **Change:** Added `min_child_weight=2`, leaving depth 24 and other settings unchanged.
- **Result:** Eval AUC 0.7535, down 0.0003. Training took 19.1s and artifact size was 63.6 MB.
- **Decision:** Discard and reset to c4b82d2. The small loss and larger artifact do not justify the extra constraint.

## Synthesis after 50 tuning experiments (51 total harness runs)

- **Current best:** Eval AUC 0.7538 at commit c4b82d2, using 1,000 trees, learning rate 0.03, loss-guided growth, `max_depth=24`, `max_leaves=255`, `max_bin=1024`, and `colsample_bytree=0.6`, with sine/cosine features for scheduled time, weekday, and month.
- **What helped:** Cyclical schedule features improved AUC from 0.7518 to 0.7533; a depth cap of 24 added another 0.0005 over unrestricted depth. A depth cap of 16 was also slightly better than unlimited depth.
- **What did not:** Depth 8 and 32, higher feature sampling (0.7/0.8), `gamma`, `min_child_weight=2`, more rounds at a lower rate, a second time harmonic, and target-rate features failed to beat the best. Higher feature sampling and gamma 1.0 caused larger regressions.
- **Current theory:** The first-harmonic cyclic features and a moderately bounded loss-guided tree structure complement the existing schedule and airport/carrier inputs. More aggressive sampling or regularization removes useful structure.
- **Next direction:** Search the remaining XGBoost split and leaf-weight regularizers at small values, or revisit histogram resolution with the new cyclic features. Any new feature family should preserve single-row evaluation semantics and use only `train.csv`-fitted lookups.

## Experiment 51 — commit a511e07

- **Class:** L1 regularization exploration.
- **Hypothesis:** A small `reg_alpha` might shrink weak leaf weights without the large structural effect of `gamma=1`.
- **Change:** Added `reg_alpha=0.1`, retaining the depth-24 best otherwise.
- **Result:** Eval AUC 0.7526, down 0.0012. Training took 19.4s and artifact size was 69.8 MB.
- **Decision:** Discard and reset to c4b82d2. The mild L1 penalty reduced AUC and increased artifact size.

## Experiment 52 — commit 81a3668

- **Class:** Tree-count follow-up at the current learning rate.
- **Hypothesis:** An extra 100 rounds at learning rate 0.03 could capture residual signal left by the 1,000-tree model.
- **Change:** Increased `n_estimators` to 1,100 and changed nothing else.
- **Result:** Eval AUC 0.7536, down 0.0002. Training took 22.0s and evaluation 41.5s.
- **Decision:** Discard and reset to c4b82d2. The added rounds did not beat the current best.

## Experiment 53 — commit 5aacf89

- **Class:** Depth-cap refinement between 16 and 24.
- **Hypothesis:** A cap of 20 might retain the depth-24 gain while constraining some deeper paths.
- **Change:** Set `max_depth=20`; kept the 255-leaf cap and all other best settings.
- **Result:** Eval AUC 0.7529, down 0.0009 from depth 24. Training took 20.3s and artifact size was 62.3 MB.
- **Decision:** Discard and reset to c4b82d2. Depth 24 remains preferable.

## Experiment 54 — commit 41707e7

- **Class:** Depth-cap refinement between 24 and 32.
- **Hypothesis:** A cap of 28 might retain more useful capacity than 24 without matching the longer paths allowed at 32.
- **Change:** Set `max_depth=28`; kept all other settings unchanged.
- **Result:** Eval AUC 0.7534, down 0.0004 from depth 24. Training took 19.2s and artifact size was 62.1 MB.
- **Decision:** Discard and reset to c4b82d2. Depth 24 remains the best tested setting.

## Experiment 55 — commit dc462d7

- **Class:** Leaf-budget ablation of the depth-24 best.
- **Hypothesis:** A modestly smaller 192-leaf budget might reduce overfitting while retaining more capacity than the earlier 127-leaf model.
- **Change:** Changed only `max_leaves` from 255 to 192.
- **Result:** Eval AUC 0.7525, down 0.0013. Training took 15.5s and artifact size fell to 49.3 MB.
- **Decision:** Discard and reset to c4b82d2. The smaller artifact does not compensate for the AUC loss.

## Experiment 56 — commit cf22dca

- **Class:** Histogram-resolution follow-up to the 1,024-bin best.
- **Hypothesis:** With six additional continuous cyclic inputs, an intermediate 768-bin histogram might balance split resolution and generalization.
- **Change:** Changed only `max_bin` from 1,024 to 768.
- **Result:** Eval AUC 0.7535, down 0.0003. Training took 18.5s and evaluation 41.3s.
- **Decision:** Discard and reset to c4b82d2. Keep 1,024 bins.

## Experiment 57 — commit 4e521f0

- **Class:** Fine-grained feature-sampling follow-up to the 0.6 best.
- **Hypothesis:** A slightly smaller per-tree feature fraction could reduce noise while still sampling enough of the six cyclic columns.
- **Change:** Set `colsample_bytree=0.55` and retained the depth-24 model otherwise.
- **Result:** Eval AUC 0.7540, a new best by 0.0002. Training took 18.6s, evaluation 41.4s, and artifact size fell to 58.4 MB.
- **Decision:** Keep commit 4e521f0 as the new best.

## Experiment 58 — commit 4741fc0

- **Class:** Follow-up to the 0.55 feature-sampling improvement.
- **Hypothesis:** A further reduction to 0.5 might reduce noise while retaining the AUC gain.
- **Change:** Set `colsample_bytree=0.5` with all other settings fixed.
- **Result:** Eval AUC 0.7540, tied with 0.55; training and evaluation times were essentially unchanged.
- **Decision:** Discard and reset to 4e521f0. The less restrictive 0.55 setting achieved the same score.

## Final summary

- **Best Eval AUC:** 0.7540 at commit 4e521f0 (`colsample_bytree=0.55`, depth 24, 255 leaves, 1,024 bins, 1,000 trees at learning rate 0.03, with cyclic sine/cosine features for scheduled departure time, weekday, and month).
- **What worked:** The cyclic schedule features and a moderate loss-guided depth cap improved the model. Reducing per-tree feature sampling from 0.6 to 0.55 produced the final small gain.
- **What did not:** Smoothed target-rate features, larger feature-sampling fractions, higher split penalties, L1 regularization, altered boosting schedules, smaller leaf budgets, and histogram settings away from 1,024 did not improve AUC. Depth 24 outperformed the tested neighboring caps.
- **Final branch state:** `oct1` at 4e521f0, the best kept commit. Results and research logs remain uncommitted as required.
