"""
alternatives.py
---------------
Finds REAL alternative trains (number + name + timings) that a passenger can
switch to at an upcoming station when their current train is running late.

Data source: RailRadar  GET /v1/trains/between/{from}/{to}?date=YYYY-MM-DD
(no AI guessing: every suggested train comes from the API).
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, time as dtime
from zoneinfo import ZoneInfo

import requests

IST = ZoneInfo("Asia/Kolkata")
RAILRADAR_BASE = "https://api.railradar.in"

# ---------------- TUNABLE SETTINGS ----------------

MIN_TRANSFER_MIN = 15        # minimum time needed to change trains at the station
MAX_WAIT_MIN = 240           # ignore trains leaving more than 4 hours after you arrive
MAX_CHANGE_STATIONS = 3      # how many upcoming stations to check
MIN_TIME_SAVED_MIN = 10      # suggest a switch only if it saves at least this much
MAX_SUGGESTIONS = 3          # how many alternative trains to return
CACHE_TTL_SEC = 120          # cache API answers for 2 minutes (saves API quota)

_cache = {}


# ---------------- SMALL HELPERS ----------------

def _iso_to_ist(iso_str):
    """ISO string -> naive datetime in IST (or None)."""
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str)
    except Exception:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(IST).replace(tzinfo=None)
    return dt


def _fmt(dt):
    return dt.strftime("%I:%M %p").lstrip("0")


def _get_trains_between(from_code, to_code, date_str):
    """Calls RailRadar trains-between-stations (with a small cache)."""
    key = (from_code, to_code, date_str)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL_SEC:
        return hit[1]

    api_key = os.getenv("RAILRADAR_API_KEY")
    if not api_key:
        return []

    try:
        resp = requests.get(
            f"{RAILRADAR_BASE}/v1/trains/between/{from_code}/{to_code}",
            params={"date": date_str},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=8,
        )
        if resp.status_code != 200:
            print(f"[alternatives] {from_code}->{to_code} status {resp.status_code}: {resp.text[:200]}")
            return []
        payload = resp.json()
        if not payload.get("success"):
            return []
        trains = (payload.get("data") or {}).get("trains", [])
        _cache[key] = (time.time(), trains)
        return trains
    except Exception as e:
        print(f"[alternatives] API error {from_code}->{to_code}: {e}")
        return []


# ---------------- MAIN FINDER ----------------

def find_alternative_trains(route_raw, current_idx, delay_min, train_number):
    """
    route_raw    : RailRadar live route (list of stops with stationCode, scheduledArrival ...)
    current_idx  : index of the train's current station in route_raw
    delay_min    : live delay of the user's train in minutes
    train_number : the user's own train (excluded from suggestions)

    Returns a list of dicts (best first), each describing:
    "get off at X, board train N (name), departs T, reaches destination at T2".
    """
    if not route_raw or current_idx + 2 >= len(route_raw):
        return []

    dest = route_raw[-1]
    dest_code = dest.get("stationCode")
    dest_name = dest.get("stationName") or dest_code
    if not dest_code:
        return []

    # When will the user's own train reach the destination?
    orig_dest_sched = _iso_to_ist(dest.get("scheduledArrival") or dest.get("scheduledDeparture"))
    orig_dest_eta = (
        orig_dest_sched + timedelta(minutes=delay_min) if orig_dest_sched else None
    )

    # Upcoming stations (excluding the destination itself) where the user could change
    stations = []
    for stop in route_raw[current_idx + 1:-1][:MAX_CHANGE_STATIONS]:
        code = stop.get("stationCode")
        sched = _iso_to_ist(stop.get("scheduledArrival") or stop.get("scheduledDeparture"))
        if not code or not sched:
            continue
        arrive = sched + timedelta(minutes=delay_min)      # when the user's train gets there
        ready = arrive + timedelta(minutes=MIN_TRANSFER_MIN)
        stations.append({
            "code": code,
            "name": stop.get("stationName") or code,
            "arrive": arrive,
            "ready": ready,
        })

    if not stations:
        return []

    # Build the API jobs (a window can cross midnight, so up to 2 dates per station)
    jobs = []
    for st in stations:
        window_end = st["ready"] + timedelta(minutes=MAX_WAIT_MIN)
        for d in sorted({st["ready"].date(), window_end.date()}):
            jobs.append((st["code"], dest_code, d.strftime("%Y-%m-%d")))

    with ThreadPoolExecutor(max_workers=4) as pool:
        answers = list(pool.map(lambda j: _get_trains_between(*j), jobs))
    results = dict(zip(jobs, answers))

    best_per_station = {}

    for st in stations:
        window_end = st["ready"] + timedelta(minutes=MAX_WAIT_MIN)

        for d in sorted({st["ready"].date(), window_end.date()}):
            trains = results.get((st["code"], dest_code, d.strftime("%Y-%m-%d")), [])

            for item in trains:
                t = item.get("train") or {}
                frm = item.get("from") or {}
                number = str(t.get("number") or "")
                dep_str = frm.get("departure")
                duration = item.get("duration")

                if not number or number == str(train_number):
                    continue
                if not dep_str or duration is None:
                    continue

                try:
                    hh, mm = dep_str.split(":")[:2]
                    dep = datetime.combine(d, dtime(int(hh), int(mm)))
                except Exception:
                    continue

                if dep < st["ready"] or dep > window_end:
                    continue

                reach = dep + timedelta(minutes=float(duration))

                saved = None
                if orig_dest_eta:
                    saved = int((orig_dest_eta - reach).total_seconds() // 60)
                    if saved < MIN_TIME_SAVED_MIN:
                        continue

                buffer_min = int((dep - st["arrive"]).total_seconds() // 60)

                if buffer_min < 20:
                    risk = 55
                elif buffer_min < 40:
                    risk = 35
                elif buffer_min < 90:
                    risk = 25
                else:
                    risk = 15

                instruction = (
                    f"Get off at {st['name']} ({st['code']}) around {_fmt(st['arrive'])} "
                    f"and board {number} {t.get('name', '')}, departing {_fmt(dep)}. "
                    f"It reaches {dest_name} at {_fmt(reach)}"
                )
                if saved is not None:
                    instruction += f", about {saved} min earlier than your current train."
                else:
                    instruction += "."

                option = {
                    "type": "train_change",
                    "option": f"Switch to {number} {t.get('name', '')} at {st['name']}",
                    "arrival": (
                        f"Reach {dest_name} {_fmt(reach)}"
                        + (f" · {saved} min earlier" if saved is not None else "")
                    ),
                    "extraCost": "New ticket needed",
                    "risk": risk,
                    "changeStation": {"code": st["code"], "name": st["name"]},
                    "getOffTime": _fmt(st["arrive"]),
                    "train": {
                        "number": number,
                        "name": t.get("name", ""),
                        "type": t.get("type", ""),
                    },
                    "departure": _fmt(dep),
                    "destinationName": dest_name,
                    "destinationArrival": _fmt(reach),
                    "timeSavedMin": saved,
                    "bufferMin": buffer_min,
                    "instruction": instruction,
                    "_reach": reach,
                }

                # keep only the earliest-reaching train for each change station
                prev = best_per_station.get(st["code"])
                if prev is None or reach < prev["_reach"]:
                    best_per_station[st["code"]] = option

    ranked = sorted(best_per_station.values(), key=lambda o: o["_reach"])[:MAX_SUGGESTIONS]
    for o in ranked:
        o.pop("_reach", None)
    return ranked


# ---------------- RESPONSE BUILDERS ----------------

def build_alternative_routes(predicted_delay, risk_score, alt_trains):
    """Replaces the old hard-coded alternatives (which had made-up costs)."""
    if predicted_delay <= 15:
        return []

    routes = [{
        "type": "stay",
        "option": "Stay on current train",
        "arrival": f"+{round(predicted_delay)} min late",
        "extraCost": "₹0",
        "risk": risk_score,
    }]

    if alt_trains:
        routes.extend(alt_trains)
    else:
        routes.append({
            "type": "info",
            "option": "No faster connecting train found",
            "arrival": "Nothing on the upcoming stations beats your current train. "
                       "You could compare bus or cab options.",
            "extraCost": "Varies",
            "risk": None,
        })

    return routes


def build_copilot_message(predicted_delay, risk_score, alt_trains, default_msg):
    if predicted_delay <= 15 or not alt_trains:
        return default_msg

    best = alt_trains[0]
    return (
        f"Your train is running {round(predicted_delay)} minutes late "
        f"(connection risk {risk_score}%). Best option: {best['instruction']}"
    )