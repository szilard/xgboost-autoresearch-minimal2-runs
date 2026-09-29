import pandas as pd
import time
import xgboost as xgb
from sklearn.base import clone
from pathlib import Path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["Month", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}
month_start = {f"c-{m}": offset for m, offset in enumerate(
    [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334], 1
)}
day_num = {f"c-{d}": d for d in range(1, 32)}

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    X["DepHour"] = pd.Categorical(df["CRSDepTime"] // 100, categories=range(24))
    day_of_year = df["Month"].map(month_start) + df["DayofMonth"].map(day_num)
    X["DateCat"] = pd.Categorical(day_of_year, categories=range(1, 366))
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=700,
    max_depth=0,
    max_leaves=8,
    num_parallel_tree=5,
    grow_policy="lossguide",
    learning_rate=0.1,
    min_child_weight=10,
    reg_lambda=5,
    reg_alpha=1,
    colsample_bytree=0.8,
    max_bin=512,
    max_cat_threshold=128,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
model.fit(X_train, y_train)
season_months = [
    [f"c-{month}" for month in range(quarter * 3 + 1, quarter * 3 + 4)]
    for quarter in range(4)
]
specialists = []
for months in season_months:
    mask = X_train["Month"].isin(months)
    specialist = clone(model).set_params(
        random_state=24,
        num_parallel_tree=1,
        grow_policy="depthwise",
        max_depth=3,
        max_leaves=0,
        n_estimators=1000,
        max_cat_threshold=32,
    )
    specialist.fit(X_train.loc[mask], y_train[mask.to_numpy()])
    specialists.append(specialist)

class SeasonalModel:
    def __init__(self, global_model, specialists, season_months):
        self.global_model = global_model
        self.specialists = specialists
        self.season_months = season_months

    def predict_proba(self, X):
        global_prob = self.global_model.predict_proba(X)
        local_prob = global_prob.copy()
        for months, specialist in zip(self.season_months, self.specialists):
            mask = X["Month"].isin(months).to_numpy()
            if mask.any():
                local_prob[mask] = specialist.predict_proba(X.loc[mask])
        return 0.7 * global_prob + 0.3 * local_prob

model = SeasonalModel(model, specialists, season_months)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
