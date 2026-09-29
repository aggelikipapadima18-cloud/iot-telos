#!/usr/bin/env python3
"""Export the notebook's historical holdout predictions for the local dashboard.

Run in an analysis environment with the packages in requirements.txt. The
dashboard itself only reads the resulting JSON and needs no ML dependencies.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.tsa.arima.model import ARIMA


ROOT = Path(__file__).resolve().parent
MAX_CHART_POINTS = 220


def chart_points(index, actual, predicted):
    """Keep charts small while including both ends of the test interval."""
    indexes = np.unique(np.linspace(0, len(actual) - 1,
                                    min(len(actual), MAX_CHART_POINTS)).astype(int))
    return [{
        "timestamp": pd.Timestamp(index[i]).isoformat(),
        "actual": round(float(actual[i]), 4),
        "predicted": round(float(predicted[i]), 4),
    } for i in indexes]


def model_result(index, actual, predicted, horizon):
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    return {
        "mae": round(float(mean_absolute_error(actual, predicted)), 6),
        "rmse": round(float(np.sqrt(mean_squared_error(actual, predicted))), 6),
        "test_points": len(actual),
        "horizon": horizon,
        "points": chart_points(index, actual, predicted),
    }


def evaluate_source(mote):
    series = (mote.set_index("timestamp")["temperature_c"].astype(float)
              .resample("20s").mean().interpolate(method="time", limit=2)
              .dropna())
    if len(series) < 30:
        raise ValueError("At least 30 regularized points are required")

    # Keep the same features and chronological 80/20 split as the notebook.
    features = pd.DataFrame({
        "current": series,
        "lag_1": series.shift(1),
        "lag_2": series.shift(2),
        "next_value": series.shift(-1),
    }).dropna()
    split = int(len(features) * 0.8)
    train, test = features.iloc[:split], features.iloc[split:]
    columns = ["current", "lag_1", "lag_2"]
    linear = LinearRegression().fit(train[columns], train["next_value"])
    linear_pred = linear.predict(test[columns])
    # Historical scores use only the first 80% for training. For live inference,
    # fit the same features on the complete available snapshot after evaluation.
    live_linear = LinearRegression().fit(features[columns], features["next_value"])
    # A feature row at t predicts the next regularized reading at t + 20s.
    linear_times = test.index + pd.Timedelta(seconds=20)

    cutoff = int(len(series) * 0.8)
    arima_train, arima_test = series.iloc[:cutoff], series.iloc[cutoff:]
    arima = ARIMA(arima_train.to_numpy(), order=(1, 0, 0)).fit()
    arima_pred = arima.forecast(steps=len(arima_test))

    return {
        "source_id": int(mote["source_id"].iloc[0]),
        "sample_count": int(len(mote)),
        "first_timestamp": mote["timestamp"].min().isoformat(),
        "last_timestamp": mote["timestamp"].max().isoformat(),
        "target": "temperature_c",
        "live_linear_model": {
            "features": columns,
            "intercept": float(live_linear.intercept_),
            "coefficients": [float(value) for value in live_linear.coef_],
            "trained_on_points": int(len(features)),
            "trained_until": features.index[-1].isoformat(),
        },
        "linear_regression": model_result(
            linear_times, test["next_value"].to_numpy(), linear_pred,
            "Διαδοχική πρόβλεψη ενός βήματος με πρόσφατες γνωστές τιμές",
        ),
        "arima": model_result(
            arima_test.index, arima_test.to_numpy(), arima_pred,
            "Πρόβλεψη όλου του τμήματος ελέγχου χωρίς νέες τιμές",
        ),
    }


def evaluate_dataset(path, expected_origin):
    df = pd.read_csv(path)
    required = {"timestamp", "source_id", "temperature_c", "data_origin"}
    if not required.issubset(df.columns):
        raise ValueError("Missing columns in {}: {}".format(path,
                         sorted(required - set(df.columns))))
    if set(df["data_origin"].dropna()) != {expected_origin}:
        raise ValueError("Unexpected data_origin in {}".format(path))
    df["timestamp"] = pd.to_datetime(df["timestamp"].map(pd.Timestamp), utc=True)
    df = df.sort_values("timestamp")
    sources = {}
    for source_id, mote in df.groupby("source_id"):
        sources[str(int(source_id))] = evaluate_source(mote.copy())
    return {
        "data_origin": expected_origin,
        "sample_count": int(len(df)),
        "first_timestamp": df["timestamp"].min().isoformat(),
        "last_timestamp": df["timestamp"].max().isoformat(),
        "sources": sources,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic-csv", type=Path,
                        default=ROOT / "synthetic-3days.csv")
    parser.add_argument("--real-csv", type=Path, required=True)
    parser.add_argument("--output", type=Path,
                        default=ROOT.parent / "host" / "dashboard_forecasts.json")
    args = parser.parse_args()
    result = {
        "method": "Chronological 80/20 holdout; same methods as sensor_forecast.ipynb",
        "datasets": {
            "synthetic": evaluate_dataset(args.synthetic_csv, "synthetic"),
            "real": evaluate_dataset(args.real_csv, "real"),
        },
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False,
                                      separators=(",", ":")), encoding="utf-8")
    print("Wrote {} ({} bytes)".format(args.output, args.output.stat().st_size))
    for name, dataset in result["datasets"].items():
        for source_id, source in dataset["sources"].items():
            print(name, source_id, source["sample_count"],
                  source["linear_regression"]["mae"], source["arima"]["mae"])


if __name__ == "__main__":
    main()
