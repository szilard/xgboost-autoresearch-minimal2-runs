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


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    month_offsets = {f"c-{month}": offset for month, offset in enumerate(
        (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334), start=1
    )}
    day_of_year = df["Month"].map(month_offsets) + df["DayofMonth"].str[2:].astype(int)
    X["DateCategory"] = pd.Categorical(day_of_year, categories=range(1, 366))
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=900,
    max_depth=6,
    min_child_weight=0.5,
    colsample_bytree=0.8,
    subsample=0.975,
    max_bin=1024,
    learning_rate=0.025,
    enable_categorical=True,
    max_cat_threshold=192,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
