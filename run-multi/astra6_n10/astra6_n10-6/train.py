import pandas as pd
import time
import xgboost as xgb
from pathlib import Path
from sklearn.ensemble import VotingClassifier
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["Month", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: pd.Index(sorted(train[col].unique())) for col in cat_cols}
date_levels = pd.Index(sorted((train["Month"] + ":" + train["DayofMonth"]).unique()))

def prepare(df):
    columns = {col: df[col].to_numpy() for col in num_cols}
    columns["IsWeekend"] = df["DayOfWeek"].isin(["c-6", "c-7"]).to_numpy(dtype="int8")
    for col in cat_cols:
        levels = cat_levels[col]
        columns[col] = pd.Categorical.from_codes(levels.get_indexer(df[col]), categories=levels)
    date_key = df["Month"] + ":" + df["DayofMonth"]
    columns["FlightDate"] = pd.Categorical.from_codes(
        date_levels.get_indexer(date_key), categories=date_levels,
    )
    X = pd.DataFrame(columns, index=df.index)
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=1200,
    max_depth=10,
    learning_rate=0.05,
    min_child_weight=20,
    reg_lambda=10,
    reg_alpha=5,
    max_cat_threshold=16,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)

shallower_model = xgb.XGBClassifier(**model.get_params())
shallower_model.set_params(max_depth=8)
faster_model = xgb.XGBClassifier(**model.get_params())
faster_model.set_params(n_estimators=320, learning_rate=0.1)
faster_model.set_params(interaction_constraints=[
    ["FlightDate", "Month", "Origin", "Dest"],
    ["CRSDepTime", "Distance", "IsWeekend", "UniqueCarrier"],
])
model = VotingClassifier(
    estimators=[("depth10", model), ("depth8", shallower_model), ("fast", faster_model)],
    voting="soft", weights=[3, 3, 2], n_jobs=1,
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
