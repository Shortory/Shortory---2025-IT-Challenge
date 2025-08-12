# object_detector.py
import os
import json
import cv2
from typing import List, Dict, Any, Optional, Tuple
from ultralytics import YOLO


# 전역에서 한 번만 로드 (필요시 device 선택 가능)
_yolo_model = None


def _get_model(device: Optional[str] = None) -> YOLO:
    global _yolo_model
    if _yolo_model is None:
        _yolo_model = YOLO("yolov8n.pt")
        if device:
            _yolo_model.to(device)
    return _yolo_model


def detect_objects_in_video(
    video_path: str,
    skip_frames: int = 1,
    save_path: Optional[str] = None,
    device: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    비디오에서 객체 탐지 결과를 프레임 단위로 추출.
    결과는 메모리로 반환하고, save_path가 주어지면 JSON으로 저장.

    Args:
        video_path: 분석할 비디오 경로
        skip_frames: 프레임 스킵 간격 (1이면 모든 프레임 처리)
        save_path: 결과를 JSON으로 저장할 경로
        device: 'cuda', 'cpu' 등 (None이면 기본값)

    Returns:
        [
          {
            "frame_id": int,
            "timestamp": float,
            "objects": [{"label": str, "bbox": [x1,y1,x2,y2], "confidence": float}],
            "resolution": [width, height]
          }, ...
        ]
    """
    model = _get_model(device=device)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"영상 열기 실패: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    print("[DEBUG] FPS:", fps)  # 추가
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    results: List[Dict[str, Any]] = []
    frame_id = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_id % skip_frames != 0:
                frame_id += 1
                continue

            yolo_result = model.predict(frame, verbose=False)[0]
            frame_objects = []
            for box in yolo_result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                cls_id = int(box.cls[0].item())
                # 최신 ultralytics에서는 model.names 로 접근
                label = model.names[cls_id]
                conf = float(box.conf[0].item())

                frame_objects.append({
                    "label": label,
                    "bbox": [x1, y1, x2, y2],
                    "confidence": conf
                })

            timestamp = frame_id / fps
            # === 이 줄 바로 아래에 추가 ===
            print(f"[DEBUG] frame_id={frame_id}, timestamp={timestamp}")
            results.append({
                "frame_id": frame_id,
                "timestamp": round(timestamp, 3),
                "objects": frame_objects,
                "resolution": [width, height]
            })

            frame_id += 1
    finally:
        cap.release()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

    return results
