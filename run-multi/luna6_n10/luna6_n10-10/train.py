import pandas as pd
import numpy as np
import time
import xgboost as xgb
from pathlib import Path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["Month", "DayofMonth", "DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}
dep_hour = (train["CRSDepTime"] // 100) % 24
dep_hour_levels = sorted(dep_hour.dropna().astype(int).unique())

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    dep_hour = (df["CRSDepTime"] // 100) % 24
    X["DepHourSin"] = np.sin(2 * np.pi * dep_hour / 24)
    X["DepHourCos"] = np.cos(2 * np.pi * dep_hour / 24)
    X["DepHour"] = pd.Categorical(
        dep_hour.where(dep_hour.isin(dep_hour_levels)),
        categories=dep_hour_levels,
    )
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=1200,
    max_depth=6,
    learning_rate=0.05,
    max_bin=128,
    tree_method="hist",
    grow_policy="lossguide",
    max_leaves=31,
    max_cat_threshold=10,
    reg_lambda=4,
    reg_alpha=1.1,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
