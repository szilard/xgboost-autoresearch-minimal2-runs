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
date_levels = sorted((train["Month"] + "|" + train["DayofMonth"]).unique())

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    X["CalendarDate"] = pd.Categorical(
        df["Month"] + "|" + df["DayofMonth"], categories=date_levels
    )
    X["DepMinute"] = df["CRSDepTime"] % 100
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=1600,
    max_depth=5,
    learning_rate=0.1,
    max_cat_threshold=8,
    reg_lambda=10,
    reg_alpha=4,
    colsample_bytree=0.9,
    grow_policy="lossguide",
    max_leaves=20,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
