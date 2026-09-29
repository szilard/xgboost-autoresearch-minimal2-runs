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
month_offsets = {
    1: 0, 2: 31, 3: 59, 4: 90, 5: 120, 6: 151,
    7: 181, 8: 212, 9: 243, 10: 273, 11: 304, 12: 334,
}

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    month_num = df["Month"].str[2:].astype(int)
    day_num = df["DayofMonth"].str[2:].astype(int)
    day_of_year = month_num.map(month_offsets) + day_num
    X["DayOfYear"] = day_of_year
    X["DayOfYearSin"] = np.sin(2 * np.pi * day_of_year / 365)
    X["DayOfYearCos"] = np.cos(2 * np.pi * day_of_year / 365)
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
    max_depth=0,
    grow_policy="lossguide",
    max_leaves=512,
    gamma=0.01,
    learning_rate=0.025,
    reg_lambda=100.0,
    reg_alpha=3.0,
    colsample_bytree=0.7,
    max_cat_threshold=4,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
