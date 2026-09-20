import pandas as pd
import numpy as np
import random

# Set seed for reproducibility
np.random.seed(42)
random.seed(42)

# Define a sample route with stations
stations = ["New Delhi", "Kota Jn", "Ratlam Jn", "Vadodara Jn", "Surat", "Mumbai Central"]
weather_options = ["Clear", "Fog", "Rain", "Heavy Rain"]

train_options = [
    {"number": 12951, "name": "Mumbai Rajdhani Express"},
    {"number": 12953, "name": "August Kranti Rajdhani"},
    {"number": 12009, "name": "Shatabdi Express"},
    {"number": 22119, "name": "Tejas Express"},
]

num_records = 2000
data = []

for i in range(num_records):
    train_choice = random.choice(train_options)
    train_number = train_choice["number"]
    train_name = train_choice["name"]

    station_index = random.randint(0, len(stations) - 2)  # not the last station
    current_station = stations[station_index]
    next_station = stations[station_index + 1]

    distance_km = round(random.uniform(20, 150), 1)
    scheduled_travel_time = round(distance_km / 60 * 60, 1)  # assume avg 60km/h -> minutes

    weather = random.choices(weather_options, weights=[60, 20, 15, 5])[0]
    congestion_level = random.choices(["Low", "Medium", "High"], weights=[50, 35, 15])[0]

    # Base delay depends on weather and congestion
    weather_delay = {"Clear": 0, "Fog": 15, "Rain": 8, "Heavy Rain": 25}[weather]
    congestion_delay = {"Low": 0, "Medium": 10, "High": 20}[congestion_level]

    # Historical average delay on this route (simulate route-specific pattern)
    historical_avg_delay = round(random.uniform(0, 20), 1)

    # Random noise
    noise = round(random.uniform(-5, 5), 1)

    # Actual delay (target variable)
    actual_delay_minutes = max(0, round(weather_delay + congestion_delay + historical_avg_delay * 0.5 + noise, 1))

    day_of_week = random.choice(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    hour_of_day = random.randint(0, 23)

    data.append({
        "train_name": train_name,
        "train_number": train_number,
        "current_station": current_station,
        "next_station": next_station,
        "distance_km": distance_km,
        "scheduled_travel_time_min": scheduled_travel_time,
        "weather": weather,
        "congestion_level": congestion_level,
        "historical_avg_delay_min": historical_avg_delay,
        "day_of_week": day_of_week,
        "hour_of_day": hour_of_day,
        "actual_delay_min": actual_delay_minutes
    })

df = pd.DataFrame(data)
df.to_csv("data/train_eta_data.csv", index=False)

print("Dataset generated successfully!")
print(f"Total records: {len(df)}")
print(df.head())