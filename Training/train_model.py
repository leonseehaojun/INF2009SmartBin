import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score

DATA_FILE = "predictive_training_data.csv"
MODEL_FILE = "time_to_full_model.joblib"

FEATURES = [
    "distance_cm",
    "weight_g",
    "pir",
    "fill_percent",
    "hour",
    "day_of_week",
    "minute_of_day",
    "delta_fill_3",
    "delta_weight_3",
    "pir_recent_3",
    "fill_rate_15m",
    "fill_rate_30m",
    "weight_rate_15m",
    "weight_rate_30m",
    "pir_count_15m",
    "pir_count_30m",
]

def main():
    df = pd.read_csv(DATA_FILE, parse_dates=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    X = df[FEATURES]
    y = df["time_to_full_minutes"]

    split_idx = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    model = RandomForestRegressor(
        n_estimators=300,
        random_state=42,
        min_samples_leaf=3,
        n_jobs=-1,
    )

    sample_weight = (
        1
        + 2 * (y_train <= 120)
        + 3 * (y_train <= 60)
        + 5 * (y_train <= 30)
    )

    model.fit(X_train, y_train, sample_weight=sample_weight)

    preds = model.predict(X_test)

    mae = mean_absolute_error(y_test, preds)
    rmse = root_mean_squared_error(y_test, preds)
    r2 = r2_score(y_test, preds)

    print(f"Train rows: {len(X_train)}")
    print(f"Test rows : {len(X_test)}")
    print(f"MAE  : {mae:.2f} minutes")
    print(f"RMSE : {rmse:.2f} minutes")
    print(f"R^2  : {r2:.4f}")

    importance_df = pd.DataFrame({
        "feature": FEATURES,
        "importance": model.feature_importances_
    }).sort_values("importance", ascending=False)

    print("\nFeature importances:")
    print(importance_df.to_string(index=False))

    preview = pd.DataFrame({
        "actual_minutes": y_test.iloc[:15].values,
        "predicted_minutes": preds[:15].round(1)
    })
    print("\nFirst 15 test predictions:")
    print(preview.to_string(index=False))

    joblib.dump({"model": model, "features": FEATURES}, MODEL_FILE)
    print(f"\nSaved model to {MODEL_FILE}")

if __name__ == "__main__":
    main()