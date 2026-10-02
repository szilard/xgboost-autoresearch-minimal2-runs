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


cat_dtypes = {
    col: pd.CategoricalDtype(sorted(train[col].unique())) for col in cat_cols
}
date_dtype = pd.CategoricalDtype(
    sorted((train["Month"] + "-" + train["DayofMonth"]).unique())
)
month_offsets = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
week_dtype = pd.CategoricalDtype(range(53))

def prepare(df):
    columns = {col: df[col].to_numpy() for col in num_cols}
    for col in cat_cols:
        columns[col] = pd.Categorical(df[col], dtype=cat_dtypes[col])
    columns["Date"] = pd.Categorical(
        [month + "-" + day for month, day in zip(df["Month"], df["DayofMonth"])],
        dtype=date_dtype,
    )
    columns["WeekBlock"] = pd.Categorical(
        [(month_offsets[int(month[2:]) - 1] + int(day[2:]) + 4) // 7
         for month, day in zip(df["Month"], df["DayofMonth"])],
        dtype=week_dtype,
    )
    X = pd.DataFrame(columns, index=df.index)
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=600,
    num_parallel_tree=3,
    max_depth=0,
    max_leaves=64,
    grow_policy="lossguide",
    learning_rate=0.05,
    min_child_weight=20,
    reg_lambda=100,
    reg_alpha=5,
    max_cat_threshold=16,
    max_bin=1024,
    colsample_bytree=0.8,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
