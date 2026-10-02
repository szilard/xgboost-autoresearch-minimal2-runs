import pandas as pd
import numpy as np
from scipy.sparse.csgraph import shortest_path
from sklearn.manifold import SpectralEmbedding
import time
import xgboost as xgb
from pathlib import Path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["UniqueCarrier", "DayOfWeek"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}
cat_levels["FlightDate"] = sorted((train["Month"] + "_" + train["DayofMonth"]).unique())

# Infer airport proximity from route distances observed in training.
airports = pd.Index(sorted(set(train["Origin"]) | set(train["Dest"])))
route_distances = train.groupby(["Origin", "Dest"])["Distance"].median()
distance_graph = np.full((len(airports), len(airports)), np.inf)
origin_ids = airports.get_indexer(route_distances.index.get_level_values(0))
dest_ids = airports.get_indexer(route_distances.index.get_level_values(1))
distance_graph[origin_ids, dest_ids] = route_distances.to_numpy()
distance_graph = np.minimum(distance_graph, distance_graph.T)
np.fill_diagonal(distance_graph, 0)
geo_distances = shortest_path(distance_graph, directed=False)
assert np.isfinite(geo_distances).all(), "Training airport graph is disconnected"
squared_distances = geo_distances ** 2
centered = -0.5 * (squared_distances - squared_distances.mean(axis=0)[None, :]
                   - squared_distances.mean(axis=1)[:, None] + squared_distances.mean())
eigenvalues, eigenvectors = np.linalg.eigh(centered)
airport_coordinates = pd.DataFrame(
    eigenvectors[:, -2:] * np.sqrt(np.maximum(eigenvalues[-2:], 0)),
    index=airports, columns=["Geo2", "Geo3"],
)

spectral_coordinates = SpectralEmbedding(
    n_components=4, affinity="precomputed_nearest_neighbors", n_neighbors=16,
    random_state=42,
).fit_transform(geo_distances)
for i in range(4):
    airport_coordinates[f"LocalGeo{i}"] = spectral_coordinates[:, i]

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col],
            categories=cat_levels[col],
        )
    X["FlightDate"] = pd.Categorical(
        df["Month"] + "_" + df["DayofMonth"], categories=cat_levels["FlightDate"]
    )
    for endpoint in ["Origin", "Dest"]:
        for axis in airport_coordinates:
            X[endpoint + axis] = df[endpoint].map(airport_coordinates[axis])
        X[endpoint + "GeoSum"] = X[endpoint + "Geo2"] + X[endpoint + "Geo3"]
        X[endpoint + "GeoDiff"] = X[endpoint + "Geo2"] - X[endpoint + "Geo3"]
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


learning_rates = np.linspace(0.16, 0.04, 300).tolist()
model = xgb.XGBClassifier(
    n_estimators=len(learning_rates),
    max_depth=7,
    min_child_weight=50,
    reg_lambda=20,
    max_bin=2048,
    num_parallel_tree=16,
    subsample=0.8,
    colsample_bynode=0.8,
    learning_rate=learning_rates[0],
    callbacks=[xgb.callback.LearningRateScheduler(learning_rates[1:] + learning_rates[-1:])],
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
