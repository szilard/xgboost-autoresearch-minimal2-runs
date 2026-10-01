import pandas as pd
import numpy as np
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

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    for col, period, name in [
        ("Month", 12.0, "Month"),
        ("DayOfWeek", 7.0, "Weekday"),
    ]:
        values = pd.to_numeric(
            df[col].astype("string").str.extract(r"(\d+)$", expand=False),
            errors="coerce",
        ).to_numpy(dtype=float)
        angle = 2.0 * np.pi * (values - 1.0) / period
        X[f"{name}Sin"] = np.sin(angle)
        X[f"{name}Cos"] = np.cos(angle)

    crs_dep_time = pd.to_numeric(df["CRSDepTime"], errors="coerce").to_numpy(dtype=float)
    dep_minutes = (np.floor(crs_dep_time / 100.0) * 60.0 + np.mod(crs_dep_time, 100.0)) % 1440.0
    dep_angle = 2.0 * np.pi * dep_minutes / 1440.0
    X["DepTimeSin"] = np.sin(dep_angle)
    X["DepTimeCos"] = np.cos(dep_angle)

    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=1000,
    max_depth=24,
    max_leaves=255,
    grow_policy="lossguide",
    tree_method="hist",
    max_bin=1024,
    learning_rate=0.03,
    colsample_bytree=0.55,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
