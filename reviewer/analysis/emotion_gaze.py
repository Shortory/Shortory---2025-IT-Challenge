import os
import csv
import cv2
import numpy as np
from tensorflow.keras.models import load_model
import mediapipe as mp
from typing import Tuple

# 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, '..'))
MODEL_DIR = os.path.join(ROOT_DIR, 'models')
LOG_DIR = os.path.join(ROOT_DIR, 'logs')

# 모델 불러오기
MODEL_PATH = os.path.join(MODEL_DIR, 'emotion_tl2_model.h5')
model = load_model(MODEL_PATH, compile=False)

# 파라미터 설정
shape_x, shape_y = 96, 96
emotion_weights = {"surprise": 5, "happy": 4, "sad": 3, "angry": 2, "neutral": 1}
mapped_emotions = ["angry", "happy", "neutral", "sad", "surprise"]

# 얼굴 인식
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1, refine_landmarks=True)

# 이전 프레임 중심 저장용
prev_pupil = None


def get_pupil_center(landmarks, image_shape):
    h, w = image_shape[:2]
    try:
        left = landmarks[468]
        right = landmarks[473]
        x = int((left.x + right.x) * 0.5 * w)
        y = int((left.y + right.y) * 0.5 * h)
        return (x, y)
    except:
        return None


def classify_movement(prev, curr):
    if not prev or not curr:
        return "UNKNOWN"
    dist = np.linalg.norm(np.array(curr) - np.array(prev))
    if dist < 8:
        return "HIGH_FOCUS"
    elif dist < 20:
        return "MEDIUM_FOCUS"
    else:
        return "LOW_FOCUS"


def emotion_weight(emotion):
    return emotion_weights.get(emotion.lower(), 0)


def calculate_attention_score(movement, emotion_score):
    eye_score = 10 if movement == "HIGH_FOCUS" else 5 if movement == "MEDIUM_FOCUS" else 0
    return round(eye_score * 0.6 + emotion_score * 0.4, 2)


def extract_face_rgb(frame, faces):
    for x, y, w, h in faces:
        face = frame[y:y + h, x:x + w]
        resized = cv2.resize(face, (shape_x, shape_y)).astype(np.float32) / 255.0
        return np.reshape(resized, (1, shape_x, shape_y, 3))
    return None


def analyze_frame_np(frame):
    global prev_pupil
    if frame is None:
        return {"emotion": "Error", "attention": 0, "movement": "UNKNOWN", "pupil": None}

    try:
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = face_cascade.detectMultiScale(gray, 1.05, 3, minSize=(60, 60))
        if len(faces) == 0:
            return {"emotion": "Unknown", "attention": 0, "movement": "UNKNOWN", "pupil": None}

        face_img = extract_face_rgb(frame, faces)
        if face_img is None:
            return {"emotion": "Unknown", "attention": 0, "movement": "UNKNOWN", "pupil": None}

        pred = model.predict(face_img, verbose=0)[0]
        idx_em = np.argmax(pred)
        emotion = mapped_emotions[idx_em]
        conf = float(pred[idx_em])

        conf_score = 2 if conf > 0.7 else 1 if conf > 0.5 else 0
        emotion_score = min(10, conf_score + emotion_weight(emotion))

        results = face_mesh.process(rgb)
        pupil = None
        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark
            pupil = get_pupil_center(landmarks, frame.shape)

        movement = classify_movement(prev_pupil, pupil)
        prev_pupil = pupil

        attention = calculate_attention_score(movement, emotion_score)

        return {
            "emotion": emotion,
            "confidence": conf,
            "movement": movement,
            "attention": attention,
            "pupil": pupil
        }

    except Exception as e:
        print(f"[ERROR] 분석 실패: {e}")
        return {"emotion": "Error", "attention": 0, "movement": "UNKNOWN", "pupil": None}


def analyze_image(image_data: bytes) -> Tuple[str, str]:
    """
    base64 이미지 데이터를 받아 emotion, attention 분석 결과 반환
    """
    nparr = np.frombuffer(image_data, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    result = analyze_frame_np(frame)
    emotion = result.get("emotion", "Unknown")
    attention_score = result.get("attention", 0)

    # 정성적 attention 레벨 분류
    if attention_score >= 8:
        attention = "High"
    elif attention_score >= 4:
        attention = "Medium"
    else:
        attention = "Low"

    return emotion, attention


def load_emotion_logs(video_id="sample"):
    log_path = os.path.join(LOG_DIR, f"{video_id}_emotion_log.csv")
    if not os.path.exists(log_path):
        print(f"[ERROR] 로그 파일 없음: {log_path}")
        return []

    logs = []
    with open(log_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                logs.append({
                    "timestamp": float(row["timestamp"]),
                    "emotion": row["emotion"],
                    "attention": float(row["attention"]),
                    "movement": row["movement"],
                    "pupil": (float(row["pupil_x"]), float(row["pupil_y"])) if row["pupil_x"] and row["pupil_y"] else None
                })
            except:
                continue
    return logs
