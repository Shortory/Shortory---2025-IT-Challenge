import os
import json
import subprocess
import cv2
from typing import List, Dict, Any, Optional


def format_drawtext(emotion: Optional[str], obj: Optional[str], score: Optional[float] = None) -> str:
    """
    drawtext용 문자열 escape 및 스타일 지정
    """
    emotion = (emotion or "Neutral").capitalize().replace(":", "\\:").replace(" ", "\\ ")
    obj = (obj or "Object").capitalize().replace(":", "\\:").replace(" ", "\\ ")
    if score is None:
        text = f"Focus\\: {emotion} on {obj}"
    else:
        text = f"Focus\\: {emotion} on {obj} (score\\: {score:.2f})"
    return f"drawtext=text='{text}':fontcolor=red:fontsize=24:x=10:y=H-th-10"


def generate_shorts(
    video_path: str,
    output_dir: str,
    segments: List[Dict[str, Any]],
    window_sec: int = 10
) -> List[str]:
    """
    상위 집중 구간 리스트를 기반으로 숏폼 생성
    영상이 짧을 경우 해당 길이만큼 생성되도록 보완
    """
    os.makedirs(output_dir, exist_ok=True)
    output_files: List[str] = []

    # 🔍 1. 전체 영상 길이 확인
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    video_duration = total_frames / fps if fps > 0 else 0
    cap.release()

    for idx, seg in enumerate(segments, start=1):
        start_time = float(seg["start"])
        emotion = seg.get("emotion", "neutral")
        obj = seg.get("object", "object")
        score = seg.get("score", 0.0)
        win = int(seg.get("window", window_sec))

        # 🔧 2. 남은 영상 길이에 맞게 길이 조정
        end_time = start_time + win
        if end_time > video_duration:
            win = max(1, int(video_duration - start_time))  # 최소 1초 이상일 때만 생성

        if win <= 0:
            print(f"[SKIP] 영상 너무 짧아 클립 생성 생략 (start: {start_time}s)")
            continue

        output_filename = f"short_{idx:02d}_{emotion}_{obj}_{int(start_time)}s_{score:.2f}.mp4"
        output_path = os.path.join(output_dir, output_filename)

        drawtext = format_drawtext(emotion, obj, score)

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_time),
            "-t", str(win),
            "-i", video_path,
            "-vf", drawtext,
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-movflags", "+faststart",
            output_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')

        if result.returncode != 0:
            print(f"[FFMPEG ERROR] Failed to create {output_filename}")
            print(result.stderr)
            continue

        print(f"[FFMPEG OK] Created: {output_filename}")
        output_files.append(output_path)

    return output_files


def generate_highlight_shorts(
    video_path: str,
    focus_path: str,
    output_dir: str,
    default_window_sec: int = 10
) -> List[str]:
    """
    저장된 focus 결과(JSON)를 읽어 generate_shorts를 호출하는 래퍼 함수
    """
    with open(focus_path, "r", encoding="utf-8") as f:
        segments = json.load(f)

    return generate_shorts(
        video_path=video_path,
        output_dir=output_dir,
        segments=segments,
        window_sec=default_window_sec
    )
