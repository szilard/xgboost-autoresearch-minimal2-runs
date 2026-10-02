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


cat_dtypes = {col: pd.CategoricalDtype(sorted(train[col].unique())) for col in cat_cols}
cat_dtypes["FlightDate"] = pd.CategoricalDtype(
    sorted((train["Month"] + "_" + train["DayofMonth"]).unique())
)
landmark_distances = {}
for anchor in ["LAX", "ATL"]:
    flights = train[(train["Origin"] == anchor) | (train["Dest"] == anchor)]
    other_end = flights["Origin"].where(flights["Origin"] != anchor, flights["Dest"])
    landmark_distances[anchor] = flights["Distance"].groupby(other_end).median()
    landmark_distances[anchor].loc[anchor] = 0

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    X["FlightDate"] = df["Month"] + "_" + df["DayofMonth"]
    for side in ["Origin", "Dest"]:
        for anchor, distances in landmark_distances.items():
            X[f"{side}DistanceTo{anchor}"] = df[side].map(distances)
    for col, dtype in cat_dtypes.items():
        X[col] = pd.Categorical.from_codes(dtype.categories.get_indexer(X[col]), dtype=dtype)
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=2000,
    max_depth=0,
    grow_policy="lossguide",
    max_leaves=64,
    max_bin=64,
    min_child_weight=100,
    reg_lambda=500,
    colsample_bynode=0.3,
    learning_rate=0.015,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
