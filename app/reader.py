import pandas as pd
import xmltodict
from datetime import datetime
import json

ORIGINAL_FILE = "../original_files/Zepp20251220063122.tcx"


def load_tcx(path=ORIGINAL_FILE):
    with open(path, "r", encoding="utf-8") as f:
        return xmltodict.parse(f.read())


def as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def tcx_to_normalized_json(tcx):
    db = tcx["TrainingCenterDatabase"]
    activity = db["Activities"]["Activity"]

    # -------- META --------
    meta_activity = {
        "sport": activity.get("@Sport"),
        "id": activity.get("Id"),
        "notes": activity.get("Notes"),
        "creator": activity.get("Creator", {}).get("Name"),
    }
    meta_laps = []

    laps = as_list(activity["Lap"])
    for lap in laps:
        # Start time (atributo XML)
        meta_lap = {
            "startTime": lap.get("@StartTime"),
            "totalTimeSeconds": float(lap.get("TotalTimeSeconds", 0)),
            "distanceMeters": float(lap.get("DistanceMeters", 0)),
            "calories": int(lap.get("Calories", 0)),
            "averageHeartRateBpm": int(
                lap.get("AverageHeartRateBpm", {}).get("Value", 0)
            ),
            "maximumHeartRateBpm": int(
                lap.get("MaximumHeartRateBpm", {}).get("Value", 0)
            ),
            "intensity": lap.get("Intensity"),
            "triggerMethod": lap.get("TriggerMethod"),
            "tracks": [],
        }

        trackpoints = as_list(lap["Track"]["Trackpoint"])

        if trackpoints:
            first_tp_time = trackpoints[0].get("Time")
            start_time_ref = datetime.fromisoformat(
                first_tp_time.replace("Z", "+00:00")
            )
        else:
            # Fallback para o startTime do lap se não houver trackpoints
            start_time_ref = datetime.fromisoformat(
                lap.get("@StartTime").replace("Z", "+00:00")
            )

        for tp in trackpoints:
            time = datetime.fromisoformat(tp["Time"].replace("Z", "+00:00"))
            if start_time_ref is None:
                start_time_ref = time

            pos = tp.get("Position", {})
            hr_node = tp.get("HeartRateBpm")
            hr = int(hr_node["Value"]) if isinstance(hr_node, dict) else None

            trackpoint = {
                "t": round((time - start_time_ref).total_seconds(), 2),
                "lat": float(pos["LatitudeDegrees"]) if pos else None,
                "lon": float(pos["LongitudeDegrees"]) if pos else None,
                "alt": float(tp.get("AltitudeMeters", 0)),
                "dist": float(tp.get("DistanceMeters", 0)),
                "hr": hr,
                "cad": (
                    float(tp.get("Cadence", 0))
                    if tp.get("Cadence") is not None
                    else None
                ),
                "speed": (
                    float(tp.get("Extensions", {}).get("ns3:TPX", {}).get("ns3:Speed", 0))
                    if tp.get("Extensions") is not None
                    else None
                ),
            }

            meta_lap["tracks"].append(trackpoint)

        meta_laps.append(meta_lap)
    return {"meta_activity": meta_activity, "meta_laps": meta_laps}


tcx = load_tcx(ORIGINAL_FILE)
data = tcx_to_normalized_json(tcx)

with open("treino_normalizado.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
