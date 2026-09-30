# Research log

## Baseline

- Branch: `sep30`.
- Commit `92e43e6`: unchanged starter `train.py`.
- Eval AUC: `0.7203`; status `ok`; runtime `31.4s` (1.1s training, 30.3s evaluation).
- This establishes the comparison point for the run.

## Initial research and hypothesis

Sources reviewed before the first non-baseline experiment:

- The [XGBoost parameter-tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) frames depth and related parameters as a bias/variance tradeoff and recommends more boosting rounds when lowering the learning rate. It also emphasizes understanding the data and preprocessing.
- The [XGBoost categorical-data guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) confirms the starter's pandas categorical columns with `enable_categorical=True` are the supported approach. Keep that representation fixed while testing the number of boosting rounds.
- The [Bureau of Transportation Statistics on-time table](https://www.transtats.bts.gov/TableInfo.asp?QO_fu146_anzr=b0-gvzr&gnoyr_VQ=FGJ) describes scheduled departure time, airline, origin/destination, and distance as core flight fields. An [airport-delay prediction study](https://www.mdpi.com/2071-1050/12/7/2749) also considers scheduled departure time, day of month/week, and origin airport as useful inputs. This suggests temporal features are a promising later direction using only fields already present here.

### Experiment 1 — increase boosting rounds

- Hypothesis: the 30-tree baseline may stop before the model has learned enough additive structure. Increasing only `n_estimators` to 100 while holding all other settings fixed tests whether additional rounds improve ranking without confounding the result with feature or regularization changes. Training has ample room under the one-minute limit.
- Class: exploration (boosting capacity).
- Decision rule: keep if Eval AUC rises; otherwise restore the baseline. If this helps, test a slower learning rate with a proportionally larger round count as a separate follow-up.
- Result: commit `6ed2e5f`, Eval AUC `0.7306` (`ok`, 32.0s total; 1.4s training). Kept: this is a +0.0103 gain over baseline with a small runtime increase.

### Experiment 2 — test additional rounds

- Hypothesis: the large gain from 30 to 100 trees suggests the baseline was underfit. Increase only `n_estimators` from 100 to 200 at `learning_rate=0.1` to test whether ranking still improves with more additive steps; the training run used only 1.4s, so this remains well inside the limit.
- Class: follow-up to the promising 100-tree result.
- Result: commit `d7cfa3f`, Eval AUC `0.7345` (`ok`, 32.9s total; 2.0s training). Kept: another +0.0039 over 100 trees.

### Experiment 3 — extend the same boosting path

- Hypothesis: Eval AUC rose again from 100 to 200 trees, so test 400 trees at the same learning rate to determine whether further boosting rounds still add useful ranking signal. This isolates round count; if gains flatten, shift to a different idea rather than continuing to double indefinitely.
- Class: follow-up to the promising 200-tree result.
- Result: commit `37e1454`, Eval AUC `0.7325` (`ok`, 34.1s total; 3.1s training). Discarded and reset: the score fell 0.0020 below 200 trees, suggesting that simply extending the same 0.1 learning-rate path overfits or overshoots.

### Experiment 4 — smaller boosting steps

- Hypothesis: the 400-tree result fell below the 200-tree result at learning rate 0.1. The XGBoost tuning guide recommends reducing `eta` while increasing boosting rounds; try 400 trees at 0.05 to test whether smaller additive steps recover generalization while allowing the same cumulative shrinkage as 200 trees at 0.1.
- Class: follow-up to the promising 200-tree result, informed by XGBoost's parameter-tuning guidance.
- Result: commit `abc2399`, Eval AUC `0.7354` (`ok`, 33.9s total; 3.1s training). Kept as the new best, +0.0009 over 200 trees at 0.1.

### Experiment 5 — scheduled departure time features

- Research: the [scikit-learn time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) explains sine/cosine features for periodic times and the continuity they provide across the end/start boundary. It demonstrates this on a different task and model family, so this is a hypothesis to test with XGBoost. An [airline delay study](https://www.mdpi.com/2071-1050/13/24/4910) specifically extracts hour from scheduled departure time stored as HHMM and evaluates a late-night indicator; the [BTS data description](https://www.transtats.bts.gov/TableInfo.asp?QO_fu146_anzr=b0-gvzr&gnoyr_VQ=FGJ) confirms scheduled departure time is a core flight field.
- Hypothesis: numeric `CRSDepTime` uses HHMM, whose gaps do not reflect elapsed minutes and whose midnight boundary is discontinuous. Add minute-of-day and sine/cosine of its 24-hour phase inside `prepare(df)`, while retaining the raw field, to expose smoother time structure without using any cross-row statistics.
- Class: exploration (feature engineering). These features depend only on each row and use no fitted lookup.
- Result: commit `1b6b839`, Eval AUC `0.7345` (`ok`, 40.2s total; 3.2s training). Discarded and reset: no measurable AUC gain at four decimals, with evaluation time increasing from about 31s to 37s.

### Experiment 6 — leakage-controlled group delay rates

- Research: the scikit-learn [TargetEncoder documentation](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html) warns that fitting an encoder on the training data and transforming that same data can leak targets; it recommends cross-fitting for training rows. A flight delay paper [target-encodes airport and airline features](https://www.mdpi.com/2226-4310/8/6/152), supporting this encoding for this domain.
- Hypothesis: smoothed delay rates for carrier, origin, destination, and route may expose learned group propensity more directly than native categories alone. Fit sums and denominators on `train` at module level, but do not expose counts as features. Use leave-one-out rates for training rows (subtract that row's label) and full smoothed train rates for evaluation rows; unknown groups fall back to the train-wide rate. This keeps the feature row-wise at inference and avoids self-label leakage.
- Class: exploration (train-fitted group target encoding).
- Result: commit `1fdcc27`, Eval AUC `0.6113` (`ok`, 51.3s total; 3.2s training). Discarded and reset: the large drop suggests the leave-one-out training feature distribution did not transfer to full-train inference lookups, especially on sparse routes.

### Experiment 7 — fold-based target encoding

- Hypothesis: the previous leave-one-out encoding can shift sparse-group values row by row because each row's label is individually subtracted. Try five-fold out-of-fold group rates instead: each training row uses one lookup built from the other four folds, while evaluation uses the full train lookup. This follows the cross-fitting approach in scikit-learn's TargetEncoder guidance and should better align train and inference encodings.
- Class: follow-up to the group target-encoding exploration. Cross-fitting here is only for feature construction; the model is fit once and the harness remains the only evaluation metric.
- Result: commit `7e36c64`, Eval AUC `0.7310` (`ok`, 51.4s total; 3.5s training). Discarded and reset: cross-fitting fixed the very low leave-one-out score but remained 0.0044 below the best kept model, so the target-rate features are not worth their complexity and evaluation cost here.

### Experiment 8 — row subsampling

- Hypothesis: the XGBoost [parameter-tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) identifies `subsample` and `colsample_bytree` as randomness controls that can reduce overfitting. Test only `subsample=0.8` on the current best model to see whether per-tree row sampling improves generalization.
- Class: follow-up/regularization of the promising 400-tree model.
- Result: commit `b5ff202`, Eval AUC `0.7285` (`ok`, 34.0s total; 3.2s training). Discarded and reset: this is 0.0069 below the kept model.

### Experiment 9 — shallower trees

- Hypothesis: the same XGBoost guide describes `max_depth` as a direct complexity control. Reduce it from 6 to 5 while holding the 400-tree, 0.05 learning-rate configuration fixed, testing whether slightly simpler trees generalize better than the current best.
- Class: follow-up/regularization of the promising 400-tree model.
- Result: commit `e6984be`, Eval AUC `0.7340` (`ok`, 33.2s total; 2.6s training). Discarded and reset: 0.0014 below the kept model.

## Synthesis after 10 logged runs

- The starter's 30 trees scored 0.7203. Increasing capacity helped substantially: 100 trees scored 0.7306 and 200 trees scored 0.7345.
- Continuing at learning rate 0.1 to 400 trees fell to 0.7325, while 400 trees at 0.05 reached the current best, 0.7354. The best theory is that this setup benefits from enough rounds with smaller boosting steps, while simply adding rounds at the original step size overshoots.
- The scheduled-time transformation tied the best score at the displayed precision and slowed evaluation, so it was discarded. The train-fitted target-rate encodings scored substantially worse even with leakage controls; those features are not worth their complexity in this form. Row subsampling at 0.8 and reducing depth to 5 also reduced AUC.
- Current best: commit `abc2399`, Eval AUC `0.7354`.
- Next direction: test whether representing the origin-destination pair directly as a categorical route feature captures a useful interaction that separate origin and destination columns do not.

### Experiment 11 — categorical route interaction

- Research: XGBoost's [categorical-data guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains that categorical splits can partition categories with similar leaf values. An [AIAA flight-delay study](https://junchen.sdsu.edu/proceedings/scitech_gnc19_Chen.pdf) discusses origin-destination pairs as a potentially relevant airport interaction, while noting that route distinctions can be weak when data is insufficient. This makes a single route-category feature a useful, low-complexity test.
- Hypothesis: adding `Origin|Dest` as a categorical feature exposes directed route identity and route-specific effects directly; XGBoost can group similar routes using its native categorical split handling. Fit only the category vocabulary on train and derive each row's route from its own origin and destination.
- Class: exploration (categorical interaction feature).
- Result: commit `d406ed8`, Eval AUC `0.7071` (`ok`, 52.6s total; 4.8s training). Discarded and reset: the route category expanded the artifact to 66 MB, made evaluation slower, and lowered AUC substantially, indicating this high-cardinality pair feature is a poor fit here.

### Experiment 12 — minimum child weight

- Hypothesis: the XGBoost tuning guide also lists `min_child_weight` as a tree-complexity control. Raise it from its default of 1 to 5 on the kept configuration, testing whether requiring more Hessian mass per child suppresses noisy splits while preserving the useful depth-6 structure.
- Class: follow-up/regularization of the promising 400-tree model.
- Result: commit `143c024`, Eval AUC `0.7346` (`ok`, 33.6s total; 3.0s training). Discarded and reset: this is 0.0008 below the best at displayed precision.

### Experiment 13 — one-hot splits for small categories

- Research: the XGBoost [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-categorical-feature) says `max_cat_to_onehot` selects one-hot splits when a feature has fewer categories than the threshold; otherwise XGBoost uses category partitioning. This parameter has been available since XGBoost 1.6.
- Hypothesis: the current default threshold may partition low-cardinality calendar categories that could be modeled more directly. Set the threshold to 16, which should enable one-hot splits for weekday and month while keeping higher-cardinality fields partitioned. Hold the data and all other model settings fixed.
- Class: exploration (categorical split strategy).
- Result: commit `2ddec7c`, Eval AUC `0.7345` (`ok`, 34.6s total; 4.0s training). Discarded and reset: tied the baseline feature setup at four decimals without an AUC gain.

### Experiment 14 — expand the one-hot category threshold

- Hypothesis: threshold 16 likely affected only month and weekday. Raise it to 32 to include day of month and possibly carrier, while leaving the airport categories on partition-based splits. This tests whether one-hot handling helps when applied to the remaining small categorical fields.
- Class: exploration (follow-up on categorical split strategy).
- Result: commit `71af766`, Eval AUC `0.7238` (`ok`, 33.4s total; 2.9s training). Discarded and reset: the wider one-hot threshold reduced AUC substantially.

### Experiment 15 — smaller steps with more rounds

- Hypothesis: 400 trees at 0.05 improved on 200 trees at 0.1, while 400 at 0.1 fell back. Continue the documented smaller-step/more-rounds strategy with 800 trees at 0.025; this keeps the nominal `n_estimators * learning_rate` product equal to the current best while testing whether still finer updates improve ranking.
- Class: follow-up to the promising 400-tree, 0.05 result.
- Result: commit `9974cea`, Eval AUC `0.7349` (`ok`, 36.3s total; 5.3s training). Discarded and reset: slightly below the kept score and twice the artifact size, so the finer steps do not justify the added model size.

### Experiment 16 — split loss penalty

- Research: the XGBoost [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster) defines `gamma` as the minimum loss reduction required for a further leaf split; increasing it makes the model more conservative. This differs from the earlier row-sampling, depth, and child-weight tests by directly penalizing low-gain splits. I also reviewed the [DART booster documentation](https://xgboost.readthedocs.io/en/release_2.0.0/tutorials/dart.html), which warns that DART prediction can drop trees unless an iteration range is supplied; the fixed harness calls `predict_proba` without such an override, so DART is not a safe experiment within the current harness contract.
- Hypothesis: set `gamma=1.0` on the kept model to suppress marginal splits while preserving high-gain structure; hold all other settings fixed.
- Class: exploration (split regularization).
- Result: commit `30ae9d2`, Eval AUC `0.7338` (`ok`, 33.0s total; 2.6s training). Discarded and reset: 0.0016 below the kept model.

### Experiment 17 — lighter split loss penalty

- Hypothesis: `gamma=1.0` was too conservative for the current data. Test `gamma=0.1` as a milder minimum split-loss threshold, with all other settings unchanged, to see whether a small penalty improves on the unregularized best.
- Class: follow-up to the split-regularization experiment.
- Result: commit `c45cd13`, Eval AUC `0.7364` (`ok`, 34.3s total; 3.2s training). Kept as the new best, +0.0010 over the prior best.

### Experiment 18 — slightly stronger split penalty

- Hypothesis: `gamma=0.1` improved on the unregularized model, while `gamma=1.0` was too strong. Test the intermediate value `gamma=0.25` to locate whether a somewhat stronger penalty improves further.
- Class: follow-up to the promising `gamma=0.1` result.
- Result: commit `5aaf37a`, Eval AUC `0.7354` (`ok`, 34.0s total; 3.1s training). Discarded and reset: the stronger penalty lost the +0.0010 gain from `gamma=0.1`.

### Experiment 19 — lighter split penalty

- Hypothesis: `gamma=0.1` was the best tested split penalty, and `gamma=0.25` was too strong. Test `gamma=0.05` to see whether the optimum lies closer to no penalty.
- Class: follow-up to the promising `gamma=0.1` result.
- Result: commit `021f692`, Eval AUC `0.7361` (`ok`, 34.3s total; 3.2s training). Discarded and reset: close but below the best result at `gamma=0.1`.

### Experiment 20 — refine split penalty

- Hypothesis: among tested values, `gamma=0.1` currently leads, with 0.05 and 0.25 slightly lower. Test `gamma=0.15` to refine the local range around that best setting.
- Class: follow-up to the promising `gamma=0.1` result.
- Result: commit `89d21ac`, Eval AUC `0.7355` (`ok`, 34.6s total; 3.2s training). Discarded and reset: below the best result at `gamma=0.1`.

## Synthesis after 20 logged runs

- The starter scored 0.7203. More trees at a moderate learning rate helped: 100 trees reached 0.7306 and 200 reached 0.7345. At 400 trees, learning rate 0.1 fell back, while 0.05 reached 0.7354.
- A small split penalty was the clearest additional improvement. `gamma=0.1` scored 0.7364, the current best. `gamma=0.05` and `0.15` were close but lower; `0.25` and `1.0` were lower still. This suggests a narrow useful regularization level rather than a broad monotonic trend.
- Time-of-day transforms tied but slowed evaluation. Target-rate encodings, a route category, one-hot categorical thresholds, row subsampling, lower depth, higher child weight, and finer 800-tree steps all reduced AUC or increased model cost without a gain.
- Current best: commit `c45cd13`, Eval AUC `0.7364`.
- Next direction: retest boosting-round capacity with `gamma=0.1`, which may let the model use more rounds while filtering low-gain splits.

### Experiment 21 — more rounds with split regularization

- Hypothesis: 400 trees at 0.05 plus `gamma=0.1` is the best result. Increase only `n_estimators` to 500 to test whether the split penalty allows additional boosting steps without the overfitting seen at 400 trees and learning rate 0.1.
- Class: follow-up to the promising `gamma=0.1` model.
- Result: commit `1e3ce8f`, Eval AUC `0.7369` (`ok`, 34.6s total; 3.7s training). Kept as the new best, +0.0005 over 400 trees with the same learning rate and gamma.

### Experiment 22 — continue the regularized boosting path

- Hypothesis: the 500-tree model improved over 400 trees under `gamma=0.1`. Increase only `n_estimators` to 600 to see whether a modest number of additional rounds adds useful ranking signal before the gains flatten.
- Class: follow-up to the promising 500-tree result.
- Result: commit `6d8a25d`, Eval AUC `0.7360` (`ok`, 35.3s total; 4.2s training). Discarded and reset: AUC fell 0.0009 from the 500-tree result.

### Experiment 23 — intermediate round count

- Hypothesis: 500 trees scored 0.7369 and 600 scored 0.7360 with all else fixed. Test 550 trees to check whether a smaller increase from the current best retains the gain or whether the optimum is near 500.
- Class: follow-up to the promising 500-tree result.
- Result: commit `8608bb4`, Eval AUC `0.7364` (`ok`, 35.0s total; 3.9s training). Discarded and reset: the midpoint was also below the 500-tree result.

### Experiment 24 — L2 leaf regularization

- Hypothesis: the best model uses `gamma=0.1` but default `reg_lambda=1`. Increase L2 leaf regularization to 2 while holding all other settings fixed to test whether slightly smaller leaf outputs improve generalization.
- Class: exploration (regularization).
- Result: commit `561a9bb`, Eval AUC `0.7359` (`ok`, 35.3s total; 4.6s training). Discarded and reset: L2=2.0 did not improve on default L2.
- Plateau note: recent 500/550/600-round and L2 experiments stayed within 0.001 of the best. Per `program.md`, research a new direction before the next run.

### Experiment 25 — cap categorical split candidates

- Research: the [XGBoost parameter-tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) includes `max_cat_threshold` among model-complexity controls. The [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-categorical-feature) defines it as the maximum categories considered for each partition-based split and says it is intended to prevent overfitting.
- Hypothesis: airport categories remain partition-based with the starter's categorical strategy, and high-cardinality route identity previously hurt badly. Test `max_cat_threshold=32` to limit category split search on the existing categorical features without adding new features or changing one-hot handling.
- Class: exploration (categorical split regularization).
- Result: commit `dbee635`, Eval AUC `0.7364` (`ok`, 34.9s total; 3.6s training). Discarded and reset: slightly below the best, despite a smaller artifact.

### Experiment 26 — tighter categorical split cap

- Hypothesis: the cap of 32 was not enough to improve AUC. Test `max_cat_threshold=16` as a stronger limit on partition-based categorical splits, while keeping the same categorical representation and model settings.
- Class: follow-up to the categorical split regularization experiment.
- Result: commit `a4c72c7`, Eval AUC `0.7400` (`ok`, 34.2s total; 3.3s training). Kept as the new best, +0.0031, and the artifact shrank from 12.7 MB to 9.6 MB.

### Experiment 27 — tighter categorical split cap

- Hypothesis: the cap of 16 produced a strong gain. Reduce it to 8 to test whether further limiting category candidates regularizes airport partitions more effectively.
- Class: follow-up to the promising `max_cat_threshold=16` result.
- Result: commit `45cb530`, Eval AUC `0.7420` (`ok`, 35.0s total; 4.1s training). Kept as the new best, +0.0020, with an 8.0 MB artifact.

### Experiment 28 — smaller categorical split cap

- Hypothesis: reducing the cap from 32 to 16 to 8 improved AUC at each step. Test a cap of 4 to determine whether this trend continues or begins to underfit.
- Class: follow-up to the promising `max_cat_threshold=8` result.
- Result: commit `8123d8b`, Eval AUC `0.7342` (`ok`, 33.5s total; 2.9s training). Discarded and reset: the cap of 4 was too restrictive and dropped below the best by 0.0078.

### Experiment 29 — intermediate categorical split cap

- Hypothesis: cap 8 scored 0.7420, while cap 4 underfit at 0.7342. Test cap 6 to check whether an intermediate level retains the gain while allowing a few more category candidates.
- Class: follow-up to the promising `max_cat_threshold=8` result.
- Result: commit `b8d8359`, Eval AUC `0.7385` (`ok`, 33.8s total; 3.0s training). Discarded and reset: below the cap-8 result by 0.0035.

### Experiment 30 — bracket the best categorical cap

- Hypothesis: cap 8 is best among 4, 6, 8, 16, and 32. Test cap 10, between the current best and the lower-scoring 16, to check whether a slightly looser cap improves on 8.
- Class: follow-up to the promising `max_cat_threshold=8` result.
- Result: commit `46f7ec4`, Eval AUC `0.7420` (`ok`, 34.5s total; 3.3s training). Discarded and reset: tied at four decimals but produced a larger artifact than cap 8.

## Synthesis after 30 logged runs

- The best kept model improved from 0.7203 at baseline to 0.7420. Increasing rounds from 30 to 200 helped, and 500 trees at learning rate 0.05 with `gamma=0.1` reached 0.7369.
- The strongest gain came from limiting categorical partition candidates. With the 500-tree, 0.05, gamma 0.1 model fixed, `max_cat_threshold=16` scored 0.7400 and 8 scored 0.7420. Caps 4, 6, and 32 were worse; 10 tied but created a larger artifact.
- Direct time features, route and target-rate encodings, one-hot category thresholds, row sampling, lower depth, higher child weight, larger L2, and extra rounds beyond 500 did not help on the earlier configuration. The main current theory is that high-cardinality airport categories were overfitting during partition splits; limiting the split search lets the other features generalize better.
- Current best: commit `45cb530`, Eval AUC `0.7420`, 8.0 MB artifact.
- Next direction: revisit boosting-round count under the new categorical cap, since the prior 550/600 tests were done before this change.

### Experiment 31 — more rounds with categorical regularization

- Hypothesis: 500 trees was best before `max_cat_threshold=8` was added. The stronger categorical regularization may support more rounds without overfitting, so test 600 trees with all other settings fixed.
- Class: follow-up to the promising cap-8 model.
- Result: commit `cf7eaa8`, Eval AUC `0.7430` (`ok`, 34.0s total; 3.6s training). Kept as the new best, +0.0010 over 500 trees under cap 8.

### Experiment 32 — continue boosting under cap 8

- Hypothesis: 600 trees improved over 500 with `max_cat_threshold=8`. Increase only `n_estimators` to 700 to test whether the new regularization continues to support more rounds.
- Class: follow-up to the promising 600-tree cap-8 result.
- Result: commit `a0a87d6`, Eval AUC `0.7438` (`ok`, 35.0s total; 4.0s training). Kept as the new best, +0.0008.

### Experiment 33 — continue cap-8 boosting

- Hypothesis: AUC rose from 0.7420 at 500 rounds to 0.7430 at 600 and 0.7438 at 700. Test 800 rounds with the same learning rate and regularization to see whether this improvement continues.
- Class: follow-up to the promising 700-tree cap-8 result.
- Result: commit `f090a42`, Eval AUC `0.7436` (`ok`, 35.2s total; 4.4s training). Discarded and reset: slightly below the 700-tree result.

### Experiment 34 — bracket the best round count

- Hypothesis: 700 rounds scored 0.7438 and 800 scored 0.7436. Test 750 rounds to check whether an intermediate count improves on the current best.
- Class: follow-up to the promising 700-tree cap-8 result.
- Result: commit `67b2336`, Eval AUC `0.7438` (`ok`, 35.4s total; 4.2s training). Discarded and reset: tied at four decimals with the 700-tree result while producing a larger artifact.

### Experiment 35 — ablate the split penalty under cap 8

- Hypothesis: cap 8 already limits high-cardinality categorical splits. Remove `gamma=0.1` and use XGBoost's default split penalty to test whether this categorical regularizer makes the extra gamma control redundant. If AUC is similar or higher, the model becomes simpler.
- Class: ablation/simplification of a promising regularizer.
- Result: commit `7811fd8`, Eval AUC `0.7421` (`ok`, 34.9s total; 4.0s training). Discarded and reset: removing gamma lost 0.0017, so the split penalty remains useful under cap 8.

### Experiment 36 — lighter gamma under cap 8

- Hypothesis: gamma 0.1 was best under the original categorical settings. Test gamma 0.05 with `max_cat_threshold=8` to see whether the interaction with categorical regularization shifts the optimum.
- Class: follow-up to the promising cap-8 model.
- Result: commit `75f3c60`, Eval AUC `0.7433` (`ok`, 35.2s total; 4.0s training). Discarded and reset: below gamma 0.1 by 0.0005.

### Experiment 37 — stronger gamma under cap 8

- Hypothesis: gamma 0.1 remains best under cap 8; gamma 0.05 was lower and removing gamma was much worse. Test gamma 0.15 to check whether a slightly stronger split penalty improves the regularized categorical model.
- Class: follow-up to the promising cap-8 model.
- Result: commit `029892f`, Eval AUC `0.7437` (`ok`, 34.7s total; 4.1s training). Discarded and reset: below the gamma 0.1 best by 0.0001.

### Research check after Experiment 37 (plateau)

- Recent gamma changes under categorical cap 8 have all missed the 0.7438 best, so I reviewed other XGBoost tree-growth controls before the next trial.
- The official [parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) says `grow_policy="lossguide"` expands the leaf with the highest loss change (supported by `hist`/`approx`) and `max_leaves` caps tree size. This gives a meaningfully different allocation of split capacity from depthwise growth. The [categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) describes XGBoost's category partitioning by ordered leaf values; keep the currently successful categorical setup fixed while testing growth policy.
- Next hypothesis (Experiment 38): use `tree_method="hist"`, `grow_policy="lossguide"`, `max_depth=0`, and `max_leaves=64`. The leaf ceiling matches the maximum leaves of a full depth-6 binary tree, while allowing loss-guided, asymmetric allocation of those splits. Keep 700 estimators, learning rate 0.05, gamma 0.1, and `max_cat_threshold=8` unchanged. Class: exploration of a different tree-growth strategy.
- Experiment 38 attempt: commit `8c257e1` crashed before training because the new `max_depth=0` duplicated the existing keyword. This is an implementation typo, not a model result; correct the existing setting and rerun the same hypothesis.
- Experiment 39 result: commit `d3a34af`, Eval AUC `0.7454` (`ok`, 37.9s total; 6.3s training), artifact 20.0 MB. Kept as the new best, +0.0016 over depthwise cap-8. (Experiment 38 was the syntax-error attempt recorded above.)

### Experiment 40 — expand loss-guided leaf budget

- Hypothesis: the loss-guided 64-leaf model improved AUC to 0.7454, suggesting its split allocation is useful. Raise only `max_leaves` from 64 to 96 to test whether additional targeted splits improve ranking; retain unlimited depth and all winning settings. A larger artifact is expected, so compare the metric and saved size.
- Class: follow-up to a promising tree-growth strategy.
- Result: commit `00ee865`, Eval AUC `0.7462` (`ok`, 38.8s total; 7.6s training), artifact 30.2 MB. Kept as the new best, +0.0008 over 64 leaves.

### Synthesis after Experiment 40

- Best checkpoint: loss-guided growth with `max_leaves=96`, unlimited depth, 700 trees, learning rate 0.05, gamma 0.1, and categorical split cap 8; AUC 0.7462 at commit `00ee865` (30.2 MB artifact).
- The strongest gains so far came from restricting categorical partition search (cap 16 then 8), modestly extending boosting rounds, and switching from depthwise depth-6 trees to loss-guided growth with a leaf cap. The latter two caps tested (64, 96) both improved, though model size rose from 20.0 to 30.2 MB.
- The original depthwise model with gamma 0.1 remains better than dropping gamma or shifting it to 0.05/0.15. Cat cap 4/6 and one-hot threshold changes were worse. Earlier feature-engineering and target-encoding trials also underperformed or cost too much time.
- Current theory: categorical regularization and targeted allocation of splits help the model capture useful carrier/airport/route segments without spending capacity uniformly. Next, extend the loss-guided leaf cap to 128, monitoring both AUC and artifact size; if the gain flattens, probe other regularizers under this growth policy.

### Experiment 41 — continue leaf-budget expansion

- Hypothesis: increasing the loss-guided cap from 64 to 96 raised AUC by 0.0008. Test 128 leaves to learn whether the positive trend continues before the larger model begins to overfit; all other settings stay fixed. Track saved artifact size as well as AUC.
- Class: follow-up to a promising tree-growth strategy.
- Result: commit `09115cd`, Eval AUC `0.7456` (`ok`, 40.2s total; 9.2s training), artifact 41.9 MB. Discarded and reset: 128 leaves was 0.0006 below the 96-leaf best and substantially larger.

### Experiment 42 — shrink loss-guided leaf scores

- Hypothesis: the 96-leaf loss-guided trees outperform depthwise trees, while the 128-leaf variant starts to lose ground. Test `reg_lambda=2` (up from XGBoost's default 1) to shrink leaf weights and potentially stabilize ranking in the deeper model. Keep structure and other settings fixed. The official [parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes L2 regularization as making the model more conservative.
- Class: follow-up regularization test on the best tree-growth strategy.
- Result: commit `2ac51a1`, Eval AUC `0.7464` (`ok`, 38.8s total; 7.6s training), artifact 29.8 MB. Kept as the new best, +0.0002; slight L2 increase preserved model size and improved AUC.

### Experiment 43 — test stronger L2 shrinkage

- Hypothesis: `reg_lambda=2` slightly improved the 96-leaf loss-guided model over the default. Raise it to 4 to test whether additional shrinkage helps control leaf scores; keep all other settings fixed.
- Class: follow-up regularization test on a promising result.
- Result: commit `55b25aa`, Eval AUC `0.7486` (`ok`, 39.1s total; 7.5s training), artifact 30.0 MB. Kept as the new best, +0.0022 over lambda 2.

### Experiment 44 — test stronger L2 shrinkage

- Hypothesis: raising `reg_lambda` from 2 to 4 gave a clear gain. Test 8 to determine whether deeper loss-guided trees benefit from further shrinkage or whether the improvement peaks around 4.
- Class: follow-up regularization test on a promising result.
- Result: commit `8fc7b8c`, Eval AUC `0.7514` (`ok`, 39.2s total; 7.8s training), artifact 30.2 MB. Kept as the new best, +0.0028 over lambda 4.

### Experiment 45 — continue L2 sweep

- Hypothesis: AUC improved at each tested `reg_lambda` value (2, 4, 8). Test 16 to see whether this trend continues or reaches its regularization optimum.
- Class: follow-up regularization test on a promising result.
- Result: commit `cfe1be1`, Eval AUC `0.7524` (`ok`, 39.9s total; 8.2s training), artifact 29.2 MB. Kept as the new best, +0.0010 over lambda 8.

### Experiment 46 — extend the L2 sweep

- Hypothesis: `reg_lambda=16` improved AUC again, although the gain was smaller than the prior step. Test 32 to see whether the positive trend persists or has reached its optimum.
- Class: follow-up regularization test on a promising result.
- Result: commit `d8e9822`, Eval AUC `0.7534` (`ok`, 39.5s total; 8.4s training), artifact 29.4 MB. Kept as the new best, +0.0010 over lambda 16.

### Experiment 47 — extend the L2 sweep

- Hypothesis: AUC increased at every tested doubling through `reg_lambda=32`. Test 64 as the next point on this systematic sweep; retain the 96-leaf loss-guided structure and all other parameters.
- Class: follow-up regularization test on a promising result.
- Result: commit `994cd4d`, Eval AUC `0.7563` (`ok`, 40.4s total; 8.9s training), artifact 31.8 MB. Kept as the new best, +0.0029 over lambda 32.

### Experiment 48 — extend the L2 sweep

- Hypothesis: the gain accelerated at `reg_lambda=64`, with AUC up 0.0029 from 32. Test 128 to see whether stronger shrinkage continues to control high-variance loss-guided leaves.
- Class: follow-up regularization test on a promising result.
- Result: commit `8a07aad`, Eval AUC `0.7562` (`ok`, 40.7s total; 9.2s training), artifact 31.6 MB. Discarded and reset: slightly below lambda 64 (difference 0.0001) at essentially the same size.

### Experiment 49 — bracket the L2 peak

- Hypothesis: `reg_lambda=64` and 128 produced nearly identical scores, with 64 ahead by 0.0001. Test the midpoint 96 to refine the promising range; keep all other settings unchanged.
- Class: follow-up parameter refinement around the best regularization setting.
- Result: commit `a4df170`, Eval AUC `0.7563` (`ok`, 40.8s total; 9.4s training), artifact 31.7 MB. Discarded and reset: tied lambda 64 at four decimals without simplifying the model.

### Experiment 50 — extend boosting under stronger L2

- Hypothesis: with loss-guided growth and `reg_lambda=64`, the model is much more regularized than earlier 700-round depthwise trials. Test 800 estimators to see if extra boosting rounds now improve ranking; hold the other current-best settings fixed.
- Class: follow-up to a promising regularized model.
- Result: commit `10bcedb`, Eval AUC `0.7565` (`ok`, 41.6s total; 10.7s training), artifact 36.1 MB. Kept as the new best, +0.0002 over the 700-round lambda-64 model.

### Synthesis after Experiment 50

- Best checkpoint: loss-guided trees, unlimited depth, `max_leaves=96`, `reg_lambda=64`, 800 estimators, learning rate 0.05, gamma 0.1, categorical split cap 8; AUC 0.7565 at commit `10bcedb` (36.1 MB artifact).
- In experiments 41–50, a 128-leaf cap slightly hurt versus 96. Raising L2 from 1 to 64 was the major gain (+0.0101 from the 96-leaf lambda-1 model); AUC rose at 2, 4, 8, 16, 32, and 64. Lambda 96 tied 64 at four decimals and 128 was 0.0001 lower. Extending to 800 rounds added a further 0.0002.
- Current theory: loss-guided trees create many small leaves, and strong L2 shrinkage is important to avoid noisy updates; this lets the model retain split detail while avoiding extreme leaf scores. Category cap 8 still appears useful. More of the same L2 doubling is unlikely to be efficient after the 64–128 plateau; look for complementary ways to regularize or capture signal.
- Fresh research is needed before selecting the next direction.

### Research check after Experiment 50

- Fresh official guidance: the [parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) group `min_child_weight` with `max_depth` and `gamma` as direct controls on tree complexity. The [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines it as a minimum child Hessian sum; increasing it makes growth more conservative.
- The allowed training labels are balanced (100,000 positive and 100,000 negative), so the usual negative/positive ratio for `scale_pos_weight` is 1.0 and there is no class weighting to add.
- New hypothesis: the current loss-guided model can create small leaves, but strong L2 may already shrink their weights. Test `min_child_weight=2` as a moderate support floor, below the earlier value 5 that hurt a depthwise model. This checks the parameter's interaction with loss-guided growth and lambda 64, while potentially reducing weak small-sample splits. If it harms AUC, discard it. This is Experiment 51, a follow-up regularization test on the current best.

### Experiment 51 — require more support in child nodes

- Hypothesis: with 96 loss-guided leaves and L2=64, a floor of 2 Hessian units may prune weak small-support splits without being as restrictive as the earlier min-child 5 setting. Keep all other current-best settings fixed and compare AUC and artifact size.
- Class: follow-up regularization test on the best model.
- Result: commit `270e2c2`, Eval AUC `0.7559` (`ok`, 41.3s total; 9.6s training), artifact 34.9 MB. Discarded and reset: min-child 2 was 0.0006 below the current best and only modestly reduced size.

### Experiment 52 — add L1 shrinkage

- Hypothesis: high L2 (64) smoothly shrinks leaf weights; a modest `reg_alpha=4` adds an L1 threshold that can zero out weak leaf updates. The official [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes L1 as making the model more conservative. Test whether it complements the successful L2 setting; hold the best structure and all other parameters fixed.
- Class: follow-up regularization test on the best model.
- Result: commit `6835db7`, Eval AUC `0.7597` (`ok`, 42.0s total; 10.6s training), artifact 21.9 MB. Kept as the new best, +0.0032, with a 14.2 MB smaller artifact than the alpha-0 model.

### Experiment 53 — increase L1 threshold

- Hypothesis: alpha 4 improved AUC and sharply reduced artifact size, consistent with weak leaf updates being suppressed. Raise `reg_alpha` to 8 to test whether stronger zeroing improves ranking further or removes useful splits' contribution.
- Class: follow-up regularization sweep on a promising result.
- Result: commit `3fc3859`, Eval AUC `0.7607` (`ok`, 40.7s total; 9.5s training), artifact 13.7 MB. Kept as the new best, +0.0010 over alpha 4; artifact is 8.2 MB smaller.

### Experiment 54 — continue L1 sweep

- Hypothesis: `reg_alpha=8` improved AUC again and further reduced model size. Test 16 to see whether the trend continues before stronger thresholding starts removing useful updates.
- Class: follow-up regularization sweep on a promising result.
- Result: commit `59b7b26`, Eval AUC `0.7573` (`ok`, 38.1s total; 6.9s training), artifact 8.6 MB. Discarded and reset: alpha 16 over-regularized, losing 0.0034 versus alpha 8 despite the smaller model.

### Experiment 55 — bracket the L1 optimum

- Hypothesis: alpha 8 was best, while alpha 16 removed too much signal. Test alpha 12 as the midpoint to refine the useful threshold and track its artifact size.
- Class: follow-up parameter refinement around the best L1 setting.
- Result: commit `78ba6d1`, Eval AUC `0.7593` (`ok`, 39.0s total; 8.2s training), artifact 10.0 MB. Discarded and reset: alpha 12 was 0.0014 below alpha 8.

### Experiment 56 — test alpha 10

- Hypothesis: alpha 8 scored 0.7607 and alpha 12 scored 0.7593. Test alpha 10 to refine this narrow L1 range; hold the rest of the best model fixed.
- Class: follow-up parameter refinement around the best L1 setting.
- Result: commit `cfd8f75`, Eval AUC `0.7597` (`ok`, 39.4s total; 8.5s training), artifact 11.1 MB. Discarded and reset: below alpha 8 by 0.0010.

### Experiment 57 — probe below alpha 8

- Hypothesis: alpha 8 is best among 4, 10, 12, and 16. Test alpha 6 between the earlier alpha-4 and alpha-8 results to check if a slightly milder threshold can recover more useful leaf contributions.
- Class: follow-up parameter refinement around the best L1 setting.
- Result: commit `087bd4d`, Eval AUC `0.7609` (`ok`, 40.8s total; 9.8s training), artifact 18.1 MB. Kept as the new best, +0.0002 over alpha 8, at the cost of a 4.4 MB larger artifact.

### Experiment 58 — refine the L1 peak

- Hypothesis: alpha 6 slightly outperformed alpha 8. Test alpha 7 to refine this small interval; retain all other current-best settings and compare both score and artifact size.
- Class: follow-up parameter refinement around the promising L1 setting.
- Result: commit `3db1a28`, Eval AUC `0.7623` (`ok`, 41.6s total; 10.5s training), artifact 18.5 MB. Kept as the new best, +0.0014 over alpha 6.

### Experiment 59 — probe between alpha 7 and 8

- Hypothesis: alpha 7 outperformed both 6 and the earlier 8 result. Test 7.5 to check whether a slightly stronger threshold can improve on this local optimum.
- Class: follow-up parameter refinement around the best L1 setting.
- Result: commit `2a3755f`, Eval AUC `0.7619` (`ok`, 41.6s total; 10.4s training), artifact 17.8 MB. Discarded and reset: 0.0004 below alpha 7.

### Experiment 60 — probe below alpha 7

- Hypothesis: alpha 7 is above alpha 6 and alpha 7.5, while alpha 6 was slightly lower. Test 6.5 to refine the L1 threshold immediately below the current optimum; keep the remaining best settings fixed.
- Class: follow-up parameter refinement around the best L1 setting.
- Result: commit `a09baa1`, Eval AUC `0.7616` (`ok`, 41.6s total; 10.3s training), artifact 18.0 MB. Discarded and reset: 0.0007 below alpha 7.

### Synthesis after Experiment 60

- Best checkpoint: loss-guided trees, unlimited depth, `max_leaves=96`, `reg_lambda=64`, `reg_alpha=7`, 800 estimators, learning rate 0.05, gamma 0.1, categorical split cap 8; AUC 0.7623 at commit `3db1a28` (18.5 MB artifact).
- The new direction in experiments 51–60 was the L1/L2 combination. L2=64 improved the loss-guided model; adding alpha 4 then 8 raised AUC again and cut the artifact from 36.1 to 13.7 MB. Stronger alpha 16/12/10 underperformed. Fine tuning found alpha 7 best among 6, 6.5, 7, 7.5, 8, 10, 12, and 16. Alpha 6 was close; 7.5, 6.5, and higher settings scored lower.
- Min-child 2 under the current architecture slightly hurt, even though it reduced artifact size. The earlier 5 setting was also too restrictive on the depthwise model. Avoid increasing this floor.
- Current theory: with loss-guided growth, strong L2 plus a moderate L1 threshold balances small-leaf variance and weak updates. More L1 quickly removes useful signal. The most useful fresh direction may be improving numeric split resolution or tuning learning rate/rounds with the new regularization mix.
- Per the experiment protocol, research new directions before Experiment 61.

### Research check after Experiment 60

- The official [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says `max_bin` controls the number of buckets for continuous features under `hist`/`approx`, and that more bins improve split optimality at higher compute cost. This is a fresh direction for the two numerical predictors (`CRSDepTime`, `Distance`): finer thresholds may add signal without disturbing the categorical and leaf-weight regularization that has worked well.
- Experiment 61 will raise `max_bin` from its default 256 to 512, keeping the alpha-7/lambda-64 model fixed. The current training time is about 10 seconds, so the expected extra cost remains comfortably below the harness training limit.

### Experiment 61 — increase numeric split resolution

- Hypothesis: doubling histogram bins gives the loss-guided model more candidate split points for scheduled departure time and distance. Test `max_bin=512` to see whether finer numeric thresholds improve AUC; keep all other current-best settings fixed.
- Class: exploration of numeric split resolution, motivated by the official XGBoost parameter guide.
- Result: commit `5ff2100`, Eval AUC `0.7616` (`ok`, 41.3s total; 10.3s training), artifact 18.1 MB. Discarded and reset: more bins reduced AUC by 0.0007 versus the default 256.

### Experiment 62 — test coarser numeric bins

- Hypothesis: `max_bin=512` underperformed the default. Test 128 to see whether coarser thresholds regularize the numerical predictors and improve held-out AUC; keep the same alpha-7/lambda-64 configuration.
- Class: follow-up to the numeric split resolution experiment.
- Result: commit `5dda787`, Eval AUC `0.7615` (`ok`, 41.8s total; 10.7s training), artifact 18.6 MB. Discarded and reset: 128 bins scored 0.0008 below the default 256.

### Experiment 63 — extend boosting with sparse leaf updates

- Hypothesis: 800 estimators slightly improved over 700 under L2=64 before adding L1; with alpha 7 zeroing weak leaf updates, 900 rounds may add useful refinements without the same overfit cost. Test 900 and compare with the current 800-round best.
- Class: follow-up to the current promising regularized model.
- Result: commit `ec951dd`, Eval AUC `0.7623` (`ok`, 42.2s total; 10.6s training), artifact 18.6 MB. Discarded and reset: tied the 800-round best at four decimals but had a larger artifact.

### Experiment 64 — reduce boosting rounds

- Hypothesis: 900 rounds tied 800 at four decimals but had a larger artifact. Test 750 rounds to see if a shorter ensemble retains the best AUC with a smaller artifact.
- Class: follow-up/simplicity test around the best boosting count.
- Result: commit `f75e74e`, Eval AUC `0.7622` (`ok`, 41.8s total; 10.4s training), artifact 17.8 MB. Discarded and reset: below the 800-round best by 0.0001.

### Experiment 65 — expand leaves under L1/L2 regularization

- Hypothesis: 128 leaves hurt the earlier model with weak weight regularization, but alpha 7 and lambda 64 may suppress the extra weak leaf updates. Test `max_leaves=128` with the current best regularization to see whether additional loss-guided splits improve AUC.
- Class: follow-up interaction test between leaf budget and the successful L1/L2 settings.
- Result: commit `5d55e23`, Eval AUC `0.7632` (`ok`, 45.3s total; 13.9s training), artifact 23.1 MB. Kept as the new best, +0.0009 over 96 leaves under the same L1/L2 settings.

### Experiment 66 — continue regularized leaf expansion

- Hypothesis: 128 leaves improved over 96 under alpha 7/lambda 64, unlike the earlier weakly regularized 128-leaf model. Test 160 leaves to see whether the gain continues or the larger capacity begins to overfit.
- Class: follow-up leaf-budget test under the successful L1/L2 combination.
- Result: commit `d24d171`, Eval AUC `0.7635` (`ok`, 47.1s total; 15.7s training), artifact 26.9 MB. Kept as the new best, +0.0003 over 128 leaves.

### Experiment 67 — continue regularized leaf expansion

- Hypothesis: AUC continued to rise from 96 to 128 to 160 leaves under L1/L2. Test 192 leaves, watching for overfit and the increasing artifact/training cost.
- Class: follow-up leaf-budget test under the successful L1/L2 combination.
- Result: commit `91a86f8`, Eval AUC `0.7642` (`ok`, 49.4s total; 17.6s training), artifact 30.6 MB. Kept as the new best, +0.0007 over 160 leaves.

### Experiment 68 — continue regularized leaf expansion

- Hypothesis: AUC still improved at 192 leaves. Test 224 leaves to see if more high-gain asymmetric splits continue to help under alpha 7/lambda 64.
- Class: follow-up leaf-budget test under the successful L1/L2 combination.
- Result: commit `cb8b6d4`, Eval AUC `0.7643` (`ok`, 51.0s total; 19.0s training), artifact 33.7 MB. Kept as the new best, +0.0001 over 192 leaves.

### Experiment 69 — check the next leaf-cap point

- Hypothesis: the 224-leaf gain was very small, but still positive. Test 256 leaves once to establish whether the current upward trend continues; if AUC stalls or falls, stop expanding and return to regularization or boosting-count tuning.
- Class: follow-up leaf-budget test under the successful L1/L2 combination.
- Result: commit `fb30572`, Eval AUC `0.7646` (`ok`, 53.3s total; 21.7s training), artifact 36.9 MB. Kept as the new best, +0.0003 over 224 leaves.

### Experiment 70 — continue leaf-cap search

- Hypothesis: 256 leaves improved AUC again under L1/L2, with training at 21.7 seconds. Test 288 leaves to continue the capacity search while remaining below the 60-second training limit.
- Class: follow-up leaf-budget test under the successful L1/L2 combination.
- Result: commit `5932a46`, Eval AUC `0.7646` (`ok`, 55.4s total; 23.5s training), artifact 39.8 MB. Discarded and reset: tied 256 leaves at four decimals with a larger artifact.

### Synthesis after Experiment 70

- Best checkpoint: loss-guided growth, unlimited depth, `max_leaves=256`, `reg_lambda=64`, `reg_alpha=7`, 800 estimators, learning rate 0.05, gamma 0.1, `max_cat_threshold=8`; AUC 0.7646 at commit `fb30572` (36.9 MB artifact).
- Under the successful L1/L2 mix, increasing the leaf cap improved results from 96 to 128 (+0.0009), 160 (+0.0003), 192 (+0.0007), 224 (+0.0001), then 256 (+0.0003). At 288, AUC tied the 256-leaf model while the artifact grew by 2.9 MB. The useful region appears near 256.
- `max_bin=512` and 128 both scored below the default 256. 750 and 900 rounds were slightly worse or tied versus 800, so keep 800 while testing other dimensions.
- Current best is the combined result of loss-guided split allocation, high L2, moderate L1, and a wider leaf budget. The next promising direction is a smaller learning rate with a proportional increase in rounds, which may smooth updates without reducing total boosting progress. Research this before Experiment 71.

### Research check after Experiment 70

- The official [parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommend reducing `eta` as an overfit-control option and increasing the round count to compensate. The [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes eta as a shrinkage factor on each tree's update.
- Experiment 71 will test `learning_rate=0.04` with 1,000 rounds, keeping the current product at 40 (`0.05 × 800`) while making each update smaller and more numerous. This is an approximate comparison, not an equivalent fit; it tests whether a smoother path helps the regularized high-capacity model. Training time is expected to be about 27 seconds, below the limit.

### Experiment 71 — smaller learning steps

- Hypothesis: with strong L1/L2 and a 256-leaf cap, smaller per-tree updates may refine the model more smoothly. Test 0.04 learning rate and 1,000 rounds against the current 0.05/800 best, with all other settings fixed.
- Class: exploration of the eta/rounds tradeoff, motivated by the official XGBoost tuning guidance.
- Result: commit `e3817f1`, Eval AUC `0.7650` (`ok`, 58.2s total; 26.2s training), artifact 46.1 MB. Kept as the new best, +0.0004 over 0.05/800.

### Experiment 72 — reduce step size further

- Hypothesis: reducing eta from 0.05 to 0.04 with a proportional round increase improved AUC. Test eta 0.03 with 1,333 rounds (approximately the same eta×rounds product of 40) to see whether smoother updates continue to help. Training should remain within the harness limit.
- Class: follow-up to a promising eta/rounds setting.
- Result: commit `c85f370`, Eval AUC `0.7649` (`ok`, 68.3s total; 36.1s training), artifact 61.4 MB. Discarded and reset: 0.0001 below the 0.04/1,000 best with a larger artifact.

### Experiment 73 — refine the learning rate

- Hypothesis: eta 0.04/1,000 slightly outperformed 0.03/1,333. Test the midpoint eta 0.045 with 889 rounds, keeping the eta×rounds product near 40, to refine the promising range without excessive model growth.
- Class: follow-up parameter refinement around the improved eta/rounds result.
- Result: commit `c688fed`, Eval AUC `0.7648` (`ok`, 55.8s total; 24.1s training), artifact 40.9 MB. Discarded and reset: below eta 0.04/1,000 by 0.0002.

### Experiment 74 — recheck L1 under wider trees

- Hypothesis: alpha 7 was optimal for the 96-leaf model, but the current 256-leaf cap permits more small leaf updates. Test alpha 8 with the current 0.04/1,000 configuration to see if stronger thresholding now improves AUC or cuts artifact size.
- Class: follow-up interaction test between L1 strength and the wider leaf budget.
- Result: commit `da3ed98`, Eval AUC `0.7648` (`ok`, 57.7s total; 25.5s training), artifact 43.0 MB. Discarded and reset: below alpha 7 by 0.0002 under the same tree budget.

### Experiment 75 — test a milder L1 threshold with wide trees

- Hypothesis: under 256 leaves, alpha 8 was slightly below alpha 7. Test alpha 6.5 to see whether a milder L1 threshold improves the current 0.04/1,000 model.
- Class: follow-up interaction test between L1 strength and the wider leaf budget.
- Result: commit `10de2b5`, Eval AUC `0.7641` (`ok`, 58.7s total; 26.8s training), artifact 48.0 MB. Discarded and reset: alpha 6.5 was 0.0009 below alpha 7.

### Experiment 76 — test more rounds at eta 0.04

- Hypothesis: eta 0.04/1,000 is the best setting tested; 0.03/1,333 and 0.045/889 were slightly lower. Test 1,100 rounds at eta 0.04 to see whether this configuration is still underfit.
- Class: follow-up to the best eta/rounds result.
- Result: commit `af93ad8`, Eval AUC `0.7649` (`ok`, 61.0s total; 28.9s training), artifact 49.8 MB. Discarded and reset: 1,100 rounds was 0.0001 below the 1,000-round best.

### Experiment 77 — strengthen split-gain regularization

- Hypothesis: the expanded 256-leaf model may benefit from a slightly higher split threshold to suppress marginal branches. Test `gamma=0.15` under the current 0.04/1,000 alpha-7/lambda-64 setup; the same gamma was near-optimal under the earlier depthwise model, so this checks its interaction with loss-guided growth.
- Class: follow-up regularization interaction test.
- Result: commit `993b867`, Eval AUC `0.7652` (`ok`, 59.7s total; 27.8s training), artifact 46.1 MB. Kept as the new best, +0.0002 over gamma 0.1.

### Experiment 78 — continue gamma refinement

- Hypothesis: gamma 0.15 slightly improved the wide, regularized model. Test gamma 0.2 to see if further pruning of marginal branches helps or begins to remove useful splits.
- Class: follow-up split-gain regularization test.
- Result: commit `5e5c608`, Eval AUC `0.7651` (`ok`, 55.1s total; 23.1s training), artifact 40.3 MB. Discarded and reset: slightly below gamma 0.15.

### Experiment 79 — refine gamma above 0.15

- Hypothesis: gamma 0.15 scored 0.7652, while 0.2 scored 0.7651. Test 0.175 to refine the current best split-gain penalty.
- Class: follow-up parameter refinement.
- Result: commit `15e9958`, Eval AUC `0.7651` (`ok`, 57.4s total; 25.4s training), artifact 45.8 MB. Discarded and reset: slightly below gamma 0.15.

### Experiment 80 — refine gamma below 0.15

- Hypothesis: gamma 0.15 scored 0.7652, while 0.1 scored 0.7650 and 0.175 scored 0.7651. Test 0.125 as the lower midpoint to see if it improves on 0.15 before the run budget expires.
- Class: follow-up parameter refinement around the current best.
- Result: commit `d546b83`, Eval AUC `0.7650` (`ok`, 58.7s total; 26.6s training), artifact 46.1 MB. Discarded and reset: below gamma 0.15 by 0.0002.

### Synthesis after Experiment 80

- Current best is commit `993b867`: loss-guided growth, max leaves 256, lambda 64, alpha 7, gamma 0.15, learning rate 0.04, 1,000 rounds, categorical threshold 8; AUC 0.7652 with a 46.1 MB artifact.
- Since Experiment 70, the 0.04/1,000 learning-rate configuration improved over 0.05/800. Eta 0.03/1,333 and 0.045/889 were slightly worse; 1,100 rounds at eta .04 was also slightly worse. A leaf-cap search under strong L1/L2 raised AUC from 0.7623 at 96 leaves to 0.7646 at 256; 288 tied but enlarged the artifact. Gamma 0.15 slightly edged .1, .175, .2, and .125.
- Higher histogram resolution did not help: max_bin 128 and 512 both lost to the default 256. Alpha 7 remained best under 256 leaves; alpha 8 and 6.5 were lower. The model benefits from the strong L1/L2 combination, loss-guided capacity, and categorical cap 8. Future work could explore interactions or a smaller learning rate around the current best if another run is authorized.

### Final summary

Best Eval AUC: 0.7652 at commit `993b867` (branch `sep30`). The largest gains came from loss-guided trees, stronger L2, moderate L1, and expanding the leaf budget; categorical split cap 8 also helped. Higher `max_bin`, min-child 2, gamma outside 0.15, alpha outside 7, and alternative round/learning-rate points did not improve the score. The final kept model used 256 leaves, `reg_lambda=64`, `reg_alpha=7`, gamma 0.15, learning rate 0.04, 1,000 trees, and `max_cat_threshold=8`.
