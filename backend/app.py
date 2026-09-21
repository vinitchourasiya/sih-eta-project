from flask import Flask, request, jsonify
from flask_cors import CORS
import pickle
import pandas as pd
import numpy as np
import random
import requests
import os
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# ---------------- MODEL FILES ----------------

with open("model.pkl", "rb") as f:
    model = pickle.load(f)

with open("encoders.pkl", "rb") as f:
    encoders = pickle.load(f)

with open("feature_cols.pkl", "rb") as f:
    feature_cols = pickle.load(f)


# ---------------- DEMO DATA ----------------

stations = [
    "New Delhi",
    "Kota Jn",
    "Ratlam Jn",
    "Vadodara Jn",
    "Surat",
    "Mumbai Central"
]

weather_options = ["Clear", "Fog", "Rain", "Heavy Rain"]
congestion_options = ["Low", "Medium", "High"]
days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

train_names = {
    "12951": "Mumbai Rajdhani Express",
    "12953": "August Kranti Rajdhani",
    "12009": "Shatabdi Express",
    "22119": "Tejas Express",
}

WEATHER_API_KEY = "4cb82387c8921a4d532d86ffb457b953"

RAILRADAR_API_KEY = os.getenv("RAILRADAR_API_KEY")


# ---------------- STATION COORDINATES ----------------

STATION_COORDS = {
    "New Delhi": (28.6139, 77.2090),
    "Kota Jn": (25.2138, 75.8648),
    "Ratlam Jn": (23.3315, 75.0367),
    "Vadodara Jn": (22.3072, 73.1812),
    "Surat": (21.1702, 72.8311),
    "Mumbai Central": (19.0760, 72.8777),
}


# ---------------- DEMO SCHEDULE ----------------

SCHEDULED_TIMES = {
    "New Delhi": "10:00 AM",
    "Kota Jn": "2:00 PM",
    "Ratlam Jn": "5:30 PM",
    "Vadodara Jn": "8:00 PM",
    "Surat": "9:30 PM",
    "Mumbai Central": "11:45 PM",
}


# ---------------- TIME HELPERS ----------------

def parse_time_str(iso_str):
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%I:%M %p").lstrip("0")
    except Exception:
        return "N/A"


def format_station_time(iso_str):
    if not iso_str:
        return "N/A"

    return parse_time_str(iso_str)


def add_minutes_to_iso(iso_str, minutes):
    try:
        dt = datetime.fromisoformat(iso_str)
        dt = dt + timedelta(minutes=minutes)
        return dt.strftime("%I:%M %p").lstrip("0")
    except Exception:
        return "N/A"


def get_actual_time_fallback(scheduled_str, delay_min):
    if not scheduled_str:
        return "N/A"

    try:
        dt = datetime.strptime(scheduled_str, "%I:%M %p")
        dt = dt + timedelta(minutes=delay_min)
        return dt.strftime("%I:%M %p").lstrip("0")
    except Exception:
        return "N/A"


# ---------------- WEATHER ----------------

def get_weather_by_coords(lat, lon):
    try:
        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?lat={lat}&lon={lon}"
            f"&appid={WEATHER_API_KEY}"
            f"&units=metric"
        )

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


def get_real_weather(station_name):
    lat, lon = STATION_COORDS.get(
        station_name,
        (28.6139, 77.2090)
    )

    return get_weather_by_coords(lat, lon)


# ---------------- REASONS ----------------

def build_reasons(
    weather,
    congestion,
    historical_avg_delay,
    current_station_name,
    real_delay=None
):
    reasons = []

    if real_delay is not None and real_delay > 0:
        impact = "High" if real_delay > 20 else "Medium"

        reasons.append({
            "factor": "Live Running Delay",
            "impact": impact,
            "explanation": (
                f"Live tracking shows this train is currently "
                f"running {round(real_delay)} minutes behind schedule."
            )
        })

    if weather == "Fog":
        reasons.append({
            "factor": "Fog",
            "impact": "High",
            "explanation": (
                f"Visibility is currently low near "
                f"{current_station_name}, reducing safe travel speed."
            )
        })

    elif weather == "Heavy Rain":
        reasons.append({
            "factor": "Heavy Rain",
            "impact": "High",
            "explanation": (
                f"Heavy rainfall near {current_station_name} "
                f"is affecting track conditions and speed."
            )
        })

    elif weather == "Rain":
        reasons.append({
            "factor": "Rain",
            "impact": "Medium",
            "explanation": (
                f"Light rain near {current_station_name} "
                f"is causing minor speed restrictions."
            )
        })

    if congestion == "High":
        reasons.append({
            "factor": "Route Congestion",
            "impact": "High",
            "explanation": (
                "Multiple trains are currently running on this "
                "section, causing signal delays."
            )
        })

    elif congestion == "Medium":
        reasons.append({
            "factor": "Route Congestion",
            "impact": "Medium",
            "explanation": (
                "Moderate traffic on this route is adding "
                "to the travel time."
            )
        })

    if historical_avg_delay > 10:
        reasons.append({
            "factor": "Historical Pattern",
            "impact": "Medium",
            "explanation": (
                f"This route typically sees around "
                f"{round(historical_avg_delay)} minutes of delay "
                f"during this time of day."
            )
        })

    if not reasons:
        reasons.append({
            "factor": "Normal Conditions",
            "impact": "Low",
            "explanation": (
                "No significant delay factors detected — "
                "train is running close to schedule."
            )
        })

    return reasons


# ---------------- EXTRA INFORMATION ----------------

def build_extras(
    predicted_delay,
    congestion,
    historical_avg_delay,
    current_station_name,
    next_station_name
):
    cascade_alerts = []

    if predicted_delay > 15:
        cascade_alerts.append(
            f"Connecting service from {next_station_name} may be affected"
        )

    if predicted_delay > 20:
        cascade_alerts.append(
            "Feeder transport delay likely"
        )

    connection_risk_score = min(
        95,
        int(
            predicted_delay * 2
            + (20 if congestion == "High" else 5)
        )
    )

    risk_level = (
        "High"
        if connection_risk_score >= 70
        else "Medium"
        if connection_risk_score >= 40
        else "Low"
    )

    connection_risk_factors = [
        f"{predicted_delay} min predicted delay",
        "8 min platform transfer buffer",
        (
            "Below average historical punctuality on this route"
            if historical_avg_delay > 10
            else "Good historical punctuality on this route"
        ),
    ]

    alternative_routes = []

    if predicted_delay > 15:
        alternative_routes = [
            {
                "option": "Stay on current train",
                "arrival": f"+{round(predicted_delay)} min late",
                "extraCost": "₹0",
                "risk": connection_risk_score
            },
            {
                "option": f"Change at {current_station_name}",
                "arrival": "Faster by ~20 min",
                "extraCost": "₹180",
                "risk": max(10, connection_risk_score - 40)
            },
            {
                "option": "Train + Bus combination",
                "arrival": "Faster by ~35 min",
                "extraCost": "₹240",
                "risk": max(5, connection_risk_score - 60)
            },
        ]

    if predicted_delay > 20:
        copilot_message = (
            f"Your train is running {round(predicted_delay)} minutes late. "
            f"Given the high connection risk ({connection_risk_score}%), "
            f"we recommend considering the alternative route options below "
            f"to save time."
        )

    elif predicted_delay > 10:
        copilot_message = (
            f"Your train is running about {round(predicted_delay)} "
            f"minutes late. It's a moderate delay — you should still "
            f"make most connections, but keep an eye on the risk score."
        )

    else:
        copilot_message = (
            "Your train is running close to schedule. "
            "No action needed — sit back and relax!"
        )

    return (
        cascade_alerts,
        connection_risk_score,
        risk_level,
        connection_risk_factors,
        alternative_routes,
        copilot_message
    )


# ---------------- RAILRADAR API ----------------

def try_railradar(train_number):

    if not RAILRADAR_API_KEY:
        print("RAILRADAR_API_KEY not found.")
        return None

    try:
        url = (
            f"https://api.railradar.in/v1/trains/"
            f"{train_number}/live"
        )

        params = {
            "haltsOnly": "true",
            "includeCoordinates": "true"
        }

        headers = {
            "Authorization": f"Bearer {RAILRADAR_API_KEY}"
        }

        resp = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=8
        )

        print(
            f"RailRadar status code: {resp.status_code}"
        )

        if resp.status_code != 200:
            print(
                f"RailRadar response body: "
                f"{resp.text[:300]}"
            )
            return None

        payload = resp.json()

        if not payload.get("success"):
            print(
                f"RailRadar success=false: {payload}"
            )
            return None

        return payload["data"]

    except Exception as e:
        print(
            f"RailRadar API exception: {e}"
        )
        return None


# ---------------- HOME ----------------

@app.route("/")
def home():
    return jsonify({
        "message": "Train ETA Prediction API is running"
    })


# ---------------- PREDICT ----------------

@app.route("/predict", methods=["POST"])
def predict():

    req_data = request.get_json() or {}

    train_number = req_data.get(
        "trainNumber",
        "12345"
    )

    station_index = req_data.get(
        "stationIndex",
        None
    )

    live_data = try_railradar(train_number)

    # =====================================================
    # REAL LIVE TRAIN MODE
    # =====================================================

    if live_data:

        train_name_real = live_data.get(
            "trainName",
            f"Train {train_number}"
        )

        real_delay = float(
            live_data.get("delayMinutes") or 0
        )

        route_raw = live_data.get(
            "route",
            []
        )

        current_code = (
            live_data.get("currentLocation", {})
            .get("stationCode")
        )

        # ---------------- BUILD ROUTE ----------------

        route = []
        current_idx = 0

        for i, stop in enumerate(route_raw):

            route.append({
                "code": stop.get("stationCode"),
                "name": stop.get("stationName"),

                "scheduledArrival": stop.get(
                    "scheduledArrival"
                ),

                "scheduledArrivalTime": format_station_time(
                    stop.get("scheduledArrival")
                ),

                "scheduledDeparture": stop.get(
                    "scheduledDeparture"
                ),

                "scheduledDepartureTime": format_station_time(
                    stop.get("scheduledDeparture")
                ),

                "actualArrival": stop.get(
                    "actualArrival"
                ),

                "actualDeparture": stop.get(
                    "actualDeparture"
                ),

                "delayMinutes": stop.get(
                    "delayMinutes"
                ),

                "status": "upcoming"
            })

            # IMPORTANT:
            # This MUST remain inside the for loop.
            if stop.get("stationCode") == current_code:
                current_idx = i

        # ---------------- STATION STATUS ----------------

        for i, stop in enumerate(route):

            if i < current_idx:
                stop["status"] = "departed"

            elif i == current_idx:
                stop["status"] = "current"

            else:
                stop["status"] = "upcoming"

        # ---------------- CURRENT / NEXT STATION ----------------

        current_station_name = (
            route[current_idx]["name"]
            if route
            else "Unknown"
        )

        next_stop = (
            route[current_idx + 1]
            if current_idx + 1 < len(route)
            else (
                route[current_idx]
                if route
                else {"name": "Destination"}
            )
        )

        next_station_name = next_stop["name"]

        # ---------------- NEXT RAW STATION ----------------

        next_raw = (
            route_raw[current_idx + 1]
            if current_idx + 1 < len(route_raw)
            else (
                route_raw[current_idx]
                if route_raw
                else {}
            )
        )

        scheduled_iso = (
            next_raw.get("scheduledArrival")
            or next_raw.get("scheduledDeparture")
        )

        scheduled_arrival_time = (
            parse_time_str(scheduled_iso)
            if scheduled_iso
            else "N/A"
        )

        actual_arrival_iso = next_raw.get(
            "actualArrival"
        )

        actual_arrival_time = (
            format_station_time(
                actual_arrival_iso
            )
            if actual_arrival_iso
            else "N/A"
        )

        # ---------------- LOCATION ----------------

        lat = (
            route_raw[current_idx].get("lat")
            if current_idx < len(route_raw)
            else None
        )

        lng = (
            route_raw[current_idx].get("lng")
            if current_idx < len(route_raw)
            else None
        )

        if lat is not None and lng is not None:
            weather = get_weather_by_coords(
                lat,
                lng
            )
        else:
            weather = random.choice(
                weather_options
            )

        # ---------------- PREDICTION ----------------

        congestion = random.choice(
            congestion_options
        )

        historical_avg_delay = round(
            random.uniform(0, 20),
            1
        )

        total_stops = max(
            len(route),
            1
        )

        progress_ratio = (
            current_idx
            / max(total_stops - 1, 1)
        )

        confidence_percent_value = int(
            70 + (progress_ratio * 25)
        )

        confidence_range = (
            8 - (progress_ratio * 5)
        )

        predicted_delay = round(
            real_delay,
            1
        )

        lower_bound = max(
            0,
            round(
                predicted_delay - confidence_range,
                1
            )
        )

        upper_bound = round(
            predicted_delay + confidence_range,
            1
        )

        # ---------------- REASONS ----------------

        reasons = build_reasons(
            weather,
            congestion,
            historical_avg_delay,
            current_station_name,
            real_delay=real_delay
        )

        (
            cascade_alerts,
            risk_score,
            risk_level,
            risk_factors,
            alt_routes,
            copilot_msg
        ) = build_extras(
            predicted_delay,
            congestion,
            historical_avg_delay,
            current_station_name,
            next_station_name
        )

        # ---------------- RESPONSE ----------------

        response = {

            "trainName": train_name_real,

            "trainNumber": train_number,

            "currentStation": current_station_name,

            "nextStation": next_station_name,

            "route": route,

            "isLive": True,

            "scheduledDelay": 0,

            "predictedDelayMin": predicted_delay,

            "etaRangeMin": lower_bound,

            "etaRangeMax": upper_bound,

            "scheduledArrivalTime": scheduled_arrival_time,

            "actualArrivalTime": actual_arrival_time,

            "predictedArrivalMin": (
                add_minutes_to_iso(
                    scheduled_iso,
                    lower_bound
                )
                if scheduled_iso
                else "N/A"
            ),

            "predictedArrivalMax": (
                add_minutes_to_iso(
                    scheduled_iso,
                    upper_bound
                )
                if scheduled_iso
                else "N/A"
            ),

            "confidencePercent": confidence_percent_value,

            "weather": weather,

            "congestion": congestion,

            "reasons": reasons,

            "cascadeAlerts": cascade_alerts,

            "connectionRiskScore": risk_score,

            "connectionRiskLevel": risk_level,

            "connectionRiskFactors": risk_factors,

            "alternativeRoutes": alt_routes,

            "copilotMessage": copilot_msg,
        }

        return jsonify(response)

    # =====================================================
    # FALLBACK DEMO MODE
    # =====================================================

    train_name = train_names.get(
        str(train_number),
        f"Train {train_number}"
    )

    if (
        station_index is not None
        and 0 <= station_index < len(stations) - 1
    ):
        current_station = stations[
            station_index
        ]

    else:
        current_station = random.choice(
            stations[:-1]
        )

    next_idx = (
        stations.index(current_station) + 1
    )

    next_station = stations[next_idx]

    distance_km = round(
        random.uniform(20, 150),
        1
    )

    scheduled_travel_time = round(
        distance_km / 60 * 60,
        1
    )

    weather = get_real_weather(
        current_station
    )

    congestion = random.choice(
        congestion_options
    )

    historical_avg_delay = round(
        random.uniform(0, 20),
        1
    )

    hour_of_day = random.randint(
        0,
        23
    )

    day_of_week = random.choice(
        days
    )

    # ---------------- MODEL INPUT ----------------

    input_dict = {
        "distance_km": distance_km,

        "scheduled_travel_time_min":
            scheduled_travel_time,

        "historical_avg_delay_min":
            historical_avg_delay,

        "hour_of_day":
            hour_of_day,

        "current_station_enc":
            encoders["current_station"].transform(
                [current_station]
            )[0],

        "next_station_enc":
            encoders["next_station"].transform(
                [next_station]
            )[0],

        "weather_enc":
            encoders["weather"].transform(
                [weather]
            )[0],

        "congestion_level_enc":
            encoders["congestion_level"].transform(
                [congestion]
            )[0],

        "day_of_week_enc":
            encoders["day_of_week"].transform(
                [day_of_week]
            )[0],
    }

    input_df = pd.DataFrame(
        [input_dict]
    )[feature_cols]

    predicted_delay = model.predict(
        input_df
    )[0]

    predicted_delay = max(
        0,
        round(float(predicted_delay), 1)
    )

    station_position = stations.index(
        current_station
    )

    total_stations = len(stations)

    progress_ratio = (
        station_position
        / (total_stations - 1)
    )

    confidence_percent_value = int(
        70 + (progress_ratio * 25)
    )

    confidence_range = (
        8 - (progress_ratio * 5)
    )

    lower_bound = max(
        0,
        predicted_delay - confidence_range
    )

    upper_bound = (
        predicted_delay
        + confidence_range
    )

    # ---------------- REASONS ----------------

    reasons = build_reasons(
        weather,
        congestion,
        historical_avg_delay,
        current_station
    )

    (
        cascade_alerts,
        risk_score,
        risk_level,
        risk_factors,
        alt_routes,
        copilot_msg
    ) = build_extras(
        predicted_delay,
        congestion,
        historical_avg_delay,
        current_station,
        next_station
    )

    # ---------------- DEMO ROUTE ----------------

    route = []

    for i, station_name in enumerate(stations):

        scheduled_time = SCHEDULED_TIMES.get(
            station_name,
            "N/A"
        )

        route.append({
            "code": station_name[:3].upper(),

            "name": station_name,

            "scheduledArrivalTime":
                scheduled_time,

            "scheduledDepartureTime":
                scheduled_time,

            "actualArrival":
                None,

            "actualDeparture":
                None,

            "delayMinutes":
                None,

            "status": (
                "departed"
                if i < station_position
                else "current"
                if i == station_position
                else "upcoming"
            )
        })

    scheduled_str = SCHEDULED_TIMES.get(
        next_station
    )

    response = {

        "trainName": train_name,

        "trainNumber": train_number,

        "currentStation": current_station,

        "nextStation": next_station,

        "route": route,

        "isLive": False,

        "scheduledDelay": 0,

        "predictedDelayMin":
            predicted_delay,

        "etaRangeMin":
            lower_bound,

        "etaRangeMax":
            upper_bound,

        "scheduledArrivalTime":
            scheduled_str or "N/A",

        "actualArrivalTime":
            "N/A",

        "predictedArrivalMin":
            get_actual_time_fallback(
                scheduled_str,
                lower_bound
            ),

        "predictedArrivalMax":
            get_actual_time_fallback(
                scheduled_str,
                upper_bound
            ),

        "confidencePercent":
            confidence_percent_value,

        "weather": weather,

        "congestion": congestion,

        "reasons": reasons,

        "cascadeAlerts": cascade_alerts,

        "connectionRiskScore":
            risk_score,

        "connectionRiskLevel":
            risk_level,

        "connectionRiskFactors":
            risk_factors,

        "alternativeRoutes":
            alt_routes,

        "copilotMessage":
            copilot_msg,
    }

    return jsonify(response)


# ---------------- RUN SERVER ----------------

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        debug=True,
        host="0.0.0.0",
        port=port
    )