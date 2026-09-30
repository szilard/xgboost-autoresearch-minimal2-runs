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
month_start = {f"c-{m}": d for m, d in enumerate(
    (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334), start=1
)}
day_number = {f"c-{d}": d for d in range(1, 32)}
weekday_number = {f"c-{d}": d for d in range(1, 8)}
holiday_distance = {
    d: min(abs(d - h) for h in (1, 150, 185, 248, 328, 359, 366))
    for d in range(1, 366)
}

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    X["DayOfYear"] = df["Month"].map(month_start) + df["DayofMonth"].map(day_number)
    X["DayOfMonthNum"] = df["DayofMonth"].map(day_number)
    X["DayOfWeekNum"] = df["DayOfWeek"].map(weekday_number)
    X["WeekOfYear"] = pd.Categorical((X["DayOfYear"] - 3) // 7 + 1, categories=range(53))
    X["YearSin"] = np.sin(2 * np.pi * X["DayOfYear"] / 365)
    X["YearCos"] = np.cos(2 * np.pi * X["DayOfYear"] / 365)
    X["HolidayDistance"] = X["DayOfYear"].map(holiday_distance)
    X["DepHour"] = pd.Categorical(df["CRSDepTime"] // 100, categories=list(range(24)))
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


class AveragedModels:
    def __init__(self, models):
        self.models = models

    def predict_proba(self, X):
        return sum(m.predict_proba(X) for m in self.models) / len(self.models)


model_params = dict(
    n_estimators=3500,
    learning_rate=0.05,
    enable_categorical=True,
    max_cat_threshold=16,
    reg_lambda=5,
    reg_alpha=10,
    min_child_weight=2,
    random_state=42,
    n_jobs=-1,
)
models = [
    xgb.XGBClassifier(max_depth=depth, **{**model_params, "max_cat_threshold": cap})
    for depth, cap in ((6, 16), (5, 8))
]


t0 = time.time()
for candidate in models:
    candidate.fit(X_train, y_train)
model = AveragedModels(models)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
