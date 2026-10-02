import pandas as pd
import numpy as np
import time
import xgboost as xgb
from pathlib import Path
from scipy.sparse.csgraph import shortest_path
from sklearn.manifold import ClassicalMDS
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["Month", "DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_types = {col: pd.CategoricalDtype(sorted(train[col].unique())) for col in cat_cols}
date_type = pd.CategoricalDtype(range(1, 366))
month_starts = dict(zip(
    [f"c-{m}" for m in range(1, 13)],
    [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334],
))
day_numbers = {f"c-{d}": d for d in range(1, 32)}
airports = sorted(set(train["Origin"]) | set(train["Dest"]))
airport_index = {airport: i for i, airport in enumerate(airports)}
graph = np.full((len(airports), len(airports)), np.inf)
np.fill_diagonal(graph, 0.0)
route_distances = train.groupby(["Origin", "Dest"])["Distance"].median()
for (origin, dest), distance in route_distances.items():
    i, j = airport_index[origin], airport_index[dest]
    graph[i, j] = graph[j, i] = min(graph[i, j], distance)
geodesic = shortest_path(graph, directed=False)
assert np.isfinite(geodesic).all(), "Training route graph must be connected"
coordinates = ClassicalMDS(n_components=2, metric="precomputed").fit_transform(geodesic)
coordinates = np.column_stack((coordinates, coordinates @ (np.array([[1.0, -1.0], [1.0, 1.0]]) / np.sqrt(2.0))))
geo_lookup = [pd.Series(coordinates[:, axis], index=airports) for axis in range(4)]

def prepare(df):
    X = df[num_cols].copy()
    for col in cat_cols:
        X[col] = pd.Categorical.from_codes(
            cat_types[col].categories.get_indexer(df[col]), dtype=cat_types[col],
        )
    day_of_year = df["Month"].map(month_starts) + df["DayofMonth"].map(day_numbers)
    X["FlightDate"] = day_of_year.astype(date_type)
    for place in ("Origin", "Dest"):
        for axis, lookup in enumerate(geo_lookup):
            X[f"{place}Geo{axis}"] = df[place].map(lookup)
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=1200,
    max_depth=8,
    learning_rate=0.05,
    min_child_weight=20,
    reg_lambda=10,
    reg_alpha=5,
    max_cat_threshold=16,
    max_bin=1024,
    colsample_bynode=0.8,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


class GeometryEnsemble:
    def __init__(self, members):
        self.members = members

    def predict_proba(self, X):
        return np.mean([
            member.predict_proba(X[member.feature_names_in_])
            for member in self.members
        ], axis=0)


t0 = time.time()
members = []
for axes in ((0, 1), (2, 3)):
    columns = num_cols + cat_cols + ["FlightDate"] + [
        f"{place}Geo{axis}" for place in ("Origin", "Dest") for axis in axes
    ]
    member = xgb.XGBClassifier(**model.get_params())
    member.fit(X_train[columns], y_train)
    members.append(member)
model = GeometryEnsemble(members)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
