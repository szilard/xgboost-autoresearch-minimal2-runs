import pandas as pd
import numpy as np
import time
import xgboost as xgb
from pathlib import Path
from scipy.sparse.csgraph import shortest_path
from sklearn.manifold import ClassicalMDS
from sklearn.base import clone
from sklearn.ensemble import VotingClassifier
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["Month", "DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}
cat_dtypes = {col: pd.CategoricalDtype(levels) for col, levels in cat_levels.items()}
month_offsets = dict(zip((f"c-{i}" for i in range(1, 13)),
                         (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)))
month_offsets = pd.Series(month_offsets)
day_numbers = pd.Series({f"c-{i}": i for i in range(1, 32)})
date_dtype = pd.CategoricalDtype(pd.RangeIndex(1, 366))

# Fit geographic lookups using only distances observed in the training data.
airports = pd.Index(sorted(set(train["Origin"]) | set(train["Dest"])))
route_distances = train.groupby(["Origin", "Dest"])["Distance"].median().unstack()
distance_matrix = route_distances.reindex(index=airports, columns=airports).to_numpy()
distance_matrix = np.fmin(distance_matrix, distance_matrix.T)
distance_matrix[np.isnan(distance_matrix)] = np.inf
np.fill_diagonal(distance_matrix, 0)
airport_coordinates = pd.DataFrame(
    ClassicalMDS(n_components=2, metric="precomputed").fit_transform(
        shortest_path(distance_matrix, directed=False)
    ),
    index=airports, columns=["Geo1", "Geo2"],
)

def prepare(df):
    features = {col: df[col].to_numpy() for col in num_cols}
    features.update({col: pd.Categorical(df[col], dtype=cat_dtypes[col]) for col in cat_cols})
    minutes = (features["CRSDepTime"] // 100) * 60 + features["CRSDepTime"] % 100
    angle = 2 * np.pi * minutes / 1440
    features["DepartureSin"] = np.sin(angle)
    features["DepartureCos"] = np.cos(angle)
    features["TravelAdjustedTime"] = (minutes + features["Distance"] / 8.0) % 1440
    day_of_month = df["DayofMonth"].map(day_numbers)
    day_of_year = df["Month"].map(month_offsets) + day_of_month
    features["DayofMonth"] = day_of_month.to_numpy()
    features["DayOfYear"] = day_of_year.to_numpy()
    features["FlightDate"] = pd.Categorical(day_of_year, dtype=date_dtype)
    for col in ("Origin", "Dest"):
        coordinates = airport_coordinates.reindex(df[col]).to_numpy()
        for i, axis in enumerate(airport_coordinates):
            features[f"{col}{axis}"] = coordinates[:, i]
    for axis in airport_coordinates:
        features[f"Route{axis}"] = features[f"Dest{axis}"] - features[f"Origin{axis}"]
    X = pd.DataFrame(features, index=df.index)
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=500,
    max_depth=0,
    grow_policy="lossguide",
    max_leaves=256,
    min_child_weight=100,
    reg_lambda=500,
    max_cat_threshold=16,
    learning_rate=0.12,
    callbacks=[xgb.callback.LearningRateScheduler(lambda epoch: 0.12 * 0.997 ** (epoch + 1))],
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)
model = VotingClassifier(
    [("lossguide", model),
     ("depthwise", clone(model).set_params(grow_policy="depthwise", max_depth=8, max_leaves=0))],
    voting="soft",
    weights=[3, 1],
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
