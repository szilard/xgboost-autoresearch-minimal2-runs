import pandas as pd
import time
import xgboost as xgb
from pathlib import Path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: pd.Index(sorted(train[col].unique())) for col in cat_cols}
date_levels = pd.Index(sorted((train["Month"] + "-" + train["DayofMonth"]).unique()))

def prepare(df):
    X = {col: df[col].to_numpy() for col in num_cols}
    for col in cat_cols:
        X[col] = pd.Categorical.from_codes(
            cat_levels[col].get_indexer(df[col]),
            categories=cat_levels[col],
        )
    X["Date"] = pd.Categorical.from_codes(
        date_levels.get_indexer(df["Month"] + "-" + df["DayofMonth"]),
        categories=date_levels,
    )
    y = (df[target] == "Y").astype(int).to_numpy()
    return pd.DataFrame(X, index=df.index), y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=400,
    max_depth=0,
    max_leaves=64,
    grow_policy="lossguide",
    learning_rate=0.05,
    min_child_weight=20,
    reg_alpha=1,
    max_cat_threshold=256,
    subsample=0.8,
    colsample_bytree=0.8,
    num_parallel_tree=4,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
