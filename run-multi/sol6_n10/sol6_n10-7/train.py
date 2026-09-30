import pandas as pd
import time
import xgboost as xgb
from pathlib import Path
from sklearn.ensemble import VotingClassifier
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["Month", "DayofMonth", "DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}
month_start = {f"c-{m}": offset for m, offset in enumerate(
    [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334], 1
)}

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    departure_time = df["CRSDepTime"]
    quarter_hour = departure_time // 100 * 4 + departure_time % 100 // 15
    X["DepQuarterHour"] = pd.Categorical(quarter_hour, categories=range(96))
    X["DayOfYear"] = df["Month"].map(month_start) + df["DayofMonth"].str[2:].astype(int)
    X["Date"] = pd.Categorical(X["DayOfYear"], categories=range(1, 366))
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model_params = dict(
    n_estimators=450,
    max_depth=6,
    learning_rate=0.05,
    max_bin=512,
    max_cat_threshold=512,
    colsample_bytree=0.6,
    enable_categorical=True,
    n_jobs=-1,
)
model = VotingClassifier(
    estimators=[
        ("seed42", xgb.XGBClassifier(**model_params, random_state=42)),
        ("seed43", xgb.XGBClassifier(**model_params, random_state=43)),
        ("seed44", xgb.XGBClassifier(**model_params, random_state=44)),
    ],
    voting="soft",
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
