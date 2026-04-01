import joblib
import pandas as pd

MODEL_FILE = "time_to_full_model2.joblib"
DATA_FILE = "predictive_training_data.csv"

def main():
    bundle = joblib.load(MODEL_FILE)
    model = bundle["model"]
    features = bundle["features"]

    df = pd.read_csv(DATA_FILE, parse_dates=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    sample = df.tail(20).copy()
    sample["predicted_time_to_full_minutes"] = model.predict(sample[features]).round(1)

    print(sample[[
        "timestamp",
        "distance_cm",
        "weight_g",
        "pir",
        "fill_percent",
        "time_to_full_minutes",
        "predicted_time_to_full_minutes"
    ]].to_string(index=False))

if __name__ == "__main__":
    main()