import pandas as pd
import time
import xgboost as xgb
from sklearn.ensemble import VotingClassifier
from pathlib import Path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}
carrier_month_levels = sorted((train["UniqueCarrier"] + ">" + train["Month"]).unique())
carrier_weekday_levels = sorted((train["UniqueCarrier"] + ">" + train["DayOfWeek"]).unique())
month_start = {f"c-{i + 1}": day for i, day in enumerate(
    [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
)}

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    X["DateCategory"] = pd.Categorical(
        df["Month"].map(month_start) + df["DayofMonth"].str[2:].astype(int),
        categories=list(range(1, 366)),
    )
    X["CarrierMonth"] = pd.Categorical(
        df["UniqueCarrier"] + ">" + df["Month"], categories=carrier_month_levels
    )
    X["CarrierWeekday"] = pd.Categorical(
        df["UniqueCarrier"] + ">" + df["DayOfWeek"], categories=carrier_weekday_levels
    )
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model_params = dict(
    n_estimators=600,
    max_depth=8,
    learning_rate=0.05,
    min_child_weight=10,
    reg_alpha=5,
    colsample_bytree=0.8,
    max_cat_threshold=256,
    enable_categorical=True,
    n_jobs=-1,
)
model = VotingClassifier(
    estimators=[
        ("approx_42", xgb.XGBClassifier(**model_params, tree_method="approx", random_state=42)),
        ("approx_17", xgb.XGBClassifier(**model_params, tree_method="approx", random_state=17)),
        ("hist_42", xgb.XGBClassifier(**model_params, tree_method="hist", random_state=42)),
    ],
    voting="soft",
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
