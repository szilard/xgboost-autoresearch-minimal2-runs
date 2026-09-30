import math
import pandas as pd
import time
import xgboost as xgb
from pathlib import Path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["Month", "DayofMonth", "DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}
month_starts = {f"c-{m}": day for m, day in enumerate(
    (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334), start=1
)}
day_numbers = {f"c-{d}": d for d in range(1, 32)}
season_sin = {d: math.sin(2 * math.pi * d / 365) for d in range(1, 366)}
season_cos = {d: math.cos(2 * math.pi * d / 365) for d in range(1, 366)}

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    X["DayOfYear"] = df["Month"].map(month_starts) + df["DayofMonth"].map(day_numbers)
    X["SeasonSin"] = X["DayOfYear"].map(season_sin)
    X["SeasonCos"] = X["DayOfYear"].map(season_cos)
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=1100,
    max_depth=0,
    max_leaves=192,
    min_child_weight=0.5,
    grow_policy="lossguide",
    learning_rate=0.03,
    reg_lambda=10,
    reg_alpha=9,
    max_cat_threshold=8,
    tree_method="hist",
    subsample=0.9,
    sampling_method="gradient_based",
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
