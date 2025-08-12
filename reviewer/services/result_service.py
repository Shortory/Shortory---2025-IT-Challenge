import os

OUTPUT_DIR = os.path.join("static", "shorts_output")
ANALYSIS_DIR = os.path.join("analysis_outputs")


def get_flask_root_dir():
    cur = os.path.abspath(os.path.dirname(__file__))
    while cur != os.path.dirname(cur):
        if '.flaskroot' in os.listdir(cur):
            return cur
        cur = os.path.dirname(cur)
    raise RuntimeError(".flaskroot 기준 루트 디렉토리를 찾을 수 없습니다.")


def get_progress(task_id):
    return 100 if is_analysis_completed(task_id) else 60


def is_analysis_completed(task_id):
    BASE_DIR = get_flask_root_dir()
    done_flag = os.path.join(BASE_DIR, "static", "shorts_output", task_id, "done.flag")
    return os.path.exists(done_flag)


def get_result_clips(task_id):
    BASE_DIR = get_flask_root_dir()
    CLIP_DIR = os.path.join(BASE_DIR, "static", "shorts_output", task_id)
    result = []

    if not os.path.exists(CLIP_DIR):
        print(f"[WARNING] 숏폼 디렉토리 없음: {CLIP_DIR}")
        return []

    files = sorted([f for f in os.listdir(CLIP_DIR) if f.endswith(".mp4")])
    if not files:
        print(f"[WARNING] mp4 파일 없음: {CLIP_DIR}")

    for f in files:
        # 파일명 파싱 (예시: short_01_happy_None_131s_1.27.mp4)
        parts = f.split('_')
        try:
            emotion = parts[2] if len(parts) > 2 else "unknown"
            timestamp_sec = parts[4][:-1] if len(parts) > 4 else ""
            try:
                ts = int(float(timestamp_sec))
                minutes = ts // 60
                seconds = ts % 60
                timestamp_str = f"{minutes:02d}:{seconds:02d}"
            except:
                timestamp_str = "00:00"
        except Exception as e:
            emotion = "unknown"
            timestamp_str = "00:00"

        result.append({
            "filename": f"{task_id}/{f}",
            "emotion": emotion,
            "timestamp": timestamp_str
        })

    return result
