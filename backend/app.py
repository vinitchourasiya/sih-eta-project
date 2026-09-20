from flask import Flask, request, jsonify
from flask_cors import CORS
import pickle
import pandas as pd
import numpy as np
import random
import requests

app = Flask(__name__)
CORS(app)  # allows frontend to call this backend

# Load trained model and encoders
with open("model.pkl", "rb") as f:
    model = pickle.load(f)

with open("encoders.pkl", "rb") as f:
    encoders = pickle.load(f)

with open("feature_cols.pkl", "rb") as f:
    feature_cols = pickle.load(f)

stations = ["New Delhi", "Kota Jn", "Ratlam Jn", "Vadodara Jn", "Surat", "Mumbai Central"]
train_names = {
    "12951": "Mumbai Rajdhani Express",
    "12953": "August Kranti Rajdhani",
    "12009": "Shatabdi Express",
    "22119": "Tejas Express",
}

WEATHER_API_KEY = "4cb82387c8921a4d532d86ffb457b953"

STATION_COORDS = {
    "New Delhi": (28.6139, 77.2090),
    "Kota Jn": (25.2138, 75.8648),
    "Ratlam Jn": (23.3315, 75.0367),
    "Vadodara Jn": (22.3072, 73.1812),
    "Surat": (21.1702, 72.8311),
    "Mumbai Central": (19.0760, 72.8777),
}

def get_real_weather(station_name):
    lat, lon = STATION_COORDS.get(station_name, (28.6139, 77.2090))
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric"
        response = requests.get(url, timeout=5)
        data = response.json()
        condition = data["weather"][0]["main"]
        
        if condition in ["Rain", "Drizzle"]:
            return "Rain"
        elif condition == "Thunderstorm":
            return "Heavy Rain"
        elif condition in ["Fog", "Mist", "Haze"]:
            return "Fog"
        else:
            return "Clear"
    except Exception as e:
        print(f"Weather API error: {e}")
        return random.choice(weather_options)
    
weather_options = ["Clear", "Fog", "Rain", "Heavy Rain"]
congestion_options = ["Low", "Medium", "High"]
days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

@app.route("/")
def home():
    return jsonify({"message": "Train ETA Prediction API is running"})

@app.route("/predict", methods=["POST"])
def predict():
    req_data = request.get_json()
    train_number = req_data.get("trainNumber", "12345")
    station_index = req_data.get("stationIndex", None)
    train_name = train_names.get(str(train_number), "Unknown Train")

     # Use given station index if provided (for simulation), else random
    if station_index is not None and 0 <= station_index < len(stations) - 1:
        current_station = stations[station_index]
    else:
        current_station = random.choice(stations[:-1])
    next_idx = stations.index(current_station) + 1
    next_station = stations[next_idx]
    distance_km = round(random.uniform(20, 150), 1)
    scheduled_travel_time = round(distance_km / 60 * 60, 1)
    weather = get_real_weather(current_station)
    congestion = random.choice(congestion_options)
    historical_avg_delay = round(random.uniform(0, 20), 1)
    hour_of_day = random.randint(0, 23)
    day_of_week = random.choice(days)

    # Encode inputs
    input_dict = {
        "distance_km": distance_km,
        "scheduled_travel_time_min": scheduled_travel_time,
        "historical_avg_delay_min": historical_avg_delay,
        "hour_of_day": hour_of_day,
        "current_station_enc": encoders["current_station"].transform([current_station])[0],
        "next_station_enc": encoders["next_station"].transform([next_station])[0],
        "weather_enc": encoders["weather"].transform([weather])[0],
        "congestion_level_enc": encoders["congestion_level"].transform([congestion])[0],
        "day_of_week_enc": encoders["day_of_week"].transform([day_of_week])[0],
    }

    input_df = pd.DataFrame([input_dict])[feature_cols]
    predicted_delay = model.predict(input_df)[0]
    predicted_delay = max(0, round(float(predicted_delay), 1))

        # Confidence improves as train gets closer to destination
    station_position = stations.index(current_station)
    total_stations = len(stations)
    progress_ratio = station_position / (total_stations - 1)  # 0 to 1

    confidence_percent_value = int(70 + (progress_ratio * 25))  # 70% to 95%
    confidence_range = 8 - (progress_ratio * 5)  # narrows from 8 min to 3 min
    lower_bound = max(0, predicted_delay - confidence_range)
    upper_bound = predicted_delay + confidence_range

    # Simple explanation logic (based on which factor contributed most)
    reasons = []
    if weather in ["Fog", "Heavy Rain"]:
        reasons.append({"factor": weather, "impact": "High"})
    if congestion == "High":
        reasons.append({"factor": "Route Congestion", "impact": "High"})
    if historical_avg_delay > 10:
        reasons.append({"factor": "Historical Pattern", "impact": "Medium"})
    if not reasons:
        reasons.append({"factor": "Normal Conditions", "impact": "Low"})

    # Cascade impact simulation
    cascade_alerts = []
    if predicted_delay > 15:
        cascade_alerts.append(f"Connecting service from {next_station} may be affected")
    if predicted_delay > 20:
        cascade_alerts.append("Feeder transport delay likely")

    response = {
        "trainName": train_name,
        "trainNumber": train_number,
        "currentStation": current_station,
        "nextStation": next_station,
        "scheduledDelay": 0,
        "predictedDelayMin": predicted_delay,
        "etaRangeMin": lower_bound,
        "etaRangeMax": upper_bound,
        "confidencePercent": confidence_percent_value,
        "weather": weather,
        "congestion": congestion,
        "reasons": reasons,
        "cascadeAlerts": cascade_alerts
    }

    return jsonify(response)

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)