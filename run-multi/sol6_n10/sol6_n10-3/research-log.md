# sep29 research log

Metric: row-by-row Eval AUC from `python3 harness.py run`. Training uses only `data/train.csv`; held-out data is off limits.

## Research before first change

- XGBoost's [parameter tuning guide](https://xgboost.readthedocs.io/en/release_2.0.0/tutorials/param_tuning.html) recommends tuning tree complexity (`max_depth`, `min_child_weight`, `gamma`), row and column sampling (`subsample`, `colsample_bytree`), and learning rate with the number of rounds.
- The [categorical data tutorial](https://xgboost.readthedocs.io/en/release_3.1.0/tutorials/categorical.html) explains native categorical splits and `max_cat_to_onehot`, relevant to `Origin`, `Dest`, and carrier.
- This [air travel delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) identifies scheduled time, route, carrier, and calendar context as useful flight features. The available data limits us to row-local transformations of these fields.

## Experiments

1. `92e43e6` baseline, unchanged starter: Eval AUC 0.7203, keep. Training 0.2s; total 31.4s.
2. Follow-up hypothesis: 30 trees underfit. Increase `n_estimators` to 300 while holding everything else fixed. XGBoost's tuning guide motivates testing a larger boosting budget; later results will show if overfitting appears.
   Result `aabb41d`: Eval AUC 0.7342, keep (+0.0139); training 1.7s. The starter was underfit.
3. Follow-up hypothesis: boosting may still be underfit at 300 trees. Try 1,000 trees at the same learning rate. This tests the saturation point of the promising change; training is still far below the 60s limit.
   Result `1801e9c`: Eval AUC 0.7253, discard (-0.0089 vs best). More depth-6 rounds overfit badly.
4. Follow-up hypothesis: shallow trees can use more boosting rounds without the same variance. Try 1,000 trees at depth 3, isolating the depth effect relative to experiment 3. XGBoost's tuning guide identifies tree depth as a key overfitting control.
   Result `b50333d`: Eval AUC 0.7351, keep (+0.0009). Shallow trees make longer boosting viable, though the gain is small.
5. Exploration hypothesis: scheduled departure hour as a categorical feature will expose daily cycles to depth-3 trees with fewer splits. It is computed from each row's `CRSDepTime`, so evaluation semantics match training. [Li et al. (2021)](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057) describe scheduled departure time in hours as a categorical factor in delay models. Keep the original time variable too.
   Result `bf2dca3`: Eval AUC 0.7356, keep (+0.0005). Extra feature costs little and captures some signal.
6. Exploration hypothesis: a numeric day-of-year feature will let shallow trees split contiguous seasonal or date periods using one node. It is derived row by row from month and day, leaving the original categories intact. [This flight delay study](https://pmc.ncbi.nlm.nih.gov/articles/PMC12685205/) includes day-of-year among engineered temporal features.
   Result `0e7196d`: Eval AUC 0.7386, keep (+0.0030). Contiguous date signal matters.
7. Exploration hypothesis: an Origin-Dest route category can represent pair-specific effects with one split, especially useful at depth 3. [Li et al. (2021)](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057) list Origin-Destination pairs among flight-delay factors. The lookup is fitted on train and applied per row; it uses no counts or target outcomes.
   Result `c60fc72`: Eval AUC 0.7105, discard (-0.0281). High-cardinality route representation overfit and slowed evaluation to 50.7s.
8. Exploration hypothesis: one-hot splits for the smaller categorical variables may preserve distinct calendar/carrier/hour effects better than category partitioning. Set `max_cat_to_onehot=32`, leaving Origin and Dest partitioned. The [XGBoost categorical tutorial](https://xgboost.readthedocs.io/en/release_3.1.0/tutorials/categorical.html) explains this parameter.
   Result `eb88897`: Eval AUC 0.7317, discard (-0.0069). Partitioning is better here.
9. Exploration hypothesis: distance to a major travel holiday may expose demand and scheduling shifts hidden within date. [Naul (2008)](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) uses holiday proximity for departure delay prediction. Use only static 2005 calendar dates and each row's DayOfYear; the original date feature remains.
   Result `2297277`: Eval AUC 0.7383, discard (-0.0003). Calendar proximity did not add useful signal beyond DayOfYear.
10. Exploration hypothesis: leaf constraints may reduce overfitting on rare airport/category patterns. Set `min_child_weight=10` at the best feature set. The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) says larger values make splits more conservative.
   Result `1c1c213`: Eval AUC 0.7388, keep (+0.0002). Small gain; warrants testing complementary regularization.

## Synthesis after 10 experiments

Best so far: `1c1c213`, Eval AUC 0.7388. Increasing trees from 30 to 300 gave the largest gain; 1,000 depth-6 trees overfit, but depth 3 with 1,000 trees recovered a small gain. Numeric DayOfYear added 0.0030, and departure hour added 0.0005. A 4,290-level route category was harmful and slower. One-hot splits for compact categories hurt, suggesting partitioning is useful. Holiday proximity was redundant with the date feature. The working theory is that temporal patterns benefit from compact derived features, while high-cardinality interactions need more restraint. Next test row/column sampling and other XGBoost regularization before larger feature additions.

Fresh research: [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) says `subsample` samples rows per tree and `colsample_bytree` samples columns per tree; `grow_policy=lossguide` prioritizes nodes with the largest loss reduction. [XGBoost's tuning guide](https://xgboost.readthedocs.io/en/release_2.0.0/tutorials/param_tuning.html) recommends sampling as an overfitting control. The next experiment isolates row sampling.

11. Exploration hypothesis: `subsample=0.8` can reduce variance among 1,000 shallow trees while keeping enough data for each split. All other settings stay fixed.
   Result `3e6f51e`: Eval AUC 0.7227, discard (-0.0161). Row sampling is costly here, likely because each tree needs the available airport/date cases.
12. Exploration hypothesis: `colsample_bytree=0.8` may reduce reliance on a few strong features while retaining full row coverage. Isolate column sampling from the failed row-sampling change, following the XGBoost tuning guide above.
   Result `b324691`: Eval AUC 0.7390, keep (+0.0002). Column sampling helped slightly, unlike row sampling.
13. Exploration hypothesis: a finer histogram (`max_bin=512` vs default 256) might place useful thresholds more accurately for scheduled time and distance, which have over 1,000 distinct values each. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) describe the accuracy/computation tradeoff.
   Result `8b377a2`: Eval AUC 0.7391, keep (+0.0001). Negligible, but no measured runtime cost.
14. Exploration hypothesis: treating DayOfYear as a categorical date identifier alongside its numeric version may capture noncontiguous high-delay dates shared by many flights in the same year. Each date has substantially more training rows than a route, so the earlier route failure does not rule this out. [Naul (2008)](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) used DayOfYear and discussed weather-driven flight-delay variability; XGBoost's [categorical tutorial](https://xgboost.readthedocs.io/en/release_3.1.0/tutorials/categorical.html) motivates partitioning categories by response gradients.
   Result `73aae74`: Eval AUC 0.7555, keep (+0.0164). Date-specific shared conditions appear to be the strongest new signal.
15. Follow-up hypothesis: allowing up to 128 categories in a partition split may capture more date-specific patterns than the default cap, at possible overfitting/computation cost. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) say `max_cat_threshold` limits categories considered to prevent overfitting. Test 128 while holding all else fixed.
   Result `e5dd442`: Eval AUC 0.7562, keep (+0.0007). Wider partitions help date signal modestly.
16. Follow-up hypothesis: raising `max_cat_threshold` from 128 to 256 tests whether more date categories further improve AUC, or whether the 128 cap is already enough. This is a saturation test of experiment 15.
   Result `5526f57`: Eval AUC 0.7551, discard (-0.0011). The 128 cap better controls categorical variance.
17. Follow-up hypothesis: depth 4 may represent date-by-airport or date-by-time interactions that depth 3 misses. Keep the 128 category cap and 1,000 trees to isolate depth. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) warn greater depth increases overfitting risk; `min_child_weight=10` may limit it.
   Result `b7c9a07`: Eval AUC 0.7525, discard (-0.0037). Depth 4 overfits despite the leaf constraint.
18. Ablation hypothesis: the stronger DateCat feature may need fewer rounds. Try 600 depth-3 trees in place of 1,000, preserving every other feature and parameter. If AUC holds or improves, this is a simpler and faster model.
   Result `78bc4b3`: Eval AUC 0.7558, discard (-0.0004). It saves about 1s of training but the AUC loss and equal code complexity favor 1,000 trees.
   Inspection of the kept model's feature importance (gain) shows CRSDepTime 0.384, DateCat 0.132, DepHour 0.124, then Origin 0.076 and Month 0.074. Time and date dominate; distance and day-of-month are weakest. This is diagnostic only, not an evaluation metric.
19. Follow-up hypothesis: 600 rounds were slightly worse than 1,000, so 1,400 may improve further before overfitting. This tests the other side of the boosting-budget curve at fixed depth 3 and fixed features.
   Result `892bd75`: Eval AUC 0.7536, discard (-0.0026). The best observed boosting budget is around 1,000 rounds.
20. Exploration hypothesis: a date-by-half-day categorical feature could capture disruption that begins or dissipates during a date. With two periods, each category has substantially more support than the failed route feature. [Hsiao and Hansen (2006)](https://journals.sagepub.com/doi/10.1177/0361198106195100113) document time-of-day effects and weather interactions in U.S. airline delays. The feature is row-local: date from Month/DayofMonth and half-day from CRSDepTime.
   Result `db40654`: Eval AUC 0.7521, discard (-0.0041). DateCat and hour as separate features are better than this interaction category.

## Synthesis after 20 experiments

Best: `e5dd442`, Eval AUC 0.7562. DateCat gave the largest gain of the second block (+0.0164); a 128-category split cap added +0.0007, while 256 reversed the gain. Depth 4, 600 or 1,400 rounds, and a date-by-half-day interaction all lost AUC. The evidence favors a shallow, moderately long model with a supported categorical date. Stronger interactions seem to introduce variance rather than useful signal. The next direction is feature ablation and different tree-growth/regularization, with priority on simple changes.

Fresh research: [Naul (2008)](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) uses distance only for arrival prediction in a flight-delay model. [XGBoost tree methods](https://xgboost.readthedocs.io/en/release_3.3.0/treemethod.html) explains `hist` and best-first growth, and the [parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `grow_policy`, `gamma`, and leaf regularization. These suggest testing whether weak features can be removed before increasing complexity.

21. Ablation hypothesis: remove `Distance` from the predictor set. It had only 0.013 gain importance in the kept model; departure delay occurs before travel distance can affect flight progress. This is a one-line simplification if AUC remains comparable.
   Result `d6cb43a`: Eval AUC 0.7558 (-0.0004 vs peak), keep as a one-feature simplification under the program's near-equal rule. Keep `e5dd442` (0.7562) as the pure AUC reference until another candidate surpasses it.
22. Ablation hypothesis: raw `DayofMonth` may be redundant with numeric and categorical DayOfYear, which encode the exact date. Removing it may simplify and reduce overfitting while retaining date signal.
   Result `eb77226`: Eval AUC 0.7560, keep (+0.0002 vs prior simplified candidate; -0.0002 vs peak). One fewer input feature and faster evaluation.
23. Ablation hypothesis: categorical DateCat may subsume numeric DayOfYear. Keep the row-local day calculation only as an intermediate for DateCat and remove the numeric model input. This simplifies the feature set without removing date information.
   Result `dc96ed4`: Eval AUC 0.7574, keep (+0.0014 vs prior; +0.0012 vs prior peak). Numeric DayOfYear competed with its more useful categorical representation.
24. Ablation hypothesis: raw DayOfWeek may also be partly redundant with exact DateCat. Remove it to test whether the smaller feature set improves categorical split allocation; if weekly pattern sharing matters, AUC should fall.
   Result `cc2fe17`: Eval AUC 0.7567 (-0.0007 vs peak), keep as a near-equal one-feature simplification; evaluation also fell from 35.7s to 32.1s. The highest-AUC reference remains `dc96ed4` at 0.7574.
25. Exploration hypothesis: a carrier-by-departure-hour category may capture airline-specific daily delay accumulation with one split. [This UC Berkeley flight-delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) reports delays by hour for each carrier rising late at night. Unlike DateHalfDay, carrier-hour pairs recur across many dates and have much more support. The feature is row-local using a carrier-code lookup fitted on train.
   Result `7da8447`: Eval AUC 0.7522, discard (-0.0045). The separate carrier and time inputs generalize better than their high-cardinality combination.
26. Exploration hypothesis: best-first tree growth with eight leaves may capture useful asymmetric interactions without giving every path the extra depth that hurt in experiment 17. Set `grow_policy=lossguide`, `max_leaves=8`, and `max_depth=0` (leaf count controls size). [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) describe loss-guided growth as splitting the node with highest loss change.
   Result `e1dfff9`: Eval AUC 0.7570, keep (+0.0003 vs prior simplified candidate). Selective asymmetric growth helped slightly.
27. Follow-up hypothesis: twelve loss-guided leaves may capture a few useful extra date/airport interactions without the full depth-4 tree shape that previously overfit. Only `max_leaves` changes from eight to twelve.
   Result `2ef35d5`: Eval AUC 0.7556, discard (-0.0014). Extra leaves overfit.
28. Follow-up hypothesis: six loss-guided leaves may reduce variance after twelve was too large. This tests the conservative side of the eight-leaf model and may yield a smaller artifact if AUC holds.
   Result `f1219ae`: Eval AUC 0.7566, discard (-0.0004 vs eight leaves). Eight remains the best leaf budget.
29. Exploration hypothesis: stronger L2 leaf regularization (`reg_lambda=5` vs default 1) may shrink noisy date-specific leaf scores without removing informative splits. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) describe lambda as a conservative penalty on leaf weights.
   Result `ceb9a3e`: Eval AUC 0.7584, keep (+0.0014 vs prior; new best). Leaf score shrinkage is useful with DateCat.
30. Follow-up hypothesis: `reg_lambda=10` may further regularize date-specific leaves. This tests whether the gain at 5 continues or has passed the optimum.
   Result `e844753`: Eval AUC 0.7574, discard (-0.0010). L2=5 is better.

## Synthesis after 30 experiments

Best: `ceb9a3e`, Eval AUC 0.7584. Removing Distance, DayofMonth, and numeric DayOfYear reduced the feature set and eventually lifted AUC above the prior peak; removing DayOfWeek cost only 0.0007 and shortened scoring, so it remains in the simplified branch. Loss-guided eight-leaf trees added 0.0003; six or twelve leaves were worse. L2 regularization at 5 added 0.0014; 10 was too strong. The current theory is that a compact feature set with categorical date benefits from moderate leaf shrinkage and selective, shallow interactions. The next block explores a different tree approximation and targeted regularization before adding complexity.

Fresh research: [XGBoost tree methods](https://xgboost.readthedocs.io/en/release_3.3.0/treemethod.html) says `approx` uses Hessian-weighted quantile sketches, unlike `hist`'s global sketch, and supports categorical data and loss-guided growth. The [DART tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) suggests tree dropout as another overfitting control but warns it trains more slowly. We will test the simpler tree-method change first.

31. Exploration hypothesis: `tree_method="approx"` may make more suitable splits for logistic loss by refreshing Hessian-weighted sketches, at a training-time cost. All other settings remain the same.
   Result `a5c0bf6`: Eval AUC 0.7575, discard (-0.0009); training rose to 18.9s from ~3s. No benefit for the cost.
32. Exploration hypothesis: `gamma=1` can prune weak date/category splits that fit noise, complementing L2 leaf shrinkage. The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) says gamma is the minimum loss reduction needed to split.
   Result `613f118`: Eval AUC 0.7578, discard (-0.0006). Split pruning saved ~0.8s training but hurt ranking slightly and added a parameter.
33. Ablation hypothesis: Month may now be redundant with DateCat, which identifies the exact 2005 date. It has the lowest gain importance (0.037) of the current compact model. Remove Month from the predictor columns while retaining it for row-local date calculation.
   Result `58420ea`: Eval AUC 0.7573, discard (-0.0011). Month still carries broad seasonal signal that DateCat alone does not efficiently share.

Plateau research after three discards: [This temporal feature engineering study](https://www.mdpi.com/2079-9292/13/24/4910) explicitly uses week of year to capture seasonal and holiday-period patterns. [Li et al. (2021)](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057) also note seasonal effects in flight delay. The last changes focused on tree settings or removing Month; a weekly category is a different, low-cardinality date representation.

34. Exploration hypothesis: a 53-level WeekOfYear category may share near-date conditions across adjacent days while DateCat captures day-specific anomalies. It is row-local from Month/DayofMonth and has far more support per category than route/date-half-day interactions.
   Result `4c20105`: Eval AUC 0.7567, discard (-0.0017). Month plus exact date capture the useful temporal structure better.
35. Follow-up to experiment 24: restoring raw DayOfWeek on the stronger loss-guided, L2-regularized model may recapture weekly pattern sharing. Its removal previously cost 0.0007; that ablation was on a different model, so this tests whether the effect persists.
   Result `def75a8`: Eval AUC 0.7569, discard (-0.0015). Regularization and loss-guided growth changed which calendar features help; the compact set remains preferable.

Research after the feature plateau: [XGBoost's random forest tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) says `num_parallel_tree>1` with multiple boosting rounds trains boosted forests, and column sampling makes the parallel trees diverse. [Malinin et al. (2020)](https://arxiv.org/abs/2006.10562) study ensembles of gradient-boosted models and their model diversity, while noting extra time and memory cost. A built-in parallel-tree setting offers a small-code test of variance reduction.

36. Exploration hypothesis: three parallel trees per boosting round may average over column-sampling variation and improve rankings. Set `num_parallel_tree=3` with the existing `colsample_bytree=0.8`; keep all other model parameters fixed.
   Result `ab51bca`: Eval AUC 0.7591, keep (+0.0007; new best). Training rose to 12.0s but remains within limit.
37. Follow-up hypothesis: five parallel trees may reduce column-sampling variance further. This saturation test raises only `num_parallel_tree` from three to five; expect a larger artifact and slower training.
   Result `48dd647`: Eval AUC 0.7603, keep (+0.0012; new best). Training 19.9s, still within 60s.
38. Follow-up hypothesis: eight parallel trees may continue the variance-reduction trend, though training cost and artifact size rise. Test before the 60s training limit becomes binding.
   Result `66e460e`: Eval AUC 0.7598, discard (-0.0005); training 33.0s. The gain peaks below eight trees.
39. Follow-up hypothesis: six parallel trees may strike a better balance than five or eight. This tests a narrow point near the observed optimum, with a smaller time cost than eight.
   Result `5699043`: Eval AUC 0.7598, discard (-0.0005); five trees train faster at 19.9s vs 23.6s.
40. Ablation hypothesis: with five parallel trees in each round, 700 rounds may preserve the ensemble benefit while reducing model size and training time. The single-tree 600-round test was only 0.0004 below 1,000, so a shorter boosted forest is worth checking.
   Result `7d54de1`: Eval AUC 0.7605, keep (+0.0002; new best), training 13.9s vs 19.9s at 1,000 rounds.

## Synthesis after 40 experiments

Best: `7d54de1`, Eval AUC 0.7605. Experiments 31-35 (`approx`, gamma, Month removal, WeekOfYear, weekday restoration) did not beat the compact, regularized histogram model. The different direction at experiment 36 did: boosted forests with 3 and then 5 parallel trees improved AUC. Six and eight trees were slower and lower, so five is the current size. Reducing rounds from 1,000 to 700 slightly improved AUC and cut training to 13.9s. The next question is whether less boosting or a smaller learning rate can improve this five-tree forest.

Fresh research: [XGBoost's boosted-forest tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) confirms that `num_parallel_tree>1` with multiple boosting rounds fits a forest each round. The [parameter tuning guide](https://xgboost.readthedocs.io/en/release_2.0.0/tutorials/param_tuning.html) says the learning rate and number of rounds should be tuned together. The [scikit-learn interface guide](https://xgboost.readthedocs.io/en/stable/python/sklearn_estimator.html) documents early stopping with an internal validation split, which remains a possible later direction if fixed-round tuning stalls.

41. Ablation hypothesis: 500 rounds may further reduce overfitting and model size; 700 improved over 1,000 at five parallel trees. Hold learning rate at 0.1 to isolate the round count.
   Result `6c10b30`: Eval AUC 0.7582, discard (-0.0023). The 500-round forest underfits; 700 remains better.
42. Exploration hypothesis: halve learning rate to 0.05 and double rounds to 1,400 to preserve roughly the same total step length with a smoother optimization path. [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/release_2.0.0/tutorials/param_tuning.html) recommends increasing rounds when reducing eta. Training should remain within 60s.
   Result `186b6c9`: Eval AUC 0.7600, discard (-0.0005); training 28.6s. The smoother path did not offset its cost.
43. Exploration hypothesis: with five trees per round, each tree may benefit from seeing key time/date features more often. Raise `colsample_bytree` from 0.8 to 0.9 to preserve some diversity while reducing omitted-feature risk. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) define the per-tree column sample ratio.
   Result `b89a1ec`: Eval AUC 0.7586, discard (-0.0019). More column diversity appears beneficial.
44. Follow-up hypothesis: lower `colsample_bytree` to 0.7 to test whether additional diversity helps the five-tree forest. This is the opposite side of the successful 0.8 setting after 0.9 reduced AUC.
   Result `274c276`: Eval AUC 0.7602, discard (-0.0003). The 0.8 setting remains the best measured balance.

Research after four parameter discards: [This flight-delay feature-engineering study](https://www.mdpi.com/2079-9292/13/24/4910) describes extracting the scheduled departure minute to represent within-hour variation in congestion. The present model has raw HHMM time and categorical hour, but a shallow tree may need several splits to share minute-of-hour patterns across hours. This gives a different, low-cardinality direction.

45. Exploration hypothesis: `DepMinute = CRSDepTime % 100` may expose recurring schedule-minute effects across hours using one split. It is numeric, row-local, and requires one line in `prepare`.
   Result `b1596fe`: Eval AUC 0.7585, discard (-0.0020). A numeric within-hour trend did not help.
46. Follow-up hypothesis: minute-of-hour effects may be nonmonotonic, with scheduled flights clustered around specific minute marks. Treat the 0-59 minute as categorical rather than numeric, so XGBoost can group favored minute marks in one partition split. This tests a different representation of the same domain idea, not a minor threshold tweak.
   Result `1ed517e`: Eval AUC 0.7588, discard (-0.0017 vs best). Grouping scheduled minute marks is better than numeric minute, but both add noise to the current model.
47. Exploration hypothesis: the five-tree forest might still fit noisy date/category groups in small leaves. Raise `min_child_weight` from 10 to 20 to require more support per leaf. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) say larger values make the algorithm more conservative.
   Result `c7000a2`: Eval AUC 0.7602, discard (-0.0003). More leaf support did not help.
48. Follow-up hypothesis: `min_child_weight=5` tests the lower side of the best value 10; smaller leaves may preserve useful local date/airport signal that the forest can average across parallel trees.
   Result `3d63b7b`: Eval AUC 0.7601, discard (-0.0004). The best leaf-support value remains 10.
49. Exploration hypothesis: parallel-tree averaging may reduce the need for L2 shrinkage. Lower `reg_lambda` from 5 to 3 while keeping leaf support 10, to test whether some useful date signal was overshrunk.
   Result `5eac36c`: Eval AUC 0.7597, discard (-0.0008). L2=5 remains best.

Plateau research after three small misses: [Zhang et al. (2021)](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12071) report airport delay dependence on time of day, season, and airport scale. [This UC Berkeley project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) highlights time-of-day operations and scheduling. `program.md` gives an allowed pattern for fitting a scheduled-time median lookup on train and mapping it per row in `prepare`. A relative time feature could expose local schedule position without using row counts or target outcomes.

50. Exploration hypothesis: minutes since scheduled departure relative to the origin airport's median scheduled time may capture whether a flight is late in that airport's daily sequence. Fit the median only on `train.csv`; calculate the residual from each row alone in `prepare`.
   Result `74d61e7`: Eval AUC 0.7598, discard (-0.0007). Relative schedule time did not improve on raw scheduled time, categorical hour, and origin.

After 50 trials, the best remains `7d54de1` at 0.7605. Recent single-feature and regularization changes have produced only small regressions. Search next for distinct representations or training methods rather than continuing minute parameter adjustments.

Research after 50: [XGBoost's random-forest tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) confirms `num_parallel_tree` grows a boosted forest at each round. Its [parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) distinguishes column sampling per tree from per node and describes L1 leaf regularization. The [categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains partition splits; a category cap remains relevant to the exact-date feature. The current five-tree forest has helped more than single-tree boosting, so test regularization and sampling that can improve diversity of its trees.

51. Exploration hypothesis: L1 leaf regularization (`reg_alpha=1`) may suppress weak date-specific leaf scores that survive L2 shrinkage, without forcing larger leaves. Keep the boosted forest and all features fixed; this isolates a different regularization mechanism from L2.
   Result `52a21d8`: Eval AUC 0.7608, keep (+0.0003). L1 suppression helps modestly.
52. Follow-up hypothesis: `reg_alpha=2` tests whether stronger sparsity extends the small improvement at 1 or overshrinks useful date and airport leaves. All other settings remain fixed.
   Result `ba669fe`: Eval AUC 0.7600, discard (-0.0008). A single unit of L1 is enough; two overshrinks.
53. Exploration hypothesis: the current `colsample_bytree=0.8` removes one feature for an entire tree. Sampling 80% of features per node with all features available to each tree may let a tree use both date and scheduled time in different branches while still diversifying splits. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) distinguish per-tree and per-node column sampling.
   Result `2f4f665`: Eval AUC 0.7586, discard (-0.0022). The per-tree omissions are more effective for this compact feature set.

Ensemble research: [scikit-learn's soft-voting documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html) defines probability averaging across fitted classifiers. [XGBoost's random-forest tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) notes that random seeds can vary tree construction. The current five-tree boosted forest could still carry seed-specific column-sampling variance; an independently trained copy tests whether averaging that variance helps.

54. Exploration hypothesis: averaging predictions of two independent five-tree boosted forests with seeds 42 and 24 may smooth seed-specific rankings beyond `num_parallel_tree=5`. The second model uses the same full `train.csv` and parameters; `prepare` stays row-local. This doubles training cost, so it needs a clear AUC gain to earn its complexity.
   Result `bafdacc`: Eval AUC 0.7617, keep (+0.0009). Training 28.1s, inside 60s. This is the first meaningful improvement after the single-model plateau; test whether the new seed alone accounts for it before retaining the larger artifact.
55. Ablation hypothesis: seed 24 alone might be better than seed 42 and make the blend unnecessary. Remove the second model and averaging wrapper, use the exact current settings with only seed 24. If AUC is about equal, prefer this much simpler, faster model.
   Result `58f2a14`: Eval AUC 0.7605, discard (-0.0012 vs blend). The gain came from averaging complementary model rankings, not a stronger second seed.
56. Follow-up hypothesis: a third independent seed may further smooth column-sampling variance. Add seed 7 to the probability average, keeping each base model unchanged. The training budget should remain below 60s; this tests whether the ensemble gain has saturated at two models.
   Result `046ebc6`: Eval AUC 0.7619, discard under simplicity criterion. The 0.0002 gain costs a third full model (training 41.4s versus 28.1s and a larger artifact). The two-model blend remains the practical best at 0.7617.
57. Exploration hypothesis: a binary weekend flag may share weekly traffic patterns across otherwise independent exact dates with less fragmentation than restoring the seven-level DayOfWeek category. [This air-transport-network study](https://arxiv.org/abs/1304.2528) reports dependence of delays on day of week. The flag is computed from each row alone.
   [BTS's field definition](https://www.bts.gov/explore-topics-and-geography/modes/aviation/number-40-technical-directive-reporting-time) confirms Monday=1 and Sunday=7, so codes 6/7 identify Saturday/Sunday. Result `ffab648`: Eval AUC 0.7611, discard (-0.0006). DateCat and Month suffice for this coarse weekly contrast.
58. Exploration hypothesis: a depthwise, single-tree booster may make different errors than the loss-guided five-tree forest and improve their probability average. This changes only the second model, using 1,000 depth-3 rounds; it should also make the blend smaller and faster than two five-tree forests. Prior experiment 4 showed depth 3 tolerates longer boosting.
   Result `9423f5d`: Eval AUC 0.7628, keep (+0.0011). Training 16.3s rather than 28.1s for the identical-architecture two-seed blend. Structural diversity is more useful and cheaper here.
59. Follow-up hypothesis: the loss-guided forest was individually stronger in prior trials, so a two-to-one probability weight may preserve more of its rank ordering while adding the depthwise model's complementary signal. Change only the averaging weight from 1:1 to 2:1.
   Result `818d6e5`: Eval AUC 0.7626, discard (-0.0002). The equal blend remains better, suggesting the depthwise member contributes more than its earlier stand-alone scores implied.
60. Follow-up hypothesis: a two-to-one weight on the depthwise member tests the opposite side of the equal blend. If this improves, the depthwise model might be stronger with the newer regularization than its older configuration, and we can simplify or reweight accordingly.
   Result `db5084d`: Eval AUC 0.7625, discard (-0.0003). The equal 1:1 blend is best among the three tested weights.

## Synthesis after 60 experiments

The best kept model is `9423f5d` at 0.7628. L1=1 lifted the five-tree forest from 0.7605 to 0.7608. A second independent forest raised this to 0.7617 but doubled training. Replacing that member with a depthwise 1,000-round model improved AUC to 0.7628 and cut training to 16.3s. A third independent forest delivered only +0.0002 at a substantial cost, so it was discarded. Per-node column sampling, a weekend flag, and both unequal blend weights were worse. The current theory is that complementary tree structures reduce ranking variance more effectively than adding similar trees or coarse calendar features. Next test constraints on the loss-guided member, then other compact architecture changes.

Research after 60: [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) describe `max_depth` as a path-length limit that can coexist with `max_leaves` under loss-guided growth. Its [interaction-constraint tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html) says limiting feature interactions can reduce prediction noise. Its [monotonic-constraint tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html) warns that histogram splits with monotonic constraints can yield shallow trees; that is less attractive for this six-feature model. Test the simple depth cap first.

61. Exploration hypothesis: the loss-guided eight-leaf member can form deep chains on rare date/airport cases. Setting `max_depth=3` while retaining `max_leaves=8` prevents those narrow interactions and may improve generalization; the depthwise second member stays unchanged.
   Result `34222bd`: Eval AUC 0.7611, discard (-0.0017). Deep asymmetric paths are apparently useful in the forest, despite the shallow complementary member.
62. Ablation hypothesis: the depthwise member may gain diversity from weaker leaf penalties, as the earlier single-tree architecture was tested without `reg_lambda=5` or `reg_alpha=1`. Restore default L2=1 and L1=0 only in the second member, leaving the stronger loss-guided forest untouched. If helpful, isolate the two penalties afterward.
   Result `d6b89fe`: Eval AUC 0.7619, discard (-0.0009). The depthwise member also benefits from the stronger leaf penalties in this blend; no need to split the two weaker penalties further.
63. Exploration hypothesis: the depthwise member might need access to all six features in every tree, unlike the five-tree forest where per-tree column sampling improves diversity. Set `colsample_bytree=1` only for the depthwise member, preserving the forest's 0.8 ratio and the complementary architectures.
   Result `d7c7633`: Eval AUC 0.7620, discard (-0.0008). Both members benefit from per-tree column sampling.

Plateau research after three discards: [Heskes (NeurIPS 1997)](https://papers.nips.cc/paper/1413-selecting-weighting-factors-in-logarithmic-opinion-pools.pdf) develops logarithmic pooling of probability statements. A [recent aggregation paper](https://arxiv.org/abs/2603.04204) identifies linear probability pooling and geometric/logit pooling as distinct ensemble rules. [scikit-learn's soft voting](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html) is the linear rule used so far. Since the two tree architectures may have different confidence scales, test equal-weight geometric pooling before more minor parameter edits.

64. Exploration hypothesis: averaging in log-odds space may combine the loss-guided and depthwise rankings better than averaging their raw probabilities. Use the normalized geometric mean of their two-class probabilities; leave training and features unchanged. This is a different ensemble rule at negligible training cost.
   Result `88fc343`: Eval AUC 0.7628, discard. It ties the linear pool at four-decimal resolution while adding an import and several lines; keep the simpler probability average.

New architecture research: [scikit-learn's mixed-column example](https://scikit-learn.org/stable/auto_examples/compose/plot_column_transformer_mixed_types.html) uses one-hot encoding of categories with a logistic model. Its [OneHotEncoder documentation](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.OneHotEncoder.html) describes sparse encoding for linear models, and [LogisticRegression documentation](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html) supports sparse input. An additive model may capture broad airport/date effects differently from boosted interactions.

65. Exploration hypothesis: a lightly weighted one-hot logistic model can supply additive date, airport, carrier, and time effects to the strongest loss-guided forest. Replace the depthwise member with logistic regression and use 80% forest / 20% logistic probability weight, since the additive model is expected to be weaker alone. All fitting uses `train.csv` and the same row-local `prepare`.
   Result `043b632`: Eval AUC 0.7594, discard (-0.0034). Even a 20% additive contribution weakens the forest; the depthwise booster offers much better complementary nonlinear signal.
66. Exploration hypothesis: flight distance was nearly neutral when removed from the older single-tree model (experiment 21), but the present blended models may use it to distinguish long-route schedules from short-haul operations. Restore the raw `Distance` feature in both models with one feature-list edit; no lookup or new row-level computation is needed.
   Result `de23097`: Eval AUC 0.7618, discard (-0.0010). Distance is still extraneous for departure delay and also lengthens training slightly.
67. Exploration hypothesis: a numeric scheduled-time offset from each origin-destination route's typical departure time may expose early and late flights on that route without the high-cardinality route category that failed in experiment 7. Fit the route median scheduled minute on `train.csv` only, as in `program.md`'s allowed lookup pattern; use each row's own route and time inside `prepare`.
   Result `4207093`: Eval AUC 0.7606, discard (-0.0022). It also raised evaluation time to 37.6s from about 33s. Route schedule context did not generalize.

Fresh categorical research: [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) says `max_cat_threshold` limits the categories considered at partition splits to control overfitting. Its [categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains that partitioning groups categories with similar leaf values. The 365-level date is the strongest engineered signal, and the two architectures may need different caps.

68. Exploration hypothesis: retain the loss-guided forest's proven category cap of 128 while constraining the depthwise member to 64. This may give its shallow splits less opportunity to fit noisy dates, increasing useful ensemble diversity; it changes only one parameter of the second model.
   Result `d5bc271`: Eval AUC 0.7620, discard (-0.0008). The depthwise member also needs the wider 128-category partitions.

New regularization research: [XGBoost's monotonic-constraint tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html) supports a named-feature constraint and warns that histogram training may produce shallow trees, though a larger `max_bin` can reduce that effect. [Delay-propagation research](https://arxiv.org/abs/1701.05556) motivates a rising scheduled-time risk within a day. The categorical hour feature can still express nonmonotonic hour effects if only raw `CRSDepTime` is constrained; the other blend member remains unconstrained.

69. Exploration hypothesis: constrain the depthwise member's raw scheduled-time effect to rise with later times, reducing noisy threshold reversals while its separate categorical hour still models local variation. Add `monotone_constraints={"CRSDepTime": 1}` only to the second model; the existing 512 histogram bins may preserve enough candidate splits.
   Result `05f00f6`: Eval AUC 0.7628, discard. It ties the unconstrained blend at four-decimal resolution and adds an assumption/parameter. The simpler model is preferable.
70. Ablation hypothesis: the 512-bin numeric histogram gave only +0.0001 in the earlier model (experiment 13). With a strong categorical date and only one numeric predictor, the default 256 bins may retain ranking while reducing split complexity and code. Remove the explicit `max_bin=512` from both members.
   Result `578fc7e`: Eval AUC 0.7618, discard (-0.0010). The finer scheduled-time histogram still matters.

## Synthesis after 70 experiments

Best kept remains `9423f5d` at 0.7628. The ten most recent trials did not improve it. A depth cap on the loss-guided model hurt, as did weaker penalties, full column access, or a tighter category cap on the depthwise partner. A monotonic time constraint and geometric probability pooling tied but added complexity. An additive logistic partner, restored Distance, and route-relative time all hurt. Removing the finer numeric histogram lost 0.0010. The likely next gains require a genuinely different way to represent seasonal or airport-specific patterns, while retaining the global model's date signal and regularization.

Research after 70: [Li et al. (2021)](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057) summarize seasonal effects as factors in flight delays. [Jacobs et al. (1991)](https://direct.mit.edu/neco/article/3/1/79/5560/Adaptive-Mixtures-of-Local-Experts) introduced the idea of experts trained on different subsets of cases. This suggests trying quarter-specific XGBoost members to learn season-dependent airport/time behavior. The global forest remains the main prediction so specialists cannot erase broad signal.

71. Exploration hypothesis: four depthwise models trained on their respective quarters may capture changes in airport and time effects across seasons more directly than global split interactions. Blend the appropriate quarter member at 20% with the global loss-guided forest at 80%. Quarter selection uses only each row's Month; each member trains only on a subset of `train.csv`.
   Result `e27e208`: Eval AUC 0.7633, keep (+0.0005). Training 17.0s and evaluation 32.8s, almost unchanged from the global two-model blend. The new routing code is more involved, so test whether more specialist weight reveals a larger, durable gain.
72. Follow-up hypothesis: if season-specific airport and time patterns truly contribute independent signal, increasing their weight from 20% to 40% may improve AUC. Keep all models and training data fixed, changing only the blend weight.
   Result `2cae5e8`: Eval AUC 0.7633, discard. It ties the 20% specialist blend, so retain the more conservative global weight.
73. Ablation hypothesis: two half-year specialists may learn seasonal shifts with more support per airport and fewer models than four quarter specialists. Replace the four three-month groups with two six-month groups, keeping 20% local weight and all member settings unchanged. An equal AUC would be a simplification win.
   Result `8ed617c`: Eval AUC 0.7627, discard (-0.0006). Half-year groups lose useful local differences; retain four specialists.
74. Follow-up hypothesis: meteorological seasons may align winter airport disruption patterns better than calendar quarters, especially by sharing December with January and February. Use four three-month specialists with groups DJF, MAM, JJA, SON; keep all model settings and the 20% specialist weight fixed.
   Result `bca5bd7`: Eval AUC 0.7629, discard (-0.0004). Calendar quarters give cleaner specialist boundaries for this 2005 sample.
75. Follow-up hypothesis: quarter specialists train on about one quarter of `train.csv`, so depth-3 trees may overfit rare airport/date interactions. Set their `max_depth=2` at the same 1,000 rounds, preserving the global forest, groups, and blend weight. If AUC improves, the useful seasonal signal is likely broad rather than a complex local interaction.
   Result `a7b7ff6`: Eval AUC 0.7615, discard (-0.0018). Specialist interactions need at least depth 3.

Plateau research: [XGBoost's Python API](https://xgboost.readthedocs.io/en/stable/python/python_api.html) identifies `max_cat_threshold` as a partition-split overfitting control, while its [tuning guide](https://xgboost.readthedocs.io/en/latest/tutorials/param_tuning.html) groups it with tree-complexity parameters. In a quarter, only about 90 DateCat values appear, so the global cap of 128 effectively leaves all dates eligible. A smaller local cap may reduce noisy date-specific partitions without removing the depth-3 interactions that proved useful.

76. Exploration hypothesis: use `max_cat_threshold=64` for quarter specialists only, keeping the global forest at 128. This limits categorical date partitions in the smaller local training subsets while retaining their depth-3 interactions.
   Result `9ddfa3b`: Eval AUC 0.7634, keep provisionally (+0.0001). One extra parameter, with no measurable runtime cost; test a tighter cap to see whether this is a real regularization trend.
77. Follow-up hypothesis: reducing the specialists' category cap from 64 to 32 tests whether still tighter date partitions improve the small gain, or whether 64 already discards useful date contrasts. No other setting changes.
   Result `9ddddcd`: Eval AUC 0.7635, keep (+0.0001). A second small gain in the same direction suggests the quarter models were overfitting categorical partitions.
78. Follow-up hypothesis: cap 16 tests whether the specialist gain continues as date partitions become still more conservative. This brackets the useful range after 128, 64, and 32; a reversal would identify the first underfit point.
   Result `b0298d4`: Eval AUC 0.7634, discard (-0.0001). The best observed local category cap is 32; tighter partitions begin to lose signal.
79. Ablation hypothesis: the quarter specialists have only about 50,000 rows each, so 1,000 boosting rounds may be more than needed. Reduce them to 700 rounds while keeping the cap of 32 and the global forest fixed. This could reduce variance, training, and artifact size if AUC holds.
   Result `2c16136`: Eval AUC 0.7632, discard (-0.0003). Reduced rounds save little runtime and lose ranking; 1,000 remains worthwhile.
80. Follow-up hypothesis: tighter category partitions helped the quarter models, so larger leaf-support requirements may also curb noisy local interactions. Increase only their `min_child_weight` from 10 to 20, retaining 1,000 rounds and the global model's setting of 10.
   Result `c4efe32`: Eval AUC 0.7633, discard (-0.0002). The cap of 32 is enough categorical regularization; larger minimum leaves lose some useful interactions.

## Synthesis after 80 experiments

Best kept: `9ddddcd`, Eval AUC 0.7635. Four quarter specialists at 20% weight improved on the global two-model blend by 0.0005, with little runtime increase. The later local category-cap search gave two small gains, from 128 to 64 to 32; 16 reversed. Half-year and meteorological-season groupings were worse than calendar quarters, and depth-2 specialists were much worse. Cutting local boosting rounds to 700 or raising minimum child weight to 20 also lost AUC. The model appears to need depth-3 seasonal interactions, but conservative categorical date partitions. Next revisit compact row-local features that may share weekly or time patterns within quarters.

Research after 80: [Cheng et al. (2019)](https://onlinelibrary.wiley.com/doi/10.1155/2019/3525912) describe weekday/weekend and time-period relationships in departure delay. [The scikit-learn time-feature guide](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) shows weekday and month as useful time decompositions, while noting trees can model nonmonotonic effects. A coarse weekend flag failed before the seasonal model, but full weekday categories could still share effects across dates within each quarter.

81. Exploration hypothesis: restore seven-level DayOfWeek as a categorical predictor for the global forest and quarter specialists. Exact DateCat distinguishes individual days but cannot directly pool Monday-through-Sunday behavior; quarter models have fewer dates, making this shared pattern more useful. This adds one existing row-local input and no lookup.
   Result `f10a49f`: Eval AUC 0.7618, discard (-0.0017), with evaluation rising to 36.5s. The categorical weekday distracts from stronger date/time features even inside quarters.
82. Exploration hypothesis: the specialists' category cap of 32 can limit how smoothly they represent gradual seasonal change within a quarter. Restore numeric DayOfYear alongside DateCat so a shallow split can share neighboring dates, using the already computed row-local `day_of_year`. The global model sees the same simple column; compare with experiment 23, where it was harmful before seasonal specialization.
   Result `594c8ea`: Eval AUC 0.7633, discard (-0.0002), with slightly slower evaluation. The mixed effect may hide a local benefit offset by the previously observed global cost, so isolate the feature to specialists once.
83. Follow-up hypothesis: numeric DayOfYear may help only quarter specialists, where its ordered within-quarter trend is meaningful; experiment 23 showed it hurt the global model. Keep the global forest on its established six columns and give only the specialists the extra numeric day column. The row-local `prepare` still computes the same value for individual evaluation rows.
   Result `b54f545`: Eval AUC 0.7634, discard (-0.0001) with more code and evaluation time. Numeric date ordering does not improve either side of the seasonal blend.

Diagnostic on the kept artifact (training-derived gain importance, not a metric): global forest emphasizes raw time (0.416), hour (0.184), date (0.155). Local specialists emphasize date, airports, and month more evenly; Q2-Q4 assign about 0.26-0.29 importance to Month. This supports trying a different local tree shape while retaining the global time-heavy forest.

84. Exploration hypothesis: local quarter models might benefit from asymmetric loss-guided eight-leaf trees, just as the global model did, while quarter routing preserves diversity. Change only the specialists from depthwise depth-3 to loss-guided eight leaves at the same 1,000 rounds and cap 32. Their smaller training subsets and L1/L2 penalties may restrain overfitting.
   Result `5feb23a`: Eval AUC 0.7633, discard (-0.0002). Depthwise growth remains the better local complement to the loss-guided global forest.

Plateau research: [Jacobs et al.'s local-experts framework](https://www.cs.toronto.edu/~hinton/absps/jjnh91.pdf) motivates assigning specialized models to known subtasks. [MoEC (AAAI 2023)](https://ojs.aaai.org/index.php/AAAI/article/view/26617) notes that too many experts can suffer sparse data allocation and overfitting. We have empirical bracket points of two half-year experts (worse) and four quarterly experts (best), so testing twelve monthly experts determines whether finer temporal specialization helps or crosses that data-scarcity boundary.

85. Exploration hypothesis: monthly experts may capture airport and scheduled-time patterns more precisely than quarterly experts, because each operates under a narrower schedule and weather regime. Use twelve one-month groups with unchanged local depth-3/1,000-round settings, category cap 32, and 20% blend weight; the global forest still supplies robust cross-month signal.
   Result `bdb2a8e`: Eval AUC 0.7633, discard (-0.0002); saved artifact 62.7 MB. Twelve experts are too fragmented and expensive for no gain.
86. Follow-up hypothesis: preserve four quarter routes but train each expert on its own quarter plus adjacent months, giving more support for airport/time effects near quarter boundaries. Use five-month overlapping windows centered on each quarter while keeping inference routing, model settings, and 20% weight unchanged. This tests whether data scarcity limited the quarter specialists.
   Result `aaf2258`: Eval AUC 0.7630, discard (-0.0005). Adjacent-month data blur the quarter-specific signal; retain disjoint quarters.
87. Exploration hypothesis: the pandas Month dtype still lists all 12 levels even inside a quarterly specialist, so XGBoost's default one-hot threshold of 4 uses partition splits for Month. [XGBoost categorical docs](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) describe `max_cat_to_onehot`. Set it to 13 only in specialists so Month uses one-hot splits while carrier, hour, date, and airports remain partitioned. This isolates the useful month contrast without the broad one-hot change that hurt in experiment 8.
   Result `cc5e746`: Eval AUC 0.7635, discard. One-hot Month ties the existing partition representation and adds a setting; keep the simpler default.
88. Exploration hypothesis: the quarter specialists fit fewer rows than the global model, so stronger L2 leaf shrinkage may reduce noisy local scores after category cap 32. Set `reg_lambda=10` only in specialists, keeping global L2=5 and all other settings fixed. Prior global L2=10 hurt, but the local sample size is different.
   Result `c79dda8`: Eval AUC 0.7634, discard (-0.0001). Additional L2 shrinkage does not help the local specialists.
89. Exploration hypothesis: smaller boosting steps may produce smoother quarter-specific date effects than 1,000 rounds at learning rate 0.1. Set only local models to learning rate 0.05 and 1,400 rounds, a lower aggregate step budget with finer increments; the global forest stays unchanged. Prior full-data trial 42 was a small miss, but these specialists have a different sample size and category cap.
   Result `95b8bbe`: Eval AUC 0.7629, discard (-0.0006). Smaller steps and more rounds do not improve local ranking.
90. Follow-up hypothesis: the opposite schedule, learning rate 0.15 and 700 local rounds, keeps roughly the same total update size as 0.1 and 1,000 rounds but may provide stronger low-order seasonal corrections with a smaller artifact. Test this one cheaper schedule before ending local learning-rate tuning.
   Result `7ba9e66`: Eval AUC 0.7631, discard (-0.0004). The local learning-rate experiments bracket 0.1 as best.

## Synthesis after 90 experiments

Best kept remains `9ddddcd` at 0.7635. Full weekday and numeric DayOfYear features did not help the seasonal blend, including when DayOfYear was isolated to specialists. Asymmetric local trees, monthly experts, and overlapping quarter training windows were worse. One-hot Month tied but added a setting. More local L2 shrinkage and slower or faster learning schedules both lost AUC. The four disjoint depth-3 quarter specialists with local category cap 32 remain the best balance of specialization and support. For the remaining time, focus on whether their probability weight can be improved, then preserve the best simple version.

Research after 90: [scikit-learn's soft-voting guide](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html) explicitly treats predicted-probability weights as an ensemble choice. The prior weight experiment at cap 128 found 20% and 40% equal; the specialists are now more regularized at cap 32, so the weight tradeoff may have shifted. Avoid changing the trained models while testing this.

91. Follow-up hypothesis: quarter specialists with cap 32 may be more reliable than those with cap 128, so a 40% local prediction weight could now exceed the 20% setting. Change only the probability blend coefficient and compare with the kept 0.7635 result.
   Result `332f68a`: Eval AUC 0.7639, keep (+0.0004). The stronger, more regularized specialists now warrant more ensemble weight.
92. Follow-up hypothesis: raise specialist weight from 40% to 60% to test whether their advantage continues or whether excessive reliance on smaller local samples starts to hurt. The trained model settings stay fixed.
   Result `389a127`: Eval AUC 0.7622, discard (-0.0017). Specialists should remain a minority contribution; 40% is the best tested weight so far.
93. Follow-up hypothesis: 50% specialist weight tests between the improved 40% blend and the failed 60% blend, to determine whether the optimum lies just above 40%. This changes one arithmetic coefficient only.
   Result `723d073`: Eval AUC 0.7633, discard (-0.0006). The weight-response peak is at or below 40%.
94. Follow-up hypothesis: 30% specialist weight tests the lower side between 20% (0.7635) and 40% (0.7639), finishing the coarse weight bracket before the clock expires. Training and features stay identical.
   Result `52303aa`: Eval AUC 0.7640, keep (+0.0001 versus the prior best 40% blend). Training 16.9s, total run 50.4s. The harness reported `TIME IS UP` immediately after this run.

## Final summary

The best kept model is commit `52303aa`, Eval AUC **0.7640** across 94 experiments, up from the unchanged baseline `92e43e6` at 0.7203 (+0.0437 AUC). It combines a loss-guided five-tree boosted forest with four depthwise specialists trained on disjoint calendar quarters. The specialists use `max_cat_threshold=32` and contribute 30% of the final probability; the global forest contributes 70%. All models train only on `train.csv`, and `prepare` uses row-local features with train-fitted category levels.

What worked: longer but shallower boosting than the starter, categorical scheduled hour and exact day of year, removal of weak/redundant raw fields, L2 and L1 leaf regularization, boosted-forest averaging, and then quarter-specific depthwise models with tighter category partitions. What did not: sparse route categories, extra minute/route features, weekday and distance restoration, more trees/depth without constraint, additive logistic blending, monthly or broad/overlapping seasonal experts, and excessive weight on the specialists. A further run could bracket 30-40% specialist weight more finely, though the tiny gaps warrant caution about Eval-set noise. The untouched holdout remains for the human-only post-hoc evaluation.
