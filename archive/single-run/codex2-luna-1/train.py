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
month_offsets = {1: 0, 2: 31, 3: 59, 4: 90, 5: 120, 6: 151,
                 7: 181, 8: 212, 9: 243, 10: 273, 11: 304, 12: 334}
month_lengths = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
                 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    month_num = df["Month"].str[2:].astype(int)
    day_num = df["DayofMonth"].str[2:].astype(int)
    X["DayOfYear"] = month_num.map(month_offsets) + day_num
    day_angle = 2 * np.pi * X["DayOfYear"].astype(float) / 365.0
    X["DayOfYearSin"] = np.sin(day_angle)
    X["DayOfYearCos"] = np.cos(day_angle)
    weekday_num = df["DayOfWeek"].str[2:].astype(int)
    X["IsWeekend"] = (weekday_num >= 6).astype(int)
    X["IsMonthEnd"] = (day_num >= month_num.map(month_lengths) - 2).astype(int)
    X["IsMonthEndWeekend"] = X["IsWeekend"] * X["IsMonthEnd"]
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=300,
    max_depth=0,
    max_leaves=512,
    grow_policy="lossguide",
    tree_method="hist",
    min_child_weight=3,
    learning_rate=0.05,
    colsample_bytree=0.4,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
