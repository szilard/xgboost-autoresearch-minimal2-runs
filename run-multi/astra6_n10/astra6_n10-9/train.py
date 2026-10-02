import pandas as pd
import numpy as np
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
correction_keys = {
    "OriginDate": ("Origin", 1),
    "DestDate": ("Dest", 1),
    "CarrierDate": ("UniqueCarrier", 1),
    "OriginDateBlock": ("Origin", 4),
    "CarrierDateBlock": ("UniqueCarrier", 4),
}

def prepare(df):
    X = {col: df[col].to_numpy() for col in num_cols}
    for col in cat_cols:
        X[col] = pd.Categorical.from_codes(
            cat_levels[col].get_indexer(df[col]),
            categories=cat_levels[col],
        )
    month = df["Month"].str[2:].astype(int).to_numpy()
    day = df["DayofMonth"].str[2:].astype(int).to_numpy()
    day_of_year = np.array([0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334])[month - 1] + day
    X["Date"] = pd.Categorical(day_of_year, categories=range(1, 366))
    X["DepHour"] = pd.Categorical(df["CRSDepTime"] // 100, categories=range(24))
    hour = df["CRSDepTime"].to_numpy() // 100
    for name, (col, blocks) in correction_keys.items():
        key = X[col].codes.astype(np.int64) * 366 + day_of_year
        X[name] = key if blocks == 1 else key * blocks + hour * blocks // 24
    y = (df[target] == "Y").astype(int).to_numpy()
    return pd.DataFrame(X, index=df.index), y

X_train, y_train = prepare(train)


model = xgb.XGBRegressor(
    objective="reg:logistic",
    n_estimators=1200,
    max_depth=0,
    grow_policy="lossguide",
    max_leaves=16,
    learning_rate=0.05,
    min_child_weight=20,
    reg_lambda=10,
    reg_alpha=5,
    max_cat_threshold=256,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


class MeanMarginClassifier:
    def __init__(self, models):
        self.models = models

    def predict(self, X, output_margin=False):
        margin = np.mean([member.predict(X, output_margin=True) for member in self.models], axis=0)
        return margin if output_margin else (margin > 0).astype(int)


t0 = time.time()
base_columns = [col for col in X_train if col not in correction_keys]
soft_target = 0.9 * y_train + 0.05
model.fit(X_train[base_columns], soft_target)
alternate = xgb.XGBRegressor(**{
    **model.get_params(), "grow_policy": "depthwise", "max_depth": 4, "max_leaves": 0,
})
alternate.fit(X_train[base_columns], soft_target)
deeper = xgb.XGBRegressor(**{**alternate.get_params(), "max_depth": 8})
deeper.fit(X_train[base_columns], soft_target)
model = MeanMarginClassifier([model, alternate, deeper])
margin = model.predict(X_train[base_columns], output_margin=True).astype(float)
corrections = {}
for key_col in correction_keys:
    probability = 1 / (1 + np.exp(-margin))
    stats = pd.DataFrame(
        {"gradient": y_train - probability, "hessian": probability * (1 - probability)},
        index=X_train.index,
    ).groupby(X_train[key_col]).sum()
    gradient = np.sign(stats["gradient"]) * np.maximum(stats["gradient"].abs() - 0.5, 0)
    scores = gradient / (stats["hessian"] + 10)
    corrections[key_col] = scores[scores != 0]
    margin += X_train[key_col].map(corrections[key_col]).fillna(0).to_numpy()


class CorrectedClassifier:
    def __init__(self, base_model, columns, tables):
        self.base_model = base_model
        self.columns = columns
        self.tables = tables

    def predict_proba(self, X):
        margin = self.base_model.predict(X[self.columns], output_margin=True).astype(float)
        for key_col, table in self.tables.items():
            margin += X[key_col].map(table).fillna(0).to_numpy()
        probability = 1 / (1 + np.exp(-margin))
        return np.column_stack([1 - probability, probability])


model = CorrectedClassifier(model, base_columns, corrections)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
