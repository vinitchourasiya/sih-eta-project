import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import xgboost as xgb
import pickle

# Load dataset
df = pd.read_csv("data/train_eta_data.csv")

# Encode categorical columns
categorical_cols = ["current_station", "next_station", "weather", "congestion_level", "day_of_week"]
encoders = {}

for col in categorical_cols:
    le = LabelEncoder()
    df[col + "_enc"] = le.fit_transform(df[col])
    encoders[col] = le

# Features and target
feature_cols = [
    "distance_km", "scheduled_travel_time_min", "historical_avg_delay_min",
    "hour_of_day", "current_station_enc", "next_station_enc",
    "weather_enc", "congestion_level_enc", "day_of_week_enc"
]

X = df[feature_cols]
y = df["actual_delay_min"]

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train XGBoost model
model = xgb.XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42)
model.fit(X_train, y_train)

# Evaluate
train_score = model.score(X_train, y_train)
test_score = model.score(X_test, y_test)
print(f"Train R2 Score: {train_score:.3f}")
print(f"Test R2 Score: {test_score:.3f}")

# Save model and encoders
with open("model.pkl", "wb") as f:
    pickle.dump(model, f)

with open("encoders.pkl", "wb") as f:
    pickle.dump(encoders, f)

with open("feature_cols.pkl", "wb") as f:
    pickle.dump(feature_cols, f)

print("Model trained and saved successfully!")