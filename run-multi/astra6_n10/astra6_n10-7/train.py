import pandas as pd
import time
import xgboost as xgb
from pathlib import Path
from sklearn.ensemble import VotingClassifier
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}
date_levels = sorted((train["Month"] + "_" + train["DayofMonth"]).unique())

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    for col in cat_cols:
        X[col] = pd.Categorical(X[col], categories=cat_levels[col])
    dates = df["Month"] + "_" + df["DayofMonth"]
    X["Date"] = pd.Categorical(dates, categories=date_levels)
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


base_parameters = dict(
    n_estimators=3600,
    max_depth=4,
    learning_rate=0.025,
    reg_lambda=100,
    min_child_weight=100,
    colsample_bynode=0.34,
    feature_weights=[2, 1, 1, 1, 1, 2],
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)

model = VotingClassifier(
    estimators=[
        ("standard", xgb.XGBClassifier(**base_parameters)),
        ("coarse", xgb.XGBClassifier(**base_parameters, max_bin=4)),
        ("deeper", xgb.XGBClassifier(**(base_parameters | {"max_depth": 5, "n_estimators": 1800}))),
    ],
    voting="soft",
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
