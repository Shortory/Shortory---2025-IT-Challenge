# analysis_service.py
import os
import base64
import shutil
from datetime import datetime
from reviewer.analysis import emotion_gaze, run_pipeline

# 로그 저장 디렉토리
LOG_DIR = "analysis_logs"
PIPELINE_LOG_DIR = os.path.join("logs")  # static 기준 루트에 logs 디렉토리
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(PIPELINE_LOG_DIR, exist_ok=True)

def start_analysis(task_id):
    log_path = os.path.join(LOG_DIR, f"{task_id}.csv")
    if not os.path.exists(log_path):
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("timestamp,video_time,emotion,attention\n")
    print(f"[START] 분석 시작: 로그 파일 생성됨 - {log_path}")
    return {"status": "started"}


def analyze_frame(image_base64, task_id, video_time):
    try:
        image_data = base64.b64decode(image_base64.split(',')[1])
        emotion, attention = emotion_gaze.analyze_image(image_data)

        log_path = os.path.join(LOG_DIR, f"{task_id}.csv")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"{now},{video_time:.2f},{emotion},{attention}\n")

        print(f"[LOG] {task_id} - {emotion}, {attention} @ {video_time:.2f}s")

        return {"status": "success"}
    except Exception as e:
        print(f"[ERROR] analyze_frame 실패: {e}")
        return {"status": "error", "message": str(e)}


def stop_analysis(task_id):
    try:
        log_path = os.path.join(LOG_DIR, f"{task_id}.csv")
        if not os.path.exists(log_path):
            return {"status": "error", "message": "로그 파일이 존재하지 않습니다."}

        # ✅ run_pipeline에서 기대하는 경로로 로그 복사
        target_log_path = os.path.join(PIPELINE_LOG_DIR, f"{task_id}_emotion_log.csv")
        shutil.copyfile(log_path, target_log_path)
        print(f"[INFO] 감정 로그 복사됨: {target_log_path}")

        print(f"[STOP] 분석 종료. 파이프라인 실행 시작 - {log_path}")
        run_pipeline.run(task_id, log_path)

        # ❌ 여기에서 done.flag를 다시 만들지 않음 (run_pipeline에서 생성됨)

        return {"status": "completed"}
    except Exception as e:
        print(f"[ERROR] stop_analysis 실패: {e}")
        return {"status": "error", "message": str(e)}
