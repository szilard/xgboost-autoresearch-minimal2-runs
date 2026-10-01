# Research log — oct1

## Setup (2026-10-01)

- Started from the current `main` HEAD on a fresh `oct1` branch.
- `data/train.csv` and `data/eval.csv` are present; the starter `train.py` is unchanged.
- The starter `train.py` was committed at the current HEAD before the experiment clock started.

## Experiment 1 — baseline

- Commit: `92e43e6` (unchanged starter `train.py`).
- Eval AUC: `0.7203`; status: `ok`; runtime: `31.4s`.
- This establishes the reference score for later experiments.

## Research and hypothesis for Experiment 2

- XGBoost's tuning guide says lowering `eta` makes updates more conservative and should be paired with more boosting rounds; its parameter guide defines `learning_rate` as `eta` and describes how it shrinks each update ([tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html), [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- **Hypothesis (exploration):** the starter's 30 rounds at learning rate 0.1 may stop too early. Try 300 rounds at 0.05, keeping tree depth, features, and all other settings fixed, to test whether more gradual boosting improves Eval AUC.
- Result: Eval AUC `0.7348` (`+0.0145` vs baseline); run completed successfully in `33.3s`. Keep commit `1f23655`.

## Experiment 3 — more rounds at the improved learning rate

- Classification: follow-up to Experiment 2.
- **Hypothesis:** 300 trees at 0.05 improved AUC, and fit time remains well below the 60-second cap. Holding all else fixed, 600 trees may capture more signal; Eval AUC will reveal whether the longer schedule overfits.
- Result: Eval AUC `0.7359` (`+0.0011` vs Experiment 2); runtime `34.8s`, status `ok`. Keep commit `bdf3a7d`.

## Experiment 4 — deeper trees

- Classification: exploration of tree capacity.
- **Hypothesis:** with the improved 600-round schedule, increasing `max_depth` from 6 to 8 may model higher order interactions among departure time, day, carrier, and route. This raises model complexity and could overfit, so only the held-out Eval AUC decides whether to keep it.
- Result: Eval AUC `0.7321` (`-0.0038` vs current best); runtime `37.9s`, status `ok`. Discard commit `282ae7e`; revert to `bdf3a7d`.

## Experiment 5 — row subsampling

- Classification: exploration of regularization, motivated by the depth 8 overfit signal.
- The XGBoost parameter guide says `subsample` randomly samples training rows each round and can reduce overfitting ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- **Hypothesis:** setting `subsample=0.8` while holding the best tree schedule fixed may improve generalization by reducing correlation between trees; the AUC may also fall if the model needs all rows each round.
- Result: Eval AUC `0.7280` (`-0.0079` vs current best); runtime `35.4s`, status `ok`. Discard commit `2f7b4dc`; revert to `bdf3a7d`.

## Experiment 6 — scheduled departure time features

- Classification: exploration through row-local feature engineering.
- Scikit-learn's time-feature guide describes sine/cosine encodings as a way to represent periodic time without a discontinuity between the last and first hour; it also notes that tree models can already learn nonlinear time effects ([time-feature guide](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html)).
- **Hypothesis:** the source `CRSDepTime` is an HHMM number, whose numeric gaps do not equal elapsed minutes. Preserve that feature and add minutes since midnight plus sine/cosine over 1,440 minutes. These row-local features may make the time structure easier to split, including around midnight; the existing tree model may already be sufficient, so AUC will decide.
- Result: Eval AUC `0.7346` (`-0.0013` vs current best); runtime `41.4s`, status `ok`. Discard commit `4dd691e`; revert to `bdf3a7d`.

## Experiment 7 — route-relative scheduled time

- Classification: exploration through a train-fitted group lookup.
- Flight-delay research commonly combines scheduled departure time with origin and destination airport features ([Li et al., *Generation and prediction of flight delays in air transport*](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057)). The route-specific baseline below is an inference from those interactions, not a feature claimed by that paper.
- **Hypothesis:** flights on the same origin-destination route may follow recurring schedules. Fit each route's median scheduled departure time on `train.csv`, then add each row's deviation from that median. This lookup is constant per route at evaluation, including when `prepare` receives a single row.
- Result: Eval AUC `0.7355` (`-0.0004` vs current best); runtime `39.6s`, status `ok`. Discard commit `c1e35c0`; revert to `bdf3a7d`.

## Experiment 8 — one-hot splits for low-cardinality categories

- Classification: exploration of native categorical split strategy.
- XGBoost's categorical guide says `max_cat_to_onehot` selects one-hot splits below a category-count threshold and partition-based splits above it; partitioning groups categories with similar leaf values ([categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html), [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- **Hypothesis:** with threshold 32, low-cardinality month/day/carrier fields can use individual category tests while airport fields retain partitioned splits. This may preserve useful distinctions among small sets of operational categories.
- Result: Eval AUC `0.7236` (`-0.0123` vs current best); runtime `34.5s`, status `ok`. Discard commit `2efbf99`; revert to `bdf3a7d`.

## Experiment 9 — limit high-cardinality category partitions

- Classification: follow-up exploration of native categorical splits.
- The XGBoost parameter reference says `max_cat_threshold` limits the categories considered in each partition-based split and is intended to prevent overfitting ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- **Hypothesis:** keep the default one-hot/partition choice after the poor threshold-32 result, but set `max_cat_threshold=32` to constrain candidate partitions for high-cardinality airport fields and reduce overfitting.
- Result: Eval AUC `0.7373` (`+0.0014` vs prior best); runtime `34.8s`, status `ok`. Keep commit `142be3f`.

## Experiment 10 — tighter category partition cap

- Classification: follow-up to Experiment 9.
- **Hypothesis:** the cap of 32 improved AUC and produced a smaller artifact. Test `max_cat_threshold=16` with all other settings fixed; a tighter cap may further regularize the airport partitions, though it may remove useful groupings.
- Result: Eval AUC `0.7409` (`+0.0036` vs Experiment 9); runtime `35.7s`, status `ok`. Keep commit `7f62064`.

## Synthesis after 10 experiments

- **What helped:** increasing the boosting schedule from 30 trees at 0.1 to 600 trees at 0.05 raised AUC from `0.7203` to `0.7359`. Restricting categorical partition candidates improved it further: threshold 32 reached `0.7373`, and threshold 16 reached `0.7409`. The 16 threshold also reduced the artifact from 15.1 MB to 11.6 MB relative to the 600-tree unconstrained configuration.
- **What did not help:** depth 8, row subsampling at 0.8, extra minute-of-day/cyclic time features, route-median departure-time residual, and one-hot splits for categories below 32 all scored below the best kept model. The feature-engineering attempts added evaluation cost without improving AUC.
- **Current theory:** the 600-tree, depth-6, 0.05 schedule is useful, while partitioning high-cardinality categorical airport values with too many candidate categories overfits. More restrictive categorical partition search appears to generalize better; the low-cardinality one-hot split strategy was harmful here.
- **Best so far:** Eval AUC `0.7409`, commit `7f62064` (`max_cat_threshold=16`).
- **Next:** test a further cap reduction to 8, then explore a separate tree regularization parameter while keeping the best schedule and category cap fixed.

## Experiment 11 — further restrict category partitions

- Classification: follow-up to Experiment 10.
- **Hypothesis:** lowering `max_cat_threshold` from 16 to 8 may continue to reduce overfitting in high-cardinality airport categories; if it removes useful partitions, AUC will fall. Keep the 600-tree schedule and all other settings fixed.
- Result: Eval AUC `0.7415` (`+0.0006` vs Experiment 10); runtime `34.1s`, status `ok`. Keep commit `cbc12e8`.

## Experiment 12 — tighten category partition cap again

- Classification: follow-up to Experiment 11.
- **Hypothesis:** AUC increased at caps 32, 16, and 8, so test a cap of 4 to see whether the same regularization trend continues. Only `max_cat_threshold` changes; stronger restrictions may begin to underfit.
- Result: Eval AUC `0.7371` (`-0.0044` vs current best); runtime `34.5s`, status `ok`. Discard commit `50487c6`; revert to `cbc12e8`.

## Experiment 13 — minimum child weight

- Classification: exploration of tree complexity regularization.
- XGBoost documents `min_child_weight` as the minimum sum of instance Hessians allowed in a child, with larger values making the model more conservative ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html), [tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- **Hypothesis:** setting it to 5 instead of the default 1 will discourage small, weakly supported leaves and may complement the successful cap on categorical partitions. Keep all other parameters fixed.
- Result: Eval AUC `0.7431` (`+0.0016` vs prior best); runtime `35.3s`, status `ok`. Keep commit `99e4b1d`.

## Experiment 14 — stronger minimum child weight

- Classification: follow-up to Experiment 13.
- **Hypothesis:** because `min_child_weight=5` improved AUC, test 10 to see if additional constraints on small leaves help further. This may also reduce useful detail, so compare only via the harness Eval AUC.
- Result: Eval AUC `0.7436` (`+0.0005` vs Experiment 13); runtime `34.0s`, status `ok`. Keep commit `a0c57b5`.

## Experiment 15 — increase minimum child weight to 20

- Classification: follow-up to Experiment 14.
- **Hypothesis:** the improvement from 5 to 10 suggests a useful regularization trend. Test 20 as a larger step; if AUC falls, retain 10 as the best balance.
- Result: Eval AUC `0.7439` (`+0.0003` vs Experiment 14); runtime `34.2s`, status `ok`. Keep commit `ac677a6`.

## Experiment 16 — minimum child weight 40

- Classification: follow-up to Experiment 15.
- **Hypothesis:** AUC has risen at 5, 10, and 20. Test 40 to find whether the improvement continues or stronger constraints begin to underfit. Change only `min_child_weight`.
- Result: Eval AUC `0.7456` (`+0.0017` vs Experiment 15); runtime `34.0s`, status `ok`. Keep commit `602b949`.

## Experiment 17 — minimum child weight 80

- Classification: follow-up to Experiment 16.
- **Hypothesis:** the consistent gains at 5, 10, 20, and 40 suggest the leaves are still too small. Test 80; if the AUC falls, the best range is below that.
- Result: Eval AUC `0.7450` (`-0.0006` vs current best); runtime `34.0s`, status `ok`. Discard commit `9998dbc`; revert to `602b949`.

## Experiment 18 — split loss threshold

- Classification: exploration of a separate tree regularization control.
- XGBoost defines `gamma` as the minimum loss reduction needed for a split; larger values make the model more conservative ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html), [tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- **Hypothesis:** with `min_child_weight=40` already helping, `gamma=1` may remove low-gain splits and further improve generalization. Keep all other settings fixed.
- Result: Eval AUC `0.7373` (`-0.0083` vs current best); runtime `33.8s`, status `ok`. Discard commit `da96cdf`; revert to `602b949`.

## Experiment 19 — smaller split loss threshold

- Classification: follow-up to Experiment 18.
- **Hypothesis:** `gamma=1` was too restrictive alongside `min_child_weight=40`; a smaller `gamma=0.1` may remove only marginal splits while preserving useful structure. Hold all other settings fixed.
- Result: Eval AUC `0.7453` (`-0.0003` vs current best); runtime `34.2s`, status `ok`. Discard commit `2b08bed`; revert to `602b949`.

## Experiment 20 — L2 leaf weight regularization

- Classification: exploration of a separate regularization parameter.
- XGBoost describes `reg_lambda` as L2 regularization on leaf weights; increasing it makes the model more conservative ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- **Hypothesis:** with the best `min_child_weight=40` and `max_cat_threshold=8`, increase `reg_lambda` from its default 1 to 5. This may smooth leaf weights and improve ranking generalization, though it may also shrink useful signal.
- Result: Eval AUC `0.7453` (`-0.0003` vs current best); runtime `34.5s`, status `ok`. Discard commit `044dbc7`; revert to `602b949`.

## Synthesis after 20 experiments

- **What helped most:** a slower 600-tree schedule and constrained categorical partitions were the largest gains. `max_cat_threshold=8` improved AUC over 16 and 32, while 4 underfit. Raising `min_child_weight` from 1 to 40 yielded a steady series of gains, reaching the current best `0.7456`; 80 slipped slightly.
- **What did not help:** deeper trees, row subsampling, cyclic/route-relative features, and a broad one-hot threshold all reduced AUC. `gamma=1` hurt substantially, `gamma=0.1` was nearly neutral but below best, and `reg_lambda=5` also came in just below best.
- **Current theory:** the strongest gains come from curbing small, high-cardinality splits, with a moderate-to-high `min_child_weight` and a low `max_cat_threshold`. Additional shrinkage from gamma or L2 may be redundant with those controls.
- **Best so far:** Eval AUC `0.7456`, commit `602b949` (`max_cat_threshold=8`, `min_child_weight=40`, 600 trees, depth 6, learning rate 0.05).
- **Next:** narrow the minimum-child-weight search around 40, then test a modestly shallower tree depth with the current best regularization.

## Experiment 21 — minimum child weight 60

- Classification: follow-up to the promising `min_child_weight=40` result.
- **Hypothesis:** 40 improved AUC while 80 declined slightly; test the midpoint 60 to check whether the best lies between them. Keep all other settings fixed.
- Result: Eval AUC `0.7468` (`+0.0012` vs prior best); runtime `34.1s`, status `ok`. Keep commit `bd6ccb9`.

## Experiment 22 — minimum child weight 50

- Classification: follow-up around the new best.
- **Hypothesis:** the midpoint 60 improved over both 40 and 80. Test 50 to check whether the local optimum is lower than 60; change only this parameter.
- Result: Eval AUC `0.7453` (`-0.0015` vs current best); runtime `34.5s`, status `ok`. Discard commit `eee859a`; revert to `bd6ccb9`.

## Experiment 23 — minimum child weight 70

- Classification: follow-up around the `min_child_weight=60` best.
- **Hypothesis:** 50 was worse than 60, while 80 was slightly worse than 60. Test 70 to check if the score remains strong toward the upper side of the local peak.
- Result: Eval AUC `0.7459` (`-0.0009` vs current best); runtime `34.4s`, status `ok`. Discard commit `90822ae`; revert to `bd6ccb9`.

## Experiment 24 — shallower trees with current regularization

- Classification: exploration of tree capacity.
- The earlier depth-8 experiment hurt, but it preceded the successful categorical and leaf constraints. **Hypothesis:** under the current stronger regularization (`min_child_weight=60`, `max_cat_threshold=8`), depth 5 may reduce unnecessary interactions and improve generalization. Change only `max_depth`.
- Result: Eval AUC `0.7402` (`-0.0066` vs current best); runtime `33.7s`, status `ok`. Discard commit `341a649`; revert to `bd6ccb9`.

## Experiment 25 — more rounds with stronger regularization

- Classification: follow-up to the successful 600-tree schedule under the newer constraints.
- **Hypothesis:** the 600-tree schedule was selected before `min_child_weight=60` and `max_cat_threshold=8`. Those constraints make each tree less flexible, so 800 trees at learning rate 0.05 may capture additional signal without the overfit seen in less constrained models. Change only `n_estimators`.
- Result: Eval AUC `0.7489` (`+0.0021` vs prior best); runtime `35.3s`, status `ok`. Keep commit `2b29a1f`.

## Experiment 26 — extend the constrained boosting schedule

- Classification: follow-up to Experiment 25.
- **Hypothesis:** 800 rounds improved AUC while staying far below the training limit. Test 1,000 with the same learning rate and regularization to check whether the score is still rising.
- Result: Eval AUC `0.7496` (`+0.0007` vs Experiment 25); runtime `42.3s`, status `ok`. Keep commit `919fcc3`.

## Experiment 27 — extend to 1,200 rounds

- Classification: follow-up to Experiment 26.
- **Hypothesis:** AUC rose again at 1,000 rounds, with training still within the limit. Test 1,200 rounds to check whether additional constrained boosting continues to improve the ranking.
- Result: Eval AUC `0.7502` (`+0.0006` vs Experiment 26); runtime `37.1s`, status `ok`. Keep commit `b4a1b99`.

## Experiment 28 — extend to 1,400 rounds

- Classification: follow-up to Experiment 27.
- **Hypothesis:** Eval AUC is still rising at 1,200 rounds, with per-run time below 40 seconds. Test 1,400 at the same learning rate and regularization to see if the diminishing gains continue.
- Result: Eval AUC `0.7504` (`+0.0002` vs Experiment 27); runtime `38.3s`, status `ok`. Keep commit `100c89b`.

## Experiment 29 — extend to 1,600 rounds

- Classification: follow-up to Experiment 28.
- **Hypothesis:** 1,400 rounds gave a small gain and remained within limits. One more 200-tree increase will test whether the score keeps rising or begins to overfit.
- Result: Eval AUC `0.7503` (`-0.0001` vs current best); runtime `38.7s`, status `ok`. Discard commit `7b207ee`; revert to `100c89b`.

## Experiment 30 — smaller steps with more rounds

- Classification: exploration of a matched boosting schedule.
- XGBoost's tuning guide recommends reducing `eta` while increasing the number of rounds; the parameter guide says `eta` shrinks each update ([tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html), [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- **Hypothesis:** reduce learning rate from 0.05 to 0.03 and increase rounds from 1,400 to 2,300. Their products are similar (`70` vs `69`), so this tests whether smaller updates improve generalization at roughly comparable cumulative shrinkage. Keep all other settings fixed.
- Result: Eval AUC `0.7508` (`+0.0004` vs prior best); runtime `43.5s`, status `ok`. Keep commit `ce38e68`.

## Synthesis after 30 experiments

- **What helped:** compared with baseline `0.7203`, the best AUC is now `0.7508`. The largest model improvements came from limiting categorical partition candidates (`max_cat_threshold=8`) and raising `min_child_weight` to about 60. With those constraints, increasing rounds continued to help through 1,400 trees at learning rate 0.05; 1,600 was effectively flat. A matched smaller-step schedule (`2,300` trees at `0.03`) improved the score again.
- **What did not help:** depth 5 or 8, row subsampling, broad one-hot category splits, added time/route features, `gamma`, and `reg_lambda=5` all scored below the kept model. Stronger leaf constraints also peaked: 50, 70, and 80 were below 60.
- **Current theory:** constraining category partitions and small leaves reduces overfit enough to support more boosting rounds. Smaller updates may yield a further gain at similar cumulative learning-rate scale.
- **Best so far:** Eval AUC `0.7508`, commit `ce38e68` (`max_cat_threshold=8`, `min_child_weight=60`, depth 6, learning rate 0.03, 2,300 trees).
- **Next:** test a longer schedule at 0.03, then consider a matched smaller learning rate if the gains continue. Keep monitoring the 60-second training and 5-minute evaluation caps.

## Experiment 31 — extend the 0.03 schedule

- Classification: follow-up to Experiment 30.
- **Hypothesis:** the 2,300-tree, 0.03 schedule beat 1,400 trees at 0.05. Increase only the round count to 2,600 to test whether the lower-rate schedule still benefits from more boosting.
- Result: Eval AUC `0.7507` (`-0.0001` vs current best); runtime `43.9s`, status `ok`. Discard commit `1fa9e7e`; revert to `ce38e68`.

## Experiment 32 — smaller updates at matched schedule scale

- Classification: follow-up to Experiment 30's smaller-step improvement.
- **Hypothesis:** lower the learning rate from 0.03 to 0.02 and raise rounds to 3,450, keeping the product near 69 as in the prior schedules. This checks whether smaller individual updates improve ranking without substantially changing total step size. The 2,600-round result at 0.03 was flat, so only the new lower-rate schedule is being tested.
- Result: Eval AUC `0.7505` (`-0.0003` vs current best); runtime `47.9s`, status `ok`. Discard commit `2f5bb54`; revert to `ce38e68`.

## Experiment 33 — intermediate learning rate

- Classification: follow-up to the matched smaller-step schedules.
- **Hypothesis:** `0.03` at 2,300 rounds scored 0.7508, while `0.02` at 3,450 scored 0.7505. Test the midpoint `0.025` with 2,760 rounds (product 69) to see whether the best lies between those rates.
- Result: Eval AUC `0.7500` (`-0.0008` vs current best); runtime `45.2s`, status `ok`. Discard commit `c6656a5`; revert to `ce38e68`.

## Experiment 34 — explicit origin-destination category

- Classification: exploration of a joint route feature after the learning-rate plateau.
- A flight-delay study's review lists origin-destination pairs among features used to model network effects ([Li et al., *Generation and prediction of flight delays in air transport*](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057)). **Inference:** a single directional `Origin-Dest` category may expose route-specific behavior that separate airport categories do not represent as directly.
- **Hypothesis:** add `Route` as a native categorical feature with levels fitted on `train.csv`; retain Origin and Dest, and rely on the already successful `max_cat_threshold=8` to constrain category partitioning. This may capture useful route interactions with the current schedule.
- Result: Eval AUC `0.7499` (`-0.0009` vs current best); runtime `70.4s`, status `ok`. Evaluation time rose to `49.0s`. Discard commit `0d79c54`; revert to `ce38e68`.

## Experiment 35 — coarse scheduled departure block

- Classification: exploration of a compact time feature after the cyclic encoding result was negative.
- A flight-delay study identifies time-of-day effects and represents departure hours with busy/off-busy periods ([Zhang et al., *A multi-step airport delay prediction model*](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12071)). **Inference:** six four-hour blocks may expose broad schedule congestion patterns while keeping the feature small.
- **Hypothesis:** derive a 0–5 departure block from scheduled HHMM, fit its categorical levels on `train.csv`, and retain the raw time. The native category may make airport-by-time effects easier to learn than raw HHMM alone.
- Result: Eval AUC `0.7504` (`-0.0004` vs current best); runtime `50.0s`, status `ok`; evaluation took `38.6s`. Discard commit `86df5da`; revert to `ce38e68`.

## Experiment 36 — origin by departure block

- Classification: exploration of a spatial-temporal interaction.
- The aviation study used airport delay values by hour and describes spatial dependencies between airports ([Zhang et al.](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12071)). **Inference:** an origin-specific time block can expose that airport congestion patterns differ across the day.
- **Hypothesis:** combine each origin airport with a four-hour scheduled departure block as a single native categorical feature. Fit category levels on `train.csv`; the `max_cat_threshold=8` cap will restrict partitioning. This is a row-local interaction and does not use target aggregates.
- Result: Eval AUC `0.7500` (`-0.0008` vs current best); runtime `56.4s`, status `ok`; evaluation took `42.6s`. Discard commit `f327baa`; revert to `ce38e68`.

## Experiment 37 — loss-guided tree growth

- Classification: exploration of a different tree growth strategy after three feature-engineering discards.
- XGBoost documents `lossguide` as expanding nodes with the highest loss change; it requires `hist` or `approx`, and `max_leaves` caps tree size ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html), [Python API](https://xgboost.readthedocs.io/en/stable/python/python_api.html)).
- **Hypothesis:** use histogram `lossguide` growth with unlimited depth and at most 64 leaves, matching the leaf capacity of a balanced depth-6 tree. The strategy may allocate splits more efficiently to high-value regions of the feature space. Keep the best boosting schedule and regularization fixed.
- Result: Eval AUC `0.7524` (`+0.0016` vs prior best); runtime `50.7s`, status `ok`; training `18.4s`, evaluation `31.1s`. Keep commit `7824878`.

## Experiment 38 — increase loss-guided leaf capacity

- Classification: follow-up to Experiment 37.
- **Hypothesis:** `lossguide` with 64 leaves improved AUC over depthwise growth. Test 128 leaves to see whether more high-value localized splits help; `min_child_weight=60` and `max_cat_threshold=8` remain fixed to control complexity.
- Result: Eval AUC `0.7474` (`-0.0050` vs current best); runtime `65.7s`, status `ok`; training `33.7s`. Discard commit `26bc48b`; revert to `7824878`.

## Experiment 39 — reduce loss-guided leaves

- Classification: follow-up to Experiment 38.
- **Hypothesis:** 128 leaves overfit relative to the 64-leaf best. Test 32 leaves to see whether a smaller loss-guided tree improves generalization; keep the growth policy and all other settings fixed.
- Result: Eval AUC `0.7531` (`+0.0007` vs Experiment 37); runtime `43.7s`, status `ok`; training `12.3s`. Keep commit `e06bcc7`.

## Experiment 40 — intermediate loss-guided leaf count

- Classification: follow-up to Experiment 39.
- **Hypothesis:** 32 leaves improved over 64, while 128 was worse. Test 48 leaves to locate the capacity sweet spot between the two better candidates; keep all other settings fixed.
- Result: Eval AUC `0.7537` (`+0.0006` vs prior best); runtime `48.0s`, status `ok`; training `16.5s`, evaluation `31.5s`. Keep commit `d0c8717`.

## Synthesis after 40 experiments

- The best score has risen from baseline `0.7203` to `0.7537` (`+0.0334` AUC). The largest reliable gains came from increasing the boosting schedule, tuning `max_cat_threshold` down to 8, increasing `min_child_weight` to 60, and switching to `lossguide` tree growth.
- Reducing the learning rate to `0.03` and increasing the number of trees to 2300 helped. Under `lossguide`, 48 leaves is currently best: 32 scored `0.7531`, 48 scored `0.7537`, 64 scored `0.7524`, and 128 scored `0.7474`.
- Several added time, route, and origin-time features failed to improve the validation score. The tested `gamma` and `reg_lambda` changes also did not beat the selected settings.
- Current working theory: the useful capacity depends on letting histogram loss-guided growth allocate a moderate number of splits to the most valuable regions, while keeping categorical partitioning and child size constrained. The neighborhood around 48 leaves is not fully resolved, so test nearby capacities before changing another parameter family.
- Next: test 56 leaves against the fixed best configuration. If it loses, probe 40 leaves; if it wins, refine the interval. Then consider whether `min_child_weight` or `max_cat_threshold` should be retuned under `lossguide`.

## Experiment 41 — 56 loss-guided leaves

- Classification: follow-up in the neighborhood of the current best leaf count.
- **Hypothesis:** 56 leaves may retain the 48-leaf model's generalization while adding useful capacity; all other settings stay fixed.
- Result: Eval AUC `0.7528` (`-0.0009` vs current best); runtime `49.9s`, status `ok`; training `18.6s`, evaluation `31.3s`. Discard commit `c47499d`; revert to `d0c8717`.

## Experiment 42 — 40 loss-guided leaves

- Classification: follow-up on the lower side of the current best leaf count.
- **Hypothesis:** if 56 leaves adds excess capacity, 40 leaves may be competitive with 48 while reducing tree size; keep all other parameters fixed.
- Result: Eval AUC `0.7537` (tied with the current best at displayed precision); runtime `45.2s`, status `ok`; training `14.2s`, evaluation `31.1s`, artifact `16.0 MB`. Keep commit `8d3a478` as a simpler, faster model than the 48-leaf candidate (`18.6 MB`, `16.5s` training).

## Experiment 43 — 44 loss-guided leaves

- Classification: follow-up to the 40- and 48-leaf candidates, which tied at displayed AUC.
- **Hypothesis:** 44 leaves may retain the tied best score while narrowing the capacity interval; all other settings stay fixed. If it also ties, prefer the smallest tied model.
- Result: Eval AUC `0.7541` (`+0.0004` vs prior best); runtime `47.4s`, status `ok`; training `15.9s`, evaluation `31.5s`. Keep commit `8b5fa9f`.

## Experiment 44 — 42 loss-guided leaves

- Classification: follow-up to the 44-leaf improvement, testing a smaller model close to the previous 40-leaf candidate.
- **Hypothesis:** 42 leaves may preserve the `0.7541` result with a smaller artifact and less training work; all other settings stay fixed.
- Result: Eval AUC `0.7527` (`-0.0014` vs current best); runtime `47.1s`, status `ok`; training `15.9s`, evaluation `31.2s`. Discard commit `61ef4cc`; revert to `8b5fa9f`.

## Experiment 45 — 46 loss-guided leaves

- Classification: follow-up between the 44-leaf best and the lower-scoring 48-leaf candidate.
- **Hypothesis:** 46 leaves may capture capacity between those results while preserving the gain at 44; keep all other settings fixed.
- Result: Eval AUC `0.7536` (`-0.0005` vs current best); runtime `47.2s`, status `ok`; training `15.5s`, evaluation `31.6s`. Discard commit `63bef7e`; revert to `8b5fa9f`.

## Experiment 46 — 43 loss-guided leaves

- Classification: follow-up to test whether one fewer leaf than the current best keeps its AUC with a smaller model.
- **Hypothesis:** 43 leaves may retain the `0.7541` score from 44 leaves while slightly reducing model size and training time; all other settings stay fixed.
- Result: Eval AUC `0.7529` (`-0.0012` vs current best); runtime `46.7s`, status `ok`; training `15.4s`, evaluation `31.3s`. Discard commit `26f58b8`; revert to `8b5fa9f`.

## Experiment 47 — tree-level column sampling

- Classification: exploration of a new regularization direction after narrowing the loss-guided leaf range.
- The XGBoost [parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `colsample_bytree` as the fraction of columns sampled for each tree, while its [tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) list it as a way to add randomness to control overfitting. **Inference:** sampling 80% of the eight available features may reduce dependence on the strongest columns while preserving most feature choices.
- **Hypothesis:** set `colsample_bytree=0.8` with the 44-leaf best configuration unchanged otherwise. This isolates whether modest tree-level feature sampling improves generalization.
- Result: Eval AUC `0.7530` (`-0.0011` vs current best); runtime `45.7s`, status `ok`; training `14.3s`, evaluation `31.4s`. Discard commit `acae50a`; revert to `8b5fa9f`.

## Experiment 48 — gentler tree-level column sampling

- Classification: follow-up to Experiment 47.
- **Hypothesis:** `colsample_bytree=0.8` underperformed the full-feature model. At eight input columns, 0.9 is a gentler sampling ratio and may retain most useful splits while adding less tree-to-tree dependence. Test `0.9`, keeping the 44-leaf configuration and every other parameter fixed.
- Result: Eval AUC `0.7533` (`-0.0008` vs current best); runtime `46.1s`, status `ok`; training `14.6s`, evaluation `31.6s`. Discard commit `7fdaa25`; revert to `8b5fa9f`.

## Experiment 49 — lower child-weight threshold under lossguide

- Classification: follow-up retuning after changing tree growth policy.
- The XGBoost [parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) explains that `min_child_weight` limits the Hessian weight needed for a child and that larger values make splitting more conservative. It was tuned to 60 under depthwise growth; **inference:** loss-guided growth and a 44-leaf cap may use moderately smaller child thresholds differently.
- **Hypothesis:** test `min_child_weight=50` with all current best settings unchanged otherwise. This checks whether allowing somewhat smaller children improves the loss-guided model.
- Result: Eval AUC `0.7545` (`+0.0004` vs prior best); runtime `46.9s`, status `ok`; training `15.1s`, evaluation `31.7s`. Keep commit `87c47e4`.

## Experiment 50 — child-weight midpoint under lossguide

- Classification: follow-up to the new `min_child_weight=50` best.
- **Hypothesis:** try `min_child_weight=55` between the new 50 setting and the earlier 60 setting. This may preserve the gain from lowering the threshold while checking for a nearby optimum; leave all other parameters fixed.
- Result: Eval AUC `0.7540` (`-0.0005` vs current best); runtime `46.3s`, status `ok`; training `15.0s`, evaluation `31.3s`. Discard commit `f113683`; revert to `87c47e4`.

## Synthesis after 50 experiments

- The best score is `0.7545` at commit `87c47e4`, up `0.0342` from the `0.7203` baseline. Gains came from longer, lower-rate boosting, `max_cat_threshold=8`, and moving to `lossguide` with a moderate leaf cap and smaller child-weight threshold.
- In the latest growth-policy search, 44 leaves scored `0.7541`; 40 tied the prior `0.7537` score with a smaller artifact, while 42 and 43 were worse. Larger tested caps (46, 48, 56, 64, 128) did not beat 44. `min_child_weight=50` then improved to `0.7545`; 55 scored `0.7540`, and 60 had scored `0.7541` under this growth policy.
- Column sampling at 0.8 and 0.9 did not help. The earlier added time and route features, several regularization changes, and depthwise growth variants also failed to beat the current best.
- Current theory: the model benefits from loss-guided allocation of a moderate number of leaves, constrained categorical splits, and enough child weight to avoid brittle small leaves. The lower child-weight boundary under `lossguide` is still unresolved.
- Next: test `min_child_weight=45` with all other settings fixed. If it improves, explore nearby lower values; otherwise retain 50 and retune categorical split capacity under the loss-guided setup.

## Experiment 51 — lower child weight under lossguide

- Classification: follow-up to the `min_child_weight=50` best.
- **Hypothesis:** test `min_child_weight=45`, between the new 50 best and the earlier 40 result from depthwise growth. A lower threshold may let `lossguide` refine high-value regions while the 44-leaf cap contains complexity. Keep other settings fixed.
- Result: Eval AUC `0.7543` (`-0.0002` vs current best); runtime `47.2s`, status `ok`; training `15.7s`, evaluation `31.5s`. Discard commit `8d8238e`; revert to `87c47e4`.

## Experiment 52 — child weight just below 50

- Classification: follow-up to Experiments 49 and 51.
- **Hypothesis:** `min_child_weight=48` may preserve or improve the `0.7545` score while allowing slightly more splitting than 50. All other settings stay fixed.
- Result: Eval AUC `0.7543` (`-0.0002` vs current best); runtime `46.5s`, status `ok`; training `15.1s`, evaluation `31.4s`. Discard commit `5876c2f`; revert to `87c47e4`.

## Experiment 53 — raise categorical partition cap under lossguide

- Classification: follow-up retuning of categorical split capacity under the new growth policy.
- XGBoost's [categorical parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) define `max_cat_threshold` as the maximum categories considered in a partition-based split and describe it as an overfitting control. **Inference:** the loss-guided model may benefit from considering more categories than the earlier depthwise model, while the 44-leaf cap limits total structure.
- **Hypothesis:** increase `max_cat_threshold` from 8 to 16, keeping the current best's 44 leaves and `min_child_weight=50` fixed. Earlier depthwise runs favored 8 over 16, so this checks for an interaction with loss-guided growth.
- Result: Eval AUC `0.7477` (`-0.0068` vs current best); runtime `48.4s`, status `ok`; training `16.8s`, evaluation `31.7s`, artifact `43.4 MB`. Discard commit `6a14f23`; revert to `87c47e4`.

## Experiment 54 — one-hot splits for low-cardinality features

- Classification: follow-up on native categorical split handling.
- XGBoost's [categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains that `max_cat_to_onehot` selects one-hot versus partition-based splits by category count. **Inference:** setting it to 8 may allow simpler one-vs-rest splits for only the low-cardinality calendar features, while leaving high-cardinality airport features partitioned. A prior value of 32 underperformed, so test the narrower threshold.
- **Hypothesis:** set `max_cat_to_onehot=8` with the current best's `max_cat_threshold=8`, 44 leaves, and child weight 50 unchanged. This isolates a limited one-hot treatment for small categories.
- Result: Eval AUC `0.7537` (`-0.0008` vs current best); runtime `46.9s`, status `ok`; training `15.1s`, evaluation `31.7s`. Discard commit `2fc9ee6`; revert to `87c47e4`.

## Experiment 55 — include Month in one-hot threshold

- Classification: follow-up to Experiment 54.
- **Hypothesis:** raise `max_cat_to_onehot` from 8 to 16. This should include Month (12 levels) along with DayOfWeek while leaving the high-cardinality airport features on partition-based splits. It tests a limited one-hot subset after 8 scored below the best.
- Result: Eval AUC `0.7531` (`-0.0014` vs current best); runtime `46.4s`, status `ok`; training `14.9s`, evaluation `31.4s`. Discard commit `14cadb3`; revert to `87c47e4`.

## Experiment 56 — cross-fitted delay-rate features

- Classification: exploration of target-derived aggregate features after native categorical variants plateaued.
- Scikit-learn's [target-encoder guide](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html) recommends cross-fitting training encodings so each row uses target statistics from other folds; the [API docs](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html) describe smoothing toward the global target mean. **Inference:** smoothed rates for Origin, Dest, carrier, and route could expose airport/airline delay tendencies that native category splits have not represented as directly.
- **Hypothesis:** add four smoothed rates (smoothing strength 50) using five stratified folds for train-row encodings and full `train.csv` lookups for eval rows. Keep the original native categorical features and best hyperparameters. This uses no eval or held-out labels, avoids each training row's own target in its encoding, and keeps all learned lookups fixed at inference time.
- Result: Eval AUC `0.7522` (`-0.0023` vs current best); runtime `64.4s`, status `ok`; training `15.7s`, evaluation `48.7s`, artifact `25.6 MB`. Discard commit `523a3aa`; revert to `87c47e4`.

## Experiment 57 — remove sparse route target rate

- Classification: ablation of Experiment 56's target-derived feature family.
- **Hypothesis:** the route rate may be noisy because many routes have few training rows. Remove only that feature and retain the denser Origin, Dest, and Carrier rates; keep the same five-fold cross-fitting and smoothing so the experiment isolates route-rate value.
- Result: Eval AUC `0.7541` (`-0.0004` vs current best); runtime `55.2s`, status `ok`; training `14.7s`, evaluation `40.5s`, artifact `22.3 MB`. Discard commit `1306688`; revert to `87c47e4`.

## Experiment 58 — airport-only target rates

- Classification: ablation of Experiment 57's target-derived features.
- **Hypothesis:** removing the Carrier rate may retain useful airport-level delay tendencies while dropping a redundant signal already available in native `UniqueCarrier`. Keep the Origin and Dest rates with the same cross-fitting and smoothing.
- Result: Eval AUC `0.7544` (`-0.0001` vs current best); runtime `52.7s`, status `ok`; training `14.6s`, evaluation `38.1s`, artifact `20.9 MB`. Discard commit `18ff1a9`; revert to `87c47e4`.

## Experiment 59 — Origin-only target rate

- Classification: ablation of the airport-rate feature pair.
- **Hypothesis:** the Origin delay rate may carry most of the airport-level signal because it reflects departure-side operating conditions. Keep only Origin's smoothed, cross-fitted rate and the native features; retain the same folds and smoothing.
- Result: Eval AUC `0.7545` (tied with the current best at displayed precision); runtime `49.3s`, status `ok`; training `14.5s`, evaluation `34.8s`, artifact `20.2 MB`. Discard commit `c04916c`; it matched the baseline score while adding preprocessing and runtime.

## Experiment 60 — Dest-only target rate

- Classification: final airport-rate ablation in this feature family.
- **Hypothesis:** the Dest rate may capture network-related delay patterns not represented by the departure airport. Test only its smoothed, cross-fitted rate with the native features; keep the same folds and smoothing.
- Result: Eval AUC `0.7537` (`-0.0008` vs current best); runtime `50.4s`, status `ok`; training `15.6s`, evaluation `34.8s`, artifact `19.4 MB`. Discard commit `4acab1e`; revert to `87c47e4`.

## Synthesis after 60 experiments

- The best remains `0.7545` at commit `87c47e4`, `+0.0342` over the `0.7203` baseline. The useful changes are the longer, lower-rate boosting schedule, `max_cat_threshold=8`, and loss-guided growth with 44 leaves and `min_child_weight=50`.
- Nearby leaf counts did not beat 44, and 50 child weight beat 45, 48, 55, and the prior 60 setting under `lossguide`. A larger categorical partition cap and limited one-hot thresholds also lost.
- Five-fold cross-fitted delay-rate features were leakage-controlled as recommended by the scikit-learn documentation, but all combinations scored below the native-feature best. Removing Route and Carrier rates moved the score closer; Origin alone tied at displayed precision, but each target-rate version added model and evaluation cost without improving AUC.
- Current theory: the native categorical treatment and selected tree structure already capture most useful airport/carrier group effects. Avoid more target-rate variants unless there is a clear way to reduce their per-row evaluation cost.
- Next: explore histogram resolution for the two numeric features (`CRSDepTime` and `Distance`) while holding the best tree settings fixed; XGBoost's `max_bin` controls numeric cut resolution for histogram growth.

## Experiment 61 — finer histogram bins

- Classification: exploration of numeric split resolution.
- XGBoost's [parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) say `max_bin` controls the number of discrete bins for continuous features and that higher values can improve split optimality at higher compute cost. **Inference:** more cut points may help the model capture useful scheduled-time or distance thresholds.
- **Hypothesis:** raise `max_bin` from its default 256 to 512 while keeping the current best's 44-leaf and 50-child-weight settings fixed. This tests finer numeric resolution without changing model capacity.
- Result: Eval AUC `0.7529` (`-0.0016` vs current best); runtime `47.2s`, status `ok`; training `15.7s`, evaluation `31.4s`, artifact `17.8 MB`. Discard commit `2c5ab63`; revert to `87c47e4`.

## Experiment 62 — coarser histogram bins

- Classification: follow-up on Experiment 61.
- **Hypothesis:** since 512 bins underperformed, test `max_bin=128` to see whether coarser numeric cuts regularize the limited numeric features. Keep all other settings fixed.
- Result: Eval AUC `0.7542` (`-0.0003` vs current best); runtime `46.6s`, status `ok`; training `15.3s`, evaluation `31.3s`, artifact `18.1 MB`. Discard commit `bd165ba`; revert to `87c47e4`.

## Experiment 63 — intermediate histogram resolution

- Classification: follow-up to Experiments 61 and 62.
- **Hypothesis:** 128 bins was close to the default 256-bin best, while 512 was worse. Test `max_bin=192` to check whether a middle resolution retains the score with slightly coarser numeric cuts.
- Result: Eval AUC `0.7539` (`-0.0006` vs current best); runtime `46.2s`, status `ok`; training `14.8s`, evaluation `31.4s`, artifact `17.9 MB`. Discard commit `d1aba92`; revert to `87c47e4`.

## Experiment 64 — light L1 leaf-weight regularization

- Classification: exploration of a regularization parameter not yet tested.
- XGBoost's [parameter guide](https://xgboost.readthedocs.io/en/latest/parameter.html) describes `reg_alpha` as L1 regularization on leaf weights; higher values make the model more conservative. **Inference:** a small value may suppress weak leaf contributions in the long 2300-tree model without materially changing the stronger splits.
- **Hypothesis:** test `reg_alpha=0.1` with the current 44-leaf, child-weight-50 configuration unchanged otherwise.
- Result: Eval AUC `0.7546` (`+0.0001` vs prior best); runtime `47.4s`, status `ok`; training `15.6s`, evaluation `31.7s`, artifact `19.1 MB`. Keep commit `a3fa724`.

## Experiment 65 — stronger L1 regularization

- Classification: follow-up to the `reg_alpha=0.1` improvement.
- **Hypothesis:** test `reg_alpha=0.5` to see whether stronger shrinkage improves on the new `0.7546` best; leave all other settings fixed.
- Result: Eval AUC `0.7581` (`+0.0035` vs prior best); runtime `48.3s`, status `ok`; training `16.7s`, evaluation `31.7s`, artifact `27.3 MB`. Keep commit `0270f00`.

## Experiment 66 — increase L1 regularization

- Classification: follow-up to the `reg_alpha=0.5` improvement.
- **Hypothesis:** test `reg_alpha=1.0` to see whether stronger shrinkage continues to remove weak leaf contributions; keep all other settings fixed.
- Result: Eval AUC `0.7584` (`+0.0003` vs prior best); runtime `46.6s`, status `ok`; training `15.1s`, evaluation `31.5s`, artifact `36.4 MB`. Keep commit `aa1a768`.

## Experiment 67 — continue L1 regularization search

- Classification: follow-up to the `reg_alpha=1.0` improvement.
- **Hypothesis:** test `reg_alpha=2.0` to see whether the upward trend continues or reaches its optimum; keep all other settings fixed.
- Result: Eval AUC `0.7568` (`-0.0016` vs current best); runtime `46.7s`, status `ok`; training `15.1s`, evaluation `31.6s`, artifact `39.0 MB`. Discard commit `d565873`; revert to `aa1a768`.

## Experiment 68 — midpoint L1 strength

- Classification: follow-up after `reg_alpha=2.0` underperformed.
- **Hypothesis:** test `reg_alpha=1.5`, midway between the `1.0` best and `2.0` loss, to locate whether the optimum lies between those values.
- Result: Eval AUC `0.7570` (`-0.0014` vs current best); runtime `46.6s`, status `ok`; training `15.0s`, evaluation `31.6s`, artifact `39.5 MB`. Discard commit `16a0058`; revert to `aa1a768`.

## Experiment 69 — midpoint below the L1 best

- Classification: follow-up to the 0.5 and 1.0 improvements.
- **Hypothesis:** test `reg_alpha=0.75` to check whether the optimum lies just below 1.0; keep all other settings fixed.
- Result: Eval AUC `0.7597` (`+0.0013` vs prior best); runtime `47.1s`, status `ok`; training `15.4s`, evaluation `31.7s`, artifact `32.6 MB`. Keep commit `5a6da1e`.

## Experiment 70 — refine L1 strength near 0.75

- Classification: follow-up to the `reg_alpha=0.75` improvement.
- **Hypothesis:** test `reg_alpha=0.8`, close to the apparent peak between the 0.5 and 1.0 results. Keep every other setting fixed.
- Result: Eval AUC `0.7591` (`-0.0006` vs current best); runtime `47.2s`, status `ok`; training `15.8s`, evaluation `31.4s`, artifact `33.5 MB`. Discard commit `467d4ee`; revert to `5a6da1e`.

## Synthesis after 70 experiments

- The best score is now `0.7597` at commit `5a6da1e`, an improvement of `0.0394` over the `0.7203` baseline. The best configuration combines 2300 trees at learning rate 0.03, loss-guided growth with 44 leaves, `min_child_weight=50`, `max_cat_threshold=8`, and `reg_alpha=0.75`.
- L1 regularization was the latest major gain: `reg_alpha=0.1` scored `0.7546`, 0.5 scored `0.7581`, 1.0 scored `0.7584`, and 0.75 scored `0.7597`. Values 1.5, 2.0, and 0.8 were lower, suggesting a useful peak near 0.75.
- Histogram resolution changes did not beat the default 256 bins. Target-rate features, added one-hot splits, higher categorical partition caps, and column sampling also failed to improve the native-feature model.
- Current theory: L1 shrinkage complements loss-guided growth by trimming weak leaf weights while retaining the most useful categorical and numeric splits. The regularization optimum is narrow enough to warrant one more nearby probe.
- Next: test `reg_alpha=0.7`, then stop at the two-hour clock limit. If it does not beat 0.75, restore commit `5a6da1e` and finish the run.

## Experiment 71 — lower-side L1 refinement

- Result: Eval AUC `0.7596` (`-0.0001` vs current best); runtime `48.0s`, status `ok`; training `16.5s`, evaluation `31.5s`, artifact `31.7 MB`. Discard commit `cfb4e7c`; revert to `5a6da1e`.

## Experiment 72 — final L1 midpoint

- Classification: follow-up to the `reg_alpha=0.75` best.
- **Hypothesis:** test `reg_alpha=0.74`, slightly below 0.75, for one final refinement under the remaining clock budget.
- Result: Eval AUC `0.7584` (`-0.0013` vs current best); runtime `47.6s`, status `ok`; training `15.9s`, evaluation `31.7s`, artifact `32.7 MB`. Discard commit `0d00ae7`; revert to `5a6da1e`.

## Final summary

- Best Eval AUC: `0.7597`, commit `5a6da1e` (`reg_alpha=0.75`), on branch `oct1`. This is `+0.0394` over the `0.7203` baseline.
- Best settings: 2300 trees, learning rate `0.03`, `lossguide`, 44 leaves, `min_child_weight=50`, `max_cat_threshold=8`, and `reg_alpha=0.75`.
- The strongest later improvement came from L1 regularization: `reg_alpha=0.5` reached `0.7581`, 1.0 reached `0.7584`, and 0.75 reached `0.7597`. Values above 1.0 or near 0.8 were lower.
- Loss-guided trees and the longer, lower-rate schedule helped. Histogram bin changes, feature sampling, extra route/time features, target-rate encodings, and categorical threshold/one-hot variants did not beat the best.
- Suggested next work: retune learning rate and tree count around the new `reg_alpha=0.75` setting, then test whether categorical cap and child weight shift under that regularization.
