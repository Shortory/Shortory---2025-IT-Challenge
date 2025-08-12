import os
import argparse
from .object_detector import detect_objects_in_video
from .focus_analyzer import analyze_focus_from_logs
from .shorts_generator import generate_highlight_shorts

# ✅ .flaskroot 기준으로 Flask 프로젝트 루트를 찾는 함수
def find_project_root():
    cur = os.path.abspath(os.path.dirname(__file__))
    while cur != os.path.dirname(cur):  # root까지 순회
        if '.flaskroot' in os.listdir(cur):
            return cur
        cur = os.path.dirname(cur)
    raise FileNotFoundError("Flask 프로젝트 루트를 찾을 수 없습니다. .flaskroot가 없음.")

# ▶ Flask 프로젝트 루트 디렉토리 탐색
ROOT_DIR = find_project_root()
print("[CHECK] Flask 루트 디렉토리:", ROOT_DIR)

# ▶ Flask 기준 디렉토리 설정
OUTPUT_DIR = os.path.join(ROOT_DIR, 'static', 'shorts_output')
VIDEO_DIR = os.path.join(ROOT_DIR, 'reviewer', 'emotion_uploads')
LOG_DIR = os.path.join(ROOT_DIR, 'logs')
OBJECT_DIR = os.path.join(ROOT_DIR, 'object_detection_results')
FOCUS_DIR = os.path.join(ROOT_DIR, 'focus_analysis_results')

# ▶ 디렉토리 생성
os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(OBJECT_DIR, exist_ok=True)
os.makedirs(FOCUS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

def run_pipeline(
    video_id: str,
    log_path: str = None,
    skip_frames: int = 1,
    window_sec: int = 10,
    step_sec: int = 5,
    top_k: int = 3,
    device: str = None,
    progress_callback=None
):
    print(f"[INFO] 유튜브 영상 ID: {video_id}")

    video_path = os.path.join(VIDEO_DIR, f"{video_id}.mp4")
    if log_path is None:
        log_path = os.path.join(LOG_DIR, f"{video_id}_emotion_log.csv")
    object_path = os.path.join(OBJECT_DIR, f"{video_id}_objects.json")
    focus_path = os.path.join(FOCUS_DIR, f"{video_id}_focus.json")

    # ✅ Flask static 디렉토리 (사용자에게 보여지는 숏폼들)
    output_path = os.path.join(OUTPUT_DIR, video_id)
    os.makedirs(output_path, exist_ok=True)

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"video not found: {video_path}")
    if not os.path.exists(log_path):
        raise FileNotFoundError(f"emotion log not found: {log_path}")

    # Step 1: 객체 인식
    print("[STEP 1] 객체 인식 시작")
    if progress_callback: progress_callback(10)
    detect_objects_in_video(
        video_path=video_path,
        skip_frames=skip_frames,
        save_path=object_path,
        device=device
    )
    if progress_callback: progress_callback(30)

    # Step 2: 집중도 분석
    print("[STEP 2] 집중도 분석 시작")
    if progress_callback: progress_callback(40)
    analyze_focus_from_logs(
        video_path=video_path,
        log_path=log_path,
        object_path=object_path,
        save_path=focus_path,
        window_sec=window_sec,
        step_sec=step_sec,
        top_k=top_k
    )
    if progress_callback: progress_callback(70)

    # Step 3: 숏폼 생성
    print("[STEP 3] 숏폼 생성 시작")
    if progress_callback: progress_callback(80)
    generate_highlight_shorts(
        video_path=video_path,
        focus_path=focus_path,
        output_dir=output_path,
        default_window_sec=window_sec
    )
    if progress_callback: progress_callback(100)

    # ✅ done.flag 파일 생성 위치 (Flask가 접근 가능한 위치 하나만 사용)
    done_flag_path = os.path.join(output_path, "done.flag")  # 💡
    with open(done_flag_path, "w") as f:
        f.write("completed")

    print(f"[COMPLETE] 전체 파이프라인 완료. 결과 디렉토리: {output_path}")
    print(f"[COMPLETE] done.flag 생성 위치:\n- {done_flag_path}")


# 🔹 stop_analysis()에서 호출하는 wrapper
def run(task_id, log_path=None):
    run_pipeline(video_id=task_id, log_path=log_path)

# 🔹 CLI 실행용
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="유튜브 영상 기반 숏폼 생성 파이프라인")
    parser.add_argument("video_id", type=str, help="분석할 유튜브 영상 ID (파일명과 동일)")
    parser.add_argument("--skip_frames", type=int, default=1, help="객체 인식 시 프레임 스킵 간격")
    parser.add_argument("--window_sec", type=int, default=10, help="집중 구간 길이(초)")
    parser.add_argument("--step_sec", type=int, default=5, help="슬라이딩 윈도우 스텝(초)")
    parser.add_argument("--top_k", type=int, default=3, help="최종 상위 구간 개수")
    parser.add_argument("--device", type=str, default=None, help="'cuda' or 'cpu'")
    args = parser.parse_args()

    run_pipeline(
        video_id=args.video_id,
        skip_frames=args.skip_frames,
        window_sec=args.window_sec,
        step_sec=args.step_sec,
        top_k=args.top_k,
        device=args.device
    )
