import pandas as pd
import time
import xgboost as xgb
from datetime import date
from pathlib import Path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}
carrier_weekday_levels = sorted((train["UniqueCarrier"] + "-" + train["DayOfWeek"]).unique())
carrier_month_levels = sorted((train["UniqueCarrier"] + "-" + train["Month"]).unique())
date_levels = sorted((train["Month"].str[2:].astype(int) * 31 + train["DayofMonth"].str[2:].astype(int)).unique())
holidays = [date(2005, m, d).toordinal() for m, d in ((1, 1), (5, 30), (7, 4), (9, 5), (11, 24), (12, 25))]
holiday_distance = {}
for key in date_levels:
    month, day = (int(key) - 1) // 31, (int(key) - 1) % 31 + 1
    holiday_distance[key] = min(abs(date(2005, month, day).toordinal() - h) for h in holidays)

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    date_index = df["Month"].str[2:].astype(int) * 31 + df["DayofMonth"].str[2:].astype(int)
    X["DateCat"] = pd.Categorical(date_index, categories=date_levels)
    X["HolidayDistance"] = date_index.map(holiday_distance)
    X["CarrierWeekday"] = pd.Categorical(df["UniqueCarrier"] + "-" + df["DayOfWeek"], categories=carrier_weekday_levels)
    X["CarrierMonth"] = pd.Categorical(df["UniqueCarrier"] + "-" + df["Month"], categories=carrier_month_levels)
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=300,
    max_depth=4,
    learning_rate=0.1,
    enable_categorical=True,
    max_cat_threshold=256,
    min_child_weight=2,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
