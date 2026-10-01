import pandas as pd
import numpy as np
import time
import xgboost as xgb
from pathlib import Path
from harness import save_and_evaluate
from scipy.sparse.csgraph import shortest_path
from sklearn.cluster import KMeans
from sklearn.ensemble import VotingClassifier


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: pd.Index(sorted(train[col].unique())) for col in cat_cols}
carrier_month_levels = pd.Index(sorted((train["UniqueCarrier"] + "_" + train["Month"]).unique()))
airport_levels = pd.Index(sorted(set(train["Origin"]) | set(train["Dest"])))
airport_index = {airport: i for i, airport in enumerate(airport_levels)}
route_distances = train.groupby(["Origin", "Dest"])["Distance"].median()
distance_graph = np.full((len(airport_levels), len(airport_levels)), np.inf)
np.fill_diagonal(distance_graph, 0.0)
for (origin, dest), distance in route_distances.items():
    i, j = airport_index[origin], airport_index[dest]
    distance_graph[i, j] = distance_graph[j, i] = min(distance_graph[i, j], distance)
geo_distances = shortest_path(distance_graph, directed=False)
assert np.isfinite(geo_distances).all(), "Training airport graph is disconnected"
squared_distances = geo_distances ** 2
gram = -0.5 * (
    squared_distances - squared_distances.mean(axis=0)[None, :]
    - squared_distances.mean(axis=1)[:, None] + squared_distances.mean()
)
eigenvalues, eigenvectors = np.linalg.eigh(gram)
coordinates = eigenvectors[:, -3:] * np.sqrt(np.maximum(eigenvalues[-3:], 0))
regions = KMeans(n_clusters=12, random_state=42, n_init=10).fit_predict(coordinates)
airport_regions = dict(zip(airport_levels, regions.astype(str)))
lookup_train = train.assign(
    OriginRegion=train["Origin"].map(airport_regions),
    DestRegion=train["Dest"].map(airport_regions),
)
hash_cols = ["Month", "DayofMonth", "DayOfWeek", "CRSDepTime", "UniqueCarrier", "Origin", "Dest", "Distance"]
hash_keys = ("0123456789abcdef", "fedcba9876543210", "0011223344556677", "8899aabbccddeeff")
encoding_cols = {
    "OriginDateRate": ["Origin", "Month", "DayofMonth"],
    "DestDateRate": ["Dest", "Month", "DayofMonth"],
    "OriginRegionDateRate": ["OriginRegion", "Month", "DayofMonth"],
    "DestRegionDateRate": ["DestRegion", "Month", "DayofMonth"],
}
training_hashes = [
    pd.util.hash_pandas_object(train[hash_cols], index=False, hash_key=key).to_numpy()
    for key in hash_keys
]
ordered_tables = {}
training_labels = (train[target] == "Y").to_numpy(dtype=float)
for name, cols in encoding_cols.items():
    codes, unique_keys = pd.factorize(pd.MultiIndex.from_frame(lookup_train[cols]), sort=False)
    unique_keys = list(unique_keys)
    ordered_tables[name] = []
    for hashes in training_hashes:
        order = np.lexsort((hashes, codes))
        sorted_codes = codes[order]
        boundaries = np.r_[0, np.flatnonzero(np.diff(sorted_codes)) + 1, len(order)]
        sorted_hashes = hashes[order]
        prefix = np.r_[0.0, training_labels[order].cumsum()]
        ordered_tables[name].append({
            unique_keys[sorted_codes[start]]: (sorted_hashes[start:end], prefix[start:end + 1] - prefix[start])
            for start, end in zip(boundaries[:-1], boundaries[1:])
        })
month_offsets = dict(zip(
    [f"c-{month}" for month in range(1, 13)],
    [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334],
))

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    for col in cat_cols:
        X[col] = pd.Categorical.from_codes(
            cat_levels[col].get_indexer(df[col]), categories=cat_levels[col]
        )
    day_of_year = [
        month_offsets[month] + int(day[2:])
        for month, day in zip(df["Month"], df["DayofMonth"])
    ]
    X["FlightDate"] = pd.Categorical(day_of_year, categories=range(1, 366))
    carrier_month = df["UniqueCarrier"] + "_" + df["Month"]
    X["CarrierMonth"] = pd.Categorical.from_codes(
        carrier_month_levels.get_indexer(carrier_month), categories=carrier_month_levels
    )
    hash_frame = df[hash_cols]
    row_hashes = [
        pd.util.hash_pandas_object(hash_frame, index=False, hash_key=key).to_numpy()
        for key in hash_keys
    ]
    encoding_inputs = {col: df[col] for col in hash_cols}
    for endpoint in ("Origin", "Dest"):
        encoding_inputs[endpoint + "Region"] = [airport_regions.get(airport, "unknown") for airport in df[endpoint]]
    for name, cols in encoding_cols.items():
        values = np.zeros(len(df))
        key_rows = {}
        for row, key in enumerate(zip(*(encoding_inputs[col] for col in cols))):
            key_rows.setdefault(key, []).append(row)
        for tables, hashes in zip(ordered_tables[name], row_hashes):
            for key, rows in key_rows.items():
                entry = tables.get(key)
                if entry is None:
                    values[rows] += 0.5
                else:
                    earlier = np.searchsorted(entry[0], hashes[rows], side="left")
                    values[rows] += (entry[1][earlier] + 10.0) / (earlier + 20.0)
        X[name] = values / len(hash_keys)
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)
for row in (0, len(train) // 2, len(train) - 1):
    pd.testing.assert_frame_equal(X_train.iloc[[row]], prepare(train.iloc[[row]])[0])


model = xgb.XGBClassifier(
    rate_drop=0.05,
    skip_drop=0.8,
    normalize_type="forest",
    n_estimators=300,
    max_depth=4,
    learning_rate=0.1,
    min_child_weight=20,
    reg_lambda=20,
    num_parallel_tree=1,
    colsample_bynode=0.8,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)
ordinary_params = {
    key: value for key, value in model.get_params().items()
    if key not in {"rate_drop", "skip_drop", "normalize_type"}
}
ordinary_params.update(n_estimators=600, learning_rate=0.05, num_parallel_tree=4)
model = VotingClassifier([
    ("dropout", model), ("ordinary", xgb.XGBClassifier(**ordinary_params)),
], voting="soft", verbose=True)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
