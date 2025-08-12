# record_emotion_log.py
import os
import cv2
import csv
import time
import threading
import numpy as np
from tensorflow.keras.models import load_model
import mediapipe as mp

# 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, '..'))
MODEL_DIR = os.path.join(ROOT_DIR, 'models')
LOG_DIR = os.path.join(ROOT_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# 모델 설정
shape_x, shape_y = 96, 96
emotion_weights = {"surprise": 5, "happy": 4, "sad": 3, "angry": 2, "neutral": 1}
mapped_emotions = ["angry", "happy", "neutral", "sad", "surprise"]
model = load_model(os.path.join(MODEL_DIR, "emotion_tl2_model.h5"), compile=False)

# 얼굴 인식 & 시선 추적 설정
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1, refine_landmarks=True)

# 상태 변수
prev_pupil = None
recording_active = False
recording_thread = None

# 유틸 함수
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

def emotion_weight(emotion):
    return emotion_weights.get(emotion.lower(), 0)

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

def calculate_attention_score(movement, emotion_score):
    eye_score = 10 if movement == "HIGH_FOCUS" else 5 if movement == "MEDIUM_FOCUS" else 0
    return round(eye_score * 0.6 + emotion_score * 0.4, 2)

def analyze_frame(frame):
    global prev_pupil

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    results = face_mesh.process(rgb)

    pupil = None
    if results.multi_face_landmarks:
        landmarks = results.multi_face_landmarks[0].landmark
        pupil = get_pupil_center(landmarks, frame.shape)

    movement = classify_movement(prev_pupil, pupil)
    prev_pupil = pupil

    faces = face_cascade.detectMultiScale(gray, 1.05, 3, minSize=(60, 60))
    if len(faces) == 0:
        return "Unknown", 0.0, movement, pupil

    x, y, w, h = faces[0]
    face = frame[y:y + h, x:x + w]
    face_resized = cv2.resize(face, (shape_x, shape_y)).astype(np.float32) / 255.0
    face_input = np.reshape(face_resized, (1, shape_x, shape_y, 3))

    pred = model.predict(face_input, verbose=0)[0]
    idx_em = np.argmax(pred)
    emotion = mapped_emotions[idx_em]
    conf = pred[idx_em]

    conf_score = 2 if conf > 0.7 else 1 if conf > 0.5 else 0
    emotion_score = min(10, conf_score + emotion_weight(emotion))
    attention = calculate_attention_score(movement, emotion_score)

    return emotion, attention, movement, pupil


def record_loop(video_id="sample"):
    global recording_active
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] 웹캠을 열 수 없습니다.")
        return

    start_time = time.time()
    filename = os.path.join(LOG_DIR, f"{video_id}_emotion_log.csv")

    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "emotion", "attention", "movement", "pupil_x", "pupil_y"])

        print("[INFO] 감정/시선 로그 기록 시작 (ESC: 종료)")

        while recording_active:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            timestamp = round(time.time() - start_time, 2)

            emotion, attention, movement, pupil = analyze_frame(frame)
            pupil_x, pupil_y = pupil if pupil else ("", "")

            print(f"[{timestamp:5.2f}s] 감정={emotion}, 집중도={attention:.2f}, 시선={movement}")
            writer.writerow([timestamp, emotion, attention, movement, pupil_x, pupil_y])

            cv2.imshow("Webcam Analysis", frame)
            if cv2.waitKey(1) & 0xFF == 27:
                break

    cap.release()
    cv2.destroyAllWindows()
    print(f"[INFO] 로그 저장 완료: {filename}")

# 외부에서 불러쓸 수 있는 제어 함수
def start_recording(video_id="sample"):
    global recording_thread, recording_active
    if recording_active:
        print("[INFO] 이미 녹화 중입니다.")
        return
    recording_active = True
    recording_thread = threading.Thread(target=record_loop, args=(video_id,))
    recording_thread.start()
    print("[INFO] 녹화 시작됨.")

def stop_recording():
    global recording_active
    recording_active = False
    print("[INFO] 녹화 종료 요청됨.")
