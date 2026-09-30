# Research log: sep29

## Baseline — 92e43e6

The unmodified starter reached Eval AUC 0.7203. Training took 1.1s and evaluation 30.2s. It uses 30 depth-6 trees with learning rate 0.1 and native categorical handling.

## Experiment 1 hypothesis

**Follow-up.** Increase `n_estimators` from 30 to 200 with all else fixed. At 30 rounds and eta 0.1 the model may still have substantial bias. The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends balancing step size with boosting rounds and adjusting model complexity. Training has ample headroom under 60s.

## Experiment 1 result — 05cfe71

Eval AUC 0.7345 (+0.0142); keep. Training 2.0s, evaluation 30.6s. The large gain supports the underfitting hypothesis.

## Experiment 2 hypothesis

**Follow-up.** Increase to 500 trees at the same learning rate, depth, and feature set. Extra rounds may capture residual structure; a lower score would indicate overfitting and set a useful upper bound.

## Experiment 2 result — c1b40e4

Eval AUC 0.7312 (-0.0033 versus best); discard. Training 3.6s. The decline suggests overfitting at this depth and learning rate.

## Experiment 3 hypothesis

**Ablation/simplification.** Return to 200 trees and reduce `max_depth` from 6 to 4. Shallower trees may generalize better on 200k rows with 8 input columns, while simplifying the model. This follows the [XGBoost depth guidance](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster).

## Experiment 3 result — 0c4d648

Eval AUC 0.7317 (-0.0028 versus best); discard. Depth 4 removed useful interactions.

## Experiment 4 hypothesis

**Exploration.** Add an ordinal day-of-year feature, keeping the original month and day categorical features. It may make seasonal patterns and nearby dates easier to express with fewer splits. [Naul's airline delay study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) included day of year among its schedule features. The feature is computed independently for each row and has no label information.

## Experiment 4 result — cee0f72

Eval AUC 0.7385 (+0.0040 versus best); keep. Training 2.0s and evaluation 35.3s. A numeric seasonal axis helps beyond separate categorical month and day.

## Experiment 5 hypothesis

**Exploration.** Add an Origin-Dest route category with levels fixed from `train.csv`. A route may encode a stable operational pattern that separate origin and destination splits cannot capture easily. [Naul's study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) discusses route-based historical predictors; [XGBoost categorical docs](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explain partition-based categorical splits. No route frequency or target statistic is used.

## Experiment 5 result — 4bbed2a

Eval AUC 0.7125 (-0.0260 versus best); discard. Evaluation rose to 47.6s. The high-cardinality route category appears to overfit badly; avoid similar unconstrained combinations.

## Experiment 6 hypothesis

**Exploration.** Add scheduled departure hour as a 24-level categorical feature, retaining the original time. This lets XGBoost group hours with similar risk while keeping numeric thresholds. [Naul's study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) lists scheduled departure time as a relevant feature, and the [XGBoost categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) describes the partition split used for this encoding.

## Experiment 6 result — 643759e

Eval AUC 0.7372 (-0.0013); discard. Departure hour adds no useful signal beyond the original numeric scheduled time.

## Experiment 7 hypothesis

**Follow-up.** Raise `min_child_weight` from the default 1 to 5 at the best 200-tree depth-6 model. The 500-tree decline and route overfit suggest regularization may help; [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster) says this parameter discourages small leaves.

## Experiment 7 result — b8e7723

Eval AUC 0.7370 (-0.0015); discard. A minimum child weight of 5 removes useful fine-grained splits.

## Experiment 8 hypothesis

**Exploration.** Try `subsample=0.8` at the best model. [XGBoost's tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) identifies row subsampling as a way to make training more robust to noise, which could help when extra rounds overfit.

## Experiment 8 result — 8e39ade

Eval AUC 0.7301 (-0.0084); discard. Row subsampling removed useful signal. The kept model's gain importances give CRSDepTime about half the total, far ahead of other features.

## Experiment 9 hypothesis

**Exploration.** Increase `max_depth` from 6 to 7 while keeping 200 trees. Depth 4 underfit, and more depth may let a tree express local interactions involving scheduled time. [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster) notes this raises complexity, so the eval result will decide whether the extra capacity is warranted.

## Experiment 9 result — 9bf33e0

Eval AUC 0.7363 (-0.0022); discard. Additional depth also hurts, so depth 6 remains best among tested values.

## Experiment 10 hypothesis

**Follow-up.** Reduce boosting rounds from 200 to 120 with all else fixed. Since 500 rounds overfit, this brackets the optimum from the other side and tests whether the best result can be matched with a simpler model.

## Experiment 10 result — 97af306

Eval AUC 0.7375 (-0.0010); discard. The best 200-tree setting lies between tested 120 and 500 rounds.

## Synthesis after 10 experiments

Best is 0.7385 at cee0f72, with 200 depth-6 trees and ordinal day of year. More rounds, fewer rounds, shallower/deeper trees, a route category, departure-hour category, min child weight 5, and row subsampling all reduced AUC. The strongest gain came from making calendar position explicit. Scheduled departure time dominates feature gain, suggesting careful handling of its many distinct values may matter more than adding high-cardinality interactions. The next direction is histogram resolution, then categorical split controls and low-cost temporal features.

Research pause: [XGBoost's tree method discussion](https://xgboost.readthedocs.io/en/release_3.3.0/treemethod.html) says higher `max_bin` with `hist` can improve split accuracy; [current parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster) explain that larger bins cost compute. [Interaction constraint docs](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html) are another possible way to focus trees if overfitting persists.

## Experiment 11 hypothesis

**Exploration.** Raise `max_bin` from 256 to 512 on the kept model. CRSDepTime has 1,162 distinct training values and is the dominant feature; finer bins may let the histogram method find better schedule-time thresholds. Training remains well below its one-minute limit.

## Experiment 11 result — 74905eb

Eval AUC 0.7370 (-0.0015); discard. Finer bins did not improve the schedule-time splits.

## Experiment 12 hypothesis

**Follow-up.** Try `max_bin=128`, the other side of the default. Coarser thresholds may regularize the dominant scheduled-time feature, whereas 512 bins hurt. This is the same histogram-control mechanism described in the [XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster).

## Experiment 12 result — 38def31

Eval AUC 0.7368 (-0.0017); discard. The default 256 bins outperforms both tested coarser and finer resolutions.

## Experiment 13 hypothesis

**Exploration.** Set `max_cat_threshold=16` to limit categories considered per partition split. Origin and destination each have 283 levels, and the unconstrained route feature overfit; the [XGBoost categorical parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-categorical-feature) describe this control as overfit prevention for categorical splits.

## Experiment 13 result — 896a651

Eval AUC 0.7419 (+0.0034); keep. Artifact shrank from 5.4 MB to 4.1 MB, and train/eval time stayed similar. High-cardinality airport splits benefited from a tighter category limit.

## Experiment 14 hypothesis

**Follow-up.** Reduce `max_cat_threshold` from 16 to 8. The 16-category limit helped substantially; a smaller candidate set may further curb noisy airport splits, though it could discard useful categories.

## Experiment 14 result — 1b481e1

Eval AUC 0.7421 (+0.0002); keep. The gain is small, but the artifact is also smaller at 3.4 MB. Categorical regularization continues to help.

## Experiment 15 hypothesis

**Follow-up.** Reduce `max_cat_threshold` from 8 to 4. This checks whether still simpler category partitions improve or whether the model begins to underfit the airport signal.

## Experiment 15 result — 197c950

Eval AUC 0.7369 (-0.0052); discard. Four categories per split is too restrictive; eight stays best.

## Experiment 16 hypothesis

**Exploration.** On the kept eight-category model, set `max_cat_to_onehot=8` so the seven-level day-of-week feature uses one-hot splits while higher-cardinality features remain partitioned. The [XGBoost categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains the two split types. A weekday-specific split may be more stable than grouping weekdays by the leaf gradient.

## Experiment 16 result — 0d5b85c

Eval AUC 0.7411 (-0.0010); discard. Partitioning is better for weekdays too.

## Experiment 17 hypothesis

**Exploration.** Add scheduled minute within the hour (`CRSDepTime % 100`). The dominant scheduled-time field may have recurring patterns at common schedule minutes, which are awkward for trees to share across all hours. [Naul's airline delay study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) supports scheduled-time features; the repeated-minute hypothesis is an inference to test. This feature uses only the row's scheduled time.

## Experiment 17 result — dd027b4

Eval AUC 0.7410 (-0.0011); discard. A separate minute-of-hour feature did not help.

## Experiment 18 hypothesis

**Exploration.** Add distance in days to selected major 2005 travel holidays (New Year's, July 4, Thanksgiving, Christmas). This single numeric feature could highlight narrow demand and congestion periods that day of year needs many splits to express. [Naul's airline delay study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) used holiday proximity; [OPM's federal holiday rules](https://www.opm.gov/policy-data-oversight/pay-leave/pay-administration/fact-sheets/holidays-work-schedules-and-pay) identify those dates. The feature is a fixed calendar lookup, not derived from eval rows or labels.

## Experiment 18 result — 1b8c76e

Eval AUC 0.7420 (-0.0001); discard. Extra calendar complexity gave no meaningful gain.

## Experiment 19 hypothesis

**Ablation/simplification.** Remove Distance, the lowest-gain feature in the kept model (about 2.3% of gain). If AUC stays equal or improves, the model and one-row evaluation can be simpler; if it falls, Distance is contributing useful geographic context.

## Experiment 19 result — a752d03

Eval AUC 0.7407 (-0.0014); discard. Distance adds useful context despite its low global gain importance.

## Experiment 20 hypothesis

**Ablation/simplification.** Remove the categorical DayofMonth input while retaining it in the computed DayOfYear feature. This asks whether the explicit calendar axis captures enough date information to simplify the model, or whether recurring day-of-month effects matter.

## Experiment 20 result — a0fa0ee

Eval AUC 0.7381 (-0.0040); discard. Explicit day-of-month category still carries useful information beyond day of year.

## Synthesis after 20 experiments

Best is 0.7421 at 1b481e1. DayOfYear and `max_cat_threshold=8` produced the clear gains. The latter also reduced artifact size. A limit of 4 underfits. Histogram bin changes, weekday one-hot splits, minute-of-hour, holiday proximity, and removing Distance or DayofMonth did not help. The current theory is that the benchmark rewards smooth seasonal position plus restrained categorical airport partitions, while most extra feature detail adds noise. Next, test boosting dynamics and tree growth without adding feature complexity.

Research pause: [XGBoost's original paper](https://arxiv.org/abs/1603.02754) discusses shrinkage and its role in leaving room for later trees; the [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) advises increasing rounds when lowering learning rate. The [tree-method guide](https://xgboost.readthedocs.io/en/release_3.3.0/treemethod.html) and [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster) suggest alternative growth policies to explore if shrinkage stalls.

## Experiment 21 hypothesis

**Exploration.** Halve learning rate to 0.05 and double boosting rounds to 400. This keeps roughly the same total boosting path while letting each tree make a smaller correction; it may improve generalization beyond the fixed-rate round sweep.

## Experiment 21 result — 7668687

Eval AUC 0.7427 (+0.0006); keep. Training remains quick at 2.7s; artifact size rose to 6.6 MB. The gain is modest but required only parameter changes, with no feature complexity.

## Experiment 22 hypothesis

**Follow-up.** Try learning rate 0.03 and 650 rounds, keeping the approximate boosting path length near 20. Further shrinkage may smooth later corrections and improve ranking, though model size grows.

## Experiment 22 result — 31cddc8

Eval AUC 0.7431 (+0.0004); keep. Training 3.9s, artifact 10.9 MB. The improvement is small but consistent with the previous shrinkage test.

## Experiment 23 hypothesis

**Follow-up.** Try learning rate 0.02 and 1,000 rounds, keeping the product of rate and rounds at 20. This checks whether the monotonic gain from smaller steps continues; a flat score would favor the smaller 650-tree model.

## Experiment 23 result — 1313856

Eval AUC 0.7432 (+0.0001); keep under the strict higher-AUC criterion. The gain is tiny relative to 650 trees, and the artifact grew to 16.7 MB, so further shrinking needs a clearer payoff.

## Experiment 24 hypothesis

**Follow-up.** Try learning rate 0.01 and 2,000 rounds as a final low-rate point at the same approximate boosting path length. This will show whether the trend continues or saturates; training remains below the 60s limit.

## Experiment 24 result — 7b26035

Eval AUC 0.7432 (equal); discard because the model doubled to 33.3 MB with no measured gain. Shrinkage appears saturated near 0.02–0.03.

## Experiment 25 hypothesis

**Exploration.** Increase L2 leaf regularization `reg_lambda` from its default 1 to 5 on the kept 1,000-tree model. This may reduce noisy late-tree leaf corrections without suppressing entire splits. [XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster) describe larger lambda as more conservative.

## Experiment 25 result — 1813392

Eval AUC 0.7458 (+0.0026); keep. Training 5.3s, artifact 17.9 MB. Stronger leaf shrinkage complements the small learning rate well.

## Experiment 26 hypothesis

**Follow-up.** Raise `reg_lambda` from 5 to 10. The clear gain at 5 suggests more leaf regularization could further tame late-tree noise; too much would underfit.

## Experiment 26 result — 9c58353

Eval AUC 0.7470 (+0.0012); keep. Artifact decreased to 16.9 MB. The categorical and leaf regularizers are both helping.

## Experiment 27 hypothesis

**Follow-up.** Raise `reg_lambda` from 10 to 20 to find whether the regularization trend continues. We expect a peak once leaf values become too conservative.

## Experiment 27 result — b080087

Eval AUC 0.7470 (equal); discard. Artifact was slightly smaller (16.5 versus 16.9 MB), but there is no meaningful improvement from doubling lambda again.

## Experiment 28 hypothesis

**Follow-up.** At the kept lambda 10 and learning rate 0.02, raise trees from 1,000 to 1,500. Stronger leaf regularization may allow additional rounds to learn signal; this tests whether the optimum number of rounds moved after the lambda change.

## Experiment 28 result — f0db0f7

Eval AUC 0.7493 (+0.0023); keep. Training 7.3s, artifact 24.6 MB. The extra rounds recover useful detail once leaf values are regularized.

## Experiment 29 hypothesis

**Follow-up.** Increase to 2,000 trees at lambda 10 and learning rate 0.02. The large gain from 1,500 rounds suggests the best stopping point may be later, while training remains comfortably under the limit.

## Experiment 29 result — 58b93e0

Eval AUC 0.7504 (+0.0011); keep. Training 9.3s, artifact 32.6 MB. The learning curve has not saturated under lambda 10.

## Experiment 30 hypothesis

**Follow-up.** Increase to 3,000 trees with the same leaf regularization and learning rate. This tests whether the upward trend continues, with expected training still below one minute.

## Experiment 30 result — ea1fa18

Eval AUC 0.7509 (+0.0005); keep. Training 13.4s, artifact 48.1 MB. Extra rounds still help, but the marginal gain is shrinking.

## Synthesis after 30 experiments

Best is 0.7509 at ea1fa18, up 0.0306 from baseline. The strongest recent pattern is small learning rate plus substantial L2 regularization and more boosting rounds. Lambda 10 improved over 5; lambda 20 tied. Under lambda 10, 1,000 → 1,500 → 2,000 → 3,000 rounds improved monotonically, with diminishing returns. Earlier feature and categorical findings remain: DayOfYear and `max_cat_threshold=8` helped. New goal: test a different leaf penalty and growth policy, then revisit round count only if gains justify the larger artifact.

Research pause: [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster) describes `reg_alpha` as an L1 leaf-weight penalty and `gamma` as a minimum split gain. Its `lossguide` growth policy prioritizes the highest-gain leaf. The [DART tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) suggests dropout as another option but notes slower training, relevant to the one-minute limit.

## Experiment 31 hypothesis

**Exploration.** Add `reg_alpha=1` to the 3,000-tree lambda-10 model. L1 shrinkage may eliminate small noisy leaf updates while retaining the effects of useful leaves, complementing the L2 penalty.

## Experiment 31 result — 46acea7

Eval AUC 0.7527 (+0.0018); keep. Training 14.2s, artifact 50.1 MB. L1 and L2 are complementary in this setup.

## Experiment 32 hypothesis

**Follow-up.** Raise `reg_alpha` from 1 to 5. A stronger threshold on small leaf values may further improve ranking; overpenalizing would harm signal.

## Experiment 32 result — 9b72c4c

Eval AUC 0.7594 (+0.0067); keep. Artifact shrank to 41.6 MB. This is the largest single improvement since increasing starter rounds: weak leaves were evidently a major source of noise.

## Experiment 33 hypothesis

**Follow-up.** Raise `reg_alpha` from 5 to 10. The strong improvement suggests another increase may further filter noisy leaves, but the optimum could be close.

## Experiment 33 result — 2b51c15

Eval AUC 0.7609 (+0.0015); keep. Artifact shrank again to 32.8 MB. The L1 benefit continues, though less sharply.

## Experiment 34 hypothesis

**Follow-up.** Raise `reg_alpha` from 10 to 20. This brackets the upper side of the L1 optimum and tests whether a much sparser set of leaf updates still captures enough signal.

## Experiment 34 result — 8726521

Eval AUC 0.7560 (-0.0049); discard. L1 at 20 suppresses useful signal. The best tested range is around 10.

## Experiment 35 hypothesis

**Follow-up.** At the kept alpha 10, increase boosting rounds from 3,000 to 4,000. Strong L1 sparsifies leaves, so more rounds may recover later residual patterns without overfitting. This also tests whether the round optimum changed after L1 regularization.

## Experiment 35 result — 0a7fb50

Eval AUC 0.7617 (+0.0008); keep. Training 19.2s and artifact 42.1 MB. More rounds still help under L1, but gains remain modest.

## Experiment 36 hypothesis

**Exploration.** Lower `reg_lambda` from 10 to 5 while retaining `reg_alpha=10` and 4,000 rounds. L1 may now handle much of the noise control; weaker L2 could restore useful leaf magnitudes. This directly tests interaction between the two penalties.

## Experiment 36 result — 2f4a00d

Eval AUC 0.7615 (-0.0002); discard. Reducing L2 did not help, despite strong L1.

## Experiment 37 hypothesis

**Follow-up.** Raise `reg_lambda` from 10 to 20 at alpha 10 and 4,000 rounds. This brackets the interaction from the other side: if L1 and L2 remain complementary, stronger L2 may improve or simplify the ensemble.

## Experiment 37 result — 156cc1d

Eval AUC 0.7606 (-0.0011); discard. L2 10 remains best with L1 10.

## Experiment 38 hypothesis

**Exploration.** Add `gamma=1` to require a minimum training-loss gain for each split. L1 has helped by suppressing weak leaves; [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster) describes gamma as a direct split penalty that may offer a simpler tree structure.

## Experiment 38 result — 88b18ba

Eval AUC 0.7491 (-0.0126); discard. Gamma 1 shrank the artifact to 10.8 MB but removed too much useful structure.

## Experiment 39 hypothesis

**Follow-up.** Try a tenfold smaller split penalty, `gamma=0.1`. The gamma-1 result shows split pruning is powerful; a gentle threshold may remove only the weakest branches without the severe underfit.

## Experiment 39 result — 2748bbc

Eval AUC 0.7569 (-0.0048); discard. Even a 0.1 split penalty prunes too much; L1 controls leaf values more effectively than gamma controls branch existence here.

## Experiment 40 hypothesis

**Exploration.** Use `grow_policy='lossguide'`, unlimited depth, and `max_leaves=64` at the kept settings. The baseline depth-6 tree can have at most 64 leaves; this alternative spends a comparable leaf budget on the highest-gain regions, possibly modeling departure-time interactions more efficiently. [XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster) define this policy and the leaf cap.

## Experiment 40 result — 93f4681

Eval AUC 0.7640 (+0.0023); keep. Training 31.2s, evaluation 36.6s, artifact 45.5 MB. Leaf-wise growth helps but uses much of the one-minute training allowance.

## Synthesis after 40 experiments

Best is 0.7640 at 93f4681, +0.0437 from baseline. The combination of DayOfYear, restrained categorical partitions, low learning rate, many rounds, L2=10, L1=10, and leaf-wise growth has produced the gains. L1=20 underfit. Adjusting L2 to 5 or 20 at L1=10 did not help. Gamma at 0.1 or 1 pruned too much, unlike L1. Next prioritize tuning the leaf budget within the 60-second training limit, then revisit feature and category controls under the improved model.

Research pause: [XGBoost's current parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster) defines `lossguide` as splitting the highest-gain leaf and `max_leaves` as its cap. The [categorical example](https://xgboost.readthedocs.io/en/stable/python/examples/categorical.html) confirms histogram training with native categorical inputs. Airport-delay research still points to schedule, weather and congestion, but the latter two are unavailable in this dataset; changes here should use only the permitted schedule fields.

## Experiment 41 hypothesis

**Follow-up.** Increase the leaf-wise cap from 64 to 96 at 4,000 rounds. More leaves may capture useful local time-airport interactions; training at 64 leaves took 31s, leaving some headroom before the 60s limit.

## Experiment 41 result — 4e752f0

Eval AUC 0.7643 (+0.0003); keep. Training rose to 41.1s and artifact to 61.4 MB. The gain is small, so the training limit is now the main constraint.

## Experiment 42 hypothesis

**Follow-up.** Increase `max_leaves` to 128. The 64-to-96 change helped slightly, and linear extrapolation from 41s suggests 128 may still fit within 60s; the harness will enforce that bound.

## Experiment 42 result — 43283ff

Eval AUC 0.7644 (+0.0001); keep under the strict higher-AUC rule. Training 47.5s and artifact 75.9 MB. The gain is tiny for the cost, so do not raise the leaf cap further without a new reason.

## Experiment 43 hypothesis

**Ablation/simplification.** Reduce trees from 4,000 to 3,000 at 128 leaves. Larger trees may need fewer rounds to capture the same structure; an equal score would give a faster, smaller model and more training headroom.

## Experiment 43 result — 99067af

Eval AUC 0.7650 (+0.0006); keep. Training fell to 39.0s and artifact to 60.4 MB. The larger leaf-wise trees work better with fewer rounds.

## Experiment 44 hypothesis

**Follow-up/simplification.** Reduce to 2,000 rounds at 128 leaves. The 3,000-round result beat 4,000 and was simpler; this probes whether the optimum moved even earlier.

## Experiment 44 result — d6fd70b

Eval AUC 0.7651 (+0.0001); keep. Training fell to 28.8s and artifact to 44.3 MB. The improvement is slight, but simpler and faster too.

## Experiment 45 hypothesis

**Follow-up/simplification.** Reduce to 1,500 rounds at 128 leaves. Since both 3,000 and 2,000 beat 4,000, a shorter ensemble may be near the optimum.

## Experiment 45 result — 675267d

Eval AUC 0.7646 (-0.0005); discard. The smaller artifact and 21.5s training did not offset the score loss. Two thousand rounds remain best.

## Experiment 46 hypothesis

**Exploration.** Raise `max_cat_threshold` from 8 to 16 in the 2,000-round, 128-leaf model. The earlier eight-category optimum was found with smaller depth-wise trees; stronger L1 and larger leaf-wise trees may support richer airport category partitions now.

## Experiment 46 result — e679d04

Eval AUC 0.7648 (-0.0003); discard. The eight-category limit still performs better and trains slightly faster.

## Experiment 47 hypothesis

**Exploration.** Set `min_child_weight=5` in the kept leaf-wise model. It hurt the early depth-wise model, but deeper 128-leaf trees can create much smaller local groups. [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster) says this limit prevents splits with too little Hessian mass, which may help specifically in the new growth regime.

## Experiment 47 result — 7028790

Eval AUC 0.7648 (-0.0003); discard. The higher child-weight limit did not help even with deeper leaf-wise trees.

## Experiment 48 hypothesis

**Ablation/simplification.** Keep 2,000 rounds but reduce the leaf cap from 128 to 96. Previous 96-leaf tests used 4,000 rounds; with fewer rounds, the smaller tree may avoid late fine-grained noise and reduce training time while retaining AUC.

## Experiment 48 result — fdf6459

Eval AUC 0.7637 (-0.0014); discard. Ninety-six leaves train faster but lose too much signal at the shorter round count.

## Experiment 49 hypothesis

**Follow-up.** Increase `reg_alpha` from 10 to 12 at the 128-leaf, 2,000-round best. The earlier depth-wise sweep put the L1 optimum near 10, but larger leaves may benefit from slightly stronger sparsity.

## Experiment 49 result — f3fb295

Eval AUC 0.7637 (-0.0014); discard. The best L1 setting remains 10; more sparsity loses signal in the leaf-wise model.

## Experiment 50 hypothesis

**Exploration/simplification.** Use learning rate 0.03 with 1,350 rounds, keeping a similar aggregate step budget to 0.02 with 2,000 rounds. Larger steps may reach comparable ranking with a smaller, faster ensemble, or may overfit the deeper leaves.

## Experiment 50 result — 0f262ad

Eval AUC 0.7651 (equal); keep as a simplification. Training fell from 28.8s to 19.9s and artifact from 44.3 to 30.0 MB. The model retains the best score with considerably less cost.

## Synthesis after 50 experiments

Best is 0.7651 at 0f262ad, up 0.0448 from baseline. The gains in this block came from leaf-wise trees, then finding that 128 leaves need fewer rounds. The final 1,350-round model matches the score of 2,000 rounds at a higher learning rate and uses much less time and space. Categorical threshold 16, child weight 5, 96 leaves at 2,000 rounds, and L1 12 all scored lower. The current theory is that the model has enough capacity; new schedule representations may be more valuable than further small parameter sweeps.

Research pause: [scikit-learn's time-feature guide](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) explains how sine/cosine encodings join the ends of periodic time ranges; it also notes trees can already model non-monotonic effects, so the benefit here is uncertain. [Airline-delay research](https://www.sciencedirect.com/science/article/pii/S2772415822000050) identifies departure time and carrier among relevant predictors. The permitted fields lack weather and live congestion, so schedule-only transformations are the available feature direction.

## Experiment 51 hypothesis

**Exploration.** Add sine and cosine of day of year, retaining the numeric DayOfYear feature. This may let the model share winter structure across the December/January boundary with fewer splits. The maps are fixed calendar functions applied per row.

## Experiment 51 result — 163afc6

Eval AUC 0.7654 (+0.0003); keep. Artifact fell to 28.6 MB, though row-wise evaluation increased from about 36s to 41s. The small gain and lower model size justify the two calendar maps.

## Experiment 52 hypothesis

**Exploration.** Add sine and cosine of scheduled minute of day, retaining raw CRSDepTime. This may join the late-night and just-after-midnight ends of the schedule clock. [scikit-learn's time-feature guide](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) explains the periodic encoding; whether it helps this tree model is an empirical question.

## Experiment 52 result — d911bf4

Eval AUC 0.7644 (-0.0010); discard. Evaluation rose to 50.5s and the extra time features did not help.

## Experiment 53 hypothesis

**Exploration.** Add scheduled departure minute relative to the training-set median for the origin airport. This may express whether a flight is early or late in its origin's usual operating day, allowing a shared split across airports. The median lookup is fitted only on `train.csv`, then applied row by row. The `program.md` feature-engineering example uses the same train-fitted lookup pattern; [airline schedule research](https://link.springer.com/article/10.1007/s13272-026-00941-7) supports airport and scheduled-time context. The relative-time benefit is an inference to test.

## Experiment 53 result — f5f668e

Eval AUC 0.7644 (-0.0010); discard. Evaluation increased to 44.9s. Relative scheduled time did not add useful information beyond origin and raw scheduled time.

## Experiment 54 hypothesis

**Ablation/simplification.** Remove `SeasonSin`, keeping `SeasonCos` and numeric DayOfYear. Cosine joins December and January and conveys the winter/summer cycle; DayOfYear can still distinguish spring from autumn. This could retain the small cyclic gain with one less feature and faster per-row preparation.

## Experiment 54 result — a649bb1

Eval AUC 0.7648 (-0.0006); discard. Evaluation improved to 38.9s, but the sine feature contributes enough to retain the full pair.

## Experiment 55 hypothesis

**Exploration.** Add `colsample_bytree=0.9` to make each tree ignore a small share of features. Scheduled departure time dominates gain; occasional trees trained without it may learn complementary airport and calendar effects. [XGBoost's original paper](https://arxiv.org/abs/1603.02754) and [tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) describe feature subsampling as an overfit control. This is distinct from the earlier failed row subsampling test.

## Experiment 55 result — 1807b07

Eval AUC 0.7652 (-0.0002); discard. Model size changed little, and mild column sampling did not improve ranking.

Plateau research: [scikit-learn's soft-voting documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html) describes weighted probability averaging of separately fitted classifiers. [XGBoost's current parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) also offers gradient-based row sampling, but the earlier uniform row-sampling loss makes that less compelling. A blend of the best leaf-wise model and a depth-wise model is a different way to reduce variance without changing the feature data.

## Experiment 56 hypothesis

**Exploration.** Train a second depth-wise XGBoost model on the same prepared training rows and soft-vote its probabilities with the kept leaf-wise model at a 1:4 weight. The models should make partly different errors; averaging may improve ranking. This adds fitting and artifact complexity, so it needs a meaningful AUC gain to keep.

## Experiment 56 result — c1d7cb5

Eval AUC 0.7653 (-0.0001); discard. Training rose to 33.7s and artifact to 60.8 MB. The extra model did not justify its complexity.

## Experiment 57 hypothesis

**Exploration.** Try histogram `sampling_method='gradient_based'` with `subsample=0.8`. Unlike the earlier uniform row-sampling test, [XGBoost's current parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster) says this prioritizes rows with larger gradients. Later rounds may focus on hard examples without giving up as much useful data.

## Experiment 57 result — fb86687

Eval AUC 0.7660 (+0.0006); keep. Training took 25.0s and the artifact was 32.2 MB. Gradient-based sampling improved the ranking enough to offset the modest extra cost.

## Experiment 58 hypothesis

**Exploration.** Reduce gradient-based `subsample` from 0.8 to 0.6. Stronger selection of high-gradient rows could focus growth on harder flights while retaining enough rows for robust splits.

## Experiment 58 result — 0cdd216

Eval AUC 0.7648 (-0.0012); discard. Training took 25.9s and the artifact was 35.9 MB. Selecting fewer rows hurt the ranking.

## Experiment 59 hypothesis

**Exploration.** Increase gradient-based `subsample` to 0.9. The 0.6 trial lost accuracy, so a milder sampling rate may retain more broad patterns while keeping the gain from prioritizing larger gradients.

## Experiment 59 result — d2e1eaa

Eval AUC 0.7664 (+0.0004); keep. Training took 24.0s and the artifact was 30.0 MB. Milder gradient sampling improved again.

## Experiment 60 hypothesis

**Exploration.** Add a categorical origin–destination route identifier from each row. The [Stanford airline delay study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) identifies origin and destination as predictive context and notes that less-traveled routes have fewer examples; [XGBoost's categorical guide](https://xgboost.readthedocs.io/en/release_3.2.0/tutorials/categorical.html) supports native category partitions. A route category may expose pair-specific effects that separate airport features cannot express cheaply. Fit its vocabulary only on `train.csv`; unseen routes become missing.

## Experiment 60 result — 9978cff

Eval AUC 0.7659 (-0.0005); discard. Training took 45.5s and evaluation 57.4s. The 4,290-level route feature also failed early in experiment 5; repeating it under the much stronger leaf-wise model still did not pay off.

## Synthesis after 60 experiments

Best is 0.7664 at d2e1eaa, up 0.0461 from baseline. The main gains came from explicit day of year and season features, strong L1/L2 regularization, many small steps, 128-leaf growth, and gradient-based row sampling. Sampling 0.9 beat 0.8, while 0.6 lost; selective sampling seems useful when it retains most rows. Route categories have now failed in both early and mature models, and the most recent attempt nearly doubled training time. The current theory is that broad temporal and airport patterns generalize better than sparse route identities. Next try a compact calendar signal for holiday travel, then consider new low-cardinality interactions or histogram settings under the current model. Research pause: the [Stanford departure-delay study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) includes holiday proximity, and the [US Office of Personnel Management holiday calendar](https://www.opm.gov/policy-data-oversight/pay-leave/federal-holidays/) defines the dates. The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends balancing tree complexity and randomized sampling; additional regularization controls already failed in this experiment.

## Experiment 61 hypothesis

**Exploration.** Add distance in days to the nearest major 2005 holiday using the row's day of year. Holiday proximity appears in the [Stanford airline delay feature set](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf), and [OPM](https://www.opm.gov/policy-data-oversight/pay-leave/pay-administration/fact-sheets/holidays-work-schedules-and-pay) defines the holiday dates. This gives trees a shared split for days near holidays while the existing season features distinguish periods of the year.

## Experiment 61 result — 3db5bca

Eval AUC 0.7661 (-0.0003); discard. Training took 23.4s and artifact was 29.4 MB. The existing day-of-year and seasonal representation seems sufficient for this coarse holiday signal.

## Experiment 62 hypothesis

**Exploration.** Raise histogram `max_bin` to 512 under the current leaf-wise model. This hurt the early depth-wise model, but the newer model uses different splits and gradient-based sampling. [XGBoost's tree-method guide](https://xgboost.readthedocs.io/en/release_3.3.0/treemethod.html) says more bins can improve split accuracy, at the cost of computation. Scheduled departure time has many distinct values, so finer thresholds may matter now.

## Experiment 62 result — 7a20488

Eval AUC 0.7661 (-0.0003); discard. Training took 23.1s and artifact was 29.7 MB. Finer histogram thresholds did not beat the default resolution.

## Experiment 63 hypothesis

**Follow-up.** Raise `max_leaves` from 128 to 160 under gradient-based sampling. The current sampling suppresses some low-gradient rows; larger leaf capacity may recover local patterns without the overfit seen in the unsampled model. [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster) says the leaf cap controls complexity with `lossguide` growth.

## Experiment 63 result — 3862ca4

Eval AUC 0.7667 (+0.0003); keep. Training took 26.6s and artifact was 34.7 MB. Additional leaf capacity under gradient sampling helps.

## Experiment 64 hypothesis

**Follow-up.** Raise `max_leaves` from 160 to 192. The 128-to-160 increase helped, and training still has over half of the one-minute allowance left. This tests whether the gain continues before the added complexity becomes overfit.

## Experiment 64 result — 753f495

Eval AUC 0.7668 (+0.0001); keep. Training took 28.7s and artifact was 39.2 MB. The gain is small but it uses the same simple model structure.

## Experiment 65 hypothesis

**Follow-up.** Raise `max_leaves` to 256 to test whether the gain from 160 to 192 is part of a broader capacity trend. Training still has substantial headroom. A larger step will show if AUC begins to decline from overfitting.

## Experiment 65 result — 08361ff

Eval AUC 0.7667 (-0.0001); discard. Training took 35.5s and artifact grew to 47.6 MB. The useful capacity range appears near 160–192 leaves.

## Experiment 66 hypothesis

**Follow-up.** Increase boosting rounds from 1,350 to 1,600 at 192 leaves. The larger trees may need a slightly longer fit to combine local patterns; [XGBoost's tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) emphasizes balancing model complexity, learning rate, and boosting rounds. Training should remain below one minute.

## Experiment 66 result — a005937

Eval AUC 0.7667 (-0.0001); discard. Training took 33.1s and artifact was 44.6 MB. Extra rounds do not improve the larger leaf-wise model.

## Experiment 67 hypothesis

**Follow-up.** Reduce boosting rounds to 1,100 at 192 leaves. The larger trees may saturate early, and removing late rounds would simplify the artifact if AUC is maintained or improved. This tests the other side of the 1,350-round setting.

## Experiment 67 result — d034468

Eval AUC 0.7668 (equal); keep for simplification. Training fell to 24.8s and artifact from 39.2 to 33.5 MB. The final 250 rounds were unnecessary.

## Experiment 68 hypothesis

**Ablation/simplification.** Reduce rounds further to 900 at 192 leaves. If AUC stays equal, the smaller model is preferable; if it falls, 1,100 rounds mark a useful lower bound.

## Experiment 68 result — 0d039d8

Eval AUC 0.7665 (-0.0003); discard. Training fell to 20.3s and artifact to 28.8 MB, but the AUC loss is too large for the simplification.

## Experiment 69 hypothesis

**Exploration.** Add an origin–carrier categorical interaction. The [Stanford departure-delay study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) analyzes carrier punctuality and airport context; it is plausible that a carrier's operation at a given origin has a distinct baseline delay risk. This pair has 1,551 training categories, much fewer than the failed 4,290-route feature. Use a train-fitted vocabulary and let XGBoost's [native categorical partitions](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) group values.

## Experiment 69 result — c2116cd

Eval AUC 0.7668 (equal); discard because six additional code lines, a 43.5 MB artifact, and slower training/evaluation brought no gain.

## Experiment 70 hypothesis

**Exploration.** Extract the minute component of scheduled departure time from its HHMM encoding. A [flight-delay feature-engineering study](https://www.mdpi.com/2079-9292/13/24/4910) explicitly separates scheduled time components. The existing raw HHMM value preserves overall time ordering, while the minute component could let trees recognize common schedule patterns without repeated time-specific splits.

## Experiment 70 result — df8406c

Eval AUC 0.7659 (-0.0009); discard. Training took 24.1s and artifact was 32.7 MB. Minute-of-hour patterns did not generalize beyond the raw scheduled time.

## Synthesis after 70 experiments

Best Eval AUC remains 0.7668 at d034468. Under gradient-based sampling, increasing the leaf cap from 128 to 160 and 192 helped; 256 leaves reversed the gain. At 192 leaves, 1,100 rounds matched 1,350 with a smaller model; 900 or 1,600 rounds lost accuracy. High-cardinality interactions, holiday proximity, finer histogram bins, and departure minute did not improve ranking. The current model seems to need enough local capacity but not extra raw features. Research pause: [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/release_3.3.0/parameter.html) defines `min_child_weight` as the minimum Hessian mass for a child, and its tuning guide treats it as a complexity control. Because gradient-based sampling changes which rows reach each tree, a lower child threshold may interact with the current leaf cap differently than the earlier upward test at 5.

## Experiment 71 hypothesis

**Exploration.** Lower `min_child_weight` from 1 to 0.5 with 192 leaves and 0.9 gradient-based sampling. [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/release_3.3.0/parameter.html) says lower thresholds permit smaller leaves. The current L1/L2 penalties may temper those leaves, while the model can capture useful local variation that the default threshold blocks.

## Experiment 71 result — 3f6136b

Eval AUC 0.7671 (+0.0003); keep. Training took 25.5s and artifact was 33.7 MB. Smaller Hessian-mass leaves help under the current sampling and regularization.

## Experiment 72 hypothesis

**Follow-up.** Lower `min_child_weight` to 0.25. The 1-to-0.5 decrease helped, and the strong L1/L2 leaf penalties may still prevent severe overfit. This tests whether the benefit continues into smaller leaves.

## Experiment 72 result — cedd6bc

Eval AUC 0.7667 (-0.0004); discard. Training took 24.4s and artifact was 33.8 MB. The child-weight optimum lies above 0.25.

## Experiment 73 hypothesis

**Follow-up.** Test `min_child_weight=0.75`, between the successful 0.5 and the former default 1. The 0.25 result shows that opening too many small leaves loses accuracy; a moderate threshold may balance local detail and regularization better.

## Experiment 73 result — 53ad35b

Eval AUC 0.7668 (-0.0003); discard. Training took 24.9s and artifact was 33.6 MB. Of the tested thresholds, 0.5 is best.

## Experiment 74 hypothesis

**Follow-up.** Raise `max_leaves` from 192 to 256 while keeping `min_child_weight=0.5`. The earlier 256-leaf trial used child weight 1 and lost slightly; allowing smaller valid leaves may let the additional capacity become useful.

## Experiment 74 result — e1770cb

Eval AUC 0.7668 (-0.0003); discard. Training took 29.1s and artifact grew to 40.5 MB. More leaves remain unhelpful even when smaller children are allowed.

## Plateau research after experiment 74

Three small discards followed the child-weight gain. [XGBoost's current parameter reference](https://xgboost.readthedocs.io/en/release_3.3.0/parameter.html) distinguishes column sampling once per tree from sampling at every node. This offers a different way to diversify splits without changing the trained feature set. It also documents categorical partition limits; the current eight-category limit could be revisited if node sampling fails.

## Experiment 75 hypothesis

**Exploration.** Set `colsample_bynode=0.9`. The earlier `colsample_bytree=0.9` reduced AUC, but node sampling allows different features within the same tree and may soften dependence on dominant scheduled time splits. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/release_3.3.0/parameter.html) describes this distinct sampling granularity.

## Experiment 75 result — 4437021

Eval AUC 0.7668 (-0.0003); discard. Training took 25.2s and artifact was 33.8 MB. Split-level feature randomness does not improve the current model.

## Experiment 76 hypothesis

**Exploration.** Lower `max_cat_threshold` from 8 to 4 with 192 leaves and child weight 0.5. [XGBoost's categorical parameter guide](https://xgboost.readthedocs.io/en/release_3.3.0/parameter.html#parameters-for-categorical-feature) says this limits category groups at each partition split to prevent overfitting. The larger leaves may use categorical features more finely than the early depth-wise model, so stronger partition regularization may help here.

## Experiment 76 result — aadf9c9

Eval AUC 0.7655 (-0.0016); discard. Training took 23.6s and artifact was 36.0 MB. The four-category cap is too restrictive.

## Research after experiment 76

[XGBoost documentation](https://xgboost.readthedocs.io/en/release_3.3.0/parameter.html) proposes class weighting for imbalanced labels, but `train.csv` has exactly 100,000 positive and 100,000 negative rows, so the standard negative/positive ratio is 1 and would leave training unchanged. The same guide defines `reg_alpha` as an L1 leaf penalty; under the newer sampling and child-weight setup, slightly less L1 may recover signal.

## Experiment 77 hypothesis

**Exploration.** Reduce `reg_alpha` from 10 to 8. The current lower child-weight setting permits smaller leaves, but L1=10 can zero their contributions. A modest reduction might retain useful local corrections without returning to the earlier, weaker alpha=5 setting.

## Experiment 77 result — 31e8c86

Eval AUC 0.7672 (+0.0001); keep. Training took 25.6s and artifact was 37.9 MB. Slightly less L1 helps under the current leaf settings.

## Experiment 78 hypothesis

**Follow-up.** Reduce `reg_alpha` further to 6. The 10-to-8 change helped, so this tests whether the current 192-leaf model can benefit from additional small corrections or begins to overfit as L1 falls.

## Experiment 78 result — 2456eab

Eval AUC 0.7662 (-0.0010); discard. Training took 24.4s and artifact grew to 43.5 MB. Reducing L1 this far overfits.

## Experiment 79 hypothesis

**Follow-up.** Test `reg_alpha=9`, between the successful 8 and former 10. The sharp loss at 6 indicates that the useful range is narrow; 9 may preserve most of the extra regularization while keeping some of the gain at 8.

## Experiment 79 result — e0e874d

Eval AUC 0.7673 (+0.0001); keep. Training took 25.4s and artifact was 35.7 MB. This is the best tested L1 setting under the current model.

## Experiment 80 hypothesis

**Exploration.** Reduce `reg_lambda` from 10 to 8 while keeping L1=9. L2 smooths leaf weights; the current smaller child-weight threshold changes how much support each leaf has, so a mild reduction may let useful local effects through. [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/release_3.3.0/parameter.html) describes L2 as a conservatism control.

## Experiment 80 result — 8e8551e

Eval AUC 0.7671 (-0.0002); discard. Training took 24.3s and artifact was 35.4 MB. Lower L2 did not help.

## Synthesis after 80 experiments

Best Eval AUC is 0.7673 at e0e874d. Since experiment 70, the key gain was reducing minimum child weight to 0.5 and then adjusting L1 to 9. Child weights 0.25 and 0.75, L1=6, extra leaf capacity, node-level column sampling, and a stricter categorical cap lost accuracy. The best model balances fine-grained leaves with strong leaf-weight penalties. [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/release_3.3.0/parameter.html) confirms that higher L2 makes leaf updates more conservative; with L2=8 worse, the next short test is L2=12.

## Experiment 81 hypothesis

**Follow-up.** Raise `reg_lambda` from 10 to 12 at the current best. The L2=8 result suggests a little more smoothing may help the smaller allowed leaves, while keeping the model structure and training time unchanged.

## Experiment 81 result — 0475c6f

Eval AUC 0.7664 (-0.0009); discard. Training took 25.3s and artifact was 35.6 MB. L2=10 remains best; both 8 and 12 were worse.

## Final summary

The best Eval AUC is **0.7673** at commit **e0e874d** on branch `sep29`, versus the starter's 0.7203. The selected model uses 1,100 XGBoost trees with leaf-wise growth, 192 leaves, learning rate 0.03, L1=9, L2=10, child weight 0.5, eight-category partition limit, and 0.9 gradient-based row sampling. Its row-by-row preparation adds day of year and seasonal sine/cosine features to the original flight fields. Its artifact was 35.7 MB and training took 25.4s in its measured run.

What worked: explicit seasonal timing, many low-step boosting rounds, stronger leaf-weight regularization, leaf-wise growth with an appropriate leaf cap, and mild gradient-based sampling. A lower child-weight threshold helped after sampling and larger leaves were established. What did not help: high-cardinality route and origin-carrier features, holiday proximity, minute-of-hour, cyclical departure time, finer histogram bins, aggressive categorical limits, column sampling, excessive leaves or rounds, and L2 settings on either side of 10. For a future experiment, investigate a genuinely new low-cardinality feature or a different training objective, with attention to train/eval transformation consistency and the one-minute fit limit. The harness evaluation is the only outcome measure used here.
