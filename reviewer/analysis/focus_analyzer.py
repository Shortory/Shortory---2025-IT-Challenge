# focus_analyzer.py
import os
import json
import csv
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

def is_point_in_bbox(pupil: Optional[Tuple[float, float]], bbox, margin: int = 10) -> bool:
    if pupil is None:
        return False
    x, y = pupil
    x1, y1, x2, y2 = bbox
    return (x1 - margin) <= x <= (x2 + margin) and (y1 - margin) <= y <= (y2 + margin)

def attention_str_to_float(att_str):
    mapping = {"Low": 0.2, "Medium": 0.5, "High": 1.0}
    try:
        return float(att_str)
    except:
        return mapping.get(att_str, 0.0)

def analyze_focus(
    emotion_logs: List[Dict[str, Any]],
    object_logs: List[Dict[str, Any]],
    window_sec: int = 10,
    step_sec: int = 5,
    top_k: int = 3,
    debug: bool = False
) -> List[Dict[str, Any]]:
    if not emotion_logs or not object_logs:
        if debug:
            print("[DEBUG] emotion_logs 또는 object_logs가 비어 있음.")
        return []

    min_time = min(log["timestamp"] for log in emotion_logs)
    max_time = max(log["timestamp"] for log in emotion_logs)
    results: List[Dict[str, Any]] = []

    t = min_time
    while t < max_time - window_sec:
        emo_window = [e for e in emotion_logs if t <= e["timestamp"] < t + window_sec]
        if not emo_window:
            t += step_sec
            continue

        obj_window = [
            min(object_logs, key=lambda o: abs(o["timestamp"] - e["timestamp"]))
            for e in emo_window
        ]

        emotions = [e["emotion"] for e in emo_window]
        emotion_weights = {"surprise": 5, "happy": 4, "sad": 3, "angry": 2, "neutral": 1}
        dominant_emotion = max(set(emotions), key=emotions.count)
        emotion_score = np.mean([emotion_weights.get(e, 0) for e in emotions])
        attention_score = float(np.mean([e["attention"] for e in emo_window]))

        object_counter = {}
        for emo, nearest_obj_frame in zip(emo_window, obj_window):
            pupil = emo.get("pupil")
            for obj in nearest_obj_frame["objects"]:
                if is_point_in_bbox(pupil, obj["bbox"]):
                    label = obj["label"]
                    object_counter[label] = object_counter.get(label, 0) + 1

        if object_counter:
            focused_object, hits = max(object_counter.items(), key=lambda x: x[1])
            object_score = min(10.0, hits / max(len(emo_window), 1) * 10.0)
        else:
            focused_object = None
            object_score = 0.0

        final_score = 0.4 * attention_score + 0.3 * emotion_score + 0.3 * object_score

        if debug:
            print(f"[DEBUG] t={t:.2f}s | emo={dominant_emotion}, att={attention_score:.2f}, "
                  f"emo_score={emotion_score:.2f}, obj_score={object_score:.2f}, final={final_score:.2f}, "
                  f"focused_obj={focused_object}")

        results.append({
            "start": round(t, 2),
            "emotion": dominant_emotion,
            "object": focused_object,
            "score": round(float(final_score), 2),
            "attention_avg": round(float(attention_score), 2),
            "emotion_score": round(float(emotion_score), 2),
            "object_score": round(float(object_score), 2),
            "window": window_sec
        })

        t += step_sec

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]

def _load_emotion_logs_from_csv(log_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(log_path):
        raise FileNotFoundError(f"emotion log not found: {log_path}")

    logs: List[Dict[str, Any]] = []
    with open(log_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                pupil = None
                if row.get("pupil_x") and row.get("pupil_y"):
                    pupil = (float(row["pupil_x"]), float(row["pupil_y"]))
                # 주의: video_time 컬럼을 timestamp로 변환
                logs.append({
                    "timestamp": float(row["video_time"]),
                    "emotion": row["emotion"],
                    "attention": attention_str_to_float(row["attention"]),
                    "movement": row.get("movement", ""),
                    "pupil": pupil
                })
            except Exception as e:
                print("[CSV ERROR]", e, row)
                continue
    return logs

def _load_object_logs_from_json(object_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(object_path):
        raise FileNotFoundError(f"object log not found: {object_path}")
    with open(object_path, "r", encoding="utf-8") as f:
        return json.load(f)

def analyze_focus_from_logs(
    video_path: str,
    log_path: str,
    object_path: str,
    save_path: Optional[str] = None,
    window_sec: int = 10,
    step_sec: int = 5,
    top_k: int = 3
) -> List[Dict[str, Any]]:
    emotion_logs = _load_emotion_logs_from_csv(log_path)
    object_logs = _load_object_logs_from_json(object_path)

    segments = analyze_focus(
        emotion_logs,
        object_logs,
        window_sec=window_sec,
        step_sec=step_sec,
        top_k=top_k,
        debug=True  # 꼭 True로 두세요 (디버깅)
    )

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(segments, f, indent=2, ensure_ascii=False)

    return segments
